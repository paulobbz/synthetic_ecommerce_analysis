import re
from datetime import date
from decimal import Decimal

import duckdb
import pandas as pd

import painel
from pipeline import painel_html


def _dados_sinteticos():
    return {
        "vendas_mensais": pd.DataFrame(
            {
                "mes": pd.to_datetime([date(2025, 1, 1), date(2025, 2, 1)]),
                "pedidos_entregues": [2, 1],
                "vendas_entregues": [Decimal("35.00"), Decimal("20.00")],
                "ticket_entregue": [17.5, 20.0],
            }
        ),
        "produtos_mais_vendidos": pd.DataFrame(
            {
                "nome_produto": ["Produto A", "Produto B"],
                "unidades_entregues": [3, 1],
            }
        ),
        "devolucoes_por_categoria": pd.DataFrame(
            {
                "categoria": ["Equipamento", "Roupa"],
                "pct_itens_com_solicitacao": [50.0, 0.0],
                "pct_itens_reembolsados": [25.0, 0.0],
            }
        ),
        "vendas_por_pais": pd.DataFrame(
            {
                "pais": ["Brasil", "Chile"],
                "valor_vendido": [Decimal("35.00"), Decimal("20.00")],
            }
        ),
        "pagamentos_por_metodo": pd.DataFrame(
            {
                "canal": ["web", "loja"],
                "metodo": ["card", "pix"],
                "status_pagamento": ["captured", "failed"],
                "valor_pagamentos": [Decimal("35.00"), Decimal("20.00")],
            }
        ),
        "entregas_por_transportadora": pd.DataFrame(
            {
                "transportadora": ["Correios", "Rápida"],
                "media_dias_envio_entrega": [2.0, 4.0],
                "pct_entregues": [100.0, 50.0],
            }
        ),
        "descontos_por_canal": pd.DataFrame(
            {
                "canal": ["web", "loja"],
                "status_pedido": ["delivered", "cancelled"],
                "pct_desconto_ponderado": [0.0, 10.0],
            }
        ),
        "recorrencia_clientes": pd.DataFrame(
            {
                "pais": ["Brasil", "Chile"],
                "nivel_fidelidade": ["gold", "silver"],
                "clientes": [2, 1],
                "clientes_recorrentes": [1, 0],
                "pct_recorrentes": [50.0, 0.0],
                "media_pedidos_entregues": [1.5, 1.0],
                "valor_entregue": [Decimal("35.00"), Decimal("20.00")],
            }
        ),
        "margem_estimada_produto": pd.DataFrame(
            {
                "nome_produto": ["Produto A", "Produto B"],
                "margem_bruta_estimada": [
                    Decimal("10.00"),
                    Decimal("5.00"),
                ],
            }
        ),
        "status_pedido_pagamento": pd.DataFrame(
            {
                "canal": ["web", "loja"],
                "status_pedido": ["delivered", "cancelled"],
                "pedidos_com_captura": [1, 0],
                "pedidos_com_falha": [0, 1],
                "pedidos_com_estorno": [0, 0],
                "pedidos_sem_pagamento": [0, 0],
            }
        ),
    }


def _criar_banco_marts(caminho, dados):
    conexao = duckdb.connect(str(caminho))
    conexao.execute("CREATE SCHEMA marts")
    try:
        for nome, dataframe in dados.items():
            conexao.register("df_mart_teste", dataframe)
            conexao.execute(
                f'CREATE TABLE marts."{nome}" AS SELECT * FROM df_mart_teste'
            )
            conexao.unregister("df_mart_teste")
    finally:
        conexao.close()


def test_montar_html_inclui_cartoes_graficos_e_filtros():
    dados = _dados_sinteticos()

    html = painel_html.montar_html(dados)

    assert html.count('class="metric"') == 5
    assert len(re.findall(r'id="grafico-[^"]+"', html)) == 10
    assert "US$ 35,00" in html
    assert "Produto A" in html
    assert "Brasil" in html
    assert "jan/2025" in html
    assert "fev/2025" in html
    assert 'id="filtro-pais"' in html
    assert "Plotly.restyle" in html
    assert not re.search(r'<script[^>]+src=["\']https?://', html, re.IGNORECASE)


def test_gerar_salva_html_com_dados_do_duckdb_temporario(
    monkeypatch, tmp_path
):
    dados = _dados_sinteticos()
    caminho_banco = tmp_path / "painel.duckdb"
    _criar_banco_marts(caminho_banco, dados)
    monkeypatch.setattr(painel, "CAMINHO_BANCO", caminho_banco)
    caminho_html = tmp_path / "dashboard.html"

    resultado = painel_html.gerar(caminho_html)

    html = caminho_html.read_text(encoding="utf-8")
    assert resultado == caminho_html
    assert caminho_html.is_file()
    assert html.startswith("<!doctype html>")
    assert html.count('class="metric"') == 5
    assert "Produto A" in html
