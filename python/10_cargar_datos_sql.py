from pathlib import Path
from datetime import datetime
import pandas as pd
import pyodbc

# ============================================================
# CONFIGURACIÓN
# ============================================================

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"

SERVIDOR = "localhost"
BASE_DATOS = "ProyectoGradoQuiebra"

CHUNK_SIZE = 50_000

CADENA = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SERVIDOR};"
    f"DATABASE={BASE_DATOS};"
    "Trusted_Connection=yes;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def convertir_entero(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    if texto == "" or texto.lower() in {"nan", "none", "<na>"}:
        return None

    try:
        return int(float(texto))
    except (ValueError, TypeError):
        return None


def convertir_bit(valor):
    entero = convertir_entero(valor)

    if entero is None:
        return 0

    return 1 if entero == 1 else 0


def registrar_inicio(
    conexion,
    tabla_destino,
    archivo_origen
):
    cursor = conexion.cursor()

    cursor.execute(
        """
        INSERT INTO control.cargas
        (
            tabla_destino,
            archivo_origen,
            fecha_inicio,
            estado
        )
        OUTPUT INSERTED.id_carga
        VALUES (?, ?, SYSDATETIME(), 'EN_PROCESO')
        """,
        tabla_destino,
        archivo_origen
    )

    id_carga = cursor.fetchone()[0]

    conexion.commit()
    cursor.close()

    return id_carga


def registrar_fin(
    conexion,
    id_carga,
    filas,
    estado="OK",
    observaciones=None
):
    cursor = conexion.cursor()

    cursor.execute(
        """
        UPDATE control.cargas
        SET
            fecha_fin = SYSDATETIME(),
            filas_cargadas = ?,
            estado = ?,
            observaciones = ?
        WHERE id_carga = ?
        """,
        filas,
        estado,
        observaciones,
        id_carga
    )

    conexion.commit()
    cursor.close()


# ============================================================
# CARGA FINANCIERA
# ============================================================

