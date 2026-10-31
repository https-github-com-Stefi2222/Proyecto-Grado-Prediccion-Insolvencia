USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   1. TABLA DE REPORTES SELECCIONADOS
   ============================================================ */

IF OBJECT_ID(
    'analytics.reportes_seleccionados',
    'U'
) IS NOT NULL
    DROP TABLE analytics.reportes_seleccionados;
GO


WITH reportes AS
(
    SELECT DISTINCT
        nit_normalizado,
        anio_corte,
        numero_radicado,
        codigo_instancia,
        punto_entrada,

        CASE
            WHEN punto_entrada LIKE '%Individual%'
                THEN 'INDIVIDUAL'

            WHEN punto_entrada LIKE '%Separado%'
                THEN 'SEPARADO'

            ELSE NULL
        END AS tipo_estado,

        CASE
            WHEN punto_entrada LIKE '%Individual%'
                THEN 1

            WHEN punto_entrada LIKE '%Separado%'
                THEN 2

            ELSE 99
        END AS prioridad_tipo,

        TRY_CONVERT(
            INT,
            LEFT(numero_radicado, 4)
        ) AS anio_radicado,

        CASE
            WHEN CHARINDEX('-', numero_radicado) > 0
            THEN TRY_CONVERT(
                BIGINT,
                RIGHT(
                    numero_radicado,
                    CHARINDEX(
                        '-',
                        REVERSE(numero_radicado)
                    ) - 1
                )
            )
            ELSE NULL
        END AS consecutivo

    FROM stg.financieros_variables

    WHERE
        fuente_estado = 'SITUACION_FINANCIERA'

        AND punto_entrada LIKE '%Pymes%'
        AND punto_entrada LIKE '%Grupo 2%'

        AND (
            punto_entrada LIKE '%Individual%'
            OR punto_entrada LIKE '%Separado%'
        )
),
ranking AS
(
    SELECT
        *,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                nit_normalizado,
                anio_corte

            ORDER BY

                /* Priorizar años de radicación válidos */
                CASE
                    WHEN anio_radicado IS NULL
                    THEN 1 ELSE 0
                END,

                /* Primera disponibilidad temporal */
                anio_radicado ASC,

                /* A igual disponibilidad: Individual */
                prioridad_tipo ASC,

                /* Última corrección dentro de ese año */
                consecutivo DESC,

                numero_radicado DESC

        ) AS rn

    FROM reportes
)

SELECT
    nit_normalizado,
    anio_corte,
    numero_radicado,
    codigo_instancia,
    tipo_estado,
    punto_entrada,
    anio_radicado,
    consecutivo

INTO analytics.reportes_seleccionados

FROM ranking

WHERE rn = 1;
GO


/* ============================================================
   2. ÍNDICE DE APOYO
   ============================================================ */

CREATE UNIQUE INDEX
IX_reportes_seleccionados_empresa_anio

ON analytics.reportes_seleccionados
(
    nit_normalizado,
    anio_corte
);
GO


/* ============================================================
   3. BASE FINANCIERA EN FORMATO EMPRESA-AÑO
   ============================================================ */

IF OBJECT_ID(
    'analytics.empresa_anio_financiero',
    'U'
) IS NOT NULL
    DROP TABLE analytics.empresa_anio_financiero;
GO


WITH valores AS
(
    SELECT
        r.nit_normalizado,
        r.anio_corte,
        r.numero_radicado,
        r.codigo_instancia,
        r.tipo_estado,
        r.anio_radicado,

        f.variable_analitica,

        TRY_CONVERT(
            DECIMAL(38,4),
            f.valor
        ) AS valor_numerico

    FROM analytics.reportes_seleccionados r

    INNER JOIN stg.financieros_variables f
        ON r.codigo_instancia = f.codigo_instancia

    WHERE
        LTRIM(RTRIM(f.periodo))
            = 'Periodo Actual'
)

