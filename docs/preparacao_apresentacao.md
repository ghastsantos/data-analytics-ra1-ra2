# Guia de apresentação — RA1 e RA2

Leiam juntos, depois treinem sem ler. A ideia é saber explicar o que o projeto fez; não decorar um texto.

## O que já está no repositório

- **RA1:** notebook `.ipynb` executado e relatório Word preenchido no template da disciplina.
- **RA2:** PDF do notebook com RA1, RA2 e saídas da execução; o trabalho também pede uma demonstração de cinco minutos para a professora.
- **Link público:** https://github.com/ghastsantos/data-analytics-ra1-ra2

Os arquivos das duas entregas estão no repositório. Se a disciplina também pedir anexar o PDF no Canvas ou em outra plataforma, enviem o PDF por lá; o link do GitHub não substitui esse envio.

## RA1 — apresentação em sala, em dupla

### Gastão: problema, objetivo e fonte

**Fala sugerida:**

> Nosso projeto começa com uma base chamada Online Retail, da UCI. Ela tem registros de uma loja online do Reino Unido entre 2010 e 2011, com preços em libras. Cada linha representa um item de uma transação, não um pedido inteiro. No RA1, nosso objetivo foi conferir e preparar esses dados para análises futuras por data, produto e país. Nesta etapa, não calculamos vendas líquidas nem lucro.

Depois, mostre no notebook a fonte e as primeiras linhas. A base original tem **541.909 registros e 8 colunas**. O arquivo veio em Excel; o processo registra a origem, confere o arquivo e lê a aba `Online Retail`.

### Gustavo: qualidade, decisões e resultado

**Fala sugerida:**

> Primeiro verificamos ausências, repetições, cancelamentos, valores fora do recorte e os tipos das colunas. Mantivemos clientes sem ID, repetições e quantidades ou preços positivos extremos, porque não havia justificativa suficiente para apagar essas linhas. Separamos cancelamentos, quantidades ou preços não positivos e códigos de frete, taxas e ajustes. Cada linha separada fica registrada com um motivo.

> Ao final, 527.761 linhas ficaram no recorte e 14.148 foram separadas. A soma volta às 541.909 linhas originais. Esse resultado é um conjunto preparado de itens positivos de mercadoria; não é receita líquida nem lucro, porque não relacionamos cada cancelamento à venda correspondente.

Se ajudar, mostre a tabela de balanço e a distribuição dos motivos. As exclusões exclusivas foram **9.288 cancelamentos, 1.336 quantidades não positivas, 1.181 preços não positivos e 2.343 lançamentos não mercantis**. Não some as contagens gerais de problemas de qualidade: alguns problemas aparecem juntos na mesma linha. O balanço de exclusões usa só o primeiro motivo aplicável.

### Perguntas prováveis do RA1

- **O que é uma linha?** Um item registrado numa transação; uma fatura pode ter várias linhas.
- **Por que deixaram clientes sem ID?** Porque ainda dá para usar item, quantidade, preço, data e país. Só não dá para fazer análise por cliente naquela linha. Foram mantidas 131.421 linhas preparadas sem ID de cliente.
- **Por que mantiveram repetições?** A base não tem uma chave única original de linha. Linhas iguais merecem atenção, mas igualdade sozinha não prova erro; 5.221 repetições extras permaneceram no recorte.
- **Por que não cortaram valores extremos positivos?** A base inclui clientes atacadistas e não há um limite de negócio confirmado para dizer que esses valores são erros.
- **O que significa 14.148?** São linhas separadas do recorte, mas preservadas com a linha original e o motivo. Não foram apagadas do arquivo bruto.
- **Isso é o total vendido ou lucro?** Não. É o recorte preparado. Não reconciliamos cancelamentos com as vendas originais nem calculamos lucro.

**Treino da dupla:** cada um apresenta sua parte, depois troquem: Gastão explica uma decisão de limpeza; Gustavo explica por que uma linha é item e por que o balanço fecha.

