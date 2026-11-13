"""
Paso 1c: clasifica una foto de huevo con el modelo entrenado.

Uso:  python scripts/predict.py data/raw/huevo07_rajado_2.jpg
"""

import json
import sys
from pathlib import Path

import yaml

# Raíz del proyecto: la carpeta que contiene scripts/
RAIZ = Path(__file__).resolve().parent.parent


def main():
    # La foto viene como argumento del comando
    if len(sys.argv) < 2:
        print("Uso: python scripts/predict.py <foto.jpg>")
        return
    ruta = Path(sys.argv[1])
    if not ruta.is_file():
        print(f"No existe el archivo: {ruta}")
        return

    # Leer configuración y clases entrenadas
    with open(RAIZ / "config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    ancho, alto = config["ancho_imagen"], config["alto_imagen"]

    modelo_dir = RAIZ / config["rutas"]["modelo"]
    ruta_modelo = modelo_dir / "egg_classifier.keras"
    if not ruta_modelo.is_file():
        print(f"No existe el modelo {ruta_modelo.relative_to(RAIZ)}.")
        print("Primero corré: python scripts/train.py")
        return
    with open(modelo_dir / "clases.json", encoding="utf-8") as f:
        clases = json.load(f)

    # Imports pesados después de validar todo, para que los mensajes
    # de error salgan al instante (sin esperar a cargar TensorFlow)
    import cv2
    import numpy as np
    import tensorflow as tf

    # Cargar la foto con OpenCV (viene en BGR, la pasamos a RGB)
    imagen = cv2.imread(str(ruta))
    if imagen is None:
        print(f"No se pudo leer la imagen: {ruta}")
        return
    imagen = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
    imagen = cv2.resize(imagen, (ancho, alto))
    imagen = np.expand_dims(imagen.astype("float32"), axis=0)

    # Predecir: el modelo ya incluye el escalado a [-1, 1]
    modelo = tf.keras.models.load_model(ruta_modelo)
    probabilidades = modelo.predict(imagen, verbose=0)[0]

    # La clase con mayor probabilidad es la predicción
    indice = int(np.argmax(probabilidades))

    print(f"Archivo:   {ruta.name}")
    print(f"Clase:     {clases[indice]}")
    print(f"Confianza: {probabilidades[indice] * 100:.1f}%")


if __name__ == "__main__":
    main()
