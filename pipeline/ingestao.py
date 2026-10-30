"""Spec da etapa de ingestão do dado cru.

A regra central desta etapa é preservar o dado como ele chegou, sem nenhum tipo de correção ou normalização. Nenhuma conversão de tipo, nenhum valor preenchido, nenhuma linha descartada e nenhum nome de coluna alterado. A razão é separar claramente a fronteira entre o dado que entrou no sistema e o dado que será refinado e validado em outra etapa. Se a limpeza acontecesse aqui, a linha entre o raw e o refined desapareceria e a auditoria do pipeline ficaria impossível.

Os arquivos CSV são lidos diretamente da pasta raw com encoding explícito utf-8, sem inferência de tipos e sem adivinhação de charset. Isso é necessário porque a etapa não pode modificar dados por conta de um caractere ou um ID numérico com zero à esquerda; a conversão e a decisão de tipo acontecem mais à frente, em uma etapa específica para isso. O pandas lê cada coluna como texto para que CEP, IDs ou campos numéricos sejam mantidos como strings e o zero não desapareça silenciosamente.

A reexecução é um requisito explícito: rodar a etapa dez vezes deve ter o mesmo efeito que rodar uma vez. Por isso a tabela é recriada em cada execução com CREATE OR REPLACE TABLE, nunca acrescentada. Essa política permite corrigir erros sem medo, porque a ingestão continua determinística.

O script também valida a existência dos sete arquivos antes de abrir o banco. Não pode ingerir parcialmente seis de sete tabelas em silêncio, porque o dashboard ficaria errado como se o dado estivesse completo. Ao detectar qualquer falha, o programa lista os arquivos ausentes, informa a pasta procurada e termina com sys.exit(1) antes de gravar qualquer tabela.

A saída em tela é a única conferência desta etapa. Cada tabela imprime uma linha com o nome qualificado e a contagem vindas do banco, com milhar separador em ponto; a última linha informa o total. A configuração do stdout para utf-8 é imprescindível no Prompt de Comando do Windows, onde acentos e caracteres especiais costumam vir embaralhados sem essa reconfiguração.

O objetivo desta etapa é estritamente materializar o raw em DuckDB, sem depender de qualquer outra parte do sistema e sem abrir o navegador ou o servidor UI. O código apenas lê os CSV, cria o schema raw e grava cada tabela em ordem, deixando o banco em um estado consistente e reproduzível.
"""
from __future__ import annotations

import sys

import pandas as pd

from pipeline import db

MAPA_TABELAS = {
    "customers.csv": "clientes",
    "order_items.csv": "itens_pedido",
    "orders.csv": "pedidos",
    "payments.csv": "pagamentos",
    "products.csv": "produtos",
    "returns.csv": "devolucoes",
    "shipments.csv": "remessas",
}


def _formatar_numero(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _reconfigurar_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    _reconfigurar_stdout_utf8()

    arquivos_ausentes = [nome for nome in MAPA_TABELAS if not (db.PASTA_RAW / nome).is_file()]
    if arquivos_ausentes:
        print(f"Arquivos ausentes em {db.PASTA_RAW}:")
        for nome in arquivos_ausentes:
            print(f"- {nome}")
        raise SystemExit(1)

    con = db.conectar()
    try:
        db.criar_schema(con, "raw")
        total = 0

        for nome_arquivo, nome_tabela in MAPA_TABELAS.items():
            caminho = db.PASTA_RAW / nome_arquivo
            df = pd.read_csv(caminho, encoding="utf-8", dtype=str, keep_default_na=True)
            contagem = db.gravar(con, df, "raw", nome_tabela)
            print(f"raw.{nome_tabela}: {_formatar_numero(contagem)}")
            total += contagem

        print(f"TOTAL: {_formatar_numero(total)}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
