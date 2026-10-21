# Cola para a apresentação — RA1 e RA2

Leiam uma vez juntos e expliquem com as próprias palavras. Não precisam decorar o texto.

## RA1 — apresentação em dupla

**O que fizemos:** usamos a base Online Retail, da UCI, com registros de itens vendidos por uma loja entre 2010 e 2011. Cada linha é um item, não um pedido completo.

**O que fizemos com os dados:** conferimos as colunas e os problemas; preparamos os registros de mercadorias com quantidade e preço positivos; separamos cancelamentos, valores não positivos e linhas de frete, taxas e ajustes. Mantivemos clientes sem ID, repetições e valores positivos extremos, com justificativa.

**Resultado:** de 541.909 linhas, 527.761 ficaram no recorte e 14.148 foram separadas. A conta fecha: 527.761 + 14.148 = 541.909. As separadas continuam guardadas com o motivo.

**Limite:** esse recorte não representa vendas líquidas nem lucro. Não relacionamos cada cancelamento à venda original.

**Divisão simples:** Gastão explica a base e o objetivo; Gustavo explica as decisões de preparação e os resultados. Ambos devem saber explicar a conta e o limite.

## RA2 — conversa individual com a professora

**O que fiz:** usei Spark Structured Streaming para acompanhar arquivos que chegam em três etapas. Os seis eventos são inventados para demonstrar o fluxo; não são vendas reais da base.

**Como calcula:** para cada evento, `quantidade × preço`; depois o Spark soma os valores em janelas de um minuto, usando o horário do evento.

**O que aparece:** após a primeira chegada, a janela das 10:00 soma 25 GBP. Após a segunda, ela soma 55 GBP e a janela das 10:01 começa com 20 GBP. No fim, os totais são 55, 30 e 10 GBP. A soma final é 95 GBP.

**Detalhe da janela:** o início conta e o fim não. Então 10:01:00 já pertence à janela `[10:01, 10:02)`, não à das 10:00.

**Limite:** é uma demonstração local com arquivos e dados fictícios. Não usamos Kafka nem armazenamento permanente.

## Se a professora perguntar

- **Por que manter cliente sem ID?** Porque ainda temos o item, a quantidade, o preço e a data; só não dá para identificar o cliente.
- **Por que manter repetição?** A base não oferece uma chave única da linha para provar que seja erro; excluir poderia apagar itens legítimos.
- **Por que separar cancelamentos?** Para não misturá-los com o recorte positivo. Eles continuam registrados e podem ser estudados à parte.
- **O que muda entre RA1 e RA2?** O RA1 prepara o histórico. O RA2 demonstra eventos chegando e sendo agregados por tempo.
- **Esses 95 GBP são vendas da loja?** Não. São a soma dos seis eventos fictícios da demonstração.

## Ordem para mostrar

No RA1: objetivo e fonte → decisões de preparação → balanço das linhas → limite do recorte.

No RA2: eventos fictícios → janela de um minuto → três chegadas e totais → limite da demonstração.
