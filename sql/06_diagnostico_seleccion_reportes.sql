USE ProyectoGradoQuiebra;
GO

SET NOCOUNT ON;


/* ============================================================
   1. TIPOS DE ESTADO DENTRO DE GRUPO 2
   ============================================================ */

PRINT '============================================================';
PRINT '1. TIPOS DE REPORTE - NIIF PYMES GRUPO 2';
PRINT '============================================================';

WITH instancias AS
(
    SELECT DISTINCT
        codigo_instancia,
        nit_normalizado,
        anio_corte,
        numero_radicado,
        punto_entrada
    FROM stg.financieros_variables
    WHERE
        fuente_estado = 'SITUACION_FINANCIERA'
        AND punto_entrada LIKE '%Pymes%'
        AND punto_entrada LIKE '%Grupo 2%'
),
clasificados AS
(
    SELECT
        *,
        CASE
            WHEN punto_entrada LIKE '%Individual%'
                THEN 'INDIVIDUAL'

            WHEN punto_entrada LIKE '%Separado%'
                THEN 'SEPARADO'

            WHEN punto_entrada LIKE '%Consolidado%'
                THEN 'CONSOLIDADO'

            ELSE 'OTRO'
        END AS tipo_estado
    FROM instancias
)
SELECT
    tipo_estado,
    COUNT(*) AS instancias,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos,
    COUNT(
        DISTINCT CONCAT(
            nit_normalizado,
            '|',
            anio_corte
        )
    ) AS empresa_anio
FROM clasificados
GROUP BY tipo_estado
ORDER BY instancias DESC;


/* ============================================================
   2. GRUPO 2 POR AÑO Y TIPO DE ESTADO
   ============================================================ */

PRINT '============================================================';
PRINT '2. GRUPO 2 POR ANIO Y TIPO DE ESTADO';
PRINT '============================================================';

WITH instancias AS
(
    SELECT DISTINCT
        codigo_instancia,
        nit_normalizado,
        anio_corte,
        punto_entrada
    FROM stg.financieros_variables
    WHERE
        fuente_estado = 'SITUACION_FINANCIERA'
        AND punto_entrada LIKE '%Pymes%'
        AND punto_entrada LIKE '%Grupo 2%'
),
clasificados AS
(
    SELECT
        *,
        CASE
            WHEN punto_entrada LIKE '%Individual%'
                THEN 'INDIVIDUAL'

            WHEN punto_entrada LIKE '%Separado%'
                THEN 'SEPARADO'

            WHEN punto_entrada LIKE '%Consolidado%'
                THEN 'CONSOLIDADO'

            ELSE 'OTRO'
        END AS tipo_estado
    FROM instancias
)
SELECT
    anio_corte,
    tipo_estado,
    COUNT(*) AS instancias,
    COUNT(DISTINCT nit_normalizado) AS nit_unicos
FROM clasificados
GROUP BY
    anio_corte,
    tipo_estado
ORDER BY
    anio_corte,
    tipo_estado;


/* ============================================================
   3. MULTIPLES RADICADOS DEL MISMO TIPO DE REPORTE
      SOLO GRUPO 2
   ============================================================ */

PRINT '============================================================';
PRINT '3. MULTIPLES RADICADOS MISMO TIPO - GRUPO 2';
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
        END AS tipo_estado

    FROM stg.financieros_variables

    WHERE
        fuente_estado = 'SITUACION_FINANCIERA'
        AND punto_entrada LIKE '%Pymes%'
        AND punto_entrada LIKE '%Grupo 2%'
),
grupos AS
(
    SELECT
        nit_normalizado,
        anio_corte,
        tipo_estado,
        COUNT(*) AS radicados
    FROM reportes
    GROUP BY
        nit_normalizado,
        anio_corte,
        tipo_estado
    HAVING COUNT(*) > 1
)
SELECT
    tipo_estado,
    radicados,
    COUNT(*) AS cantidad_empresa_anio
FROM grupos
GROUP BY
    tipo_estado,
    radicados
ORDER BY
    tipo_estado,
    radicados;


/* ============================================================
   4. ¿LOS MULTIPLES RADICADOS DEL MISMO TIPO
      TIENEN LOS MISMOS VALORES?
   ============================================================ */

PRINT '============================================================';
PRINT '4. COMPARACION DE VALORES ENTRE RADICADOS DEL MISMO TIPO';
PRINT '============================================================';

WITH base AS
(
    SELECT DISTINCT
        f.nit_normalizado,
        f.anio_corte,
        f.numero_radicado,
        f.codigo_instancia,
        f.variable_analitica,
        f.valor,

        CASE
            WHEN f.punto_entrada LIKE '%Individual%'
                THEN 'INDIVIDUAL'

            WHEN f.punto_entrada LIKE '%Separado%'
                THEN 'SEPARADO'

            WHEN f.punto_entrada LIKE '%Consolidado%'
                THEN 'CONSOLIDADO'

            ELSE 'OTRO'
        END AS tipo_estado

    FROM stg.financieros_variables f

    WHERE
        f.fuente_estado = 'SITUACION_FINANCIERA'
        AND LTRIM(RTRIM(f.periodo)) = 'Periodo Actual'
        AND f.punto_entrada LIKE '%Pymes%'
        AND f.punto_entrada LIKE '%Grupo 2%'
),
grupos_multiradicado AS
(
    SELECT
        nit_normalizado,
        anio_corte,
        tipo_estado
    FROM base
    GROUP BY
        nit_normalizado,
        anio_corte,
        tipo_estado
    HAVING COUNT(DISTINCT numero_radicado) > 1
),
comparacion AS
(
    SELECT
        b.nit_normalizado,
        b.anio_corte,
        b.tipo_estado,
        b.variable_analitica,

        COUNT(DISTINCT b.numero_radicado)
            AS radicados,

        COUNT(DISTINCT b.valor)
            AS valores_distintos

    FROM base b

    INNER JOIN grupos_multiradicado g
        ON  b.nit_normalizado = g.nit_normalizado
        AND b.anio_corte = g.anio_corte
        AND b.tipo_estado = g.tipo_estado

    GROUP BY
        b.nit_normalizado,
        b.anio_corte,
        b.tipo_estado,
        b.variable_analitica
)
SELECT
    tipo_estado,
    variable_analitica,

    COUNT(*) AS grupos_empresa_anio,

    SUM(
        CASE
            WHEN valores_distintos = 1
            THEN 1 ELSE 0
        END
    ) AS mismo_valor,

    SUM(
        CASE
            WHEN valores_distintos > 1
            THEN 1 ELSE 0
        END
    ) AS valor_cambio_entre_radicados,

    MAX(radicados) AS max_radicados,

    MAX(valores_distintos) AS max_valores_distintos

FROM comparacion

GROUP BY
    tipo_estado,
    variable_analitica

ORDER BY
    tipo_estado,
    variable_analitica;
GO