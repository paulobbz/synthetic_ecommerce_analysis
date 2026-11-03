import shutil
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from pipeline import db, marts

_DDL_REFINED = (
    """
    CREATE TABLE refined.clientes (
        cliente_id VARCHAR, pais VARCHAR, nivel_fidelidade VARCHAR
    )
    """,
    """
    CREATE TABLE refined.devolucoes (
        devolucao_id VARCHAR, item_pedido_id VARCHAR, status VARCHAR,
        valor_reembolso DECIMAL(10, 2)
    )
    """,
    """
    CREATE TABLE refined.itens_pedido (
        item_pedido_id VARCHAR, pedido_id VARCHAR, produto_id VARCHAR,
        quantidade INTEGER, preco_unitario DECIMAL(10, 2),
        total_item DECIMAL(10, 2)
    )
    """,
    """
    CREATE TABLE refined.pagamentos (
        pagamento_id VARCHAR, pedido_id VARCHAR, metodo VARCHAR,
        status VARCHAR, valor DECIMAL(10, 2)
    )
    """,
    """
    CREATE TABLE refined.pedidos (
        pedido_id VARCHAR, cliente_id VARCHAR, data_pedido TIMESTAMP,
        status VARCHAR, canal VARCHAR, subtotal DECIMAL(10, 2),
        valor_desconto DECIMAL(10, 2), valor_frete DECIMAL(10, 2),
        valor_imposto DECIMAL(10, 2), valor_total DECIMAL(10, 2),
        moeda VARCHAR
    )
    """,
    """
    CREATE TABLE refined.produtos (
        produto_id VARCHAR, nome_produto VARCHAR, categoria VARCHAR,
        custo_unitario DECIMAL(10, 2)
    )
    """,
    """
    CREATE TABLE refined.remessas (
        remessa_id VARCHAR, pedido_id VARCHAR, transportadora VARCHAR,
        data_envio TIMESTAMP, data_entrega TIMESTAMP
    )
    """,
)


def _criar_refined(conexao, com_dados=True):
    conexao.execute("CREATE SCHEMA refined")
    for ddl in _DDL_REFINED:
        conexao.execute(ddl)
    if not com_dados:
        return

    conexao.execute(
        "INSERT INTO refined.clientes VALUES "
        "('c1', 'Brasil', 'gold'), ('c2', 'Chile', 'silver')"
    )
    conexao.execute(
        "INSERT INTO refined.devolucoes VALUES "
        "('r1', 'i1', 'requested', 0), ('r2', 'i2', 'refunded', 10)"
    )
    conexao.execute(
        "INSERT INTO refined.itens_pedido VALUES "
        "('i1', 'o1', 'p1', 2, 10, 20), "
        "('i2', 'o1', 'p1', 1, 10, 10), "
        "('i3', 'o2', 'p2', 4, 5, 20)"
    )
    conexao.execute(
        "INSERT INTO refined.pagamentos VALUES "
        "('pg1', 'o1', 'card', 'captured', 35), "
        "('pg2', 'o2', 'card', 'failed', 35)"
    )
    conexao.execute(
        "INSERT INTO refined.pedidos VALUES "
        "('o1', 'c1', '2025-01-15 10:00:00', 'delivered', 'web', "
        "30, 0, 2, 3, 35, 'USD'), "
        "('o2', 'c2', '2025-01-20 12:00:00', 'cancelled', 'store', "
        "40, 5, 0, 0, 35, 'USD')"
    )
    conexao.execute(
        "INSERT INTO refined.produtos VALUES "
        "('p1', 'Produto A', 'equipamento', 6), "
        "('p2', 'Produto B', 'roupa', 2)"
    )
    conexao.execute(
        "INSERT INTO refined.remessas VALUES "
        "('s1', 'o1', 'Correios', '2025-01-15 15:00:00', "
        "'2025-01-17 15:00:00')"
    )


