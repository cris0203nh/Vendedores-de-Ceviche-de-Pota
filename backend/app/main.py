from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from contextlib import contextmanager
import sqlite3

DB = Path(__file__).resolve().parent.parent / "ceviche_seguro.db"

app = FastAPI(
    title="CevicheSeguro API",
    description="Trazabilidad y control sanitario de vendedores de ceviche de pota",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@contextmanager
def database():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

def initialize():
    with database() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS vendedores(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            documento TEXT NOT NULL UNIQUE,
            telefono TEXT,
            puesto TEXT NOT NULL,
            ubicacion TEXT,
            licencia TEXT DEFAULT 'Pendiente',
            estado TEXT DEFAULT 'Activo',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS inspecciones(
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

        CREATE TABLE IF NOT EXISTS proveedores(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            documento TEXT,
            telefono TEXT,
            procedencia TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS lotes(
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

        CREATE TABLE IF NOT EXISTS reportes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendedor_id INTEGER,
            descripcion TEXT NOT NULL,
            tipo TEXT NOT NULL,
            estado TEXT DEFAULT 'Recibido',
            respuesta TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(vendedor_id) REFERENCES vendedores(id)
        );

        CREATE TABLE IF NOT EXISTS incumplimientos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspeccion_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            evidencia TEXT,
            estado TEXT DEFAULT 'Pendiente',
            FOREIGN KEY(inspeccion_id) REFERENCES inspecciones(id)
        );
        """)

initialize()

class Vendedor(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    documento: str = Field(pattern=r"^\d{8}$")
    telefono: str = ""
    puesto: str = Field(min_length=2)
    ubicacion: str = ""
    licencia: str = "Pendiente"

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

def rows(sql, params=()):
    with database() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]

def insert(sql, params):
    try:
        with database() as con:
            cur = con.execute(sql, params)
            return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Registro duplicado o relacionado inexistente") from exc

@app.get("/")
def inicio():
    return {"sistema": "CevicheSeguro", "estado": "operativo"}

@app.get("/api/health")
def health():
    return {"estado": "operativo", "base_datos": "SQLite"}

# VDCP-5: Registro de vendedores
@app.post("/api/vendedores", status_code=201)
def crear_vendedor(data: Vendedor):
    id = insert(
        """INSERT INTO vendedores(nombre,documento,telefono,puesto,ubicacion,licencia)
        VALUES(?,?,?,?,?,?)""",
        (data.nombre,data.documento,data.telefono,data.puesto,data.ubicacion,data.licencia)
    )
    return {"id": id, "mensaje": "Vendedor registrado"}

# VDCP-6: Registro y consulta de puestos
@app.get("/api/vendedores")
def listar_vendedores():
    return rows("SELECT * FROM vendedores ORDER BY id DESC")

@app.get("/api/vendedores/{id}")
def consultar_vendedor(id: int):
    result = rows("SELECT * FROM vendedores WHERE id=?", (id,))
    if not result:
        raise HTTPException(404, "Vendedor no encontrado")
    return result[0]

# VDCP-7: Verificación de licencias
@app.patch("/api/vendedores/{id}/licencia")
def verificar_licencia(id: int, data: Licencia):
    if data.estado not in ["Vigente", "Observada", "Vencida", "Pendiente"]:
        raise HTTPException(422, "Estado de licencia inválido")
    with database() as con:
        cur = con.execute("UPDATE vendedores SET licencia=? WHERE id=?", (data.estado,id))
        if not cur.rowcount:
            raise HTTPException(404, "Vendedor no encontrado")
    return {"mensaje": "Licencia actualizada", "estado": data.estado}

# VDCP-8 y VDCP-9: Inspecciones y temperaturas
@app.post("/api/inspecciones", status_code=201)
def crear_inspeccion(data: Inspeccion):
    if not rows("SELECT id FROM vendedores WHERE id=?", (data.vendedor_id,)):
        raise HTTPException(404, "Vendedor no encontrado")
    id = insert(
        """INSERT INTO inspecciones(vendedor_id,inspector,higiene,temperatura,
        conservacion,observaciones,resultado) VALUES(?,?,?,?,?,?,?)""",
        (data.vendedor_id,data.inspector,data.higiene,data.temperatura,
         data.conservacion,data.observaciones,data.resultado)
    )
    return {"id": id, "mensaje": "Inspección registrada"}

@app.get("/api/inspecciones")
def listar_inspecciones():
    return rows("""
        SELECT i.*,v.nombre AS vendedor FROM inspecciones i
        JOIN vendedores v ON v.id=i.vendedor_id ORDER BY i.id DESC
    """)

# VDCP-10: Incumplimientos sanitarios
@app.post("/api/incumplimientos", status_code=201)
def crear_incumplimiento(data: Incumplimiento):
    if not rows("SELECT id FROM inspecciones WHERE id=?", (data.inspeccion_id,)):
        raise HTTPException(404, "Inspección no encontrada")
    id = insert(
        "INSERT INTO incumplimientos(inspeccion_id,descripcion,evidencia) VALUES(?,?,?)",
        (data.inspeccion_id,data.descripcion,data.evidencia)
    )
    return {"id": id, "mensaje": "Incumplimiento registrado"}

@app.get("/api/incumplimientos")
def listar_incumplimientos():
    return rows("SELECT * FROM incumplimientos ORDER BY id DESC")

# VDCP-11: Registro de proveedores
@app.post("/api/proveedores", status_code=201)
def crear_proveedor(data: Proveedor):
    id = insert(
        "INSERT INTO proveedores(nombre,documento,telefono,procedencia) VALUES(?,?,?,?)",
        (data.nombre,data.documento,data.telefono,data.procedencia)
    )
    return {"id": id, "mensaje": "Proveedor registrado"}

@app.get("/api/proveedores")
def listar_proveedores():
    return rows("SELECT * FROM proveedores ORDER BY id DESC")

# VDCP-12: Registro de lotes
@app.post("/api/lotes", status_code=201)
def crear_lote(data: Lote):
    if not rows("SELECT id FROM proveedores WHERE id=?", (data.proveedor_id,)):
        raise HTTPException(404, "Proveedor no encontrado")
    id = insert(
        """INSERT INTO lotes(codigo,proveedor_id,fecha_ingreso,especie_declarada,
        cantidad,unidad,procedencia) VALUES(?,?,?,?,?,?,?)""",
        (data.codigo,data.proveedor_id,data.fecha_ingreso,data.especie_declarada,
         data.cantidad,data.unidad,data.procedencia)
    )
    return {"id": id, "mensaje": "Lote registrado"}

@app.get("/api/lotes")
def listar_lotes():
    return rows("""
        SELECT l.*,p.nombre AS proveedor FROM lotes l
        JOIN proveedores p ON p.id=l.proveedor_id ORDER BY l.id DESC
    """)

# VDCP-13: Verificación de información del producto
@app.patch("/api/lotes/{id}/verificacion")
def verificar_lote(id: int, data: Verificacion):
    if data.verificacion not in ["Verificado", "Observado", "Pendiente"]:
        raise HTTPException(422, "Resultado de verificación inválido")
    with database() as con:
        cur = con.execute(
            "UPDATE lotes SET verificacion=?,observaciones=? WHERE id=?",
            (data.verificacion,data.observaciones,id)
        )
        if not cur.rowcount:
            raise HTTPException(404, "Lote no encontrado")
    return {"mensaje": "Verificación actualizada"}

# VDCP-14: Consulta pública de vendedores
@app.get("/api/publico/vendedores")
def consulta_publica():
    return rows("""
        SELECT id,nombre,puesto,ubicacion,licencia,estado
        FROM vendedores WHERE estado='Activo' ORDER BY nombre
    """)

# VDCP-15: Denuncias ciudadanas
@app.post("/api/reportes", status_code=201)
def crear_reporte(data: Reporte):
    id = insert(
        "INSERT INTO reportes(vendedor_id,descripcion,tipo) VALUES(?,?,?)",
        (data.vendedor_id,data.descripcion,data.tipo)
    )
    return {"id": id, "codigo_seguimiento": f"REP-{id:05d}"}

# VDCP-16: Gestión de reportes
@app.get("/api/reportes")
def listar_reportes():
    return rows("""
        SELECT r.*,v.nombre AS vendedor FROM reportes r
        LEFT JOIN vendedores v ON v.id=r.vendedor_id ORDER BY r.id DESC
    """)

@app.patch("/api/reportes/{id}")
def actualizar_reporte(id: int, data: ActualizarReporte):
    if data.estado not in ["Recibido", "En revisión", "Atendido", "Rechazado"]:
        raise HTTPException(422, "Estado de reporte inválido")
    with database() as con:
        cur = con.execute(
            "UPDATE reportes SET estado=?,respuesta=? WHERE id=?",
            (data.estado,data.respuesta,id)
        )
        if not cur.rowcount:
            raise HTTPException(404, "Reporte no encontrado")
    return {"mensaje": "Reporte actualizado"}

@app.get("/api/dashboard")
def dashboard():
    return {
        "vendedores": rows("SELECT COUNT(*) AS total FROM vendedores")[0]["total"],
        "inspecciones": rows("SELECT COUNT(*) AS total FROM inspecciones")[0]["total"],
        "proveedores": rows("SELECT COUNT(*) AS total FROM proveedores")[0]["total"],
        "lotes": rows("SELECT COUNT(*) AS total FROM lotes")[0]["total"],
        "reportes_pendientes": rows(
            "SELECT COUNT(*) AS total FROM reportes WHERE estado='Recibido'"
        )[0]["total"]
    }
def migrate_database():
    with database() as con:
        columns = {
            row["name"]
            for row in con.execute("PRAGMA table_info(vendedores)").fetchall()
        }

        migrations = {
            "telefono": "ALTER TABLE vendedores ADD COLUMN telefono TEXT",
            "ubicacion": "ALTER TABLE vendedores ADD COLUMN ubicacion TEXT",
            "licencia": "ALTER TABLE vendedores ADD COLUMN licencia TEXT DEFAULT 'Pendiente'",
            "created_at": "ALTER TABLE vendedores ADD COLUMN created_at DATETIME"
        }

        for column, sql in migrations.items():
            if column not in columns:
                con.execute(sql)

migrate_database()
