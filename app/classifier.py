"""
Clasificador de huevos: la única puerta de entrada a la "inteligencia".

Usa el modelo REAL entrenado (model/egg_classifier.keras + clases.json).
Si el modelo no existe, clasificar() lanza ValueError y la app muestra
"modelo no disponible": nunca devuelve resultados simulados.
"""

import json
from pathlib import Path

import cv2
import numpy as np

from app.size import estimar_tamano

# Raíz del proyecto: app/ está al lado de model/
RAIZ = Path(__file__).resolve().parent.parent
RUTA_MODELO = RAIZ / "model" / "egg_classifier.keras"
RUTA_CLASES = RAIZ / "model" / "clases.json"

# El modelo se carga una sola vez y queda en memoria (la app lo reutiliza
# entre reruns de Streamlit)
_MODELO = None
_CLASES = None


def modelo_disponible():
    """¿Están el modelo y el orden de clases entrenados?"""
    return RUTA_MODELO.is_file() and RUTA_CLASES.is_file()


def _cargar_modelo():
    """Carga el modelo y las clases (una sola vez)."""
    global _MODELO, _CLASES
    if _MODELO is None:
        # tensorflow pesa: se importa solo cuando hace falta
        from tensorflow import keras

        _MODELO = keras.models.load_model(RUTA_MODELO)
        with open(RUTA_CLASES, encoding="utf-8") as f:
            _CLASES = json.load(f)
    return _MODELO, _CLASES


def clasificar(imagen):
    """Clasifica una foto de huevo (BGR de OpenCV).

    Devuelve un dict con:
      defecto, confianza, largo_mm, ancho_mm, categoria_tamano

    Lanza ValueError si el modelo no está entrenado.
    """
    if not modelo_disponible():
        raise ValueError(
            "Modelo no disponible: falta model/egg_classifier.keras. "
            "Entrená con: python scripts/train.py"
        )

    modelo, clases = _cargar_modelo()

    # Preprocesamiento: BGR (OpenCV) -> RGB, 224x224, batch de 1.
    # El modelo ya trae su Rescaling adentro: entra RGB en 0-255.
    rgb = imagen[:, :, ::-1]
    redimida = cv2.resize(rgb, (224, 224))
    entrada = np.expand_dims(redimida.astype("float32"), axis=0)

    probabilidades = modelo.predict(entrada, verbose=0)[0]
    indice = int(np.argmax(probabilidades))
    defecto = clases[indice]
    confianza = float(probabilidades[indice])

    # Medidas del huevo en la foto: medición con OpenCV (Paso 2, sin IA).
    # Sin model/scale.json no hay calibración → quedan en None y la app
    # muestra "no calibrado". Si la segmentación falla, idem.
    try:
        largo_mm, ancho_mm, categoria = estimar_tamano(imagen)
    except ValueError:
        largo_mm, ancho_mm, categoria = None, None, None

    return {
        "defecto": defecto,
        "confianza": round(confianza, 3),
        "largo_mm": largo_mm,
        "ancho_mm": ancho_mm,
        "categoria_tamano": categoria,
    }
