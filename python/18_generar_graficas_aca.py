from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# RUTAS
# ============================================================

RAIZ = Path(__file__).resolve().parent.parent

TABLAS = RAIZ / "outputs" / "tablas"
GRAFICOS = RAIZ / "outputs" / "graficos"

GRAFICOS.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# ESTILO GENERAL
# ============================================================

plt.rcParams.update({
    "font.family": "Times New Roman",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "figure.dpi": 120
})


ETIQUETAS = {
    "razon_corriente":
        "Razón corriente",

    "prueba_acida":
        "Prueba ácida",

    "roa":
        "ROA",

    "roe":
        "ROE",

    "margen_neto":
        "Margen neto",

    "endeudamiento":
        "Endeudamiento",

    "apalancamiento":
        "Apalancamiento",

    "rotacion_activos":
        "Rotación de activos",

    "rotacion_cartera":
        "Rotación de cartera",

    "missingindicator_prueba_acida":
        "Faltante prueba ácida",

    "missingindicator_margen_neto":
        "Faltante margen neto",

    "missingindicator_rotacion_cartera":
        "Faltante rotación cartera",

    "missingindicator_razon_corriente":
        "Faltante razón corriente",

    "missingindicator_roa":
        "Faltante ROA",

    "missingindicator_roe":
        "Faltante ROE"
}


print("=" * 80)
print("GENERACIÓN DE GRÁFICAS PARA EL ACA")
print("=" * 80)


# ============================================================
# FIGURA 1
# MEDIANAS POR CLASE
# ============================================================

medianas = pd.read_csv(
    TABLAS /
    "eda_medianas_por_clase.csv"
)

