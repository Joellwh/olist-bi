/*
    dw.dim_geografia: los 27 estados de Brasil con su región.

    Es la geografía del CLIENTE al momento del pedido (regla R9): la que usan
    los filtros de región y la seguridad por fila de la Fase 9. La del
    vendedor va como atributo de dim_vendedor.

    Los estados y regiones son datos de referencia fijos (no vienen del
    dataset), por eso se escriben acá y no se cargan de un archivo.
*/

USE [$(DB_NAME)];
GO

INSERT INTO dw.dim_geografia (geografia_key, estado, estado_nombre, region)
VALUES (-1, '--', N'Desconocido', N'Desconocida'),
       ( 1, 'AC', N'Acre', N'Norte'),
       ( 2, 'AL', N'Alagoas', N'Nordeste'),
       ( 3, 'AP', N'Amapá', N'Norte'),
       ( 4, 'AM', N'Amazonas', N'Norte'),
       ( 5, 'BA', N'Bahía', N'Nordeste'),
       ( 6, 'CE', N'Ceará', N'Nordeste'),
       ( 7, 'DF', N'Distrito Federal', N'Centro-Oeste'),
       ( 8, 'ES', N'Espírito Santo', N'Sudeste'),
       ( 9, 'GO', N'Goiás', N'Centro-Oeste'),
       (10, 'MA', N'Maranhão', N'Nordeste'),
       (11, 'MT', N'Mato Grosso', N'Centro-Oeste'),
       (12, 'MS', N'Mato Grosso do Sul', N'Centro-Oeste'),
       (13, 'MG', N'Minas Gerais', N'Sudeste'),
       (14, 'PA', N'Pará', N'Norte'),
       (15, 'PB', N'Paraíba', N'Nordeste'),
       (16, 'PR', N'Paraná', N'Sur'),
       (17, 'PE', N'Pernambuco', N'Nordeste'),
       (18, 'PI', N'Piauí', N'Nordeste'),
       (19, 'RJ', N'Río de Janeiro', N'Sudeste'),
       (20, 'RN', N'Rio Grande do Norte', N'Nordeste'),
       (21, 'RS', N'Rio Grande do Sul', N'Sur'),
       (22, 'RO', N'Rondônia', N'Norte'),
       (23, 'RR', N'Roraima', N'Norte'),
       (24, 'SC', N'Santa Catarina', N'Sur'),
       (25, 'SP', N'São Paulo', N'Sudeste'),
       (26, 'SE', N'Sergipe', N'Nordeste'),
       (27, 'TO', N'Tocantins', N'Norte');
GO
