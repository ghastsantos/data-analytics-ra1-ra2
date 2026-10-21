# Data Analytics — RA1 e RA2

**Equipe:** Gastão Eduardo e Gustavo Schott
**Curso:** Sistemas de Informação, 6º período
**Professora:** Marina de Lara

O notebook prepara a base histórica Online Retail (RA1) e mostra uma demonstração de streaming no Apache Spark com seis eventos fictícios (RA2).

## Entregas

- `projeto_data_analytics.ipynb`: código executado e explicações dos dois trabalhos.
- `docs/relatorio_ra1.docx`: documentação preenchida no modelo da disciplina.
- `docs/projeto_data_analytics.pdf`: PDF do notebook para o RA2.
- `docs/preparacao_apresentacao.md`: roteiro de fala do RA1 em dupla e do RA2 individual.
- `scripts/` e `tests/`: código da preparação e verificações.
- `evidence/`: fonte, diagnósticos, balanço de linhas e resultados do streaming.

**Repositório:** https://github.com/ghastsantos/data-analytics-ra1-ra2

## Abrir no Google Colab

1. Envie `projeto_data_analytics.ipynb` ao Colab.
2. Escolha **Ambiente de execução > Executar tudo**.
3. Aguarde. O notebook instala as dependências, baixa a base da UCI e executa os dois trabalhos.

Ao final do RA2, os totais por minuto são 55, 30 e 10 GBP. Os dados históricos e os seis eventos inventados ficam separados.

## Base e recorte

Chen (2015), [Online Retail, UCI](https://archive.ics.uci.edu/dataset/352/online+retail), DOI 10.24432/C5BW33, licença CC BY 4.0. A base original tem 541.909 linhas. O recorte preparado tem 527.761; outras 14.148 linhas estão separadas com seus motivos.

Uma linha representa um item de uma transação. O recorte não mede vendas líquidas ou lucro, porque os cancelamentos não foram ligados às vendas correspondentes.
