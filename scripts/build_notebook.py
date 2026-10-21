"""Monta o notebook autocontido; não fabrica nem preenche saídas de execução."""
from pathlib import Path
import json
import textwrap

ROOT = Path(__file__).resolve().parents[1]
cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {},
                  "source": textwrap.dedent(text).strip()})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                  "outputs": [], "source": textwrap.dedent(text).strip()})


md("""
# Preparação de dados e acompanhamento de vendas de uma loja online

**PUCPR · Data Analytics · RA1 e RA2**
**Equipe:** Gastão Eduardo e Gustavo Schott
**Curso:** Sistemas de Informação, 6º período
**Professora:** Marina de Lara
**Entrega:** 21/10/2026

Este projeto prepara uma base real de itens de transações de uma loja online
e demonstra uma análise simples com novos registros simulados.
O **RA1** documenta a origem, a qualidade e a preparação dos dados.
O **RA2** utiliza Apache Spark Structured Streaming para somar o valor de itens
por janelas fixas de um minuto, conforme chegam novos arquivos.

Os dados históricos reais e os eventos artificiais da demonstração ficam separados.
Os valores do RA2 não são resultados históricos da loja.

## Como executar

Execute as células de cima para baixo. Em Google Colab, faça upload deste `.ipynb`
e use **Ambiente de execução > Executar tudo**. A primeira execução precisa de
internet para instalar dependências e obter a base oficial (aproximadamente 23 MB).
No ambiente local, instale `requirements.txt` e tenha Java 17 disponível.
Cada execução do streaming usa uma pasta nova e não apaga execuções anteriores.

Para a apresentação, execute a preparação antecipadamente e mostre as três
chegadas de dados do RA2, uma célula de cada vez.
""")

md("""
## Ambiente

Um notebook reúne texto, código e saídas. Uma **célula de código** executa uma etapa;
uma **célula Markdown** explica o objetivo e a interpretação.
Pandas organiza os dados em tabelas; PySpark permite usar o motor Apache Spark.
As versões efetivamente utilizadas aparecem abaixo. Testado com Python 3.12,
Java 17, pandas 2.3.3 e PySpark 3.5.7.
""")
code("""
import os
import sys
import subprocess
import importlib.util
from pathlib import Path

try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "pandas==2.3.3", "openpyxl==3.1.5", "pyspark==3.5.7"], check=True
    )
    java17 = Path("/usr/lib/jvm/java-17-openjdk-amd64")
    if not java17.exists():
        subprocess.run(["apt-get", "update", "-qq"], check=True)
        subprocess.run(["apt-get", "install", "-y", "-qq",
                        "openjdk-17-jre-headless"], check=True)
    os.environ["JAVA_HOME"] = str(java17)
    os.environ["PATH"] = str(java17 / "bin") + os.pathsep + os.environ["PATH"]

import json
import hashlib
import platform
import urllib.request
import zipfile
import pandas as pd
import numpy as np
import pyspark
from datetime import datetime, timezone
from IPython.display import display

ROOT = Path.cwd()
for relative in ["data/raw", "data/processed", "evidence", "data/stream_runs"]:
    (ROOT / relative).mkdir(parents=True, exist_ok=True)

java_info = subprocess.run(["java", "-version"], capture_output=True, text=True, check=True)
java_version = next(line for line in java_info.stderr.splitlines() if "version" in line.lower())
print("Python:", platform.python_version())
print("pandas:", pd.__version__, "| PySpark:", pyspark.__version__)
print("Java:", java_version)
""")

md("""
# RA1 — Ingestão e preparação dos dados

## RA1.1 Problema, objetivo e perguntas

Uma loja online precisa de registros consistentes para acompanhar suas transações.
Dados ausentes, tipos inadequados e registros de frete, ajustes ou cancelamentos
podem mudar a interpretação de uma análise de mercadorias.

**Objetivo:** preparar registros positivos de mercadorias da base Online Retail,
documentando as verificações e decisões, para apoiar análises posteriores.
O recorte histórico abrange o período disponibilizado pela fonte, de dezembro de
2010 a dezembro de 2011, e todos os países presentes na base.

**Unidade de observação:** uma linha representa um item registrado em uma transação.
Um mesmo `InvoiceNo` pode conter vários itens; contar linhas não equivale a contar pedidos.

| ID | Pergunta que orienta o projeto | Dados necessários |
|---|---|---|
| P1 | Como o valor dos registros positivos de mercadorias varia por dia no período disponível? | InvoiceDate, Quantity, UnitPrice e regras do recorte |
| P2 | Quais produtos apresentam maior quantidade registrada nesse recorte? | StockCode, Description, Quantity |
| P3 | Na simulação, como o total dos itens por minuto se atualiza quando novos registros chegam? | Horário do evento, quantidade e preço dos eventos simulados |

P1 e P2 orientam a preparação para etapas posteriores; não são respondidas no RA1.
O RA2 demonstra P3. A base preparada **não representa vendas líquidas, lucro ou
receita contábil**: separar uma linha de cancelamento não desfaz a venda original.
Não há chave de linha de transação que permita afirmar que toda repetição é erro.
""")

