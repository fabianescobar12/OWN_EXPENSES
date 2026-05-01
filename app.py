import streamlit as st
import pandas as pd
from datetime import date
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import extra_streamlit_components as stx
import hashlib

COOKIE_NAME = "mis_gastos_auth"
COOKIE_EXPIRY_DAYS = 30

def get_cookie_manager():
    return stx.CookieManager()

def make_token(user: str, key: str) -> str:
    raw = f"{user}:{key}:mis_gastos_salt"
    return hashlib.sha256(raw.encode()).hexdigest()

# ── Config ──────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

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

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

# ── Google Sheets helpers ────────────────────────────────────────────────────
@st.cache_resource
def get_worksheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sh = client.open_by_url(st.secrets["sheet"]["url"])
    return sh.sheet1

def cargar_gastos() -> list[dict]:
    # Sin cache — siempre lee fresco desde Sheets
    return get_worksheet().get_all_records()

def agregar_gasto(nuevo: dict):
    get_worksheet().append_row([
        nuevo["descripcion"],
        nuevo["costo"],
        nuevo["categoria"],
        nuevo["fecha"],
    ])

def eliminar_gasto(row_index: int):
    """row_index es 0-based sobre los datos (sin encabezado)."""
    get_worksheet().delete_rows(row_index + 2)  # +1 encabezado, +1 base 1

def to_df(gastos: list[dict]) -> pd.DataFrame:
    if not gastos:
        return pd.DataFrame(columns=["descripcion", "costo", "categoria", "fecha"])
    df = pd.DataFrame(gastos)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["costo"] = df["costo"].astype(float)
    return df.sort_values("fecha", ascending=False).reset_index(drop=True)

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

.stApp {
    background: #0f0f13;
    color: #f0ede8;
}

h1 { font-weight: 800; letter-spacing: -1px; }

[data-testid="metric-container"] {
    background: #1a1a22;
    border: 1px solid #2e2e3a;
    border-radius: 14px;
    padding: 1rem 1.4rem;
}

[data-testid="stForm"] {
    background: #1a1a22;
    border: 1px solid #2e2e3a;
    border-radius: 18px;
    padding: 1.6rem 2rem 1.2rem;
}

input, .stSelectbox div[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    background: #0f0f13 !important;
    border-color: #2e2e3a !important;
    color: #f0ede8 !important;
    font-family: 'DM Mono', monospace !important;
    border-radius: 10px !important;
}

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

button[kind="secondary"] {
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: .75rem !important;
}

[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid #2e2e3a;
}

