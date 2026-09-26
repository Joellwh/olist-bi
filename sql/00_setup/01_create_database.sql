/*
    Crea la base del proyecto y sus esquemas. Se puede correr las veces que
    haga falta: si algo ya existe, no lo toca.

    Ejecución:
      - Python:  python -m src.setup.create_database
      - sqlcmd:  sqlcmd -S .\SQLEXPRESS -E -v DB_NAME=OlistDW -i sql/00_setup/01_create_database.sql
      - SSMS:    activar Consulta > Modo SQLCMD y agregar al inicio  :setvar DB_NAME OlistDW

    Esquemas (una capa por esquema, ver docs/decisiones.md):
      raw  datos tal cual vienen de los CSV, sin transformar
      stg  datos limpios y tipados (staging)
      dw   modelo dimensional: dimensiones y tablas de hechos
      rpt  vistas analíticas que consumen Power BI y los informes
      etl  control del pipeline: log de ejecuciones y resultados de validación
*/

IF DB_ID(N'$(DB_NAME)') IS NULL
    CREATE DATABASE [$(DB_NAME)];
GO

-- Modelo de recuperación SIMPLE: la base se reconstruye entera desde los CSV,
-- así que no hace falta un log de transacciones que crezca con cada carga.
ALTER DATABASE [$(DB_NAME)] SET RECOVERY SIMPLE;
GO

USE [$(DB_NAME)];
GO

IF SCHEMA_ID(N'raw') IS NULL EXEC(N'CREATE SCHEMA raw');
IF SCHEMA_ID(N'stg') IS NULL EXEC(N'CREATE SCHEMA stg');
IF SCHEMA_ID(N'dw')  IS NULL EXEC(N'CREATE SCHEMA dw');
IF SCHEMA_ID(N'rpt') IS NULL EXEC(N'CREATE SCHEMA rpt');
IF SCHEMA_ID(N'etl') IS NULL EXEC(N'CREATE SCHEMA etl');
GO
