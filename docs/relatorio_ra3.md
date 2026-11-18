# RA3 — Análise, visualização e regressão

**Equipe:** Gastão Eduardo e Gustavo Schott | **Disciplina:** Data Analytics — Sistemas de Informação, PUCPR
**Base:** Online Retail, UCI Machine Learning Repository

## Objetivo e recorte

Usamos as 527.761 linhas preparadas no RA1. Elas cobrem uma loja online do Reino Unido entre 1º de dezembro de 2010 e 9 de dezembro de 2011. Cada linha representa um item de uma transação.

Multiplicamos `Quantity × UnitPrice` e somamos os valores por data. Como os cancelamentos foram separados sem conciliação com as compras originais, essa soma mede o valor bruto dos itens positivos registrados em cada dia.

## Análise estatística descritiva

| Variável | Média | Mediana | Desvio padrão | P90 | P99 | Máximo |
|---|---:|---:|---:|---:|---:|---:|
| Quantidade por linha (unidades) | 10,57 | 3 | 155,83 | 24 | 100 | 80.995 |
| Preço unitário (GBP) | 3,27 | 2,08 | 4,38 | 7,62 | 16,63 | 649,50 |
| Valor por linha (GBP) | 19,46 | 9,90 | 268,60 | 31,60 | 179,00 | 168.469,60 |

A média de 19,46 GBP é quase o dobro da mediana, de 9,90 GBP. As linhas de valor alto puxam a média para cima. Mantivemos os extremos positivos porque a loja vendia no atacado e a base não permite tratá-los como erros.

O calendário tem 374 dias. A média diária foi de 27.463,72 GBP, com mediana de 25.206,52 GBP e desvio padrão de 22.556,45 GBP. Preenchemos com zero os 69 dias sem itens positivos registrados para manter a sequência diária.

## Visualizações e interpretação

1. Na série diária, a média móvel de sete dias suaviza as oscilações. A linha dos totais diários preserva os picos.
2. O histograma usa escala logarítmica para incluir os valores mais altos. Em 90% das linhas, o valor ficou em até 31,60 GBP.
3. O Reino Unido concentra 8.747.561,66 GBP, seguido pelos Países Baixos (283.889,34 GBP) e pela Irlanda (EIRE, 271.164,30 GBP). O gráfico mostra onde se concentram os registros da loja.
4. No período de teste, o Random Forest acompanha parte da variação semanal, mas erra picos isolados, como o que aparece perto do fim da série.

## Representatividade e limitações

As conclusões se limitam a essa loja e ao período observado. Há 38 países no campo `Country`, com forte concentração no Reino Unido. O identificador de cliente está ausente em 24,90% das linhas, e a análise diária usa data, quantidade e preço.

Mantivemos 5.221 linhas idênticas extras no recorte. Sem um identificador único por item de transação, não dá para saber quantas dessas linhas são repetições indevidas.

## Aplicação supervisionada

O Random Forest estima o total do dia com os valores de um e sete dias antes, a média dos sete dias anteriores e o dia da semana (codificado por seno e cosseno). Usamos 300 árvores, `min_samples_leaf=5` e `random_state=42`.

Os sete primeiros dias fornecem o histórico para montar as entradas. Treinamos com os 293 dias seguintes, até 26 de setembro de 2011, e testamos nos 74 dias de 27 de setembro a 9 de dezembro. Para cada previsão, usamos os valores observados até o dia anterior.

Como referência, usamos o total do mesmo dia da semana anterior. O MAE mede o erro absoluto médio. O RMSE dá mais peso aos erros grandes. Ambos são expressos em GBP.

| Abordagem | MAE (GBP) | RMSE (GBP) |
|---|---:|---:|
| Random Forest | 13.607,02 | 23.879,93 |
| Referência semanal | 14.587,53 | 24.896,61 |

No teste, o Random Forest reduziu o MAE em 6,7% e o RMSE em 4,1%. Mesmo com a melhora, o erro absoluto médio ainda equivale a 54% da mediana diária do período completo.

## Reprodução

No Google Colab, abra o notebook e selecione **Ambiente de execução > Executar tudo**. Para rodar localmente, siga o [README](../README.md#abrir-no-google-colab). [Métricas da execução](../evidence/ra3_results.json).

## Referências

- Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. DOI: 10.24432/C5BW33. Licença CC BY 4.0.
- scikit-learn. [RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html), [MAE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html) e [RMSE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.root_mean_squared_error.html).
- Enunciado RA3 — Analysis, Visualization and Machine Learning, disciplina Data Analytics, PUCPR, 2026.
