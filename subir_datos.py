import json
import gspread
from google.oauth2.service_account import Credentials

# Configuración
SPREADSHEET_ID = "17AlCV7QTnuz1QZCW2Z7Q9YpzaD2tNhscuerAO6tZb68"
JSON_KEY_FILE = "golf-andes-admin.json"  # Tu archivo JSON de credenciales

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Conectar
creds = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet("Propietarios")

# Cargar datos del JSON
with open("propietarios.json", "r", encoding="utf-8") as f:
    datos = json.load(f)

# Encabezados
headers = ["codigo", "torre", "dpto", "dni", "nombre", 
           "direccion", "celular", "correo", "situacion"]

# Subir encabezados
sheet.update("A1", [headers])

# Subir datos
filas = []
for p in datos:
    fila = [p.get(h, "") for h in headers]
    filas.append(fila)

sheet.update("A2", filas)
print(f"✅ {len(filas)} propietarios subidos correctamente!")
