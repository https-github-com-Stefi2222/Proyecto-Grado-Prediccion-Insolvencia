USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   1. DISTRIBUCIÓN DEL PRIMER AÑO DE INSOLVENCIA
   ============================================================ */

PRINT '============================================================';
PRINT '1. PRIMER ANIO DE APERTURA DE INSOLVENCIA';
PRINT '============================================================';

SELECT
    anio_primera_apertura,
    COUNT(*) AS nit_unicos
FROM stg.insolvencia_maestra
GROUP BY anio_primera_apertura
ORDER BY anio_primera_apertura;


/* ============================================================
   2. CRUCE DEL UNIVERSO FINANCIERO CON INSOLVENCIA
   ============================================================ */

PRINT '============================================================';
PRINT '2. COINCIDENCIA FINANCIEROS - INSOLVENCIA';
PRINT '============================================================';

SELECT
    COUNT(DISTINCT f.nit_normalizado)
        AS nit_financieros,

    COUNT(
        DISTINCT CASE
            WHEN i.nit_normalizado IS NOT NULL
            THEN f.nit_normalizado
        END
    ) AS nit_con_insolvencia,

    COUNT(
        DISTINCT CASE
            WHEN i.nit_normalizado IS NULL
            THEN f.nit_normalizado
        END
    ) AS nit_sin_insolvencia

FROM analytics.empresa_anio_financiero f

LEFT JOIN stg.insolvencia_maestra i
    ON f.nit_normalizado = i.nit_normalizado;


/* ============================================================
   3. RELACIÓN TEMPORAL ENTRE REPORTE E INSOLVENCIA
   ============================================================ */

PRINT '============================================================';
PRINT '3. RELACION TEMPORAL REPORTE - INSOLVENCIA';
PRINT '============================================================';

WITH base AS
(
    SELECT
        f.nit_normalizado,
        f.anio_corte,
        f.anio_radicado,
        i.anio_primera_apertura,

        CASE
            WHEN i.nit_normalizado IS NULL
                THEN 'SIN_REGISTRO_INSOLVENCIA'

            WHEN i.anio_primera_apertura IS NULL
                THEN 'INSOLVENCIA_SIN_ANIO'

            WHEN i.anio_primera_apertura
                 <= f.anio_radicado
                THEN 'INSOLVENCIA_PREVIA_O_MISMO_ANIO'

            WHEN i.anio_primera_apertura
                 = f.anio_radicado + 1
                THEN 'INSOLVENCIA_ANIO_SIGUIENTE'

            WHEN i.anio_primera_apertura
                 > f.anio_radicado + 1
                THEN 'INSOLVENCIA_POSTERIOR'

            ELSE 'OTRO'
        END AS situacion

    FROM analytics.empresa_anio_financiero f

    LEFT JOIN stg.insolvencia_maestra i
        ON f.nit_normalizado = i.nit_normalizado
)

SELECT
    situacion,
    COUNT(*) AS empresa_anio,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos
FROM base
GROUP BY situacion
ORDER BY empresa_anio DESC;


/* ============================================================
   4. SIMULACIÓN DE OBJETIVO PREDICTIVO A 1 AÑO
   ============================================================ */

PRINT '============================================================';
PRINT '4. SIMULACION TARGET A UN ANIO';
PRINT '============================================================';

WITH base AS
(
    SELECT
        f.nit_normalizado,
        f.anio_corte,
        f.anio_radicado,
        i.anio_primera_apertura

    FROM analytics.empresa_anio_financiero f

    LEFT JOIN stg.insolvencia_maestra i
        ON f.nit_normalizado = i.nit_normalizado
),
elegibles AS
(
    SELECT
        *,

        CASE
            WHEN anio_primera_apertura
                 = anio_radicado + 1
            THEN 1
            ELSE 0
        END AS target_insolvencia_1anio

    FROM base

    WHERE
        /* Tenemos insolvencia observada únicamente hasta 2024 */
        anio_radicado <= 2023

        /* La empresa debía estar libre del evento
           cuando la información se hizo disponible */
        AND (
            anio_primera_apertura IS NULL
            OR anio_primera_apertura > anio_radicado
        )
)

SELECT
    anio_corte,
    anio_radicado,

    COUNT(*) AS observaciones,

    SUM(target_insolvencia_1anio)
        AS target_1,

    COUNT(*) -
    SUM(target_insolvencia_1anio)
        AS target_0,

    CAST(
        100.0 *
        SUM(target_insolvencia_1anio)
        / NULLIF(COUNT(*), 0)

        AS DECIMAL(8,4)
    ) AS porcentaje_target_1

FROM elegibles

GROUP BY
    anio_corte,
    anio_radicado

ORDER BY
    anio_corte,
    anio_radicado;


/* ============================================================
   5. OBSERVACIONES QUE NO PUEDEN USARSE PARA ENTRENAMIENTO
   ============================================================ */

PRINT '============================================================';
PRINT '5. OBSERVACIONES FUERA DEL ENTRENAMIENTO';
PRINT '============================================================';

WITH base AS
(
    SELECT
        f.nit_normalizado,
        f.anio_corte,
        f.anio_radicado,
        i.anio_primera_apertura

    FROM analytics.empresa_anio_financiero f

    LEFT JOIN stg.insolvencia_maestra i
        ON f.nit_normalizado = i.nit_normalizado
)

SELECT
    CASE

        WHEN anio_primera_apertura IS NOT NULL
         AND anio_primera_apertura <= anio_radicado
            THEN 'EVENTO_PREVIO_O_MISMO_ANIO'

        WHEN anio_radicado >= 2024
            THEN 'SIN_SEGUIMIENTO_COMPLETO_A_UN_ANIO'

        ELSE 'ELEGIBLE_ENTRENAMIENTO'

    END AS clasificacion,

    COUNT(*) AS empresa_anio,

    COUNT(DISTINCT nit_normalizado)
        AS nit_unicos

FROM base

GROUP BY
    CASE

        WHEN anio_primera_apertura IS NOT NULL
         AND anio_primera_apertura <= anio_radicado
            THEN 'EVENTO_PREVIO_O_MISMO_ANIO'

        WHEN anio_radicado >= 2024
            THEN 'SIN_SEGUIMIENTO_COMPLETO_A_UN_ANIO'

        ELSE 'ELEGIBLE_ENTRENAMIENTO'

    END

ORDER BY empresa_anio DESC;
GO