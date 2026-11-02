"""Página Streamlit do painel de e-commerce."""

from __future__ import annotations

import duckdb
import pandas as pd
import streamlit as st
from plotly.graph_objects import Figure

import painel


@st.cache_data(show_spinner=False)
def _ler_marts() -> dict[str, pd.DataFrame]:
    return painel.ler(painel.MARTS)


def _mostrar_grafico(figura: Figure) -> None:
    st.plotly_chart(
        figura,
        width="stretch",
        config={"locale": "pt-BR", "responsive": True},
    )


st.set_page_config(page_title="Visão da operação", layout="wide")

if not painel.CAMINHO_BANCO.is_file():
    st.error(
        f"Banco não encontrado: {painel.CAMINHO_BANCO}. "
        "Execute a ingestão, a transformação e os marts; para recriar os "
        "marts, rode `uv run python -m pipeline.marts`."
    )
    st.stop()

try:
    dados = _ler_marts()
except painel.MartsAusentesError as erro:
    faltantes = ", ".join(f"`marts.{nome}`" for nome in erro.nomes)
    st.error(
        f"Marts ausentes: {faltantes}. "
        "Execute `uv run python -m pipeline.marts`."
    )
    st.stop()
except duckdb.Error as erro:
    st.error(
        f"Não foi possível ler o banco {painel.CAMINHO_BANCO}: {erro}. "
        "Confirme que o arquivo está íntegro e, para recriar os marts, rode "
        "`uv run python -m pipeline.marts`."
    )
    st.stop()

meses = sorted(dados["vendas_mensais"]["mes"].dt.date.unique())
if not meses:
    st.error(
        "`marts.vendas_mensais` não contém meses. "
        "Execute `uv run python -m pipeline.marts`."
    )
    st.stop()

col_titulo, col_controles = st.columns([5, 7], vertical_alignment="center")
with col_titulo:
    st.title("E-commerce sintético · visão da operação")

with col_controles:
    col_periodo, col_recarregar = st.columns([5, 1], vertical_alignment="center")
    with col_periodo:
        inicio, fim = st.select_slider(
            "Período mensal",
            options=meses,
            value=(meses[0], meses[-1]),
            format_func=painel.rotular_mes,
        )
        st.caption("O filtro altera somente o gráfico de vendas mensais.")
    with col_recarregar:
        st.write("")
        st.button(
            "Recarregar dados",
            on_click=_ler_marts.clear,
            width="stretch",
        )

mensal = dados["vendas_mensais"]
ultimo_mes = mensal.sort_values("mes").iloc[-1]
produto_lider = dados["produtos_mais_vendidos"].iloc[0]
pais_lider = dados["vendas_por_pais"].iloc[0]

cartoes = st.columns(5)
cartoes[0].metric(
    "Receita entregue · último mês disponível",
    painel.moeda_usd(ultimo_mes["vendas_entregues"]),
)
cartoes[1].metric(
    "Pedidos entregues · último mês disponível",
    painel.numero(ultimo_mes["pedidos_entregues"]),
)
cartoes[2].metric(
    "Ticket médio · último mês disponível",
    painel.moeda_usd(ultimo_mes["ticket_entregue"]),
)
cartoes[3].metric(
    "Produto líder · unidades entregues",
    str(produto_lider["nome_produto"]),
    delta=f'{painel.numero(produto_lider["unidades_entregues"])} unidades',
)
cartoes[4].metric(
    "País líder · vendas entregues",
    str(pais_lider["pais"]),
    delta=painel.moeda_usd(pais_lider["valor_vendido"]),
)

mensal_filtrado = mensal.loc[
    mensal["mes"].dt.date.between(inicio, fim)
]
_mostrar_grafico(painel.grafico_vendas_mensais(mensal_filtrado))

colunas = st.columns(3)
with colunas[0]:
    _mostrar_grafico(
        painel.grafico_produtos_mais_vendidos(dados["produtos_mais_vendidos"])
    )
with colunas[1]:
    _mostrar_grafico(painel.grafico_vendas_por_pais(dados["vendas_por_pais"]))
with colunas[2]:
    _mostrar_grafico(
        painel.grafico_pagamentos_por_metodo(dados["pagamentos_por_metodo"])
    )

colunas = st.columns(3)
with colunas[0]:
    _mostrar_grafico(
        painel.grafico_devolucoes_por_categoria(
            dados["devolucoes_por_categoria"]
        )
    )
with colunas[1]:
    _mostrar_grafico(
        painel.grafico_entregas_por_transportadora(
            dados["entregas_por_transportadora"]
        )
    )
with colunas[2]:
    _mostrar_grafico(painel.grafico_descontos_por_canal(dados["descontos_por_canal"]))

colunas = st.columns(3)
with colunas[0]:
    paises = sorted(dados["recorrencia_clientes"]["pais"].dropna().unique())
    pais_selecionado = st.selectbox(
        "País · recorrência",
        options=[None, *paises],
        format_func=lambda pais: "Todos os países" if pais is None else pais,
    )
    _mostrar_grafico(
        painel.grafico_recorrencia_clientes(
            dados["recorrencia_clientes"], pais_selecionado
        )
    )
with colunas[1]:
    _mostrar_grafico(
        painel.grafico_margem_estimada_produto(dados["margem_estimada_produto"])
    )
with colunas[2]:
    _mostrar_grafico(
        painel.grafico_status_pedido_pagamento(dados["status_pedido_pagamento"])
    )
