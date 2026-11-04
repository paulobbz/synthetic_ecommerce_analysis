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
01 · Vendas entregues por mês. Linha com marcadores, mês no eixo X,
vendas_entregues em USD no eixo Y e rótulos de dados com separador de
milhar brasileiro.

Terceira faixa, dois gráficos em duas colunas:
02 · Produtos mais vendidos: barras horizontais de unidades_entregues por
nome_produto, em ordem decrescente e com rótulos numéricos; os valores do
eixo inferior ficam ocultos.
03 · Solicitações e reembolsos por categoria: barras horizontais agrupadas
de pct_itens_com_solicitacao e pct_itens_reembolsados, com rótulos e a
explicação de que os percentuais usam os itens da categoria como base. O
eixo percentual usa escala automática.
04 · Vendas por país: barras horizontais de valor_vendido em USD, em ordem
decrescente e com valores nos rótulos; os valores do eixo inferior ficam
ocultos.
05 · Mix de pagamentos: barras horizontais empilhadas a 100% por método,
com status em português por cor e rótulos dos valores em USD. O seletor
permite todos os canais ou Site, Aplicativo e Marketplace; "Todos" inclui
os canais do mart. O valor exato em USD também aparece no hover e
"% do valor" no eixo X.

Quarta faixa: dois gráficos em duas colunas.
06 · Comparação tabular de media_dias_envio_entrega (dias) e
pct_entregues (%) por transportadora; os dois indicadores têm unidades
distintas e são apresentados em colunas separadas.
07 · Descontos por canal: pct_desconto_ponderado por canal e
status_pedido. Canais e status são exibidos em português e cada barra tem
seu percentual.

Quinta faixa: dois gráficos em duas colunas e o gráfico 10 em largura
inteira.
08 · Recorrência por nível de fidelidade: pct_recorrentes por país
selecionado e nivel_fidelidade, com rótulos percentuais nas barras. O
seletor lista todos os países e abre no primeiro país do mart para evitar
sobreposição entre muitos países; os valores do eixo lateral ficam ocultos.
09 · Margem estimada por produto: barras horizontais de
margem_bruta_estimada em USD por nome_produto, preservando a ordem do mart
e identificando a margem como estimada; os valores aparecem nos rótulos.
10 · Matriz da situação do pagamento por status_pedido e canal, com
contagens exatas nas células e escala de cor logarítmica para que status
menos frequentes continuem visíveis.

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
O seletor mensal oferece todos os valores de mes em vendas_mensais,
incluindo os meses desde jan/2024, e começa em jan/2026 até o mês mais
recente disponível. Se jan/2026 não estiver disponível, começa no primeiro
mês disponível. Ele filtra somente o gráfico de vendas; os demais marts
não têm mês e os cartões não devem ser recalculados para o período. A
página informa: "O filtro altera somente o gráfico de vendas mensais."

O seletor de país afeta somente as linhas do gráfico de recorrência e
começa no primeiro país devolvido pelo mart. Cada gráfico mostra um país
por vez, mas o seletor conserva todos os países disponíveis.

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
- O gráfico mensal mantém todos os 33 meses disponíveis para filtro e começa
  selecionado de jan/2026 até o mês mais recente.
- O filtro mensal só altera esse gráfico; os cinco cartões e os outros
  nove gráficos não mudam.
- O seletor de país só altera o gráfico de recorrência.
- Os cartões mostram os registros definidos acima sem recalcular métricas;
  os valores monetários e a margem estimada são identificados em USD.
- Pagamentos distinguem método, status e canal; status de pedidos
  distinguem status do pedido e canal, com contagens exatas na matriz.
- Os gráficos 01, 02, 03, 04, 05, 07, 08 e 09 apresentam rótulos; os eixos
  redundantes dos gráficos 01, 02, 04 e 08 não exibem seus valores.
- Uma busca por operações tabulares proibidas não encontra cálculos de
  negócio em painel.py e app.py.
- Arquivo ou marts ausentes geram mensagem explícita e instrução para
  materializá-los, sem renderização parcial.
- Com o painel aberto, uv run python -m pipeline.marts recria os marts sem
  erro de lock.

SUPOSIÇÕES APROVADAS NESTA PROPOSTA
- Sem rascunho visual, a página usa cinco cartões, uma faixa para vendas
  mensais e três seções de gráficos com larguras ajustadas à legibilidade.
- Sem mart de KPIs gerais, os cartões usam o mês mais recente e as linhas
  líderes já retornadas por outros marts; não são totais do período.
