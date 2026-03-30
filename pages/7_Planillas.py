import streamlit as st
import os

st.set_page_config(page_title="Plantillas Excel", page_icon="📥", layout="wide")

st.title("📥 Descargar Plantillas Excel")
st.markdown("Selecciona la plantilla que necesitas para cargar tus datos correctamente.")

# Lista de archivos disponibles (nombre que se muestra, nombre del archivo)
plantillas = [
    ("Propietarios", "propietarios_plantilla.xlsx"),
    ("Programación Mantenimiento", "mantenimiento_plantilla.xlsx"),
    ("Medidores", "medidores_plantilla.xlsx"),
    ("Amortización", "amortizacion_plantilla.xlsx"),
    ("Otros Ingresos", "otros_plantilla.xlsx"),
    ("Pagos Bancos", "pagos_plantilla.xlsx"),
    ("Deuda Inicial", "deuda_inicial_plantilla.xlsx")
]

# Carpeta donde están los archivos (relativo a la raíz del proyecto)
carpeta_plantillas = "plantillas"

# Mostrar cada plantilla con su botón de descarga
for nombre, archivo in plantillas:
    ruta = os.path.join(carpeta_plantillas, archivo)
    try:
        with open(ruta, "rb") as f:
            st.download_button(
                label=f"📎 {nombre}",
                data=f,
                file_name=archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    except FileNotFoundError:
        st.error(f"❌ Archivo no encontrado: {archivo}. Asegúrate de que esté en la carpeta `plantillas/`.")

st.markdown("---")
st.info("💡 **Nota:** Descarga la plantilla correspondiente, complétala con tus datos y luego súbela en la página correspondiente (Propietarios, Programación, Pagos, etc.).")
