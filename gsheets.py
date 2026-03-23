def leer_propietarios():
    sheet = get_sheet("Propietarios")
    todos = sheet.get_all_values()
    if len(todos) < 2:
        return pd.DataFrame()
    
    headers = todos[0]
    filas = todos[1:]
    df = pd.DataFrame(filas, columns=headers)
    
    # ✅ FIX: astype(str) antes de zfill
    df["codigo"] = df["codigo"].astype(str).str.strip().str.zfill(5)
    df["torre"]  = df["torre"].astype(str).str.strip().str.zfill(2)
    df["dpto"]   = df["dpto"].astype(str).str.strip().str.zfill(3)
    df["dni"]    = df["dni"].astype(str).str.strip().str.zfill(8)
    
    # Limpiar vacíos
    df["codigo"] = df["codigo"].apply(lambda x: "" if x == "00000" else x)
    df["torre"]  = df["torre"].apply(lambda x: "" if x == "00" else x)
    df["dpto"]   = df["dpto"].apply(lambda x: "" if x == "000" else x)
    df["dni"]    = df["dni"].apply(lambda x: "" if x == "00000000" else x)
    
    return df
