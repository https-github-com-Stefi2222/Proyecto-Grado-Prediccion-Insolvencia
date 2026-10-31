USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   1. DUPLICIDAD DENTRO DE PERIODO ACTUAL
   ============================================================ */

PRINT '============================================================';
PRINT '1. DUPLICIDAD EN PERIODO ACTUAL';
PRINT '============================================================';

WITH grupos AS
(
    SELECT
        fuente_estado,
        codigo_instancia,
        variable_analitica,

        COUNT(*) AS registros,

        COUNT(DISTINCT valor) AS valores_distintos,

        COUNT(DISTINCT id_taxonomia) AS taxonomias_distintas

    FROM stg.financieros_variables

    WHERE LTRIM(RTRIM(periodo)) = 'Periodo Actual'

    GROUP BY
        fuente_estado,
        codigo_instancia,
        variable_analitica
),
repetidos AS
(
    SELECT *
    FROM grupos
    WHERE registros > 1
)
SELECT
    fuente_estado,
    variable_analitica,

    COUNT(*) AS grupos_repetidos,

    SUM(
        CASE
            WHEN valores_distintos = 1 THEN 1
            ELSE 0
        END
    ) AS mismo_valor,

    SUM(
        CASE
            WHEN valores_distintos > 1 THEN 1
            ELSE 0
        END
    ) AS valores_diferentes,

    MAX(registros) AS max_registros,

    MAX(valores_distintos) AS max_valores_distintos,

    MAX(taxonomias_distintas) AS max_taxonomias

FROM repetidos

GROUP BY
    fuente_estado,
    variable_analitica

ORDER BY
    fuente_estado,
    variable_analitica;


/* ============================================================
   2. REGISTROS EXACTAMENTE REPETIDOS EN PERIODO ACTUAL
   ============================================================ */

PRINT '============================================================';
PRINT '2. REPETICIONES EXACTAS EN PERIODO ACTUAL';
PRINT '============================================================';

WITH base AS
(
    SELECT
        fuente_estado,
        codigo_instancia,
        variable_analitica,
        periodo,
        valor,
        concepto,
        COUNT(*) AS veces

    FROM stg.financieros_variables

    WHERE LTRIM(RTRIM(periodo)) = 'Periodo Actual'

    GROUP BY
        fuente_estado,
        codigo_instancia,
        variable_analitica,
        periodo,
        valor,
        concepto

    HAVING COUNT(*) > 1
)
SELECT
    fuente_estado,
    variable_analitica,

    COUNT(*) AS combinaciones_repetidas,

    SUM(veces) AS registros_involucrados,

    MAX(veces) AS max_repeticion

FROM base

GROUP BY
    fuente_estado,
    variable_analitica

ORDER BY
    fuente_estado,
    variable_analitica;


/* ============================================================
   3. CLASIFICACION SEGUN PUNTO DE ENTRADA
   ============================================================ */

PRINT '============================================================';
PRINT '3. CLASIFICACION SEGUN PUNTO DE ENTRADA';
PRINT '============================================================';

WITH instancias AS
(
    SELECT DISTINCT
        codigo_instancia,
        nit_normalizado,
        anio_corte,
        id_punto_entrada,
        punto_entrada

    FROM stg.financieros_variables

    WHERE fuente_estado = 'SITUACION_FINANCIERA'
),
clasificacion AS
(
    SELECT
        *,

        CASE

            WHEN punto_entrada LIKE '%Pymes%'
             AND punto_entrada LIKE '%Grupo 2%'
                THEN 'NIIF_PYMES_GRUPO_2'

            WHEN punto_entrada LIKE '%Plenas%'
             AND punto_entrada LIKE '%Grupo 1%'
                THEN 'NIIF_PLENAS_GRUPO_1'

            WHEN punto_entrada LIKE '%Grupo 3%'
                THEN 'GRUPO_3'

            ELSE 'OTRO'

        END AS grupo_contable

    FROM instancias
)
SELECT
    grupo_contable,

    COUNT(*) AS instancias,

    COUNT(DISTINCT nit_normalizado) AS nit_unicos,

    COUNT(
        DISTINCT CONCAT(
            nit_normalizado,
            '|',
            anio_corte
        )
    ) AS empresa_anio

FROM clasificacion

GROUP BY grupo_contable

ORDER BY instancias DESC;


/* ============================================================
   4. DETALLE DE PUNTOS DE ENTRADA
   ============================================================ */

PRINT '============================================================';
PRINT '4. DETALLE PUNTOS DE ENTRADA';
PRINT '============================================================';

WITH instancias AS
(
    SELECT DISTINCT
        codigo_instancia,
        id_punto_entrada,
        punto_entrada

    FROM stg.financieros_variables

    WHERE fuente_estado = 'SITUACION_FINANCIERA'
)
SELECT
    id_punto_entrada,
    punto_entrada,
    COUNT(*) AS instancias

FROM instancias

GROUP BY
    id_punto_entrada,
    punto_entrada

ORDER BY instancias DESC;


/* ============================================================
   5. MULTIPLES RADICADOS: MISMO O DISTINTO TIPO DE REPORTE
   ============================================================ */

PRINT '============================================================';
PRINT '5. MULTIPLES RADICADOS POR EMPRESA-ANIO';
PRINT '============================================================';

WITH reportes AS
(
    SELECT DISTINCT
        nit_normalizado,
        anio_corte,
        numero_radicado,
        codigo_instancia,
        punto_entrada

    FROM stg.financieros_variables

    WHERE fuente_estado = 'SITUACION_FINANCIERA'
),
empresa_anio AS
(
    SELECT
        nit_normalizado,
        anio_corte,

        COUNT(*) AS radicados,

        COUNT(
            DISTINCT punto_entrada
        ) AS tipos_reporte

    FROM reportes

    GROUP BY
        nit_normalizado,
        anio_corte
)
SELECT
    radicados,
    tipos_reporte,
    COUNT(*) AS cantidad_empresa_anio

FROM empresa_anio

WHERE radicados > 1

GROUP BY
    radicados,
    tipos_reporte

ORDER BY
    radicados,
    tipos_reporte;
GO