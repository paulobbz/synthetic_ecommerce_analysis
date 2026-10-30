CREATE OR REPLACE TABLE marts.margem_estimada_produto AS
SELECT
    p.categoria,
    p.produto_id,
    p.nome_produto,
    sum(i.total_item) AS receita_itens_entregues,
    sum(i.quantidade * p.custo_unitario) AS custo_estimado,
    sum(i.total_item - i.quantidade * p.custo_unitario)
        AS margem_bruta_estimada,
    round(
        100.0 * sum(i.total_item - i.quantidade * p.custo_unitario)
            / nullif(sum(i.total_item), 0),
        2
    ) AS margem_pct
FROM refined.produtos AS p
JOIN refined.itens_pedido AS i
    ON i.produto_id = p.produto_id
JOIN refined.pedidos AS o
    ON o.pedido_id = i.pedido_id
WHERE o.status = 'delivered'
GROUP BY p.categoria, p.produto_id, p.nome_produto
ORDER BY margem_bruta_estimada DESC
LIMIT 10;
