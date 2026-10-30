"""Spec do módulo de conexão e persistência.

Este módulo é a fronteira entre "o banco de dados" e cada etapa do pipeline. A regra central é que ele apenas conhece o caminho da pasta raw e o arquivo ecommerce.duckdb na raiz do projeto, sem saber nada sobre os CSV nem sobre qualquer tabela específica. A razão é a mesma da arquitetura do projeto: as etapas importam este módulo e todas compartilham a mesma convenção de localização do banco e do schema, sem espalhar caminhos fixos no código de cada aula.

A constante PASTA_RAW resolve a pasta raw/ a partir da localização deste arquivo, jamais a partir do diretório corrente. Isso impede que um script rodado de outra pasta crie um ecommerce.duckdb vazio no local errado, o que faz parecer que a ingestão foi executada com sucesso quando, na verdade, foi feita no lugar errado. O arquivo do banco também nasce na raiz do projeto para que qualquer etapa se conecte ao mesmo banco, independentemente de onde o comando foi disparado.

A função conectar() abre a conexão do DuckDB em modo regular e devolve o objeto conectado para que quem chamou decida quando fechar. O módulo não guarda uma conexão global porque cada execução pode ter um ciclo de vida diferente; guardar estado global cria acoplamento e quebra reexecução e testes.

A função criar_schema(con, nome) apenas garante a existência do schema solicitado. O motivo é permitir que cada etapa escolha o schema de destino sem esconder a decisão de negócio dentro do módulo de banco; este arquivo não decide nomes de schema nem regras de negócio.

A função gravar(con, df, schema, tabela) recria a tabela usando CREATE OR REPLACE TABLE, preservando as colunas e os valores do DataFrame e devolvendo a contagem lida no banco. Isso é essencial para a reexecução idempotente da ingestão, porque a contagem exibida ao usuário precisa refletir o que foi gravado e não o que ficou em memória. O módulo não lê CSV, não altera nomes de coluna e não apaga linhas; a etapa de ingestão decide isso antes de chamar gravar. O que este módulo garante é a criação e a contagem da tabela resultante, sem deixar tabela temporária ou view para trás.

A intenção aqui é manter o módulo de conexão tão simples quanto possível: ele expõe apenas a forma de encontrar os dados, abrir a conexão e gravar DataFrames no banco, sem saber nada sobre CSV, regras de negócio ou etapas do pipeline.
"""
from pathlib import Path

import duckdb

PASTA_RAW = Path(__file__).resolve().parent.parent / "raw"


def conectar():
    caminho_banco = Path(__file__).resolve().parent.parent / "ecommerce.duckdb"
    return duckdb.connect(str(caminho_banco))


def criar_schema(con, nome):
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {nome}")


def gravar(con, df, schema, tabela):
    nome_tmp = "__df_gravar__"
    con.register(nome_tmp, df)
    try:
        con.execute(f"CREATE OR REPLACE TABLE {schema}.{tabela} AS SELECT * FROM {nome_tmp}")
    finally:
        con.unregister(nome_tmp)
    return con.execute(f"SELECT count(*) FROM {schema}.{tabela}").fetchone()[0]
