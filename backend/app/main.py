from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from contextlib import contextmanager
import sqlite3

app = FastAPI(
    title="CevicheSeguro API",
    description="Sistema de trazabilidad y control sanitario de vendedores de ceviche de pota",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

DATABASE = Path(__file__).resolve().parent.parent / "ceviche_seguro.db"

@contextmanager
def database():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def rows(sql, params=()):
    with database() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]

def insert(sql, params):
    try:
        with database() as con:
            cursor = con.execute(sql, params)
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="El registro ya existe o contiene una referencia inválida"
        ) from exc

def initialize_database():
    with database() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS vendedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                documento TEXT NOT NULL UNIQUE,
                telefono TEXT,
                puesto TEXT NOT NULL,
                ubicacion TEXT,
                licencia TEXT DEFAULT 'Pendiente',
                estado TEXT DEFAULT 'Activo',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migración compatible con bases de datos anteriores
        columns = {
            row["name"]
            for row in con.execute("PRAGMA table_info(vendedores)").fetchall()
        }

        migrations = {
            "telefono": "ALTER TABLE vendedores ADD COLUMN telefono TEXT",
            "ubicacion": "ALTER TABLE vendedores ADD COLUMN ubicacion TEXT",
            "licencia": "ALTER TABLE vendedores ADD COLUMN licencia TEXT DEFAULT 'Pendiente'",
            "estado": "ALTER TABLE vendedores ADD COLUMN estado TEXT DEFAULT 'Activo'",
            "created_at": "ALTER TABLE vendedores ADD COLUMN created_at DATETIME"
        }

        for column, sql in migrations.items():
            if column not in columns:
                con.execute(sql)

        con.execute("""
            CREATE TABLE IF NOT EXISTS puestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor_id INTEGER NOT NULL,
                nombre_puesto TEXT NOT NULL,
                ubicacion TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(vendedor_id) REFERENCES vendedores(id),
                UNIQUE(vendedor_id, nombre_puesto, ubicacion)
            )
        """)

@app.on_event("startup")
def startup():
    initialize_database()

class Vendedor(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    documento: str = Field(pattern=r"^\d{8}$")
    telefono: str = ""
    puesto: str = Field(min_length=2)
    ubicacion: str = ""
    licencia: str = "Pendiente"

class Puesto(BaseModel):
    vendedor_id: int = Field(gt=0)
    nombre_puesto: str = Field(min_length=2, max_length=120)
    ubicacion: str = Field(min_length=3, max_length=200)

@app.get("/")
def inicio():
    return {"mensaje": "CevicheSeguro API funcionando"}

@app.get("/api/health")
def health():
    return {"estado": "operativo", "base_datos": "SQLite"}

# HU-01: Registro de vendedores
@app.post("/api/vendedores", status_code=201)
def crear_vendedor(data: Vendedor):
    vendedor_id = insert("""
        INSERT INTO vendedores(nombre,documento,telefono,puesto,ubicacion,licencia)
        VALUES(?,?,?,?,?,?)
    """, (
        data.nombre.strip(),
        data.documento,
        data.telefono,
        data.puesto.strip(),
        data.ubicacion,
        data.licencia
    ))
    return {"id": vendedor_id, "mensaje": "Vendedor registrado"}

@app.get("/api/vendedores")
def listar_vendedores():
    return rows("SELECT * FROM vendedores ORDER BY id DESC")

@app.get("/api/vendedores/{id}")
def consultar_vendedor(id: int):
    resultado = rows("SELECT * FROM vendedores WHERE id=?", (id,))
    if not resultado:
        raise HTTPException(404, "Vendedor no encontrado")
    return resultado[0]

# HU-02: Registro de puestos de venta
@app.post("/api/puestos", status_code=201)
def crear_puesto(data: Puesto):
    vendedor = rows(
        "SELECT id FROM vendedores WHERE id=?",
        (data.vendedor_id,)
    )

    if not vendedor:
        raise HTTPException(404, "El vendedor no está registrado")

    existente = rows("""
        SELECT id FROM puestos
        WHERE vendedor_id=?
        AND LOWER(TRIM(nombre_puesto))=LOWER(TRIM(?))
        AND LOWER(TRIM(ubicacion))=LOWER(TRIM(?))
    """, (
        data.vendedor_id,
        data.nombre_puesto,
        data.ubicacion
    ))

    if existente:
        raise HTTPException(
            409,
            "Este puesto ya está registrado para el vendedor"
        )

    puesto_id = insert("""
        INSERT INTO puestos(vendedor_id,nombre_puesto,ubicacion)
        VALUES(?,?,?)
    """, (
        data.vendedor_id,
        data.nombre_puesto.strip(),
        data.ubicacion.strip()
    ))

    return {
        "id": puesto_id,
        "vendedor_id": data.vendedor_id,
        "mensaje": "Puesto de venta registrado correctamente"
    }

@app.get("/api/puestos")
def listar_puestos():
    return rows("""
        SELECT p.id,p.vendedor_id,v.nombre AS vendedor,
        p.nombre_puesto,p.ubicacion,p.created_at
        FROM puestos p
        JOIN vendedores v ON v.id=p.vendedor_id
        ORDER BY p.id DESC
    """)

# ENDPOINTS GENERALES DEL SISTEMA

@app.get("/api/publico/vendedores")
def vendedores_publicos():
    return rows("""
        SELECT id, nombre, puesto, ubicacion, estado
        FROM vendedores
        ORDER BY nombre ASC
    """)

@app.get("/api/dashboard")
def dashboard():
    vendedores = rows("SELECT COUNT(*) AS total FROM vendedores")[0]["total"]
    puestos = rows("SELECT COUNT(*) AS total FROM puestos")[0]["total"]

    return {
        "vendedores": vendedores,
        "puestos": puestos
    }
