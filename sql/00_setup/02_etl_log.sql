/*
    Tablas de control del ETL (esquema etl). Guardan el historial de todas las
    ejecuciones: el pipeline las llena, nunca las vacía.

    Como el resto del setup, se puede correr las veces que haga falta.

      etl.log_ejecucion   una fila por corrida de python -m src.etl.run
      etl.log_paso        cada paso de una corrida: qué tabla, cuántas filas, cuánto tardó
      etl.log_validacion  el resultado de cada regla de docs/02_calidad_datos.md
*/

USE [$(DB_NAME)];
GO

IF OBJECT_ID(N'etl.log_ejecucion') IS NULL
CREATE TABLE etl.log_ejecucion (
    ejecucion_id INT IDENTITY(1, 1) NOT NULL CONSTRAINT pk_log_ejecucion PRIMARY KEY,
    inicio       DATETIME2(0)   NOT NULL CONSTRAINT df_log_ejecucion_inicio DEFAULT SYSDATETIME(),
    fin          DATETIME2(0)   NULL,
    estado       VARCHAR(10)    NOT NULL CONSTRAINT df_log_ejecucion_estado DEFAULT 'EN CURSO',
    mensaje      NVARCHAR(2000) NULL,
    usuario      NVARCHAR(128)  NOT NULL CONSTRAINT df_log_ejecucion_usuario DEFAULT SUSER_SNAME(),
    CONSTRAINT ck_log_ejecucion_estado CHECK (estado IN ('EN CURSO', 'OK', 'FALLA'))
);
GO

IF OBJECT_ID(N'etl.log_paso') IS NULL
CREATE TABLE etl.log_paso (
    paso_id      INT IDENTITY(1, 1) NOT NULL CONSTRAINT pk_log_paso PRIMARY KEY,
    ejecucion_id INT          NOT NULL CONSTRAINT fk_log_paso_ejecucion REFERENCES etl.log_ejecucion (ejecucion_id),
    capa         VARCHAR(10)  NOT NULL,   -- raw, stg
    objeto       VARCHAR(100) NOT NULL,   -- tabla o script
    filas        INT          NULL,
    inicio       DATETIME2(3) NOT NULL,
    fin          DATETIME2(3) NOT NULL,
    segundos     AS CAST(DATEDIFF(MILLISECOND, inicio, fin) / 1000.0 AS DECIMAL(9, 1))
);
GO

IF OBJECT_ID(N'etl.log_validacion') IS NULL
CREATE TABLE etl.log_validacion (
    validacion_id   INT IDENTITY(1, 1) NOT NULL CONSTRAINT pk_log_validacion PRIMARY KEY,
    ejecucion_id    INT           NOT NULL CONSTRAINT fk_log_validacion_ejecucion REFERENCES etl.log_ejecucion (ejecucion_id),
    codigo          VARCHAR(10)   NOT NULL,   -- V01, V02... (docs/02_calidad_datos.md)
    gravedad        VARCHAR(11)   NOT NULL,
    descripcion     NVARCHAR(300) NOT NULL,
    filas_afectadas INT           NOT NULL,
    resultado       VARCHAR(5)    NOT NULL,
    momento         DATETIME2(0)  NOT NULL CONSTRAINT df_log_validacion_momento DEFAULT SYSDATETIME(),
    CONSTRAINT ck_log_validacion_gravedad CHECK (gravedad IN ('CRITICA', 'ADVERTENCIA')),
    CONSTRAINT ck_log_validacion_resultado CHECK (resultado IN ('OK', 'FALLA', 'AVISO'))
);
GO
