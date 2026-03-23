# ... (tu código anterior: lectura de excel, validaciones, etc.)

if 'df' in locals() and df is not None:  # solo mostrar si ya se cargó el excel
    periodo_key = f"{mes.upper()}_{int(anio)}"
    
    if gsheets.existe_programacion(periodo_key):
        st.error(f"⚠️ Ya existe una programación para {mes} {anio}. No se puede subir duplicado.")
        st.info("Cambia el mes/año o elimina la hoja existente en Google Sheets.")
    else:
        if st.button("💾 Guardar en Google Sheets", type="primary"):
            with st.spinner("Creando hoja y guardando datos..."):
                try:
                    nombre_hoja = gsheets.crear_y_guardar_programacion(
                        df=df,
                        periodo_key=periodo_key,
                        mes=mes,
                        anio=int(anio)
                    )
                    st.success(f"✅ ¡Guardado exitoso!")
                    st.balloons()
                    st.markdown(f"Hoja creada: **{nombre_hoja}**")
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")
                    st.info("Revisa los logs en 'Manage app' → Logs para más detalles.")
