USE ProyectoGradoQuiebra;
GO

/* ============================================================
   TABLA FINANCIERA CONSOLIDADA
   ============================================================ */

IF OBJECT_ID('stg.financieros_variables', 'U') IS NULL
BEGIN
    CREATE TABLE stg.financieros_variables
    (
        id_registro BIGINT IDENTITY(1,1) PRIMARY KEY,

        fuente_estado NVARCHAR(50) NOT NULL,
        archivo_origen NVARCHAR(300) NOT NULL,

        codigo_instancia NVARCHAR(150) NULL,
        nit NVARCHAR(50) NULL,
        nit_normalizado NVARCHAR(50) NULL,
        numero_radicado NVARCHAR(100) NULL,

        id_punto_entrada NVARCHAR(100) NULL,
        punto_entrada NVARCHAR(500) NULL,

        id_taxonomia NVARCHAR(100) NULL,
        taxonomia NVARCHAR(500) NULL,

        fecha_corte NVARCHAR(100) NULL,
        anio_corte SMALLINT NULL,

        concepto NVARCHAR(1000) NULL,
        variable_analitica NVARCHAR(100) NOT NULL,

        periodo NVARCHAR(300) NULL,
        valor NVARCHAR(300) NULL,

        fecha_carga DATETIME2 NOT NULL
            DEFAULT SYSDATETIME()
    );
END;
GO


/* ============================================================
   HISTÓRICO DE INSOLVENCIA
   ============================================================ */

IF OBJECT_ID('stg.insolvencia_historial', 'U') IS NULL
BEGIN
    CREATE TABLE stg.insolvencia_historial
    (
        id_registro BIGINT IDENTITY(1,1) PRIMARY KEY,

        nro NVARCHAR(50) NULL,
        nit NVARCHAR(50) NULL,
        nit_normalizado NVARCHAR(50) NULL,
        nombre NVARCHAR(500) NULL,

        regional NVARCHAR(200) NULL,
        departamento NVARCHAR(200) NULL,
        ciudad NVARCHAR(200) NULL,

        ciiu NVARCHAR(100) NULL,
        macrosector NVARCHAR(300) NULL,
        proceso NVARCHAR(500) NULL,
        categoria_ss NVARCHAR(500) NULL,

        activos NVARCHAR(150) NULL,
        pasivos NVARCHAR(150) NULL,
        empleos NVARCHAR(100) NULL,

        anio_apertura SMALLINT NULL,
        fecha_generacion NVARCHAR(150) NULL,

        corte_anio SMALLINT NULL,
        archivo_origen NVARCHAR(300) NULL,

        fecha_carga DATETIME2 NOT NULL
            DEFAULT SYSDATETIME()
    );
END;
GO


/* ============================================================
   MAESTRA DE INSOLVENCIA
   ============================================================ */

IF OBJECT_ID('stg.insolvencia_maestra', 'U') IS NULL
BEGIN
    CREATE TABLE stg.insolvencia_maestra
    (
        nit_normalizado NVARCHAR(50) NOT NULL PRIMARY KEY,

        primer_corte SMALLINT NULL,
        ultimo_corte SMALLINT NULL,
        num_cortes TINYINT NULL,

        cortes_presentes NVARCHAR(100) NULL,

        anio_primera_apertura SMALLINT NULL,
        anio_ultima_apertura SMALLINT NULL,

        registro_insolvencia BIT NOT NULL
    );
END;
GO


/* ============================================================
   VERIFICACIÓN
   ============================================================ */

SELECT
    s.name AS esquema,
    t.name AS tabla
FROM sys.tables t
INNER JOIN sys.schemas s
    ON t.schema_id = s.schema_id
WHERE s.name = 'stg'
ORDER BY t.name;
GO