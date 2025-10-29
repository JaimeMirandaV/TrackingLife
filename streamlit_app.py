import os
import sqlite3
from pathlib import Path
import yaml
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

APP_TITLE = "Tracker Personal · Finanzas · Deporte · Salud"
DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "tracker.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
CONFIG_PATH = Path(__file__).parent / "config.yaml"

st.set_page_config(page_title=APP_TITLE, layout="wide")

def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            con.executescript(f.read())

@st.cache_data
def load_config():
    if CONFIG_PATH.exists():
        return yaml.safe_load(open(CONFIG_PATH, "r", encoding="utf-8"))
    return {"goals": []}

def upsert(table, df: pd.DataFrame, key_cols):
    with sqlite3.connect(DB_PATH) as con:
        existing = pd.read_sql_query(f"SELECT * FROM {table}", con)
        combined = pd.concat([existing, df], ignore_index=True)
        # drop duplicates based on key
        combined = combined.drop_duplicates(subset=key_cols, keep="last")
        combined.to_sql(table, con, if_exists="replace", index=False)

def insert_rows(table, rows: pd.DataFrame):
    with sqlite3.connect(DB_PATH) as con:
        rows.to_sql(table, con, if_exists="append", index=False)

def read_sql(sql: str, params=None) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query(sql, con, params=params or {})

def kpi_card(label, value, help_text=None):
    st.metric(label, value)
    if help_text:
        st.caption(help_text)

def goal_progress(goals_df: pd.DataFrame):
    # Compute simple progress depending on type
    today = pd.Timestamp.today().normalize()
    results = []
    for _, g in goals_df.iterrows():
        start = pd.to_datetime(g["start_date"])
        end = pd.to_datetime(g["end_date"]) if pd.notna(g["end_date"]) else today
        mask = (df_dates["date"] >= start) & (df_dates["date"] <= end)
        window_dates = df_dates.loc[mask, "date"]

        value = None
        detail = ""
        if g["area"] == "finanzas":
            tx = df_finance[df_finance["date"].isin(window_dates)]
            # acumulado de ahorro = ingresos - gastos negativos (o categoría 'Ahorro')
            value = tx["amount"].sum()
            detail = "Suma de montos (+ingreso, -gasto)."
        elif g["area"] == "deporte":
            sp = df_sport[df_sport["date"].isin(window_dates)]
            # distancia total como referencia
            if g["type"] == "acumulativo":
                value = sp["distance_km"].fillna(0).sum()
                detail = "Suma de km en el período."
            elif g["type"] == "promedio":
                value = sp["duration_min"].fillna(0).mean()
                detail = "Promedio de minutos/día con registro."
        elif g["area"] == "salud":
            hl = df_health[df_health["date"].isin(window_dates)]
            if g["type"] == "promedio":
                value = hl["weight_kg"].dropna().mean()
                detail = "Promedio de peso en el período."
            elif g["type"] == "habito":
                # ejemplo: dormir >= 7 horas
                value = (hl["sleep_hours"].fillna(0) >= 7).mean() * 100
                detail = "% de días con ≥7 h de sueño."
            else:
                value = hl["weight_kg"].dropna().iloc[-1] if not hl.empty else None
                detail = "Último valor de peso."

        # compute achieved wrt direction
        target = g["target_value"]
        direction = g["direction"]
        achieved = None
        if value is not None and target is not None:
            if direction == ">=":
                achieved = (value >= target)
            elif direction == "<=":
                achieved = (value <= target)
            elif direction == "==":
                achieved = (value == target)

        results.append({
            "area": g["area"],
            "name": g["name"],
            "periodo": g["period"],
            "tipo": g["type"],
            "valor": value,
            "meta": target,
            "unidad": g.get("unit"),
            "regla": direction,
            "cumplido": achieved,
            "detalle": detail,
            "desde": g["start_date"],
            "hasta": g["end_date"],
        })
    return pd.DataFrame(results)

def date_input_default():
    return st.session_state.get("default_date", date.today())

# Init
init_db()
cfg = load_config()

st.title(APP_TITLE)
st.caption("Registra en minutos; revisa tu tablero y el avance vs. metas (corto/mediano/largo).")

tab_dashboard, tab_finance, tab_sport, tab_health, tab_goals = st.tabs(
    ["Dashboard", "Finanzas", "Deporte", "Salud", "Objetivos"]
)

# Load data for the whole app
df_finance = read_sql("SELECT * FROM finance_tx")
if "date" in df_finance.columns:
    df_finance["date"] = pd.to_datetime(df_finance["date"])