md("""
## RA1.2 Fonte e ingestão

**Fonte:** Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository.
**DOI:** https://doi.org/10.24432/C5BW33
**Página:** https://archive.ics.uci.edu/dataset/352/online+retail
**Licença:** Creative Commons Attribution 4.0 (CC BY 4.0).
**Origem:** transações de uma loja online sediada no Reino Unido; vários clientes
são atacadistas. Preços em libras esterlinas (GBP).
**Arquivo:** Excel `Online Retail.xlsx`, planilha `Online Retail`, oito colunas.

A ingestão baixa o ZIP oficial apenas quando necessário, extrai somente o arquivo
esperado e lê a planilha com `openpyxl`. A comparação SHA-256 identifica a versão
dos dados. O código não executa fórmulas, macros ou instruções do conteúdo.
""")
code("""
SOURCE_URL = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
EXPECTED_ZIP_SHA256 = "f5385cbb54bbebf7196389109c6b0621faab0c304e3702548165e71c84aede8b"
archive_path = ROOT / "data/raw/online_retail_uci.zip"
source_path = ROOT / "data/raw/Online Retail.xlsx"

if not archive_path.exists():
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "AcademicDataProject/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != EXPECTED_ZIP_SHA256:
        raise ValueError("A versão da fonte mudou; revisar o arquivo antes de continuar.")
    archive_path.write_bytes(payload)

archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
assert archive_hash == EXPECTED_ZIP_SHA256, "ZIP diferente da versão verificada"
with zipfile.ZipFile(archive_path) as archive:
    source_bytes = archive.read("Online Retail.xlsx")
if not source_path.exists():
    source_path.write_bytes(source_bytes)
assert hashlib.sha256(source_path.read_bytes()).digest() == hashlib.sha256(source_bytes).digest()

raw = pd.read_excel(source_path, sheet_name="Online Retail", engine="openpyxl")
source_evidence = {
    "download_url": SOURCE_URL, "license": "CC BY 4.0",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "zip_sha256": archive_hash,
    "xlsx_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    "rows": len(raw), "columns": len(raw.columns),
}
(ROOT / "evidence/source_verified.json").write_text(
    json.dumps(source_evidence, indent=2, ensure_ascii=False), encoding="utf-8")
print("Registros carregados:", len(raw), "| Colunas:", len(raw.columns))
print("SHA-256 do XLSX:", source_evidence["xlsx_sha256"])
display(raw.head(3)[["InvoiceNo", "StockCode", "Quantity", "UnitPrice"]])
display(raw.head(3)[["InvoiceDate", "Description", "Country"]])
""")