def _banco_temporario(monkeypatch, tmp_path, com_dados=True):
    caminho = tmp_path / "ecommerce.duckdb"
    conexao = duckdb.connect(str(caminho))
    _criar_refined(conexao, com_dados=com_dados)
    conexao.close()
    monkeypatch.setattr(db, "conectar", lambda: duckdb.connect(str(caminho)))
    return caminho


def _copiar_sqls(pasta_destino):
    pasta_origem = Path(__file__).resolve().parent.parent / "marts"
    shutil.copytree(pasta_origem, pasta_destino)
    return pasta_destino


def test_marts_materializa_dez_tabelas_e_reexecuta_sem_acumular(
    monkeypatch, tmp_path, capsys
):
    caminho = _banco_temporario(monkeypatch, tmp_path)

    marts.main()
    primeira_saida = capsys.readouterr().out
    marts.main()
    segunda_saida = capsys.readouterr().out

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        tabelas = conexao.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'marts' ORDER BY table_name"
        ).fetchall()
        receita = conexao.execute(
            "SELECT valor_pedido_registrado, vendas_entregues, "
            "pedidos_total, pedidos_entregues FROM marts.vendas_mensais"
        ).fetchone()
        assert len(tabelas) == len(marts.MODELOS)
        assert receita == (Decimal("70.00"), Decimal("35.00"), 2, 1)
    finally:
        conexao.close()
    assert primeira_saida == segunda_saida
    assert "marts.vendas_mensais: 1 linhas" in primeira_saida


def test_pedido_cancelado_nao_entra_em_vendas_entregues(tmp_path):
    caminho = tmp_path / "vendas.duckdb"
    conexao = duckdb.connect(str(caminho))
    _criar_refined(conexao)
    conexao.execute("CREATE SCHEMA marts")
    sql = (Path(__file__).resolve().parent.parent / "marts" / "vendas_mensais.sql").read_text(
        encoding="utf-8"
    )
    conexao.execute(sql)
    linha = conexao.execute(
        "SELECT pedidos_total, pedidos_entregues, valor_pedido_registrado, "
        "vendas_entregues, ticket_entregue FROM marts.vendas_mensais"
    ).fetchone()
    conexao.close()

    assert linha == (2, 1, Decimal("70.00"), Decimal("35.00"), 35.0)


def test_produtos_mais_vendidos_exclui_itens_de_pedidos_cancelados(tmp_path):
    caminho = tmp_path / "produtos.duckdb"
    conexao = duckdb.connect(str(caminho))
    _criar_refined(conexao)
    conexao.execute("CREATE SCHEMA marts")
    sql = (
        Path(__file__).resolve().parent.parent
        / "marts"
        / "produtos_mais_vendidos.sql"
    ).read_text(encoding="utf-8")
    conexao.execute(sql)
    linhas = conexao.execute(
        "SELECT produto_id, unidades_entregues, receita_itens "
        "FROM marts.produtos_mais_vendidos"
    ).fetchall()
    conexao.close()

    assert linhas == [("p1", 3, Decimal("30.00"))]


def test_devolucoes_calcula_solicitacao_reembolso_e_valor(tmp_path):
    caminho = tmp_path / "devolucoes.duckdb"
    conexao = duckdb.connect(str(caminho))
    _criar_refined(conexao)
    conexao.execute("CREATE SCHEMA marts")
    sql = (
        Path(__file__).resolve().parent.parent
        / "marts"
        / "devolucoes_por_categoria.sql"
    ).read_text(encoding="utf-8")
    conexao.execute(sql)
    linha = conexao.execute(
        """
        SELECT itens_pedidos, itens_com_solicitacao,
               pct_itens_com_solicitacao, itens_reembolsados,
               pct_itens_reembolsados, valor_reembolsado
        FROM marts.devolucoes_por_categoria
        WHERE categoria = 'equipamento'
        """
    ).fetchone()
    conexao.close()

    assert linha == (2, 2, 100.0, 1, 50.0, Decimal("10.00"))


