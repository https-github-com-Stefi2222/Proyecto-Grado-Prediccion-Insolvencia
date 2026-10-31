from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd

from sqlalchemy import create_engine

from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier,
    HistGradientBoostingClassifier
)
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score
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
# DATOS: SOLO COHORTE 2021 PARA SELECCIÓN
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

    CAST(target_insolvencia_1anio AS INT) AS target

FROM analytics.dataset_modelado

WHERE anio_corte = 2021;
"""


df = pd.read_sql_query(
    consulta,
    engine
)


for variable in INDICADORES:
    df[variable] = pd.to_numeric(
        df[variable],
        errors="coerce"
    )


X = df[INDICADORES].copy()
y = df["target"].astype(int)


print("=" * 90)
print("COMPARACIÓN DE MODELOS - VALIDACIÓN CRUZADA COHORTE 2021")
print("=" * 90)

print(
    f"Observaciones: {len(df):,}"
)

print(
    f"Positivos: {y.sum():,}"
)

print(
    f"Prevalencia: {100*y.mean():.4f}%"
)


# ============================================================
# WINSORIZACIÓN PREVIA GLOBAL SOLO DENTRO DE COHORTE TRAIN
# ============================================================

limites = {}

for variable in INDICADORES:

    serie = X[variable].dropna()

    limites[variable] = (
        serie.quantile(0.01),
        serie.quantile(0.99)
    )

    X[variable] = X[variable].clip(
        lower=limites[variable][0],
        upper=limites[variable][1]
    )


# ============================================================
# PESOS PARA HIST GRADIENT BOOSTING
# ============================================================

n_negativos = int((y == 0).sum())
n_positivos = int((y == 1).sum())

peso_positivo = (
    n_negativos / n_positivos
)

sample_weight = np.where(
    y == 1,
    peso_positivo,
    1.0
)


# ============================================================
# MODELOS
# ============================================================

modelos = {

    "REGRESION_LOGISTICA":
        Pipeline([
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True
                )
            ),
            (
                "scaler",
                StandardScaler()
            ),
            (
                "modelo",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=42
                )
            )
        ]),

    "RANDOM_FOREST":
        Pipeline([
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
        ]),

    "HIST_GRADIENT_BOOSTING":
        Pipeline([
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True
                )
            ),
            (
                "modelo",
                HistGradientBoostingClassifier(
                    learning_rate=0.05,
                    max_iter=300,
                    max_leaf_nodes=15,
                    min_samples_leaf=20,
                    l2_regularization=1.0,
                    random_state=42
                )
            )
        ])
}


# ============================================================
# VALIDACIÓN CRUZADA
# ============================================================

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

resultados = []


for nombre, modelo_base in modelos.items():

    print("\n" + "-" * 90)
    print(f"Evaluando: {nombre}")
    print("-" * 90)

    for fold, (idx_train, idx_val) in enumerate(
        cv.split(X, y),
        start=1
    ):

        X_train = X.iloc[idx_train]
        X_val = X.iloc[idx_val]

        y_train = y.iloc[idx_train]
        y_val = y.iloc[idx_val]

        modelo = clone(
            modelo_base
        )

        if nombre == "HIST_GRADIENT_BOOSTING":

            pesos_fold = (
                sample_weight[idx_train]
            )

            modelo.fit(
                X_train,
                y_train,
                modelo__sample_weight=pesos_fold
            )

        else:

            modelo.fit(
                X_train,
                y_train
            )

        probabilidades = (
            modelo.predict_proba(
                X_val
            )[:, 1]
        )

        roc_auc = roc_auc_score(
            y_val,
            probabilidades
        )

        pr_auc = average_precision_score(
            y_val,
            probabilidades
        )

        baseline = y_val.mean()

        lift = (
            pr_auc / baseline
            if baseline > 0
            else np.nan
        )

        resultados.append({
            "modelo": nombre,
            "fold": fold,
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "baseline_pr_auc": baseline,
            "lift_pr_auc": lift
        })

        print(
            f"Fold {fold}: "
            f"ROC-AUC={roc_auc:.4f} | "
            f"PR-AUC={pr_auc:.4f} | "
            f"Lift={lift:.2f}x"
        )


# ============================================================
# RESUMEN
# ============================================================

df_resultados = pd.DataFrame(
    resultados
)

resumen = (
    df_resultados
    .groupby("modelo")
    .agg(
        roc_auc_media=("roc_auc", "mean"),
        roc_auc_std=("roc_auc", "std"),

        pr_auc_media=("pr_auc", "mean"),
        pr_auc_std=("pr_auc", "std"),

        lift_pr_media=("lift_pr_auc", "mean")
    )
    .reset_index()
    .sort_values(
        "pr_auc_media",
        ascending=False
    )
)


print("\n" + "=" * 90)
print("RESUMEN VALIDACIÓN CRUZADA")
print("=" * 90)

print(
    resumen.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# GUARDAR
# ============================================================

df_resultados.to_csv(
    TABLAS /
    "comparacion_modelos_cv_detalle.csv",
    index=False,
    encoding="utf-8-sig"
)

resumen.to_csv(
    TABLAS /
    "comparacion_modelos_cv_resumen.csv",
    index=False,
    encoding="utf-8-sig"
)


print("\nArchivos generados:")

print(
    TABLAS /
    "comparacion_modelos_cv_detalle.csv"
)

print(
    TABLAS /
    "comparacion_modelos_cv_resumen.csv"
)

print(
    "\nCOMPARACIÓN DE MODELOS FINALIZADA"
)