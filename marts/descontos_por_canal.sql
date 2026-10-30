CREATE OR REPLACE TABLE marts.descontos_por_canal AS
WITH itens_por_pedido AS (
    SELECT pedido_id, sum(quantidade) AS unidades
    FROM refined.itens_pedido
    GROUP BY pedido_id
)
SELECT
    o.canal,
    o.status AS status_pedido,
    count(*) AS pedidos,
    sum(o.subtotal) AS subtotal,
    sum(o.valor_desconto) AS descontos,
    round(
        100.0 * sum(o.valor_desconto) / nullif(sum(o.subtotal), 0),
        2
    ) AS pct_desconto_ponderado,
    round(
        avg(100.0 * o.valor_desconto / nullif(o.subtotal, 0)),
        2
    ) AS pct_desconto_medio_por_pedido,
    sum(coalesce(i.unidades, 0)) AS unidades
FROM refined.pedidos AS o
LEFT JOIN itens_por_pedido AS i
    ON i.pedido_id = o.pedido_id
GROUP BY o.canal, o.status
ORDER BY o.canal, o.status;