- Somente vendas_mensais tem mês, então apenas seu gráfico é filtrado por
  período. O filtro de país fica restrito à recorrência.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from math import floor, log10
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
_CANAIS_PT = {
    "app": "Aplicativo",
    "marketplace": "Marketplace",
    "store": "Loja",
    "web": "Site",
    "loja": "Loja",
}
_STATUS_PEDIDO_PT = {
    "cancelled": "Cancelado",
    "delivered": "Entregue",
    "processing": "Em processamento",
    "returned": "Devolvido",
    "shipped": "Enviado",
}
_STATUS_PAGAMENTO_PT = {
    "captured": "Capturado",
    "failed": "Falhou",
    "refunded": "Reembolsado",
}
_METODOS_PAGAMENTO_PT = {
    "apple_pay": "Apple Pay",
    "bank_transfer": "Transferência bancária",
    "card": "Cartão",
    "cartao": "Cartão",
    "google_pay": "Google Pay",
    "klarna": "Klarna",
    "paypal": "PayPal",
    "pix": "Pix",
}
_NIVEIS_FIDELIDADE_PT = {
    "gold": "Ouro",
    "none": "Sem fidelidade",
    "platinum": "Platina",
    "silver": "Prata",
}
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
        mode="lines+markers+text",
        text=[numero(valor, casas=0) for valor in dados["vendas_entregues"]],
        textposition="top center",
        cliponaxis=False,
        hovertemplate="%{x}<br>Vendas entregues: US$ %{y:,.2f}<extra></extra>",
    )
    figura.update_yaxes(
        title_text="Vendas entregues (USD)",
        tickformat=",.2f",
        showticklabels=False,
    )
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
        text=[numero(valor) for valor in dados["unidades_entregues"]],
        labels={
            "unidades_entregues": "Unidades entregues",
            "nome_produto": "Produto",
        },
        color_discrete_sequence=[AZUL],
    )
    figura.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>Unidades entregues: %{x:,.0f}<extra></extra>",
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(
        title_text="Unidades entregues",
        tickformat=",.0f",
        showticklabels=False,
    )
    return _base(figura)


