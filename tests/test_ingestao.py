import csv

import duckdb
import pytest

from pipeline import db, ingestao


def _escrever_csvs(pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    for indice, nome_arquivo in enumerate(ingestao.MAPA_TABELAS):
        caminho = pasta / nome_arquivo
        with caminho.open("w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(["codigo", "texto"])
            if indice == 0:
                escritor.writerows(
                    [
                        ["001", "NA"],
                        ["002", "N/A"],
                        ["003", "NULL"],
                        ["004", "None"],
                        ["005", "nan"],
                        ["006", ""],
                    ]
                )
            else:
                escritor.writerow([f"{indice:03}", "preservado"])


def _conectar_ao_banco_temporario(monkeypatch, tmp_path):
    caminho = tmp_path / "ecommerce.duckdb"
    monkeypatch.setattr(db, "conectar", lambda: duckdb.connect(str(caminho)))
    return caminho


def test_ingestao_preserva_textos_vazios_como_null_e_reexecuta(
    monkeypatch, tmp_path, capsys
):
    pasta_raw = tmp_path / "raw"
    _escrever_csvs(pasta_raw)
    monkeypatch.setattr(db, "PASTA_RAW", pasta_raw)
    caminho_banco = _conectar_ao_banco_temporario(monkeypatch, tmp_path)

    ingestao.main()
    primeira_saida = capsys.readouterr().out
    ingestao.main()
    segunda_saida = capsys.readouterr().out

    conexao = duckdb.connect(str(caminho_banco), read_only=True)
    try:
        valores = conexao.execute(
            "SELECT codigo, texto FROM raw.clientes ORDER BY codigo"
        ).fetchall()
        tipos = conexao.execute("DESCRIBE raw.clientes").fetchall()
        tabelas = conexao.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'raw'"
        ).fetchone()[0]
        assert valores == [
            ("001", "NA"),
            ("002", "N/A"),
            ("003", "NULL"),
            ("004", "None"),
            ("005", "nan"),
            ("006", None),
        ]
        assert [linha[1] for linha in tipos] == ["VARCHAR", "VARCHAR"]
        assert tabelas == len(ingestao.MAPA_TABELAS)
    finally:
        conexao.close()

    assert primeira_saida == segunda_saida
    assert "TOTAL: 12" in primeira_saida
    assert "raw.clientes: 6" in primeira_saida


def test_arquivo_ausente_para_antes_de_criar_ou_gravar_banco(
    monkeypatch, tmp_path, capsys
):
    pasta_raw = tmp_path / "raw"
    _escrever_csvs(pasta_raw)
    (pasta_raw / next(iter(ingestao.MAPA_TABELAS))).unlink()
    caminho_banco = tmp_path / "ecommerce.duckdb"
    chamadas_conexao = []

    def conectar():
        chamadas_conexao.append(True)
        return duckdb.connect(str(caminho_banco))

    monkeypatch.setattr(db, "PASTA_RAW", pasta_raw)
    monkeypatch.setattr(db, "conectar", conectar)

    with pytest.raises(SystemExit) as erro:
        ingestao.main()

    assert erro.value.code == 1
    assert not chamadas_conexao
    assert not caminho_banco.exists()
    assert next(iter(ingestao.MAPA_TABELAS)) in capsys.readouterr().out
