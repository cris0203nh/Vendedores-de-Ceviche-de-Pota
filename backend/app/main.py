
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

DATABASE = Path(__file__).resolve().parent.parent / "ceviche_seguro.db"

app = FastAPI(
    title="CevicheSeguro API",
    description="Trazabilidad y control sanitario de vendedores de ceviche de pota",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CONEXIÓN Y OPERACIONES SQLITE
# =========================================================

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
        return [
            dict(row)
            for row in con.execute(sql, params).fetchall()
        ]


def insert(sql, params):
    try:
        with database() as con:
            cursor = con.execute(sql, params)
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="El registro ya existe o contiene una referencia inválida",
        ) from exc


# =========================================================
# INICIALIZACIÓN DE BASE DE DATOS
# =========================================================

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

        columns = {
            row["name"]
            for row in con.execute(
                "PRAGMA table_info(vendedores)"
            ).fetchall()
        }

        migrations = {
            "telefono": "ALTER TABLE vendedores ADD COLUMN telefono TEXT",
            "ubicacion": "ALTER TABLE vendedores ADD COLUMN ubicacion TEXT",
            "licencia": "ALTER TABLE vendedores ADD COLUMN licencia TEXT DEFAULT 'Pendiente'",
            "estado": "ALTER TABLE vendedores ADD COLUMN estado TEXT DEFAULT 'Activo'",
            "created_at": "ALTER TABLE vendedores ADD COLUMN created_at DATETIME",
        }

        for column, sql in migrations.items():
            if column not in columns:
                con.execute(sql)

        con.executescript("""
            CREATE TABLE IF NOT EXISTS puestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor_id INTEGER NOT NULL,
                nombre_puesto TEXT NOT NULL,
                ubicacion TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(vendedor_id) REFERENCES vendedores(id),
                UNIQUE(vendedor_id, nombre_puesto, ubicacion)
            );

            CREATE TABLE IF NOT EXISTS inspecciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor_id INTEGER NOT NULL,
                inspector TEXT NOT NULL,
                higiene TEXT NOT NULL,
                temperatura REAL,
                conservacion TEXT,
                observaciones TEXT,
                resultado TEXT DEFAULT 'Pendiente',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(vendedor_id) REFERENCES vendedores(id)
            );

            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                documento TEXT,
                telefono TEXT,
                procedencia TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                proveedor_id INTEGER NOT NULL,
                fecha_ingreso TEXT NOT NULL,
                especie_declarada TEXT NOT NULL,
                cantidad REAL NOT NULL,
                unidad TEXT DEFAULT 'kg',
                procedencia TEXT,
                verificacion TEXT DEFAULT 'Pendiente',
                observaciones TEXT,
                FOREIGN KEY(proveedor_id) REFERENCES proveedores(id)
            );

            CREATE TABLE IF NOT EXISTS reportes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor_id INTEGER,
                descripcion TEXT NOT NULL,
                tipo TEXT NOT NULL,
                estado TEXT DEFAULT 'Recibido',
                respuesta TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(vendedor_id) REFERENCES vendedores(id)
            );

            CREATE TABLE IF NOT EXISTS incumplimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspeccion_id INTEGER NOT NULL,
                descripcion TEXT NOT NULL,
                evidencia TEXT,
                estado TEXT DEFAULT 'Pendiente',
                FOREIGN KEY(inspeccion_id) REFERENCES inspecciones(id)
            );
        """)


initialize_database()


# =========================================================
# MODELOS DE DATOS
# =========================================================

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


class Licencia(BaseModel):
    estado: str


class Inspeccion(BaseModel):
    vendedor_id: int
    inspector: str
    higiene: str
    temperatura: float | None = None
    conservacion: str = ""
    observaciones: str = ""
    resultado: str = "Pendiente"


class Proveedor(BaseModel):
    nombre: str
    documento: str = ""
    telefono: str = ""
    procedencia: str


class Lote(BaseModel):
    codigo: str
    proveedor_id: int
    fecha_ingreso: str
    especie_declarada: str
    cantidad: float = Field(gt=0)
    unidad: str = "kg"
    procedencia: str = ""


