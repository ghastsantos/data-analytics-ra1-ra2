"""Monta o notebook a partir das células e dos módulos de análise."""
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
# RA1, RA2 e RA3 — Online Retail

**Gastão Eduardo e Gustavo Schott · Sistemas de Informação, 6º período · Professora Marina de Lara**

No **RA1**, preparamos a base Online Retail. No **RA2**, demonstramos o processamento de seis eventos fictícios no Spark. No **RA3**, voltamos à base histórica para analisar os registros da loja e testar uma previsão de um dia à frente.

### No Google Colab
1. Envie este arquivo `.ipynb`.
2. Selecione **Ambiente de execução > Executar tudo**.

A primeira execução instala as dependências e baixa a base da UCI. Para rodar localmente, instale `requirements.txt`, use Java 17 e inicie o notebook na raiz do repositório.
""")

md("""
## Ambiente

Usamos pandas para preparar os dados, Spark para o streaming, Matplotlib para os gráficos e scikit-learn para a regressão.
""")
code("""
import os
import sys
import subprocess
from pathlib import Path

try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "pandas==2.3.3", "openpyxl==3.1.5", "pyspark==3.5.7",
         "matplotlib>=3.8,<4", "scikit-learn>=1.4,<2"], check=True
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
import matplotlib.pyplot as plt
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
# RA1 — Ingestão e preparação

## Problema e objetivo

Uma loja precisa de registros organizados para analisar suas transações. O objetivo aqui é conferir a base Online Retail e preparar registros positivos de mercadorias, de todos os países e durante o período disponível.

**Perguntas para análises futuras:**
1. Como o valor dos registros positivos varia por dia?
2. Quais produtos têm maior quantidade registrada?
3. No RA2, como os valores por minuto mudam quando chegam novos eventos?

No RA1, preparamos os dados; não respondemos às duas primeiras perguntas nem calculamos lucro ou vendas líquidas. Uma linha é um item da transação, não necessariamente um pedido inteiro.
""")

md("""
## RA1.2 Fonte e ingestão

