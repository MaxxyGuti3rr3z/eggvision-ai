"""
EggVision AI: entry point de la app.

Carga el estilo global (CSS) y arma la navegación de 3 páginas con
st.navigation. Cada página vive en app/pages/ y exporta un run().

Uso:  streamlit run app/main.py
"""

import sys
from pathlib import Path

import streamlit as st

# Raíz del proyecto: app/ está al lado de config.yaml
RAIZ = Path(__file__).resolve().parent.parent

# Hace falta para poder importar app desde acá
sys.path.insert(0, str(RAIZ))

from app import db  # noqa: E402

# --- Estilo propio (CSS) ---
# Tarjetas con bordes redondeados y sombra suave, tipografía limpia
# y espaciado consistente. Los colores de estado:
#   verde = normal, ámbar = rajado, rojo = roto_total.
CSS = """
<style>
/* Tipografía general */
.stApp {
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
}

/* Encabezado con el nombre del proyecto */
.encabezado {
    background: #0f172a;
    color: #ffffff;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.25);
}
.encabezado span {
    color: #93c5fd;
    font-weight: 400;
    font-size: 0.95rem;
    margin-left: 0.75rem;
}

/* Tarjeta de resultado */
.tarjeta {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.5rem 2rem;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.10);
    margin: 0.5rem 0 1rem 0;
}
.tarjeta-normal    { border-left: 8px solid #16a34a; }
.tarjeta-rajado    { border-left: 8px solid #d97706; }
.tarjeta-roto_total{ border-left: 8px solid #dc2626; }
.tarjeta-titulo {
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0 0 0.75rem 0;
}
.tarjeta-normal     .tarjeta-titulo { color: #16a34a; }
.tarjeta-rajado     .tarjeta-titulo { color: #d97706; }
.tarjeta-roto_total .tarjeta-titulo { color: #dc2626; }

/* Barra de confianza */
.barra-confianza {
    background: #e2e8f0;
    border-radius: 999px;
    height: 14px;
    overflow: hidden;
}
.barra-confianza > div {
    height: 100%;
    border-radius: 999px;
}
.tarjeta-meta {
    color: #475569;
    font-size: 1rem;
    margin-top: 0.75rem;
}

/* KPIs del panel como tarjetas */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}

/* Espaciado consistente entre secciones */
section[data-testid="stMainBlockContainer"] {
    padding-top: 2rem;
}
</style>
"""

st.set_page_config(
    page_title="EggVision AI",
    page_icon=":material/egg:",
    layout="wide",
)

st.markdown(CSS, unsafe_allow_html=True)

# Encabezado visible en todas las páginas
st.markdown(
    '<div class="encabezado">EggVision AI'
    "<span>visión artificial para clasificación de huevos</span></div>",
    unsafe_allow_html=True,
)

# Base lista para la app y el panel
db.crear_tabla()

# --- Navegación de 3 páginas ---
paginas = [
    st.Page(
        "pages/clasificar.py",
        title="Clasificar",
        icon=":material/camera:",
        default=True,
    ),
    st.Page(
        "pages/panel.py",
        title="Panel",
        icon=":material/dashboard:",
    ),
    st.Page(
        "pages/acerca_de.py",
        title="Acerca de",
        icon=":material/info:",
    ),
]

st.navigation(paginas).run()
