from collections.abc import Callable

import duckdb
import pytest

from pipeline import db, transformacao


def _valor_de_origem(tabela, coluna):
    tipo = transformacao.TIPOS.get(tabela, {}).get(coluna)
    if tipo == "DATE":
        return "2025-02-03"
    if tipo in {"TIMESTAMP", "DATE_TIMESTAMP"}:
        return "2025-02-03 15:30:00"
    if tipo == "DECIMAL":
        return "12.34"
    if tipo == "INTEGER":
        return "2"
    if tipo == "BOOLEAN":
        return "1"
    if coluna in transformacao.CHAVES[tabela]:
        return f"{tabela}_{coluna}"
    return f"valor_{coluna}"


def _criar_raw(conexao, modificar: Callable | None = None):
    conexao.execute("CREATE SCHEMA raw")
    for tabela, mapa in transformacao.MAPA_COLUNAS.items():
        colunas = list(mapa)
        definicoes = ", ".join(f'"{coluna}" VARCHAR' for coluna in colunas)
        conexao.execute(f'CREATE TABLE raw."{tabela}" ({definicoes})')
        valores = [_valor_de_origem(tabela, coluna) for coluna in colunas]
        if modificar is not None:
            modificar(tabela, colunas, valores, conexao)
        marcadores = ", ".join("?" for _ in valores)
        conexao.execute(
            f'INSERT INTO raw."{tabela}" VALUES ({marcadores})', valores
        )


def _conectar_ao_banco_temporario(monkeypatch, tmp_path):
    caminho = tmp_path / "ecommerce.duckdb"
    monkeypatch.setattr(db, "conectar", lambda: duckdb.connect(str(caminho)))
    return caminho


def test_transformacao_renomeia_converte_tipos_preserva_null_e_raw(
    monkeypatch, tmp_path
):
    caminho = _conectar_ao_banco_temporario(monkeypatch, tmp_path)
    conexao = duckdb.connect(str(caminho))
    _criar_raw(conexao)
    conexao.execute(
        "UPDATE raw.clientes SET phone = NULL, marketing_opt_in = '0'"
    )
    conexao.close()

    transformacao.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        colunas_pedidos = {
            linha[0]: linha[1]
            for linha in conexao.execute("DESCRIBE refined.pedidos").fetchall()
        }
        colunas_clientes = {
            linha[0]: linha[1]
            for linha in conexao.execute("DESCRIBE refined.clientes").fetchall()
        }
        colunas_itens = {
            linha[0]: linha[1]
            for linha in conexao.execute("DESCRIBE refined.itens_pedido").fetchall()
        }
        valores = conexao.execute(
            "SELECT cliente_id, telefone, aceita_marketing "
            "FROM refined.clientes"
        ).fetchone()
        tabelas_raw = conexao.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'raw'"
        ).fetchone()[0]
        assert colunas_pedidos["data_pedido"] == "TIMESTAMP"
        assert colunas_pedidos["valor_total"] == "DECIMAL(10,2)"
        assert colunas_clientes["data_cadastro"] == "DATE"
        assert colunas_clientes["aceita_marketing"] == "BOOLEAN"
        assert colunas_itens["quantidade"] == "INTEGER"
        assert colunas_itens["produto_id"] == "VARCHAR"
        assert valores == ("clientes_customer_id", None, False)
        assert tabelas_raw == len(transformacao.TABELAS)
    finally:
        conexao.close()


def test_transformacao_remove_somente_linha_inteira_duplicada(
    monkeypatch, tmp_path, capsys
):
    caminho = _conectar_ao_banco_temporario(monkeypatch, tmp_path)
    conexao = duckdb.connect(str(caminho))
    _criar_raw(conexao)
    dados = conexao.execute("SELECT * FROM raw.clientes").fetchone()
    marcadores = ", ".join("?" for _ in dados)
    conexao.execute(f"INSERT INTO raw.clientes VALUES ({marcadores})", dados)
    conexao.close()

    transformacao.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        entrada = conexao.execute("SELECT count(*) FROM raw.clientes").fetchone()[0]
        saida = conexao.execute("SELECT count(*) FROM refined.clientes").fetchone()[0]
        assert (entrada, saida) == (2, 1)
    finally:
        conexao.close()
    assert "1 duplicatas" in capsys.readouterr().out


def test_chave_conflitante_interrompe_sem_escrever_refined(
    monkeypatch, tmp_path, capsys
):
    caminho = _conectar_ao_banco_temporario(monkeypatch, tmp_path)
    conexao = duckdb.connect(str(caminho))
    _criar_raw(conexao)
    conexao.execute(
        "INSERT INTO raw.clientes SELECT * REPLACE ('outro' AS first_name) "
        "FROM raw.clientes"
    )
    conexao.close()

    with pytest.raises(SystemExit) as erro:
        transformacao.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        schemas = conexao.execute(
            "SELECT schema_name FROM information_schema.schemata"
        ).fetchall()
        assert erro.value.code == 1
        assert ("refined",) not in schemas
    finally:
        conexao.close()
    assert "clientes_customer_id" in capsys.readouterr().out


def test_conversao_invalida_faz_rollback_e_preserva_refined(
    monkeypatch, tmp_path, capsys
):
    caminho = _conectar_ao_banco_temporario(monkeypatch, tmp_path)
    conexao = duckdb.connect(str(caminho))
    _criar_raw(conexao)
    conexao.execute("UPDATE raw.pedidos SET order_date = 'data-invalida'")
    conexao.execute("CREATE SCHEMA refined")
    conexao.execute("CREATE TABLE refined.anterior AS SELECT 7 AS valor")
    conexao.close()

    with pytest.raises(SystemExit) as erro:
        transformacao.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        tabelas_refined = conexao.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'refined'"
        ).fetchall()
        valor_anterior = conexao.execute(
            "SELECT valor FROM refined.anterior"
        ).fetchone()[0]
        assert erro.value.code == 1
        assert tabelas_refined == [("anterior",)]
        assert valor_anterior == 7
    finally:
        conexao.close()
    saida = capsys.readouterr().out
    assert "raw.pedidos.order_date" in saida
    assert "strptime" in saida.lower() or "date" in saida.lower()


def test_tabela_raw_ausente_interrompe_antes_de_criar_refined(
    monkeypatch, tmp_path
):
    caminho = _conectar_ao_banco_temporario(monkeypatch, tmp_path)
    conexao = duckdb.connect(str(caminho))
    _criar_raw(conexao)
    conexao.execute("DROP TABLE raw.produtos")
    conexao.close()

    with pytest.raises(SystemExit) as erro:
        transformacao.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        schemas = conexao.execute(
            "SELECT schema_name FROM information_schema.schemata"
        ).fetchall()
        assert erro.value.code == 1
        assert ("refined",) not in schemas
    finally:
        conexao.close()
