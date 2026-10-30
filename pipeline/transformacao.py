"""Spec da etapa de transformacao de raw para refined.

Esta etapa le as sete tabelas brutas e recria suas correspondentes no schema
refined, sem jamais alterar raw. A separacao preserva a fonte original para
auditoria e permite que as etapas seguintes trabalhem com nomes e tipos
explicitos.

Cada coluna recebe o nome definido em Spec_etapa_2.txt; nenhuma coluna e
descartada. Identificadores, categorias e demais atributos permanecem texto
porque nao sao medidas. Datas, valores monetarios, quantidades, peso e flags
sao convertidos no DuckDB para que datas e dinheiro tenham tipos adequados,
sem copiar tabelas para a memoria Python.

As conversoes sao estritas. Um valor invalido nao pode virar NULL, pois isso
apagaria a diferenca entre um nulo de origem e um erro de dado. Duplicatas de
linha inteira sao reduzidas a uma ocorrencia; chaves com conteudo conflitante
interrompem o processamento, pois escolher uma linha seria uma decisao de
negocio silenciosa.

Nulos e anomalias existentes sao preservados, sem preenchimento, descarte ou
correcao de fatos. CREATE OR REPLACE torna a etapa reexecutavel. A validacao
das tabelas ocorre antes de qualquer escrita, e uma transacao impede que uma
falha durante a conversao deixe refined parcialmente atualizado.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from typing import Any

import duckdb

from pipeline import db

MAPA_COLUNAS: dict[str, dict[str, str]] = {
    "clientes": {
        "customer_id": "cliente_id",
        "first_name": "primeiro_nome",
        "last_name": "sobrenome",
        "email": "email",
        "phone": "telefone",
        "country": "pais",
        "city": "cidade",
        "signup_date": "data_cadastro",
        "loyalty_tier": "nivel_fidelidade",
        "marketing_opt_in": "aceita_marketing",
    },
    "devolucoes": {
        "return_id": "devolucao_id",
        "order_item_id": "item_pedido_id",
        "reason": "motivo",
        "refund_amount": "valor_reembolso",
        "requested_at": "data_solicitacao",
        "status": "status",
    },
    "itens_pedido": {
        "order_item_id": "item_pedido_id",
        "order_id": "pedido_id",
        "product_id": "produto_id",
        "quantity": "quantidade",
        "unit_price": "preco_unitario",
        "line_total": "total_item",
    },
    "pagamentos": {
        "payment_id": "pagamento_id",
        "order_id": "pedido_id",
        "method": "metodo",
        "amount": "valor",
        "paid_at": "data_pagamento",
        "status": "status",
    },
    "pedidos": {
        "order_id": "pedido_id",
        "customer_id": "cliente_id",
        "order_date": "data_pedido",
        "status": "status",
        "channel": "canal",
        "subtotal": "subtotal",
        "discount_amount": "valor_desconto",
        "shipping_fee": "valor_frete",
        "tax_amount": "valor_imposto",
        "total_amount": "valor_total",
        "currency": "moeda",
    },
    "produtos": {
        "product_id": "produto_id",
        "sku": "sku",
        "product_name": "nome_produto",
        "category": "categoria",
        "brand": "marca",
        "unit_price": "preco_unitario",
        "unit_cost": "custo_unitario",
        "weight_kg": "peso_kg",
        "is_active": "ativo",
        "created_at": "data_criacao",
    },
    "remessas": {
        "shipment_id": "remessa_id",
        "order_id": "pedido_id",
        "carrier": "transportadora",
        "tracking_number": "codigo_rastreio",
        "shipped_at": "data_envio",
        "delivered_at": "data_entrega",
        "status": "status",
    },
}

CHAVES: dict[str, tuple[str, ...]] = {
    "clientes": ("customer_id",),
    "devolucoes": ("return_id",),
    "itens_pedido": ("order_item_id",),
    "pagamentos": ("payment_id",),
    "pedidos": ("order_id",),
    "produtos": ("product_id",),
    "remessas": ("shipment_id",),
}

TIPOS: dict[str, dict[str, str]] = {
    "clientes": {
        "signup_date": "DATE",
        "marketing_opt_in": "BOOLEAN",
    },
    "devolucoes": {
        "refund_amount": "DECIMAL",
        "requested_at": "DATE_TIMESTAMP",
    },
    "itens_pedido": {
        "quantity": "INTEGER",
        "unit_price": "DECIMAL",
        "line_total": "DECIMAL",
    },
    "pagamentos": {
        "amount": "DECIMAL",
        "paid_at": "TIMESTAMP",
    },
    "pedidos": {
        "order_date": "TIMESTAMP",
        "subtotal": "DECIMAL",
        "discount_amount": "DECIMAL",
        "shipping_fee": "DECIMAL",
        "tax_amount": "DECIMAL",
        "total_amount": "DECIMAL",
    },
    "produtos": {
        "unit_price": "DECIMAL",
        "unit_cost": "DECIMAL",
        "weight_kg": "DECIMAL",
        "is_active": "BOOLEAN",
        "created_at": "DATE",
    },
    "remessas": {
        "shipped_at": "DATE_TIMESTAMP",
        "delivered_at": "DATE_TIMESTAMP",
    },
}

TABELAS = tuple(MAPA_COLUNAS)


def _identificador(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def _formatar_numero(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _reconfigurar_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def _expressao_coluna(coluna: str, tipo: str | None) -> str:
    identificador = _identificador(coluna)
    if tipo is None:
        return identificador
    if tipo == "TIMESTAMP":
        return f"strptime({identificador}, '%Y-%m-%d %H:%M:%S')"
    if tipo == "DATE_TIMESTAMP":
        return f"CAST(strptime({identificador}, '%Y-%m-%d %H:%M:%S') AS DATE)"
    if tipo == "DATE":
        return f"CAST(strptime({identificador}, '%Y-%m-%d') AS DATE)"
    if tipo == "DECIMAL":
        return f"CAST({identificador} AS DECIMAL(10, 2))"
    if tipo == "INTEGER":
        return f"CAST({identificador} AS INTEGER)"
    if tipo == "BOOLEAN":
        return f"CAST({identificador} AS BOOLEAN)"
    raise ValueError(f"Tipo de conversao nao configurado: {tipo}")


def _colunas_origem(con: duckdb.DuckDBPyConnection, tabela: str) -> list[str]:
    linhas = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'raw' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [tabela],
    ).fetchall()
    return [linha[0] for linha in linhas]


def _validar_estrutura(
    con: duckdb.DuckDBPyConnection,
) -> dict[str, list[str]]:
    existentes = {
        linha[0]
        for linha in con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
            """
        ).fetchall()
    }
    ausentes = [tabela for tabela in TABELAS if tabela not in existentes]
    if ausentes:
        print("Tabelas ausentes em raw:")
        for tabela in ausentes:
            print(f"- raw.{tabela}")
        print('Rode "uv run python -m pipeline.ingestao" antes da transformacao.')
        raise SystemExit(1)

    colunas_por_tabela: dict[str, list[str]] = {}
    for tabela, mapa in MAPA_COLUNAS.items():
        colunas = _colunas_origem(con, tabela)
        esperadas = list(mapa)
        faltantes = [coluna for coluna in esperadas if coluna not in colunas]
        extras = [coluna for coluna in colunas if coluna not in mapa]
        if faltantes or extras:
            print(f"Colunas inesperadas em raw.{tabela}.")
            if faltantes:
                print(f"Ausentes: {', '.join(faltantes)}")
            if extras:
                print(f"Fora do mapa: {', '.join(extras)}")
            raise SystemExit(1)
        colunas_por_tabela[tabela] = colunas
    return colunas_por_tabela


