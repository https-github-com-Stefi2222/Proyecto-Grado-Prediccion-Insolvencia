from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd

from sqlalchemy import create_engine

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    balanced_accuracy_score,
    confusion_matrix
)


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
# VARIABLES DEL MODELO
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
# CONSULTAR DATASET
# ============================================================

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

    CAST(target_insolvencia_1anio AS INT)
        AS target

FROM analytics.dataset_modelado;
"""


print("=" * 90)
print("MODELO BASE - REGRESIÓN LOGÍSTICA")
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


df["target"] = pd.to_numeric(
    df["target"],
    errors="coerce"
).astype(int)


# ============================================================
# PARTICIÓN TEMPORAL
# ============================================================

train = df[
    df["anio_corte"] == 2021
].copy()

test = df[
    df["anio_corte"] == 2022
].copy()


nits_train = set(
    train["nit_normalizado"]
)

test_nuevas = test[
    ~test["nit_normalizado"].isin(
        nits_train
    )
].copy()


print("\nPARTICIÓN:")

print(
    f"Train 2021: {len(train):,} | "
    f"positivos: {train['target'].sum():,}"
)

print(
    f"Test 2022: {len(test):,} | "
    f"positivos: {test['target'].sum():,}"
)

print(
    f"Test empresas nuevas: {len(test_nuevas):,} | "
    f"positivos: {test_nuevas['target'].sum():,}"
)


# ============================================================
# PARÁMETROS CALCULADOS SOLO EN TRAIN
# ============================================================

parametros = []

for variable in INDICADORES:

    serie = train[variable].dropna()

    parametros.append({
        "variable": variable,

        "mediana":
            serie.median(),

        "p01":
            serie.quantile(0.01),

        "p99":
            serie.quantile(0.99)
    })


df_parametros = (
    pd.DataFrame(parametros)
    .set_index("variable")
)


# ============================================================
# FUNCIÓN DE PREPROCESAMIENTO
# ============================================================

def preparar(datos):

    salida = pd.DataFrame(
        index=datos.index
    )

    for variable in INDICADORES:

        serie = datos[
            variable
        ].copy()

        # Indicador de faltante antes de imputar
        salida[
            f"{variable}_faltante"
        ] = (
            serie.isna()
            .astype(int)
        )

        mediana = (
            df_parametros
            .loc[variable, "mediana"]
        )

        p01 = (
            df_parametros
            .loc[variable, "p01"]
        )

        p99 = (
            df_parametros
            .loc[variable, "p99"]
        )

        # Imputación
        serie = serie.fillna(
            mediana
        )

        # Winsorización usando límites
        # calculados exclusivamente con train
        serie = serie.clip(
            lower=p01,
            upper=p99
        )

        salida[variable] = serie

    return salida


X_train = preparar(train)
X_test = preparar(test)
X_test_nuevas = preparar(test_nuevas)

y_train = train["target"]
y_test = test["target"]
y_test_nuevas = test_nuevas["target"]


# ============================================================
# ESCALADO
# ============================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(
    X_train
)

X_test_scaled = scaler.transform(
    X_test
)

X_test_nuevas_scaled = scaler.transform(
    X_test_nuevas
)


# ============================================================
# MODELO
# ============================================================

modelo = LogisticRegression(
    class_weight="balanced",
    max_iter=5000,
    random_state=42
)

modelo.fit(
    X_train_scaled,
    y_train
)


# ============================================================
# EVALUACIÓN
# ============================================================

def evaluar(
    nombre,
    X,
    y
):

    probabilidades = (
        modelo.predict_proba(X)[:, 1]
    )

    predicciones = (
        probabilidades >= 0.5
    ).astype(int)

    tn, fp, fn, tp = (
        confusion_matrix(
            y,
            predicciones,
            labels=[0, 1]
        ).ravel()
    )

    prevalencia = (
        y.mean()
    )

    roc_auc = roc_auc_score(
        y,
        probabilidades
    )

    pr_auc = average_precision_score(
        y,
        probabilidades
    )

    precision = precision_score(
        y,
        predicciones,
        zero_division=0
    )

    recall = recall_score(
        y,
        predicciones,
        zero_division=0
    )

    f1 = f1_score(
        y,
        predicciones,
        zero_division=0
    )

    especificidad = (
        tn / (tn + fp)
        if (tn + fp) > 0
        else np.nan
    )

    balanced_accuracy = (
        balanced_accuracy_score(
            y,
            predicciones
        )
    )

    lift_pr = (
        pr_auc / prevalencia
        if prevalencia > 0
        else np.nan
    )

    resultado = {
        "conjunto": nombre,

        "observaciones": len(y),
        "positivos_reales": int(y.sum()),

        "prevalencia": prevalencia,

        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "baseline_pr_auc": prevalencia,
        "lift_pr_auc": lift_pr,

        "precision": precision,
        "recall": recall,
        "f1": f1,

        "especificidad": especificidad,
        "balanced_accuracy":
            balanced_accuracy,

        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),

        "predichos_positivos":
            int(predicciones.sum())
    }

    return resultado


resultados = []

resultados.append(
    evaluar(
        "TRAIN_2021",
        X_train_scaled,
        y_train
    )
)

resultados.append(
    evaluar(
        "TEST_TEMPORAL_2022",
        X_test_scaled,
        y_test
    )
)

resultados.append(
    evaluar(
        "TEST_EMPRESAS_NUEVAS",
        X_test_nuevas_scaled,
        y_test_nuevas
    )
)


metricas = pd.DataFrame(
    resultados
)


# ============================================================
# MOSTRAR MÉTRICAS
# ============================================================

print("\n" + "=" * 90)
print("MÉTRICAS DEL MODELO BASE")
print("=" * 90)

columnas_mostrar = [
    "conjunto",
    "observaciones",
    "positivos_reales",
    "roc_auc",
    "pr_auc",
    "baseline_pr_auc",
    "lift_pr_auc",
    "precision",
    "recall",
    "f1",
    "especificidad",
    "balanced_accuracy"
]

print(
    metricas[
        columnas_mostrar
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# MATRIZ DE CONFUSIÓN
# ============================================================

print("\n" + "=" * 90)
print("MATRICES DE CONFUSIÓN")
print("=" * 90)

for _, fila in metricas.iterrows():

    print(
        f"\n{fila['conjunto']}"
    )

    print(
        f"TN: {int(fila['tn']):,} | "
        f"FP: {int(fila['fp']):,}"
    )

    print(
        f"FN: {int(fila['fn']):,} | "
        f"TP: {int(fila['tp']):,}"
    )

    print(
        f"Predichos positivos: "
        f"{int(fila['predichos_positivos']):,}"
    )


# ============================================================
# COEFICIENTES DEL MODELO
# ============================================================

coeficientes = pd.DataFrame({
    "variable":
        X_train.columns,

    "coeficiente":
        modelo.coef_[0]
})

coeficientes[
    "coeficiente_absoluto"
] = (
    coeficientes[
        "coeficiente"
    ].abs()
)

coeficientes = (
    coeficientes
    .sort_values(
        "coeficiente_absoluto",
        ascending=False
    )
)


print("\n" + "=" * 90)
print("COEFICIENTES ESTANDARIZADOS")
print("=" * 90)

print(
    coeficientes[
        [
            "variable",
            "coeficiente"
        ]
    ]
    .head(18)
    .to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# GUARDAR RESULTADOS
# ============================================================

metricas.to_csv(
    TABLAS /
    "modelo_logistico_metricas.csv",
    index=False,
    encoding="utf-8-sig"
)

coeficientes.to_csv(
    TABLAS /
    "modelo_logistico_coeficientes.csv",
    index=False,
    encoding="utf-8-sig"
)

df_parametros.reset_index().to_csv(
    TABLAS /
    "modelo_logistico_preprocesamiento.csv",
    index=False,
    encoding="utf-8-sig"
)


print("\nArchivos generados:")

print(
    TABLAS /
    "modelo_logistico_metricas.csv"
)

print(
    TABLAS /
    "modelo_logistico_coeficientes.csv"
)

print(
    TABLAS /
    "modelo_logistico_preprocesamiento.csv"
)

print(
    "\nMODELO LOGÍSTICO BASE FINALIZADO"
)