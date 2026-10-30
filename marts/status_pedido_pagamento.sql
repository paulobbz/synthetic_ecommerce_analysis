CREATE OR REPLACE TABLE marts.status_pedido_pagamento AS
WITH pagamento_por_pedido AS (
    SELECT
        pedido_id,
        count(*) AS pagamentos,
        count(*) FILTER (WHERE status = 'captured') AS capturados,
        count(*) FILTER (WHERE status = 'failed') AS falhos,
        count(*) FILTER (WHERE status = 'refunded') AS estornados,
        sum(valor) FILTER (WHERE status = 'captured') AS valor_capturado,
        sum(valor) FILTER (WHERE status = 'refunded') AS valor_estornado
    FROM refined.pagamentos
    GROUP BY pedido_id
)
SELECT
    o.canal,
    o.status AS status_pedido,
    count(*) AS pedidos,
    count(*) FILTER (WHERE coalesce(pg.capturados, 0) > 0)
        AS pedidos_com_captura,
    count(*) FILTER (WHERE coalesce(pg.falhos, 0) > 0)
        AS pedidos_com_falha,
    count(*) FILTER (WHERE coalesce(pg.estornados, 0) > 0)
        AS pedidos_com_estorno,
    count(*) FILTER (WHERE pg.pedido_id IS NULL)
        AS pedidos_sem_pagamento,
    sum(o.valor_total) AS valor_pedidos,
    coalesce(sum(pg.valor_capturado), 0) AS valor_capturado,
    coalesce(sum(pg.valor_estornado), 0) AS valor_estornado
FROM refined.pedidos AS o
LEFT JOIN pagamento_por_pedido AS pg
    ON pg.pedido_id = o.pedido_id
GROUP BY o.canal, o.status
ORDER BY o.canal, o.status;
