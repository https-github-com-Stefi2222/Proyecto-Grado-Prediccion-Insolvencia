USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   1. RELACIÓN RADICADO - INSTANCIA
   ============================================================ */

PRINT '============================================================';
PRINT '1. RELACION RADICADO - CODIGO_INSTANCIA';
PRINT '============================================================';

WITH pares AS
(
    SELECT DISTINCT
        numero_radicado,
        codigo_instancia
    FROM stg.financieros_variables
    WHERE
        numero_radicado IS NOT NULL
        AND numero_radicado <> ''
        AND codigo_instancia IS NOT NULL
        AND codigo_instancia <> ''
)
SELECT
    COUNT(*) AS pares_distintos,
    COUNT(DISTINCT numero_radicado) AS radicados,
    COUNT(DISTINCT codigo_instancia) AS instancias
FROM pares;


/* ============================================================
   2. ¿CODIGO_INSTANCIA + VARIABLE + PERIODO ES ÚNICO?
   ============================================================ */

PRINT '============================================================';
PRINT '2. UNICIDAD AGREGANDO PERIODO';
PRINT '============================================================';

WITH grupos AS
(
    SELECT
        fuente_estado,
        codigo_instancia,
        variable_analitica,
        COALESCE(
            NULLIF(LTRIM(RTRIM(periodo)), ''),
            '[VACIO]'
        ) AS periodo_normalizado,
        COUNT(*) AS registros
    FROM stg.financieros_variables
    GROUP BY
        fuente_estado,
        codigo_instancia,
        variable_analitica,
        COALESCE(
            NULLIF(LTRIM(RTRIM(periodo)), ''),
            '[VACIO]'
        )
)
SELECT
    fuente_estado,
    variable_analitica,
    COUNT(*) AS grupos,

    SUM(
        CASE WHEN registros = 1
        THEN 1 ELSE 0 END
    ) AS grupos_unicos,

    SUM(
        CASE WHEN registros > 1
        THEN 1 ELSE 0 END
    ) AS grupos_repetidos,

    MAX(registros) AS max_registros

FROM grupos
GROUP BY
    fuente_estado,
    variable_analitica
ORDER BY
    fuente_estado,
    variable_analitica;


/* ============================================================
   3. CANTIDAD DE PERIODOS POR INSTANCIA + VARIABLE
   ============================================================ */

PRINT '============================================================';
PRINT '3. NUMERO DE PERIODOS POR INSTANCIA Y VARIABLE';
PRINT '============================================================';

WITH base AS
(
    SELECT
        fuente_estado,
        codigo_instancia,
        variable_analitica,

        COUNT(
            DISTINCT COALESCE(
                NULLIF(LTRIM(RTRIM(periodo)), ''),
                '[VACIO]'
            )
        ) AS numero_periodos

    FROM stg.financieros_variables

    GROUP BY
        fuente_estado,
        codigo_instancia,
        variable_analitica
)
SELECT
    fuente_estado,
    variable_analitica,
    numero_periodos,
    COUNT(*) AS cantidad_instancias
FROM base
GROUP BY
    fuente_estado,
    variable_analitica,
    numero_periodos
ORDER BY
    fuente_estado,
    variable_analitica,
    numero_periodos;


/* ============================================================
   4. VALORES DE PERIODO MÁS FRECUENTES
   Usamos dos variables representativas.
   ============================================================ */

PRINT '============================================================';
PRINT '4. VALORES DE PERIODO MAS FRECUENTES';
PRINT '============================================================';

WITH conteo AS
(
    SELECT
        fuente_estado,
        variable_analitica,
        COALESCE(
            NULLIF(LTRIM(RTRIM(periodo)), ''),
            '[VACIO]'
        ) AS periodo,
        COUNT(*) AS registros
    FROM stg.financieros_variables
    WHERE variable_analitica IN
    (
        'ACTIVOS_TOTALES',
        'INGRESOS'
    )
    GROUP BY
        fuente_estado,
        variable_analitica,
        COALESCE(
            NULLIF(LTRIM(RTRIM(periodo)), ''),
            '[VACIO]'
        )
),
ranking AS
(
    SELECT
        *,
        ROW_NUMBER() OVER
        (
            PARTITION BY
                fuente_estado,
                variable_analitica
            ORDER BY registros DESC
        ) AS posicion
    FROM conteo
)
SELECT
    fuente_estado,
    variable_analitica,
    periodo,
    registros
FROM ranking
WHERE posicion <= 20
ORDER BY
    fuente_estado,
    variable_analitica,
    posicion;


/* ============================================================
   5. CUÁNTOS RADICADOS TIENE CADA EMPRESA-AÑO
   ============================================================ */

PRINT '============================================================';
PRINT '5. RADICADOS POR NIT Y ANIO';
PRINT '============================================================';

WITH radicados AS
(
    SELECT DISTINCT
        nit_normalizado,
        anio_corte,
        numero_radicado
    FROM stg.financieros_variables
    WHERE
        fuente_estado = 'SITUACION_FINANCIERA'
        AND nit_normalizado IS NOT NULL
        AND nit_normalizado <> ''
),
empresa_anio AS
(
    SELECT
        nit_normalizado,
        anio_corte,
        COUNT(*) AS numero_radicados
    FROM radicados
    GROUP BY
        nit_normalizado,
        anio_corte
)
SELECT
    numero_radicados,
    COUNT(*) AS cantidad_empresa_anio
FROM empresa_anio
GROUP BY numero_radicados
ORDER BY numero_radicados;


/* ============================================================
   6. PUNTOS DE ENTRADA / TIPOS DE REPORTE
   ============================================================ */

PRINT '============================================================';
PRINT '6. PUNTOS DE ENTRADA';
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
GO