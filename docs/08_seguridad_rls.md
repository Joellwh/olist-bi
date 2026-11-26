# Seguridad a nivel de fila

**Fase:** 9 · **Decisión:** [D-022](decisiones.md#d-022--seguridad-por-fila-dinámica-con-una-tabla-por-gerente-y-estado)

Cada gerente regional ve solo los estados que tiene a cargo, y Dirección ve todo (requerimiento de [01_requerimientos.md](01_requerimientos.md)). El filtro está en el modelo semántico, no en el reporte: no depende de un segmentador que alguien pueda cambiar, y vale igual para cualquier reporte que use el modelo.

## 1. Cómo funciona

```
 inicio de sesión ──► USERPRINCIPALNAME() = "diego.alves@example.com"
                              │
                              ▼
   Gerentes (oculta)    email                     estado
                        diego.alves@example.com   AC, AM, AP, PA, RO, RR, TO,   ◄─ Norte
                                                  AL, BA, CE, MA, PB, PE, PI,   ◄─ Nordeste
                                                  RN, SE
                              │  rol "Gerente regional": [Estado (sigla)] IN { esos 16 estados }
                              ▼
                        dim_geografia ──► fact_items
                                     └──► fact_pedidos
```

- **La tabla de seguridad** es `dw.seguridad_gerentes`: una fila por gerente y estado. Se carga en el ETL ([sql/03_dw/15_seguridad_gerentes.sql](../sql/03_dw/15_seguridad_gerentes.sql)) y en Power BI se llama `Gerentes`, oculta y sin relaciones.
- **El filtro va sobre `dim_geografia`**, la geografía del cliente de cada pedido. Desde ahí baja a los dos hechos por las relaciones que ya existían, así que todas las medidas, todas las páginas y la página de detalle quedan filtradas sin tocar el DAX.
- **La propia tabla `Gerentes` también se filtra:** cada gerente ve solo su fila, y los roles estáticos no la ven. Los correos de los demás no quedan expuestos.

## 2. Los roles

| Rol | Tipo | Filtro | Para qué |
|---|---|---|---|
| `Dirección` | Sin filtro | — | Ve todo. Hace falta aunque no filtre: en el servicio de Power BI, quien no está en ningún rol de un modelo con seguridad no ve nada. |
| `Gerente regional` | Dinámico | `dim_geografia[Estado (sigla)] IN CALCULATETABLE ( VALUES ( Gerentes[Estado (sigla)] ), Gerentes[Email] = USERPRINCIPALNAME () )` | El que se usa: un solo rol para todos los gerentes. |
| `Región Norte`, `Región Nordeste`, `Región Centro-Oeste`, `Región Sudeste`, `Región Sur` | Estático | `dim_geografia[Región] = "<región>"` | Para comparar. Un gerente nuevo o una región reasignada obligan a cambiar el modelo y publicarlo de nuevo; con el dinámico alcanza con una fila en SQL. |

En Power BI Desktop se definen los roles y su filtro. Quién pertenece a cada rol se asigna en el servicio, al publicar (Fase 11).

## 3. Los gerentes de prueba

El dataset no trae usuarios, así que los gerentes son ficticios. Usan el dominio `example.com`, reservado para ejemplos: esos correos no existen ni pueden existir.

| Gerente | Correo | Región | Estados | Ventas | Pedidos |
|---|---|---|---:|---:|---:|
| Ana Souza | ana.souza@example.com | Sudeste | 4 | R$ 8.794.685,26 | 67.146 |
| Bruno Lima | bruno.lima@example.com | Sur | 3 | R$ 1.930.565,23 | 13.947 |
| Carla Rocha | carla.rocha@example.com | Centro-Oeste | 4 | R$ 859.469,14 | 5.712 |
| Diego Alves | diego.alves@example.com | Norte y Nordeste | 16 | R$ 1.864.810,05 | 11.100 |
| **Dirección** | — | todas | 27 | **R$ 13.449.529,68** | **97.905** |

Ventas y pedidos del período de análisis, calculados en SQL. Los cuatro gerentes suman exactamente el total de Dirección: ningún estado queda sin gerente y ninguno está en dos regiones. Diego tiene dos regiones a propósito, para probar que el filtro admite varios estados.

## 4. Qué protege que no se rompa

| Riesgo | Protección |
|---|---|
| Un estado mal escrito en la tabla de seguridad | Clave foránea a `dim_geografia(estado)`: la carga falla. |
| Una región mal escrita en la carga, que deja sus estados sin gerente | Validación **V16** (crítica) en el ETL: cada estado tiene al menos un gerente. Y un test compara las regiones de la carga con las de `dim_geografia`. |
| Que alguien borre un rol, le quite el filtro o deje visible la tabla de gerentes | Tests en [tests/test_modelo_semantico.py](../tests/test_modelo_semantico.py): roles declarados, `Dirección` sin filtro, el dinámico con `USERPRINCIPALNAME()` sobre `dim_geografia` y `Gerentes`, los estáticos sin acceso a `Gerentes`, la tabla oculta. |

## 5. Límites conocidos

- **Las dimensiones que no dependen de la geografía se ven completas.** Un gerente puede encontrar en un segmentador el nombre de un vendedor o una categoría que solo vende en otra región, aunque todas sus cifras salen vacías. Con los nombres anonimizados del dataset no expone nada. En un caso real, si el nombre del vendedor fuera sensible, habría que filtrar también `dim_vendedor`.
- **"Marketplace" pasa a significar "mi región".** En el detalle de vendedor, `Participación en el marketplace` y `Ticket del marketplace` quitan el filtro de vendedor con `REMOVEFILTERS`, pero la seguridad no se puede quitar: para un gerente, la comparación es contra su región. Es lo correcto para la seguridad, pero el texto de la tarjeta lo dice mal para un gerente.
- **El filtro es por la geografía del cliente.** Un gerente ve las ventas hechas *a* sus estados, no las de los vendedores *de* sus estados. Es la definición del requerimiento: cada región responde por sus clientes.

## 6. Cómo se prueba

En Power BI Desktop: **Modelado → Ver como**.

| Prueba | Qué elegir | Resultado esperado en Resumen |
|---|---|---|
| Dirección | Rol `Dirección` | R$ 13,4 mill. y 97,9 mil pedidos, como sin seguridad |
| Estático | Rol `Región Sudeste` | R$ 8,8 mill. y 67,1 mil pedidos; el filtro Región solo ofrece Sudeste |
| Dinámico, una región | **Otro usuario** = `ana.souza@example.com` y rol `Gerente regional` | Lo mismo que `Región Sudeste` |
| Dinámico, dos regiones | **Otro usuario** = `diego.alves@example.com` y rol `Gerente regional` | R$ 1,9 mill. y 11,1 mil pedidos; el filtro Región ofrece Norte y Nordeste |
| Usuario sin fila | **Otro usuario** = `nadie@example.com` y rol `Gerente regional` | Todo vacío |

**Resultados** (2026-11-26): los cinco casos dieron lo esperado en Power BI Desktop, con los datos actualizados desde SQL Server.
