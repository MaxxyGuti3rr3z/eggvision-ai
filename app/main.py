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
# Paleta de la landing: fondo gris pulpa, tarjetas cáscara, texto
# oscuro, acento verde musgo y yema. Estados:
#   musgo = normal, yema = rajado, rojo = roto_total.
# Tipografía: Bricolage Grotesque (títulos) y Newsreader (texto).
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..700&family=Newsreader:opsz,wght@6..72,400..600&display=swap');

/* --- Paleta --- */
.stApp {
    font-family: "Newsreader", Georgia, serif;
    font-size: 17px;
    color: #1B2320;
    background-color: #D3D7CE;
}
h1, h2, h3, h4, h5, h6,
.encabezado, .kpi-valor, .tarjeta-titulo, .alerta-lote-nombre,
.alerta-lote-pct, .aviso-revision {
    font-family: "Bricolage Grotesque", "Segoe UI", system-ui, sans-serif;
}

/* Encabezado con el nombre y la línea de contexto */
.encabezado {
    background: #2F5D50;
    color: #F6F2E7;
    padding: 1.1rem 1.5rem;
    border-radius: 14px;
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    margin-bottom: 1.5rem;
    border-bottom: 5px solid #EFAE16;
    box-shadow: 0 6px 18px rgba(27, 35, 32, 0.20);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}
.encabezado-texto {
    min-width: 0;
}
.encabezado span {
    display: block;
    color: #EFAE16;
    font-family: "Newsreader", Georgia, serif;
    font-weight: 400;
    font-size: 1rem;
    margin-top: 0.3rem;
    letter-spacing: 0;
}
.encabezado-ilustracion {
    flex-shrink: 0;
}

/* Cargador de archivos: textos en inglés -> español */
[data-testid="stFileUploaderDropzoneInstructions"] {
    font-size: 0;
}
[data-testid="stFileUploaderDropzoneInstructions"]::after {
    content: "JPG o PNG, hasta 200 MB";
    font-size: 0.95rem;
    color: rgba(27, 35, 32, 0.75);
}
[data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"] {
    font-size: 0;
}
[data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"]::after {
    content: "Subir foto";
    font-size: 1rem;
    font-weight: 600;
}

/* Botón "Clasificar": verde musgo, texto claro, grande, redondeado */
button[data-testid="stBaseButton-primary"] {
    background-color: #2F5D50 !important;
    color: #F6F2E7 !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.7rem 1.75rem !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
    width: 100%;
}
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #24493F !important;
    border: none !important;
}
button[data-testid="stBaseButton-primary"]:active {
    background-color: #1E3D35 !important;
    border: none !important;
}

