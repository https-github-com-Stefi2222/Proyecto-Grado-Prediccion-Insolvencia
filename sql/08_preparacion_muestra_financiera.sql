USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   1. DIFERENCIA ENTRE AÑO DE CORTE Y AÑO DEL RADICADO
   ============================================================ */

PRINT '============================================================';
PRINT '1. DIFERENCIA ANIO RADICADO VS ANIO CORTE';
PRINT '============================================================';

WITH reportes AS
(
    SELECT DISTINCT
        nit_normalizado,
        anio_corte,
        numero_radicado,

        TRY_CONVERT(
            INT,
            LEFT(numero_radicado, 4)
        ) AS anio_radicado

    FROM stg.financieros_variables

    WHERE fuente_estado = 'SITUACION_FINANCIERA'
)
SELECT
    anio_corte,
    anio_radicado,
    anio_radicado - anio_corte AS diferencia_anios,
    COUNT(*) AS reportes

FROM reportes

GROUP BY
    anio_corte,
    anio_radicado

ORDER BY
    anio_corte,
    anio_radicado;


/* ============================================================
   2. CONSTRUIR UNIVERSO DE REPORTES NIIF PYMES GRUPO 2
   ============================================================ */

PRINT '============================================================';
PRINT '2. SELECCION PRELIMINAR DE REPORTES';
PRINT '============================================================';

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

            WHEN punto_entrada LIKE '%Consolidado%'
                THEN 'CONSOLIDADO'

            ELSE 'OTRO'
        END AS tipo_estado,

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
),
elegibles AS
(
    SELECT
        *,
        CASE
            WHEN tipo_estado = 'INDIVIDUAL' THEN 1
            WHEN tipo_estado = 'SEPARADO'   THEN 2
            ELSE 99
        END AS prioridad_tipo
    FROM reportes
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
                prioridad_tipo ASC,
                anio_radicado DESC,
                consecutivo DESC,
                numero_radicado DESC
        ) AS rn

    FROM elegibles

    WHERE prioridad_tipo < 99
)
SELECT
    tipo_estado,
    COUNT(*) AS empresa_anio,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos

FROM ranking

WHERE rn = 1

GROUP BY tipo_estado

ORDER BY empresa_anio DESC;


/* ============================================================
   3. MUESTRA SELECCIONADA POR AÑO
   ============================================================ */

PRINT '============================================================';
PRINT '3. MUESTRA PRELIMINAR POR ANIO';
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
                CASE
                    WHEN tipo_estado = 'INDIVIDUAL' THEN 1
                    WHEN tipo_estado = 'SEPARADO' THEN 2
                    ELSE 99
                END,
                anio_radicado DESC,
                consecutivo DESC,
                numero_radicado DESC
        ) AS rn

    FROM reportes

    WHERE tipo_estado IN ('INDIVIDUAL', 'SEPARADO')
)
SELECT
    anio_corte,
    COUNT(*) AS empresa_anio,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos

FROM ranking

WHERE rn = 1

GROUP BY anio_corte

ORDER BY anio_corte;


/* ============================================================
   4. VALIDAR CONVERSION NUMERICA DE LAS VARIABLES
   ============================================================ */

PRINT '============================================================';
PRINT '4. VALIDACION NUMERICA DE VALOR';
PRINT '============================================================';

SELECT
    variable_analitica,

    COUNT(*) AS registros_periodo_actual,

    SUM(
        CASE
            WHEN TRY_CONVERT(FLOAT, valor) IS NOT NULL
            THEN 1 ELSE 0
        END
    ) AS valores_numericos,

    SUM(
        CASE
            WHEN TRY_CONVERT(FLOAT, valor) IS NULL
            THEN 1 ELSE 0
        END
    ) AS valores_no_numericos

FROM stg.financieros_variables

WHERE LTRIM(RTRIM(periodo)) = 'Periodo Actual'

GROUP BY variable_analitica

ORDER BY variable_analitica;


/* ============================================================
   5. COBERTURA DE VARIABLES EN LOS REPORTES SELECCIONADOS
   ============================================================ */

PRINT '============================================================';
PRINT '5. COBERTURA DE VARIABLES EN MUESTRA PRELIMINAR';
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
                CASE
                    WHEN tipo_estado = 'INDIVIDUAL' THEN 1
                    WHEN tipo_estado = 'SEPARADO' THEN 2
                    ELSE 99
                END,
                anio_radicado DESC,
                consecutivo DESC,
                numero_radicado DESC
        ) AS rn

    FROM reportes

    WHERE tipo_estado IN ('INDIVIDUAL', 'SEPARADO')
),
seleccionados AS
(
    SELECT *
    FROM ranking
    WHERE rn = 1
),
variables AS
(
    SELECT DISTINCT
        f.codigo_instancia,
        f.variable_analitica

    FROM stg.financieros_variables f

    INNER JOIN seleccionados s
        ON f.codigo_instancia = s.codigo_instancia

    WHERE
        LTRIM(RTRIM(f.periodo)) = 'Periodo Actual'
)
SELECT
    variable_analitica,

    COUNT(DISTINCT codigo_instancia)
        AS reportes_con_variable,

    CAST(
        100.0 * COUNT(DISTINCT codigo_instancia)
        /
        (
            SELECT COUNT(*)
            FROM seleccionados
        )
        AS DECIMAL(6,2)
    ) AS cobertura_porcentaje

FROM variables

GROUP BY variable_analitica

ORDER BY variable_analitica;
GO