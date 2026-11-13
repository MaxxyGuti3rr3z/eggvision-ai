"""
Página "Acerca de": problema, cómo funciona, datos usados y limitaciones.
"""

import streamlit as st


def run():
    st.title("Acerca de")

    st.subheader("Problema")
    st.markdown(
        """
        En la planta los huevos se clasifican a mano, uno por uno: primero
        el defecto (`normal` / `rajado` / `roto_total`) y después el tamaño.
        La tarea es lenta, cansadora y subjetiva, y no queda registro de lo
        clasificado: no se puede auditar un lote ni responder "¿cuántos
        rajados salieron el martes?".
        """
    )

    st.subheader("Cómo funciona")
    st.markdown(
        """
        1. **Clasifica el defecto** con una red neuronal (MobileNetV2 +
           transfer learning) entrenada con las fotos del dataset.
        2. **Mide el tamaño sin IA**: segmenta el huevo con OpenCV y calcula
           su largo y ancho. Sin calibración de la cámara, muestra
           "no calibrado" en lugar de milímetros.
        3. **Guarda cada resultado** en SQLite (fecha, lote, defecto,
           confianza, largo, ancho, tamaño) y lo muestra en el panel con
           filtros, gráficos y reporte CSV descargable.
        """
    )

    st.subheader("Datos usados")
    st.markdown(
        """
        Fotos reales en `data/raw/`: `normal/` (fotos propias),
        `rajado/` y `roto_total/` (imágenes de internet). Reparto
        estratificado 75/25 en train/test.

        Los registros del panel pueden ser de demostración: aparecen
        marcados como **DATOS SIMULADOS**.

        *Pendiente: ampliar el dataset con más fotos propias y de la
        planta (enlace y licencia de las fotos de internet).*
        """
    )

    st.subheader("Limitaciones")
    st.markdown(
        """
        - Dataset chico: con pocas fotos por clase el modelo puede
          fallar con fotos nuevas.
        - Las fotos de `normal/` y las de defecto vienen de fuentes
          distintas: el modelo podría distinguir el estilo de la foto
          y no el defecto.
        - Una foto = un huevo: no detecta varios huevos en la misma imagen.
        - Las medidas en mm dependen de la calibración de la cámara
          (hoy sin calibrar).
        - Un solo defecto por foto: no cubre manchas, suciedad, doble yema.
        """
    )


if __name__ == "__main__":
    run()
