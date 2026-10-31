USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   1. CREAR DATASET DE MODELADO
   ============================================================ */

IF OBJECT_ID(
    'analytics.dataset_modelado',
    'U'
) IS NOT NULL
    DROP TABLE analytics.dataset_modelado;
GO


SELECT

    f.nit_normalizado,

    f.anio_corte,
    f.anio_radicado,

    f.numero_radicado,
    f.codigo_instancia,
    f.tipo_estado,

    /* Variables financieras originales */

    f.activos_totales,
    f.activos_corrientes,
    f.pasivos_corrientes,
    f.inventarios,
    f.pasivos_totales,
    f.patrimonio,
    f.cuentas_por_cobrar,
    f.ingresos,
    f.utilidad_neta,

    /* Indicadores */

    f.razon_corriente,
    f.prueba_acida,
    f.roa,
    f.roe,
    f.margen_neto,
    f.endeudamiento,
    f.apalancamiento,
    f.rotacion_activos,
    f.rotacion_cartera,

    /* Año del primer evento conocido */

    CASE
        WHEN i.anio_primera_apertura
             BETWEEN 1900 AND 2100
        THEN i.anio_primera_apertura

        ELSE NULL
    END AS anio_primera_insolvencia,

    /* ========================================================
       TARGET:
       1 = primera insolvencia en el año siguiente
       0 = no se observa primera insolvencia en ese horizonte
       ======================================================== */

    CASE
        WHEN i.anio_primera_apertura
             = f.anio_radicado + 1
        THEN CAST(1 AS BIT)

        ELSE CAST(0 AS BIT)
    END AS target_insolvencia_1anio


INTO analytics.dataset_modelado

FROM analytics.indicadores_financieros f

LEFT JOIN stg.insolvencia_maestra i
    ON f.nit_normalizado = i.nit_normalizado

WHERE

    /* Solo presentación anual comparable */
    f.anio_radicado = f.anio_corte + 1

    /* Necesitamos seguimiento completo a un año */
    AND f.anio_radicado <= 2023

    /* Empresa libre del evento cuando
       el reporte estuvo disponible */
    AND (
        i.nit_normalizado IS NULL

        OR i.anio_primera_apertura IS NULL

        OR i.anio_primera_apertura > f.anio_radicado

        /* Valor claramente inválido */
        OR i.anio_primera_apertura NOT BETWEEN 1900 AND 2100
    );
GO


/* ============================================================
   2. ÍNDICE
   ============================================================ */

CREATE UNIQUE INDEX
IX_dataset_modelado_empresa_anio

ON analytics.dataset_modelado
(
    nit_normalizado,
    anio_corte
);
GO


/* ============================================================
   3. CONTROL GENERAL
   ============================================================ */

PRINT '============================================================';
PRINT '1. CONTROL DEL DATASET DE MODELADO';
PRINT '============================================================';

SELECT
    COUNT(*) AS observaciones,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos,

    SUM(
        CAST(target_insolvencia_1anio AS INT)
    ) AS positivos,

    COUNT(*) -
    SUM(
        CAST(target_insolvencia_1anio AS INT)
    ) AS negativos,

    CAST(
        100.0 *
        SUM(
            CAST(target_insolvencia_1anio AS INT)
        )
        / COUNT(*)

        AS DECIMAL(8,4)
    ) AS porcentaje_positivos

FROM analytics.dataset_modelado;


/* ============================================================
   4. CONTROL POR COHORTE TEMPORAL
   ============================================================ */

PRINT '============================================================';
PRINT '2. DISTRIBUCION POR COHORTE';
PRINT '============================================================';

SELECT
    anio_corte,
    anio_radicado,
    anio_radicado + 1
        AS anio_objetivo,

    COUNT(*) AS observaciones,

    SUM(
        CAST(target_insolvencia_1anio AS INT)
    ) AS positivos,

    COUNT(*) -
    SUM(
        CAST(target_insolvencia_1anio AS INT)
    ) AS negativos,

    CAST(
        100.0 *
        SUM(
            CAST(target_insolvencia_1anio AS INT)
        )
        / COUNT(*)

        AS DECIMAL(8,4)
    ) AS porcentaje_positivos

FROM analytics.dataset_modelado

GROUP BY
    anio_corte,
    anio_radicado

ORDER BY
    anio_corte;


/* ============================================================
   5. CONTROL DE FUGA TEMPORAL
   ============================================================ */

PRINT '============================================================';
PRINT '3. CONTROL DE FUGA TEMPORAL';
PRINT '============================================================';

SELECT
    COUNT(*) AS observaciones_con_evento_previo
FROM analytics.dataset_modelado
WHERE
    anio_primera_insolvencia
        <= anio_radicado;


/* ============================================================
   6. COMPLETITUD DE INDICADORES
   ============================================================ */

PRINT '============================================================';
PRINT '4. COMPLETITUD DEL DATASET DE MODELADO';
PRINT '============================================================';

SELECT
    COUNT(*) AS total,

    SUM(CASE WHEN razon_corriente IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_razon_corriente,

    SUM(CASE WHEN prueba_acida IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_prueba_acida,

    SUM(CASE WHEN roa IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_roa,

    SUM(CASE WHEN roe IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_roe,

    SUM(CASE WHEN margen_neto IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_margen_neto,

    SUM(CASE WHEN endeudamiento IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_endeudamiento,

    SUM(CASE WHEN apalancamiento IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_apalancamiento,

    SUM(CASE WHEN rotacion_activos IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_rotacion_activos,

    SUM(CASE WHEN rotacion_cartera IS NULL
        THEN 1 ELSE 0 END)
        AS faltan_rotacion_cartera

FROM analytics.dataset_modelado;
GO