def grafico_devolucoes_por_categoria(df: pd.DataFrame) -> go.Figure:
    dados = df.sort_values("pct_itens_com_solicitacao", ascending=False)
    figura = px.bar(
        dados,
        x=["pct_itens_com_solicitacao", "pct_itens_reembolsados"],
        y="categoria",
        orientation="h",
        barmode="group",
        title=(
            "03 · Solicitações e reembolsos por categoria"
            "<br><sup>Percentual dos itens de cada categoria</sup>"
        ),
        labels={
            "categoria": "Categoria",
            "value": "Itens da categoria (%)",
            "variable": "Indicador",
            "pct_itens_com_solicitacao": "Com solicitação",
            "pct_itens_reembolsados": "Com reembolso",
        },
        color_discrete_sequence=CORES[:2],
    )
    for trace, nome in zip(
        figura.data, ("Com solicitação", "Com reembolso"), strict=True
    ):
        trace.name = nome
        trace.text = [pct(valor) for valor in trace.x]
    figura.update_traces(
        textposition="outside",
        texttemplate="%{text}",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{fullData.name}: %{x:.2f}%<extra></extra>",
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(
        title_text="Itens da categoria (%)",
        ticksuffix="%",
        autorange=True,
    )
    return _base(figura)


def grafico_vendas_por_pais(df: pd.DataFrame) -> go.Figure:
    dados = df.sort_values("valor_vendido", ascending=False)
    figura = px.bar(
        dados,
        x="valor_vendido",
        y="pais",
        orientation="h",
        title="04 · Vendas por país",
        text=[numero(valor, casas=0) for valor in dados["valor_vendido"]],
        labels={"valor_vendido": "Vendas (USD)", "pais": "País"},
        color_discrete_sequence=[AZUL],
    )
    figura.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>Vendas: US$ %{x:,.2f}<extra></extra>",
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(
        title_text="Vendas (USD)",
        tickformat=",.2f",
        showticklabels=False,
    )
    return _base(figura)


def grafico_pagamentos_por_metodo(
    df: pd.DataFrame, canal: str = "Todos"
) -> go.Figure:
    dados = df.copy()
    dados["canal_exibicao"] = (
        dados["canal"].map(_CANAIS_PT).fillna(dados["canal"])
    )
    if canal != "Todos":
        dados = dados.loc[dados["canal_exibicao"] == canal]
    dados["status_pagamento_exibicao"] = (
        dados["status_pagamento"]
        .map(_STATUS_PAGAMENTO_PT)
        .fillna(dados["status_pagamento"])
    )
    dados["metodo_exibicao"] = (
        dados["metodo"].map(_METODOS_PAGAMENTO_PT).fillna(dados["metodo"])
    )
    dados = dados.groupby(
        ["metodo_exibicao", "status_pagamento_exibicao"],
        as_index=False,
        dropna=False,
    )["valor_pagamentos"].sum()
    figura = px.bar(
        dados,
        x="valor_pagamentos",
        y="metodo_exibicao",
        orientation="h",
        color="status_pagamento_exibicao",
        text=[moeda_usd(valor, casas=0) for valor in dados["valor_pagamentos"]],
        custom_data=["valor_pagamentos"],
        barmode="stack",
        title="05 · Mix de pagamentos",
        labels={
            "metodo_exibicao": "",
            "valor_pagamentos": "% do valor",
            "status_pagamento_exibicao": "Status do pagamento",
        },
        category_orders={
            "status_pagamento_exibicao": [
                "Capturado",
                "Reembolsado",
                "Falhou",
            ]
        },
        color_discrete_map={
            "Capturado": AZUL,
            "Reembolsado": "#F28E2B",
            "Falhou": "#E15759",
        },
    )
    figura.update_traces(
        textposition="inside",
        texttemplate="%{text}",
        hovertemplate=(
            "%{y}<br>%{fullData.name}: US$ "
            "%{customdata[0]:,.2f}<extra></extra>"
        ),
    )
    figura.update_xaxes(title_text="% do valor", range=[0, 100], ticksuffix="%")
    figura.update_yaxes(title_text="", autorange="reversed", automargin=True)
    figura = _base(figura)
    figura.update_layout(
        height=470,
        barmode="stack",
        barnorm="percent",
        margin={"l": 150, "r": 20, "t": 58, "b": 48},
    )
    return figura


def grafico_entregas_por_transportadora(df: pd.DataFrame) -> go.Figure:
    dados = df.sort_values("media_dias_envio_entrega")
    figura = go.Figure(
        data=[
            go.Table(
                header={
                    "values": [
                        "Transportadora",
                        "Prazo médio<br>envio–entrega",
                        "Pedidos<br>entregues",
                    ],
                    "fill_color": "#EAF1F7",
                    "align": ["left", "right", "right"],
                    "font": {"color": "#14283B", "size": 13},
                    "height": 34,
                },
                cells={
                    "values": [
                        dados["transportadora"],
                        [
                            f"{numero(valor, casas=2)} dias"
                            for valor in dados["media_dias_envio_entrega"]
                        ],
                        [pct(valor, casas=2) for valor in dados["pct_entregues"]],
                    ],
                    "fill_color": [["#FFFFFF", "#F5F8FB"] * len(dados)],
                    "align": ["left", "right", "right"],
                    "font": {"color": "#263B4D", "size": 12},
                    "height": 30,
                },
                columnwidth=[1.5, 1.2, 1],
            )
        ]
    )
    figura.update_layout(
        title=(
            "06 · Prazo médio e taxa de pedidos entregues "
            "por transportadora"
        ),
        height=max(330, 150 + 30 * len(dados)),
        margin={"l": 8, "r": 8, "t": 70, "b": 8},
    )
    return _base(figura)


def grafico_descontos_por_canal(df: pd.DataFrame) -> go.Figure:
    dados = df.copy()
    dados["canal_exibicao"] = dados["canal"].map(_CANAIS_PT).fillna(dados["canal"])
    dados["status_exibicao"] = (
        dados["status_pedido"]
        .map(_STATUS_PEDIDO_PT)
        .fillna(dados["status_pedido"])
    )
    figura = px.bar(
        dados,
        x="canal_exibicao",
        y="pct_desconto_ponderado",
        color="status_exibicao",
        barmode="group",
        title="07 · Descontos por canal",
        labels={
            "canal_exibicao": "Canal",
            "pct_desconto_ponderado": "Desconto ponderado (%)",
            "status_exibicao": "Status do pedido",
        },
        color_discrete_sequence=CORES,
    )
    for trace in figura.data:
        trace.text = [pct(valor) for valor in trace.y]
    figura.update_traces(
        textposition="outside",
        texttemplate="%{text}",
        cliponaxis=False,
        hovertemplate="%{x}<br>%{fullData.name}: %{y:.2f}%<extra></extra>",
    )
    figura.update_xaxes(title_text="Canal de venda")
    figura.update_yaxes(title_text="Desconto ponderado (%)", ticksuffix="%")
    return _base(figura)


def grafico_recorrencia_clientes(df: pd.DataFrame, pais: str | None) -> go.Figure:
    dados = df.copy()
    if pais is not None:
        dados = dados.loc[dados["pais"].eq(pais)]
    dados["nivel_fidelidade_exibicao"] = (
        dados["nivel_fidelidade"]
        .map(_NIVEIS_FIDELIDADE_PT)
        .fillna(dados["nivel_fidelidade"])
    )
    figura = px.bar(
        dados,
        x="nivel_fidelidade_exibicao",
        y="pct_recorrentes",
        color="pais",
        barmode="group",
        title="08 · Recorrência por nível de fidelidade",
        text=[pct(valor, casas=1) for valor in dados["pct_recorrentes"]],
        labels={
            "nivel_fidelidade_exibicao": "Nível de fidelidade",
            "pct_recorrentes": "Clientes recorrentes (%)",
            "pais": "País",
        },
        color_discrete_sequence=CORES,
    )
    figura.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "%{x}<br>%{fullData.name}: %{y:.2f}% recorrentes<extra></extra>"
        ),
    )
    if pais is None:
        pais_inicial = str(df.iloc[0]["pais"])
        for trace in figura.data:
            trace.visible = trace.name == pais_inicial
    figura.update_xaxes(title_text="Nível de fidelidade")
    figura.update_yaxes(
        title_text="Clientes recorrentes (%)",
        ticksuffix="%",
        showticklabels=False,
    )
    return _base(figura)


