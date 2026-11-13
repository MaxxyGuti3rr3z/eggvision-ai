"""
Página "Panel": KPIs, gráficos, alertas por lote y tabla filtrable
con reporte CSV.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Raíz del proyecto: este archivo vive en app/pages/
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from app import db                     # noqa: E402
from app.size import cargar_config     # noqa: E402

# Paleta coherente con los colores de estado de la app
COLORES = {
    "normal": "#16a34a",
    "rajado": "#d97706",
    "roto_total": "#dc2626",
}
# Tonos de azul para las categorías de tamaño (chico -> extra)
TONOS_TAMANO = ["#dbeafe", "#93c5fd", "#3b82f6", "#1d4ed8"]


def consultar(desde, hasta, lote, defecto, incluir_demo):
    """Trae de SQLite los registros que pasan los filtros."""
    sql = """
        SELECT fecha_hora, lote, defecto, confianza, largo_mm,
               ancho_mm, categoria_tamano, es_demo
        FROM clasificaciones
        WHERE 1 = 1
    """
    params = []
    if lote != "Todos":
        sql += " AND lote = ?"
        params.append(lote)
    if defecto != "Todos":
        sql += " AND defecto = ?"
        params.append(defecto)
    if desde is not None:
        sql += " AND date(fecha_hora) >= ?"
        params.append(desde.isoformat())
    if hasta is not None:
        sql += " AND date(fecha_hora) <= ?"
        params.append(hasta.isoformat())
    if not incluir_demo:
        sql += " AND es_demo = 0"
    sql += " ORDER BY fecha_hora DESC"
    return db.leer_dataframe(sql, params)


def calcular_kpis(df):
    """Devuelve las métricas de la fila de KPIs."""
    total = len(df)
    if total == 0:
        return None
    conteo = df["defecto"].value_counts()
    rajados = int(conteo.get("rajado", 0))
    rotos = int(conteo.get("roto_total", 0))
    defectuosos = rajados + rotos
    # Lote con más defectos (empates: se queda con el primero)
    por_lote = (
        df.assign(defectuoso=df["defecto"] != "normal")
        .groupby("lote")["defectuoso"]
        .sum()
    )
    lote_top = por_lote.idxmax() if por_lote.max() > 0 else "—"
    return {
        "total": total,
        "pct_defectuosos": defectuosos / total * 100,
        "rajados": rajados,
        "rotos": rotos,
        "lote_top": lote_top,
    }


def lotes_en_alerta(df, umbral):
    """Lotes cuyo % de defectos supera el umbral (config.yaml)."""
    alertas = []
    for lote, grupo in df.groupby("lote"):
        pct = (grupo["defecto"] != "normal").mean() * 100
        if pct > umbral:
            alertas.append((lote, pct))
    return sorted(alertas, key=lambda x: -x[1])


def grafico_tamanos(df, categorias):
    """Barras: cuántos huevos por categoría de tamaño."""
    conteo = (
        df["categoria_tamano"]
        .value_counts()
        .reindex(categorias)
        .fillna(0)
        .astype(int)
        .reset_index()
    )
    conteo.columns = ["Tamaño", "Cantidad"]
    tonos = dict(zip(categorias, TONOS_TAMANO[:len(categorias)]))
    fig = px.bar(
        conteo,
        x="Tamaño",
        y="Cantidad",
        color="Tamaño",
        color_discrete_map=tonos,
        text="Cantidad",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        showlegend=False,
        template="plotly_white",
        margin=dict(t=10, b=10, l=10, r=10),
        yaxis_title="Huevos",
    )
    return fig


def grafico_defectos_por_dia(df):
    """Línea: % de defectos por día."""
    por_dia = (
        df.assign(
            dia=df["fecha_hora"].str[:10],
            defectuoso=df["defecto"] != "normal",
        )
        .groupby("dia")
        .agg(total=("defecto", "size"), defectuosos=("defectuoso", "sum"))
        .reset_index()
    )
    por_dia["pct"] = por_dia["defectuosos"] / por_dia["total"] * 100
    fig = px.line(
        por_dia,
        x="dia",
        y="pct",
        markers=True,
        color_discrete_sequence=["#d97706"],
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(t=10, b=10, l=10, r=10),
        xaxis_title="Día",
        yaxis_title="% defectuosos",
    )
    return fig


def grafico_lotes(df):
    """Barras apiladas: composición de defectos por lote."""
    conteo = (
        df.groupby(["lote", "defecto"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    fig = px.bar(
        conteo,
        x="lote",
        y=[c for c in ["normal", "rajado", "roto_total"] if c in conteo.columns],
        color_discrete_map=COLORES,
        barmode="stack",
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(t=10, b=10, l=10, r=10),
        xaxis_title="Lote",
        yaxis_title="Huevos",
        legend_title="Defecto",
    )
    return fig


def run():
    st.title("Panel de control")
    config = cargar_config()
    clases = config["clases_defecto"]
    categorias = [c["categoria"] for c in config["categorias_tamano"]]
    umbral = config.get("alertas", {}).get("umbral_defectos_lote", 15)

    db.crear_tabla()

    # --- Filtros ---
    st.subheader("Filtros")
    df_lotes = db.leer_dataframe(
        "SELECT DISTINCT lote FROM clasificaciones "
        "WHERE lote IS NOT NULL ORDER BY lote"
    )
    lotes = df_lotes["lote"].tolist()

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    desde = col1.date_input("Desde", value=None)
    hasta = col2.date_input("Hasta", value=None)
    lote = col3.selectbox("Lote", ["Todos"] + lotes)
    defecto = col4.selectbox("Defecto", ["Todos"] + clases)
    incluir_demo = st.toggle(
        "Incluir datos de demostración (simulados)", value=False,
    )

    df = consultar(desde, hasta, lote, defecto, incluir_demo)

    # Etiqueta visible cuando los datos de demostración están activos
    if incluir_demo:
        st.warning("DATOS SIMULADOS — registros de demostración incluidos.")

    if df.empty:
        st.info("No hay registros con los filtros actuales.")
        return

    # --- KPIs ---
    st.subheader("Resumen")
    kpis = calcular_kpis(df)
    columnas = st.columns(5)
    columnas[0].metric("Total clasificados", kpis["total"])
    columnas[1].metric("Defectuosos", f"{kpis['pct_defectuosos']:.1f}%")
    columnas[2].metric("Rajados", kpis["rajados"])
    columnas[3].metric("Rotos totales", kpis["rotos"])
    columnas[4].metric("Lote con más defectos", kpis["lote_top"])

    # --- Alerta por umbral de defectos por lote ---
    alertas = lotes_en_alerta(df, umbral)
    if alertas:
        texto = "; ".join(f"{l} ({p:.0f}%)" for l, p in alertas)
        st.warning(
            f"Lotes por encima del umbral del {umbral}% de defectos: {texto}"
        )

    # --- Gráficos (Plotly) ---
    st.subheader("Por tamaño")
    st.plotly_chart(grafico_tamanos(df, categorias), width="stretch")

    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("% de defectos por día")
        st.plotly_chart(grafico_defectos_por_dia(df), width="stretch")
    with col_der:
        st.subheader("Comparación entre lotes")
        st.plotly_chart(grafico_lotes(df), width="stretch")

    # --- Tabla filtrable y reporte ---
    st.subheader("Registros")
    st.dataframe(df, hide_index=True, width="stretch")
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Descargar reporte (CSV)",
        data=csv,
        file_name="reporte_eggvision.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    run()
