# Data Analytics — RA1, RA2 e RA3

**Equipe:** Gastão Eduardo e Gustavo Schott
**Curso:** Sistemas de Informação, 6º período
**Professora:** Marina de Lara

O notebook prepara a base histórica Online Retail (RA1), demonstra streaming no Apache Spark com seis eventos fictícios (RA2) e analisa o histórico com estatística descritiva, visualizações e regressão supervisionada (RA3).

## Entregas

- `projeto_data_analytics.ipynb`: código executado, análises e explicações dos três trabalhos.
- `docs/relatorio_ra1.docx`: documentação preenchida no modelo da disciplina.
- `docs/projeto_data_analytics.pdf`: PDF do notebook com código, gráficos e resultados.
- `docs/relatorio_ra3.md`: síntese dos métodos, resultados e limitações da última etapa.
- `docs/preparacao_apresentacao.md`: roteiro de fala do RA1 em dupla e dos RA2 e RA3.
- `scripts/`: preparação dos dados, análises do RA3 e geração/exportação do notebook; `tests/`: verificações do preparo existente.
- `evidence/`: fonte, diagnósticos, balanço de linhas, resultados do streaming e métricas do RA3.

**Repositório:** https://github.com/ghastsantos/data-analytics-ra1-ra2

## Abrir no Google Colab

1. Envie `projeto_data_analytics.ipynb` ao Colab.
2. Escolha **Ambiente de execução > Executar tudo**.
3. Aguarde. O notebook instala as dependências, baixa a base da UCI e executa os três trabalhos.

Ao final do RA2, os totais por minuto são 55, 30 e 10 GBP. O RA3 usa somente os dados históricos preparados; os seis eventos inventados do RA2 continuam separados.

## RA3: análise e previsão

A análise descritiva resume quantidade, preço e valor bruto por linha. Os gráficos mostram a evolução diária, a distribuição dos valores por linha e os países com maior valor registrado. A regressão estima o valor bruto diário dos itens positivos com variáveis temporais e uma divisão cronológica entre treino e teste; ela é comparada a um baseline que repete o valor do mesmo dia da semana anterior.

O valor calculado é `Quantity × UnitPrice` após as regras de preparação do RA1. Como cancelamentos não foram ligados às compras originais, esse valor não representa vendas líquidas nem lucro. A base cobre uma única loja entre 2010 e 2011 e não representa o comércio eletrônico atual.

## Base e recorte

Chen (2015), [Online Retail, UCI](https://archive.ics.uci.edu/dataset/352/online+retail), DOI 10.24432/C5BW33, licença CC BY 4.0. A base original tem 541.909 linhas. O recorte preparado tem 527.761; outras 14.148 linhas estão separadas com seus motivos.

Uma linha representa um item de uma transação. O recorte não mede vendas líquidas ou lucro, porque os cancelamentos não foram ligados às vendas correspondentes.
