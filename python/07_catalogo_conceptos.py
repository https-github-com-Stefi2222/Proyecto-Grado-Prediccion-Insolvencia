from pathlib import Path
from collections import Counter
import pandas as pd
import unicodedata
import re

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
OUTPUT = RAIZ / "outputs" / "tablas"

OUTPUT.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 250_000


def normalizar_texto(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto).lower().strip()

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    texto = re.sub(r"\s+", " ", texto)

    return texto


archivos = [
    PROCESSED / "financiero_caratula_2021_2024.csv",
    PROCESSED / "financiero_resultado_integral_2021_2024.csv",
    PROCESSED / "financiero_situacion_financiera_2021_2024.csv"
]


PALABRAS_CLAVE = {
    "financiero_situacion_financiera_2021_2024.csv": [
        "activo corriente",
        "activos corrientes",
        "pasivo corriente",
        "pasivos corrientes",
        "inventario",
        "inventarios",
        "activos totales",
        "total activos",
        "pasivos totales",
        "total pasivos",
        "patrimonio",
        "cuentas por cobrar",
        "cuentas comerciales por cobrar"
    ],

    "financiero_resultado_integral_2021_2024.csv": [
        "ingresos de actividades ordinarias",
        "ingresos operacionales",
        "ingresos",
        "ganancia neta",
        "utilidad neta",
        "ganancia del periodo",
        "resultado del periodo",
        "ganancia perdida",
        "ganancia"
    ],

    "financiero_caratula_2021_2024.csv": [
        "tamano",
        "actividad economica",
        "ciiu",
        "sector",
        "tipo societario",
        "empleados",
        "domicilio"
    ]
}


catalogos = []
candidatos = []

print("=" * 90)
print("CATÁLOGO DE CONCEPTOS FINANCIEROS")
print("=" * 90)


for archivo in archivos:

    print(f"\nProcesando: {archivo.name}")

    contador = Counter()
    filas = 0

    lector = pd.read_csv(
        archivo,
        usecols=["CONCEPTO"],
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False
    )

    for numero_chunk, chunk in enumerate(lector, start=1):

        filas += len(chunk)

        conceptos = (
            chunk["CONCEPTO"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        contador.update(conceptos.tolist())

        if numero_chunk % 10 == 0:
            print(
                f"  Bloques: {numero_chunk} | "
                f"Filas procesadas: {filas:,}"
            )

    print(f"  Total filas: {filas:,}")
    print(f"  Conceptos distintos: {len(contador):,}")

    df_catalogo = pd.DataFrame(
        contador.items(),
        columns=["concepto", "frecuencia"]
    )

    df_catalogo["archivo"] = archivo.name

    df_catalogo = df_catalogo.sort_values(
        "frecuencia",
        ascending=False
    )

    catalogos.append(df_catalogo)

    print("\n  TOP 15 CONCEPTOS:")

    for _, fila in df_catalogo.head(15).iterrows():
        print(
            f"    {fila['frecuencia']:>10,} | "
            f"{fila['concepto']}"
        )

    palabras = [
        normalizar_texto(p)
        for p in PALABRAS_CLAVE[archivo.name]
    ]

    df_catalogo["concepto_normalizado"] = (
        df_catalogo["concepto"]
        .map(normalizar_texto)
    )

    patron = "|".join(
        re.escape(palabra)
        for palabra in palabras
    )

    seleccion = df_catalogo[
        df_catalogo["concepto_normalizado"]
        .str.contains(patron, regex=True, na=False)
    ].copy()

    seleccion = seleccion.sort_values(
        "frecuencia",
        ascending=False
    )

    candidatos.append(seleccion)

    print("\n  CONCEPTOS CANDIDATOS PARA EL PROYECTO:")

    if seleccion.empty:
        print("    No se encontraron coincidencias.")
    else:
        for _, fila in seleccion.head(40).iterrows():
            print(
                f"    {fila['frecuencia']:>10,} | "
                f"{fila['concepto']}"
            )

    print("\n" + "-" * 90)


catalogo_total = pd.concat(
    catalogos,
    ignore_index=True
)

candidatos_total = pd.concat(
    candidatos,
    ignore_index=True
)

ruta_catalogo = OUTPUT / "catalogo_conceptos_financieros.csv"
ruta_candidatos = OUTPUT / "conceptos_candidatos_modelo.csv"

catalogo_total.to_csv(
    ruta_catalogo,
    index=False,
    encoding="utf-8-sig"
)

candidatos_total.to_csv(
    ruta_candidatos,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 90)
print("CATÁLOGO FINALIZADO")
print("=" * 90)

print("\nArchivos generados:")
print(ruta_catalogo)
print(ruta_candidatos)