def _linhas_conflitantes(
    con: duckdb.DuckDBPyConnection,
    tabela: str,
    colunas: list[str],
) -> list[tuple[Any, ...]]:
    colunas_sql = ", ".join(_identificador(coluna) for coluna in colunas)
    chaves = CHAVES[tabela]
    chaves_sql = ", ".join(_identificador(chave) for chave in chaves)
    conflitos_sql = (
        f"(SELECT {chaves_sql} "
        f"FROM (SELECT DISTINCT {colunas_sql} FROM raw.{_identificador(tabela)}) AS distintas "
        f"GROUP BY {chaves_sql} HAVING count(*) > 1)"
    )
    condicoes = " AND ".join(
        f"r.{_identificador(chave)} IS NOT DISTINCT FROM c.{_identificador(chave)}"
        for chave in chaves
    )
    return con.execute(
        f"""
        SELECT DISTINCT {", ".join(f"r.{_identificador(coluna)}" for coluna in colunas)}
        FROM raw.{_identificador(tabela)} AS r
        WHERE EXISTS (
            SELECT 1 FROM {conflitos_sql} AS c
            WHERE {condicoes}
        )
        ORDER BY {", ".join(f"r.{_identificador(coluna)}" for coluna in chaves)}
        """
    ).fetchall()


