CREATE OR REPLACE TABLE marts.recorrencia_clientes AS
WITH pedidos_cliente AS (
    SELECT
        cliente_id,
        count(*) FILTER (WHERE status = 'delivered') AS pedidos_entregues,
        sum(valor_total) FILTER (WHERE status = 'delivered') AS valor_entregue
    FROM refined.pedidos
    GROUP BY cliente_id
)
SELECT
    c.pais,
    c.nivel_fidelidade,
    count(*) AS clientes,
    count(*) FILTER (
        WHERE coalesce(pc.pedidos_entregues, 0) > 1
    ) AS clientes_recorrentes,
    round(
        100.0 * count(*) FILTER (
            WHERE coalesce(pc.pedidos_entregues, 0) > 1
        ) / count(*),
        2
    ) AS pct_recorrentes,
    round(avg(coalesce(pc.pedidos_entregues, 0)), 2)
        AS media_pedidos_entregues,
    coalesce(sum(pc.valor_entregue), 0) AS valor_entregue
FROM refined.clientes AS c
LEFT JOIN pedidos_cliente AS pc
    ON pc.cliente_id = c.cliente_id
GROUP BY c.pais, c.nivel_fidelidade
ORDER BY valor_entregue DESC;