class Verificacion(BaseModel):
    verificacion: str
    observaciones: str = ""


class Reporte(BaseModel):
    vendedor_id: int | None = None
    descripcion: str
    tipo: str


class ActualizarReporte(BaseModel):
    estado: str
    respuesta: str = ""


class Incumplimiento(BaseModel):
    inspeccion_id: int
    descripcion: str
    evidencia: str = ""


# =========================================================
# RUTAS GENERALES
# =========================================================

@app.get("/")
def inicio():
    return {
        "sistema": "CevicheSeguro",
        "estado": "operativo"
    }


@app.get("/api/health")
def health():
    return {
        "estado": "operativo",
        "base_datos": "SQLite"
    }


# =========================================================
# VDCP-5 / HU-01: REGISTRO DE VENDEDORES
# =========================================================

@app.post("/api/vendedores", status_code=201)
def crear_vendedor(data: Vendedor):
    vendedor_id = insert("""
        INSERT INTO vendedores(
            nombre, documento, telefono, puesto, ubicacion, licencia
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.nombre.strip(),
        data.documento,
        data.telefono.strip(),
        data.puesto.strip(),
        data.ubicacion.strip(),
        data.licencia
    ))

    return {
        "id": vendedor_id,
        "mensaje": "Vendedor registrado"
    }


@app.get("/api/vendedores")
def listar_vendedores():
    return rows(
        "SELECT * FROM vendedores ORDER BY id DESC"
    )


@app.get("/api/vendedores/{id}")
def consultar_vendedor(id: int):
    resultado = rows(
        "SELECT * FROM vendedores WHERE id = ?",
        (id,)
    )

    if not resultado:
        raise HTTPException(
            status_code=404,
            detail="Vendedor no encontrado"
        )

    return resultado[0]


# =========================================================
# VDCP-6 / HU-02: REGISTRO DE PUESTOS
# =========================================================

@app.post("/api/puestos", status_code=201)
def crear_puesto(data: Puesto):

    vendedor = rows(
        "SELECT id FROM vendedores WHERE id = ?",
        (data.vendedor_id,)
    )

    if not vendedor:
        raise HTTPException(
            status_code=404,
            detail="El vendedor no está registrado"
        )

    existente = rows("""
        SELECT id
        FROM puestos
        WHERE vendedor_id = ?
        AND LOWER(TRIM(nombre_puesto)) = LOWER(TRIM(?))
        AND LOWER(TRIM(ubicacion)) = LOWER(TRIM(?))
    """, (
        data.vendedor_id,
        data.nombre_puesto,
        data.ubicacion
    ))

    if existente:
        raise HTTPException(
            status_code=409,
            detail="Este puesto ya está registrado para el vendedor"
        )

    puesto_id = insert("""
        INSERT INTO puestos(
            vendedor_id,
            nombre_puesto,
            ubicacion
        )
        VALUES (?, ?, ?)
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
        SELECT
            p.id,
            p.vendedor_id,
            v.nombre AS vendedor,
            p.nombre_puesto,
            p.ubicacion,
            p.created_at
        FROM puestos p
        INNER JOIN vendedores v
            ON v.id = p.vendedor_id
        ORDER BY p.id DESC
    """)


# =========================================================
# VDCP-7: VERIFICACIÓN DE LICENCIAS
# =========================================================

@app.patch("/api/vendedores/{id}/licencia")
def verificar_licencia(id: int, data: Licencia):

    estados_validos = [
        "Vigente",
        "Observada",
        "Vencida",
        "Pendiente"
    ]

    if data.estado not in estados_validos:
        raise HTTPException(
            status_code=422,
            detail="Estado de licencia inválido"
        )

    with database() as con:
        cursor = con.execute(
            "UPDATE vendedores SET licencia = ? WHERE id = ?",
            (data.estado, id)
        )

        if not cursor.rowcount:
            raise HTTPException(
                status_code=404,
                detail="Vendedor no encontrado"
            )

    return {
        "mensaje": "Licencia actualizada",
        "estado": data.estado
    }


# =========================================================
# VDCP-8 Y VDCP-9: INSPECCIONES Y TEMPERATURAS
# =========================================================

@app.post("/api/inspecciones", status_code=201)
def crear_inspeccion(data: Inspeccion):

    vendedor = rows(
        "SELECT id FROM vendedores WHERE id = ?",
        (data.vendedor_id,)
    )

    if not vendedor:
        raise HTTPException(
            status_code=404,
            detail="Vendedor no encontrado"
        )

    inspeccion_id = insert("""
        INSERT INTO inspecciones(
            vendedor_id,
            inspector,
            higiene,
            temperatura,
            conservacion,
            observaciones,
            resultado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.vendedor_id,
        data.inspector,
        data.higiene,
        data.temperatura,
        data.conservacion,
        data.observaciones,
        data.resultado
    ))

    return {
        "id": inspeccion_id,
        "mensaje": "Inspección registrada"
    }


