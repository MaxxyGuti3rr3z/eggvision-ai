"""
Paso 2: tamaño del huevo por medición con OpenCV (sin IA).

Flujo:
  1. medir_huevo(): separa al huevo de un fondo liso, se queda con el
     contorno más grande y devuelve su largo (eje mayor) y ancho
     (eje menor) en píxeles, con minAreaRect.
  2. estimar_tamano(): divide los píxeles por la escala de la cámara
     (model/scale.json, que genera scripts/calibrate.py con una foto
     de referencia) y devuelve las medidas en milímetros junto con la
     categoría de config.yaml.
"""

import json
from pathlib import Path

import cv2
import numpy as np
import yaml

# Raíz del proyecto: app/ está al lado de config.yaml
RAIZ = Path(__file__).resolve().parent.parent

# Controles de la segmentación: el huevo debe ocupar entre el 1% y el 95%
# de la foto. Si queda fuera de ese rango, algo salió mal.
AREA_MINIMA = 0.01
AREA_MAXIMA = 0.95

# Diferencia mínima de brillo entre el huevo y el fondo para confiar
# en la medición (escala 0-255). Con menos contraste, Otsu agarra ruido.
CONTRASTE_MINIMO = 10


def cargar_config():
    """Lee config.yaml (categorías de tamaño, rutas, etc.)."""
    with open(RAIZ / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_imagen(imagen):
    """Acepta una ruta de archivo o una imagen ya cargada (BGR de OpenCV)."""
    if isinstance(imagen, (str, Path)):
        img = cv2.imread(str(imagen))
        if img is None:
            raise ValueError(f"No se pudo leer la imagen: {imagen}")
        return img
    return imagen


def _contorno_mas_grande(diferencia):
    """Umbraliza la diferencia y devuelve (contorno, área) del objeto mayor."""
    # Otsu elige el umbral solo, sobre una imagen donde el fondo queda en 0
    _, mascara = cv2.threshold(
        diferencia, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    # Limpiar ruido y cerrar huecos del cascarón
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel)

    contornos, _ = cv2.findContours(
        mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contornos:
        return None, 0.0
    contorno = max(contornos, key=cv2.contourArea)
    return contorno, float(cv2.contourArea(contorno))


def medir_huevo(imagen):
    """Segmenta el huevo sobre un fondo liso y lo mide.

    Devuelve (largo_px, ancho_px): los ejes del rectángulo mínimo que
    rodea al contorno más grande (minAreaRect). Lanza ValueError si no
    encuentra un objeto razonable.
    """
    img = cargar_imagen(imagen)
    alto, ancho = img.shape[:2]

    # 1) Pasar a escala de grises
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2) Estimar el color del fondo con los bordes de la foto
    #    (se asume un fondo liso que llega hasta el borde)
    borde = np.concatenate([gris[0, :], gris[-1, :], gris[:, 0], gris[:, -1]])
    fondo = float(np.median(borde))

    # 3) Distancia al fondo en las DOS direcciones: el huevo puede ser
    #    más claro o más oscuro que el fondo. Nos quedamos con la dirección
    #    que encuentre el objeto más grande. Así una sombra proyectada
    #    (más oscura) no se confunde con un huevo blanco sobre fondo claro.
    gris_f = gris.astype(np.float32)
    diferencia_clara = np.clip(gris_f - fondo, 0, 255).astype(np.uint8)
    diferencia_oscura = np.clip(fondo - gris_f, 0, 255).astype(np.uint8)
    contorno, area = _contorno_mas_grande(diferencia_clara)
    contorno_oscuro, area_oscuro = _contorno_mas_grande(diferencia_oscura)
    if area_oscuro > area:
        contorno, area = contorno_oscuro, area_oscuro

    # 4) Control: que haya un contorno de tamaño razonable
    if contorno is None or area < AREA_MINIMA * ancho * alto:
        raise ValueError(
            "No se encontró el huevo: revisá que la foto tenga un solo "
            "huevo sobre un fondo liso y con buen contraste."
        )
    if area > AREA_MAXIMA * ancho * alto:
        raise ValueError(
            "La segmentación tomó casi toda la foto: revisá la iluminación "
            "y que el fondo sea parejo."
        )

    # 5) Control de contraste: si el huevo no destaca del fondo,
    #    la medición no es confiable y conviene avisar en vez de mentir
    mascara_huevo = np.zeros(gris.shape, dtype=np.uint8)
    cv2.drawContours(mascara_huevo, [contorno], -1, 255, -1)
    brillo_dentro = float(np.median(gris[mascara_huevo > 0]))
    if abs(brillo_dentro - fondo) < CONTRASTE_MINIMO:
        raise ValueError(
            f"Contraste insuficiente: el huevo difiere del fondo solo en "
            f"{abs(brillo_dentro - fondo):.0f} niveles (mínimo "
            f"{CONTRASTE_MINIMO}). Necesitás más luz o un fondo que "
            f"destaque más del cascarón."
        )

    # 6) Ejes del rectángulo mínimo que rodea al huevo:
    #    eje mayor = largo del huevo, eje menor = ancho
    (_, _), (ancho_r, largo_r), _ = cv2.minAreaRect(contorno)
    largo_px = float(max(ancho_r, largo_r))
    ancho_px = float(min(ancho_r, largo_r))

    return largo_px, ancho_px


def cargar_escala():
    """Devuelve px_por_mm (model/scale.json, generado por calibrate.py)."""
    ruta = RAIZ / "model" / "scale.json"
    if not ruta.is_file():
        raise ValueError(
            "Falta model/scale.json. Corré: python scripts/calibrate.py"
        )
    with open(ruta, encoding="utf-8") as f:
        return float(json.load(f)["px_por_mm"])


def categoria_para_dimensiones(largo_mm, ancho_mm):
    """Devuelve la categoría de config.yaml para unas medidas en mm.

    Cada categoría trae un rango por largo, por ancho, o por ambos
    (si trae los dos, se exigen los dos). Rango [mínimo, máximo).
    """
    for cat in cargar_config()["categorias_tamano"]:
        # Sin rangos configurados la categoría no puede evaluar nada
        if "largo_mm" not in cat and "ancho_mm" not in cat:
            continue
        cumple = True
        if "largo_mm" in cat:
            minimo, maximo = cat["largo_mm"]
            cumple = cumple and minimo <= largo_mm < maximo
        if "ancho_mm" in cat:
            minimo, maximo = cat["ancho_mm"]
            cumple = cumple and minimo <= ancho_mm < maximo
        if cumple:
            return cat["categoria"]
    raise ValueError(
        f"Las medidas ({largo_mm:.1f} x {ancho_mm:.1f} mm) no caen en "
        f"ninguna categoría de config.yaml (categorias_tamano)."
    )


def estimar_tamano(imagen):
    """Devuelve (largo_mm, ancho_mm, categoria) para una foto de huevo."""
    # Primero la escala: sin model/scale.json no hay calibración y no
    # tiene sentido medir (lanza ValueError y la app muestra "no calibrado")
    px_por_mm = cargar_escala()

    largo_px, ancho_px = medir_huevo(imagen)
    largo_mm = largo_px / px_por_mm
    ancho_mm = ancho_px / px_por_mm

    return (
        round(largo_mm, 1),
        round(ancho_mm, 1),
        categoria_para_dimensiones(largo_mm, ancho_mm),
    )
