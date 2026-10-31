from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "outputs" / "tablas"
GRAFICOS = RAIZ / "outputs" / "graficos"


plt.rcParams.update({
    "font.family": "Times New Roman",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 10
})


df = pd.read_csv(
    TABLAS / "eda_medianas_por_clase.csv"
)


ETIQUETAS = {
    "razon_corriente": "Razón corriente",
    "prueba_acida": "Prueba ácida",
    "endeudamiento": "Endeudamiento",
    "apalancamiento": "Apalancamiento",
    "rotacion_activos": "Rotación de activos",
    "rotacion_cartera": "Rotación de cartera",
    "roa": "ROA",
    "roe": "ROE",
    "margen_neto": "Margen neto"
}


grupo_a = [
    "razon_corriente",
    "prueba_acida",
    "endeudamiento",
    "apalancamiento",
    "rotacion_activos",
    "rotacion_cartera"
]

grupo_b = [
    "roa",
    "roe",
    "margen_neto"
]


fig, axes = plt.subplots(
    2,
    1,
    figsize=(11, 9)
)


def dibujar(ax, variables, titulo):

    datos = (
        df[df["variable"].isin(variables)]
        .copy()
    )

    orden = {
        variable: i
        for i, variable in enumerate(variables)
    }

    datos["orden"] = datos["variable"].map(orden)

    datos = (
        datos
        .sort_values("orden")
    )

    labels = [
        ETIQUETAS[v]
        for v in datos["variable"]
    ]

    x = np.arange(len(datos))
    ancho = 0.38

    ax.bar(
        x - ancho / 2,
        datos["mediana_target_0"],
        ancho,
        label="Sin insolvencia"
    )

    ax.bar(
        x + ancho / 2,
        datos["mediana_target_1"],
        ancho,
        label="Insolvencia al año siguiente"
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        labels,
        rotation=25,
        ha="right"
    )

    ax.set_ylabel(
        "Mediana"
    )

    ax.set_title(
        titulo
    )

    ax.grid(
        axis="y",
        alpha=0.25
    )


dibujar(
    axes[0],
    grupo_a,
    "A. Liquidez, endeudamiento y eficiencia"
)

dibujar(
    axes[1],
    grupo_b,
    "B. Rentabilidad"
)


axes[0].legend(
    frameon=False
)

fig.suptitle(
    "Mediana de indicadores financieros según ocurrencia de insolvencia",
    fontsize=14
)

fig.tight_layout(
    rect=[0, 0, 1, 0.96]
)


ruta = (
    GRAFICOS /
    "01_medianas_indicadores_por_clase_final.png"
)

fig.savefig(
    ruta,
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)

print(
    f"Gráfica generada: {ruta}"
)