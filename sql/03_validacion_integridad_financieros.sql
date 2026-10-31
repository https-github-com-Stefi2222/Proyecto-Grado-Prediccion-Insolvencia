USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT '1. CONTROL GENERAL POR FUENTE';
PRINT '============================================================';

SELECT
    fuente_estado,
    COUNT(*) AS registros,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos,
    COUNT(DISTINCT numero_radicado) AS radicados_unicos,
    COUNT(DISTINCT codigo_instancia) AS instancias_unicas
FROM stg.financieros_variables
GROUP BY fuente_estado
ORDER BY fuente_estado;


PRINT '============================================================';
PRINT '2. CONTROL POR AÑO Y FUENTE';
PRINT '============================================================';

SELECT
    anio_corte,
    fuente_estado,
    COUNT(*) AS registros,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos,
    COUNT(DISTINCT numero_radicado) AS radicados_unicos,
    COUNT(DISTINCT codigo_instancia) AS instancias_unicas
FROM stg.financieros_variables
GROUP BY
    anio_corte,
    fuente_estado
ORDER BY
    anio_corte,
    fuente_estado;


PRINT '============================================================';
PRINT '3. COBERTURA POR VARIABLE';
PRINT '============================================================';

SELECT
    fuente_estado,
    variable_analitica,
    COUNT(*) AS registros,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos,
    COUNT(
        DISTINCT CONCAT(
            nit_normalizado,
            '|',
            anio_corte
        )
    ) AS empresa_anio
FROM stg.financieros_variables
WHERE
    nit_normalizado IS NOT NULL
    AND nit_normalizado <> ''
GROUP BY
    fuente_estado,
    variable_analitica
ORDER BY
    fuente_estado,
    variable_analitica;


PRINT '============================================================';
PRINT '4. MULTIPLICIDAD NIT + AÑO + VARIABLE';
PRINT '============================================================';

WITH grupos AS
(
    SELECT
        fuente_estado,
        nit_normalizado,
        anio_corte,
        variable_analitica,
        COUNT(*) AS registros,
        COUNT(DISTINCT numero_radicado) AS radicados,
        COUNT(DISTINCT codigo_instancia) AS instancias
    FROM stg.financieros_variables
    WHERE
        nit_normalizado IS NOT NULL
        AND nit_normalizado <> ''
        AND anio_corte IS NOT NULL
    GROUP BY
        fuente_estado,
        nit_normalizado,
        anio_corte,
        variable_analitica
)
SELECT
    fuente_estado,
    variable_analitica,

    COUNT(*) AS grupos_empresa_anio,

    SUM(
        CASE
            WHEN registros = 1 THEN 1
            ELSE 0
        END
    ) AS grupos_con_un_registro,

    SUM(
        CASE
            WHEN registros > 1 THEN 1
            ELSE 0
        END
    ) AS grupos_con_multiples_registros,

    MAX(registros) AS max_registros_mismo_grupo,

    MAX(radicados) AS max_radicados_mismo_grupo,

    MAX(instancias) AS max_instancias_mismo_grupo

FROM grupos
GROUP BY
    fuente_estado,
    variable_analitica
ORDER BY
    fuente_estado,
    variable_analitica;


PRINT '============================================================';
PRINT '5. UNICIDAD POR CODIGO_INSTANCIA + VARIABLE';
PRINT '============================================================';

WITH instancia AS
(
    SELECT
        fuente_estado,
        codigo_instancia,
        variable_analitica,
        COUNT(*) AS registros
    FROM stg.financieros_variables
    WHERE
        codigo_instancia IS NOT NULL
        AND codigo_instancia <> ''
    GROUP BY
        fuente_estado,
        codigo_instancia,
        variable_analitica
)
SELECT
    fuente_estado,
    COUNT(*) AS grupos_instancia_variable,

    SUM(
        CASE
            WHEN registros = 1 THEN 1
            ELSE 0
        END
    ) AS grupos_unicos,

    SUM(
        CASE
            WHEN registros > 1 THEN 1
            ELSE 0
        END
    ) AS grupos_repetidos,

    MAX(registros) AS max_registros

FROM instancia
GROUP BY fuente_estado
ORDER BY fuente_estado;


PRINT '============================================================';
PRINT '6. CAMPOS CLAVE FALTANTES';
PRINT '============================================================';

SELECT
    fuente_estado,

    SUM(
        CASE
            WHEN nit_normalizado IS NULL
              OR nit_normalizado = ''
            THEN 1 ELSE 0
        END
    ) AS nit_faltante,

    SUM(
        CASE
            WHEN anio_corte IS NULL
            THEN 1 ELSE 0
        END
    ) AS anio_faltante,

    SUM(
        CASE
            WHEN numero_radicado IS NULL
              OR numero_radicado = ''
            THEN 1 ELSE 0
        END
    ) AS radicado_faltante,

    SUM(
        CASE
            WHEN codigo_instancia IS NULL
              OR codigo_instancia = ''
            THEN 1 ELSE 0
        END
    ) AS instancia_faltante,

    SUM(
        CASE
            WHEN valor IS NULL
              OR LTRIM(RTRIM(valor)) = ''
            THEN 1 ELSE 0
        END
    ) AS valor_faltante

FROM stg.financieros_variables
GROUP BY fuente_estado
ORDER BY fuente_estado;
GO