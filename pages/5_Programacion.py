# Después de leer df del uploaded_file y validar que no existe

if st.button("💾 Guardar en Google Sheets", type="primary"):
    periodo_key = f"{mes.upper()}_{int(anio)}"
    
    if gsheets.existe_programacion(periodo_key):
        st.error(f"Ya existe programación para {mes} {anio}. No se puede subir duplicado.")
    else:
        with st.spinner("Creando hoja y guardando..."):
            try:
                nombre_hoja = gsheets.crear_y_guardar_programacion(
                    df=df,
                    periodo_key=periodo_key,
                    mes=mes,
                    anio=int(anio)
                )
                st.success(f"✅ Guardado en la hoja: **{nombre_hoja}**")
            except Exception as e:
                st.error(f"Error: {str(e)}")
