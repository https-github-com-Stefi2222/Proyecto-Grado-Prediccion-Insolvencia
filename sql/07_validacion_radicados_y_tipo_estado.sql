USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   1. VALIDAR ESTRUCTURA DEL NUMERO DE RADICADO
   ============================================================ */

PRINT '============================================================';
PRINT '1. VALIDACION DE NUMERO DE RADICADO';
PRINT '============================================================';

WITH radicados AS
(
    SELECT DISTINCT
        numero_radicado,
        anio_corte,

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
        END AS consecutivo_radicado

    FROM stg.financieros_variables

    WHERE numero_radicado IS NOT NULL
      AND numero_radicado <> ''
)
SELECT
    anio_corte,

    COUNT(*) AS radicados,

    SUM(
        CASE
            WHEN anio_radicado = anio_corte
            THEN 1 ELSE 0
        END
    ) AS anio_coincide,

    SUM(
        CASE
            WHEN anio_radicado <> anio_corte
              OR anio_radicado IS NULL
            THEN 1 ELSE 0
        END
    ) AS anio_no_coincide,

    SUM(
        CASE
            WHEN consecutivo_radicado IS NULL
            THEN 1 ELSE 0
        END
    ) AS consecutivo_no_valido

FROM radicados
GROUP BY anio_corte
ORDER BY anio_corte;


/* ============================================================
   2. COMBINACIONES DE TIPO DE ESTADO POR EMPRESA-AÑO
      SOLO NIIF PYMES GRUPO 2
   ============================================================ */

PRINT '============================================================';
PRINT '2. COMBINACIONES DE TIPO DE ESTADO';
PRINT '============================================================';

WITH reportes AS
(
    SELECT DISTINCT
        nit_normalizado,
        anio_corte,

        CASE
            WHEN punto_entrada LIKE '%Individual%'
                THEN 'INDIVIDUAL'

            WHEN punto_entrada LIKE '%Separado%'
                THEN 'SEPARADO'

            WHEN punto_entrada LIKE '%Consolidado%'
                THEN 'CONSOLIDADO'

            ELSE 'OTRO'
        END AS tipo_estado

    FROM stg.financieros_variables

    WHERE fuente_estado = 'SITUACION_FINANCIERA'
      AND punto_entrada LIKE '%Pymes%'
      AND punto_entrada LIKE '%Grupo 2%'
),
banderas AS
(
    SELECT
        nit_normalizado,
        anio_corte,

        MAX(
            CASE WHEN tipo_estado = 'INDIVIDUAL'
            THEN 1 ELSE 0 END
        ) AS individual,

        MAX(
            CASE WHEN tipo_estado = 'SEPARADO'
            THEN 1 ELSE 0 END
        ) AS separado,

        MAX(
            CASE WHEN tipo_estado = 'CONSOLIDADO'
            THEN 1 ELSE 0 END
        ) AS consolidado,

        MAX(
            CASE WHEN tipo_estado = 'OTRO'
            THEN 1 ELSE 0 END
        ) AS otro

    FROM reportes
    GROUP BY
        nit_normalizado,
        anio_corte
),
clasificacion AS
(
    SELECT
        *,
        CONCAT(
            CASE WHEN individual = 1
                 THEN 'INDIVIDUAL+' ELSE '' END,

            CASE WHEN separado = 1
                 THEN 'SEPARADO+' ELSE '' END,

            CASE WHEN consolidado = 1
                 THEN 'CONSOLIDADO+' ELSE '' END,

            CASE WHEN otro = 1
                 THEN 'OTRO+' ELSE '' END
        ) AS combinacion
    FROM banderas
)
SELECT
    LEFT(
        combinacion,
        LEN(combinacion) - 1
    ) AS combinacion_tipo_estado,

    COUNT(*) AS empresa_anio

FROM clasificacion

GROUP BY combinacion
ORDER BY empresa_anio DESC;


/* ============================================================
   3. MULTIPLES RADICADOS DEL MISMO TIPO:
      ¿PODEMOS ORDENARLOS POR CONSECUTIVO?
   ============================================================ */

PRINT '============================================================';
PRINT '3. ORDENAMIENTO DE MULTIPLES RADICADOS';
PRINT '============================================================';

WITH reportes AS
(
    SELECT DISTINCT
        nit_normalizado,
        anio_corte,
        numero_radicado,
        codigo_instancia,

        CASE
            WHEN punto_entrada LIKE '%Individual%'
                THEN 'INDIVIDUAL'

            WHEN punto_entrada LIKE '%Separado%'
                THEN 'SEPARADO'

            WHEN punto_entrada LIKE '%Consolidado%'
                THEN 'CONSOLIDADO'

            ELSE 'OTRO'
        END AS tipo_estado,

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

    WHERE fuente_estado = 'SITUACION_FINANCIERA'
      AND punto_entrada LIKE '%Pymes%'
      AND punto_entrada LIKE '%Grupo 2%'
),
grupos AS
(
    SELECT
        nit_normalizado,
        anio_corte,
        tipo_estado,

        COUNT(*) AS radicados,

        COUNT(consecutivo)
            AS consecutivos_validos,

        COUNT(DISTINCT consecutivo)
            AS consecutivos_distintos

    FROM reportes

    GROUP BY
        nit_normalizado,
        anio_corte,
        tipo_estado

    HAVING COUNT(*) > 1
)
SELECT
    tipo_estado,

    COUNT(*) AS grupos_con_multiples_radicados,

    SUM(
        CASE
            WHEN radicados = consecutivos_validos
             AND radicados = consecutivos_distintos
            THEN 1 ELSE 0
        END
    ) AS grupos_ordenables,

    SUM(
        CASE
            WHEN radicados <> consecutivos_validos
              OR radicados <> consecutivos_distintos
            THEN 1 ELSE 0
        END
    ) AS grupos_problematicos,

    MAX(radicados) AS max_radicados

FROM grupos
GROUP BY tipo_estado
ORDER BY tipo_estado;


/* ============================================================
   4. CUÁNTAS OBSERVACIONES QUEDARÍAN
      SI CONSERVAMOS UNA PRESENTACIÓN POR TIPO
   ============================================================ */

PRINT '============================================================';
PRINT '4. REPORTES UNICOS DESPUES DE PRIORIZAR ULTIMO RADICADO';
PRINT '============================================================';

WITH reportes AS
(
    SELECT DISTINCT
        nit_normalizado,
        anio_corte,
        numero_radicado,
        codigo_instancia,

        CASE
            WHEN punto_entrada LIKE '%Individual%'
                THEN 'INDIVIDUAL'

            WHEN punto_entrada LIKE '%Separado%'
                THEN 'SEPARADO'

            WHEN punto_entrada LIKE '%Consolidado%'
                THEN 'CONSOLIDADO'

            ELSE 'OTRO'
        END AS tipo_estado,

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

    WHERE fuente_estado = 'SITUACION_FINANCIERA'
      AND punto_entrada LIKE '%Pymes%'
      AND punto_entrada LIKE '%Grupo 2%'
),
ranking AS
(
    SELECT
        *,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                nit_normalizado,
                anio_corte,
                tipo_estado

            ORDER BY
                consecutivo DESC,
                numero_radicado DESC
        ) AS rn

    FROM reportes
)
SELECT
    tipo_estado,
    COUNT(*) AS reportes_seleccionados,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos,
    COUNT(
        DISTINCT CONCAT(
            nit_normalizado,
            '|',
            anio_corte
        )
    ) AS empresa_anio

FROM ranking

WHERE rn = 1

GROUP BY tipo_estado
ORDER BY reportes_seleccionados DESC;
GO