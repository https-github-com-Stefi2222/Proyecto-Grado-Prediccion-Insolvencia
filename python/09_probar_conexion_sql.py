import pyodbc

SERVIDOR = "localhost"
BASE_DATOS = "ProyectoGradoQuiebra"

cadena = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SERVIDOR};"
    f"DATABASE={BASE_DATOS};"
    "Trusted_Connection=yes;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

print("=" * 70)
print("PRUEBA DE CONEXIÓN PYTHON -> SQL SERVER")
print("=" * 70)

try:
    conexion = pyodbc.connect(
        cadena,
        timeout=10
    )

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            DB_NAME() AS base_datos,
            @@SERVERNAME AS servidor,
            SUSER_SNAME() AS usuario
    """)

    fila = cursor.fetchone()

    print(f"Base de datos: {fila.base_datos}")
    print(f"Servidor: {fila.servidor}")
    print(f"Usuario conectado: {fila.usuario}")
    print("\nCONEXIÓN EXITOSA")

    cursor.close()
    conexion.close()

except Exception as error:
    print("\nERROR DE CONEXIÓN")
    print(error)