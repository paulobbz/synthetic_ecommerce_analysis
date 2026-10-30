CREATE OR REPLACE TABLE marts.vendas_por_pais AS
SELECT
    c.pais,
    count(DISTINCT o.pedido_id) AS pedidos_entregues,
    count(DISTINCT o.cliente_id) AS clientes_com_compra,
    sum(o.valor_total) AS valor_vendido,
    round(avg(o.valor_total), 2) AS ticket_medio
FROM refined.pedidos AS o
JOIN refined.clientes AS c
    ON c.cliente_id = o.cliente_id
WHERE o.status = 'delivered'
GROUP BY c.pais
ORDER BY valor_vendido DESC;