def cargar_financieros(
    conexion,
    archivo,
    fuente_estado
):

    print("\n" + "=" * 90)
    print(f"CARGANDO: {archivo.name}")
    print("=" * 90)

    id_carga = registrar_inicio(
        conexion,
        "stg.financieros_variables",
        archivo.name
    )

    total = 0

    sql = """
    INSERT INTO stg.financieros_variables
    (
        fuente_estado,
        archivo_origen,
        codigo_instancia,
        nit,
        nit_normalizado,
        numero_radicado,
        id_punto_entrada,
        punto_entrada,
        id_taxonomia,
        taxonomia,
        fecha_corte,
        anio_corte,
        concepto,
        variable_analitica,
        periodo,
        valor
    )
    VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:

        lector = pd.read_csv(
            archivo,
            chunksize=CHUNK_SIZE,
            encoding="utf-8-sig",
            dtype="string",
            keep_default_na=False,
            low_memory=False
        )

        for numero_chunk, chunk in enumerate(
            lector,
            start=1
        ):

            registros = []

            for fila in chunk.itertuples(index=False):

                registros.append(
                    (
                        fuente_estado,
                        archivo.name,
                        str(fila.CODIGO_INSTANCIA),
                        str(fila.NIT),
                        str(fila.NIT_NORMALIZADO),
                        str(fila.NUMERO_RADICADO),
                        str(fila.ID_PUNTO_ENTRADA),
                        str(fila.PUNTO_ENTRADA),
                        str(fila.ID_TAXONOMIA),
                        str(fila.TAXONOMIA),
                        str(fila.FECHA_CORTE),
                        convertir_entero(fila.ANIO_CORTE),
                        str(fila.CONCEPTO),
                        str(fila.VARIABLE_ANALITICA),
                        str(fila.PERIODO),
                        str(fila.VALOR)
                    )
                )

            cursor = conexion.cursor()
            cursor.fast_executemany = True

            cursor.executemany(
                sql,
                registros
            )

            conexion.commit()
            cursor.close()

            total += len(registros)

            print(
                f"  Bloque {numero_chunk:>3} | "
                f"Total cargado: {total:,}"
            )

        registrar_fin(
            conexion,
            id_carga,
            total,
            "OK"
        )

        print(
            f"\nCarga finalizada: {total:,} registros"
        )

    except Exception as error:

        conexion.rollback()

        registrar_fin(
            conexion,
            id_carga,
            total,
            "ERROR",
            str(error)[:900]
        )

        raise


# ============================================================
# CARGA HISTÓRICO DE INSOLVENCIA
# ============================================================

def cargar_insolvencia_historial(
    conexion,
    archivo
):

    print("\n" + "=" * 90)
    print("CARGANDO HISTÓRICO DE INSOLVENCIA")
    print("=" * 90)

    id_carga = registrar_inicio(
        conexion,
        "stg.insolvencia_historial",
        archivo.name
    )

    total = 0

    sql = """
    INSERT INTO stg.insolvencia_historial
    (
        nro,
        nit,
        nit_normalizado,
        nombre,
        regional,
        departamento,
        ciudad,
        ciiu,
        macrosector,
        proceso,
        categoria_ss,
        activos,
        pasivos,
        empleos,
        anio_apertura,
        fecha_generacion,
        corte_anio,
        archivo_origen
    )
    VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:

        df = pd.read_csv(
            archivo,
            encoding="utf-8-sig",
            dtype="string",
            keep_default_na=False,
            low_memory=False
        )

        # Garantizar columna presente aunque algunos cortes
        # originales no la tuvieran.
        if "FECHA_GENERACION" not in df.columns:
            df["FECHA_GENERACION"] = ""

        registros = []

        for fila in df.itertuples(index=False):

            registros.append(
                (
                    str(getattr(fila, "NRO", "")),
                    str(getattr(fila, "NIT", "")),
                    str(
                        getattr(
                            fila,
                            "NIT_NORMALIZADO",
                            ""
                        )
                    ),
                    str(getattr(fila, "NOMBRE", "")),
                    str(getattr(fila, "REGIONAL", "")),
                    str(
                        getattr(
                            fila,
                            "DEPARTAMENTO",
                            ""
                        )
                    ),
                    str(getattr(fila, "CIUDAD", "")),
                    str(getattr(fila, "CIIU", "")),
                    str(
                        getattr(
                            fila,
                            "MACROSECTOR",
                            ""
                        )
                    ),
                    str(getattr(fila, "PROCESO", "")),
                    str(
                        getattr(
                            fila,
                            "CATEGORIA_SS",
                            ""
                        )
                    ),
                    str(getattr(fila, "ACTIVOS", "")),
                    str(getattr(fila, "PASIVOS", "")),
                    str(getattr(fila, "EMPLEOS", "")),
                    convertir_entero(
                        getattr(
                            fila,
                            "ANIO_APERTURA",
                            None
                        )
                    ),
                    str(
                        getattr(
                            fila,
                            "FECHA_GENERACION",
                            ""
                        )
                    ),
                    convertir_entero(
                        getattr(
                            fila,
                            "CORTE_ANIO",
                            None
                        )
                    ),
                    str(
                        getattr(
                            fila,
                            "ARCHIVO_ORIGEN",
                            ""
                        )
                    )
                )
            )

        cursor = conexion.cursor()
        cursor.fast_executemany = True

        cursor.executemany(
            sql,
            registros
        )

        conexion.commit()
        cursor.close()

        total = len(registros)

        registrar_fin(
            conexion,
            id_carga,
            total,
            "OK"
        )

        print(
            f"Carga finalizada: {total:,} registros"
        )

    except Exception as error:

        conexion.rollback()

        registrar_fin(
            conexion,
            id_carga,
            total,
            "ERROR",
            str(error)[:900]
        )

        raise


# ============================================================
# CARGA MAESTRA DE INSOLVENCIA
# ============================================================

