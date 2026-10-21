# Colinha para apresentar o RA1 e o RA2

Não precisa decorar. Leiam juntos, entendam a ideia e usem os títulos para achar cada parte no notebook.

## RA1 — apresentação em dupla

### Gastão: explicar o começo

No Colab, procure **“RA1 — Ingestão e preparação”** e **“RA1.2 Fonte e ingestão”**.

Você pode falar assim:

> Nosso trabalho usa uma base chamada Online Retail, que pegamos no site da UCI. Ela tem compras de uma loja online entre 2010 e 2011. Cada linha é um item da compra, então uma compra pode aparecer em várias linhas. No RA1, a gente organizou a base para poder analisar depois. Ela começa com 541.909 linhas e 8 colunas.

Mostre a fonte e a tabelinha com algumas linhas. Aponte que tem data, produto, quantidade, preço e país.

### Gustavo: explicar o tratamento e o resultado

Procure **“RA1.3 Qualidade dos dados”**, **“RA1.4 Preparação”** e **“RA1.5 Resultado e validação”**.

Você pode falar assim:

> A gente conferiu o que tinha na base e separou as linhas que não entravam no nosso recorte: cancelamentos, quantidades ou preços não positivos e registros de frete, taxas e ajustes. Mantivemos clientes sem ID, repetições e valores positivos altos porque não dava para afirmar que eram erros. No fim, ficaram 527.761 linhas preparadas e 14.148 separadas. Somando as duas partes, voltamos às 541.909 linhas do começo.

Mostre a tabela dos motivos. Termine dizendo:

> Isso não quer dizer que calculamos o lucro ou as vendas líquidas. A gente não ligou cada cancelamento à venda original.

### Se perguntarem sobre o RA1

- **Por que deixaram cliente sem ID?** A linha ainda tem informação do produto, preço, quantidade e data. Só não sabemos quem foi o cliente.
- **Por que deixaram linhas repetidas?** O arquivo não diz se são erros. Apagar poderia tirar uma linha válida.
- **O que são as 14.148 linhas separadas?** Linhas que ficaram fora do recorte, mas foram guardadas com o motivo.
- **Por que não chamam o resultado de vendas?** Porque não conferimos os cancelamentos contra as vendas originais.

**Passagem:** Gastão termina dizendo “Agora o Gustavo mostra como preparamos os dados”; Gustavo fecha com o balanço e o limite do trabalho.

## RA2 — conversa individual com a professora

Procure **“RA2.2 Eventos simulados”**, **“RA2.3 Janela e consulta”** e depois as três seções **“Chegada 1”**, **“Chegada 2”** e **“Chegada 3”**.

### Como começar

> No RA2, fiz uma demonstração com Spark. Preparei seis eventos inventados e mandei em três arquivos, dois de cada vez. O Spark lê cada chegada e soma o valor dos itens por minuto. Esses eventos são só para demonstrar; não são vendas reais.

### O que explicar enquanto mostra

Em **“RA2.2 Eventos simulados”**, mostre a tabela dos seis eventos. Diga que o horário do evento é o que decide em qual minuto ele entra.

Em **“RA2.3 Janela e consulta”**, explique sem entrar em todo o código: para cada evento, o cálculo é **quantidade × preço**; depois o Spark soma os valores dentro de cada minuto. Pense na janela como uma caixinha para cada minuto: eventos das 10:00 vão numa caixa, os das 10:01 vão na próxima.

Nas três chegadas, mostre a tabela que aparece embaixo de cada célula:

1. **Chegada 1:** dois itens de 10 GBP e um item de 5 GBP dão **25 GBP** na janela das 10:00.
2. **Chegada 2:** entram mais 30 GBP na mesma janela, que passa a **55 GBP**. Um evento às 10:01 abre a próxima janela com **20 GBP**.
3. **Chegada 3:** a janela das 10:01 passa a **30 GBP** e a das 10:02 começa com **10 GBP**.

No final, os totais são **55, 30 e 10 GBP**. Somados, dão **95 GBP**.

### Se perguntarem sobre o RA2

- **O que significa streaming?** O Spark fica acompanhando arquivos novos e processa os registros quando eles chegam.
- **O horário do evento é quando o arquivo chega?** Não. O arquivo pode chegar depois; o horário dentro do evento é usado para escolher a janela.
- **O que acontece às 10:01 em ponto?** Ele entra na caixinha nova. A das 10:00 vai só até antes das 10:01.
- **Os 95 GBP são vendas reais?** Não. São a soma dos seis eventos inventados.
- **Tem Kafka ou banco permanente?** Não. É uma demonstração simples com arquivos e uma tabela temporária.

### Se tiver cinco minutos

Comece dizendo qual é a demonstração; mostre os eventos; explique a conta de quantidade vezes preço; passe pelas três chegadas; termine explicando que os dados são inventados e que 10:01 já conta no minuto seguinte.

Se as chegadas já aparecem na tela, mostre cada resultado uma vez. Não clique de novo numa célula “Chegada”: ela impede repetir a mesma chegada no mesmo fluxo. Se precisar rodar tudo outra vez, comece uma sessão nova e execute o notebook desde o começo.

## Para lembrar na hora

**RA1:** 541.909 no começo; 527.761 preparadas; 14.148 separadas. Uma linha é um item. Não calculamos lucro nem venda líquida.

**RA2:** seis eventos inventados; três chegadas; totais finais de 55, 30 e 10 GBP; 95 GBP é só a soma da demonstração.
