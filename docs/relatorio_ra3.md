# RA3 — Análise, visualização e regressão

**Equipe:** Gastão Eduardo e Gustavo Schott | **Disciplina:** Data Analytics — Sistemas de Informação, PUCPR
**Base:** Online Retail, UCI Machine Learning Repository

## Objetivo e recorte

O RA3 analisa os registros positivos de mercadorias preparados no RA1. Cada linha da base continua representando um item de uma transação. Para resumir o histórico por dia, calculamos `Quantity × UnitPrice` por linha e somamos esses valores por data.

Chamamos a medida de **valor bruto dos itens positivos registrados**. Cancelamentos não foram ligados às compras originais, portanto o valor não representa vendas líquidas ou lucro. O conjunto analisado tem 527.761 linhas e cobre uma loja online sediada no Reino Unido, de 1º de dezembro de 2010 a 9 de dezembro de 2011.

## Análise estatística descritiva

| Variável | Média | Mediana | Desvio padrão | P90 | P99 | Máximo |
|---|---:|---:|---:|---:|---:|---:|
| Quantidade por linha (unidades) | 10,57 | 3 | 155,83 | 24 | 100 | 80.995 |
| Preço unitário (GBP) | 3,27 | 2,08 | 4,38 | 7,62 | 16,63 | 649,50 |
| Valor por linha (GBP) | 19,46 | 9,90 | 268,60 | 31,60 | 179,00 | 168.469,60 |

A média do valor por linha é quase o dobro da mediana, e o desvio padrão é alto. Isso mostra que a distribuição é assimétrica e inclui valores extremos positivos. Eles foram mantidos, seguindo o critério do RA1, pois a base inclui operações de atacado e não há evidência suficiente para removê-los como erros.

No calendário diário completo há 374 dias. A média do valor bruto diário é GBP 27.463,72, a mediana é GBP 25.206,52 e o desvio padrão é GBP 22.556,45. Em 69 dias não há itens positivos registrados; esses dias foram representados com valor zero para preservar a sequência temporal.

## Visualizações e interpretação

1. **Evolução diária:** a série tem variação diária acentuada e picos isolados. A média móvel de sete dias ajuda a observar oscilações de curto prazo. Ela não elimina nem substitui os valores diários.
2. **Distribuição por linha:** o histograma em escala logarítmica mostra a concentração de valores em faixas menores e uma cauda que alcança valores muito altos. A mediana é GBP 9,90; o percentil 90 é GBP 31,60.
3. **Países com maior valor registrado:** o Reino Unido concentra GBP 8.747.561,66, seguido pelos Países Baixos (GBP 283.889,34) e pela Irlanda (EIRE, GBP 271.164,30). O gráfico descreve o volume presente nesta base, não participação de mercado.
4. **Previsões no teste:** o gráfico compara valores observados, previsões do Random Forest e o baseline semanal nos 74 dias finais. O modelo acompanha parte do padrão semanal, mas não prevê bem picos isolados, como o observado no fim do período.

## Representatividade e limitações

Os dados correspondem ao histórico disponível de uma única loja, entre 2010 e 2011. Não são uma amostra aleatória de lojas ou clientes e não representam o comércio eletrônico atual. Há 38 países no campo `Country`, mas o volume é fortemente concentrado no Reino Unido. O identificador de cliente está ausente em 24,90% das linhas; por isso, a análise diária não depende dessa variável.

O recorte preserva 5.221 linhas idênticas extras e extremos positivos. Cancelamentos e outros registros não positivos ou que não representam mercadorias foram separados no RA1. Essas decisões podem afetar somas e comparações, e não permitem afirmar que cada linha repetida corresponde a uma venda distinta.

## Aplicação supervisionada

**Problema:** prever o valor bruto dos itens positivos registrados em um dia, usando o histórico disponível até o dia anterior. O alvo é um valor numérico, portanto foi usada regressão.

**Entradas do modelo:** valor do dia anterior, valor de sete dias antes, média dos sete dias anteriores e posição do dia da semana, codificada por seno e cosseno. Cada data é prevista usando apenas valores anteriores. Dias sem registros são mantidos como zero.

**Treino e teste:** após a remoção dos primeiros dias sem histórico suficiente para os atributos de defasagem, 293 dias foram usados para treino até 26 de setembro de 2011. Os 74 dias seguintes, de 27 de setembro a 9 de dezembro de 2011, foram reservados para teste. A divisão preserva a ordem cronológica. A avaliação é de um passo à frente: valores observados até o dia anterior estão disponíveis para a previsão do próximo dia.

**Modelo:** Random Forest com 300 árvores, `min_samples_leaf=5` e semente aleatória 42. Ele foi comparado a um baseline sazonal que prevê o valor do mesmo dia da semana anterior.

| Abordagem | MAE (GBP) | RMSE (GBP) |
|---|---:|---:|
| Random Forest | 13.607,02 | 23.879,93 |
| Baseline semanal | 14.587,53 | 24.896,61 |

O Random Forest reduziu o MAE em 6,7% e o RMSE em 4,1% em relação ao baseline neste período de teste. A melhora é modesta: o MAE ainda equivale a cerca de 54% da mediana do valor diário do conjunto. O RMSE acima do MAE reflete a influência de erros maiores. O resultado sugere que as variáveis temporais ajudam um pouco neste recorte, mas não sustentam uma previsão precisa de picos nem generalização para outros períodos ou lojas.

## Conclusão

As análises mostram uma série diária irregular, uma distribuição de valores por linha com cauda longa e forte concentração geográfica no Reino Unido. A regressão temporal superou o baseline semanal por uma margem pequena. Essas conclusões se aplicam aos registros positivos da loja no período coberto; não estimam vendas líquidas, lucro ou comportamento atual do varejo.

## Reprodução

Instale as dependências de `requirements.txt`, tenha Java 17 disponível e execute `projeto_data_analytics.ipynb` de cima para baixo. No Google Colab, envie o notebook e selecione **Ambiente de execução > Executar tudo**. Os resultados do modelo são registrados em `evidence/ra3_results.json`.

## Referências

- Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. DOI: 10.24432/C5BW33. Licença CC BY 4.0.
- scikit-learn. [RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html), [MAE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html) e [RMSE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.root_mean_squared_error.html).
- Enunciado RA3 — Analysis, Visualization and Machine Learning, disciplina Data Analytics, PUCPR, 2026.
