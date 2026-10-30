CREATE OR REPLACE TABLE marts.vendas_mensais AS
SELECT
    date_trunc('month', data_pedido)::DATE AS mes,
    count(*) AS pedidos_total,
    count(*) FILTER (WHERE status = 'delivered') AS pedidos_entregues,
    sum(valor_total) AS valor_pedido_registrado,
    sum(valor_total) FILTER (WHERE status = 'delivered') AS vendas_entregues,
    round(avg(valor_total) FILTER (WHERE status = 'delivered'), 2) AS ticket_entregue
FROM refined.pedidos
GROUP BY 1
ORDER BY 1;