def grafico_margem_estimada_produto(df: pd.DataFrame) -> go.Figure:
    figura = px.bar(
        df,
        x="margem_bruta_estimada",
        y="nome_produto",
        orientation="h",
        title="09 · Margem bruta estimada por produto",
        text=[
            numero(valor, casas=0)
            for valor in df["margem_bruta_estimada"]
        ],
        labels={
            "margem_bruta_estimada": "Margem estimada (USD)",
            "nome_produto": "Produto",
        },
        color_discrete_sequence=[AZUL],
    )
    figura.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>Margem estimada: US$ %{x:,.2f}<extra></extra>",
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(title_text="Margem estimada (USD)", tickformat=",.2f")
    return _base(figura)


def grafico_status_pedido_pagamento(df: pd.DataFrame) -> go.Figure:
    colunas = (
        ("pedidos_com_captura", "Captura"),
        ("pedidos_com_falha", "Falha"),
        ("pedidos_com_estorno", "Estorno"),
        ("pedidos_sem_pagamento", "Sem pagamento"),
    )
    dados = df.sort_values(["canal", "status_pedido"])
    status_canais = []
    valores = []
    for linha in dados.itertuples(index=False):
        canal = _CANAIS_PT.get(linha.canal, linha.canal)
        status = _STATUS_PEDIDO_PT.get(
            linha.status_pedido, linha.status_pedido
        )
        status_canais.append(f"{status} · {canal}")
        valores.append([int(getattr(linha, coluna)) for coluna, _ in colunas])

    contagens = valores
    z = [[log10(max(contagem, 1)) for contagem in serie] for serie in contagens]
    texto = [[numero(contagem) for contagem in serie] for serie in contagens]
    max_expoente = floor(max(max(serie) for serie in z))
    figura = go.Figure(
        data=[
            go.Heatmap(
                x=[rotulo for _, rotulo in colunas],
                y=status_canais,
                z=z,
                text=texto,
                customdata=contagens,
                texttemplate="%{text}",
                textfont={"size": 12},
                colorscale="Blues",
                colorbar={
                    "title": {"text": "Pedidos<br>(escala log₁₀)"},
                    "tickvals": list(range(max_expoente + 1)),
                    "ticktext": [
                        numero(10**expoente)
                        for expoente in range(max_expoente + 1)
                    ],
                },
                hovertemplate=(
                    "%{y}<br>%{x}: %{customdata} pedidos"
                    "<extra></extra>"
                ),
            )
        ]
    )
    figura.update_layout(
        title=(
            "10 · Situação do pagamento por status do pedido e canal"
            "<br><sup>Valores exatos nas células; cores em escala logarítmica</sup>"
        ),
        height=max(530, 190 + 25 * len(status_canais)),
        xaxis_title="Situação do pagamento",
        yaxis_title="Status do pedido · canal",
    )
    figura.update_yaxes(autorange="reversed")
    return _base(figura)
