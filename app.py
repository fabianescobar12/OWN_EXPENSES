import streamlit as st
import pandas as pd
import json
import os
from datetime import date
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
DATA_FILE = Path.home() / ".mis_gastos.json"

CATEGORIAS = {
    "🍕 Comida":      "COMIDA",
    "🎮 Juegos":      "JUEGOS",
    "🚗 Uber/DiDi":   "UBER/DIDI",
    "🏥 Salud":       "SALUD",
}

COLORES = {
    "COMIDA":    "#FF6B6B",
    "JUEGOS":    "#6BCB77",
    "UBER/DIDI": "#4D96FF",
    "SALUD":     "#FFD93D",
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def cargar_gastos() -> list[dict]:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_gastos(gastos: list[dict]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(gastos, f, ensure_ascii=False, indent=2, default=str)

def to_df(gastos: list[dict]) -> pd.DataFrame:
    if not gastos:
        return pd.DataFrame(columns=["descripcion", "costo", "categoria", "fecha"])
    df = pd.DataFrame(gastos)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["costo"] = df["costo"].astype(float)
    return df.sort_values("fecha", ascending=False)

# ── Page setup ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mis Gastos",
    page_icon="💸",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}

/* fondo general */
.stApp {
    background: #0f0f13;
    color: #f0ede8;
}

/* título principal */
h1 { font-weight: 800; letter-spacing: -1px; }

/* cards métricas */
[data-testid="metric-container"] {
    background: #1a1a22;
    border: 1px solid #2e2e3a;
    border-radius: 14px;
    padding: 1rem 1.4rem;
}

/* formulario */
[data-testid="stForm"] {
    background: #1a1a22;
    border: 1px solid #2e2e3a;
    border-radius: 18px;
    padding: 1.6rem 2rem 1.2rem;
}

/* inputs */
input, .stSelectbox div[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    background: #0f0f13 !important;
    border-color: #2e2e3a !important;
    color: #f0ede8 !important;
    font-family: 'DM Mono', monospace !important;
    border-radius: 10px !important;
}

/* botón principal */
button[kind="primaryFormSubmit"], button[kind="primary"] {
    background: linear-gradient(135deg, #ff6b6b, #ff4d4d) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: .5px !important;
}
button[kind="primaryFormSubmit"]:hover {
    filter: brightness(1.12);
}

/* botón eliminar */
button[kind="secondary"] {
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: .75rem !important;
}

/* tabla */
[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid #2e2e3a;
}

/* separador */
hr { border-color: #2e2e3a; }

/* chip categoría */
.chip {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-family: 'DM Mono', monospace;
    font-size: .78rem;
    font-weight: 500;
    letter-spacing: .4px;
}
</style>
""", unsafe_allow_html=True)

# ── Estado ───────────────────────────────────────────────────────────────────
if "gastos" not in st.session_state:
    st.session_state.gastos = cargar_gastos()

gastos = st.session_state.gastos

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 💸 Mis Gastos")
st.markdown("<p style='color:#666;margin-top:-12px;font-family:DM Mono,monospace;font-size:.9rem'>control personal de gastos</p>", unsafe_allow_html=True)
st.markdown("---")

# ── Layout ───────────────────────────────────────────────────────────────────
col_form, col_lista = st.columns([1, 1.6], gap="large")

# ────────────────────────── FORMULARIO ──────────────────────────────────────
with col_form:
    st.markdown("### ➕ Nuevo gasto")

    with st.form("form_gasto", clear_on_submit=True):
        descripcion = st.text_input(
            "Descripción",
            placeholder="Ej: chocolate, café, Uber al mall…",
        )

        costo = st.number_input(
            "Costo ($)",
            min_value=0.0,
            step=100.0,
            format="%.0f",
        )

        cat_label = st.selectbox("Categoría", list(CATEGORIAS.keys()))

        fecha = st.date_input("Fecha", value=date.today())

        submitted = st.form_submit_button("Registrar gasto", use_container_width=True, type="primary")

        if submitted:
            if not descripcion.strip():
                st.error("Escribe una descripción.")
            elif costo <= 0:
                st.error("El costo debe ser mayor a $0.")
            else:
                nuevo = {
                    "descripcion": descripcion.strip(),
                    "costo": float(costo),
                    "categoria": CATEGORIAS[cat_label],
                    "fecha": str(fecha),
                }
                gastos.insert(0, nuevo)
                st.session_state.gastos = gastos
                guardar_gastos(gastos)
                st.success(f"✅ Gasto registrado: **{descripcion}** — ${costo:,.0f}")

# ────────────────────────── MÉTRICAS + LISTA ────────────────────────────────
with col_lista:
    if not gastos:
        st.info("Aún no tienes gastos registrados. ¡Agrega el primero! 👈")
    else:
        df = to_df(gastos)

        # --- métricas
        total = df["costo"].sum()
        mes_actual = date.today().strftime("%Y-%m")
        df_mes = df[df["fecha"].dt.strftime("%Y-%m") == mes_actual]
        total_mes = df_mes["costo"].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Total acumulado", f"${total:,.0f}")
        m2.metric("Este mes", f"${total_mes:,.0f}")
        m3.metric("Registros", len(df))

        st.markdown("---")

        # --- filtros rápidos
        st.markdown("**Filtrar por categoría**")
        cats_disponibles = ["Todas"] + list(df["categoria"].unique())
        filtro = st.radio("", cats_disponibles, horizontal=True, label_visibility="collapsed")

        df_vista = df if filtro == "Todas" else df[df["categoria"] == filtro]

        # --- lista de gastos
        st.markdown(f"<p style='color:#555;font-size:.8rem;font-family:DM Mono,monospace'>{len(df_vista)} registro(s)</p>", unsafe_allow_html=True)

        for i, row in df_vista.iterrows():
            color = COLORES.get(row["categoria"], "#888")
            with st.container():
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f"""
                        <div style='background:#1a1a22;border:1px solid #2e2e3a;border-left:4px solid {color};
                                    border-radius:12px;padding:.7rem 1rem;margin-bottom:.5rem'>
                            <div style='display:flex;justify-content:space-between;align-items:center'>
                                <span style='font-weight:700;font-size:1rem'>{row['descripcion']}</span>
                                <span style='font-family:DM Mono,monospace;font-size:1rem;color:{color};font-weight:700'>
                                    ${row['costo']:,.0f}
                                </span>
                            </div>
                            <div style='margin-top:.3rem;display:flex;gap:.5rem;align-items:center'>
                                <span class='chip' style='background:{color}22;color:{color}'>{row['categoria']}</span>
                                <span style='color:#555;font-family:DM Mono,monospace;font-size:.78rem'>
                                    {row['fecha'].strftime('%d %b %Y')}
                                </span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown("<div style='margin-top:.6rem'></div>", unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_{i}", help="Eliminar gasto"):
                        gastos_actualizado = [g for j, g in enumerate(gastos) if j != i]
                        st.session_state.gastos = gastos_actualizado
                        guardar_gastos(gastos_actualizado)
                        st.rerun()

        # --- resumen por categoría
        st.markdown("---")
        st.markdown("### 📊 Por categoría")
        resumen = df.groupby("categoria")["costo"].sum().reset_index()
        resumen.columns = ["Categoría", "Total"]
        resumen["Total"] = resumen["Total"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(resumen, hide_index = True)