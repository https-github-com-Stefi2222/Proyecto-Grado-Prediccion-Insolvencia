from pathlib import Path
import pandas as pd
import re

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "raw" / "insolvencia"
OUTPUT = RAIZ / "outputs" / "tablas"

OUTPUT.mkdir(parents=True, exist_ok=True)


def obtener_anio(nombre_archivo):
    coincidencia = re.search(r"20(21|22|23|24)", nombre_archivo)
    return int(coincidencia.group()) if coincidencia else None


def normalizar_nit(serie):
    """
    Conserva el NIT como texto y elimina puntos,
    guiones, espacios u otros caracteres.
    """
    return (
        serie.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\D", "", regex=True)
        .replace("", pd.NA)
    )


archivos = sorted(CARPETA.glob("*.csv"))

print("=" * 85)
print("ANÁLISIS DE REGISTROS DE INSOLVENCIA 2021-2024")
print("=" * 85)
print(f"Archivos encontrados: {len(archivos)}\n")

datos = {}
resumen = []

for archivo in archivos:

    anio = obtener_anio(archivo.name)

    df = pd.read_csv(
        archivo,
        sep=";",
        encoding="cp1252",
        low_memory=False,
        dtype={"NIT": "string"}
    )

    # Limpiar nombres de columnas
    df.columns = [str(c).strip() for c in df.columns]

    # Normalizar identificador
    df["NIT_NORMALIZADO"] = normalizar_nit(df["NIT"])

    filas = len(df)
    nit_validos = df["NIT_NORMALIZADO"].notna().sum()
    nit_unicos = df["NIT_NORMALIZADO"].nunique(dropna=True)
    nit_duplicados = df["NIT_NORMALIZADO"].duplicated(keep=False).sum()
    duplicados_exactos = df.duplicated().sum()

    datos[anio] = df

    resumen.append({
        "anio_corte": anio,
        "archivo": archivo.name,
        "filas": filas,
        "nit_validos": nit_validos,
        "nit_unicos": nit_unicos,
        "registros_con_nit_repetido": nit_duplicados,
        "duplicados_exactos": duplicados_exactos
    })

    print(f"Corte {anio}")
    print(f"  Filas: {filas:,}")
    print(f"  NIT válidos: {nit_validos:,}")
    print(f"  NIT únicos: {nit_unicos:,}")
    print(f"  Registros con NIT repetido: {nit_duplicados:,}")
    print(f"  Duplicados exactos: {duplicados_exactos:,}")
    print()


# --------------------------------------------------
# Comparación entre años
# --------------------------------------------------

anios = sorted(datos.keys())

matriz = pd.DataFrame(index=anios, columns=anios, dtype="int64")

for anio_a in anios:

    nits_a = set(
        datos[anio_a]["NIT_NORMALIZADO"]
        .dropna()
        .unique()
    )

    for anio_b in anios:

        nits_b = set(
            datos[anio_b]["NIT_NORMALIZADO"]
            .dropna()
            .unique()
        )

        matriz.loc[anio_a, anio_b] = len(nits_a.intersection(nits_b))


print("=" * 85)
print("NIT COMPARTIDOS ENTRE CORTES")
print("=" * 85)
print(matriz.to_string())
print()


# --------------------------------------------------
# NIT nuevos respecto a cortes anteriores
# --------------------------------------------------

vistos = set()
evolucion = []

print("=" * 85)
print("EVOLUCIÓN DE NIT ENTRE CORTES")
print("=" * 85)

for anio in anios:

    actuales = set(
        datos[anio]["NIT_NORMALIZADO"]
        .dropna()
        .unique()
    )

    nuevos = actuales - vistos
    repetidos = actuales.intersection(vistos)

    evolucion.append({
        "anio": anio,
        "nit_unicos_corte": len(actuales),
        "nit_nuevos_respecto_cortes_anteriores": len(nuevos),
        "nit_ya_presentes_en_cortes_anteriores": len(repetidos)
    })

    print(
        f"{anio}: "
        f"{len(actuales):,} NIT únicos | "
        f"{len(nuevos):,} nuevos | "
        f"{len(repetidos):,} ya observados"
    )

    vistos.update(actuales)


print()
print(f"NIT únicos acumulados 2021-2024: {len(vistos):,}")


# --------------------------------------------------
# Guardar resultados
# --------------------------------------------------

df_resumen = pd.DataFrame(resumen)
df_evolucion = pd.DataFrame(evolucion)

df_resumen.to_csv(
    OUTPUT / "insolvencia_resumen_anual.csv",
    index=False,
    encoding="utf-8-sig"
)

matriz.to_csv(
    OUTPUT / "insolvencia_matriz_coincidencias.csv",
    encoding="utf-8-sig"
)

df_evolucion.to_csv(
    OUTPUT / "insolvencia_evolucion_nit.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nArchivos generados:")

print(
    OUTPUT / "insolvencia_resumen_anual.csv"
)

print(
    OUTPUT / "insolvencia_matriz_coincidencias.csv"
)

print(
    OUTPUT / "insolvencia_evolucion_nit.csv"
)

print("\nANÁLISIS DE INSOLVENCIA FINALIZADO")