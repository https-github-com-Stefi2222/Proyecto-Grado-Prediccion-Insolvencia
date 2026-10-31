from pathlib import Path
import pandas as pd
import csv
import time

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
OUTPUT = RAIZ / "outputs" / "tablas"

OUTPUT.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 250_000


def detectar_configuracion_csv(ruta):
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


def obtener_anio(valor):
    if pd.isna(valor):
        return None

    texto = str(valor)

    for anio in range(2000, 2031):
        if str(anio) in texto:
            return anio

    return None


archivos = sorted(RAW.rglob("*.csv"))

resumen = []
detalle_nulos = []

print("=" * 90)
print("PERFILAMIENTO DE CALIDAD - PROYECTO DE GRADO")
print("=" * 90)
print(f"Archivos encontrados: {len(archivos)}")
print(f"Procesamiento por bloques de: {CHUNK_SIZE:,} filas\n")


for numero, archivo in enumerate(archivos, start=1):

    inicio = time.time()

    print("=" * 90)
    print(f"[{numero}/{len(archivos)}] {archivo.name}")
    print("=" * 90)

    encoding, separador = detectar_configuracion_csv(archivo)

    total_filas = 0
    columnas = None
    nulos = None
    nit_unicos = set()
    anos = set()
    error_archivo = None

    try:
        lector = pd.read_csv(
            archivo,
            sep=separador,
            encoding=encoding,
            chunksize=CHUNK_SIZE,
            low_memory=False
        )

        for nro_chunk, chunk in enumerate(lector, start=1):

            total_filas += len(chunk)

            if columnas is None:
                columnas = list(chunk.columns)
                nulos = pd.Series(0, index=columnas, dtype="int64")

            nulos = nulos.add(chunk.isna().sum(), fill_value=0)

            # NIT únicos
            if "NIT" in chunk.columns:
                serie_nit = (
                    chunk["NIT"]
                    .dropna()
                    .astype(str)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", "", regex=False)
                    .str.strip()
                )

                nit_unicos.update(serie_nit.tolist())

            # Años
            columnas_fecha = [
                c for c in chunk.columns
                if c.upper() in ["FECHA_CORTE", "PERIODO",
                                 "AÑO_DE_APERTURA/CELEBRACIÓN",
                                 "AÑO_DE_APERTURA_CELEBRACION"]
            ]

            for columna in columnas_fecha:
                valores = chunk[columna].dropna()

                for valor in valores:
                    anio = obtener_anio(valor)
                    if anio is not None:
                        anos.add(anio)

            if nro_chunk % 10 == 0:
                print(
                    f"   Bloques procesados: {nro_chunk} | "
                    f"Filas acumuladas: {total_filas:,}"
                )

        duracion = time.time() - inicio

        print(f"\nFilas totales: {total_filas:,}")
        print(f"Columnas: {len(columnas)}")
        print(f"NIT únicos detectados: {len(nit_unicos):,}")
        print(
            "Años detectados: "
            + (", ".join(map(str, sorted(anos))) if anos else "No determinados")
        )
        print(f"Tiempo: {duracion / 60:.2f} minutos")

        resumen.append({
            "archivo": archivo.name,
            "tamano_gb": round(archivo.stat().st_size / (1024 ** 3), 3),
            "filas": total_filas,
            "columnas": len(columnas),
            "nit_unicos": len(nit_unicos),
            "anos_detectados": ", ".join(map(str, sorted(anos))),
            "encoding": encoding,
            "separador": separador,
            "estado": "OK"
        })

        for columna in columnas:

            cantidad_nulos = int(nulos[columna])
            porcentaje_nulos = (
                cantidad_nulos / total_filas * 100
                if total_filas > 0
                else 0
            )

            detalle_nulos.append({
                "archivo": archivo.name,
                "columna": columna,
                "nulos": cantidad_nulos,
                "porcentaje_nulos": round(porcentaje_nulos, 4)
            })

    except Exception as e:

        error_archivo = str(e)

        print(f"\nERROR: {error_archivo}")

        resumen.append({
            "archivo": archivo.name,
            "tamano_gb": round(archivo.stat().st_size / (1024 ** 3), 3),
            "filas": total_filas,
            "columnas": len(columnas) if columnas else 0,
            "nit_unicos": len(nit_unicos),
            "anos_detectados": ", ".join(map(str, sorted(anos))),
            "encoding": encoding,
            "separador": separador,
            "estado": f"ERROR: {error_archivo}"
        })

    print()


df_resumen = pd.DataFrame(resumen)
df_nulos = pd.DataFrame(detalle_nulos)

ruta_resumen = OUTPUT / "perfilamiento_resumen.csv"
ruta_nulos = OUTPUT / "perfilamiento_nulos.csv"

df_resumen.to_csv(
    ruta_resumen,
    index=False,
    encoding="utf-8-sig"
)

df_nulos.to_csv(
    ruta_nulos,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 90)
print("RESUMEN FINAL")
print("=" * 90)

if not df_resumen.empty:
    print(
        df_resumen[
            [
                "archivo",
                "filas",
                "columnas",
                "nit_unicos",
                "anos_detectados",
                "estado"
            ]
        ].to_string(index=False)
    )

print("\nArchivos generados:")
print(ruta_resumen)
print(ruta_nulos)

print("\nPERFILAMIENTO DE CALIDAD FINALIZADO")