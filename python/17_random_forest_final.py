from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd

from sqlalchemy import create_engine

from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    f1_score,
    fbeta_score,
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
# WINSORIZADOR
# Aprende P1-P99 solamente sobre los datos usados en fit()
# ============================================================

class PercentileClipper(
    BaseEstimator,
    TransformerMixin
):

    def __init__(self, lower=0.01, upper=0.99):
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):

        X_df = pd.DataFrame(
            X,
            columns=getattr(
                X,
                "columns",
                None
            )
        ).copy()

        self.lower_bounds_ = X_df.quantile(
            self.lower
        )

        self.upper_bounds_ = X_df.quantile(
            self.upper
        )

        return self

    def transform(self, X):

        X_df = pd.DataFrame(
            X,
            columns=getattr(
                X,
                "columns",
                None
            )
        ).copy()

        return X_df.clip(
            lower=self.lower_bounds_,
            upper=self.upper_bounds_,
            axis=1
        )


# ============================================================
# MODELO
# ============================================================

def crear_modelo():

    return Pipeline([
        (
            "clipper",
            PercentileClipper(
                lower=0.01,
                upper=0.99
            )
        ),
        (
            "imputer",
            SimpleImputer(
                strategy="median",
                add_indicator=True
            )
        ),
        (
            "modelo",
            RandomForestClassifier(
                n_estimators=500,
                max_depth=8,
                min_samples_leaf=10,
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=42
            )
        )
    ])


# ============================================================
# CARGAR DATOS
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

    CAST(
        target_insolvencia_1anio AS INT
    ) AS target

