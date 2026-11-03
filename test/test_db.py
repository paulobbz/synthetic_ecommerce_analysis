import os
import subprocess
import sys

import duckdb
import pandas as pd

from pipeline import db


def _redirecionar_conexao(monkeypatch, tmp_path):
    raiz = tmp_path / "projeto"
    (raiz / "pipeline").mkdir(parents=True)
    monkeypatch.setattr(db, "__file__", str(raiz / "pipeline" / "db.py"))
    return raiz / "ecommerce.duckdb"


def test_importar_db_nao_cria_arquivo_de_banco(tmp_path):
    raiz = os.path.abspath(os.getcwd())
    ambiente = os.environ.copy()
    ambiente["PYTHONPATH"] = raiz

    resultado = subprocess.run(
        [sys.executable, "-c", "import pipeline.db"],
        cwd=tmp_path,
        env=ambiente,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultado.returncode == 0
    assert not (tmp_path / "ecommerce.duckdb").exists()


def test_conectar_cria_banco_na_raiz_do_modulo(monkeypatch, tmp_path):
    caminho_banco = _redirecionar_conexao(monkeypatch, tmp_path)
    diretorio_corrente = tmp_path / "outra_pasta"
    diretorio_corrente.mkdir()
    monkeypatch.chdir(diretorio_corrente)

    conexao = db.conectar()
    try:
        assert caminho_banco.is_file()
        assert not (diretorio_corrente / "ecommerce.duckdb").exists()
    finally:
        conexao.close()


def test_criar_schema_e_idempotente(tmp_path):
    conexao = duckdb.connect(str(tmp_path / "teste.duckdb"))
    try:
        db.criar_schema(conexao, "raw")
        db.criar_schema(conexao, "raw")
        schemas = conexao.execute(
            "SELECT schema_name FROM information_schema.schemata"
        ).fetchall()
        assert ("raw",) in schemas
    finally:
        conexao.close()


def test_gravar_preserva_dados_tipos_nulls_e_substitui_tabela(tmp_path):
    conexao = duckdb.connect(str(tmp_path / "teste.duckdb"))
    try:
        db.criar_schema(conexao, "raw")
        original = pd.DataFrame(
            {"codigo": ["001", "002", "003"], "valor": [1.25, None, 3.75]}
        )
        assert db.gravar(conexao, original, "raw", "amostra") == 3
        substituta = pd.DataFrame({"codigo": ["004"], "valor": [9.5]})
        assert db.gravar(conexao, substituta, "raw", "amostra") == 1

        linhas = conexao.execute(
            "SELECT codigo, valor FROM raw.amostra ORDER BY codigo"
        ).fetchall()
        tipos = conexao.execute("DESCRIBE raw.amostra").fetchall()
        objetos = conexao.execute(
            """
            SELECT table_type, table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
            """
        ).fetchall()
        assert linhas == [("004", 9.5)]
        assert [linha[1] for linha in tipos] == ["VARCHAR", "DOUBLE"]
        assert objetos == [("BASE TABLE", "amostra")]
    finally:
        conexao.close()
