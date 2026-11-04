"""Gera dashboard.html como uma cópia estática e independente dos marts."""

from __future__ import annotations

import json
from datetime import date, datetime
from html import escape
from pathlib import Path

import pandas as pd
import plotly.io as pio

import painel

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_HTML = RAIZ_PROJETO / "dashboard.html"

_GRAFICOS = (
    ("grafico-mensal", "vendas_mensais", painel.grafico_vendas_mensais),
    (
        "grafico-produtos",
        "produtos_mais_vendidos",
        painel.grafico_produtos_mais_vendidos,
    ),
    (
        "grafico-vendas-pais",
        "vendas_por_pais",
        painel.grafico_vendas_por_pais,
    ),
    (
        "grafico-pagamentos",
        "pagamentos_por_metodo",
        painel.grafico_pagamentos_por_metodo,
    ),
    (
        "grafico-devolucoes",
        "devolucoes_por_categoria",
        painel.grafico_devolucoes_por_categoria,
    ),
    (
        "grafico-entregas",
        "entregas_por_transportadora",
        painel.grafico_entregas_por_transportadora,
    ),
    (
        "grafico-descontos",
        "descontos_por_canal",
        painel.grafico_descontos_por_canal,
    ),
    (
        "grafico-recorrencia",
        "recorrencia_clientes",
        lambda df: painel.grafico_recorrencia_clientes(df, None),
    ),
    (
        "grafico-margem",
        "margem_estimada_produto",
        painel.grafico_margem_estimada_produto,
    ),
    (
        "grafico-status",
        "status_pedido_pagamento",
        painel.grafico_status_pedido_pagamento,
    ),
)


def _cartao(rotulo: str, valor: str, detalhe: str) -> str:
    return (
        '<article class="metric">'
        f'<span class="metric-label">{escape(rotulo)}</span>'
        f'<strong>{escape(valor)}</strong>'
        f'<small>{escape(detalhe)}</small>'
        "</article>"
    )


def _cartoes(dados: dict[str, pd.DataFrame]) -> str:
    mensal = dados["vendas_mensais"].sort_values("mes")
    ultimo_mes = mensal.iloc[-1]
    produto = dados["produtos_mais_vendidos"].iloc[0]
    pais = dados["vendas_por_pais"].iloc[0]
    cartoes = (
        _cartao(
            "Receita entregue",
            painel.moeda_usd(ultimo_mes["vendas_entregues"]),
            f"Mês: {painel.rotular_mes(ultimo_mes['mes'])}",
        ),
        _cartao(
            "Pedidos entregues",
            painel.numero(ultimo_mes["pedidos_entregues"]),
            f"Mês: {painel.rotular_mes(ultimo_mes['mes'])}",
        ),
        _cartao(
            "Ticket médio",
            painel.moeda_usd(ultimo_mes["ticket_entregue"]),
            f"Mês: {painel.rotular_mes(ultimo_mes['mes'])}",
        ),
        _cartao(
            "Produto líder · unidades",
            painel.numero(produto["unidades_entregues"]),
            str(produto["nome_produto"]),
        ),
        _cartao(
            "Vendas do país líder",
            painel.moeda_usd(pais["valor_vendido"]),
            str(pais["pais"]),
        ),
    )
    return "\n".join(cartoes)


def _controles_meses(df: pd.DataFrame) -> tuple[str, list[str], int]:
    meses = sorted(df["mes"].dt.date.unique())
    indice_inicio_padrao = next(
        (indice for indice, mes in enumerate(meses) if mes >= date(2026, 1, 1)),
        0,
    )
    opcoes = "\n".join(
        f'<option value="{indice}">{escape(painel.rotular_mes(mes))}</option>'
        for indice, mes in enumerate(meses)
    )
    html_controle = f"""
    <div class="filter-group">
      <label for="mes-inicio">De</label>
      <select id="mes-inicio">{opcoes}</select>
      <label for="mes-fim">Até</label>
      <select id="mes-fim">{opcoes}</select>
    </div>
    """
    return (
        html_controle,
        [painel.rotular_mes(mes) for mes in meses],
        indice_inicio_padrao,
    )