def test_mart_vazio_e_resultado_valido(monkeypatch, tmp_path, capsys):
    caminho = _banco_temporario(monkeypatch, tmp_path, com_dados=False)

    marts.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        vazias = conexao.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'marts' AND table_name IN "
            "(SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'marts')"
        ).fetchone()[0]
        linhas = conexao.execute(
            "SELECT count(*) FROM marts.vendas_mensais"
        ).fetchone()[0]
        assert vazias == len(marts.MODELOS)
        assert linhas == 0
    finally:
        conexao.close()
    assert "marts.vendas_mensais: 0 linhas" in capsys.readouterr().out


def test_arquivo_sql_ausente_para_sem_conectar_e_preserva_marts(
    monkeypatch, tmp_path, capsys
):
    caminho = tmp_path / "ecommerce.duckdb"
    conexao = duckdb.connect(str(caminho))
    conexao.execute("CREATE SCHEMA marts")
    conexao.execute("CREATE TABLE marts.anterior AS SELECT 42 AS valor")
    conexao.close()
    pasta_sql = _copiar_sqls(tmp_path / "sql")
    (pasta_sql / f"{marts.MODELOS[0]}.sql").unlink()
    monkeypatch.setattr(marts, "PASTA_MARTS", pasta_sql)
    chamadas_conexao = []

    def conectar():
        chamadas_conexao.append(True)
        return duckdb.connect(str(caminho))

    monkeypatch.setattr(db, "conectar", conectar)
    with pytest.raises(SystemExit) as erro:
        marts.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        valor = conexao.execute("SELECT valor FROM marts.anterior").fetchone()[0]
        assert erro.value.code == 1
        assert valor == 42
        assert not chamadas_conexao
    finally:
        conexao.close()
    assert f"{marts.MODELOS[0]}.sql" in capsys.readouterr().out


def test_tabelas_refined_ausentes_interrompem_sem_criar_marts(
    monkeypatch, tmp_path, capsys
):
    caminho = tmp_path / "ecommerce.duckdb"
    monkeypatch.setattr(db, "conectar", lambda: duckdb.connect(str(caminho)))

    with pytest.raises(SystemExit) as erro:
        marts.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        schemas = conexao.execute(
            "SELECT schema_name FROM information_schema.schemata"
        ).fetchall()
        assert erro.value.code == 1
        assert ("marts",) not in schemas
    finally:
        conexao.close()
    assert "refined" in capsys.readouterr().out


def test_falha_sql_faz_rollback_e_preserva_tabelas_existentes(
    monkeypatch, tmp_path, capsys
):
    caminho = _banco_temporario(monkeypatch, tmp_path)
    conexao = duckdb.connect(str(caminho))
    conexao.execute("CREATE SCHEMA marts")
    conexao.execute("CREATE TABLE marts.anterior AS SELECT 42 AS valor")
    conexao.close()
    pasta_sql = _copiar_sqls(tmp_path / "sql")
    (pasta_sql / f"{marts.MODELOS[0]}.sql").write_text(
        "CREATE TABLE marts.vendas_mensais AS SELECT * FROM refined.inexistente;",
        encoding="utf-8",
    )
    monkeypatch.setattr(marts, "PASTA_MARTS", pasta_sql)

    with pytest.raises(SystemExit) as erro:
        marts.main()

    conexao = duckdb.connect(str(caminho), read_only=True)
    try:
        tabelas = conexao.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'marts' ORDER BY table_name"
        ).fetchall()
        valor = conexao.execute("SELECT valor FROM marts.anterior").fetchone()[0]
        assert erro.value.code == 1
        assert tabelas == [("anterior",)]
        assert valor == 42
    finally:
        conexao.close()
    assert "Falha ao executar" in capsys.readouterr().out
