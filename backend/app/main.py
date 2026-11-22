from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
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

def initialize_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS vendedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                documento TEXT NOT NULL UNIQUE,
                puesto TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'Pendiente'
            )
        """)

@app.on_event("startup")
def startup():
    initialize_database()

@app.get("/")
def inicio():
    return {"mensaje": "CevicheSeguro API funcionando"}

@app.get("/api/health")
def health():
    return {
        "estado": "operativo",
        "base_datos": "SQLite"
    }
