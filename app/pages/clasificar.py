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
        st.markdown(
            '<div class="aviso-revision">Revisar manualmente — confianza '
            f"{confianza:.0f}% (mínimo {CONFIANZA_MINIMA:.0%})</div>",
            unsafe_allow_html=True,
        )


def mostrar_tarjeta_vacia():
    """Estado inicial de la tarjeta: huevo en SVG y texto de espera."""
    st.markdown(
        """
        <div class="tarjeta tarjeta-vacia">
            <svg class="huevo-svg" width="88" height="112" viewBox="0 0 88 112"
                 fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M44 6C61 6 78 34 78 62C78 88 63 106 44 106
                         C25 106 10 88 10 62C10 34 27 6 44 6Z"
                      fill="#EDE8DA" stroke="rgba(27,35,32,0.45)"
                      stroke-width="3"/>
                <path d="M28 44C30 34 36 26 44 22"
                      stroke="rgba(255,255,255,0.8)" stroke-width="6"
                      stroke-linecap="round"/>
            </svg>
            <div class="tarjeta-vacia-texto">Acá aparece el resultado</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    # Formulario a la izquierda / tarjeta de resultado a la derecha
    col_form, col_result = st.columns([1, 1], gap="large")

    with col_form:
        # 1) El lote se ingresa ANTES de clasificar
        lote = st.text_input("Lote", placeholder="Ej.: LOTE-12")

        # 2) La foto: archivo subido o cámara
        fuente = st.radio("Foto", ["Subir archivo", "Cámara"], horizontal=True)
        if fuente == "Subir archivo":
            archivo = st.file_uploader(
                "Elegí una foto del huevo", type=["jpg", "jpeg", "png"],
            )
        else:
            archivo = st.camera_input("Tomá una foto del huevo")

        # 3) Clasificar
        if st.button("Clasificar", type="primary"):
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

    # 4) Resultado a la derecha (vacío al inicio, se llena al clasificar)
    with col_result:
        resultado = st.session_state.get("resultado")
        if resultado is None:
            mostrar_tarjeta_vacia()
        else:
            mostrar_tarjeta(resultado)

    # 5) Historial
    mostrar_historial()


if __name__ == "__main__":
    run()