md("""
## RA1.3 Compreensão e diagnóstico de qualidade

| Atributo | Significado | Tipo de uso | Unidade ou domínio |
|---|---|---|---|
| InvoiceNo | Identificador da transação; prefixo C indica cancelamento | Texto | Código categórico, pode se repetir entre itens |
| StockCode | Identificador do produto ou de outro lançamento | Texto | Código categórico |
| Description | Descrição do item | Texto | Nome ou descrição do lançamento |
| Quantity | Quantidade registrada naquela linha | Inteiro | Unidades; sinais precisam de interpretação |
| InvoiceDate | Data e hora do registro | Data e hora | Fonte não informa fuso horário |
| UnitPrice | Preço por unidade | Decimal numérico | GBP, libras esterlinas |
| CustomerID | Identificador do cliente | Texto anulável | Não é uma medida; pode estar ausente |
| Country | País do cliente | Texto | Categoria geográfica |

Os controles abaixo são verificações de qualidade, não análises de desempenho da loja.
Um registro pode apresentar mais de um sinal; **não somamos as contagens desta
tabela para calcular exclusões**. O balanço sem sobreposição aparece na preparação.
""")
code("""
description_text = raw.Description.astype("string")
quality = pd.DataFrame([
    ("Q1", "Description ausente", int(raw.Description.isna().sum())),
    ("Q2", "CustomerID ausente", int(raw.CustomerID.isna().sum())),
    ("Q3", "Repetições extras nas oito colunas", int(raw.duplicated().sum())),
    ("Q4", "InvoiceNo com prefixo C", int(raw.InvoiceNo.astype(str).str.upper().str.startswith("C").sum())),
    ("Q5", "Quantity menor ou igual a zero", int(raw.Quantity.le(0).sum())),
    ("Q6", "UnitPrice menor ou igual a zero", int(raw.UnitPrice.le(0).sum())),
    ("Q7", "Description com espaços nas pontas",
     int(description_text.ne(description_text.str.strip()).fillna(False).sum())),
    ("Q8", "InvoiceDate inválida", int(pd.to_datetime(raw.InvoiceDate, errors="coerce").isna().sum())),
], columns=["ID", "Verificação", "Quantidade"])
quality["Percentual da base"] = (quality.Quantidade / len(raw) * 100).round(2)
display(quality)
print("Denominador de todos os percentuais:", len(raw), "linhas brutas")
print("Período:", raw.InvoiceDate.min(), "até", raw.InvoiceDate.max())
display(pd.DataFrame({"Coluna": raw.columns, "Tipo observado": raw.dtypes.astype(str).values}))
display(raw[["Quantity", "UnitPrice"]].describe(percentiles=[0.5, 0.99]).T)
quality.to_csv(ROOT / "evidence/quality_checks.csv", index=False)
""")
md("""
**Interpretação do diagnóstico.** A identificação do cliente não é necessária para
agrupar itens por produto ou horário; seus valores ausentes podem ser mantidos.
Quantidade negativa pode representar cancelamento ou ajuste. Preço zero ou negativo
não entra no recorte de registros positivos, mas não é automaticamente um erro de digitação.

As repetições exatas são sinalizadas e mantidas: sem um identificador de linha fornecido
pela loja não podemos comprovar duplicidade acidental. Isso limita futuras somas,
que representam registros observados e podem incluir repetições.

Quantidades ou preços altos merecem revisão, mas a fonte inclui atacadistas;
não removemos extremos somente por distância da média ou de um percentil.
O código de identificação é texto, mesmo quando seus caracteres são números.
""")

md("""
## RA1.4 Limpeza e preparação

| Decisão | Ação e justificativa |
|---|---|
| D1 | Padronizar textos removendo espaços externos, tratar IDs como texto, datas como datetime e medidas como números. Não inventar valores. |
| D2 | Separar cancelamentos e registros sem quantidade/preço positivos. O objetivo é acompanhar registros positivos; não calcular vendas líquidas. |
| D3 | Separar códigos observados de frete, taxas, ajustes manuais, descontos, amostras e vouchers. Preservar códigos incomuns de mercadorias, como DCGSSBOY e PADS. |
| D4 | Preservar clientes ausentes, repetições exatas e extremos positivos, com suas limitações documentadas. |
| D5 | Adicionar SourceRow, que aponta para a linha original do Excel, e salvar cada exclusão com seu primeiro motivo aplicável. |

A lista de códigos fora do recorte foi definida a partir das descrições da própria
base: POST e DOT (postagem), C2 (transporte), BANK CHARGES e AMAZONFEE (taxas),
CRUK (comissão), D (desconto), B (ajuste), M/m (manual), S (amostras) e GIFT_ (vouchers).
Essa classificação é operacional e deve ser revista para uma fonte diferente.
Não rejeitamos um produto apenas porque seu código foge de um formato numérico.

A função abaixo contém integralmente as regras usadas pelo projeto.
""")
code((ROOT / "scripts/data_preparation.py").read_text(encoding="utf-8"))
code("""
prepared, excluded, preparation_summary = prepare_data(raw)
prepared.to_csv(ROOT / "data/processed/sales_prepared.csv", index=False)
excluded.to_csv(ROOT / "data/processed/excluded_records.csv", index=False)
(ROOT / "evidence/preparation_summary.json").write_text(
    json.dumps(preparation_summary, indent=2, ensure_ascii=False), encoding="utf-8")

reason_labels = {
    "cancellation": "Cancelamento identificado pelo prefixo C",
    "invalid_required_fields": "Campo essencial inválido",
    "non_positive_quantity": "Quantidade não positiva, após regras anteriores",
    "non_positive_price": "Preço não positivo, após regras anteriores",
    "non_merchandise_code": "Frete, taxas, ajustes, amostras ou voucher",
    "missing_description": "Descrição ausente após regras anteriores",
}
exclusion_table = pd.DataFrame([
    (reason_labels[key], int((excluded.ExclusionReason == key).sum()))
    for key in reason_labels
], columns=["Primeiro motivo aplicável", "Linhas separadas"])
display(exclusion_table)
print("Balanço:", len(raw), "=", len(prepared), "preparadas +", len(excluded), "separadas")
display(excluded[["SourceRow", "InvoiceNo", "StockCode", "ExclusionReason"]].head(6))
""")

