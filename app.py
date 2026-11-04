"""Página Streamlit do painel de e-commerce."""

from __future__ import annotations

import subprocess
import sys
from datetime import date

import duckdb
import pandas as pd
import streamlit as st
from plotly.graph_objects import Figure

import painel


@st.cache_data(show_spinner=False)
def _ler_marts() -> dict[str, pd.DataFrame]:
    return painel.ler(painel.MARTS)


def _marts_ausentes() -> list[str]:
    if not painel.CAMINHO_BANCO.is_file():
        return list(painel.MARTS)

    conexao = duckdb.connect(str(painel.CAMINHO_BANCO), read_only=True)
    try:
        existentes = {
            linha[0]
            for linha in conexao.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'marts'
                """
            ).fetchall()
        }
    finally:
        conexao.close()
    return [nome for nome in painel.MARTS if nome not in existentes]


def _preparar_banco() -> str | None:
    etapas = (
        ("ingestão", "pipeline.ingestao"),
        ("transformação", "pipeline.transformacao"),
        ("materialização dos marts", "pipeline.marts"),
    )
    for etapa, modulo in etapas:
        try:
            resultado = subprocess.run(
                [sys.executable, "-m", modulo],
                cwd=painel.CAMINHO_BANCO.parent,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError as erro:
            return f"Não foi possível iniciar a etapa de {etapa}: {erro}"

        if resultado.returncode:
            detalhes = "\n".join(
                saida
                for saida in (resultado.stdout.strip(), resultado.stderr.strip())
                if saida
            )
            if not detalhes:
                detalhes = f"Processo encerrado com código {resultado.returncode}."
            return f"Falha na etapa de {etapa}.\n{detalhes}"
    return None


def _mostrar_grafico(figura: Figure) -> None:
    st.plotly_chart(
        figura,
        width="stretch",
        config={"locale": "pt-BR", "responsive": True},
    )


st.set_page_config(page_title="Visão da operação", layout="wide")

try:
    marts_ausentes = _marts_ausentes()
except duckdb.Error as erro:
    st.error(f"Não foi possível verificar o banco {painel.CAMINHO_BANCO}: {erro}")
    st.stop()

if marts_ausentes:
    with st.spinner("Preparando o banco e os dados analíticos..."):
        erro_preparacao = _preparar_banco()
    if erro_preparacao:
        st.error(
            "Não foi possível preparar os dados para o painel. "
            f"{erro_preparacao}"
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
inicio_padrao = next(
    (mes for mes in meses if mes >= date(2026, 1, 1)),
    meses[0],
)

col_titulo, col_controles = st.columns([5, 7], vertical_alignment="center")
with col_titulo:
    st.title("E-commerce sintético · visão da operação")

with col_controles:
    col_periodo, col_recarregar = st.columns([5, 1], vertical_alignment="center")
    with col_periodo:
        inicio, fim = st.select_slider(
            "Período mensal",
            options=meses,
            value=(inicio_padrao, meses[-1]),
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
    "Receita entregue",
    painel.moeda_usd(ultimo_mes["vendas_entregues"]),
)
cartoes[0].caption(f"Mês: {painel.rotular_mes(ultimo_mes['mes'])}")
cartoes[1].metric(
    "Pedidos entregues",
    painel.numero(ultimo_mes["pedidos_entregues"]),
)
cartoes[1].caption(f"Mês: {painel.rotular_mes(ultimo_mes['mes'])}")
cartoes[2].metric(
    "Ticket médio",
    painel.moeda_usd(ultimo_mes["ticket_entregue"]),
)
cartoes[2].caption(f"Mês: {painel.rotular_mes(ultimo_mes['mes'])}")
cartoes[3].metric(
    "Produto líder · unidades",
    painel.numero(produto_lider["unidades_entregues"]),
)
cartoes[3].caption(str(produto_lider["nome_produto"]))
cartoes[4].metric(
    "Vendas do país líder",
    painel.moeda_usd(pais_lider["valor_vendido"]),
)
cartoes[4].caption(str(pais_lider["pais"]))

mensal_filtrado = mensal.loc[
    mensal["mes"].dt.date.between(inicio, fim)
]
_mostrar_grafico(painel.grafico_vendas_mensais(mensal_filtrado))

colunas = st.columns(2)
with colunas[0]:
    _mostrar_grafico(
        painel.grafico_produtos_mais_vendidos(dados["produtos_mais_vendidos"])
    )
with colunas[1]:
    _mostrar_grafico(
        painel.grafico_devolucoes_por_categoria(
            dados["devolucoes_por_categoria"]
        )
    )

_mostrar_grafico(painel.grafico_vendas_por_pais(dados["vendas_por_pais"]))
canal_pagamentos = st.selectbox(
    "Canal dos pagamentos",
    ("Todos", "Site", "Aplicativo", "Marketplace"),
)
_mostrar_grafico(
    painel.grafico_pagamentos_por_metodo(
        dados["pagamentos_por_metodo"], canal_pagamentos
    )
)

colunas = st.columns(2)
with colunas[0]:
    _mostrar_grafico(
        painel.grafico_entregas_por_transportadora(
            dados["entregas_por_transportadora"]
        )
    )
with colunas[1]:
    _mostrar_grafico(
        painel.grafico_descontos_por_canal(dados["descontos_por_canal"])
    )

colunas = st.columns(2)
with colunas[0]:
    paises = list(
        dict.fromkeys(dados["recorrencia_clientes"]["pais"].dropna().tolist())
    )
    pais_selecionado = st.selectbox(
        "País analisado · recorrência",
        options=paises,
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
_mostrar_grafico(
    painel.grafico_status_pedido_pagamento(dados["status_pedido_pagamento"])
)
