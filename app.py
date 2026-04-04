import pandas as pd
import streamlit as st
from pathlib import Path

CSV_PATH = Path("output/ofertas_qf.csv")

st.set_page_config(page_title="Ofertas QF Chile", page_icon="💊", layout="wide")

st.title("💊 Ofertas Químico Farmacéutico — Chile")

if not CSV_PATH.exists():
    st.warning("Aún no hay datos. Corre `python3 run.py` para generar el CSV.")
    st.stop()

df = pd.read_csv(CSV_PATH, dtype=str).fillna("")

st.caption(f"{len(df)} ofertas encontradas · última actualización: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")

# Filtros
col1, col2 = st.columns([3, 1])
with col1:
    buscar = st.text_input("🔍 Buscar en título o empresa", placeholder="ej. regente, laboral, Santiago")
with col2:
    fuentes = ["Todas"] + sorted(df["fuente"].unique().tolist())
    fuente_sel = st.selectbox("Fuente", fuentes)

# Aplicar filtros
mask = pd.Series([True] * len(df))
if buscar:
    q = buscar.lower()
    mask &= df["titulo"].str.lower().str.contains(q) | df["empresa"].str.lower().str.contains(q)
if fuente_sel != "Todas":
    mask &= df["fuente"] == fuente_sel

df_filtrado = df[mask].reset_index(drop=True)

st.write(f"**{len(df_filtrado)}** resultados")

# Tabla con links clicables
def make_link(row):
    if row["url"]:
        return f'<a href="{row["url"]}" target="_blank">↗</a>'
    return ""

df_display = df_filtrado[["titulo", "empresa", "ubicacion", "fecha_publicacion", "fuente"]].copy()
df_display.insert(0, "link", df_filtrado.apply(make_link, axis=1))

st.write(
    df_display.to_html(escape=False, index=False),
    unsafe_allow_html=True,
)
