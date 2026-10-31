from pathlib import Path
import pandas as pd
import re

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "data" / "raw" / "insolvencia"
DESTINO = RAIZ / "data" / "processed"
TABLAS = RAIZ / "outputs" / "tablas"

DESTINO.mkdir(parents=True, exist_ok=True)
TABLAS.mkdir(parents=True, exist_ok=True)


def obtener_anio_archivo(nombre):
    coincidencia = re.search(r"20(21|22|23|24)", nombre)
    return int(coincidencia.group()) if coincidencia else None


def normalizar_nit(serie):
    return (
        serie.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\D", "", regex=True)
        .replace("", pd.NA)
    )


def normalizar_monto(serie):
    """
    Convierte los montos de insolvencia a formato numérico.

    2021-2023:
        14.816.197 -> 14816197

    2024:
        valores numéricos se conservan.
    """

    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce")

    limpio = (
        serie.astype("string")
        .str.strip()
        .str.replace("$", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", "", regex=False)
    )

    return pd.to_numeric(limpio, errors="coerce")


archivos = sorted(ORIGEN.glob("*.csv"))

print("=" * 90)
print("CONSOLIDACIÓN DE REGISTROS DE INSOLVENCIA")
print("=" * 90)
print(f"Archivos encontrados: {len(archivos)}\n")

historicos = []

for archivo in archivos:

    anio_corte = obtener_anio_archivo(archivo.name)

    print(f"Procesando corte {anio_corte}: {archivo.name}")

    df = pd.read_csv(
        archivo,
        sep=";",
        encoding="cp1252",
        low_memory=False,
        dtype={"NIT": "string"}
    )

    # Eliminar espacios en nombres de columnas
    df.columns = [str(c).strip() for c in df.columns]

    # Estandarización de nombres entre 2021-2023 y 2024
    cambios = {
        "Nro": "NRO",
        "NIT": "NIT",
        "NOMBRE": "NOMBRE",
        "REGIONAL": "REGIONAL",
        "DEPARTAMENTO": "DEPARTAMENTO",
        "CIUDAD": "CIUDAD",
        "CIIU": "CIIU",
        "MACROSECTOR": "MACROSECTOR",
        "PROCESO": "PROCESO",
        "CATEGORÍA SS": "CATEGORIA_SS",
        "CATEGORIA": "CATEGORIA_SS",
        "ACTIVOS": "ACTIVOS",
        "ACTIVO": "ACTIVOS",
        "PASIVOS": "PASIVOS",
        "PASIVO": "PASIVOS",
        "EMPLEOS": "EMPLEOS",
        "AÑO_DE_APERTURA/CELEBRACIÓN": "ANIO_APERTURA",
        "AÑO_DE_APERTURA_CELEBRACION": "ANIO_APERTURA",
        "Fecha de Generación": "FECHA_GENERACION"
    }

    df = df.rename(columns=cambios)

    # Columna basura presente en 2024
    columnas_unnamed = [
        c for c in df.columns
        if str(c).lower().startswith("unnamed")
    ]

    if columnas_unnamed:
        df = df.drop(columns=columnas_unnamed)

    # NIT normalizado
    df["NIT_NORMALIZADO"] = normalizar_nit(df["NIT"])

    # Montos normalizados
    if "ACTIVOS" in df.columns:
        df["ACTIVOS"] = normalizar_monto(df["ACTIVOS"])

    if "PASIVOS" in df.columns:
        df["PASIVOS"] = normalizar_monto(df["PASIVOS"])

    # Año de apertura
    if "ANIO_APERTURA" in df.columns:
        df["ANIO_APERTURA"] = pd.to_numeric(
            df["ANIO_APERTURA"],
            errors="coerce"
        ).astype("Int64")

    # Año del corte descargado
    df["CORTE_ANIO"] = anio_corte

    # Archivo de procedencia para trazabilidad
    df["ARCHIVO_ORIGEN"] = archivo.name

    historicos.append(df)

    print(f"  Registros procesados: {len(df):,}")
    print(f"  NIT únicos: {df['NIT_NORMALIZADO'].nunique():,}\n")


# ============================================================
# UNIÓN HISTÓRICA
# ============================================================

historial = pd.concat(
    historicos,
    ignore_index=True,
    sort=False
)

filas_antes = len(historial)

# Solo eliminamos registros COMPLETAMENTE idénticos.
# NO eliminamos por NIT porque un NIT puede aparecer
# legítimamente en distintos cortes o procesos.
historial = historial.drop_duplicates()

filas_despues = len(historial)
duplicados_exactos_eliminados = filas_antes - filas_despues


# ============================================================
# TABLA MAESTRA POR NIT
# ============================================================

base_valida = historial[
    historial["NIT_NORMALIZADO"].notna()
].copy()


def unir_anios(serie):
    valores = sorted(
        set(
            int(x)
            for x in serie.dropna()
        )
    )

    return ",".join(map(str, valores))


maestra = (
    base_valida
    .groupby("NIT_NORMALIZADO", as_index=False)
    .agg(
        PRIMER_CORTE=("CORTE_ANIO", "min"),
        ULTIMO_CORTE=("CORTE_ANIO", "max"),
        NUM_CORTES=("CORTE_ANIO", "nunique"),
        CORTES_PRESENTES=("CORTE_ANIO", unir_anios),
        ANIO_PRIMERA_APERTURA=("ANIO_APERTURA", "min"),
        ANIO_ULTIMA_APERTURA=("ANIO_APERTURA", "max")
    )
)

# Indicador de pertenencia al universo de insolvencia.
# La asignación temporal definitiva al dataset financiero
# se realizará posteriormente.
maestra["REGISTRO_INSOLVENCIA"] = 1


# ============================================================
# GUARDAR PRODUCTOS
# ============================================================

ruta_historial = DESTINO / "insolvencia_historial_estandarizado.csv"
ruta_maestra = DESTINO / "insolvencia_maestra_nit.csv"

historial.to_csv(
    ruta_historial,
    index=False,
    encoding="utf-8-sig"
)

maestra.to_csv(
    ruta_maestra,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RESUMEN DE CONTROL
# ============================================================

resumen = pd.DataFrame({
    "indicador": [
        "Registros históricos antes de deduplicación exacta",
        "Registros históricos después de deduplicación exacta",
        "Duplicados exactos eliminados",
        "NIT únicos en tabla maestra",
        "NIT con registro de insolvencia"
    ],
    "valor": [
        filas_antes,
        filas_despues,
        duplicados_exactos_eliminados,
        maestra["NIT_NORMALIZADO"].nunique(),
        maestra["REGISTRO_INSOLVENCIA"].sum()
    ]
})

ruta_resumen = TABLAS / "consolidacion_insolvencia_resumen.csv"

resumen.to_csv(
    ruta_resumen,
    index=False,
    encoding="utf-8-sig"
)


print("=" * 90)
print("RESULTADO DE LA CONSOLIDACIÓN")
print("=" * 90)

print(f"Registros históricos originales: {filas_antes:,}")
print(f"Registros históricos consolidados: {filas_despues:,}")
print(
    f"Duplicados exactos eliminados: "
    f"{duplicados_exactos_eliminados:,}"
)
print(f"NIT únicos en tabla maestra: {len(maestra):,}")

print("\nDistribución según cantidad de cortes en los que aparece el NIT:")
print(
    maestra["NUM_CORTES"]
    .value_counts()
    .sort_index()
    .to_string()
)

print("\nArchivos generados:")
print(ruta_historial)
print(ruta_maestra)
print(ruta_resumen)

print("\nCONSOLIDACIÓN DE INSOLVENCIA FINALIZADA")