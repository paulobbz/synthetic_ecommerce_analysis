from datetime import date
from decimal import Decimal

import duckdb
import pandas as pd
import plotly.graph_objects as go
import pytest

import painel


def _dados_graficos():
    return {
        "vendas_mensais": pd.DataFrame(
            {
                "mes": [date(2025, 1, 1), date(2025, 2, 1)],
                "vendas_entregues": [Decimal("1250.50"), Decimal("875.25")],
            }
        ),
        "produtos_mais_vendidos": pd.DataFrame(
            {
                "nome_produto": ["Produto A", "Produto B"],
                "unidades_entregues": [4, 2],
            }
        ),
        "devolucoes_por_categoria": pd.DataFrame(
            {
                "categoria": ["Acessorios", "Livros"],
                "pct_itens_com_solicitacao": [50.0, 25.0],
                "pct_itens_reembolsados": [25.0, 0.0],
            }
        ),
        "vendas_por_pais": pd.DataFrame(
            {
                "pais": ["Brasil", "Chile"],
                "valor_vendido": [Decimal("120.00"), Decimal("80.00")],
            }
        ),
        "pagamentos_por_metodo": pd.DataFrame(
            {
                "canal": ["web", "loja", "web"],
                "metodo": ["cartao", "pix", "paypal"],
                "status_pagamento": ["captured", "failed", "refunded"],
                "valor_pagamentos": [
                    Decimal("120.00"),
                    Decimal("80.00"),
                    Decimal("30.00"),
                ],
            }
        ),
        "entregas_por_transportadora": pd.DataFrame(
            {
                "transportadora": ["Transportadora A", "Transportadora B"],
                "media_dias_envio_entrega": [2.0, 4.0],
                "pct_entregues": [100.0, 50.0],
            }
        ),
        "descontos_por_canal": pd.DataFrame(
            {
                "canal": ["web", "loja"],
                "status_pedido": ["delivered", "cancelled"],
                "pct_desconto_ponderado": [10.0, 5.0],
            }
        ),
        "recorrencia_clientes": pd.DataFrame(
            {
                "pais": ["Brasil", "Chile"],
                "nivel_fidelidade": ["gold", "silver"],
                "pct_recorrentes": [25.0, 50.0],
            }
        ),
        "margem_estimada_produto": pd.DataFrame(
            {
                "nome_produto": ["Produto A", "Produto B"],
                "margem_bruta_estimada": [
                    Decimal("40.00"),
                    Decimal("15.00"),
                ],
            }
        ),
        "status_pedido_pagamento": pd.DataFrame(
            {
                "canal": ["web", "loja"],
                "status_pedido": ["delivered", "cancelled"],
                "pedidos_com_captura": [2, 0],
                "pedidos_com_falha": [0, 1],
                "pedidos_com_estorno": [0, 0],
                "pedidos_sem_pagamento": [0, 1],
            }
        ),
    }


def test_formatadores_usam_separadores_e_casas_deterministicos():
    assert painel.moeda_usd(Decimal("1234567.8")) == "US$ 1.234.567,80"
    assert painel.pct(12.345, casas=2) == "12,35%"
    assert painel.numero(96470) == "96.470"


def test_rotular_mes_nao_depende_do_locale():
    assert painel.rotular_mes(date(2025, 1, 1)) == "jan/2025"
    assert painel.rotular_mes(date(2025, 12, 1)) == "dez/2025"


def test_ler_retorna_dataframe_do_mart_temporario(monkeypatch, tmp_path):
    caminho = tmp_path / "painel.duckdb"
    conexao = duckdb.connect(str(caminho))
    conexao.execute("CREATE SCHEMA marts")
    conexao.execute(
        "CREATE TABLE marts.vendas_mensais AS "
        "SELECT DATE '2025-01-01' AS mes, 25 AS vendas"
    )
    conexao.close()
    monkeypatch.setattr(painel, "CAMINHO_BANCO", caminho)

    dados = painel.ler(["vendas_mensais"])

    assert list(dados) == ["vendas_mensais"]
    assert dados["vendas_mensais"].to_dict(orient="records") == [
        {"mes": pd.Timestamp("2025-01-01"), "vendas": 25}
    ]