## RA2 — demonstração individual para a professora

### Explicação inicial

**Fala sugerida para Gastão:**

> No RA2, demonstro o Spark Structured Streaming acompanhando arquivos novos. A base usada para montar os exemplos vem do RA1, mas os seis eventos são inventados. Para cada evento, calculamos quantidade vezes preço e somamos os valores por janela de um minuto, usando o horário do evento. A cada chegada, a tabela mostra como os totais mudam.

### O que mostrar no notebook

1. **Eventos:** são seis eventos fictícios, enviados em três arquivos com dois eventos cada. A hora em `event_time` determina a janela; a hora de chegada do arquivo pode ser diferente.
2. **Consulta Spark:** `readStream` observa os arquivos, `window` agrupa por minuto e `sum` soma `Quantity × UnitPrice`. `count` conta os registros de evento naquela janela.
3. **Chegada 1:** `2 × 10 + 1 × 5 = 25 GBP` na janela das 10:00.
4. **Chegada 2:** `3 × 10 = 30` acrescenta à janela das 10:00, que passa de 25 a **55 GBP**. O evento das 10:01:00 abre a janela seguinte com **20 GBP**.
5. **Chegada 3:** mais **10 GBP** na janela das 10:01, que passa a **30 GBP**; outro evento abre a janela das 10:02 com **10 GBP**.

**Resultado final:** janelas 10:00, 10:01 e 10:02: **55, 30 e 10 GBP**. A soma final é **95 GBP**. O contador de eventos por janela é 3, 2 e 1; ele conta linhas de evento, não unidades de produto.

### Conceitos que podem perguntar

- **O que é streaming aqui?** O Spark consulta uma fonte que recebe arquivos e processa os novos registros à medida que chegam, em micro-lotes.
- **Chegada e horário do evento são a mesma coisa?** Não. Chegada é quando o arquivo fica disponível; `event_time` é quando o evento teria acontecido e é o horário usado para a janela.
- **Qual janela foi usada?** Tumbling, ou fixa, de um minuto. As janelas não se sobrepõem.
- **O que acontece exatamente às 10:01:00?** O início da janela conta e o fim não. Por isso, 10:01:00 pertence a `[10:01, 10:02)`, e não a `[10:00, 10:01)`.
- **Os 95 GBP são vendas reais?** Não. São só a soma dos seis eventos inventados para a demonstração.
- **Isso usa Kafka ou guarda dados permanentemente?** Não. A demonstração usa arquivos e uma tabela em memória; não implementa Kafka nem armazenamento permanente de produção.

### Roteiro para os cinco minutos

- **0:00–0:45:** apresente a pergunta e diga que os eventos são simulados.
- **0:45–1:30:** mostre a tabela dos seis eventos e explique `event_time`.
- **1:30–2:15:** aponte `readStream`, a janela de um minuto e a soma de quantidade vezes preço.
- **2:15–4:15:** mostre as três chegadas e narre 25; depois 55 e 20; por fim 55, 30 e 10.
- **4:15–5:00:** explique a fronteira das 10:01 e relembre que 95 GBP é um resultado da simulação.

Se as saídas já estiverem na tela, mostre cada chegada uma vez. Não reexecute só uma célula “Chegada”: ela bloqueia a publicação duplicada no mesmo fluxo. Se precisar repetir a execução, comece uma sessão nova e rode o notebook desde o início.

## Antes de responder

Se não souber algo, não chute. Mostre onde o notebook registra a decisão e diga o limite do que foi implementado. Para guardar a apresentação inteira:

**RA1:** base UCI → uma linha é um item → decisões justificadas → 541.909 = 527.761 + 14.148 → não é venda líquida.

**RA2:** seis eventos inventados → três chegadas → janela de um minuto por `event_time` → 55, 30 e 10 GBP → simulação, não venda real.