df_sport = read_sql("SELECT * FROM sport_daily")
if "date" in df_sport.columns:
    df_sport["date"] = pd.to_datetime(df_sport["date"])

df_health = read_sql("SELECT * FROM health_daily")
if "date" in df_health.columns:
    df_health["date"] = pd.to_datetime(df_health["date"])

# Date index helper
all_dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=120, freq="D")
df_dates = pd.DataFrame({"date": all_dates})

with tab_finance:
    st.subheader("Registrar finanzas")
    col1, col2, col3 = st.columns(3)
    with col1:
        f_date = st.date_input("Fecha", value=date_input_default())
        f_account = st.text_input("Cuenta (opcional)", value="Billetera")
        f_method = st.selectbox("Método", ["efectivo","transferencia","debito","credito","otro"])
    with col2:
        f_category = st.text_input("Categoría", value="General")
        f_subcategory = st.text_input("Subcategoría", value="")
        f_amount = st.number_input("Monto (+ingreso, -gasto)", step=100.0, value=0.0, format="%.0f")
    with col3:
        f_desc = st.text_input("Descripción", value="")
        f_tags = st.text_input("Tags (coma separada)", value="")
        if st.button("Agregar movimiento"):
            new = pd.DataFrame([{
                "date": f_date.isoformat(),
                "account": f_account,
                "category": f_category,
                "subcategory": f_subcategory,
                "description": f_desc,
                "amount": float(f_amount),
                "method": f_method,
                "tags": f_tags
            }])
            insert_rows("finance_tx", new)
            st.success("Movimiento agregado.")
            st.experimental_rerun()

    st.divider()
    st.subheader("Historial (últimos 30)")
    df_show = read_sql("SELECT * FROM finance_tx ORDER BY date DESC, id DESC LIMIT 30")
    st.dataframe(df_show)

with tab_sport:
    st.subheader("Registrar deporte")
    col1, col2, col3 = st.columns(3)
    with col1:
        s_date = st.date_input("Fecha", value=date_input_default(), key="s_date")
        s_activity = st.text_input("Actividad", value="Correr")
        s_duration = st.number_input("Duración (min)", step=5.0, value=0.0)
    with col2:
        s_distance = st.number_input("Distancia (km)", step=0.1, value=0.0, format="%.2f")
        s_cal = st.number_input("Calorías", step=10.0, value=0.0)
        s_rpe = st.slider("Esfuerzo percibido (RPE 1–10)", 1, 10, 5)
    with col3:
        s_notes = st.text_input("Notas", value="")
        if st.button("Agregar entreno"):
            new = pd.DataFrame([{
                "date": s_date.isoformat(),
                "activity": s_activity,
                "duration_min": float(s_duration),
                "distance_km": float(s_distance),
                "calories": float(s_cal),
                "rpe": int(s_rpe),
                "notes": s_notes
            }])
            insert_rows("sport_daily", new)
            st.success("Entreno agregado.")
            st.experimental_rerun()

    st.divider()
    st.subheader("Historial (últimos 30)")
    df_show = read_sql("SELECT * FROM sport_daily ORDER BY date DESC, id DESC LIMIT 30")
    st.dataframe(df_show)

with tab_health:
    st.subheader("Registrar salud")
    col1, col2, col3 = st.columns(3)
    with col1:
        h_date = st.date_input("Fecha", value=date_input_default(), key="h_date")
        h_weight = st.number_input("Peso (kg)", step=0.1, value=0.0)
        h_sleep = st.number_input("Horas de sueño", step=0.25, value=0.0, format="%.2f")
    with col2:
        h_steps = st.number_input("Pasos", step=100, value=0)
        h_rhr = st.number_input("FC reposo", step=1, value=0)
        h_water = st.number_input("Agua (L)", step=0.25, value=0.0, format="%.2f")
    with col3:
        h_cin = st.number_input("Calorías ingeridas", step=50.0, value=0.0)
        h_cout = st.number_input("Calorías gastadas", step=50.0, value=0.0)
        h_notes = st.text_input("Notas", value="")
        if st.button("Guardar día de salud"):
            new = pd.DataFrame([{
                "date": h_date.isoformat(),
                "weight_kg": float(h_weight),
                "sleep_hours": float(h_sleep),
                "steps": int(h_steps),
                "resting_hr": int(h_rhr),
                "water_l": float(h_water),
                "calories_in": float(h_cin),
                "calories_out": float(h_cout),
                "notes": h_notes
            }])
            upsert("health_daily", new, key_cols=["date"])
            st.success("Salud del día guardada.")
            st.experimental_rerun()

    st.divider()
    st.subheader("Historial (últimos 30)")
    df_show = read_sql("SELECT * FROM health_daily ORDER BY date DESC LIMIT 30")
    st.dataframe(df_show)

