"""
Página "Panel": KPIs, gráficos, alertas por lote, vista de maple
y tabla filtrable con reporte CSV.
"""

import html
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

# Raíz del proyecto: este archivo vive en app/pages/
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from app import db                     # noqa: E402
from app.size import cargar_config     # noqa: E402

# Paleta de la landing, igual que en el CSS global:
# musgo = normal, yema = rajado, rojo = roto_total.
COLORES = {
    "normal": "#2F5D50",
    "rajado": "#EFAE16",
    "roto_total": "#B5412F",
}
# Tonos musgo (claro -> oscuro) para las categorías de tamaño
TONOS_TAMANO = ["#C7D6CD", "#93B7A6", "#5B8F7B", "#2F5D50"]


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


def _kpi(valor, etiqueta, pct_barra, color_barra, estilo_valor=""):
    """Tarjeta de KPI: número grande, etiqueta chica y barra de color."""
    ancho = max(0.0, min(100.0, float(pct_barra)))
    return (
        '<div class="kpi">'
        f'<div class="kpi-valor"{estilo_valor}>{valor}</div>'
        f'<div class="kpi-etiqueta">{etiqueta}</div>'
        '<div class="kpi-barra">'
        f'<span style="width:{ancho:.0f}%;background:{color_barra}"></span>'
        "</div>"
        "</div>"
    )