SELECT
    nit_normalizado,
    anio_corte,

    numero_radicado,
    codigo_instancia,
    tipo_estado,
    anio_radicado,

    MAX(
        CASE
            WHEN variable_analitica =
                 'ACTIVOS_TOTALES'
            THEN valor_numerico
        END
    ) AS activos_totales,

    MAX(
        CASE
            WHEN variable_analitica =
                 'ACTIVOS_CORRIENTES'
            THEN valor_numerico
        END
    ) AS activos_corrientes,

    MAX(
        CASE
            WHEN variable_analitica =
                 'PASIVOS_CORRIENTES'
            THEN valor_numerico
        END
    ) AS pasivos_corrientes,

    MAX(
        CASE
            WHEN variable_analitica =
                 'INVENTARIOS'
            THEN valor_numerico
        END
    ) AS inventarios,

    MAX(
        CASE
            WHEN variable_analitica =
                 'PASIVOS_TOTALES'
            THEN valor_numerico
        END
    ) AS pasivos_totales,

    MAX(
        CASE
            WHEN variable_analitica =
                 'PATRIMONIO'
            THEN valor_numerico
        END
    ) AS patrimonio,

    MAX(
        CASE
            WHEN variable_analitica =
                 'CUENTAS_POR_COBRAR'
            THEN valor_numerico
        END
    ) AS cuentas_por_cobrar,

    MAX(
        CASE
            WHEN variable_analitica =
                 'INGRESOS'
            THEN valor_numerico
        END
    ) AS ingresos,

    MAX(
        CASE
            WHEN variable_analitica =
                 'UTILIDAD_NETA'
            THEN valor_numerico
        END
    ) AS utilidad_neta

INTO analytics.empresa_anio_financiero

FROM valores

GROUP BY
    nit_normalizado,
    anio_corte,
    numero_radicado,
    codigo_instancia,
    tipo_estado,
    anio_radicado;
GO


/* ============================================================
   4. ÍNDICE DE LA BASE ANALÍTICA
   ============================================================ */

CREATE UNIQUE INDEX
IX_empresa_anio_financiero

ON analytics.empresa_anio_financiero
(
    nit_normalizado,
    anio_corte
);
GO


/* ============================================================
   5. CONTROL DE RESULTADOS
   ============================================================ */

PRINT '============================================================';
PRINT 'CONTROL BASE ANALITICA EMPRESA-ANIO';
PRINT '============================================================';


SELECT
    COUNT(*) AS total_empresa_anio,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos
FROM analytics.empresa_anio_financiero;


SELECT
    anio_corte,
    COUNT(*) AS empresa_anio,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos
FROM analytics.empresa_anio_financiero
GROUP BY anio_corte
ORDER BY anio_corte;


SELECT
    tipo_estado,
    COUNT(*) AS empresa_anio
FROM analytics.empresa_anio_financiero
GROUP BY tipo_estado
ORDER BY empresa_anio DESC;


/* ============================================================
   6. COMPLETITUD DE VARIABLES
   ============================================================ */

SELECT
    COUNT(*) AS total,

    SUM(
        CASE WHEN activos_totales IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_activos_totales,

    SUM(
        CASE WHEN activos_corrientes IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_activos_corrientes,

    SUM(
        CASE WHEN pasivos_corrientes IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_pasivos_corrientes,

    SUM(
        CASE WHEN inventarios IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_inventarios,

    SUM(
        CASE WHEN pasivos_totales IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_pasivos_totales,

    SUM(
        CASE WHEN patrimonio IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_patrimonio,

    SUM(
        CASE WHEN cuentas_por_cobrar IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_cuentas_por_cobrar,

    SUM(
        CASE WHEN ingresos IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_ingresos,

    SUM(
        CASE WHEN utilidad_neta IS NULL
        THEN 1 ELSE 0 END
    ) AS faltan_utilidad_neta

FROM analytics.empresa_anio_financiero;
GO