def cargar_insolvencia_maestra(
    conexion,
    archivo
):

    print("\n" + "=" * 90)
    print("CARGANDO MAESTRA DE INSOLVENCIA")
    print("=" * 90)

    id_carga = registrar_inicio(
        conexion,
        "stg.insolvencia_maestra",
        archivo.name
    )

    total = 0

    sql = """
    INSERT INTO stg.insolvencia_maestra
    (
        nit_normalizado,
        primer_corte,
        ultimo_corte,
        num_cortes,
        cortes_presentes,
        anio_primera_apertura,
        anio_ultima_apertura,
        registro_insolvencia
    )
    VALUES
    (?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:

        df = pd.read_csv(
            archivo,
            encoding="utf-8-sig",
            dtype="string",
            keep_default_na=False
        )

        registros = []

        for fila in df.itertuples(index=False):

            registros.append(
                (
                    str(fila.NIT_NORMALIZADO),
                    convertir_entero(
                        fila.PRIMER_CORTE
                    ),
                    convertir_entero(
                        fila.ULTIMO_CORTE
                    ),
                    convertir_entero(
                        fila.NUM_CORTES
                    ),
                    str(fila.CORTES_PRESENTES),
                    convertir_entero(
                        fila.ANIO_PRIMERA_APERTURA
                    ),
                    convertir_entero(
                        fila.ANIO_ULTIMA_APERTURA
                    ),
                    convertir_bit(
                        fila.REGISTRO_INSOLVENCIA
                    )
                )
            )

        cursor = conexion.cursor()
        cursor.fast_executemany = True

        cursor.executemany(
            sql,
            registros
        )

        conexion.commit()
        cursor.close()

        total = len(registros)

        registrar_fin(
            conexion,
            id_carga,
            total,
            "OK"
        )

        print(
            f"Carga finalizada: {total:,} registros"
        )

    except Exception as error:

        conexion.rollback()

        registrar_fin(
            conexion,
            id_carga,
            total,
            "ERROR",
            str(error)[:900]
        )

        raise


# ============================================================
# EJECUCIÓN
# ============================================================

print("=" * 90)
print("CARGA DE DATOS A SQL SERVER")
print("=" * 90)

conexion = pyodbc.connect(
    CADENA,
    timeout=30
)

cursor = conexion.cursor()

print("\nLimpiando tablas de staging...")

cursor.execute(
    "TRUNCATE TABLE stg.financieros_variables"
)

cursor.execute(
    "TRUNCATE TABLE stg.insolvencia_historial"
)

cursor.execute(
    "TRUNCATE TABLE stg.insolvencia_maestra"
)

conexion.commit()
cursor.close()

print("Tablas preparadas.\n")


cargar_financieros(
    conexion,
    PROCESSED /
    "variables_situacion_financiera_2021_2024.csv",
    "SITUACION_FINANCIERA"
)

cargar_financieros(
    conexion,
    PROCESSED /
    "variables_resultado_integral_2021_2024.csv",
    "RESULTADO_INTEGRAL"
)

cargar_insolvencia_historial(
    conexion,
    PROCESSED /
    "insolvencia_historial_estandarizado.csv"
)

cargar_insolvencia_maestra(
    conexion,
    PROCESSED /
    "insolvencia_maestra_nit.csv"
)


# ============================================================
# CONTROL FINAL
# ============================================================

cursor = conexion.cursor()

cursor.execute("""
    SELECT COUNT(*)
    FROM stg.financieros_variables
""")

financieros = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*)
    FROM stg.insolvencia_historial
""")

historial = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*)
    FROM stg.insolvencia_maestra
""")

maestra = cursor.fetchone()[0]

cursor.close()
conexion.close()


print("\n" + "=" * 90)
print("CONTROL FINAL DE CARGA")
print("=" * 90)

print(
    f"stg.financieros_variables: "
    f"{financieros:,}"
)

print(
    f"stg.insolvencia_historial: "
    f"{historial:,}"
)

print(
    f"stg.insolvencia_maestra: "
    f"{maestra:,}"
)

print("\nCARGA SQL FINALIZADA")