/* Tarjeta de resultado (Clasificar) */
.tarjeta {
    background: #F6F2E7;
    border: 1px solid rgba(27, 35, 32, 0.10);
    border-radius: 16px;
    padding: 2rem 2.25rem;
    box-shadow: 0 6px 18px rgba(27, 35, 32, 0.10);
    margin: 0.75rem 0 1.25rem 0;
}
.tarjeta-normal    { border-left: 10px solid #2F5D50; }
.tarjeta-rajado    { border-left: 10px solid #EFAE16; }
.tarjeta-roto_total{ border-left: 10px solid #B5412F; }
.tarjeta-titulo {
    display: inline-block;
    font-size: clamp(1.7rem, 4vw, 2.4rem);
    font-weight: 700;
    line-height: 1.2;
    padding: 0.4rem 1.3rem;
    border-radius: 999px;
    margin: 0 0 1.2rem 0;
}
.tarjeta-normal     .tarjeta-titulo { background: #2F5D50; color: #F6F2E7; }
.tarjeta-rajado     .tarjeta-titulo { background: #EFAE16; color: #1B2320; }
.tarjeta-roto_total .tarjeta-titulo { background: #B5412F; color: #F6F2E7; }

/* Barra de confianza redondeada, coloreada por estado */
.barra-confianza {
    background: rgba(27, 35, 32, 0.12);
    border-radius: 999px;
    height: 18px;
    overflow: hidden;
}
.barra-confianza > div {
    height: 100%;
    border-radius: 999px;
}
.tarjeta-normal     .barra-confianza > div { background: #2F5D50; }
.tarjeta-rajado     .barra-confianza > div { background: #EFAE16; }
.tarjeta-roto_total .barra-confianza > div { background: #B5412F; }
.tarjeta-meta {
    color: rgba(27, 35, 32, 0.78);
    font-size: 1.1rem;
    margin-top: 0.9rem;
}

/* Tarjeta de resultado vacía (estado inicial de Clasificar) */
.tarjeta-vacia {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    min-height: 300px;
    border: 2px dashed rgba(27, 35, 32, 0.30);
    background: rgba(246, 242, 231, 0.55);
    box-shadow: none;
}
.tarjeta-vacia-texto {
    color: rgba(27, 35, 32, 0.60);
    font-size: 1.15rem;
    margin-top: 1rem;
}
.huevo-svg {
    opacity: 0.85;
}

/* Aviso de revisión manual (confianza baja) */
.aviso-revision {
    background: #B5412F;
    color: #F6F2E7;
    border-radius: 12px;
    padding: 0.9rem 1.3rem;
    font-size: 1.15rem;
    font-weight: 700;
    margin: 0 0 1.25rem 0;
    box-shadow: 0 4px 14px rgba(181, 65, 47, 0.30);
}

/* Banner de datos simulados (bien visible) */
.banner-demo {
    background: #EFAE16;
    color: #1B2320;
    border-left: 8px solid #B5412F;
    border-radius: 12px;
    padding: 0.9rem 1.3rem;
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    margin: 0.25rem 0 1.25rem 0;
    box-shadow: 0 4px 14px rgba(27, 35, 32, 0.12);
}
.chip-demo {
    display: inline-block;
    background: #EFAE16;
    color: #1B2320;
    border-radius: 999px;
    padding: 0.25rem 0.85rem;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    margin-top: 0.4rem;
}

/* KPIs como tarjetas grandes */
.kpis {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin: 0.5rem 0 1.25rem 0;
}
.kpi {
    flex: 1 1 190px;
    background: #F6F2E7;
    border: 1px solid rgba(27, 35, 32, 0.10);
    border-radius: 14px;
    padding: 1.1rem 1.25rem 1rem 1.25rem;
    box-shadow: 0 4px 14px rgba(27, 35, 32, 0.08);
}
.kpi-valor {
    font-size: clamp(1.8rem, 3vw, 2.6rem);
    font-weight: 700;
    line-height: 1.1;
    color: #1B2320;
}
.kpi-etiqueta {
    font-size: 0.95rem;
    color: rgba(27, 35, 32, 0.75);
    margin-top: 0.25rem;
}
.kpi-barra {
    height: 8px;
    border-radius: 999px;
    background: rgba(27, 35, 32, 0.10);
    margin-top: 0.85rem;
    overflow: hidden;
}
.kpi-barra span {
    display: block;
    height: 100%;
    border-radius: 999px;
}

/* Alertas por lote: tarjetas yema con acento rojo */
.alertas {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin: 0.25rem 0 1.5rem 0;
}
.alerta-lote {
    flex: 1 1 250px;
    background: #EFAE16;
    color: #1B2320;
    border-left: 8px solid #B5412F;
    border-radius: 14px;
    padding: 1rem 1.3rem;
    box-shadow: 0 6px 18px rgba(27, 35, 32, 0.14);
}
.alerta-lote-nombre { font-size: 1.25rem; font-weight: 700; }
.alerta-lote-pct { font-size: 2rem; font-weight: 700; line-height: 1.2; }
.alerta-lote-nota { font-size: 0.95rem; color: rgba(27, 35, 32, 0.85); }

/* Vista de maple: grilla de huevos con CSS */
.mapa {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.75rem;
    background: #F6F2E7;
    border: 1px solid rgba(27, 35, 32, 0.10);
    border-radius: 14px;
    padding: 1.25rem;
    box-shadow: 0 4px 14px rgba(27, 35, 32, 0.08);
    margin-bottom: 1.5rem;
}
.mapa-celda {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.45rem;
    background: rgba(27, 35, 32, 0.04);
    border-radius: 10px;
    padding: 0.7rem 0.35rem 0.55rem 0.35rem;
}
.huevo {
    width: 42px;
    height: 54px;
    border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
    box-shadow: inset -4px -6px 0 rgba(0, 0, 0, 0.14);
}
.mapa-label {
    font-size: 0.78rem;
    color: #1B2320;
    text-align: center;
}

/* Espaciado consistente entre secciones */
section[data-testid="stMainBlockContainer"] {
    padding-top: 2rem;
}

/* Móvil */
@media (max-width: 700px) {
    .stApp { font-size: 16px; }
    .encabezado { font-size: 1.25rem; padding: 0.9rem 1.1rem; }
    .encabezado-ilustracion { display: none; }
    .tarjeta { padding: 1.4rem 1.2rem; }
    .tarjeta-vacia { min-height: 220px; }
    .mapa { grid-template-columns: repeat(3, 1fr); gap: 0.6rem; padding: 0.9rem; }
    .kpi { flex: 1 1 150px; }
    .alerta-lote-pct { font-size: 1.6rem; }
}
@media (max-width: 420px) {
    .mapa { grid-template-columns: repeat(2, 1fr); }
}
</style>
"""

st.set_page_config(
    page_title="EggVision AI",
    page_icon=":material/egg:",
    layout="wide",
)

st.markdown(CSS, unsafe_allow_html=True)

# Encabezado visible en todas las páginas (con mini maple de huevos)
st.markdown(
    '<div class="encabezado">'
    '<div class="encabezado-texto">EggVision AI'
    "<span>visión artificial para clasificación de huevos</span></div>"
    '<svg class="encabezado-ilustracion" width="150" height="72" '
    'viewBox="0 0 150 72" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    # Bandeja del maple
    '<path d="M8 30 H142 L134 64 H16 Z" fill="#F6F2E7" fill-opacity="0.35" '
    'stroke="#F6F2E7" stroke-opacity="0.8" stroke-width="2"/>'
    # Huevos de la bandeja
    '<ellipse cx="34" cy="30" rx="16" ry="22" fill="#F6F2E7" fill-opacity="0.95"/>'
    '<ellipse cx="75" cy="27" rx="16" ry="22" fill="#EFAE16" fill-opacity="0.9"/>'
    '<ellipse cx="116" cy="30" rx="16" ry="22" fill="#F6F2E7" fill-opacity="0.95"/>'
    # División del maple
    '<path d="M8 30 H142" stroke="#F6F2E7" stroke-opacity="0.8" stroke-width="2"/>'
    "</svg>"
    "</div>",
    unsafe_allow_html=True,
)

# Base lista para la app y el panel. Si la BD no existía (clon limpio /
# deploy nuevo), además se cargan los 300 registros de demo (es_demo = 1).
_db_nueva = not db.ruta_base_datos().exists()
db.crear_tabla()
if _db_nueva:
    from scripts.seed_demo import main as _seed_demo

    _seed_demo()

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
