CREATE OR REPLACE TABLE marts.produtos_mais_vendidos AS
SELECT
    p.produto_id,
    p.nome_produto,
    p.categoria,
    sum(i.quantidade) AS unidades_entregues,
    count(*) AS linhas_pedido,
    sum(i.total_item) AS receita_itens
FROM refined.itens_pedido AS i
JOIN refined.produtos AS p
    ON p.produto_id = i.produto_id
JOIN refined.pedidos AS o
    ON o.pedido_id = i.pedido_id
WHERE o.status = 'delivered'
GROUP BY p.produto_id, p.nome_produto, p.categoria
ORDER BY unidades_entregues DESC
LIMIT 10;
