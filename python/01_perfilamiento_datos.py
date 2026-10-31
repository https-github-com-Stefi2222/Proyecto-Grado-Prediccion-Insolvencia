from pathlib import Path
import pandas as pd
import csv

# Ruta raíz del proyecto
RAIZ = Path(__file__).resolve().parent.parent

# Carpeta con datos originales
CARPETA_RAW = RAIZ / "data" / "raw"

print("=" * 80)
print("PERFILAMIENTO INICIAL - PROYECTO DE GRADO")
print("=" * 80)
print(f"Carpeta analizada: {CARPETA_RAW}\n")


def detectar_configuracion_csv(ruta):
    """
    Intenta detectar codificación y separador sin cargar todo el archivo.
    """
    codificaciones = ["utf-8-sig", "utf-8", "cp1252", "latin1"]

    for encoding in codificaciones:
        try:
            with open(ruta, "r", encoding=encoding, errors="strict") as archivo:
                muestra = archivo.read(100000)

            try:
                dialecto = csv.Sniffer().sniff(
                    muestra,
                    delimiters=[",", ";", "\t", "|"]
                )
                separador = dialecto.delimiter
            except csv.Error:
                separador = ","

            return encoding, separador

        except UnicodeDecodeError:
            continue

    return "latin1", ","


archivos = list(CARPETA_RAW.rglob("*.csv"))

if not archivos:
    print("No se encontraron archivos CSV.")
    raise SystemExit

print(f"Archivos CSV encontrados: {len(archivos)}\n")

for numero, archivo in enumerate(archivos, start=1):

    print("=" * 80)
    print(f"ARCHIVO {numero}: {archivo.name}")
    print("=" * 80)

    tamano_gb = archivo.stat().st_size / (1024 ** 3)

    print(f"Ruta: {archivo}")
    print(f"Tamaño: {tamano_gb:.3f} GB")

    encoding, separador = detectar_configuracion_csv(archivo)

    print(f"Codificación detectada: {encoding}")
    print(f"Separador detectado: {repr(separador)}")

    try:
        # Solo lee una pequeña muestra. NO carga el archivo completo.
        muestra = pd.read_csv(
            archivo,
            sep=separador,
            encoding=encoding,
            nrows=20,
            low_memory=False
        )

        print(f"Número de columnas: {len(muestra.columns)}")

        print("\nCOLUMNAS:")
        for i, columna in enumerate(muestra.columns, start=1):
            print(f"{i:03}. {columna}")

        print("\nTIPOS DETECTADOS EN LA MUESTRA:")
        print(muestra.dtypes)

        print("\nPRIMERAS 5 FILAS:")
        print(muestra.head())

    except Exception as e:
        print("\nERROR AL LEER EL ARCHIVO:")
        print(e)

    print("\n")

print("=" * 80)
print("PERFILAMIENTO INICIAL FINALIZADO")
print("=" * 80)