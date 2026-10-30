# Pipeline de dados: e-commerce sintético

Pipeline de dados em Python sobre um dataset sintético de comércio eletrônico, com DuckDB como banco. Projeto da pós-graduação: replica, com outro dataset, as etapas do projeto original feito sobre a base da Olist ([pipeline-olist](https://github.com/ckoliveiraa/pipeline-olist)).

O desenvolvimento segue *spec-driven development*: a spec (`Spec.txt`) é a fonte da verdade e o código é consequência dela.

## Stack

- Python 3.12 ou superior, dependências gerenciadas com [uv](https://docs.astral.sh/uv/)
- pandas para ler os CSVs
- DuckDB (fixado em 1.5.6) como banco, no arquivo `ecommerce.duckdb`
- Sem orquestrador: scripts executados pela linha de comando

## Estrutura

```
.
├── pipeline/
│   ├── db.py          # conexão com o DuckDB (usada por todas as etapas)
│   └── ingestao.py    # etapa 1: ingestão para o schema raw
├── raw/               # os sete CSVs do dataset
├── ui.py              # abre a interface web do DuckDB
├── Spec.txt           # especificação do projeto
├── pyproject.toml
└── uv.lock
```

O `ecommerce.duckdb` não é versionado: ele é gerado pela ingestão.

## Como rodar

Pré-requisito: ter o `uv` instalado.

```
git clone https://github.com/paulobbz/synthetic_ecommerce_analysis.git
cd synthetic_ecommerce_analysis
uv sync
```

**Ingestão** (cria o `ecommerce.duckdb` e carrega as tabelas no schema `raw`):

```
uv run python -m pipeline.ingestao
```

A saída é uma linha por tabela, com a contagem de linhas lida do banco, e uma linha final com o total.

**Interface web do DuckDB** (abre o navegador em http://localhost:4213):

```
uv run python ui.py
```

Encerre com `Ctrl+C`. Com a interface aberta, a ingestão falha com "Could not set lock on file", porque o arquivo do banco aceita um único processo escrevendo. Feche a interface antes de rodar a ingestão.

## Etapas

| Etapa | Descrição | Status |
|-------|-----------|--------|
| 1 | Ingestão: CSVs para o schema `raw`, sem nenhuma transformação | concluída (tag `etapa-1`) |
| 2 | Refined: conversões de tipo e correções, como decisões registradas | a fazer |
| 3 | (preencher) | a fazer |
| 4 | (preencher) | a fazer |

### Etapa 1: ingestão

Cada arquivo de `raw/` vira uma tabela no schema `raw`, com nome em português:

| Arquivo | Tabela |
|---------|--------|
| `customers.csv` | `raw.clientes` |
| `order_items.csv` | `raw.itens_pedido` |
| `orders.csv` | `raw.pedidos` |
| `payments.csv` | `raw.pagamentos` |
| `products.csv` | `raw.produtos` |
| `returns.csv` | `raw.devolucoes` |
| `shipments.csv` | `raw.remessas` |

Regras da etapa:

- **Nada é corrigido.** Sem conversão de tipo, sem linha descartada, sem coluna renomeada. Toda coluna entra como texto (`VARCHAR`).
- **Só o campo vazio vira nulo.** Textos como `NA` ou `None` continuam texto, exatamente como vieram no arquivo.
- **Reexecutável.** As tabelas são recriadas a cada execução, então rodar dez vezes dá o mesmo resultado que rodar uma.
- **Tudo ou nada.** Se qualquer um dos sete CSVs faltar, o script lista os que faltam e encerra antes de gravar qualquer tabela.

## Decisões técnicas

- **`duckdb==1.5.6` fixado.** Na versão 2.0.0 a extensão `ui` falhou ao carregar no Windows (erro de inicialização de DLL); na 1.5.6 funciona.
- **`uv.lock` versionado**, para que `uv sync` reproduza o mesmo ambiente.
- **Caminhos a partir do código.** `raw/` e o `ecommerce.duckdb` são resolvidos a partir da localização de `pipeline/db.py`, e não da pasta onde o comando é executado.

## Fluxo de git

- `main`: versão estável, só recebe etapas concluídas.
- `dev`: trabalho em andamento.
- Cada etapa concluída entra na `main` por pull request (merge commit) e recebe uma tag: `etapa-1`, `etapa-2` e assim por diante.

## Autor

[@paulobbz](https://github.com/paulobbz)