**Fonte:** Chen (2015), *Online Retail*, UCI Machine Learning Repository. [Página da base](https://archive.ics.uci.edu/dataset/352/online+retail) · DOI 10.24432/C5BW33 · Licença CC BY 4.0.

A base contém transações de uma loja do Reino Unido, de 2010 a 2011, com preços em GBP. O arquivo é um Excel com oito colunas. O código baixa o ZIP oficial, confere seu hash e lê a planilha `Online Retail`.
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
## RA1.3 Qualidade dos dados

As oito colunas são: `InvoiceNo` (transação), `StockCode` e `Description` (item), `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID` e `Country`.

Uma fatura pode aparecer em várias linhas. As contagens de qualidade podem se sobrepor; não devem ser somadas para calcular exclusões. O balanço sem sobreposição aparece na próxima etapa.
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
Clientes sem ID foram mantidos: ainda é possível usar o item e o horário. Linhas idênticas foram sinalizadas e mantidas porque a fonte não fornece uma chave única de linha. Quantidades e preços positivos extremos também foram mantidos; a loja atende atacadistas. Cancelamentos e valores não positivos precisam ser interpretados, não tratados automaticamente como erro.
""")

md("""
## RA1.4 Preparação

- Textos padronizados; datas e números convertidos; identificadores tratados como texto.
- Campos essenciais inválidos, cancelamentos, quantidades ou preços não positivos e códigos de frete, taxas, ajustes ou vouchers ficam separados.
- Clientes ausentes, repetições, extremos positivos e códigos raros de produtos são preservados.
- Cada linha mantém sua origem no Excel (`SourceRow`) e, se separada, recebe o primeiro motivo aplicável.

A função abaixo contém as regras usadas na preparação.
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
## RA1.5 Resultado e validação

O arquivo preparado contém **527.761 linhas**; **14.148** ficaram separadas com justificativa. O balanço é `541.909 = 527.761 + 14.148`.

`sales_prepared.csv` contém os registros do recorte. `excluded_records.csv` mantém as linhas separadas e seus motivos. As verificações confirmam campos essenciais, quantidades e preços positivos, origem única e balanço completo.
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
### Limites e reprodução

A base cobre uma loja e um período histórico específico. Não representa todo o comércio online. O recorte não é receita líquida nem lucro: não ligamos cada cancelamento à venda correspondente.

O notebook contém o processo de ingestão e preparação. A documentação de entrega acompanha o template da disciplina. Fonte: Chen (2015), *Online Retail*, UCI Machine Learning Repository, DOI 10.24432/C5BW33, CC BY 4.0.
""")

md("""
# RA2 — Spark Structured Streaming

## Objetivo

Pergunta: como a soma do valor dos itens por minuto muda conforme chegam novos eventos? Usamos o cenário do enunciado com uma fonte estática e chegadas simuladas.

A única análise é `Quantity × UnitPrice` por janela de um minuto. Os eventos são fictícios; os códigos e nomes de dois produtos vêm do conjunto preparado no RA1.
""")
md("""
## RA2.2 Eventos simulados

São seis eventos fictícios em três arquivos, dois por chegada. Horários, quantidades e preços foram criados para a demonstração. A hora no evento (`event_time`) determina a janela; a hora em que o arquivo chega ao Spark pode ser diferente.

Resultados esperados: chegada 1 → **25 GBP**; chegada 2 → **55 e 20 GBP**; chegada 3 → **55, 30 e 10 GBP**. Soma final: **95 GBP**.
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
## RA2.3 Janela e consulta

A janela **tumbling** dura um minuto e não se sobrepõe à seguinte. O início entra e o fim não: `[10:00, 10:01)`. Por isso, o evento das 10:01:00 pertence à janela que começa às 10:01.

`readStream` acompanha novos arquivos, `window` agrupa pelo horário do evento e `sum` soma os valores. `writeStream` atualiza a tabela da demonstração em memória. Ela não é armazenamento permanente de produção.

Referência: [guia oficial do Spark Structured Streaming 3.5.7](https://spark.apache.org/docs/3.5.7/structured-streaming-programming-guide.html).
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
## Chegada 1: `20 + 5 = 25 GBP` na janela 10:00.
""")
code('publish_batch(1, events[:2], {"10:00:00": ("25.00", 2)})')
md("""
## Chegada 2: a janela 10:00 passa a 55 GBP; às 10:01 começa outra com 20 GBP.
""")
code('publish_batch(2, events[2:4], {"10:00:00": ("55.00", 3), "10:01:00": ("20.00", 1)})')
md("""
## Chegada 3: a janela 10:01 passa a 30 GBP e a janela 10:02 começa com 10 GBP.
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
## RA2.5 Resultado e limites

As três chegadas processaram dois eventos cada. Os totais observados conferem com a conta manual. São resultados da simulação, não conclusões sobre as vendas históricas.

A demonstração usa uma janela e uma agregação. Não implementa Kafka, armazenamento durável, watermark ou tratamento de falhas de produção.
""")
md("""
# RA3 — Análise, visualização e regressão

## RA3.1 Valor por linha

Multiplicamos `Quantity × UnitPrice` em cada linha do recorte do RA1. Como os cancelamentos foram separados sem conciliação com as compras originais, a soma mede o valor bruto dos itens positivos registrados.

A mediana por linha foi de 9,90 GBP, enquanto a média chegou a 19,46 GBP. A diferença aparece no histograma, que mostra poucas linhas com valores muito acima da mediana.
""")
code((ROOT / "scripts/ra3_analysis.py").read_text(encoding="utf-8"))
code("""
# Mostra as estatísticas por linha e guarda os valores usados nos gráficos.
display(descriptive_statistics(loaded))
valued_items = add_item_value(loaded)
line_values = valued_items["ItemValueGBP"]
""")

md("""
## RA3.2 Evolução diária

Em 69 dos 374 dias, o recorte não tem itens positivos registrados. Preenchemos esses dias com zero para manter o calendário contínuo. A média móvel de sete dias suaviza as oscilações, e a linha dos totais diários mostra onde ocorreram os picos.
""")
code("""
# Resume os totais diários e conta os dias sem registros.
ra3_daily = build_daily_dataset(loaded)
daily_distribution = ra3_daily["DailyValueGBP"].describe(
    percentiles=[.50, .90, .99]
).rename({"50%": "Mediana", "90%": "P90", "99%": "P99"}).to_frame("Valor diário (GBP)")
display(daily_distribution.round(2))
print(f"Dias sem itens positivos: {int(ra3_daily['ItemLines'].eq(0).sum())} de {len(ra3_daily)}")
# Compara os totais diários com a média móvel de sete dias.
ra3_rolling = ra3_daily["DailyValueGBP"].rolling(7, min_periods=7).mean()
fig, ax = plt.subplots(figsize=(12, 4.5))
ax.plot(ra3_daily.index, ra3_daily["DailyValueGBP"], color="#4C78A8", alpha=.55,
        linewidth=1, label="Valor diário")
ax.plot(ra3_daily.index, ra3_rolling, color="#E45756", linewidth=2,
        label="Média móvel de 7 dias")
ax.set(title="Valor bruto diário dos itens positivos — Online Retail",
       xlabel="Data", ylabel="Valor dos itens (GBP)")
ax.legend(frameon=False)
ax.grid(axis="y", alpha=.2)
fig.tight_layout()
plt.show()
""")

md("""
## RA3.3 Distribuição do valor por linha

Em 90% das linhas, o valor ficou em até 31,60 GBP. O eixo horizontal usa escala logarítmica para mostrar no mesmo gráfico as linhas de menor valor e os extremos positivos mantidos no RA1.
""")
code("""
# Mostra a distribuição dos valores por linha em escala logarítmica.
bins = np.geomspace(line_values.min(), line_values.max(), 45)
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.hist(line_values, bins=bins, color="#72B7B2", edgecolor="white")
ax.set_xscale("log")
ax.axvline(line_values.median(), color="#F58518", linestyle="--", linewidth=2,
           label=f"Mediana: GBP {line_values.median():.2f}")
ax.axvline(line_values.quantile(.90), color="#B279A2", linestyle=":", linewidth=2,
           label=f"P90: GBP {line_values.quantile(.90):.2f}")
ax.set(title="Distribuição do valor bruto por linha de item",
       xlabel="Quantity × UnitPrice (GBP, escala logarítmica)", ylabel="Número de linhas")
ax.legend(frameon=False)
ax.grid(axis="y", alpha=.2)
fig.tight_layout()
plt.show()
""")

md("""
## RA3.4 Países com maior valor registrado

O Reino Unido concentra 8,75 milhões de GBP, seguido pelos Países Baixos e pela Irlanda. O gráfico se refere aos registros desta loja, que ficava no Reino Unido.
""")
code("""
# Compara os dez países com maior valor registrado no recorte.
country_values = (
    valued_items.groupby("Country", as_index=False)
    .agg(Linhas=("InvoiceNo", "size"), ValorGBP=("ItemValueGBP", "sum"))
    .sort_values("ValorGBP", ascending=False)
)
top_countries = country_values.head(10).sort_values("ValorGBP")
display(country_values.head(10).round({"ValorGBP": 2}))
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.barh(top_countries["Country"], top_countries["ValorGBP"] / 1000,
        color="#54A24B")
ax.set(title="10 países com maior valor de itens positivos no recorte",
       xlabel="Valor bruto dos itens (mil GBP)", ylabel="País")
ax.grid(axis="x", alpha=.2)
fig.tight_layout()
plt.show()
""")

md("""
## RA3.5 Representatividade

As conclusões se limitam ao período de dezembro de 2010 a dezembro de 2011 e ao histórico disponível dessa loja. Mantivemos as linhas idênticas porque a base não tem uma chave por item de transação para verificar se são repetições indevidas. A análise diária usa data, quantidade e preço, então inclui as linhas sem `CustomerID`.
""")
code("""
# Calcula o percentual de linhas sem ID de cliente e conta as linhas repetidas.
missing_customer_share = loaded["CustomerID"].isna().mean() * 100
duplicate_count = loaded.drop(columns="SourceRow").duplicated().sum()
# Mostra o período e o número de países para indicar a cobertura da base.
print(f"Período: {loaded.InvoiceDate.min().date()} a {loaded.InvoiceDate.max().date()}")
print(f"Países: {loaded.Country.nunique()}")
print(f"Linhas sem CustomerID: {missing_customer_share:.2f}%")
print(f"Linhas idênticas extras preservadas: {duplicate_count:,}".replace(",", "."))
""")

md("""
## RA3.6 Previsão diária

O Random Forest estima o total do dia usando os valores de um e sete dias antes, a média dos sete dias anteriores e o dia da semana (codificado por seno e cosseno). Os primeiros sete dias servem para montar o histórico. Dividimos os dias restantes em 293 para treino e 74 para teste, em ordem cronológica.

Para cada dia de teste, o modelo recebe os totais observados até o dia anterior. A referência semanal usa o total de sete dias antes. O MAE é o erro absoluto médio, e o RMSE dá mais peso aos erros grandes. Os dois são expressos em GBP.
""")
code("""
# Mostra os erros, a importância das entradas e as datas de treino e teste.
ra3_model = fit_daily_value_model(loaded)
ra3_metrics = ra3_model["metrics"]
ra3_comparison = ra3_model["comparison"]
display(ra3_metrics)
display(ra3_model["importance"].round(3))
print(f"Treino: {ra3_model['train_days']} dias, até {ra3_model['train_end'].date()}")
print(f"Teste: {ra3_model['test_days']} dias, de {ra3_model['test_start'].date()} a {ra3_model['test_end'].date()}")
# Compara os valores observados com as duas previsões no período de teste.
fig, ax = plt.subplots(figsize=(12, 4.5))
ax.plot(ra3_comparison.index, ra3_comparison["Real (GBP)"], color="#222222",
        linewidth=1.8, label="Observado")
ax.plot(ra3_comparison.index, ra3_comparison["Modelo (GBP)"], color="#4C78A8",
        linewidth=1.5, label="Random Forest")
ax.plot(ra3_comparison.index, ra3_comparison["Baseline semanal (GBP)"],
        color="#F58518", alpha=.8, linewidth=1.2, label="Baseline semanal")
ax.set(title="Previsão de um dia à frente — período de teste",
       xlabel="Data", ylabel="Valor bruto dos itens (GBP)")
ax.legend(frameon=False, ncol=3)
ax.grid(axis="y", alpha=.2)
fig.tight_layout()
plt.show()
""")

md("""
## RA3.7 Resultados da previsão

O Random Forest reduziu o MAE em 6,7% e o RMSE em 4,1% em relação à referência semanal. O MAE de 13.607,02 GBP equivale a cerca de 54% da mediana diária de todo o período. O pico perto do fim do gráfico foi um dos maiores erros da previsão.

As métricas ficam em `evidence/ra3_results.json`.

### Referências do RA3

- Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. DOI 10.24432/C5BW33.
- Documentação do scikit-learn. [RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html), [MAE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html) e [RMSE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.root_mean_squared_error.html).
""")
code("""
from matplotlib import __version__ as matplotlib_version
from sklearn import __version__ as sklearn_version

# Reúne e salva as métricas, o período de teste e os limites da análise.
ra3_record = {
    "rows_analyzed": int(len(loaded)),
    "daily_observations": int(len(ra3_model["daily"])),
    "daily_target": "Soma diária de Quantity × UnitPrice (GBP)",
    "train_days": int(ra3_model["train_days"]),
    "test_days": int(ra3_model["test_days"]),
    "train_end": ra3_model["train_end"].date().isoformat(),
    "test_start": ra3_model["test_start"].date().isoformat(),
    "test_end": ra3_model["test_end"].date().isoformat(),
    "metrics": ra3_metrics.to_dict(orient="records"),
    "missing_customer_share_percent": round(float(missing_customer_share), 4),
    "countries": int(loaded.Country.nunique()),
    "libraries": {"matplotlib": matplotlib_version, "scikit_learn": sklearn_version},
    "limitations": [
        "Uma loja, de dezembro de 2010 a dezembro de 2011",
        "Valor bruto dos itens positivos, com cancelamentos separados",
        "Avaliação de um dia à frente",
    ],
}
(ROOT / "evidence/ra3_results.json").write_text(
    json.dumps(ra3_record, ensure_ascii=False, indent=2), encoding="utf-8")
print("Resultados do RA3 registrados em evidence/ra3_results.json.")
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
    "ra3_daily_observations": ra3_record["daily_observations"],
    "ra3_train_days": ra3_record["train_days"],
    "ra3_test_days": ra3_record["test_days"],
    "ra3_metrics": ra3_record["metrics"],
    "ra3_libraries": ra3_record["libraries"],
}
(ROOT / "evidence/execution_record.json").write_text(
    json.dumps(execution_record, ensure_ascii=False, indent=2), encoding="utf-8")
print("Registro de execução atualizado em evidence/execution_record.json.")
""")

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