def _controle_paises(df: pd.DataFrame) -> str:
    pais_inicial = str(df.iloc[0]["pais"])
    paises = dict.fromkeys(str(pais) for pais in df["pais"].dropna())
    opcoes = "\n".join(
        f'<option value="{escape(pais, quote=True)}"'
        f'{" selected" if pais == pais_inicial else ""}>'
        f"{escape(pais)}</option>"
        for pais in paises
    )
    return f"""
    <label class="country-filter" for="filtro-pais">
      País analisado · recorrência
      <select id="filtro-pais">
        {opcoes}
      </select>
    </label>
    """


def _figuras(dados: dict[str, pd.DataFrame]) -> dict[str, str]:
    fragmentos: dict[str, str] = {}
    for indice, (identificador, nome_mart, criar_figura) in enumerate(_GRAFICOS):
        figura = criar_figura(dados[nome_mart])
        if figura.layout.height is None:
            figura.update_layout(height=470)
        if identificador == "grafico-mensal":
            figura.update_layout(height=440)
        fragmentos[identificador] = pio.to_html(
            figura,
            full_html=False,
            include_plotlyjs=indice == 0,
            config={"responsive": True, "displaylogo": False},
            div_id=identificador,
        )
    return fragmentos


def montar_html(dados: dict[str, pd.DataFrame]) -> str:
    """Monta o dashboard independente a partir dos DataFrames dos marts."""
    controle_meses, meses, indice_inicio_padrao = _controles_meses(
        dados["vendas_mensais"]
    )
    opcoes_mes_json = json.dumps(meses, ensure_ascii=False)
    figuras = _figuras(dados)
    gerado_em = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Painel estático de análise do e-commerce sintético">
  <title>E-commerce sintético · visão da operação</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      color: #17212b;
      background: #f3f6fa;
      font-synthesis: none;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding: 26px clamp(20px, 4vw, 64px);
      color: #fff;
      background: #12263a;
    }}
    h1 {{ margin: 0; font-size: clamp(1.35rem, 2.5vw, 2rem); }}
    .snapshot {{ margin: 7px 0 0; color: #bed0df; font-size: .85rem; }}
    .filter-bar {{ display: flex; align-items: end; gap: 18px; flex-wrap: wrap; }}
    .filter-group {{ display: flex; align-items: center; gap: 8px; }}
    label {{ font-size: .85rem; font-weight: 600; }}
    select {{
      min-height: 38px;
      padding: 7px 30px 7px 10px;
      border: 1px solid #c7d2de;
      border-radius: 7px;
      background: #fff;
      color: #17212b;
      font: inherit;
    }}
    .filter-bar label, .filter-group label {{ color: #e4edf5; }}
    main {{ max-width: 1800px; margin: auto; padding: 22px clamp(14px, 3vw, 48px) 48px; }}
    .scope-note {{ margin: 0 0 16px; color: #526477; font-size: .9rem; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .metric {{
      display: flex;
      min-height: 128px;
      flex-direction: column;
      justify-content: space-between;
      gap: 10px;
      padding: 17px;
      border: 1px solid #e0e7ef;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 3px 12px #18344d0a;
    }}
    .metric-label {{ color: #526477; font-size: .8rem; font-weight: 600; }}
    .metric strong {{ overflow-wrap: anywhere; color: #14283b; font-size: clamp(1.05rem, 1.65vw, 1.5rem); }}
    .metric small {{ overflow-wrap: anywhere; color: #65788b; font-size: .8rem; }}
    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}
    .chart-grid-two {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .chart {{
      min-width: 0;
      overflow: hidden;
      padding: 8px;
      border: 1px solid #e0e7ef;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 3px 12px #18344d0a;
    }}
    .chart-wide {{ margin-top: 16px; }}
    .country-filter {{ display: flex; max-width: 300px; flex-direction: column; gap: 6px; margin: 12px 12px 0; }}
    .country-filter select {{ width: 100%; }}
    footer {{ padding: 18px; color: #687b8d; text-align: center; font-size: .8rem; }}
    @media (max-width: 1050px) {{
      .metrics {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .chart-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 680px) {{
      header {{ align-items: flex-start; flex-direction: column; }}
      .metrics, .chart-grid, .chart-grid-two {{ grid-template-columns: 1fr; }}
      .metric {{ min-height: 105px; }}
      .filter-bar {{ align-items: flex-start; flex-direction: column; }}
      .filter-group {{ flex-wrap: wrap; }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>E-commerce sintético · visão da operação</h1>
      <p class="snapshot">Snapshot gerado em {escape(gerado_em)} · os dados não se atualizam automaticamente</p>
    </div>
    <div class="filter-bar">
      {controle_meses}
    </div>
  </header>
  <main>
    <p class="scope-note">O filtro altera somente o gráfico de vendas mensais.</p>
    <section class="metrics" aria-label="Indicadores do painel">
      {_cartoes(dados)}
    </section>
    <section class="chart chart-wide" aria-label="Vendas entregues por mês">
      {figuras["grafico-mensal"]}
    </section>
    <div class="chart-grid chart-grid-two">
      <section class="chart" aria-label="Produtos mais vendidos">{figuras["grafico-produtos"]}</section>
      <section class="chart" aria-label="Solicitações e reembolsos por categoria">{figuras["grafico-devolucoes"]}</section>
    </div>
    <section class="chart chart-wide" aria-label="Vendas por país">{figuras["grafico-vendas-pais"]}</section>
    <section class="chart chart-wide" aria-label="Mix de pagamentos">{figuras["grafico-pagamentos"]}</section>
    <div class="chart-grid chart-grid-two">
      <section class="chart" aria-label="Prazo e taxa de entrega por transportadora">{figuras["grafico-entregas"]}</section>
      <section class="chart" aria-label="Descontos por canal">{figuras["grafico-descontos"]}</section>
    </div>
    <div class="chart-grid chart-grid-two">
      <section class="chart" aria-label="Recorrência por país e fidelidade">
        {_controle_paises(dados["recorrencia_clientes"])}
        {figuras["grafico-recorrencia"]}
      </section>
      <section class="chart" aria-label="Margem estimada por produto">{figuras["grafico-margem"]}</section>
    </div>
    <section class="chart chart-wide" aria-label="Status de pedidos e pagamentos">{figuras["grafico-status"]}</section>
  </main>
  <footer>
    Arquivo HTML independente. Para atualizar este snapshot, execute
    <code>uv run python -m pipeline.painel_html</code>.
  </footer>
  <script>
    const mesesDisponiveis = {opcoes_mes_json};
    const indiceInicioPadrao = {indice_inicio_padrao};
    const controleInicio = document.getElementById("mes-inicio");
    const controleFim = document.getElementById("mes-fim");
    const graficoMensal = document.getElementById("grafico-mensal");
    const mesesOriginais = graficoMensal.data[0].x.slice();
    const valores = graficoMensal.data[0].y;
    const valoresOriginais = Array.isArray(valores)
      ? valores.slice()
      : Array.from(valores._inputArray);
    const rotulosOriginais = graficoMensal.data[0].text.slice();
    controleInicio.value = String(indiceInicioPadrao);
    controleFim.value = String(mesesDisponiveis.length - 1);

    function atualizarPeriodo() {{
      let inicio = Number(controleInicio.value);
      let fim = Number(controleFim.value);
      if (inicio > fim) {{
        if (document.activeElement === controleInicio) {{
          fim = inicio;
          controleFim.value = String(fim);
        }} else {{
          inicio = fim;
          controleInicio.value = String(inicio);
        }}
      }}
      const indices = mesesOriginais
        .map((_, indice) => indice)
        .filter((indice) => indice >= inicio && indice <= fim);
      Plotly.restyle(
        graficoMensal,
        {{
          x: [indices.map((indice) => mesesOriginais[indice])],
          y: [indices.map((indice) => valoresOriginais[indice])],
          text: [indices.map((indice) => rotulosOriginais[indice])]
        }},
        [0]
      );
      Plotly.relayout(graficoMensal, {{"yaxis.autorange": true}});
    }}
    controleInicio.addEventListener("change", atualizarPeriodo);
    controleFim.addEventListener("change", atualizarPeriodo);
    atualizarPeriodo();

    const filtroPais = document.getElementById("filtro-pais");
    const graficoRecorrencia = document.getElementById("grafico-recorrencia");
    filtroPais.addEventListener("change", () => {{
      const selecionado = filtroPais.value;
      const visibilidades = graficoRecorrencia.data.map(
        (traco) => !selecionado || traco.name === selecionado
      );
      Plotly.restyle(graficoRecorrencia, {{visible: visibilidades}});
    }});
  </script>
</body>
</html>"""


def gerar(caminho: Path = CAMINHO_HTML) -> Path:
    """Lê os marts e grava um HTML independente com o snapshot atual."""
    dados = painel.ler(painel.MARTS)
    conteudo = montar_html(dados)
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def main() -> None:
    caminho = gerar()
    print(f"Painel HTML gerado: {caminho}")


if __name__ == "__main__":
    main()
