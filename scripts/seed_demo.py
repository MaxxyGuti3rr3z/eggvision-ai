"""
Paso 4b: carga datos de ejemplo en data/eggs.db.

Genera ~200 registros con es_demo = 1 (simulados), repartidos en varios
lotes y en los últimos días, para probar el panel. Si ya había datos de
demostración los reemplaza, así que se puede volver a correr sin duplicar.

Uso:  python scripts/seed_demo.py
"""

import random
import sqlite3
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Raíz del proyecto: la carpeta que contiene scripts/
RAIZ = Path(__file__).resolve().parent.parent

# Hace falta para poder importar app desde acá
sys.path.insert(0, str(RAIZ))
from app import db                                  # noqa: E402
from app.size import cargar_config                  # noqa: E402

N_REGISTROS = 300       # cantidad de registros de ejemplo
DIAS = 14               # se reparten en los últimos 14 días
LOTES = [f"LOTE-{i:03d}" for i in range(1, 11)]   # 10 lotes
SEMILLA = 42            # con la misma semilla, siempre la misma data

# Distribución de defectos de ejemplo (aprox. 90% / 7% / 3%)
DISTRIBUCION = {"normal": 0.90, "rajado": 0.07, "roto_total": 0.03}

# Rangos típicos (mm) para la dimensión que la categoría no fije
TIPICO_LARGO = (40, 70)
TIPICO_ANCHO = (30, 45)

# Proporción típica del huevo: ancho ≈ 0.70 * largo
RELACION_ANCHO_LARGO = 0.70


def muestrear(azar, rango, tipico):
    """Número aleatorio dentro del rango [mín, máx] de config.yaml
    (o dentro del rango típico si la categoría no fija esa dimensión)."""
    minimo, maximo = rango if rango else tipico
    return round(azar.uniform(minimo, maximo), 1)


def main():
    config = cargar_config()
    clases = [c for c in config["clases_defecto"] if c in DISTRIBUCION]
    if not clases:
        raise SystemExit(
            f"Ninguna clase de config.yaml coincide con {list(DISTRIBUCION)}"
        )
    pesos = [DISTRIBUCION[c] for c in clases]

    # Categorías de tamaño de ejemplo (la empresa define las suyas)
    rangos = config["categorias_tamano"]
    if not rangos:
        raise SystemExit("config.yaml: falta la lista categorias_tamano.")

    azar = random.Random(SEMILLA)
    hoy = date.today()

    # 1) Armar los registros
    filas = []
    for _ in range(N_REGISTROS):
        dia = hoy - timedelta(days=azar.randint(0, DIAS - 1))
        momento = datetime.combine(
            dia,
            time(azar.randint(7, 18), azar.randint(0, 59), azar.randint(0, 59)),
        )
        defecto = azar.choices(clases, weights=pesos, k=1)[0]
        confianza = round(azar.uniform(0.55, 1.0), 3)
        # Elegir una categoría y medirla dentro de sus rangos
        cat = azar.choice(rangos)
        largo = muestrear(azar, cat.get("largo_mm"), TIPICO_LARGO)
        if "ancho_mm" in cat:
            ancho = muestrear(azar, cat["ancho_mm"], TIPICO_ANCHO)
        else:
            # Si la categoría no fija el ancho, se acerca al ancho
            # típico del huevo (ancho ≈ 0.70 * largo)
            ancho = round(
                largo * RELACION_ANCHO_LARGO + azar.uniform(-1.0, 1.0), 1,
            )
        filas.append((
            momento.strftime("%Y-%m-%d %H:%M:%S"),
            azar.choice(LOTES),
            defecto,
            confianza,
            largo,
            ancho,
            cat["categoria"],
        ))

    # 2) Guardar: primero los datos de ejemplo viejos, después los nuevos
    db.crear_tabla()
    conexion = sqlite3.connect(db.ruta_base_datos())
    try:
        conexion.execute("DELETE FROM clasificaciones WHERE es_demo = 1")
        conexion.executemany(
            """
            INSERT INTO clasificaciones
                (fecha_hora, lote, defecto, confianza, largo_mm,
                 ancho_mm, categoria_tamano, es_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            filas,
        )
        conexion.commit()
    finally:
        conexion.close()

    # 3) Resumen
    conteo = {}
    for fila in filas:
        conteo[fila[2]] = conteo.get(fila[2], 0) + 1
    print(f"Cargados {len(filas)} registros de DEMOSTRACIÓN (es_demo = 1)")
    print(f"  Fechas:  últimos {DIAS} días "
          f"(hasta {hoy - timedelta(days=DIAS - 1)} ... {hoy})")
    print(f"  Lotes:   {', '.join(LOTES)}")
    for clase in clases:
        print(f"  {clase}: {conteo.get(clase, 0)}")
    print("\nPara verlos: streamlit run app/main.py -> panel -> "
          "interruptor de demostración")


if __name__ == "__main__":
    main()