@app.get("/api/inspecciones")
def listar_inspecciones():
    return rows("""
        SELECT i.*, v.nombre AS vendedor
        FROM inspecciones i
        INNER JOIN vendedores v
            ON v.id = i.vendedor_id
        ORDER BY i.id DESC
    """)


# =========================================================
# VDCP-10: INCUMPLIMIENTOS SANITARIOS
# =========================================================

@app.post("/api/incumplimientos", status_code=201)
def crear_incumplimiento(data: Incumplimiento):

    inspeccion = rows(
        "SELECT id FROM inspecciones WHERE id = ?",
        (data.inspeccion_id,)
    )

    if not inspeccion:
        raise HTTPException(
            status_code=404,
            detail="Inspección no encontrada"
        )

    incumplimiento_id = insert("""
        INSERT INTO incumplimientos(
            inspeccion_id,
            descripcion,
            evidencia
        )
        VALUES (?, ?, ?)
    """, (
        data.inspeccion_id,
        data.descripcion,
        data.evidencia
    ))

    return {
        "id": incumplimiento_id,
        "mensaje": "Incumplimiento registrado"
    }


@app.get("/api/incumplimientos")
def listar_incumplimientos():
    return rows(
        "SELECT * FROM incumplimientos ORDER BY id DESC"
    )


# =========================================================
# VDCP-11: REGISTRO DE PROVEEDORES
# =========================================================

@app.post("/api/proveedores", status_code=201)
def crear_proveedor(data: Proveedor):

    proveedor_id = insert("""
        INSERT INTO proveedores(
            nombre,
            documento,
            telefono,
            procedencia
        )
        VALUES (?, ?, ?, ?)
    """, (
        data.nombre,
        data.documento,
        data.telefono,
        data.procedencia
    ))

    return {
        "id": proveedor_id,
        "mensaje": "Proveedor registrado"
    }


@app.get("/api/proveedores")
def listar_proveedores():
    return rows(
        "SELECT * FROM proveedores ORDER BY id DESC"
    )


# =========================================================
# VDCP-12: REGISTRO DE LOTES
# =========================================================

