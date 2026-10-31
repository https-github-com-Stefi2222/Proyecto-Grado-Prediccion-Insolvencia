from pathlib import Path
import pandas as pd
import re

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
TABLAS = RAIZ / "outputs" / "tablas"

TABLAS.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 250_000


# ============================================================
# CONCEPTOS DEL ESTADO DE SITUACIÓN FINANCIERA
# ============================================================

CONCEPTOS_SITUACION = {
    "Total de activos": "ACTIVOS_TOTALES",
    "Activos corrientes totales": "ACTIVOS_CORRIENTES",
    "Pasivos corrientes totales": "PASIVOS_CORRIENTES",
    "Inventarios corrientes": "INVENTARIOS",
    "Total pasivos": "PASIVOS_TOTALES",
    "Patrimonio total": "PATRIMONIO",
    "Cuentas comerciales por cobrar y otras cuentas por cobrar corrientes":
        "CUENTAS_POR_COBRAR"
}


# ============================================================
# ARCHIVOS
# ============================================================

archivo_situacion = (
    PROCESSED /
    "financiero_situacion_financiera_2021_2024.csv"
)

archivo_resultado = (
    PROCESSED /
    "financiero_resultado_integral_2021_2024.csv"
)

salida_situacion = (
    PROCESSED /
    "variables_situacion_financiera_2021_2024.csv"
)

salida_resultado = (
    PROCESSED /
    "variables_resultado_integral_2021_2024.csv"
)


# Eliminar ejecuciones anteriores
for ruta in [salida_situacion, salida_resultado]:
    if ruta.exists():
        ruta.unlink()


columnas_salida = [
    "CODIGO_INSTANCIA",
    "NIT",
    "NIT_NORMALIZADO",
    "NUMERO_RADICADO",
    "ID_PUNTO_ENTRADA",
    "PUNTO_ENTRADA",
    "ID_TAXONOMIA",
    "TAXONOMIA",
    "FECHA_CORTE",
    "ANIO_CORTE",
    "CONCEPTO",
    "VARIABLE_ANALITICA",
    "PERIODO",
    "VALOR"
]


resumen = []


# ============================================================
# SITUACIÓN FINANCIERA
# ============================================================

print("=" * 90)
print("EXTRACCIÓN DE VARIABLES FINANCIERAS PARA EL MODELO")
print("=" * 90)

print("\nProcesando Estado de Situación Financiera...")

total_leidas = 0
total_seleccionadas = 0
primer_bloque = True
conteos = {v: 0 for v in CONCEPTOS_SITUACION.values()}

lector = pd.read_csv(
    archivo_situacion,
    chunksize=CHUNK_SIZE,
    encoding="utf-8-sig",
    low_memory=False,
    dtype={"NIT": "string", "NIT_NORMALIZADO": "string"}
)

for numero_chunk, chunk in enumerate(lector, start=1):

    total_leidas += len(chunk)

    seleccion = chunk[
        chunk["CONCEPTO"].isin(CONCEPTOS_SITUACION.keys())
    ].copy()

    if not seleccion.empty:

        seleccion["VARIABLE_ANALITICA"] = (
            seleccion["CONCEPTO"]
            .map(CONCEPTOS_SITUACION)
        )

        total_seleccionadas += len(seleccion)

        for variable, cantidad in (
            seleccion["VARIABLE_ANALITICA"]
            .value_counts()
            .items()
        ):
            conteos[variable] += int(cantidad)

        columnas_existentes = [
            c for c in columnas_salida
            if c in seleccion.columns
        ]

        seleccion[columnas_existentes].to_csv(
            salida_situacion,
            mode="a",
            index=False,
            header=primer_bloque,
            encoding="utf-8-sig"
        )

        primer_bloque = False

    if numero_chunk % 10 == 0:
        print(
            f"  Bloques: {numero_chunk} | "
            f"Leídas: {total_leidas:,} | "
            f"Seleccionadas: {total_seleccionadas:,}"
        )


print("\nVariables seleccionadas - Situación Financiera:")

for variable, cantidad in sorted(conteos.items()):
    print(f"  {variable}: {cantidad:,}")

