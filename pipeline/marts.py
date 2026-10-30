"""Materializa os marts definidos nos arquivos SQL de marts/."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

from pipeline import db

PASTA_MARTS = Path(__file__).resolve().parent.parent / "marts"
MODELOS = (
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


def _formatar_numero(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _reconfigurar_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def _validar_tabelas_refined(con: duckdb.DuckDBPyConnection) -> None:
    tabelas_necessarias = {
        "clientes",
        "devolucoes",
        "itens_pedido",
        "pagamentos",
        "pedidos",
        "produtos",
        "remessas",
    }
    existentes = {
        linha[0]
        for linha in con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'refined'
            """
        ).fetchall()
    }
    ausentes = sorted(tabelas_necessarias - existentes)
    if ausentes:
        print("Tabelas ausentes em refined:")
        for tabela in ausentes:
            print(f"- refined.{tabela}")
        print(
            'Rode "uv run python -m pipeline.transformacao" '
            "antes de materializar os marts."
        )
        raise SystemExit(1)


def main() -> None:
    _reconfigurar_stdout_utf8()
    arquivos = {nome: PASTA_MARTS / f"{nome}.sql" for nome in MODELOS}
    ausentes = [caminho.name for caminho in arquivos.values() if not caminho.is_file()]
    if ausentes:
        print(f"Arquivos SQL ausentes em {PASTA_MARTS}:")
        for nome in ausentes:
            print(f"- {nome}")
        raise SystemExit(1)

    consultas = {
        nome: caminho.read_text(encoding="utf-8") for nome, caminho in arquivos.items()
    }
    con = db.conectar()
    try:
        _validar_tabelas_refined(con)
        con.execute("BEGIN TRANSACTION")
        committed = False
        try:
            con.execute("CREATE SCHEMA IF NOT EXISTS marts")
            for nome, sql in consultas.items():
                try:
                    con.execute(sql)
                except duckdb.Error as erro:
                    print(f"Falha ao executar marts/{nome}.sql: {erro}")
                    raise SystemExit(1) from erro
                contagem = con.execute(
                    f'SELECT count(*) FROM marts."{nome}"'
                ).fetchone()[0]
                print(f"marts.{nome}: {_formatar_numero(contagem)} linhas")
            con.execute("COMMIT")
            committed = True
        finally:
            if not committed:
                con.execute("ROLLBACK")
    finally:
        con.close()


if __name__ == "__main__":
    main()
