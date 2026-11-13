"""
Paso 2b: calibra la escala de la cámara (píxeles por milímetro).

Mide la foto de una referencia de tamaño conocido (una moneda, una
regla, ...) con app/size.py y calcula:

    px_por_mm = lado_mayor_px / medida_mm

Lo guarda en model/scale.json. La cámara queda fija, así que la misma
escala sirve para todas las fotos.

La foto y la medida REAL de la referencia se configuran en
config.yaml (sección referencia).

Uso:  python scripts/calibrate.py
"""

import json
import sys
from pathlib import Path

# Raíz del proyecto: la carpeta que contiene scripts/
RAIZ = Path(__file__).resolve().parent.parent

# Hace falta para poder importar app.size desde acá
sys.path.insert(0, str(RAIZ))
from app.size import cargar_config, medir_huevo  # noqa: E402


def main():
    config = cargar_config()
    referencia = config.get("referencia") or {}
    archivo = referencia.get("archivo")
    medida_mm = referencia.get("medida_mm")

    if not archivo or not medida_mm:
        print("Falta la sección 'referencia' en config.yaml "
              "(archivo y medida_mm).")
        return

    ruta = RAIZ / archivo
    if not ruta.is_file():
        print(f"No existe la foto de la referencia: {archivo}")
        print("Sacá una foto de una moneda o regla con la cámara en la "
              "misma posición que para los huevos y poné la ruta en "
              "config.yaml -> referencia.archivo")
        return

    try:
        largo_px, _ = medir_huevo(ruta)
    except ValueError as error:
        print(f"No se pudo medir la referencia: {error}")
        print("Necesita un solo objeto sobre un fondo liso y con "
              "contraste.")
        return

    # Se usa el lado mayor del objeto: el diámetro de la moneda o el
    # largo de la regla
    px_por_mm = largo_px / float(medida_mm)

    modelo_dir = RAIZ / "model"
    modelo_dir.mkdir(parents=True, exist_ok=True)
    escala = {
        "px_por_mm": px_por_mm,
        "foto": archivo,
        "medida_mm": float(medida_mm),
        "lado_mayor_px": round(largo_px, 2),
    }
    with open(modelo_dir / "scale.json", "w", encoding="utf-8") as f:
        json.dump(escala, f, indent=2, ensure_ascii=False)

    # Resumen
    print("\n=== ESCALA GUARDADA ===")
    print(f"Archivo:    model/scale.json")
    print(f"Referencia: {archivo} ({medida_mm} mm reales)")
    print(f"Lado mayor: {largo_px:.1f} px")
    print(f"Escala:     {px_por_mm:.4f} px por mm")
    print("\nCon esta escala se miden todas las fotos (cámara fija).")


if __name__ == "__main__":
    main()