def _estilo(fig):
    """Fondo transparente, grilla ligera y tipografía de la paleta."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Newsreader, Georgia, serif", size=15, color="#1B2320"),
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=14)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(27,35,32,0.12)", zeroline=False)
    return fig


def grafico_proporcion(df):
    """Donut: proporción normal / rajado / roto_total con total al centro."""
    conteo = df["defecto"].value_counts()
    fig = px.pie(
        names=conteo.index,
        values=conteo.values,
        color=conteo.index,
        color_discrete_map=COLORES,
        hole=0.62,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color="#F6F2E7", width=2)),
    )
    for trazo in fig.data:
        claro = trazo.name in ("normal", "roto_total")
        trazo.textfont = dict(
            family="Bricolage Grotesque, sans-serif",
            size=15,
            color="#F6F2E7" if claro else "#1B2320",
        )
    fig.add_annotation(
        text=f"<b>{len(df)}</b><br>huevos",
        x=0.5, y=0.5, showarrow=False,
        font=dict(family="Bricolage Grotesque, sans-serif", size=22, color="#1B2320"),
    )
    return fig


def grafico_tamanos(df, categorias):
    """Barras: cuántos huevos por categoría de tamaño (etiqueta directa)."""
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
    fig.update_traces(
        textposition="outside",
        textfont=dict(family="Bricolage Grotesque, sans-serif", size=15, color="#1B2320"),
    )
    fig.update_layout(showlegend=False, yaxis_title="Huevos")
    return fig


def grafico_defectos_por_dia(df):
    """Línea: % de defectos por día (etiqueta directa si hay pocos días)."""
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
    mostrar_texto = len(por_dia) <= 10
    fig = px.line(
        por_dia,
        x="dia",
        y="pct",
        color_discrete_sequence=["#B5412F"],
    )
    fig.update_traces(
        mode="lines+markers" + ("+text" if mostrar_texto else ""),
        text=[f"{v:.0f}%" for v in por_dia["pct"]] if mostrar_texto else None,
        textposition="top center",
        textfont=dict(family="Bricolage Grotesque, sans-serif", color="#B5412F"),
        line=dict(width=3),
        marker=dict(size=8),
    )
    fig.update_layout(xaxis_title="Día", yaxis_title="% defectuosos")
    fig.update_yaxes(rangemode="tozero")
    return fig


def grafico_lotes(df):
    """Barras apiladas: composición de defectos por lote (etiqueta directa)."""
    conteo = (
        df.groupby(["lote", "defecto"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    orden = [c for c in ["normal", "rajado", "roto_total"] if c in conteo.columns]
    largo = conteo.melt(
        id_vars="lote",
        value_vars=orden,
        var_name="defecto",
        value_name="cantidad",
    )
    # Etiqueta vacía en los ceros para no ensuciar la barra
    largo["etiqueta"] = largo["cantidad"].map(
        lambda v: str(int(v)) if v > 0 else ""
    )
    fig = px.bar(
        largo,
        x="lote",
        y="cantidad",
        color="defecto",
        color_discrete_map=COLORES,
        barmode="stack",
        text="etiqueta",
    )
    fig.update_traces(textposition="inside")
    for trazo in fig.data:
        claro = trazo.name in ("normal", "roto_total")
        trazo.textfont = dict(
            family="Bricolage Grotesque, sans-serif",
            size=13,
            color="#F6F2E7" if claro else "#1B2320",
        )
    fig.update_layout(
        showlegend=False,
        xaxis_title="Lote",
        yaxis_title="Huevos",
    )
    fig.update_xaxes(tickangle=-45)
    return fig


def mapa_html(df, incluir_demo):
    """Grilla de hasta 30 huevos CSS coloreados por estado (últimos registros)."""
    titulo = (
        '<div style="display:flex;align-items:center;gap:0.9rem;'
        'flex-wrap:wrap;margin:0.5rem 0 0.6rem 0">'
        '<h3 style="margin:0">Últimos 30 huevos clasificados</h3>'
        + ('<span class="chip-demo">INCLUYE DATOS SIMULADOS</span>'
           if incluir_demo else "")
        + "</div>"
    )
    celdas = []
    for _, fila in df.head(30).iterrows():
        estado = fila["defecto"]
        lote_txt = html.escape(str(fila["lote"] or "—"))
        celdas.append(
            '<div class="mapa-celda">'
            f'<div class="huevo" style="background:{COLORES.get(estado, "#999")}"></div>'
            f'<div class="mapa-label">{lote_txt}<br>{estado}</div>'
            "</div>"
        )
    return titulo + '<div class="mapa">' + "".join(celdas) + "</div>"


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

    # Banner bien visible cuando los datos de demostración están activos
    if incluir_demo:
        st.markdown(
            '<div class="banner-demo">DATOS SIMULADOS — registros de '
            "demostración incluidos en los gráficos y KPIs.</div>",
            unsafe_allow_html=True,
        )

    if df.empty:
        st.info("No hay registros con los filtros actuales.")
        return

    # --- KPIs como tarjetas ---
    st.subheader("Resumen")
    kpis = calcular_kpis(df)
    total = kpis["total"]
    pct_def = kpis["pct_defectuosos"]
    # % de defectos del lote con más defectos (sale del mismo df)
    pct_lote = 0.0
    if kpis["lote_top"] != "—":
        grupo = df[df["lote"] == kpis["lote_top"]]
        pct_lote = float((grupo["defecto"] != "normal").mean() * 100)
    # El % de defectuosos se pinta en rojo si pasa el umbral
    color_def = "#B5412F" if pct_def > umbral else "#2F5D50"
    estilo_def = f' style="color:{color_def}"' if pct_def > umbral else ""

    tarjetas = [
        _kpi(str(total), "Total clasificados", 100, "#2F5D50"),
        _kpi(f"{pct_def:.1f}%", f"Defectuosos (umbral {umbral}%)",
             pct_def, color_def, estilo_def),
        _kpi(str(kpis["rajados"]), "Rajados",
             kpis["rajados"] / total * 100, "#EFAE16"),
        _kpi(str(kpis["rotos"]), "Rotos totales",
             kpis["rotos"] / total * 100, "#B5412F"),
        _kpi(html.escape(str(kpis["lote_top"])), "Lote con más defectos",
             pct_lote, "#B5412F", ' style="font-size:1.5rem"'),
    ]
    st.markdown(
        '<div class="kpis">' + "".join(tarjetas) + "</div>",
        unsafe_allow_html=True,
    )

    # --- Alertas por umbral de defectos por lote (tarjetas yema) ---
    alertas = lotes_en_alerta(df, umbral)
    if alertas:
        visibles = alertas[:6]
        bloques = "".join(
            '<div class="alerta-lote">'
            f'<div class="alerta-lote-nombre">{html.escape(l)}</div>'
            f'<div class="alerta-lote-pct">{p:.0f}% de defectos</div>'
            f'<div class="alerta-lote-nota">Supera el umbral del {umbral}% '
            "de config.yaml</div>"
            "</div>"
            for l, p in visibles
        )
        st.markdown('<div class="alertas">' + bloques + "</div>",
                    unsafe_allow_html=True)
        restantes = len(alertas) - len(visibles)
        if restantes:
            st.caption(
                f"Y {restantes} lotes más por encima del umbral del {umbral}%."
            )

    # --- Vista de maple: últimos 30 huevos ---
    st.markdown(mapa_html(df, incluir_demo), unsafe_allow_html=True)

    # --- Gráficos (Plotly) ---
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("Proporción de estados")
        st.plotly_chart(_estilo(grafico_proporcion(df)), width="stretch")
    with col_der:
        st.subheader("Por tamaño")
        st.plotly_chart(_estilo(grafico_tamanos(df, categorias)), width="stretch")

    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("% de defectos por día")
        st.plotly_chart(_estilo(grafico_defectos_por_dia(df)), width="stretch")
    with col_der:
        st.subheader("Comparación entre lotes")
        st.plotly_chart(_estilo(grafico_lotes(df)), width="stretch")

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