orden = [
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

medianas["orden"] = (
    medianas["variable"]
    .map({
        nombre: i
        for i, nombre
        in enumerate(orden)
    })
)

medianas = (
    medianas
    .sort_values("orden")
)

labels = [
    ETIQUETAS.get(x, x)
    for x in medianas["variable"]
]

x = np.arange(
    len(medianas)
)

ancho = 0.38

fig, ax = plt.subplots(
    figsize=(12, 6)
)

ax.bar(
    x - ancho / 2,
    medianas["mediana_target_0"],
    ancho,
    label="Sin insolvencia"
)

ax.bar(
    x + ancho / 2,
    medianas["mediana_target_1"],
    ancho,
    label="Insolvencia al año siguiente"
)

ax.set_title(
    "Mediana de indicadores financieros según ocurrencia de insolvencia"
)

ax.set_ylabel(
    "Mediana del indicador"
)

ax.set_xticks(x)

ax.set_xticklabels(
    labels,
    rotation=45,
    ha="right"
)

ax.legend(
    frameon=False
)

ax.grid(
    axis="y",
    alpha=0.25
)

fig.tight_layout()

ruta = (
    GRAFICOS /
    "01_medianas_indicadores_por_clase.png"
)

fig.savefig(
    ruta,
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)

print(
    f"OK: {ruta}"
)


# ============================================================
# FIGURA 2
# COMPARACIÓN DE MODELOS POR PR-AUC
# ============================================================

modelos = pd.read_csv(
    TABLAS /
    "comparacion_modelos_cv_sin_fuga_resumen.csv"
)

detalle = pd.read_csv(
    TABLAS /
    "comparacion_modelos_cv_sin_fuga_detalle.csv"
)

baseline = (
    detalle[
        "baseline_pr_auc"
    ]
    .mean()
)

nombres_modelos = {
    "REGRESION_LOGISTICA":
        "Regresión logística",

    "RANDOM_FOREST":
        "Random Forest",

    "HIST_GRADIENT_BOOSTING":
        "HistGradientBoosting"
}

modelos[
    "modelo_etiqueta"
] = (
    modelos["modelo"]
    .map(nombres_modelos)
)

modelos = (
    modelos
    .sort_values(
        "pr_auc_media",
        ascending=True
    )
)


fig, ax = plt.subplots(
    figsize=(9, 5.5)
)

ax.barh(
    modelos["modelo_etiqueta"],
    modelos["pr_auc_media"],
    xerr=modelos["pr_auc_std"],
    capsize=5
)

ax.axvline(
    baseline,
    linestyle="--",
    linewidth=1.5,
    label=(
        f"PR-AUC base = "
        f"{baseline:.4f}"
    )
)

ax.set_title(
    "Comparación de modelos mediante validación cruzada"
)

ax.set_xlabel(
    "PR-AUC promedio"
)

ax.set_ylabel(
    "Modelo"
)

ax.legend(
    frameon=False
)

ax.grid(
    axis="x",
    alpha=0.25
)

fig.tight_layout()

ruta = (
    GRAFICOS /
    "02_comparacion_modelos_pr_auc.png"
)

fig.savefig(
    ruta,
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)

print(
    f"OK: {ruta}"
)


# ============================================================
# FIGURA 3
# CAPTURA DE INSOLVENCIAS EN TOP DE RIESGO
# ============================================================

top = pd.read_csv(
    TABLAS /
    "random_forest_final_top_riesgo.csv"
)

top_test = (
    top[
        top["conjunto"]
        == "TEST_TEMPORAL_2022"
    ]
    .copy()
    .sort_values(
        "top_porcentaje"
    )
)


fig, ax = plt.subplots(
    figsize=(8.5, 5.5)
)

ax.plot(
    top_test[
        "top_porcentaje"
    ],
    top_test[
        "captura_positivos_pct"
    ],
    marker="o",
    linewidth=2,
    label="Random Forest"
)

# Referencia de selección aleatoria:
# revisar X% capturaría aproximadamente X%
ax.plot(
    top_test[
        "top_porcentaje"
    ],
    top_test[
        "top_porcentaje"
    ],
    linestyle="--",
    linewidth=1.5,
    label="Referencia aleatoria"
)

for _, fila in top_test.iterrows():

    ax.annotate(
        (
            f"{fila['captura_positivos_pct']:.1f}%"
        ),
        (
            fila["top_porcentaje"],
            fila["captura_positivos_pct"]
        ),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center"
    )


ax.set_title(
    "Concentración de insolvencias en empresas de mayor riesgo"
)

ax.set_xlabel(
    "Porcentaje de empresas revisadas con mayor riesgo"
)

ax.set_ylabel(
    "Porcentaje de insolvencias capturadas"
)

ax.set_xticks(
    top_test[
        "top_porcentaje"
    ]
)

ax.set_ylim(
    0,
    max(
        65,
        top_test[
            "captura_positivos_pct"
        ].max() + 5
    )
)

ax.legend(
    frameon=False
)

ax.grid(
    alpha=0.25
)

fig.tight_layout()

ruta = (
    GRAFICOS /
    "03_captura_insolvencias_top_riesgo.png"
)

fig.savefig(
    ruta,
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)

print(
    f"OK: {ruta}"
)


# ============================================================
# FIGURA 4
# IMPORTANCIA DE VARIABLES RANDOM FOREST
# ============================================================

importancias = pd.read_csv(
    TABLAS /
    "random_forest_final_importancias.csv"
)

importancias = (
    importancias
    .head(10)
    .copy()
)

importancias[
    "etiqueta"
] = (
    importancias["variable"]
    .map(ETIQUETAS)
    .fillna(
        importancias["variable"]
    )
)

importancias[
    "importancia_pct"
] = (
    100
    * importancias[
        "importancia"
    ]
)

importancias = (
    importancias
    .sort_values(
        "importancia_pct",
        ascending=True
    )
)


fig, ax = plt.subplots(
    figsize=(9, 6)
)

ax.barh(
    importancias[
        "etiqueta"
    ],
    importancias[
        "importancia_pct"
    ]
)

ax.set_title(
    "Importancia de variables en el modelo Random Forest"
)

ax.set_xlabel(
    "Importancia relativa (%)"
)

ax.set_ylabel(
    "Variable"
)

ax.grid(
    axis="x",
    alpha=0.25
)

fig.tight_layout()

ruta = (
    GRAFICOS /
    "04_importancia_variables_random_forest.png"
)

fig.savefig(
    ruta,
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)

print(
    f"OK: {ruta}"
)


# ============================================================
# FIN
# ============================================================

print("\n" + "=" * 80)
print("GRÁFICAS GENERADAS CORRECTAMENTE")
print("=" * 80)

print(
    f"Carpeta: {GRAFICOS}"
)