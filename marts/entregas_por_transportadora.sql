CREATE OR REPLACE TABLE marts.entregas_por_transportadora AS
SELECT
    r.transportadora,
    count(*) AS remessas,
    count(*) FILTER (WHERE r.data_entrega IS NOT NULL) AS entregues,
    round(
        100.0 * count(*) FILTER (WHERE r.data_entrega IS NOT NULL) / count(*),
        2
    ) AS pct_entregues,
    round(
        avg(date_diff('day', r.data_envio, r.data_entrega))
            FILTER (WHERE r.data_entrega IS NOT NULL),
        2
    ) AS media_dias_envio_entrega,
    round(
        avg(date_diff('day', CAST(o.data_pedido AS DATE), r.data_entrega))
            FILTER (WHERE r.data_entrega IS NOT NULL),
        2
    ) AS media_dias_pedido_entrega
FROM refined.remessas AS r
JOIN refined.pedidos AS o
    ON o.pedido_id = r.pedido_id
GROUP BY r.transportadora
ORDER BY media_dias_envio_entrega;
