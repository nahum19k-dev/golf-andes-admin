import streamlit as st
from gsheets import subir_excel_a_sheets

st.title("📤 Subir Datos a Google Sheets")

archivo = st.file_uploader("Sube el Excel de Propietarios", type=["xlsx"])

if archivo:
    if st.button("⬆️ Subir a Sheets"):
        with st.spinner("Subiendo..."):
            total = subir_excel_a_sheets(archivo)
            st.success(f"✅ {total} propietarios subidos con ceros intactos!")