def test_ler_rejeita_nome_de_mart_nao_permitido(tmp_path):
    with pytest.raises(ValueError, match="Marts não permitidos"):
        painel.ler(["pedidos"])

    assert not (tmp_path / "ecommerce.duckdb").exists()


def test_ler_informa_mart_ausente_e_fecha_conexao(monkeypatch, tmp_path):
    caminho = tmp_path / "painel.duckdb"
    conexao = duckdb.connect(str(caminho))
    conexao.execute("CREATE SCHEMA marts")
    conexao.execute("CREATE TABLE marts.vendas_mensais (mes DATE)")
    conexao.close()
    monkeypatch.setattr(painel, "CAMINHO_BANCO", caminho)

    with pytest.raises(painel.MartsAusentesError) as erro:
        painel.ler(["vendas_mensais", "produtos_mais_vendidos"])

    conexao = duckdb.connect(str(caminho))
    try:
        conexao.execute("CREATE TABLE marts.confirmacao_fechamento (valor INTEGER)")
        assert erro.value.nomes == ("produtos_mais_vendidos",)
    finally:
        conexao.close()


def test_funcoes_de_grafico_geram_figuras_com_dados_dos_marts():
    dados = _dados_graficos()
    figuras = {
        "mensal": painel.grafico_vendas_mensais(dados["vendas_mensais"]),
        "produtos": painel.grafico_produtos_mais_vendidos(
            dados["produtos_mais_vendidos"]
        ),
        "devolucoes": painel.grafico_devolucoes_por_categoria(
            dados["devolucoes_por_categoria"]
        ),
        "paises": painel.grafico_vendas_por_pais(dados["vendas_por_pais"]),
        "pagamentos": painel.grafico_pagamentos_por_metodo(
            dados["pagamentos_por_metodo"]
        ),
        "entregas": painel.grafico_entregas_por_transportadora(
            dados["entregas_por_transportadora"]
        ),
        "descontos": painel.grafico_descontos_por_canal(
            dados["descontos_por_canal"]
        ),
        "recorrencia": painel.grafico_recorrencia_clientes(
            dados["recorrencia_clientes"], None
        ),
        "margem": painel.grafico_margem_estimada_produto(
            dados["margem_estimada_produto"]
        ),
        "status": painel.grafico_status_pedido_pagamento(
            dados["status_pedido_pagamento"]
        ),
    }

    assert all(isinstance(figura, go.Figure) for figura in figuras.values())
    assert list(figuras["mensal"].data[0].x) == ["jan/2025", "fev/2025"]
    assert list(figuras["mensal"].data[0].y) == [1250.5, 875.25]
    assert list(figuras["mensal"].data[0].text) == ["1.250", "875"]
    assert figuras["mensal"].data[0].textposition == "top center"
    assert figuras["mensal"].data[0].mode == "lines+markers+text"
    assert figuras["mensal"].layout.yaxis.showticklabels is False
    assert list(figuras["produtos"].data[0].y) == ["Produto A", "Produto B"]
    assert list(figuras["produtos"].data[0].text) == ["4", "2"]
    assert figuras["produtos"].layout.xaxis.showticklabels is False
    assert len(figuras["devolucoes"].data) == 2
    assert [trace.name for trace in figuras["devolucoes"].data] == [
        "Com solicitação",
        "Com reembolso",
    ]
    assert list(figuras["devolucoes"].data[0].text) == ["50,0%", "25,0%"]
    assert figuras["devolucoes"].layout.xaxis.autorange is True
    assert figuras["devolucoes"].layout.xaxis.range is None
    assert list(figuras["paises"].data[0].y) == ["Brasil", "Chile"]
    assert list(figuras["paises"].data[0].text) == ["120", "80"]
    assert figuras["paises"].layout.xaxis.showticklabels is False
    assert len(figuras["pagamentos"].data) == 3
    assert {trace.name for trace in figuras["pagamentos"].data} == {
        "Capturado",
        "Falhou",
        "Reembolsado",
    }
    assert {valor for trace in figuras["pagamentos"].data for valor in trace.y} == {
        "Cartão",
        "Pix",
        "PayPal",
    }
    assert figuras["pagamentos"].layout.barmode == "stack"
    assert figuras["pagamentos"].layout.barnorm == "percent"
    assert figuras["pagamentos"].layout.xaxis.title.text == "% do valor"
    assert all(trace.orientation == "h" for trace in figuras["pagamentos"].data)
    assert all(trace.text is not None for trace in figuras["pagamentos"].data)
    assert all(trace.textposition == "inside" for trace in figuras["pagamentos"].data)
    assert all(
        str(rotulo).startswith("US$ ")
        for trace in figuras["pagamentos"].data
        for rotulo in trace.text
    )
    assert all(
        "US$ %{customdata[0]:,.2f}" in trace.hovertemplate
        for trace in figuras["pagamentos"].data
    )
    assert {trace.name: trace.marker.color for trace in figuras["pagamentos"].data} == {
        "Capturado": painel.AZUL,
        "Falhou": "#E15759",
        "Reembolsado": "#F28E2B",
    }
    site = painel.grafico_pagamentos_por_metodo(
        dados["pagamentos_por_metodo"], "Site"
    )
    assert {valor for trace in site.data for valor in trace.y} == {
        "Cartão",
        "PayPal",
    }
    assert list(figuras["entregas"].data[0].header.values) == [
        "Transportadora",
        "Prazo médio<br>envio–entrega",
        "Pedidos<br>entregues",
    ]
    assert len(figuras["descontos"].data) == 2
    assert list(figuras["descontos"].data[0].x) == ["Site"]
    assert figuras["descontos"].data[0].name == "Entregue"
    assert list(figuras["descontos"].data[0].text) == ["10,0%"]
    assert len(figuras["recorrencia"].data) == 2
    assert figuras["recorrencia"].data[0].visible is True
    assert figuras["recorrencia"].data[1].visible is False
    assert list(figuras["recorrencia"].data[0].x) == ["Ouro"]
    assert list(figuras["recorrencia"].data[0].text) == ["25,0%"]
    assert figuras["recorrencia"].layout.yaxis.showticklabels is False
    assert len(figuras["margem"].data[0].y) == 2
    assert list(figuras["margem"].data[0].text) == ["40", "15"]
    assert len(figuras["status"].data) == 1
    assert list(figuras["status"].data[0].x) == [
        "Captura",
        "Falha",
        "Estorno",
        "Sem pagamento",
    ]
    assert list(figuras["status"].data[0].y) == [
        "Cancelado · Loja",
        "Entregue · Site",
    ]
    assert list(figuras["status"].data[0].text[0]) == ["0", "1", "0", "1"]
    assert list(figuras["status"].data[0].text[1]) == ["2", "0", "0", "0"]


