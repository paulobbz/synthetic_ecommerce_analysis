"""Spec da interface web para navegar no banco DuckDB.

Este arquivo tem um objetivo específico: abrir o banco do projeto no navegador, em vez de forçar o usuário a ler tabelas pelo terminal. O browser é a forma mais natural de explorar os dados, especialmente quando a extensão ui do DuckDB expõe o schema e os objetos de forma visual. A regra do projeto é abrir o arquivo ecommerce.duckdb da raiz do projeto e não criar um banco novo se ele não existir; isso impede a falsa sensação de que a ingestão funcionou quando, na verdade, o navegador abriu um banco vazio.

A extensão ui precisa ser instalada e carregada no próprio DuckDB antes de chamar start_ui(). A chamada a esse procedimento faz o servidor entrar em modo de serviço em http://localhost:4213 e abrir o navegador. O script mantém esse processo vivo enquanto a conexão estiver aberta, porque a extensão serve enquanto a conexão existe; quando ela chega ao fim, o servidor para. Isto é o comportamento que a ferramenta precisa, e a mensagem "Ctrl+C para encerrar" deixa explícito como desligar a UI com segurança.

A etapa de UI não cria o arquivo do banco. Se o arquivo não estiver presente, o script deve informar que é preciso rodar a ingestão antes e sair com sys.exit(1). Isso é importante porque o módulo de conexão em pipeline/db.py cria o arquivo quando ele falta, mas neste caso a regra é justamente não fazer isso: a UI não pode mascarar um banco inexistente como se fosse um estado válido.

Separação de responsabilidades: este arquivo não importa pipeline.ingestao, e a etapa de ingestão não importa ui.py. A ingestão é uma etapa de materialização do raw; a UI é apenas uma ferramenta de exploração e não participa do processamento de dados. Isso mantém o pipeline executável mesmo sem a extensão ui e evita acoplamento desnecessário.

A saída em tela segue a mesma regra do restante do projeto: stdout em UTF-8, para evitar acentos quebrados no Prompt de Comando do Windows. O objetivo não é apenas mostrar a URL, mas também deixar claro como encerrar o processo sem traceback e sem deixar o arquivo .duckdb travado.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

BANCO = Path(__file__).resolve().parent / "ecommerce.duckdb"


def _reconfigurar_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    _reconfigurar_stdout_utf8()

    if not BANCO.exists():
        print(f"Banco não encontrado em {BANCO}. Rode a ingestão antes.")
        raise SystemExit(1)

    con = duckdb.connect(str(BANCO))
    try:
        con.execute("INSTALL ui;")
        con.execute("LOAD ui;")
        con.execute("CALL start_ui();")
        print("Abra o navegador em http://localhost:4213")
        print("Ctrl+C para encerrar")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando a UI do DuckDB...")
    finally:
        con.close()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        raise
