"""
Base de datos SQLite (data/eggs.db).

La tabla se define UNA sola vez, acá: la app, el panel y el script de
datos de ejemplo importan este módulo para no repetir el esquema.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

# Raíz del proyecto: app/ está al lado de config.yaml
RAIZ = Path(__file__).resolve().parent.parent


def ruta_base_datos():
    """Ruta del archivo de base de datos, según config.yaml (rutas.base_datos)."""
    with open(RAIZ / "config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return RAIZ / config["rutas"]["base_datos"]


def crear_tabla():
    """Crea la tabla de resultados si todavía no existe.

    Si encuentra el esquema viejo (con peso_estimado), lo migra al
    nuevo (dimensiones en mm).
    """
    ruta = ruta_base_datos()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS clasificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora TEXT NOT NULL,
                lote TEXT,
                defecto TEXT,
                confianza REAL,
                largo_mm REAL,
                ancho_mm REAL,
                categoria_tamano TEXT,
                es_demo INTEGER DEFAULT 0
            )
        """)
        # Migración: la tabla vieja guardaba peso_estimado; ahora se
        # guardan el largo y el ancho medidos en mm
        columnas = [
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(clasificaciones)"
            )
        ]
        if "peso_estimado" in columnas and "largo_mm" not in columnas:
            conexion.execute(
                "ALTER TABLE clasificaciones DROP COLUMN peso_estimado"
            )
            conexion.execute(
                "ALTER TABLE clasificaciones ADD COLUMN largo_mm REAL"
            )
            conexion.execute(
                "ALTER TABLE clasificaciones ADD COLUMN ancho_mm REAL"
            )
        conexion.commit()
    finally:
        conexion.close()


def guardar_resultado(lote, defecto, confianza, largo_mm, ancho_mm, categoria):
    """Guarda una clasificación hecha por la app (es_demo = 0)."""
    conexion = sqlite3.connect(ruta_base_datos())
    try:
        conexion.execute(
            """
            INSERT INTO clasificaciones
                (fecha_hora, lote, defecto, confianza, largo_mm,
                 ancho_mm, categoria_tamano, es_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             lote, defecto, confianza, largo_mm, ancho_mm, categoria),
        )
        conexion.commit()
    finally:
        conexion.close()


def leer_dataframe(sql, params=()):
    """Ejecuta una consulta SELECT y devuelve un DataFrame de pandas."""
    conexion = sqlite3.connect(ruta_base_datos())
    try:
        return pd.read_sql_query(sql, conexion, params=params)
    finally:
        conexion.close()