def test_grafico_pagamentos_agrega_status_e_filtra_canal():
    dados = pd.DataFrame(
        {
            "canal": ["web", "app", "web"],
            "metodo": ["card", "card", "card"],
            "status_pagamento": ["captured", "captured", "failed"],
            "valor_pagamentos": [100, 300, 50],
        }
    )

    todos = painel.grafico_pagamentos_por_metodo(dados)
    capturados_todos = next(
        trace for trace in todos.data if trace.name == "Capturado"
    )
    falhas_todas = next(trace for trace in todos.data if trace.name == "Falhou")
    assert list(capturados_todos.x) == [400]
    assert list(falhas_todas.x) == [50]

    site = painel.grafico_pagamentos_por_metodo(dados, "Site")
    capturados_site = next(
        trace for trace in site.data if trace.name == "Capturado"
    )
    falhas_site = next(trace for trace in site.data if trace.name == "Falhou")
    assert list(capturados_site.x) == [100]
    assert list(falhas_site.x) == [50]


def test_grafico_de_recorrencia_filtra_somente_o_pais_selecionado():
    dados = _dados_graficos()["recorrencia_clientes"]

    figura = painel.grafico_recorrencia_clientes(dados, "Brasil")

    assert len(figura.data) == 1
    assert figura.data[0].name == "Brasil"
    assert list(figura.data[0].y) == [25.0]
