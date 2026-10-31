from pathlib import Path
import pandas as pd
import csv
import re
import time

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
PROCESSED = RAIZ / "data" / "processed"
TABLAS = RAIZ / "outputs" / "tablas"

PROCESSED.mkdir(parents=True, exist_ok=True)
TABLAS.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 250_000
ANIOS_VALIDOS = {2021, 2022, 2023, 2024}


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


def extraer_anio_fecha_corte(valor):
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).strip()

    coincidencia = re.search(r"\b(20\d{2})\b", texto)

    if coincidencia:
        return int(coincidencia.group(1))

    return pd.NA


def normalizar_nit(serie):
    return (
        serie.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\D", "", regex=True)
        .replace("", pd.NA)
    )


archivos = sorted([
    archivo
    for archivo in RAW.glob("*.csv")
    if "Estados_Financieros" in archivo.name
])

print("=" * 90)
print("FILTRADO DE ESTADOS FINANCIEROS - PERIODO 2021-2024")
print("=" * 90)
print(f"Archivos financieros encontrados: {len(archivos)}")
print(f"Procesamiento por bloques: {CHUNK_SIZE:,} filas\n")

resumen = []

for numero, archivo in enumerate(archivos, start=1):

    inicio = time.time()

    encoding, separador = detectar_configuracion_csv(archivo)

    if "Carátula" in archivo.name or "Caratula" in archivo.name:
        nombre_salida = "financiero_caratula_2021_2024.csv"

    elif "Resultado_Integral" in archivo.name:
        nombre_salida = "financiero_resultado_integral_2021_2024.csv"

    elif "Situación_Financiera" in archivo.name or "Situacion_Financiera" in archivo.name:
        nombre_salida = "financiero_situacion_financiera_2021_2024.csv"

    else:
        nombre_salida = f"filtrado_{archivo.name}"

    salida = PROCESSED / nombre_salida

    # Si existe una ejecución anterior, se elimina para evitar duplicar datos
    if salida.exists():
        salida.unlink()

    total_leidas = 0
    total_conservadas = 0
    conteo_anual = {
        2021: 0,
        2022: 0,
        2023: 0,
        2024: 0
    }

    primer_bloque_escrito = False

    print("=" * 90)
    print(f"[{numero}/{len(archivos)}] {archivo.name}")
    print(f"Salida: {nombre_salida}")
    print("=" * 90)

    lector = pd.read_csv(
        archivo,
        sep=separador,
        encoding=encoding,
        chunksize=CHUNK_SIZE,
        low_memory=False,
        dtype={"NIT": "string"}
    )

    for nro_chunk, chunk in enumerate(lector, start=1):

        total_leidas += len(chunk)

        # Obtener año únicamente desde FECHA_CORTE
        chunk["ANIO_CORTE"] = (
            chunk["FECHA_CORTE"]
            .map(extraer_anio_fecha_corte)
            .astype("Int64")
        )

        filtrado = chunk[
            chunk["ANIO_CORTE"].isin(ANIOS_VALIDOS)
        ].copy()

        if not filtrado.empty:

            # Crear identificador homogéneo para futuras integraciones
            if "NIT" in filtrado.columns:
                filtrado["NIT_NORMALIZADO"] = normalizar_nit(
                    filtrado["NIT"]
                )

            total_conservadas += len(filtrado)

            for anio, cantidad in (
                filtrado["ANIO_CORTE"]
                .value_counts()
                .items()
            ):
                conteo_anual[int(anio)] += int(cantidad)

            filtrado.to_csv(
                salida,
                mode="a",
                index=False,
                header=not primer_bloque_escrito,
                encoding="utf-8-sig"
            )

            primer_bloque_escrito = True

        if nro_chunk % 10 == 0:
            print(
                f"  Bloques procesados: {nro_chunk} | "
                f"Leídas: {total_leidas:,} | "
                f"Conservadas: {total_conservadas:,}"
            )

    duracion = time.time() - inicio

    print("\nRESULTADO:")
    print(f"  Filas originales: {total_leidas:,}")
    print(f"  Filas conservadas 2021-2024: {total_conservadas:,}")
    print(f"  Filas descartadas: {total_leidas - total_conservadas:,}")

    for anio in sorted(conteo_anual):
        print(
            f"  {anio}: {conteo_anual[anio]:,}"
        )

    print(
        f"  Tiempo: {duracion / 60:.2f} minutos"
    )

    print(
        f"  Archivo generado: {salida}\n"
    )

    resumen.append({
        "archivo_origen": archivo.name,
        "archivo_salida": nombre_salida,
        "filas_originales": total_leidas,
        "filas_2021_2024": total_conservadas,
        "filas_descartadas": total_leidas - total_conservadas,
        "filas_2021": conteo_anual[2021],
        "filas_2022": conteo_anual[2022],
        "filas_2023": conteo_anual[2023],
        "filas_2024": conteo_anual[2024]
    })


df_resumen = pd.DataFrame(resumen)

ruta_resumen = TABLAS / "filtrado_financieros_2021_2024_resumen.csv"

df_resumen.to_csv(
    ruta_resumen,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 90)
print("RESUMEN FINAL DEL FILTRADO")
print("=" * 90)

columnas_mostrar = [
    "archivo_salida",
    "filas_originales",
    "filas_2021_2024",
    "filas_descartadas",
    "filas_2021",
    "filas_2022",
    "filas_2023",
    "filas_2024"
]

print(
    df_resumen[columnas_mostrar]
    .to_string(index=False)
)

print("\nTOTAL DE REGISTROS CONSERVADOS:")
print(
    f"{df_resumen['filas_2021_2024'].sum():,}"
)

print("\nArchivo de control generado:")
print(ruta_resumen)

print("\nFILTRADO 2021-2024 FINALIZADO")