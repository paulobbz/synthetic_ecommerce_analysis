# Pipeline de dados: e-commerce sintético

Pipeline de dados em Python sobre um dataset sintético de comércio eletrônico, com DuckDB como banco. Projeto da Aceleração Emprega Dados - Engenheiro de Dados.

O desenvolvimento segue *spec-driven development*: `Spec.txt` especifica o projeto e a ingestão; `Spec_etapa_2.txt` especifica a transformação para `refined`.

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
│   ├── ingestao.py    # etapa 1: ingestão para o schema raw
│   ├── transformacao.py # etapa 2: conversões e regras para refined
│   └── marts.py       # materializa os marts a partir dos arquivos SQL
├── raw/               # os sete CSVs do dataset
├── marts/             # dez consultas SQL que materializam tabelas analíticas
├── ui.py              # abre a interface web do DuckDB
├── Spec.txt           # especificação do projeto
├── Spec_etapa_2.txt   # especificação da transformação para refined
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

**Transformação** (converte tipos e nomes de coluna de `raw` para `refined`):

```
uv run python -m pipeline.transformacao
```

Uma linha por tabela mostra as contagens antes/depois e as duplicatas removidas; colunas com nulos mostram a quantidade mantida.

**Marts** (cria/recria as dez tabelas analíticas no schema `marts`):

```
uv run python -m pipeline.marts
```

Execute a transformação antes de materializar os marts. Cada arquivo em `marts/` corresponde a uma tabela analítica; a execução usa uma transação e substitui os resultados anteriores.

**Interface web do DuckDB** (abre o navegador em http://localhost:4213):

```
uv run python ui.py
```

Encerre com `Ctrl+C`. Com a interface aberta, a ingestão falha com "Could not set lock on file", porque o arquivo do banco aceita um único processo escrevendo. Feche a interface antes de rodar a ingestão.

## Etapas

| Etapa | Descrição | Status |
|-------|-----------|--------|
| 1 | Ingestão: CSVs para o schema `raw`, sem nenhuma transformação | concluída (tag `etapa-1`) |
| 2 | Refined: conversões de tipo e nomes de coluna conforme a spec | implementada |
| 3 | Marts: consultas analíticas materializadas no schema `marts` | implementada |
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

### Etapa 2: transformação para `refined`

A transformação lê as tabelas de `raw` e recria suas versões tipadas e com nomes de coluna em português no schema `refined`. Ela não altera `raw`, não preenche valores nulos e não corrige anomalias de negócio. Para executar:

```
uv run python -m pipeline.transformacao
```

O mapeamento de tabelas é:

| Tabela `raw` | Tabela `refined` |
|--------------|------------------|
| `raw.clientes` | `refined.clientes` |
| `raw.devolucoes` | `refined.devolucoes` |
| `raw.itens_pedido` | `refined.itens_pedido` |
| `raw.pagamentos` | `refined.pagamentos` |
| `raw.pedidos` | `refined.pedidos` |
| `raw.produtos` | `refined.produtos` |
| `raw.remessas` | `refined.remessas` |

As colunas são renomeadas para português, por exemplo `customer_id` para `cliente_id`, `order_date` para `data_pedido` e `unit_price` para `preco_unitario`. Os tipos são convertidos no DuckDB: datas sem horário significativo para `DATE`; datas com horário para `TIMESTAMP`; valores monetários para `DECIMAL(10,2)`; quantidade de itens para `INTEGER`; e campos binários `0/1` para `BOOLEAN`. Identificadores e demais atributos permanecem `VARCHAR`.

Linhas inteiramente duplicadas são reduzidas a uma ocorrência. Chaves repetidas com conteúdo diferente interrompem a transformação, em vez de escolher um registro silenciosamente. Conversões inválidas também interrompem o processo; a etapa não converte erros em nulos. A execução é reprocessável e recria as tabelas em `refined`.

### Etapa 3: marts

As consultas respondem a perguntas sobre vendas mensais, produtos mais vendidos, devoluções e reembolsos por categoria, vendas por país, pagamentos por método e canal, desempenho de transportadoras, descontos por canal, recorrência de clientes, margem estimada por produto e relação entre status do pedido e do pagamento. Nove dos dez marts combinam tabelas com `JOIN`; agregações intermediárias evitam multiplicar valores de pedidos.

| Arquivo SQL | Tabela materializada | Pergunta respondida |
|-------------|----------------------|---------------------|
| `vendas_mensais.sql` | `marts.vendas_mensais` | Quanto vendemos por mês, com entregas separadas dos demais status? |
| `produtos_mais_vendidos.sql` | `marts.produtos_mais_vendidos` | Quais são os dez produtos com mais unidades vendidas em pedidos entregues? |
| `devolucoes_por_categoria.sql` | `marts.devolucoes_por_categoria` | Qual a taxa de solicitação e reembolso por categoria? |
| `vendas_por_pais.sql` | `marts.vendas_por_pais` | Quanto vendemos e qual o ticket médio por país? |
| `pagamentos_por_metodo.sql` | `marts.pagamentos_por_metodo` | Quais métodos e status de pagamento aparecem em cada canal? |
| `entregas_por_transportadora.sql` | `marts.entregas_por_transportadora` | Qual o percentual entregue e o tempo médio por transportadora? |
| `descontos_por_canal.sql` | `marts.descontos_por_canal` | Quanto de desconto é concedido por canal e status? |
| `recorrencia_clientes.sql` | `marts.recorrencia_clientes` | Qual a recorrência de clientes por país e nível de fidelidade? |
| `margem_estimada_produto.sql` | `marts.margem_estimada_produto` | Quais produtos têm maior margem bruta estimada? |
| `status_pedido_pagamento.sql` | `marts.status_pedido_pagamento` | Como status de captura, falha ou estorno se relacionam com pedidos? |

Todos os valores de vendas usam a moeda registrada nos pedidos (atualmente USD). O mart de vendas mensais inclui uma métrica de pedidos entregues (`vendas_entregues`) separada do total registrado em todos os status (`valor_pedido_registrado`). O mart de devoluções distingue solicitações de itens efetivamente reembolsados. A margem é estimada com o custo atual do produto e não deduz frete, impostos, descontos alocados ou reembolsos.

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
