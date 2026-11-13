"""
Paso 2c: valida la medición contra medidas hechas a mano.

Lee data/measurements.csv (columnas: archivo, largo_mm, ancho_mm con
las medidas manuales de cada foto), mide las mismas fotos con
app/size.py + la escala de model/scale.json y muestra el error medio
en mm por largo y por ancho.

Uso:  python scripts/validate_size.py
"""

import sys
from pathlib import Path

import pandas as pd

# Raíz del proyecto: la carpeta que contiene scripts/
RAIZ = Path(__file__).resolve().parent.parent

# Hace falta para poder importar app.size desde acá
sys.path.insert(0, str(RAIZ))
from app.size import estimar_tamano  # noqa: E402


def buscar_foto(nombre):
    """Busca la foto en la raíz del proyecto o en data/raw/."""
    for candidata in (RAIZ / nombre, RAIZ / "data" / "raw" / nombre):
        if candidata.is_file():
            return candidata
    return None


def main():
    ruta_csv = RAIZ / "data" / "measurements.csv"
    if not ruta_csv.is_file():
        print(f"No existe {ruta_csv}.")
        print("Crealo con las columnas: archivo,largo_mm,ancho_mm")
        print("Ejemplo: huevo01_normal_1.jpg,52.3,38.1")
        return

    df = pd.read_csv(ruta_csv)
    if not {"archivo", "largo_mm", "ancho_mm"}.issubset(df.columns):
        print(f"Faltan columnas. Se esperaban 'archivo', 'largo_mm' y "
              f"'ancho_mm', y el CSV tiene: {list(df.columns)}")
        return

    errores_largo, errores_ancho, fallos = [], [], []
    for _, fila in df.iterrows():
        nombre = str(fila["archivo"]).strip()
        ruta = buscar_foto(nombre)
        if ruta is None:
            fallos.append(f"{nombre} (no se encontró el archivo)")
            continue
        try:
            largo_mm, ancho_mm, _ = estimar_tamano(ruta)
        except ValueError as error:
            fallos.append(f"{nombre} ({error})")
            continue
        errores_largo.append(abs(largo_mm - float(fila["largo_mm"])))
        errores_ancho.append(abs(ancho_mm - float(fila["ancho_mm"])))

    print(f"Fotos comparadas: {len(errores_largo)} de {len(df)}")
    for fallo in fallos:
        print(f"  OJO, no se pudo medir: {fallo}")

    if not errores_largo:
        print("No se pudo comparar ninguna foto.")
        return

    # Resumen: error medio absoluto (promedio de |programa - mano|)
    print("\n=== ERROR RESPECTO A LAS MEDIDAS A MANO ===")
    print(f"Error medio del largo: "
          f"{sum(errores_largo) / len(errores_largo):.2f} mm")
    print(f"Error medio del ancho: "
          f"{sum(errores_ancho) / len(errores_ancho):.2f} mm")


if __name__ == "__main__":
    main()
