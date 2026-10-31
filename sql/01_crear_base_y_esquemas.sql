/* ============================================================
   PROYECTO DE GRADO
   Creación de base de datos y arquitectura inicial
   ============================================================ */

USE master;
GO

IF DB_ID('ProyectoGradoQuiebra') IS NULL
BEGIN
    CREATE DATABASE ProyectoGradoQuiebra;
END;
GO

ALTER DATABASE ProyectoGradoQuiebra
SET RECOVERY SIMPLE;
GO

USE ProyectoGradoQuiebra;
GO


/* ============================================================
   ESQUEMAS
   ============================================================ */

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'stg'
)
BEGIN
    EXEC('CREATE SCHEMA stg');
END;
GO


IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'analytics'
)
BEGIN
    EXEC('CREATE SCHEMA analytics');
END;
GO


IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'control'
)
BEGIN
    EXEC('CREATE SCHEMA control');
END;
GO


/* ============================================================
   TABLA DE CONTROL DE FUENTES
   ============================================================ */

IF OBJECT_ID(
    'control.fuentes_datos',
    'U'
) IS NULL
BEGIN
    CREATE TABLE control.fuentes_datos
    (
        id_fuente INT IDENTITY(1,1) PRIMARY KEY,
        nombre_fuente NVARCHAR(200) NOT NULL,
        archivo NVARCHAR(300) NOT NULL,
        tipo_fuente NVARCHAR(100) NULL,
        periodo_desde SMALLINT NULL,
        periodo_hasta SMALLINT NULL,
        ruta_relativa NVARCHAR(500) NULL,
        fecha_registro DATETIME2 NOT NULL
            DEFAULT SYSDATETIME(),
        observaciones NVARCHAR(1000) NULL
    );
END;
GO


/* ============================================================
   TABLA DE CONTROL DE CARGAS
   ============================================================ */

IF OBJECT_ID(
    'control.cargas',
    'U'
) IS NULL
BEGIN
    CREATE TABLE control.cargas
    (
        id_carga BIGINT IDENTITY(1,1) PRIMARY KEY,
        tabla_destino NVARCHAR(200) NOT NULL,
        archivo_origen NVARCHAR(300) NOT NULL,
        fecha_inicio DATETIME2 NULL,
        fecha_fin DATETIME2 NULL,
        filas_cargadas BIGINT NULL,
        estado NVARCHAR(30) NULL,
        observaciones NVARCHAR(1000) NULL
    );
END;
GO


/* ============================================================
   VERIFICACIÓN
   ============================================================ */

SELECT
    DB_NAME() AS base_datos,
    name AS esquema
FROM sys.schemas
WHERE name IN (
    'stg',
    'analytics',
    'control'
)
ORDER BY name;
GO