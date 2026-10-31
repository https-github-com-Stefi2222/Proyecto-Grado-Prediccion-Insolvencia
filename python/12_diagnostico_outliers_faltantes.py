from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine


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


consulta = """
SELECT
    nit_normalizado,
    anio_corte,

    razon_corriente,
    prueba_acida,
    roa,
    roe,
    margen_neto,
    endeudamiento,
    apalancamiento,
    rotacion_activos,
    rotacion_cartera,

    CAST(target_insolvencia_1anio AS INT) AS target

FROM analytics.dataset_modelado;
"""


print("=" * 90)
print("DIAGNÓSTICO DE OUTLIERS Y FALTANTES POR CLASE")
print("=" * 90)

df = pd.read_sql_query(
    consulta,
    engine
)

for variable in INDICADORES:
    df[variable] = pd.to_numeric(
        df[variable],
        errors="coerce"
    )


# ============================================================
# FALTANTES POR CLASE
# ============================================================

faltantes = []

for variable in INDICADORES:

    for clase in [0, 1]:

        subconjunto = df[
            df["target"] == clase
        ]

        cantidad = int(
            subconjunto[variable]
            .isna()
            .sum()
        )

        total = len(subconjunto)

        faltantes.append({
            "variable": variable,
            "target": clase,
            "total_clase": total,
            "faltantes": cantidad,
            "porcentaje_faltante":
                100 * cantidad / total
        })


df_faltantes = pd.DataFrame(
    faltantes
)

print("\n" + "=" * 90)
print("FALTANTES POR CLASE")
print("=" * 90)

tabla_faltantes = (
    df_faltantes
    .pivot(
        index="variable",
        columns="target",
        values="porcentaje_faltante"
    )
    .reset_index()
)

tabla_faltantes.columns = [
    "variable",
    "faltante_target_0_pct",
    "faltante_target_1_pct"
]

print(
    tabla_faltantes.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)


# ============================================================
# PERCENTILES Y OUTLIERS
# ============================================================

resultados = []

for variable in INDICADORES:

    serie_total = (
        df[variable]
        .dropna()
    )

    if serie_total.empty:
        continue

    p01 = serie_total.quantile(0.01)
    p99 = serie_total.quantile(0.99)

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

        extremos = (
            (serie < p01)
            | (serie > p99)
        )

        resultados.append({
            "variable": variable,
            "target": clase,

            "n_validos": len(serie),

            "p01_global": p01,
            "mediana": serie.median(),
            "p99_global": p99,

            "minimo": serie.min(),
            "maximo": serie.max(),

            "fuera_p01_p99":
                int(extremos.sum()),

            "porcentaje_fuera_p01_p99":
                100 * extremos.mean()
        })


df_outliers = pd.DataFrame(
    resultados
)


print("\n" + "=" * 90)
print("OBSERVACIONES FUERA DEL PERCENTIL 1-99")
print("=" * 90)

tabla_outliers = (
    df_outliers[
        [
            "variable",
            "target",
            "n_validos",
            "mediana",
            "fuera_p01_p99",
            "porcentaje_fuera_p01_p99"
        ]
    ]
)

print(
    tabla_outliers.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# RANGOS P01-P99
# ============================================================

rangos = []

for variable in INDICADORES:

    serie = df[variable].dropna()

    rangos.append({
        "variable": variable,
        "p01": serie.quantile(0.01),
        "p05": serie.quantile(0.05),
        "mediana": serie.median(),
        "p95": serie.quantile(0.95),
        "p99": serie.quantile(0.99),
        "minimo": serie.min(),
        "maximo": serie.max()
    })


df_rangos = pd.DataFrame(rangos)

print("\n" + "=" * 90)
print("RANGOS Y PERCENTILES DE LOS INDICADORES")
print("=" * 90)

print(
    df_rangos.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# GUARDAR
# ============================================================

tabla_faltantes.to_csv(
    TABLAS /
    "eda_faltantes_por_clase.csv",
    index=False,
    encoding="utf-8-sig"
)

df_outliers.to_csv(
    TABLAS /
    "eda_outliers_por_clase.csv",
    index=False,
    encoding="utf-8-sig"
)

df_rangos.to_csv(
    TABLAS /
    "eda_percentiles_indicadores.csv",
    index=False,
    encoding="utf-8-sig"
)


print("\nArchivos generados:")

print(
    TABLAS /
    "eda_faltantes_por_clase.csv"
)

print(
    TABLAS /
    "eda_outliers_por_clase.csv"
)

print(
    TABLAS /
    "eda_percentiles_indicadores.csv"
)

print(
    "\nDIAGNÓSTICO DE OUTLIERS "
    "Y FALTANTES FINALIZADO"
)