def _validar_duplicatas(
    con: duckdb.DuckDBPyConnection,
    tabela: str,
    colunas: list[str],
) -> tuple[int, int]:
    colunas_sql = ", ".join(_identificador(coluna) for coluna in colunas)
    nome = _identificador(tabela)
    entrada, distintas = con.execute(
        f"""
        SELECT
            (SELECT count(*) FROM raw.{nome}),
            (SELECT count(*) FROM (
                SELECT DISTINCT {colunas_sql} FROM raw.{nome}
            ))
        """
    ).fetchone()
    linhas_conflitantes = _linhas_conflitantes(con, tabela, colunas)
    if linhas_conflitantes:
        posicoes_chaves = [colunas.index(chave) for chave in CHAVES[tabela]]
        grupos: dict[tuple[Any, ...], list[tuple[Any, ...]]] = defaultdict(list)
        for linha in linhas_conflitantes:
            chave = tuple(linha[posicao] for posicao in posicoes_chaves)
            grupos[chave].append(linha)

        print(f"Chaves repetidas com conteudo diferente em raw.{tabela}:")
        for chave, linhas in grupos.items():
            print(f"- chave {chave}:")
            for linha in linhas:
                registro = dict(zip(colunas, linha, strict=True))
                print(f"  {registro}")
        raise SystemExit(1)
    return entrada, entrada - distintas


def _validar_conversoes(
    con: duckdb.DuckDBPyConnection,
    tabela: str,
) -> None:
    for coluna, tipo in TIPOS.get(tabela, {}).items():
        expressao = _expressao_coluna(coluna, tipo)
        try:
            con.execute(
                f"SELECT count({expressao}) FROM raw.{_identificador(tabela)}"
            ).fetchone()
        except duckdb.Error as erro:
            print(
                f"Falha de conversao em raw.{tabela}.{coluna}; "
                f"valor de exemplo e erro original do DuckDB: {erro}"
            )
            raise SystemExit(1) from erro


def _criar_tabela_refined(
    con: duckdb.DuckDBPyConnection,
    tabela: str,
    colunas: list[str],
) -> int:
    selecao = []
    for coluna in colunas:
        expressao = _expressao_coluna(coluna, TIPOS.get(tabela, {}).get(coluna))
        alias = _identificador(MAPA_COLUNAS[tabela][coluna])
        selecao.append(f"{expressao} AS {alias}")

    con.execute(
        f"""
        CREATE OR REPLACE TABLE refined.{_identificador(tabela)} AS
        SELECT DISTINCT {", ".join(selecao)}
        FROM raw.{_identificador(tabela)}
        """
    )
    return con.execute(
        f"SELECT count(*) FROM refined.{_identificador(tabela)}"
    ).fetchone()[0]


def _contar_nulos(
    con: duckdb.DuckDBPyConnection,
    tabela: str,
) -> list[tuple[str, int]]:
    colunas = list(MAPA_COLUNAS[tabela].values())
    selecao = ", ".join(
        f"count(*) FILTER (WHERE {_identificador(coluna)} IS NULL)"
        for coluna in colunas
    )
    contagens = con.execute(
        f"SELECT {selecao} FROM refined.{_identificador(tabela)}"
    ).fetchone()
    return [
        (coluna, contagem)
        for coluna, contagem in zip(colunas, contagens, strict=True)
        if contagem
    ]


def main() -> None:
    _reconfigurar_stdout_utf8()
    con = db.conectar()
    try:
        colunas_por_tabela = _validar_estrutura(con)
        metadados = {
            tabela: _validar_duplicatas(con, tabela, colunas_por_tabela[tabela])
            for tabela in TABELAS
        }

        resultados: list[tuple[str, int, int, int, list[tuple[str, int]]]] = []
        con.execute("BEGIN TRANSACTION")
        committed = False
        try:
            db.criar_schema(con, "refined")
            for tabela in TABELAS:
                _validar_conversoes(con, tabela)
                entrada, duplicatas = metadados[tabela]
                saida = _criar_tabela_refined(con, tabela, colunas_por_tabela[tabela])
                nulos = _contar_nulos(con, tabela)
                resultados.append((tabela, entrada, saida, duplicatas, nulos))
            con.execute("COMMIT")
            committed = True
        finally:
            if not committed:
                con.execute("ROLLBACK")

        total_entrada = 0
        total_saida = 0
        total_duplicatas = 0
        for tabela, entrada, saida, duplicatas, nulos in resultados:
            print(
                f"refined.{tabela:<20} {_formatar_numero(entrada)} -> "
                f"{_formatar_numero(saida)} linhas "
                f"({_formatar_numero(duplicatas)} duplicatas)"
            )
            if nulos:
                resumo_nulos = ", ".join(
                    f"{coluna} {_formatar_numero(contagem)}"
                    for coluna, contagem in nulos
                )
                print(f"    nulos mantidos: {resumo_nulos}")
            total_entrada += entrada
            total_saida += saida
            total_duplicatas += duplicatas

        print(
            f"TOTAL: {_formatar_numero(total_entrada)} -> "
            f"{_formatar_numero(total_saida)} linhas "
            f"({_formatar_numero(total_duplicatas)} duplicatas)"
        )
    finally:
        con.close()


if __name__ == "__main__":
    main()
