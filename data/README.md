# Datos

**Fuente:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle, licencia CC BY-NC-SA 4.0).

Unos 100 mil pedidos reales y anonimizados de 2016 a 2018, hechos en varios marketplaces de Brasil.

## Por qué no están en el repo

Los 9 CSV pesan 126 MB en total; `olist_geolocation_dataset.csv` sola pesa 61 MB, más que el límite recomendado por GitHub. Además tienen licencia propia en Kaggle. Por eso `data/raw/` está en `.gitignore` y cada persona los descarga.

## Cómo obtenerlos

1. Descargar el zip desde Kaggle (requiere cuenta).
2. Extraerlo y verificarlo:

   ```bash
   python -m src.setup.extract_data "ruta/al/archive.zip"
   ```

   El script extrae los 9 archivos a `data/raw/` y comprueba que cada uno tenga la cantidad de filas esperada, definida en `src/paths.py`.

## Tablas

| Archivo | Filas | Contenido |
|---|---:|---|
| `olist_orders_dataset.csv` | 99.441 | Pedidos: estado y fechas de compra, aprobación, despacho, entrega real y estimada |
| `olist_order_items_dataset.csv` | 112.650 | Ítems de cada pedido: producto, vendedor, precio y flete |
| `olist_order_payments_dataset.csv` | 103.886 | Pagos: medio, cuotas y valor (un pedido puede tener varios) |
| `olist_order_reviews_dataset.csv` | 99.224 | Reseñas: puntaje de 1 a 5 y comentario |
| `olist_customers_dataset.csv` | 99.441 | Clientes: ciudad, estado y código postal |
| `olist_sellers_dataset.csv` | 3.095 | Vendedores: ciudad, estado y código postal |
| `olist_products_dataset.csv` | 32.951 | Productos: categoría, medidas y peso |
| `olist_geolocation_dataset.csv` | 1.000.163 | Latitud y longitud por código postal (con muchos repetidos) |
| `product_category_name_translation.csv` | 71 | Traducción de categorías del portugués al inglés |
