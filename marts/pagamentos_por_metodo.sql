CREATE OR REPLACE TABLE marts.pagamentos_por_metodo AS
SELECT
    o.canal,
    pg.metodo,
    pg.status AS status_pagamento,
    count(DISTINCT pg.pagamento_id) AS pagamentos,
    count(DISTINCT pg.pedido_id) AS pedidos,
    sum(pg.valor) AS valor_pagamentos
FROM refined.pagamentos AS pg
JOIN refined.pedidos AS o
    ON o.pedido_id = pg.pedido_id
GROUP BY o.canal, pg.metodo, pg.status
ORDER BY pagamentos DESC;
