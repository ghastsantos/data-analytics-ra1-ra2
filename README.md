# Data Analytics — RA1, RA2 e RA3

**Equipe:** Gastão Eduardo e Gustavo Schott
**Curso:** Sistemas de Informação, 6º período
**Professora:** Marina de Lara

O RA1 prepara a base Online Retail. O RA2 usa seis eventos fictícios para demonstrar streaming com Apache Spark. No RA3, usamos o histórico preparado no RA1 para analisar os registros da loja e testar uma previsão de um dia à frente.

## Entregas

- Código, gráficos e resultados das três etapas no [notebook](projeto_data_analytics.ipynb) e no [PDF](docs/projeto_data_analytics.pdf).
- Metodologia e resultados no [relatório do RA1](docs/relatorio_ra1.docx) e no [relatório do RA3](docs/relatorio_ra3.md).
- [Roteiro de apresentação](docs/preparacao_apresentacao.md) e [registros de execução](evidence/).

## Abrir no Google Colab

Envie `projeto_data_analytics.ipynb` ao Colab e selecione **Ambiente de execução > Executar tudo**. O notebook instala as dependências e baixa a base da UCI na primeira execução.

Para rodar localmente, use Python 3.12 e Java 17, instale as dependências com `python -m pip install -r requirements.txt` e abra o notebook na raiz do repositório.

## RA3 — análise e previsão

Calculamos o valor de cada linha com `Quantity × UnitPrice`. Os gráficos mostram a evolução diária, a distribuição dos valores por linha e os dez países com maior valor registrado.

Nos 74 dias de teste, o Random Forest obteve um erro absoluto médio de **13.607,02 GBP**. A referência semanal, que repete o valor de sete dias antes, obteve **14.587,53 GBP**. A redução foi de **6,7%**, e os maiores picos continuaram difíceis de prever. [Métricas da execução](evidence/ra3_results.json).

## Base e recorte

A base cobre uma loja online do Reino Unido entre dezembro de 2010 e dezembro de 2011. Cada linha representa um item de uma transação. Das 541.909 linhas originais, 527.761 ficaram no recorte e 14.148 foram separadas com o motivo da exclusão. Como o preparo separa os cancelamentos sem conciliá-los com as compras, as somas medem o valor bruto dos itens positivos registrados.

Chen (2015), DOI 10.24432/C5BW33, licença CC BY 4.0. [Online Retail, UCI](https://archive.ics.uci.edu/dataset/352/online+retail).
