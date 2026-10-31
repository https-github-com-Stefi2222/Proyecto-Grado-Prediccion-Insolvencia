from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine


# ============================================================
# CONFIGURACIÓN
# ============================================================

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "outputs" / "tablas"

TABLAS.mkdir(parents=True, exist_ok=True)

SERVIDOR = "localhost"
BASE_DATOS = "ProyectoGradoQuiebra"


cadena_odbc = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SERVIDOR};"
    f"DATABASE={BASE_DATOS};"
    "Trusted_Connection=yes;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

engine = create_engine(
    "mssql+pyodbc:///?odbc_connect="
    + quote_plus(cadena_odbc)
)


# ============================================================
# VARIABLES
# ============================================================

INDICADORES = [
    "razon_corriente",
    "prueba_acida",
    "roa",
    "roe",
    "margen_neto",
    "endeudamiento",
    "apalancamiento",
    "rotacion_activos",
    "rotacion_cartera"
]


# ============================================================
# CONSULTA
# ============================================================

consulta = """
SELECT
    nit_normalizado,
    anio_corte,
    anio_radicado,

    razon_corriente,
    prueba_acida,
    roa,
    roe,
    margen_neto,
    endeudamiento,
    apalancamiento,
    rotacion_activos,
    rotacion_cartera,

    CAST(target_insolvencia_1anio AS INT)
        AS target

FROM analytics.dataset_modelado;
"""


print("=" * 90)
print("ANÁLISIS EXPLORATORIO DEL DATASET DE MODELADO")
print("=" * 90)

print("\nLeyendo información desde SQL Server...")

df = pd.read_sql_query(
    consulta,
    engine
)

print(f"Observaciones cargadas: {len(df):,}")
print(
    f"NIT únicos: "
    f"{df['nit_normalizado'].nunique():,}"
)


# ============================================================
# CONVERSIÓN NUMÉRICA
# ============================================================

for columna in INDICADORES:
    df[columna] = pd.to_numeric(
        df[columna],
        errors="coerce"
    )

df["target"] = pd.to_numeric(
    df["target"],
    errors="coerce"
).astype(int)


# ============================================================
# BALANCE DE CLASES
# ============================================================

balance = (
    df["target"]
    .value_counts()
    .sort_index()
    .rename_axis("target")
    .reset_index(name="observaciones")
)

balance["porcentaje"] = (
    100
    * balance["observaciones"]
    / len(df)
)

print("\n" + "=" * 90)
print("BALANCE DE CLASES")
print("=" * 90)

print(
    balance.to_string(
        index=False,
        formatters={
            "porcentaje":
                lambda x: f"{x:.4f}%"
        }
    )
)


# ============================================================
# BALANCE POR COHORTE
# ============================================================

cohortes = (
    df.groupby(
        ["anio_corte", "anio_radicado", "target"]
    )
    .size()
    .reset_index(name="observaciones")
)

print("\n" + "=" * 90)
print("DISTRIBUCIÓN POR COHORTE Y CLASE")
print("=" * 90)

print(cohortes.to_string(index=False))


# ============================================================
# FALTANTES
# ============================================================

faltantes = []

for variable in INDICADORES:

    cantidad = int(
        df[variable].isna().sum()
    )

    faltantes.append({
        "variable": variable,
        "faltantes": cantidad,
        "porcentaje_faltante":
            100 * cantidad / len(df)
    })

df_faltantes = pd.DataFrame(faltantes)


print("\n" + "=" * 90)
print("FALTANTES POR INDICADOR")
print("=" * 90)

print(
    df_faltantes.to_string(
        index=False,
        formatters={
            "porcentaje_faltante":
                lambda x: f"{x:.2f}%"
        }
    )
)


# ============================================================
# ESTADÍSTICAS ROBUSTAS POR CLASE
# ============================================================

resultados = []

for variable in INDICADORES:

    for clase in [0, 1]:

        serie = (
            df.loc[
                df["target"] == clase,
                variable
            ]
            .dropna()
        )

        if serie.empty:
            continue

        resultados.append({
            "variable": variable,
            "target": clase,

            "n_validos": len(serie),

            "media": serie.mean(),
            "desviacion": serie.std(),

            "minimo": serie.min(),

            "p01": serie.quantile(0.01),
            "p05": serie.quantile(0.05),

            "q1": serie.quantile(0.25),
            "mediana": serie.median(),
            "q3": serie.quantile(0.75),

            "p95": serie.quantile(0.95),
            "p99": serie.quantile(0.99),

            "maximo": serie.max()
        })


estadisticas = pd.DataFrame(resultados)


# ============================================================
# TABLA COMPACTA DE MEDIANAS
# ============================================================

medianas = (
    estadisticas[
        [
            "variable",
            "target",
            "n_validos",
            "q1",
            "mediana",
            "q3"
        ]
    ]
    .copy()
)

tabla_medianas = medianas.pivot(
    index="variable",
    columns="target",
    values="mediana"
)

tabla_medianas.columns = [
    "mediana_target_0",
    "mediana_target_1"
]

tabla_medianas = (
    tabla_medianas
    .reset_index()
)


print("\n" + "=" * 90)
print("MEDIANAS DE INDICADORES POR CLASE")
print("=" * 90)

print(
    tabla_medianas.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# SOLAPAMIENTO DE NIT ENTRE COHORTES
# ============================================================

nits_2021 = set(
    df.loc[
        df["anio_corte"] == 2021,
        "nit_normalizado"
    ]
)

nits_2022 = set(
    df.loc[
        df["anio_corte"] == 2022,
        "nit_normalizado"
    ]
)

nits_compartidos = (
    nits_2021.intersection(nits_2022)
)


print("\n" + "=" * 90)
print("SOLAPAMIENTO DE EMPRESAS ENTRE COHORTES")
print("=" * 90)

print(
    f"NIT cohorte 2021: "
    f"{len(nits_2021):,}"
)

print(
    f"NIT cohorte 2022: "
    f"{len(nits_2022):,}"
)

print(
    f"NIT presentes en ambas cohortes: "
    f"{len(nits_compartidos):,}"
)


# ============================================================
# GUARDAR
# ============================================================

balance.to_csv(
    TABLAS / "eda_balance_clases.csv",
    index=False,
    encoding="utf-8-sig"
)

cohortes.to_csv(
    TABLAS / "eda_balance_por_cohorte.csv",
    index=False,
    encoding="utf-8-sig"
)

df_faltantes.to_csv(
    TABLAS / "eda_faltantes_indicadores.csv",
    index=False,
    encoding="utf-8-sig"
)

estadisticas.to_csv(
    TABLAS / "eda_estadisticas_por_clase.csv",
    index=False,
    encoding="utf-8-sig"
)

tabla_medianas.to_csv(
    TABLAS / "eda_medianas_por_clase.csv",
    index=False,
    encoding="utf-8-sig"
)


print("\nArchivos generados:")

for nombre in [
    "eda_balance_clases.csv",
    "eda_balance_por_cohorte.csv",
    "eda_faltantes_indicadores.csv",
    "eda_estadisticas_por_clase.csv",
    "eda_medianas_por_clase.csv"
]:
    print(TABLAS / nombre)


print("\nANÁLISIS EXPLORATORIO FINALIZADO")