FROM analytics.dataset_modelado;
"""


print("=" * 90)
print("RANDOM FOREST FINAL - VALIDACIÓN TEMPORAL")
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


df["target"] = (
    pd.to_numeric(
        df["target"],
        errors="coerce"
    )
    .astype(int)
)


train = df[
    df["anio_corte"] == 2021
].copy()

test = df[
    df["anio_corte"] == 2022
].copy()


X_train = train[INDICADORES]
y_train = train["target"]

X_test = test[INDICADORES]
y_test = test["target"]


# Empresas nuevas en 2022
nits_train = set(
    train["nit_normalizado"]
)

mascara_nuevas = (
    ~test["nit_normalizado"]
    .isin(nits_train)
)

test_nuevas = test[
    mascara_nuevas
].copy()

X_test_nuevas = (
    test_nuevas[INDICADORES]
)

y_test_nuevas = (
    test_nuevas["target"]
)


print("\nPARTICIÓN:")

print(
    f"Train 2021: {len(train):,} | "
    f"positivos: {int(y_train.sum()):,}"
)

print(
    f"Test 2022: {len(test):,} | "
    f"positivos: {int(y_test.sum()):,}"
)

print(
    f"Test empresas nuevas: "
    f"{len(test_nuevas):,} | "
    f"positivos: "
    f"{int(y_test_nuevas.sum()):,}"
)


# ============================================================
# PREDICCIONES OUT-OF-FOLD EN TRAIN
# PARA ELEGIR UMBRAL SIN MIRAR TEST
# ============================================================

print("\nGenerando predicciones OOF en cohorte 2021...")

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

prob_oof = np.zeros(
    len(train),
    dtype=float
)


for fold, (idx_fit, idx_val) in enumerate(
    cv.split(X_train, y_train),
    start=1
):

    modelo_fold = crear_modelo()

    modelo_fold.fit(
        X_train.iloc[idx_fit],
        y_train.iloc[idx_fit]
    )

    prob_oof[idx_val] = (
        modelo_fold.predict_proba(
            X_train.iloc[idx_val]
        )[:, 1]
    )

    print(
        f"  Fold {fold} finalizado"
    )


# ============================================================
# SELECCIONAR UMBRAL CON F1 SOBRE OOF
# ============================================================

precision_curve, recall_curve, thresholds = (
    precision_recall_curve(
        y_train,
        prob_oof
    )
)

# precision y recall tienen un elemento extra
precision_t = precision_curve[:-1]
recall_t = recall_curve[:-1]

f1_values = (
    2
    * precision_t
    * recall_t
    /
    (
        precision_t
        + recall_t
        + 1e-15
    )
)

mejor_idx = int(
    np.nanargmax(
        f1_values
    )
)

umbral_f1 = float(
    thresholds[mejor_idx]
)


print("\n" + "=" * 90)
print("UMBRAL SELECCIONADO SOLO CON TRAIN OOF")
print("=" * 90)

print(
    f"Umbral F1: {umbral_f1:.6f}"
)

print(
    f"Precision OOF en ese umbral: "
    f"{precision_t[mejor_idx]:.4f}"
)

print(
    f"Recall OOF en ese umbral: "
    f"{recall_t[mejor_idx]:.4f}"
)

print(
    f"F1 OOF: "
    f"{f1_values[mejor_idx]:.4f}"
)


# ============================================================
# ENTRENAR MODELO FINAL CON TODO 2021
# ============================================================

print("\nEntrenando Random Forest final...")

modelo_final = crear_modelo()

modelo_final.fit(
    X_train,
    y_train
)


# ============================================================
# FUNCIÓN DE EVALUACIÓN
# ============================================================

def evaluar(
    nombre,
    X,
    y,
    umbral
):

    probabilidades = (
        modelo_final.predict_proba(
            X
        )[:, 1]
    )

    predicciones = (
        probabilidades >= umbral
    ).astype(int)

    tn, fp, fn, tp = (
        confusion_matrix(
            y,
            predicciones,
            labels=[0, 1]
        ).ravel()
    )

    prevalencia = float(
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

    f2 = fbeta_score(
        y,
        predicciones,
        beta=2,
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


    return {
        "conjunto": nombre,

        "observaciones": len(y),
        "positivos_reales":
            int(y.sum()),

        "prevalencia":
            prevalencia,

        "roc_auc":
            roc_auc,

        "pr_auc":
            pr_auc,

        "baseline_pr_auc":
            prevalencia,

        "lift_pr_auc":
            lift_pr,

        "umbral":
            umbral,

        "precision":
            precision,

        "recall":
            recall,

        "f1":
            f1,

        "f2":
            f2,

        "especificidad":
            especificidad,

        "balanced_accuracy":
            balanced_accuracy,

        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),

        "predichos_positivos":
            int(predicciones.sum())
    }, probabilidades


# ============================================================
# EVALUAR
# ============================================================

resultado_test, prob_test = evaluar(
    "TEST_TEMPORAL_2022",
    X_test,
    y_test,
    umbral_f1
)

resultado_nuevas, prob_nuevas = evaluar(
    "TEST_EMPRESAS_NUEVAS",
    X_test_nuevas,
    y_test_nuevas,
    umbral_f1
)


metricas = pd.DataFrame([
    resultado_test,
    resultado_nuevas
])


print("\n" + "=" * 90)
print("EVALUACIÓN FINAL RANDOM FOREST")
print("=" * 90)

columnas = [
    "conjunto",
    "observaciones",
    "positivos_reales",
    "roc_auc",
    "pr_auc",
    "baseline_pr_auc",
    "lift_pr_auc",
    "umbral",
    "precision",
    "recall",
    "f1",
    "f2",
    "especificidad",
    "balanced_accuracy"
]

print(
    metricas[
        columnas
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# MATRICES DE CONFUSIÓN
# ============================================================

print("\n" + "=" * 90)
print("MATRICES DE CONFUSIÓN - UMBRAL BLOQUEADO")
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
# CAPTURA DE CASOS POSITIVOS EN TOP X% DE RIESGO
# ============================================================

def tabla_top_riesgo(
    y,
    probabilidades,
    nombre
):

    temporal = pd.DataFrame({
        "target":
            np.asarray(y),
        "probabilidad":
            probabilidades
    })

    temporal = (
        temporal
        .sort_values(
            "probabilidad",
            ascending=False
        )
        .reset_index(drop=True)
    )

    positivos_totales = int(
        temporal["target"].sum()
    )

    filas = []

    for porcentaje in [
        0.01,
        0.05,
        0.10,
        0.20
    ]:

        n = max(
            1,
            int(
                np.ceil(
                    len(temporal)
                    * porcentaje
                )
            )
        )

        top = temporal.head(n)

        positivos_top = int(
            top["target"].sum()
        )

        captura = (
            100
            * positivos_top
            / positivos_totales
            if positivos_totales > 0
            else np.nan
        )

        precision_top = (
            100
            * positivos_top
            / n
        )

        filas.append({
            "conjunto": nombre,
            "top_porcentaje":
                int(porcentaje * 100),
            "empresas_top": n,
            "positivos_capturados":
                positivos_top,
            "captura_positivos_pct":
                captura,
            "precision_top_pct":
                precision_top
        })

    return pd.DataFrame(
        filas
    )


top_test = tabla_top_riesgo(
    y_test,
    prob_test,
    "TEST_TEMPORAL_2022"
)

top_nuevas = tabla_top_riesgo(
    y_test_nuevas,
    prob_nuevas,
    "TEST_EMPRESAS_NUEVAS"
)

tabla_top = pd.concat(
    [
        top_test,
        top_nuevas
    ],
    ignore_index=True
)


print("\n" + "=" * 90)
print("CAPTURA DE INSOLVENCIAS EN EMPRESAS DE MAYOR RIESGO")
print("=" * 90)

print(
    tabla_top.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)


# ============================================================
# IMPORTANCIA DE VARIABLES
# ============================================================

imputer = (
    modelo_final
    .named_steps["imputer"]
)

rf = (
    modelo_final
    .named_steps["modelo"]
)

nombres_variables = (
    imputer.get_feature_names_out(
        INDICADORES
    )
)

importancias = pd.DataFrame({
    "variable":
        nombres_variables,

    "importancia":
        rf.feature_importances_
})

importancias = (
    importancias
    .sort_values(
        "importancia",
        ascending=False
    )
)


print("\n" + "=" * 90)
print("IMPORTANCIA DE VARIABLES - RANDOM FOREST")
print("=" * 90)

print(
    importancias
    .head(15)
    .to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# GUARDAR
# ============================================================

metricas.to_csv(
    TABLAS /
    "random_forest_final_metricas.csv",
    index=False,
    encoding="utf-8-sig"
)

tabla_top.to_csv(
    TABLAS /
    "random_forest_final_top_riesgo.csv",
    index=False,
    encoding="utf-8-sig"
)

importancias.to_csv(
    TABLAS /
    "random_forest_final_importancias.csv",
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    [{
        "umbral_oof_f1":
            umbral_f1,

        "precision_oof":
            precision_t[mejor_idx],

        "recall_oof":
            recall_t[mejor_idx],

        "f1_oof":
            f1_values[mejor_idx]
    }]
).to_csv(
    TABLAS /
    "random_forest_umbral_oof.csv",
    index=False,
    encoding="utf-8-sig"
)


print("\nArchivos generados:")

for nombre in [
    "random_forest_final_metricas.csv",
    "random_forest_final_top_riesgo.csv",
    "random_forest_final_importancias.csv",
    "random_forest_umbral_oof.csv"
]:
    print(
        TABLAS / nombre
    )


print(
    "\nEVALUACIÓN FINAL RANDOM FOREST FINALIZADA"
)