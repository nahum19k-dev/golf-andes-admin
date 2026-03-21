import streamlit as st
import json, pandas as pd

st.set_page_config(page_title="Dashboard", page_icon="📈", layout="wide")
st.markdown("""<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%); }
[data-testid="stSidebar"] * { color: white !important; }
</style>""", unsafe_allow_html=True)

@st.cache_data
def cargar():
    with open("propietarios.json","r",encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))

df = cargar()
st.markdown("### Dashboard")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Propietarios", len(df))
c2.metric("Torres", 19)
c3.metric("Con correo", df[df["correo"].str.strip()!=""].shape[0])
c4.metric("Con celular", df[df["celular"].str.strip()!=""].shape[0])
st.markdown("---")
st.markdown("#### Propietarios por Torre")
por_torre = df[df["torre"].str.strip()!=""].groupby("torre").size().reset_index(name="cantidad")
por_torre["torre"] = "Torre " + por_torre["torre"]
st.bar_chart(por_torre.set_index("torre"))