md("""
## RA1.5 Conjunto resultante e validação

**Saída principal:** `data/processed/sales_prepared.csv`. Mantém as oito variáveis
da fonte e acrescenta `SourceRow`. Uma linha continua sendo um item registrado,
agora dentro do recorte positivo de mercadorias.

**Saída de rastreabilidade:** `data/processed/excluded_records.csv`, com as linhas
fora do recorte e `ExclusionReason`. Os dados brutos permanecem intactos.

Os testes a seguir comprovam consistência e o balanço das linhas. Também reabrimos
o CSV para verificar que o arquivo efetivamente salvo pode ser utilizado depois.
CSV não armazena um esquema de tipos: por isso a releitura define os tipos dos IDs.
""")
code("""
essential = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "Country"]
assert prepared[essential].notna().all().all()
assert prepared.Quantity.gt(0).all() and prepared.Quantity.mod(1).eq(0).all()
assert prepared.UnitPrice.gt(0).all()
assert not prepared.InvoiceNo.str.upper().str.startswith("C").any()
assert prepared.SourceRow.is_unique
assert len(prepared) + len(excluded) == len(raw)
assert not set(prepared.SourceRow).intersection(excluded.SourceRow)

loaded = pd.read_csv(ROOT / "data/processed/sales_prepared.csv",
    dtype={"InvoiceNo": "string", "StockCode": "string", "CustomerID": "string",
           "Quantity": "Int64", "SourceRow": "int64"}, parse_dates=["InvoiceDate"])
assert len(loaded) == len(prepared)
assert loaded.SourceRow.tolist() == prepared.SourceRow.tolist()
assert loaded.CustomerID.isna().sum() == prepared.CustomerID.isna().sum()

comparison = pd.DataFrame([
    ("Linhas", len(raw), len(prepared)),
    ("Colunas", raw.shape[1], prepared.shape[1]),
    ("Descrições ausentes", int(raw.Description.isna().sum()), int(prepared.Description.isna().sum())),
    ("Clientes ausentes", int(raw.CustomerID.isna().sum()), int(prepared.CustomerID.isna().sum())),
    ("Repetições extras nos 8 atributos", int(raw.duplicated().sum()),
     int(prepared[COLUMNS].duplicated().sum())),
], columns=["Medida", "Após ingestão", "Após preparação"])
display(comparison)
print("Todas as verificações de consistência e releitura passaram.")
comparison.to_csv(ROOT / "evidence/before_after.csv", index=False)
""")
md("""
**Limitações remanescentes:** clientes ausentes não foram recuperados; repetições e
extremos permanecem identificados, sem confirmação externa de sua natureza.
Cancelamentos não foram reconciliados com vendas originais. O significado de códigos
especiais foi inferido das descrições observadas, sem um catálogo oficial complementar.
O horário histórico não recebeu fuso inventado. A amostra é de uma loja e de um período
histórico específico; não representa todo o comércio online nem o mercado atual.

## RA1.6 Organização e reprodução

O notebook contém todo o código necessário. Os scripts e testes do repositório
permitem reconstruir e verificar o material; as explicações e saídas também estão
neste arquivo. Para repetir: preparar ambiente, executar as células em ordem,
conferir as mensagens de validação e localizar as saídas em `data/processed` e `evidence`.

O arquivo `evidence/execution_record.json`, gerado ao final, registra o ambiente e
o horário da execução. A publicação do repositório e seu endereço devem ser
confirmados pela equipe antes de enviar a atividade no Canvas.

## RA1.7 Referências

- Chen, D. (2015). Online Retail. UCI Machine Learning Repository. DOI: 10.24432/C5BW33. CC BY 4.0.
- pandas. Documentação de leitura Excel e manipulação de dados: https://pandas.pydata.org/docs/
- Apache Spark. Structured Streaming Programming Guide 3.5.7: https://spark.apache.org/docs/3.5.7/structured-streaming-programming-guide.html
- Enunciados RA1 e RA2 e modelo de documentação disponibilizados na disciplina Data Analytics, PUCPR, 2026.

Fontes públicas consultadas em 15/10/2026. Os resultados de qualidade acima foram
medidos no arquivo, em vez de presumidos a partir da descrição do catálogo.
""")