print(f"\nTotal seleccionadas: {total_seleccionadas:,}")


for variable, cantidad in conteos.items():
    resumen.append({
        "fuente": "Estado de Situación Financiera",
        "variable": variable,
        "registros": cantidad
    })


# ============================================================
# RESULTADO INTEGRAL
# ============================================================

print("\n" + "=" * 90)
print("Procesando Estado de Resultado Integral...")
print("=" * 90)

total_leidas_resultado = 0
total_seleccionadas_resultado = 0
primer_bloque = True

conteos_resultado = {
    "INGRESOS": 0,
    "UTILIDAD_NETA": 0
}

lector = pd.read_csv(
    archivo_resultado,
    chunksize=CHUNK_SIZE,
    encoding="utf-8-sig",
    low_memory=False,
    dtype={"NIT": "string", "NIT_NORMALIZADO": "string"}
)

for numero_chunk, chunk in enumerate(lector, start=1):

    total_leidas_resultado += len(chunk)

    concepto = (
        chunk["CONCEPTO"]
        .astype("string")
        .str.strip()
    )

    # Ingresos: coincidencia exacta
    mascara_ingresos = (
        concepto == "Ingresos de actividades ordinarias"
    )

    # Utilidad neta:
    # Selecciona únicamente el concepto corto:
    # Ganancia (pérdida)
    #
    # Se usa una expresión regular porque la fuente contiene
    # caracteres de codificación irregulares en la palabra pérdida.
    mascara_utilidad = concepto.str.match(
        r"^Ganancia \([^)]*\)$",
        na=False
    )

    seleccion = chunk[
        mascara_ingresos | mascara_utilidad
    ].copy()

    if not seleccion.empty:

        concepto_sel = (
            seleccion["CONCEPTO"]
            .astype("string")
            .str.strip()
        )

        seleccion["VARIABLE_ANALITICA"] = "UTILIDAD_NETA"

        seleccion.loc[
            concepto_sel == "Ingresos de actividades ordinarias",
            "VARIABLE_ANALITICA"
        ] = "INGRESOS"

        total_seleccionadas_resultado += len(seleccion)

        for variable, cantidad in (
            seleccion["VARIABLE_ANALITICA"]
            .value_counts()
            .items()
        ):
            conteos_resultado[variable] += int(cantidad)

        columnas_existentes = [
            c for c in columnas_salida
            if c in seleccion.columns
        ]

        seleccion[columnas_existentes].to_csv(
            salida_resultado,
            mode="a",
            index=False,
            header=primer_bloque,
            encoding="utf-8-sig"
        )

        primer_bloque = False

    if numero_chunk % 10 == 0:
        print(
            f"  Bloques: {numero_chunk} | "
            f"Leídas: {total_leidas_resultado:,} | "
            f"Seleccionadas: {total_seleccionadas_resultado:,}"
        )


print("\nVariables seleccionadas - Resultado Integral:")

for variable, cantidad in sorted(conteos_resultado.items()):
    print(f"  {variable}: {cantidad:,}")

print(
    f"\nTotal seleccionadas: "
    f"{total_seleccionadas_resultado:,}"
)


for variable, cantidad in conteos_resultado.items():
    resumen.append({
        "fuente": "Estado de Resultado Integral",
        "variable": variable,
        "registros": cantidad
    })


# ============================================================
# RESUMEN
# ============================================================

df_resumen = pd.DataFrame(resumen)

ruta_resumen = (
    TABLAS /
    "resumen_variables_modelo.csv"
)

df_resumen.to_csv(
    ruta_resumen,
    index=False,
    encoding="utf-8-sig"
)


print("\n" + "=" * 90)
print("RESUMEN DE VARIABLES EXTRAÍDAS")
print("=" * 90)

print(
    df_resumen
    .sort_values(["fuente", "variable"])
    .to_string(index=False)
)

print("\nTOTAL DE REGISTROS EXTRAÍDOS:")
print(f"{df_resumen['registros'].sum():,}")

print("\nArchivos generados:")
print(salida_situacion)
print(salida_resultado)
print(ruta_resumen)

print("\nEXTRACCIÓN DE VARIABLES FINALIZADA")