with tab_goals:
    st.subheader("Objetivos (corto / mediano / largo)")
    goals_df = pd.DataFrame(cfg.get("goals", []))
    if not goals_df.empty:
        st.dataframe(goals_df)
    else:
        st.info("No hay objetivos en config.yaml todavía.")

    with st.expander("Agregar / editar objetivo"):
        col1, col2, col3 = st.columns(3)
        with col1:
            g_area = st.selectbox("Área", ["finanzas","deporte","salud"])
            g_name = st.text_input("Nombre")
            g_type = st.selectbox("Tipo", ["acumulativo","promedio","habito"])
        with col2:
            g_target = st.number_input("Meta (valor)", value=0.0, step=0.1)
            g_unit = st.text_input("Unidad (opcional)", value="")
            g_period = st.selectbox("Plazo", ["corto","mediano","largo"])
        with col3:
            g_start = st.date_input("Desde", value=date.today().replace(day=1))
            g_end = st.date_input("Hasta (opcional)", value=date.today()+timedelta(days=30))
            g_dir = st.selectbox("Regla", [">=","<=","=="])
            g_notes = st.text_input("Notas", value="")

        if st.button("Guardar objetivo"):
            row = pd.DataFrame([{
                "area": g_area, "name": g_name, "type": g_type,
                "target_value": float(g_target), "unit": g_unit or None,
                "period": g_period, "start_date": g_start.isoformat(),
                "end_date": g_end.isoformat() if g_end else None,
                "direction": g_dir, "notes": g_notes
            }])
            insert_rows("goals", row)
            st.success("Objetivo guardado en la base de datos.")
            st.info("También puedes mantener objetivos en config.yaml para plantillas.")
            st.experimental_rerun()

with tab_dashboard:
    st.subheader("Resumen rápido")
    # KPIs recientes
    last7 = pd.Timestamp.today().normalize() - pd.Timedelta(days=7)
    finance_7 = df_finance[df_finance["date"] >= last7]["amount"].sum() if not df_finance.empty else 0
    sport_7_km = df_sport[df_sport["date"] >= last7]["distance_km"].sum() if "distance_km" in df_sport else 0
    sleep_7 = df_health[df_health["date"] >= last7]["sleep_hours"].mean() if "sleep_hours" in df_health else 0

    c1,c2,c3 = st.columns(3)
    with c1:
        kpi_card("Balance 7 días (CLP)", f"{finance_7:,.0f}".replace(",", "."))
    with c2:
        kpi_card("Km en 7 días", f"{sport_7_km:.1f}")
    with c3:
        kpi_card("Sueño promedio 7 días (h)", f"{sleep_7:.2f}")

    st.divider()
    st.subheader("Avance vs. metas")
    # usar metas de BD si existen; si no, de config.yaml
    db_goals = read_sql("SELECT * FROM goals")
    goals_df = db_goals if not db_goals.empty else pd.DataFrame(cfg.get("goals", []))
    if goals_df.empty:
        st.info("Agrega objetivos en la pestaña Objetivos o en config.yaml.")
    else:
        prog = goal_progress(goals_df)
        st.dataframe(prog)

    st.divider()
    st.subheader("Exportar CSV")
    colx1, colx2, colx3, colx4 = st.columns(4)
    with colx1:
        st.download_button("Finanzas (CSV)", data=df_finance.to_csv(index=False).encode("utf-8"),
                           file_name="finanzas.csv", mime="text/csv")
    with colx2:
        st.download_button("Deporte (CSV)", data=df_sport.to_csv(index=False).encode("utf-8"),
                           file_name="deporte.csv", mime="text/csv")
    with colx3:
        st.download_button("Salud (CSV)", data=df_health.to_csv(index=False).encode("utf-8"),
                           file_name="salud.csv", mime="text/csv")

st.sidebar.header("Opciones")
default_date = st.sidebar.date_input("Fecha por defecto para formularios", value=date.today())
st.session_state["default_date"] = default_date
st.sidebar.info("Tip: agrega este proyecto a tu celular via un ícono al escritorio (PWA) si levantas la app en tu red local.")
