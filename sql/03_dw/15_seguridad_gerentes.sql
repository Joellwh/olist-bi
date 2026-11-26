/*
    dw.seguridad_gerentes: los estados que ve cada gerente regional (Fase 9, D-022).

    El dataset no trae usuarios: los gerentes son ficticios, con correos del
    dominio reservado example.com (no existen ni pueden existir). Se cargan
    por región, pero la tabla guarda estados, así un gerente puede tener
    cualquier combinación sin cambiar el modelo: Diego Alves tiene dos
    regiones, que es el caso que prueba que el filtro admite varios estados.

    Dirección no figura: su rol en Power BI no tiene filtro.
*/

USE [$(DB_NAME)];
GO

INSERT INTO dw.seguridad_gerentes (email, nombre, estado)
SELECT g.email, g.nombre, d.estado
FROM (VALUES (N'ana.souza@example.com',   N'Ana Souza',   N'Sudeste'),
             (N'bruno.lima@example.com',  N'Bruno Lima',  N'Sur'),
             (N'carla.rocha@example.com', N'Carla Rocha', N'Centro-Oeste'),
             (N'diego.alves@example.com', N'Diego Alves', N'Norte'),
             (N'diego.alves@example.com', N'Diego Alves', N'Nordeste')) AS g (email, nombre, region)
JOIN dw.dim_geografia AS d ON d.region = g.region;
GO
