"""Demostración ligera del modelo entrenado, sin SQL Server ni datos empresariales.
Perfiles ilustrativos de ratios medianos: no son empresas concretas.
Ejecutar desde la raíz del repositorio: python demo/ejecutar_demo.py
"""
from pathlib import Path
import sys

import joblib
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "python"))  # Permite deserializar PercentileClipper

ruta = RAIZ / "modelos" / "random_forest_pipeline.joblib"
if not ruta.exists():
    raise FileNotFoundError(
        f"No está el modelo entrenado en {ruta}.\n"
        "Ejecuta primero python/17_random_forest_final.py en el computador original "
        "con SQL Server y copia el archivo .joblib generado a modelos/."
    )

# Cargar únicamente archivos joblib generados por el propio equipo, nunca de terceros.
artefacto = joblib.load(ruta)
modelo = artefacto["pipeline"]
indicadores = artefacto["indicadores"]
umbral = artefacto["umbral"]

# Perfiles hipotéticos construidos usando medianas de cada clase publicadas
# en la Tabla 10 del informe. No representan empresas reales.
ejemplos = pd.DataFrame(
    [
        {
            "perfil": "Perfil ilustrativo A (medianas sin evento)",
            "razon_corriente": 2.1133, "prueba_acida": 1.2860,
            "roa": 0.0295, "roe": 0.0692, "margen_neto": 0.0491,
            "endeudamiento": 0.4407, "apalancamiento": 0.7037,
            "rotacion_activos": 0.5426, "rotacion_cartera": 3.7615,
        },
        {
            "perfil": "Perfil ilustrativo B (medianas con evento)",
            "razon_corriente": 1.6391, "prueba_acida": 0.9358,
            "roa": 0.0087, "roe": 0.0389, "margen_neto": 0.0087,
            "endeudamiento": 0.6812, "apalancamiento": 1.8291,
            "rotacion_activos": 0.8070, "rotacion_cartera": 2.9988,
        },
    ]
)

X = ejemplos[indicadores].astype(float)
puntuaciones = modelo.predict_proba(X)[:, 1]

resultado = pd.DataFrame({
    "Perfil": ejemplos["perfil"],
    "Puntuacion relativa": puntuaciones.round(6),
    "Senal segun umbral": ["Positivo" if p >= umbral else "Negativo" for p in puntuaciones],
})

# ============================================================
# PRESENTACION DE RESULTADOS
# ============================================================

ANCHO = 72

print("\n" + "=" * ANCHO)
print("MODELO PREDICTIVO DE RIESGO DE INSOLVENCIA".center(ANCHO))
print("RANDOM FOREST".center(ANCHO))
print("=" * ANCHO)

print("\n")
print("RESULTADOS DEL MODELO".center(ANCHO))
print()

print(
    f"{'PERFIL':<20}"
    f"{'PUNTUACIÓN RELATIVA':>28}"
    f"{'CLASIFICACIÓN':>20}"
)

print("-" * ANCHO)

for nombre, puntuacion in zip(
    ["Perfil A", "Perfil B"],
    puntuaciones
):
    clasificacion = (
        "Positivo" if puntuacion >= umbral else "Negativo"
    )

    print(
        f"{nombre:<20}"
        f"{puntuacion:>28.6f}"
        f"{clasificacion:>20}"
    )

print("\n" + "-" * ANCHO)

print(f"Umbral de clasificación: {umbral:.6f}")

print("-" * ANCHO)

print("\n")
print("EVALUACIÓN FINALIZADA".center(ANCHO))
print("=" * ANCHO)