@app.post("/api/lotes", status_code=201)
def crear_lote(data: Lote):

    proveedor = rows(
        "SELECT id FROM proveedores WHERE id = ?",
        (data.proveedor_id,)
    )

    if not proveedor:
        raise HTTPException(
            status_code=404,
            detail="Proveedor no encontrado"
        )

    lote_id = insert("""
        INSERT INTO lotes(
            codigo,
            proveedor_id,
            fecha_ingreso,
            especie_declarada,
            cantidad,
            unidad,
            procedencia
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.codigo,
        data.proveedor_id,
        data.fecha_ingreso,
        data.especie_declarada,
        data.cantidad,
        data.unidad,
        data.procedencia
    ))

    return {
        "id": lote_id,
        "mensaje": "Lote registrado"
    }


@app.get("/api/lotes")
def listar_lotes():
    return rows("""
        SELECT l.*, p.nombre AS proveedor
        FROM lotes l
        INNER JOIN proveedores p
            ON p.id = l.proveedor_id
        ORDER BY l.id DESC
    """)


# =========================================================
# VDCP-13: VERIFICACIÓN DE INFORMACIÓN DEL PRODUCTO
# =========================================================

@app.patch("/api/lotes/{id}/verificacion")
def verificar_lote(id: int, data: Verificacion):

    estados_validos = [
        "Verificado",
        "Observado",
        "Pendiente"
    ]

    if data.verificacion not in estados_validos:
        raise HTTPException(
            status_code=422,
            detail="Resultado de verificación inválido"
        )

    with database() as con:
        cursor = con.execute("""
            UPDATE lotes
            SET verificacion = ?, observaciones = ?
            WHERE id = ?
        """, (
            data.verificacion,
            data.observaciones,
            id
        ))

        if not cursor.rowcount:
            raise HTTPException(
                status_code=404,
                detail="Lote no encontrado"
            )

    return {
        "mensaje": "Verificación actualizada"
    }


# =========================================================
# VDCP-14: CONSULTA PÚBLICA DE VENDEDORES
# =========================================================

@app.get("/api/publico/vendedores")
def consulta_publica():
    return rows("""
        SELECT
            id,
            nombre,
            puesto,
            ubicacion,
            licencia,
            estado
        FROM vendedores
        WHERE estado = 'Activo'
        ORDER BY nombre
    """)


# =========================================================
# VDCP-15: DENUNCIAS CIUDADANAS
# =========================================================

@app.post("/api/reportes", status_code=201)
def crear_reporte(data: Reporte):

    if data.vendedor_id is not None:
        vendedor = rows(
            "SELECT id FROM vendedores WHERE id = ?",
            (data.vendedor_id,)
        )

        if not vendedor:
            raise HTTPException(
                status_code=404,
                detail="Vendedor no encontrado"
            )

    reporte_id = insert("""
        INSERT INTO reportes(
            vendedor_id,
            descripcion,
            tipo
        )
        VALUES (?, ?, ?)
    """, (
        data.vendedor_id,
        data.descripcion,
        data.tipo
    ))

    return {
        "id": reporte_id,
        "codigo_seguimiento": f"REP-{reporte_id:05d}"
    }


# =========================================================
# VDCP-16: GESTIÓN DE REPORTES
# =========================================================

@app.get("/api/reportes")
def listar_reportes():
    return rows("""
        SELECT
            r.*,
            v.nombre AS vendedor
        FROM reportes r
        LEFT JOIN vendedores v
            ON v.id = r.vendedor_id
        ORDER BY r.id DESC
    """)


@app.patch("/api/reportes/{id}")
def actualizar_reporte(id: int, data: ActualizarReporte):

    estados_validos = [
        "Recibido",
        "En revisión",
        "Atendido",
        "Rechazado"
    ]

    if data.estado not in estados_validos:
        raise HTTPException(
            status_code=422,
            detail="Estado de reporte inválido"
        )

    with database() as con:
        cursor = con.execute("""
            UPDATE reportes
            SET estado = ?, respuesta = ?
            WHERE id = ?
        """, (
            data.estado,
            data.respuesta,
            id
        ))

        if not cursor.rowcount:
            raise HTTPException(
                status_code=404,
                detail="Reporte no encontrado"
            )

    return {
        "mensaje": "Reporte actualizado"
    }


# =========================================================
# DASHBOARD GENERAL
# =========================================================

@app.get("/api/dashboard")
def dashboard():
    return {
        "vendedores": rows(
            "SELECT COUNT(*) AS total FROM vendedores"
        )[0]["total"],

        "puestos": rows(
            "SELECT COUNT(*) AS total FROM puestos"
        )[0]["total"],

        "inspecciones": rows(
            "SELECT COUNT(*) AS total FROM inspecciones"
        )[0]["total"],

        "proveedores": rows(
            "SELECT COUNT(*) AS total FROM proveedores"
        )[0]["total"],

        "lotes": rows(
            "SELECT COUNT(*) AS total FROM lotes"
        )[0]["total"],

        "reportes_pendientes": rows(
            "SELECT COUNT(*) AS total FROM reportes WHERE estado = 'Recibido'"
        )[0]["total"],
    }
