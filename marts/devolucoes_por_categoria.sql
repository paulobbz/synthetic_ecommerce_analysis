CREATE OR REPLACE TABLE marts.devolucoes_por_categoria AS
WITH devolucao_por_item AS (
    SELECT
        item_pedido_id,
        count(DISTINCT devolucao_id) AS solicitacoes,
        count(DISTINCT item_pedido_id)
            FILTER (WHERE status = 'refunded') AS itens_reembolsados,
        sum(valor_reembolso)
            FILTER (WHERE status = 'refunded') AS valor_reembolsado
    FROM refined.devolucoes
    GROUP BY item_pedido_id
)
SELECT
    p.categoria,
    count(*) AS itens_pedidos,
    count(*) FILTER (WHERE d.solicitacoes > 0) AS itens_com_solicitacao,
    round(
        100.0 * count(*) FILTER (WHERE d.solicitacoes > 0) / count(*),
        2
    ) AS pct_itens_com_solicitacao,
    count(*) FILTER (WHERE d.itens_reembolsados > 0) AS itens_reembolsados,
    round(
        100.0 * count(*) FILTER (WHERE d.itens_reembolsados > 0) / count(*),
        2
    ) AS pct_itens_reembolsados,
    coalesce(sum(d.valor_reembolsado), 0) AS valor_reembolsado
FROM refined.itens_pedido AS i
JOIN refined.produtos AS p
    ON p.produto_id = i.produto_id
LEFT JOIN devolucao_por_item AS d
    ON d.item_pedido_id = i.item_pedido_id
GROUP BY p.categoria
ORDER BY pct_itens_com_solicitacao DESC;
