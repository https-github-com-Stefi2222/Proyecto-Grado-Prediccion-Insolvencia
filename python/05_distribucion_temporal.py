from pathlib import Path
import pandas as pd
import csv
import re

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
OUTPUT = RAIZ / "outputs" / "tablas"

OUTPUT.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 250_000


def detectar_configuracion_csv(ruta):
    codificaciones = ["utf-8-sig", "utf-8", "cp1252", "latin1"]

    for encoding in codificaciones:
        try:
            with open(ruta, "r", encoding=encoding) as archivo:
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


def extraer_anio(valor):
    if pd.isna(valor):
        return None

    texto = str(valor)

    coincidencias = re.findall(r"(20\d{2})", texto)

    if coincidencias:
        return int(coincidencias[0])

    return None


archivos = [
    p for p in RAW.glob("*.csv")
    if "Estados_Financieros" in p.name
]

resultados = []

print("=" * 90)
print("ANÁLISIS DE DISTRIBUCIÓN TEMPORAL")
print("=" * 90)

for archivo in sorted(archivos):

    print(f"\nProcesando: {archivo.name}")

    encoding, separador = detectar_configuracion_csv(archivo)

    conteo_fecha_corte = {}
    conteo_periodo = {}
    total = 0

    lector = pd.read_csv(
        archivo,
        sep=separador,
        encoding=encoding,
        usecols=["FECHA_CORTE", "PERIODO"],
        chunksize=CHUNK_SIZE,
        low_memory=False
    )

    for numero_chunk, chunk in enumerate(lector, start=1):

        total += len(chunk)

        anos_fecha = chunk["FECHA_CORTE"].map(extraer_anio)
        anos_periodo = chunk["PERIODO"].map(extraer_anio)

        for anio, cantidad in anos_fecha.value_counts().items():
            if pd.notna(anio):
                anio = int(anio)
                conteo_fecha_corte[anio] = (
                    conteo_fecha_corte.get(anio, 0) + int(cantidad)
                )

        for anio, cantidad in anos_periodo.value_counts().items():
            if pd.notna(anio):
                anio = int(anio)
                conteo_periodo[anio] = (
                    conteo_periodo.get(anio, 0) + int(cantidad)
                )

        if numero_chunk % 10 == 0:
            print(
                f"  Bloques: {numero_chunk} | "
                f"Filas procesadas: {total:,}"
            )

    print(f"\nTotal de filas: {total:,}")

    print("\nDistribución por FECHA_CORTE:")
    for anio in sorted(conteo_fecha_corte):
        print(
            f"  {anio}: "
            f"{conteo_fecha_corte[anio]:,}"
        )

        resultados.append({
            "archivo": archivo.name,
            "campo": "FECHA_CORTE",
            "anio": anio,
            "filas": conteo_fecha_corte[anio]
        })

    print("\nDistribución por PERIODO:")
    for anio in sorted(conteo_periodo):
        print(
            f"  {anio}: "
            f"{conteo_periodo[anio]:,}"
        )

        resultados.append({
            "archivo": archivo.name,
            "campo": "PERIODO",
            "anio": anio,
            "filas": conteo_periodo[anio]
        })

    print("\n" + "-" * 90)


df_resultados = pd.DataFrame(resultados)

ruta = OUTPUT / "distribucion_temporal_financieros.csv"

df_resultados.to_csv(
    ruta,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 90)
print("RESUMEN 2021-2024")
print("=" * 90)

periodo_estudio = df_resultados[
    df_resultados["anio"].between(2021, 2024)
]

if not periodo_estudio.empty:
    resumen = (
        periodo_estudio
        .pivot_table(
            index=["archivo", "campo"],
            columns="anio",
            values="filas",
            aggfunc="sum",
            fill_value=0
        )
    )

    print(resumen.to_string())

print("\nArchivo generado:")
print(ruta)

print("\nANÁLISIS TEMPORAL FINALIZADO")