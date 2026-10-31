USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   TABLA DE INDICADORES FINANCIEROS
   ============================================================ */

IF OBJECT_ID(
    'analytics.indicadores_financieros',
    'U'
) IS NOT NULL
    DROP TABLE analytics.indicadores_financieros;
GO


SELECT

    nit_normalizado,
    anio_corte,
    numero_radicado,
    codigo_instancia,
    tipo_estado,
    anio_radicado,

    /* ========================================================
       VARIABLES FINANCIERAS ORIGINALES
       ======================================================== */

    activos_totales,
    activos_corrientes,
    pasivos_corrientes,
    inventarios,
    pasivos_totales,
    patrimonio,
    cuentas_por_cobrar,
    ingresos,
    utilidad_neta,


    /* ========================================================
       1. RAZÓN CORRIENTE
       Activos corrientes / Pasivos corrientes
       ======================================================== */

    CAST(
        activos_corrientes
        / NULLIF(pasivos_corrientes, 0)

        AS DECIMAL(38,10)
    ) AS razon_corriente,


    /* ========================================================
       2. PRUEBA ÁCIDA
       (Activos corrientes - Inventarios)
       / Pasivos corrientes
       ======================================================== */

    CAST(
        (activos_corrientes - inventarios)
        / NULLIF(pasivos_corrientes, 0)

        AS DECIMAL(38,10)
    ) AS prueba_acida,


    /* ========================================================
       3. ROA
       Utilidad neta / Activos totales
       ======================================================== */

    CAST(
        utilidad_neta
        / NULLIF(activos_totales, 0)

        AS DECIMAL(38,10)
    ) AS roa,


    /* ========================================================
       4. ROE
       Utilidad neta / Patrimonio
       ======================================================== */

    CAST(
        utilidad_neta
        / NULLIF(patrimonio, 0)

        AS DECIMAL(38,10)
    ) AS roe,


    /* ========================================================
       5. MARGEN NETO
       Utilidad neta / Ingresos
       ======================================================== */

    CAST(
        utilidad_neta
        / NULLIF(ingresos, 0)

        AS DECIMAL(38,10)
    ) AS margen_neto,


    /* ========================================================
       6. ENDEUDAMIENTO
       Pasivos totales / Activos totales
       ======================================================== */

    CAST(
        pasivos_totales
        / NULLIF(activos_totales, 0)

        AS DECIMAL(38,10)
    ) AS endeudamiento,


    /* ========================================================
       7. APALANCAMIENTO
       Pasivos totales / Patrimonio
       ======================================================== */

    CAST(
        pasivos_totales
        / NULLIF(patrimonio, 0)

        AS DECIMAL(38,10)
    ) AS apalancamiento,


    /* ========================================================
       8. ROTACIÓN DE ACTIVOS
       Ingresos / Activos totales
       ======================================================== */

    CAST(
        ingresos
        / NULLIF(activos_totales, 0)

        AS DECIMAL(38,10)
    ) AS rotacion_activos,


    /* ========================================================
       9. ROTACIÓN DE CARTERA
       Ingresos / Cuentas por cobrar
       ======================================================== */

    CAST(
        ingresos
        / NULLIF(cuentas_por_cobrar, 0)

        AS DECIMAL(38,10)
    ) AS rotacion_cartera


INTO analytics.indicadores_financieros

FROM analytics.empresa_anio_financiero;
GO


/* ============================================================
   ÍNDICE
   ============================================================ */

CREATE UNIQUE INDEX
IX_indicadores_empresa_anio

ON analytics.indicadores_financieros
(
    nit_normalizado,
    anio_corte
);
GO


/* ============================================================
   1. CONTROL GENERAL
   ============================================================ */

PRINT '============================================================';
PRINT '1. CONTROL GENERAL DE INDICADORES';
PRINT '============================================================';

SELECT
    COUNT(*) AS total_empresa_anio,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos,
    MIN(anio_corte) AS anio_minimo,
    MAX(anio_corte) AS anio_maximo
FROM analytics.indicadores_financieros;


/* ============================================================
   2. COBERTURA DE INDICADORES
   ============================================================ */

PRINT '============================================================';
PRINT '2. COBERTURA DE INDICADORES';
PRINT '============================================================';

SELECT
    COUNT(*) AS total,

    SUM(CASE WHEN razon_corriente IS NOT NULL
        THEN 1 ELSE 0 END) AS razon_corriente_validos,

    SUM(CASE WHEN prueba_acida IS NOT NULL
        THEN 1 ELSE 0 END) AS prueba_acida_validos,

    SUM(CASE WHEN roa IS NOT NULL
        THEN 1 ELSE 0 END) AS roa_validos,

    SUM(CASE WHEN roe IS NOT NULL
        THEN 1 ELSE 0 END) AS roe_validos,

    SUM(CASE WHEN margen_neto IS NOT NULL
        THEN 1 ELSE 0 END) AS margen_neto_validos,

    SUM(CASE WHEN endeudamiento IS NOT NULL
        THEN 1 ELSE 0 END) AS endeudamiento_validos,

    SUM(CASE WHEN apalancamiento IS NOT NULL
        THEN 1 ELSE 0 END) AS apalancamiento_validos,

    SUM(CASE WHEN rotacion_activos IS NOT NULL
        THEN 1 ELSE 0 END) AS rotacion_activos_validos,

    SUM(CASE WHEN rotacion_cartera IS NOT NULL
        THEN 1 ELSE 0 END) AS rotacion_cartera_validos

FROM analytics.indicadores_financieros;


/* ============================================================
   3. DENOMINADORES EN CERO
   ============================================================ */

PRINT '============================================================';
PRINT '3. DENOMINADORES EN CERO';
PRINT '============================================================';

SELECT

    SUM(
        CASE WHEN pasivos_corrientes = 0
        THEN 1 ELSE 0 END
    ) AS pasivos_corrientes_cero,

    SUM(
        CASE WHEN activos_totales = 0
        THEN 1 ELSE 0 END
    ) AS activos_totales_cero,

    SUM(
        CASE WHEN patrimonio = 0
        THEN 1 ELSE 0 END
    ) AS patrimonio_cero,

    SUM(
        CASE WHEN ingresos = 0
        THEN 1 ELSE 0 END
    ) AS ingresos_cero,

    SUM(
        CASE WHEN cuentas_por_cobrar = 0
        THEN 1 ELSE 0 END
    ) AS cuentas_por_cobrar_cero

FROM analytics.indicadores_financieros;


/* ============================================================
   4. RESUMEN PRELIMINAR POR AÑO
   ============================================================ */

PRINT '============================================================';
PRINT '4. RESUMEN PRELIMINAR POR ANIO';
PRINT '============================================================';

SELECT
    anio_corte,

    COUNT(*) AS empresa_anio,

    CAST(
        AVG(razon_corriente)
        AS DECIMAL(18,4)
    ) AS promedio_razon_corriente,

    CAST(
        AVG(roa)
        AS DECIMAL(18,4)
    ) AS promedio_roa,

    CAST(
        AVG(roe)
        AS DECIMAL(18,4)
    ) AS promedio_roe,

    CAST(
        AVG(margen_neto)
        AS DECIMAL(18,4)
    ) AS promedio_margen_neto,

    CAST(
        AVG(endeudamiento)
        AS DECIMAL(18,4)
    ) AS promedio_endeudamiento,

    CAST(
        AVG(rotacion_activos)
        AS DECIMAL(18,4)
    ) AS promedio_rotacion_activos

FROM analytics.indicadores_financieros

GROUP BY anio_corte

ORDER BY anio_corte;
GO