"""
Página "Clasificar": subir foto o tomarla con la cámara, elegir el lote
y ver el resultado en una tarjeta con color según el estado.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import streamlit as st

# Raíz del proyecto: este archivo vive en app/pages/
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from app import classifier, db  # noqa: E402

# Umbral de confianza por debajo del cual el huevo va a revisión manual
CONFIANZA_MINIMA = 0.6


def leer_foto(archivo):
    """Convierte la foto de Streamlit (bytes) en una imagen BGR de OpenCV."""
    datos = np.frombuffer(archivo.getvalue(), np.uint8)
    return cv2.imdecode(datos, cv2.IMREAD_COLOR)


def procesar(lote, archivo):
    """Clasifica la foto, la guarda en SQLite y devuelve el resultado."""
    imagen = leer_foto(archivo)
    if imagen is None:
        raise ValueError("No se pudo leer la imagen.")
    resultado = classifier.clasificar(imagen)
    db.guardar_resultado(
        lote,
        resultado["defecto"],
        resultado["confianza"],
        resultado["largo_mm"],
        resultado["ancho_mm"],
        resultado["categoria_tamano"],
    )
    return resultado


def mostrar_tarjeta(resultado):
    """Muestra el resultado en una tarjeta grande con color de estado."""
    confianza = resultado["confianza"] * 100
    if resultado["largo_mm"] is not None:
        medidas = (
            f"Largo {resultado['largo_mm']:.1f} mm · "
            f"Ancho {resultado['ancho_mm']:.1f} mm · "
            f"Tamaño {resultado['categoria_tamano']}"
        )
    else:
        medidas = "Tamaño: no calibrado"

    st.markdown(
        f"""
        <div class="tarjeta tarjeta-{resultado['defecto']}">
            <div class="tarjeta-titulo">{resultado['defecto']}</div>
            <div class="barra-confianza">
                <div style="width: {confianza:.0f}%"></div>
            </div>
            <div class="tarjeta-meta">Confianza {confianza:.0f}% · {medidas}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if resultado["confianza"] < CONFIANZA_MINIMA:
        st.error("Revisar manualmente")


def mostrar_historial():
    """Últimas 10 clasificaciones guardadas en SQLite."""
    st.subheader("Últimas 10 clasificaciones")
    df = db.leer_dataframe(
        """
        SELECT fecha_hora, lote, defecto, confianza, largo_mm,
               ancho_mm, categoria_tamano
        FROM clasificaciones
        ORDER BY id DESC
        LIMIT 10
        """
    )
    if df.empty:
        st.caption("Todavía no hay clasificaciones.")
    else:
        st.dataframe(df, hide_index=True, width="stretch")


def run():
    st.title("Clasificar")
    st.caption("Una foto = un huevo: subí una foto o tomala con la cámara.")

    # Sin modelo entrenado no hay clasificación: se avisa y no se simula
    if not classifier.modelo_disponible():
        st.error(
            "Modelo no disponible: falta model/egg_classifier.keras. "
            "Entrená con: python scripts/train.py"
        )
        return

    # 1) El lote se ingresa ANTES de clasificar
    lote = st.text_input("Lote")

    # 2) La foto: archivo subido o cámara
    fuente = st.radio("Foto", ["Subir archivo", "Cámara"], horizontal=True)
    if fuente == "Subir archivo":
        archivo = st.file_uploader(
            "Elegí una foto del huevo", type=["jpg", "jpeg", "png"],
        )
    else:
        archivo = st.camera_input("Tomá una foto del huevo")

    # 3) Clasificar
    if st.button("Clasificar"):
        if not lote.strip():
            st.warning("Ingresá el lote antes de clasificar.")
        elif archivo is None:
            st.warning("Subí una foto o tomá una con la cámara.")
        else:
            try:
                st.session_state["resultado"] = procesar(
                    lote.strip(), archivo,
                )
            except ValueError as error:
                st.warning(str(error))

    # 4) Resultado (persiste entre interacciones)
    resultado = st.session_state.get("resultado")
    if resultado is not None:
        st.subheader("Resultado")
        mostrar_tarjeta(resultado)

    # 5) Historial
    mostrar_historial()


if __name__ == "__main__":
    run()