hr { border-color: #2e2e3a; }

.chip {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-family: 'DM Mono', monospace;
    font-size: .78rem;
    font-weight: 500;
    letter-spacing: .4px;
}

/* Progress bar de categoría */
.cat-bar-bg {
    background: #2e2e3a;
    border-radius: 999px;
    height: 8px;
    overflow: hidden;
    margin-top: 4px;
}
.cat-bar-fill {
    height: 8px;
    border-radius: 999px;
    transition: width 0.6s ease;
}

.metric-card {
    background: #1a1a22;
    border: 1px solid #2e2e3a;
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: .6rem;
}

.big-number {
    font-family: 'DM Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -1px;
    line-height: 1;
}

.label-sm {
    font-family: 'DM Mono', monospace;
    font-size: .75rem;
    color: #666;
    margin-bottom: .3rem;
    text-transform: uppercase;
    letter-spacing: .8px;
}

/* Tabs */
[data-testid="stTabs"] button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Login ────────────────────────────────────────────────────────────────────
def check_login():
    cookie_manager = get_cookie_manager()
    token_valido = make_token(st.secrets["auth"]["user"], st.secrets["auth"]["key"])

    # ¿Ya hay cookie válida?
    cookie = cookie_manager.get(COOKIE_NAME)
    if cookie and cookie == token_valido:
        st.session_state.autenticado = True

    if st.session_state.get("autenticado"):
        return True, cookie_manager

    st.markdown("""
    <div style='max-width:380px;margin:80px auto 0;'>
        <div style='text-align:center;margin-bottom:2rem'>
            <span style='font-size:3rem'>💸</span>
            <h2 style='margin:.4rem 0 .2rem;font-weight:800;letter-spacing:-1px'>Mis Gastos</h2>
            <p style='color:#555;font-family:DM Mono,monospace;font-size:.85rem'>acceso privado</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            usuario = st.text_input("Usuario", placeholder="usuario")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            entrar = st.form_submit_button("Entrar →", use_container_width=True, type="primary")

        if entrar:
            if (usuario == st.secrets["auth"]["user"] and
                    password == st.secrets["auth"]["key"]):
                st.session_state.autenticado = True
                cookie_manager.set(
                    COOKIE_NAME,
                    token_valido,
                    max_age=COOKIE_EXPIRY_DAYS * 24 * 3600,
                )
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    return False, cookie_manager

autenticado, cookie_manager = check_login()
if not autenticado:
    st.stop()

# ── Estado ───────────────────────────────────────────────────────────────────
if "gastos" not in st.session_state:
    st.session_state.gastos = cargar_gastos()

gastos = st.session_state.gastos

# ── Header ───────────────────────────────────────────────────────────────────
h1, h2 = st.columns([6, 1])
with h1:
    st.markdown("# 💸 Gastos")
    st.markdown("<p style='color:#666;margin-top:-12px;font-family:DM Mono,monospace;font-size:.9rem'>control personal de gastos</p>", unsafe_allow_html=True)
with h2:
    st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)
    if st.button("Salir →", use_container_width=True):
        st.session_state.autenticado = False
        cookie_manager.delete(COOKIE_NAME)
        st.rerun()
st.markdown("---")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_registro, tab_metricas = st.tabs(["📋 Registro", "📊 Métricas"])

# ═══════════════════════════════════════════════════════════
#  TAB 1 — REGISTRO
# ═══════════════════════════════════════════════════════════
with tab_registro:
    col_form, col_lista = st.columns([1, 1.6], gap="large")

    # ── FORMULARIO ──────────────────────────────────────────
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
                    agregar_gasto(nuevo)
                    st.session_state.gastos = cargar_gastos()
                    st.success(f"✅ Gasto registrado: **{descripcion}** — ${costo:,.0f}")
                    st.rerun()

    # ── LISTA ───────────────────────────────────────────────
    with col_lista:
        if not gastos:
            st.info("Aún no tienes gastos registrados. ¡Agrega el primero! 👈")
        else:
            df = to_df(gastos)

            total = df["costo"].sum()
            mes_actual = date.today().strftime("%Y-%m")
            df_mes = df[df["fecha"].dt.strftime("%Y-%m") == mes_actual]
            total_mes = df_mes["costo"].sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("Total acumulado", f"${total:,.0f}")
            m2.metric("Este mes", f"${total_mes:,.0f}")
            m3.metric("Registros", len(df))

            st.markdown("---")

            st.markdown("**Filtrar por categoría**")
            cats_disponibles = ["Todas"] + list(df["categoria"].unique())
            filtro = st.radio("", cats_disponibles, horizontal=True, label_visibility="collapsed")

            df_vista = df if filtro == "Todas" else df[df["categoria"] == filtro]

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
                            eliminar_gasto(i)
                            st.session_state.gastos = cargar_gastos()
                            st.rerun()

            st.markdown("---")
            st.markdown("### 📊 Por categoría")
            resumen = df.groupby("categoria")["costo"].sum().reset_index()
            resumen.columns = ["Categoría", "Total"]
            resumen["Total"] = resumen["Total"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(resumen, hide_index=True)


# ═══════════════════════════════════════════════════════════
#  TAB 2 — MÉTRICAS
# ═══════════════════════════════════════════════════════════

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono, monospace", color="#f0ede8"),
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="right", x=1,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    ),
)

with tab_metricas:
    if not gastos:
        st.info("Sin datos aún. Registra algunos gastos para ver las métricas. 👈")
    else:
        df_all = to_df(gastos)
        hoy = date.today()

        # ── Selector de período ─────────────────────────
        st.markdown("### 🔍 Período de análisis")
        modo = st.radio(
            "",
            ["📅 Por mes", "📆 Por año", "🗓 Intervalo personalizado"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if modo == "📅 Por mes":
            años_disp = sorted(df_all["fecha"].dt.year.unique(), reverse=True)
            col_a, col_m = st.columns([1, 2])
            with col_a:
                año_sel = st.selectbox("Año", años_disp)
            with col_m:
                meses_disp = sorted(
                    df_all[df_all["fecha"].dt.year == año_sel]["fecha"].dt.month.unique()
                )
                mes_nombre = st.selectbox(
                    "Mes", [MESES_ES[m] for m in meses_disp],
                    index=len(meses_disp) - 1 if hoy.year == año_sel else 0,
                )
                mes_sel = [k for k, v in MESES_ES.items() if v == mes_nombre][0]
            df = df_all[
                (df_all["fecha"].dt.year == año_sel) &
                (df_all["fecha"].dt.month == mes_sel)
            ]
            titulo_periodo = f"{mes_nombre} {año_sel}"

        elif modo == "📆 Por año":
            años_disp = sorted(df_all["fecha"].dt.year.unique(), reverse=True)
            año_sel = st.selectbox("Año", años_disp)
            df = df_all[df_all["fecha"].dt.year == año_sel]
            titulo_periodo = f"Año {año_sel}"

        else:
            col_d1, col_d2 = st.columns(2)
            fecha_min = df_all["fecha"].min().date()
            fecha_max = df_all["fecha"].max().date()
            with col_d1:
                desde = st.date_input("Desde", value=fecha_min, min_value=fecha_min, max_value=fecha_max)
            with col_d2:
                hasta = st.date_input("Hasta", value=fecha_max, min_value=fecha_min, max_value=fecha_max)
            df = df_all[
                (df_all["fecha"].dt.date >= desde) &
                (df_all["fecha"].dt.date <= hasta)
            ]
            titulo_periodo = f"{desde.strftime('%d %b %Y')} → {hasta.strftime('%d %b %Y')}"

        if df.empty:
            st.warning(f"Sin gastos en el período: **{titulo_periodo}**")
        else:
            # ══════════════════════════════════════════════
            #  GRÁFICOS PRIMERO
            # ══════════════════════════════════════════════

            st.markdown("---")
            st.markdown(f"### 📊 Visualizaciones — {titulo_periodo}")

            # ── Fila 1: Donut + Barras apiladas ─────────
            gcol1, gcol2 = st.columns([1, 1.8], gap="large")

            with gcol1:
                st.markdown("##### Distribución por categoría")
                resumen_cat = (
                    df.groupby("categoria")["costo"]
                    .agg(["sum", "count", "mean", "max"])
                    .reset_index()
                )
                resumen_cat.columns = ["categoria", "total", "cantidad", "promedio", "maximo"]
                resumen_cat = resumen_cat.sort_values("total", ascending=False)
                total_p = resumen_cat["total"].sum()

                fig_donut = go.Figure(go.Pie(
                    labels=resumen_cat["categoria"],
                    values=resumen_cat["total"],
                    hole=0.62,
                    marker=dict(
                        colors=[COLORES.get(c, "#888") for c in resumen_cat["categoria"]],
                        line=dict(color="#0f0f13", width=2),
                    ),
                    textinfo="percent",
                    textfont=dict(size=12, family="DM Mono, monospace"),
                    hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
                ))
                fig_donut.add_annotation(
                    text=f"<b>${total_p:,.0f}</b>",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=18, color="#f0ede8", family="DM Mono, monospace"),
                )
                fig_donut.update_layout(
                    **PLOTLY_LAYOUT,
                    height=300,
                    showlegend=True,
                )
                st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

            with gcol2:
                # ── Evolución temporal ───────────────────
                st.markdown("##### Evolución temporal")
                df_tiempo = df.copy()
                rango_dias = (df_tiempo["fecha"].max() - df_tiempo["fecha"].min()).days

                if rango_dias <= 31:
                    df_tiempo["periodo"] = df_tiempo["fecha"].dt.strftime("%d %b")
                    x_label = "Día"
                elif rango_dias <= 366:
                    df_tiempo["periodo"] = df_tiempo["fecha"].dt.to_period("W").apply(
                        lambda r: r.start_time.strftime("%d %b")
                    )
                    x_label = "Semana"
                else:
                    df_tiempo["periodo"] = df_tiempo["fecha"].dt.strftime("%b %Y")
                    x_label = "Mes"

                df_evo = df_tiempo.groupby(["periodo", "categoria"])["costo"].sum().reset_index()
                periodos_ord = (
                    df_tiempo.groupby("periodo")["fecha"].min()
                    .sort_values().index.tolist()
                )

                fig_bars = go.Figure()
                for cat in resumen_cat["categoria"]:
                    sub = df_evo[df_evo["categoria"] == cat]
                    sub_map = dict(zip(sub["periodo"], sub["costo"]))
                    fig_bars.add_trace(go.Bar(
                        name=cat,
                        x=periodos_ord,
                        y=[sub_map.get(p, 0) for p in periodos_ord],
                        marker_color=COLORES.get(cat, "#888"),
                        hovertemplate=f"<b>{cat}</b><br>%{{x}}<br>$%{{y:,.0f}}<extra></extra>",
                    ))
                fig_bars.update_layout(
                    **PLOTLY_LAYOUT,
                    barmode="stack",
                    height=300,
                    xaxis=dict(gridcolor="#2e2e3a", tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="#2e2e3a", tickprefix="$", tickfont=dict(size=10)),
                )
                st.plotly_chart(fig_bars, use_container_width=True, config={"displayModeBar": False})

            # ── Fila 2: Barras horizontales por cat + Días semana ──
            gcol3, gcol4 = st.columns([1.4, 1], gap="large")

            with gcol3:
                st.markdown("##### Gasto por categoría (detalle)")
                fig_hbar = go.Figure()
                for _, row in resumen_cat.sort_values("total").iterrows():
                    color = COLORES.get(row["categoria"], "#888")
                    fig_hbar.add_trace(go.Bar(
                        name=row["categoria"],
                        x=[row["total"]],
                        y=[row["categoria"]],
                        orientation="h",
                        marker=dict(color=color, line=dict(color=color, width=0)),
                        text=f"  ${row['total']:,.0f}  ({row['total']/total_p*100:.1f}%)",
                        textposition="outside",
                        textfont=dict(size=11, color=color),
                        hovertemplate=(
                            f"<b>{row['categoria']}</b><br>"
                            f"Total: ${row['total']:,.0f}<br>"
                            f"Transacciones: {int(row['cantidad'])}<br>"
                            f"Promedio: ${row['promedio']:,.0f}<extra></extra>"
                        ),
                    ))
                fig_hbar.update_layout(
                    **PLOTLY_LAYOUT,
                    showlegend=False,
                    height=220,
                    xaxis=dict(gridcolor="#2e2e3a", tickprefix="$", tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=12)),
                )
                st.plotly_chart(fig_hbar, use_container_width=True, config={"displayModeBar": False})

            with gcol4:
                st.markdown("##### Gasto por día de semana")
                dias_nombre = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                df_dias = df.copy()
                df_dias["dia_semana"] = df_dias["fecha"].dt.dayofweek
                gasto_dia = df_dias.groupby("dia_semana")["costo"].sum()
                vals_dias = [gasto_dia.get(d, 0) for d in range(7)]
                colors_dias = [
                    "#FF6B6B" if d == hoy.weekday() else "rgba(77,150,255,0.25)"
                    for d in range(7)
                ]
                fig_dias = go.Figure(go.Bar(
                    x=dias_nombre,
                    y=vals_dias,
                    marker=dict(
                        color=colors_dias,
                        line=dict(color="rgba(0,0,0,0)"),
                    ),
                    hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
                ))
                fig_dias.update_layout(
                    **PLOTLY_LAYOUT,
                    showlegend=False,
                    height=220,
                    xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11)),
                    yaxis=dict(gridcolor="#2e2e3a", tickprefix="$", tickfont=dict(size=10)),
                )
                st.plotly_chart(fig_dias, use_container_width=True, config={"displayModeBar": False})

            # ══════════════════════════════════════════════
            #  KPIs + DETALLES ABAJO
            # ══════════════════════════════════════════════

            st.markdown("---")
            st.markdown(f"#### 📌 Resumen — {titulo_periodo}")

            total_periodo = df["costo"].sum()
            n_registros = len(df)
            promedio = df["costo"].mean()
            gasto_max = df["costo"].max()
            dias_con_gasto = df["fecha"].dt.date.nunique()

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("💰 Total gastado", f"${total_periodo:,.0f}")
            k2.metric("🧾 Transacciones", n_registros)
            k3.metric("📈 Promedio por gasto", f"${promedio:,.0f}")
            k4.metric("🔺 Gasto más alto", f"${gasto_max:,.0f}")
            k5.metric("📅 Días con gastos", dias_con_gasto)

            st.markdown("---")

            # ── Tarjetas por categoría + Top 5 ─────────
            col_cats, col_top = st.columns([1.2, 1], gap="large")

            with col_cats:
                st.markdown("#### 🗂 Detalle por categoría")
                for _, row in resumen_cat.iterrows():
                    color = COLORES.get(row["categoria"], "#888")
                    pct = (row["total"] / total_p * 100) if total_p > 0 else 0
                    st.markdown(
                        f"""
                        <div style='background:#1a1a22;border:1px solid #2e2e3a;border-radius:14px;
                                    padding:1rem 1.2rem;margin-bottom:.8rem;border-left:4px solid {color}'>
                            <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                                <div>
                                    <div style='font-weight:700;font-size:1rem'>{row['categoria']}</div>
                                    <div style='font-family:DM Mono,monospace;font-size:.75rem;color:#555;margin-top:2px'>
                                        {int(row['cantidad'])} transacciones · prom ${row['promedio']:,.0f} · max ${row['maximo']:,.0f}
                                    </div>
                                </div>
                                <div style='text-align:right'>
                                    <div style='font-family:DM Mono,monospace;font-size:1.15rem;
                                                font-weight:700;color:{color}'>${row['total']:,.0f}</div>
                                    <div style='font-family:DM Mono,monospace;font-size:.75rem;color:#666'>{pct:.1f}%</div>
                                </div>
                            </div>
                            <div class='cat-bar-bg' style='margin-top:.6rem'>
                                <div class='cat-bar-fill' style='width:{pct}%;background:{color}'></div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with col_top:
                st.markdown("#### 🏆 Top 5 gastos del período")
                top5 = df.nlargest(5, "costo")
                for rank, (_, row) in enumerate(top5.iterrows(), 1):
                    color = COLORES.get(row["categoria"], "#888")
                    st.markdown(
                        f"""
                        <div style='background:#1a1a22;border:1px solid #2e2e3a;border-radius:12px;
                                    padding:.7rem 1rem;margin-bottom:.5rem;display:flex;
                                    align-items:center;gap:.8rem'>
                            <span style='font-family:DM Mono,monospace;font-size:1.1rem;
                                        color:#333;font-weight:700;min-width:24px'>#{rank}</span>
                            <div style='flex:1'>
                                <div style='font-weight:700'>{row['descripcion']}</div>
                                <div style='display:flex;gap:.4rem;margin-top:2px'>
                                    <span class='chip' style='background:{color}22;color:{color}'>{row['categoria']}</span>
                                    <span style='font-family:DM Mono,monospace;font-size:.75rem;color:#555'>
                                        {row['fecha'].strftime('%d %b')}
                                    </span>
                                </div>
                            </div>
                            <span style='font-family:DM Mono,monospace;font-weight:700;color:{color};font-size:1rem'>
                                ${row['costo']:,.0f}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("---")

            # ── Tabla detallada ─────────────────────────
            st.markdown("#### 🗃 Detalle completo del período")
            df_export = df[["fecha", "descripcion", "categoria", "costo"]].copy()
            df_export["fecha"] = df_export["fecha"].dt.strftime("%d %b %Y")
            df_export["costo"] = df_export["costo"].apply(lambda x: f"${x:,.0f}")
            df_export.columns = ["Fecha", "Descripción", "Categoría", "Costo"]
            st.dataframe(df_export, hide_index=True, use_container_width=True)