md("""
# RA2 — Processamento em streaming

## RA2.1 Objetivo e relação com o RA1

**Pergunta:** como o valor total de itens por minuto se atualiza quando novos registros chegam?
Usamos o cenário A do enunciado: a fonte histórica é estática e a chegada de novos
registros é simulada. Dois produtos do conjunto preparado dão contexto aos eventos.
Quantidade, preço e horários da demonstração são artificiais e explicitamente identificados.

**Análise única:** soma de `Quantity × UnitPrice` em GBP por janela tumbling de um minuto.
A contagem de eventos é uma evidência auxiliar de processamento.

Em processamento de lote (batch), lemos um conjunto finito de uma vez.
No streaming, o Spark acompanha uma pasta e processa novos arquivos à medida que chegam.
Esta implementação usa micro-lotes: pequenos lotes incrementais, sem reler a base histórica.
""")
md("""
## RA2.2 Fonte dos eventos e resultados esperados

Os seis eventos serão publicados em três arquivos, em momentos distintos.
O campo `event_time` representa quando a venda fictícia ocorreu; o instante de publicação
representa quando o sistema a recebeu. Os dois conceitos não precisam coincidir.
Somente para a simulação, adotamos UTC, sem alterar o horário histórico da fonte.

| Chegada | Evento | Horário do evento | Quantidade | Preço GBP | Valor GBP |
|---|---|---|---:|---:|---:|
| 1 | SIM001 | 10:00:05 | 2 | 10,00 | 20,00 |
| 1 | SIM002 | 10:00:30 | 1 | 5,00 | 5,00 |
| 2 | SIM003 | 10:00:45 | 3 | 10,00 | 30,00 |
| 2 | SIM004 | 10:01:00 | 4 | 5,00 | 20,00 |
| 3 | SIM005 | 10:01:20 | 1 | 10,00 | 10,00 |
| 3 | SIM006 | 10:02:05 | 2 | 5,00 | 10,00 |

**Antes de executar**, o resultado esperado é: chegada 1 = 25,00 na primeira janela;
chegada 2 = 55,00 na primeira e 20,00 na segunda; chegada 3 = 55,00, 30,00 e 10,00.
Esses valores, calculados manualmente, serão comparados com a saída real do Spark.
""")
code("""
import uuid
from decimal import Decimal
from pyspark.sql import SparkSession, functions as F, types as T

os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
os.environ["PYSPARK_PYTHON"] = sys.executable
spark = (SparkSession.builder.master("local[2]")
    .appName("RA2OnlineRetail")
    .config("spark.ui.enabled", "false")
    .config("spark.sql.shuffle.partitions", "2")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

run_id = uuid.uuid4().hex
run_dir = ROOT / "data/stream_runs" / run_id
input_dir = run_dir / "input"
staging_dir = run_dir / "staging"
input_dir.mkdir(parents=True)
staging_dir.mkdir()
query_name = "sales_" + run_id

catalog = loaded[["StockCode", "Description"]].drop_duplicates("StockCode").head(2)
products = catalog.to_dict("records")
event_specs = [
    ("SIM001", "10:00:05", 2, 10.00, 0),
    ("SIM002", "10:00:30", 1, 5.00, 1),
    ("SIM003", "10:00:45", 3, 10.00, 0),
    ("SIM004", "10:01:00", 4, 5.00, 1),
    ("SIM005", "10:01:20", 1, 10.00, 0),
    ("SIM006", "10:02:05", 2, 5.00, 1),
]
events = [
    {"event_id": event_id, "event_time": "2026-10-15T" + clock + "Z",
     "StockCode": products[product]["StockCode"],
     "Description": products[product]["Description"],
     "Quantity": quantity, "UnitPrice": price, "synthetic": True}
    for event_id, clock, quantity, price, product in event_specs
]
assert len({event["event_id"] for event in events}) == 6
assert all(event["StockCode"] in set(catalog.StockCode) for event in events)
display(pd.DataFrame(events)[["event_id", "event_time", "StockCode", "Quantity", "UnitPrice"]])
print("Eventos artificiais; códigos e descrições vêm do conjunto preparado no RA1.")
""")
md("""
## RA2.3 Janela temporal e consulta contínua

Uma janela **tumbling** tem duração fixa e não se sobrepõe à próxima.
Aqui, duração e deslocamento são de um minuto: [10:00, 10:01), [10:01, 10:02) etc.
O colchete inclui o início; o parêntese exclui o fim. Assim, o evento exatamente
às 10:01:00 pertence à segunda janela.

`readStream` acompanha os arquivos novos. `window` agrupa pelo horário do evento.
`sum` calcula o total. `writeStream` mantém a consulta ativa.
O preço usa `DecimalType` para evitar erro de representação binária no cálculo monetário.

O destino em memória e o modo `complete` mostram toda a tabela de resultados a cada
atualização. São adequados à pequena demonstração. Não implementamos política de
atrasos/watermark nem retenção limitada de estado; um fluxo de produção exigiria
essas decisões e um destino persistente. O checkpoint local acompanha esta execução,
mas não torna a tabela em memória um armazenamento durável.
""")
code("""
schema = T.StructType([
    T.StructField("event_id", T.StringType(), False),
    T.StructField("event_time", T.TimestampType(), False),
    T.StructField("StockCode", T.StringType(), False),
    T.StructField("Description", T.StringType(), False),
    T.StructField("Quantity", T.IntegerType(), False),
    T.StructField("UnitPrice", T.DecimalType(12, 2), False),
    T.StructField("synthetic", T.BooleanType(), False),
])
incoming = (spark.readStream.schema(schema).option("mode", "FAILFAST")
            .option("maxFilesPerTrigger", 1).json(str(input_dir)))
assert incoming.isStreaming
window_totals = (incoming
    .withColumn("item_value", F.col("Quantity") * F.col("UnitPrice"))
    .groupBy(F.window("event_time", "1 minute"))
    .agg(F.sum("item_value").alias("total_gbp"), F.count("event_id").alias("events")))
query = (window_totals.writeStream.format("memory").queryName(query_name)
    .outputMode("complete")
    .option("checkpointLocation", str(run_dir / "checkpoint"))
    .trigger(processingTime="1 second").start())
print("Consulta ativa:", query.isActive, "| DataFrame streaming:", incoming.isStreaming)
snapshots = []
""")
code("""
def publish_batch(number, batch_events, expected):
    # Grava fora da pasta observada e move o arquivo completo de uma vez.
    staged = staging_dir / f"batch_{number}.json"
    target = input_dir / staged.name
    if target.exists():
        raise ValueError("Esta chegada já foi publicada; reinicie o RA2 para repetir.")
    payload = "\\n".join(json.dumps(event, ensure_ascii=False) for event in batch_events) + "\\n"
    staged.write_text(payload, encoding="utf-8")
    staged.rename(target)
    arrived_at = datetime.now(timezone.utc).isoformat()
    query.processAllAvailable()
    if query.exception() is not None:
        raise RuntimeError(str(query.exception()))

    rows = (spark.table(query_name).orderBy("window.start")
            .select(F.date_format("window.start", "HH:mm:ss").alias("start"),
                    F.date_format("window.end", "HH:mm:ss").alias("end"),
                    "total_gbp", "events").collect())
    observed = {row["start"]: (str(row["total_gbp"]), row["events"]) for row in rows}
    assert observed == expected, f"Resultado diferente do esperado: {observed}"
    data_progress = [p for p in query.recentProgress if p["numInputRows"] > 0]
    progress = data_progress[-1]
    assert progress["numInputRows"] == len(batch_events)
    snapshot = {"arrival": number, "arrived_at_utc": arrived_at,
                "spark_batch_id": progress["batchId"],
                "new_rows": progress["numInputRows"], "windows": observed}
    snapshots.append(snapshot)
    print(f"Chegada {number}: {len(batch_events)} novos registros | batchId={progress['batchId']}")
    print("Recebidos em UTC:", arrived_at)
    display(pd.DataFrame([row.asDict() for row in rows]).rename(columns={
        "start": "Início", "end": "Fim exclusivo", "total_gbp": "Total GBP", "events": "Eventos"}))
    print("Resultado conferido com a conta manual.")
""")
md("""
## RA2.4 Três chegadas e evidências de atualização

**Chegada 1:** dois eventos na primeira janela. Esperado: 2 × 10 + 1 × 5 = 25 GBP.
""")
code('publish_batch(1, events[:2], {"10:00:00": ("25.00", 2)})')
md("""
**Chegada 2:** um evento acrescenta 30 GBP à primeira janela; outro abre a segunda
com 20 GBP. O evento às 10:01:00 comprova a regra da fronteira entre janelas.
""")
code('publish_batch(2, events[2:4], {"10:00:00": ("55.00", 3), "10:01:00": ("20.00", 1)})')
md("""
**Chegada 3:** a segunda janela recebe mais 10 GBP e a terceira recebe 10 GBP.
O resultado final esperado é 55, 30 e 10 GBP, com seis eventos ao todo.
""")
code('publish_batch(3, events[4:], {"10:00:00": ("55.00", 3), "10:01:00": ("30.00", 2), "10:02:00": ("10.00", 1)})')
code("""
assert sum(snapshot["new_rows"] for snapshot in snapshots) == 6
assert len({snapshot["spark_batch_id"] for snapshot in snapshots}) == 3
assert sum(Decimal(value[0]) for value in snapshots[-1]["windows"].values()) == Decimal("95.00")
(ROOT / "evidence/streaming_snapshots.json").write_text(
    json.dumps(snapshots, ensure_ascii=False, indent=2), encoding="utf-8")
print("Validação final: 3 chegadas distintas, 6 eventos, 3 janelas e total de 95.00 GBP.")
query.stop()
print("Consulta encerrada:", not query.isActive)
spark.stop()
""")
md("""
## RA2.5 Interpretação e limites

A primeira janela passou de 25 para 55 GBP após a chegada 2; a segunda passou de 20
para 30 GBP após a chegada 3. Isso demonstra a atualização de uma agregação com novos
registros, além da abertura de uma nova janela. Cada chegada foi confirmada por
`numInputRows = 2` em um `batchId` diferente do Spark.

O evento na fronteira 10:01:00 foi atribuído à janela que começa às 10:01.
A soma final de 95 GBP coincide com o cálculo manual dos seis eventos.
São resultados da simulação, não conclusões sobre as vendas históricas da loja.

Usamos uma única análise e um único tipo de janela, conforme o escopo do RA2.
O fluxo é pequeno e controlado: eventos válidos, uma publicação por arquivo,
sem reenvios duplicados, sem interrupção durante a demonstração.
Não foram avaliados throughput, escalabilidade ou recuperação de falhas de produção.

## RA2.6 Reprodução e demonstração

Para repetir a demonstração, execute novamente a partir da criação do Spark e das
pastas de execução (RA2.2), depois RA2.3 e as três chegadas em RA2.4.
Se interromper a execução no meio, encerre a consulta com `query.stop()` antes de recomeçar.
A pasta nova evita misturar resultados e checkpoints de execuções diferentes.

O PDF desta entrega foi convertido deste notebook executado e inclui código e saídas.
Na apresentação, use o notebook: o PDF registra evidências, mas não executa código.
""")
code("""
execution_record = {
    "executed_at_utc": datetime.now(timezone.utc).isoformat(),
    "execution_type": "registro gerado ao alcançar a última célula do notebook",
    "python": platform.python_version(), "pandas": pd.__version__,
    "pyspark": pyspark.__version__, "java": java_version,
    "source_sha256": source_evidence["xlsx_sha256"],
    "prepared_rows": len(prepared), "excluded_rows": len(excluded),
    "ra1_checks_passed": True, "ra2_checked_arrivals": len(snapshots),
    "ra2_checked_events": sum(item["new_rows"] for item in snapshots),
    "synthetic_total_gbp": "95.00",
}
(ROOT / "evidence/execution_record.json").write_text(
    json.dumps(execution_record, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(execution_record, ensure_ascii=False, indent=2))
""")

