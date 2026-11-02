"""SPEC DO PAINEL — VISUALIZAÇÃO DOS MARTS

CONTEXTO E STACK
Este projeto analisa um dataset sintético de comércio eletrônico com Python
3.12+, uv, DuckDB 1.5.6, Streamlit e Plotly. Esta spec é a fonte da verdade
do painel; o código não deve acrescentar regras de negócio. A ingestão, a
transformação e a materialização SQL dos marts já existem e não são
reimplementadas aqui.

ARTEFATOS
Este módulo, na raiz, reúne a leitura, a formatação e uma função Plotly por
gráfico. app.py monta a página e é executado por:
    uv run streamlit run app.py

1. LEITURA
ler(nomes_marts) devolve um dict de nome para DataFrame. Para cada nome,
executa somente SELECT * FROM marts.<nome>. Apenas os dez marts listados
abaixo são aceitos; as consultas SQL existentes são a fonte das métricas.

A conexão usa duckdb.connect(caminho, read_only=True), aponta para
ecommerce.duckdb na raiz do projeto e é fechada dentro da função, inclusive
em caso de erro. O caminho vem da localização deste arquivo, não da pasta
corrente. Assim, o painel sempre lê o banco correto e não mantém uma
conexão que impeça o pipeline de gravar.

Marts lidos:
vendas_mensais, produtos_mais_vendidos, devolucoes_por_categoria,
vendas_por_pais, pagamentos_por_metodo, entregas_por_transportadora,
descontos_por_canal, recorrencia_clientes, margem_estimada_produto e
status_pedido_pagamento.

Os valores monetários são USD. vendas_entregues não é o mesmo que
valor_pedido_registrado, que inclui pedidos em outros status. A margem é
estimada pelo custo atual e não deduz frete, impostos, descontos alocados
ou reembolsos.

2. SEM CÁLCULO DE NEGÓCIO
É proibido criar, recompor ou agregar métricas no painel. São permitidos
ordenar e filtrar linhas, selecionar ou renomear colunas, limitar linhas,
formatar valores como texto e selecionar registros já calculados.
Apresentações que precisem de novas métricas devem parar e identificar o
mart ou a coluna ausente, em vez de estimar o valor. Assim, cada número
continua definido em SQL e pode ser auditado.

3. LAYOUT DE app.py
A página usa layout largo. O cabeçalho mostra "E-commerce sintético · visão
da operação" à esquerda e, à direita, o filtro mensal e o botão
"Recarregar dados".

Primeira faixa, cinco cartões nesta ordem:
- Receita entregue no mês mais recente: vendas_mensais.vendas_entregues.
- Pedidos entregues no mesmo mês: vendas_mensais.pedidos_entregues.
- Ticket médio no mesmo mês: vendas_mensais.ticket_entregue.
- Produto líder: nome_produto e unidades_entregues da primeira linha de
  produtos_mais_vendidos.
- País líder: pais e valor_vendido da primeira linha de vendas_por_pais.
Os três primeiros cartões são do último mês, não do período do filtro. Os
dois últimos usam a linha líder já devolvida pelo mart. Isso evita
apresentar valores parciais como totais gerais.

Segunda faixa, largura inteira:
01 · Vendas entregues por mês. Linha com marcadores, mes no eixo X e
vendas_entregues em USD no eixo Y.

Terceira faixa, três colunas:
02 · Produtos mais vendidos: barras horizontais de unidades_entregues por
nome_produto, em ordem decrescente.
04 · Vendas por país: barras horizontais de valor_vendido em USD, em ordem
decrescente.
05 · Mix de pagamentos: valor_pagamentos em USD por método, com status de
pagamento em cores e painéis separados por canal.

Quarta faixa, três colunas:
03 · Solicitações e reembolsos por categoria: barras horizontais agrupadas
de pct_itens_com_solicitacao e pct_itens_reembolsados.
06 · Prazo e taxa de entrega por transportadora: dispersão de
media_dias_envio_entrega (dias) contra pct_entregues (%), identificando a
transportadora em cada ponto.
07 · Descontos por canal: pct_desconto_ponderado por canal, colorido por
status_pedido.

Quinta faixa, três colunas:
08 · Recorrência por país e fidelidade: pct_recorrentes por
nivel_fidelidade. Um seletor local filtra o país somente neste gráfico.
09 · Margem estimada por produto: barras horizontais de
margem_bruta_estimada em USD por nome_produto, preservando a ordem do mart
e identificando a margem como estimada.
10 · Status de pedidos e pagamentos: pedidos com captura, falha, estorno e
sem pagamento por status_pedido, separados por canal.

Cada gráfico identifica as unidades dos eixos, usa uma cor principal
consistente e é renderizado com width="stretch". Percentuais já vêm na
escala de 0 a 100; não são convertidos ou recalculados. Cada função de
gráfico recebe o DataFrame do mart e devolve uma figura Plotly; a função de
recorrência também recebe o país selecionado. As funções de gráfico e de
formatação não importam Streamlit nem acessam o banco, o que permite testá-
las e reutilizar as figuras.

4. FORMATAÇÃO
moeda_usd(valor, casas=2), pct(valor, casas=1) e numero(valor, casas=0)
são funções puras. Usam ponto para milhar e vírgula para decimais sem
depender do locale da máquina. As datas são rotuladas com abreviações de
meses em português definidas no código, para não variar conforme o sistema.

5. FILTROS
O seletor mensal oferece os valores de mes em vendas_mensais e começa com
todo o intervalo disponível selecionado. Ele filtra somente o gráfico de
vendas; os demais marts não têm mês e os cartões não devem ser recalculados
para o período. A página informa: "O filtro altera somente o gráfico de
vendas mensais."

O seletor de país afeta somente as linhas do gráfico de recorrência. A
separação dos filtros mantém explícito o escopo temporal disponível em
cada mart.

6. CACHE E ERROS
app.py usa st.cache_data para a leitura. "Recarregar dados" limpa o cache.
Se o arquivo do banco ou algum mart estiver ausente, a página informa o que
falta, mostra o comando uv run python -m pipeline.marts e interrompe a
renderização. Não se substituem erros por tabelas vazias ou gráficos
parciais. O fechamento da conexão após a leitura deixa o pipeline livre
para substituir os marts.

CRITÉRIOS DE ACEITE
- O comando uv run streamlit run app.py abre o painel e lê os dez marts em
  modo somente leitura.
- O gráfico mensal exibe os 33 meses disponíveis, com o intervalo completo
  selecionado inicialmente.
- O filtro mensal só altera esse gráfico; os cinco cartões e os outros
  nove gráficos não mudam.
- O seletor de país só altera o gráfico de recorrência.
- Os cartões mostram os registros definidos acima sem recalcular métricas;
  os valores monetários e a margem estimada são identificados em USD.
- Pagamentos distinguem método, status e canal; status de pedidos
  distinguem status do pedido e canal.
- Uma busca por operações tabulares proibidas não encontra cálculos de
  negócio em painel.py e app.py.
- Arquivo ou marts ausentes geram mensagem explícita e instrução para
  materializá-los, sem renderização parcial.
- Com o painel aberto, uv run python -m pipeline.marts recria os marts sem
  erro de lock.

SUPOSIÇÕES APROVADAS NESTA PROPOSTA
- Sem rascunho visual, a página usa cinco cartões e cinco faixas: uma para
  cartões, uma para vendas mensais e três com três gráficos cada.
- Sem mart de KPIs gerais, os cartões usam o mês mais recente e as linhas
  líderes já retornadas por outros marts; não são totais do período.
- Somente vendas_mensais tem mês, então apenas seu gráfico é filtrado por
  período. O filtro de país fica restrito à recorrência.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CAMINHO_BANCO = Path(__file__).resolve().parent / "ecommerce.duckdb"
MARTS = (
    "vendas_mensais",
    "produtos_mais_vendidos",
    "devolucoes_por_categoria",
    "vendas_por_pais",
    "pagamentos_por_metodo",
    "entregas_por_transportadora",
    "descontos_por_canal",
    "recorrencia_clientes",
    "margem_estimada_produto",
    "status_pedido_pagamento",
)

AZUL = "#2878B5"
CORES = ["#2878B5", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#76B7B2"]
MESES_PT = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)


class MartsAusentesError(RuntimeError):
    """Indica quais tabelas analíticas não estão disponíveis no banco."""

    def __init__(self, nomes: Iterable[str]) -> None:
        self.nomes = tuple(nomes)
        super().__init__(", ".join(f"marts.{nome}" for nome in self.nomes))


def ler(nomes_marts: Iterable[str]) -> dict[str, pd.DataFrame]:
    """Lê os marts solicitados e sempre fecha a conexão DuckDB."""
    nomes = tuple(nomes_marts)
    invalidos = [nome for nome in nomes if nome not in MARTS]
    if invalidos:
        raise ValueError(f"Marts não permitidos: {', '.join(invalidos)}")

    conexao = duckdb.connect(str(CAMINHO_BANCO), read_only=True)
    dados: dict[str, pd.DataFrame] = {}
    ausentes: list[str] = []
    try:
        for nome in nomes:
            try:
                dados[nome] = conexao.execute(
                    f"SELECT * FROM marts.{nome}"
                ).fetchdf()
            except duckdb.CatalogException as erro:
                if "does not exist" not in str(erro):
                    raise
                ausentes.append(nome)
        if ausentes:
            raise MartsAusentesError(ausentes)
        return dados
    finally:
        conexao.close()


def _formatar(valor: float | Decimal, casas: int) -> str:
    formatado = f"{valor:,.{casas}f}"
    return formatado.replace(",", "\0").replace(".", ",").replace("\0", ".")


def moeda_usd(valor: float | Decimal, casas: int = 2) -> str:
    return f"US$ {_formatar(valor, casas)}"


def pct(valor: float | Decimal, casas: int = 1) -> str:
    return f"{_formatar(valor, casas)}%"


def numero(valor: float | Decimal, casas: int = 0) -> str:
    return _formatar(valor, casas)


def rotular_mes(valor: date | pd.Timestamp) -> str:
    return f"{MESES_PT[valor.month - 1]}/{valor.year}"


def _base(figura: go.Figure) -> go.Figure:
    figura.update_layout(
        template="plotly_white",
        margin={"l": 12, "r": 12, "t": 58, "b": 12},
        legend_title_text=None,
    )
    return figura


def grafico_vendas_mensais(df: pd.DataFrame) -> go.Figure:
    dados = df.copy()
    dados["mes_rotulo"] = dados["mes"].map(rotular_mes)
    figura = px.line(
        dados,
        x="mes_rotulo",
        y="vendas_entregues",
        markers=True,
        title="01 · Vendas entregues por mês",
        labels={"mes_rotulo": "Mês", "vendas_entregues": "Vendas (USD)"},
    )
    figura.update_traces(
        line={"color": AZUL},
        marker={"color": AZUL},
        hovertemplate="%{x}<br>Vendas entregues: US$ %{y:,.2f}<extra></extra>",
    )
    figura.update_yaxes(title_text="Vendas entregues (USD)", tickformat=",.2f")
    figura.update_xaxes(title_text="Mês")
    return _base(figura)


def grafico_produtos_mais_vendidos(df: pd.DataFrame) -> go.Figure:
    dados = df.sort_values("unidades_entregues", ascending=False)
    figura = px.bar(
        dados,
        x="unidades_entregues",
        y="nome_produto",
        orientation="h",
        title="02 · Produtos mais vendidos",
        labels={
            "unidades_entregues": "Unidades entregues",
            "nome_produto": "Produto",
        },
        color_discrete_sequence=[AZUL],
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(title_text="Unidades entregues", tickformat=",.0f")
    return _base(figura)


def grafico_devolucoes_por_categoria(df: pd.DataFrame) -> go.Figure:
    dados = df.sort_values("pct_itens_com_solicitacao", ascending=False)
    figura = px.bar(
        dados,
        x=["pct_itens_com_solicitacao", "pct_itens_reembolsados"],
        y="categoria",
        orientation="h",
        barmode="group",
        title="03 · Solicitações e reembolsos por categoria",
        labels={
            "categoria": "Categoria",
            "value": "Itens (%)",
            "variable": "Indicador",
            "pct_itens_com_solicitacao": "Com solicitação",
            "pct_itens_reembolsados": "Reembolsados",
        },
        color_discrete_sequence=CORES[:2],
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(title_text="Itens (%)", ticksuffix="%")
    return _base(figura)


def grafico_vendas_por_pais(df: pd.DataFrame) -> go.Figure:
    dados = df.sort_values("valor_vendido", ascending=False)
    figura = px.bar(
        dados,
        x="valor_vendido",
        y="pais",
        orientation="h",
        title="04 · Vendas por país",
        labels={"valor_vendido": "Vendas (USD)", "pais": "País"},
        color_discrete_sequence=[AZUL],
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(title_text="Vendas (USD)", tickformat=",.2f")
    return _base(figura)


def grafico_pagamentos_por_metodo(df: pd.DataFrame) -> go.Figure:
    figura = px.bar(
        df,
        x="metodo",
        y="valor_pagamentos",
        color="status_pagamento",
        facet_col="canal",
        facet_col_wrap=2,
        barmode="group",
        title="05 · Mix de pagamentos",
        labels={
            "metodo": "Método de pagamento",
            "valor_pagamentos": "Pagamentos (USD)",
            "status_pagamento": "Status do pagamento",
            "canal": "Canal",
        },
        color_discrete_sequence=CORES,
    )
    figura.update_yaxes(title_text="Pagamentos (USD)", tickformat=",.2f")
    figura.update_xaxes(title_text="Método de pagamento")
    return _base(figura)


def grafico_entregas_por_transportadora(df: pd.DataFrame) -> go.Figure:
    figura = px.scatter(
        df,
        x="media_dias_envio_entrega",
        y="pct_entregues",
        hover_name="transportadora",
        title="06 · Prazo e taxa de entrega por transportadora",
        labels={
            "media_dias_envio_entrega": "Envio até entrega (dias)",
            "pct_entregues": "Entregues (%)",
            "transportadora": "Transportadora",
        },
        color_discrete_sequence=[AZUL],
    )
    figura.update_traces(
        hovertemplate=(
            "%{hovertext}<br>Dias: %{x:.2f}<br>"
            "Entregues: %{y:.2f}%<extra></extra>"
        )
    )
    figura.update_xaxes(title_text="Envio até entrega (dias)")
    figura.update_yaxes(title_text="Entregues (%)", ticksuffix="%")
    return _base(figura)


def grafico_descontos_por_canal(df: pd.DataFrame) -> go.Figure:
    figura = px.bar(
        df,
        x="canal",
        y="pct_desconto_ponderado",
        color="status_pedido",
        barmode="group",
        title="07 · Descontos por canal",
        labels={
            "canal": "Canal",
            "pct_desconto_ponderado": "Desconto ponderado (%)",
            "status_pedido": "Status do pedido",
        },
        color_discrete_sequence=CORES,
    )
    figura.update_xaxes(title_text="Canal")
    figura.update_yaxes(title_text="Desconto ponderado (%)", ticksuffix="%")
    return _base(figura)


def grafico_recorrencia_clientes(df: pd.DataFrame, pais: str | None) -> go.Figure:
    dados = df
    if pais is not None:
        dados = df.loc[df["pais"].eq(pais)]
    figura = px.bar(
        dados,
        x="nivel_fidelidade",
        y="pct_recorrentes",
        color="pais",
        barmode="group",
        title="08 · Recorrência por país e fidelidade",
        labels={
            "nivel_fidelidade": "Nível de fidelidade",
            "pct_recorrentes": "Clientes recorrentes (%)",
            "pais": "País",
        },
        color_discrete_sequence=CORES,
    )
    figura.update_xaxes(title_text="Nível de fidelidade")
    figura.update_yaxes(title_text="Clientes recorrentes (%)", ticksuffix="%")
    return _base(figura)


def grafico_margem_estimada_produto(df: pd.DataFrame) -> go.Figure:
    figura = px.bar(
        df,
        x="margem_bruta_estimada",
        y="nome_produto",
        orientation="h",
        title="09 · Margem bruta estimada por produto",
        labels={
            "margem_bruta_estimada": "Margem estimada (USD)",
            "nome_produto": "Produto",
        },
        color_discrete_sequence=[AZUL],
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(title_text="Margem estimada (USD)", tickformat=",.2f")
    return _base(figura)


def grafico_status_pedido_pagamento(df: pd.DataFrame) -> go.Figure:
    figura = px.bar(
        df,
        x="status_pedido",
        y=[
            "pedidos_com_captura",
            "pedidos_com_falha",
            "pedidos_com_estorno",
            "pedidos_sem_pagamento",
        ],
        facet_col="canal",
        facet_col_wrap=2,
        barmode="group",
        title="10 · Status de pedidos e pagamentos",
        labels={
            "status_pedido": "Status do pedido",
            "value": "Pedidos",
            "variable": "Situação do pagamento",
            "canal": "Canal",
            "pedidos_com_captura": "Com captura",
            "pedidos_com_falha": "Com falha",
            "pedidos_com_estorno": "Com estorno",
            "pedidos_sem_pagamento": "Sem pagamento",
        },
        color_discrete_sequence=CORES[:4],
    )
    figura.update_xaxes(title_text="Status do pedido")
    figura.update_yaxes(title_text="Pedidos", tickformat=",.0f")
    return _base(figura)
