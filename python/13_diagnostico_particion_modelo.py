from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine


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


consulta = """
SELECT
    nit_normalizado,
    anio_corte,
    CAST(target_insolvencia_1anio AS INT) AS target
FROM analytics.dataset_modelado;
"""


df = pd.read_sql_query(
    consulta,
    engine
)


train = df[
    df["anio_corte"] == 2021
].copy()

test = df[
    df["anio_corte"] == 2022
].copy()


nits_train = set(
    train["nit_normalizado"]
)

test["empresa_vista_en_train"] = (
    test["nit_normalizado"]
    .isin(nits_train)
)


def mostrar_resumen(nombre, datos):

    total = len(datos)

    positivos = int(
        datos["target"].sum()
    )

    negativos = (
        total - positivos
    )

    porcentaje = (
        100 * positivos / total
        if total > 0
        else 0
    )

    print(nombre)
    print(
        f"  Observaciones: {total:,}"
    )
    print(
        f"  NIT únicos: "
        f"{datos['nit_normalizado'].nunique():,}"
    )
    print(
        f"  Positivos: {positivos:,}"
    )
    print(
        f"  Negativos: {negativos:,}"
    )
    print(
        f"  % positivos: {porcentaje:.4f}%"
    )
    print()


print("=" * 80)
print("DIAGNÓSTICO DE PARTICIÓN TEMPORAL")
print("=" * 80)

mostrar_resumen(
    "ENTRENAMIENTO - COHORTE 2021",
    train
)

mostrar_resumen(
    "PRUEBA TEMPORAL COMPLETA - COHORTE 2022",
    test
)


test_vistas = test[
    test["empresa_vista_en_train"]
].copy()

test_nuevas = test[
    ~test["empresa_vista_en_train"]
].copy()


print("=" * 80)
print("SOLAPAMIENTO DEL TEST CON ENTRENAMIENTO")
print("=" * 80)

mostrar_resumen(
    "TEST - EMPRESAS YA VISTAS",
    test_vistas
)

mostrar_resumen(
    "TEST - EMPRESAS NO VISTAS",
    test_nuevas
)


print("=" * 80)
print("DISTRIBUCIÓN DE POSITIVOS EN TEST")
print("=" * 80)

resumen = (
    test.groupby(
        "empresa_vista_en_train"
    )["target"]
    .agg(
        observaciones="size",
        positivos="sum"
    )
    .reset_index()
)

resumen["negativos"] = (
    resumen["observaciones"]
    - resumen["positivos"]
)

resumen["porcentaje_positivos"] = (
    100
    * resumen["positivos"]
    / resumen["observaciones"]
)

print(
    resumen.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)

print(
    "\nDIAGNÓSTICO DE PARTICIÓN FINALIZADO"
)