compact_markdown = [
    """
# RA1 e RA2 — Online Retail

**Gastão Eduardo e Gustavo Schott · Sistemas de Informação, 6º período · Professora Marina de Lara**

No **RA1**, preparamos o histórico da loja. No **RA2**, mostramos seis eventos fictícios chegando em três momentos.

### No Google Colab
1. Envie este arquivo `.ipynb`.
2. Selecione **Ambiente de execução > Executar tudo**.
3. Aguarde todas as células terminarem. A primeira execução instala as dependências e baixa a base.
""",
    """
## Ambiente

Pandas organiza os dados em tabelas. Apache Spark processa os arquivos que chegam no RA2. As versões usadas e os resultados aparecem nas células.
""",
    """
# RA1 — Ingestão e preparação

## Problema e objetivo

Uma loja precisa de registros organizados para analisar suas transações. O objetivo aqui é conferir a base Online Retail e preparar registros positivos de mercadorias, de todos os países e durante o período disponível.

**Perguntas para análises futuras:**
1. Como o valor dos registros positivos varia por dia?
2. Quais produtos têm maior quantidade registrada?
3. No RA2, como os valores por minuto mudam quando chegam novos eventos?

No RA1, preparamos os dados; não respondemos às duas primeiras perguntas nem calculamos lucro ou vendas líquidas. Uma linha é um item da transação, não necessariamente um pedido inteiro.
""",
    """
## RA1.2 Fonte e ingestão

**Fonte:** Chen (2015), *Online Retail*, UCI Machine Learning Repository. [Página da base](https://archive.ics.uci.edu/dataset/352/online+retail) · DOI 10.24432/C5BW33 · Licença CC BY 4.0.

A base contém transações de uma loja do Reino Unido, de 2010 a 2011, com preços em GBP. O arquivo é um Excel com oito colunas. O código baixa o ZIP oficial, confere seu hash e lê a planilha `Online Retail`.
""",
    """
## RA1.3 Qualidade dos dados

As oito colunas são: `InvoiceNo` (transação), `StockCode` e `Description` (item), `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID` e `Country`.

Uma fatura pode aparecer em várias linhas. As contagens de qualidade podem se sobrepor; não devem ser somadas para calcular exclusões. O balanço sem sobreposição aparece na próxima etapa.
""",
    """
Clientes sem ID foram mantidos: ainda é possível usar o item e o horário. Linhas idênticas foram sinalizadas e mantidas porque a fonte não fornece uma chave única de linha. Quantidades e preços positivos extremos também foram mantidos; a loja atende atacadistas. Cancelamentos e valores não positivos precisam ser interpretados, não tratados automaticamente como erro.
""",
    """
## RA1.4 Preparação

- Textos padronizados; datas e números convertidos; identificadores tratados como texto.
- Campos essenciais inválidos, cancelamentos, quantidades ou preços não positivos e códigos de frete, taxas, ajustes ou vouchers ficam separados.
- Clientes ausentes, repetições, extremos positivos e códigos raros de produtos são preservados.
- Cada linha mantém sua origem no Excel (`SourceRow`) e, se separada, recebe o primeiro motivo aplicável.

A função abaixo contém as regras usadas na preparação.
""",
    """
## RA1.5 Resultado e validação

O arquivo preparado contém **527.761 linhas**; **14.148** ficaram separadas com justificativa. O balanço é `541.909 = 527.761 + 14.148`.

`sales_prepared.csv` contém os registros do recorte. `excluded_records.csv` mantém as linhas separadas e seus motivos. As verificações confirmam campos essenciais, quantidades e preços positivos, origem única e balanço completo.
""",
    """
### Limites e reprodução

A base cobre uma loja e um período histórico específico. Não representa todo o comércio online. O recorte não é receita líquida nem lucro: não ligamos cada cancelamento à venda correspondente.

O notebook contém o processo de ingestão e preparação. A documentação de entrega acompanha o template da disciplina. Fonte: Chen (2015), *Online Retail*, UCI Machine Learning Repository, DOI 10.24432/C5BW33, CC BY 4.0.
""",
    """
# RA2 — Spark Structured Streaming

## Objetivo

Pergunta: como a soma do valor dos itens por minuto muda conforme chegam novos eventos? Usamos o cenário do enunciado com uma fonte estática e chegadas simuladas.

A única análise é `Quantity × UnitPrice` por janela de um minuto. Os eventos são fictícios; os códigos e nomes de dois produtos vêm do conjunto preparado no RA1.
""",
    """
## RA2.2 Eventos simulados

São seis eventos fictícios em três arquivos, dois por chegada. Horários, quantidades e preços foram criados para a demonstração. A hora no evento (`event_time`) determina a janela; a hora em que o arquivo chega ao Spark pode ser diferente.

Resultados esperados: chegada 1 → **25 GBP**; chegada 2 → **55 e 20 GBP**; chegada 3 → **55, 30 e 10 GBP**. Soma final: **95 GBP**.
""",
    """
## RA2.3 Janela e consulta

A janela **tumbling** dura um minuto e não se sobrepõe à seguinte. O início entra e o fim não: `[10:00, 10:01)`. Por isso, o evento das 10:01:00 pertence à janela que começa às 10:01.

`readStream` acompanha novos arquivos, `window` agrupa pelo horário do evento e `sum` soma os valores. `writeStream` atualiza a tabela da demonstração em memória. Ela não é armazenamento permanente de produção.

Referência: [guia oficial do Spark Structured Streaming 3.5.7](https://spark.apache.org/docs/3.5.7/structured-streaming-programming-guide.html).
""",
    "## Chegada 1: `20 + 5 = 25 GBP` na janela 10:00.",
    "## Chegada 2: a janela 10:00 passa a 55 GBP; às 10:01 começa outra com 20 GBP.",
    "## Chegada 3: a janela 10:01 passa a 30 GBP e a janela 10:02 começa com 10 GBP.",
    """
## RA2.5 Resultado e limites

As três chegadas processaram dois eventos cada. Os totais observados conferem com a conta manual. São resultados da simulação, não conclusões sobre as vendas históricas.

A demonstração usa uma janela e uma agregação. Não implementa Kafka, armazenamento durável, watermark ou tratamento de falhas de produção.
""",
]
markdown_cells = [cell for cell in cells if cell["cell_type"] == "markdown"]
if len(markdown_cells) != len(compact_markdown):
    raise RuntimeError("A lista de explicações deve corresponder às células Markdown do notebook.")
for cell, source in zip(markdown_cells, compact_markdown):
    cell["source"] = textwrap.dedent(source).strip()

for i, cell in enumerate(cells):
    cell["id"] = f"cell-{i:03d}"
notebook = {"cells": cells, "metadata": {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12"},
    "colab": {"provenance": []},
}, "nbformat": 4, "nbformat_minor": 5}
path = ROOT / "projeto_data_analytics.ipynb"
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook gerado sem saídas: {len(cells)} células, {sum(c['cell_type']=='code' for c in cells)} de código")
