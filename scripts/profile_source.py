"""Diagnóstico reproduzível do arquivo oficial Online Retail para o RA1.

O XLSX original é somente lido. Este script não calcula receita, não executa
conteúdo da planilha e não produz a base preparada final.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from data_preparation import prepare_data


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
EVIDENCE = ROOT / "evidence"
PAGE_URL = "https://archive.ics.uci.edu/dataset/352/online+retail"
DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
MEMBER_NAME = "Online Retail.xlsx"
EXPECTED_ARCHIVE_SHA256 = "f5385cbb54bbebf7196389109c6b0621faab0c304e3702548165e71c84aede8b"
PRODUCT_PATTERN = r"\d{5}[A-Za-z]*"
EXPECTED_COLUMNS = [
    "InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
    "UnitPrice", "CustomerID", "Country",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    return value


def records(frame: pd.DataFrame, limit: int = 5) -> list[dict]:
    return [
        {"source_row": int(index) + 2, **{key: json_value(value) for key, value in row.items()}}
        for index, row in frame.head(limit).iterrows()
    ]


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    archive_path = RAW / "online_retail_uci.zip"
    workbook_path = RAW / MEMBER_NAME
    download_manifest_path = RAW / "download_manifest.json"
    if not archive_path.exists():
        request = urllib.request.Request(DOWNLOAD_URL, headers={"User-Agent": "Academic-Data-Profile/1.0"})
        temp_path = archive_path.with_suffix(".zip.part")
        with urllib.request.urlopen(request, timeout=180) as response, temp_path.open("wb") as target:
            http_metadata = {
                "final_url": response.url,
                "content_type": response.headers.get("Content-Type"),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
            }
            shutil.copyfileobj(response, target)
        temp_path.replace(archive_path)
        download_manifest = {
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "page_url": PAGE_URL,
            "download_url": DOWNLOAD_URL,
            "http": http_metadata,
            "archive_sha256": sha256(archive_path),
        }
        download_manifest_path.write_text(json.dumps(download_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    elif download_manifest_path.exists():
        download_manifest = json.loads(download_manifest_path.read_text(encoding="utf-8"))
        if sha256(archive_path) != download_manifest["archive_sha256"]:
            raise ValueError("O ZIP existente diverge do hash registrado; original não sobrescrito.")
    else:
        # O notebook pode ter obtido a mesma fonte antes deste diagnóstico.
        if sha256(archive_path) != EXPECTED_ARCHIVE_SHA256:
            raise ValueError("ZIP sem manifesto e diferente da versão oficial verificada.")
        download_manifest = {
            "downloaded_at_utc": None,
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "page_url": PAGE_URL, "download_url": DOWNLOAD_URL,
            "archive_sha256": EXPECTED_ARCHIVE_SHA256,
            "note": "Arquivo preexistente verificado; instante do download não conhecido.",
        }
        download_manifest_path.write_text(
            json.dumps(download_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if sha256(archive_path) != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("A versão do ZIP difere da fonte verificada para este projeto.")
    with zipfile.ZipFile(archive_path) as archive:
        archive_members = archive.namelist()
        if MEMBER_NAME not in archive_members:
            raise ValueError(f"Arquivo esperado ausente do ZIP: {MEMBER_NAME}")
        if not workbook_path.exists():
            # Copia apenas o membro conhecido, sem extrair caminhos arbitrários.
            with archive.open(MEMBER_NAME) as source, workbook_path.open("xb") as target:
                shutil.copyfileobj(source, target)
        workbook_member_hash = hashlib.sha256(archive.read(MEMBER_NAME)).hexdigest()
        if sha256(workbook_path) != workbook_member_hash:
            raise ValueError("O XLSX existente diverge do membro original no ZIP.")

    with pd.ExcelFile(workbook_path, engine="openpyxl") as workbook:
        sheet_names = workbook.sheet_names
        frame = pd.read_excel(workbook, sheet_name=0)
    if list(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError(f"Esquema inesperado: {list(frame.columns)}")

    invoice = frame["InvoiceNo"].astype("string").str.strip()
    stock = frame["StockCode"].astype("string").str.strip()
    description = frame["Description"].astype("string").str.strip()
    country = frame["Country"].astype("string").str.strip()
    quantity = pd.to_numeric(frame["Quantity"], errors="coerce")
    price = pd.to_numeric(frame["UnitPrice"], errors="coerce")
    dates = pd.to_datetime(frame["InvoiceDate"], errors="coerce")
    customer = pd.to_numeric(frame["CustomerID"], errors="coerce")
    blank_description = description.isna() | description.eq("")
    cancellation = invoice.str.upper().str.startswith("C", na=False)
    product_code = stock.str.fullmatch(PRODUCT_PATTERN, na=False)
    invalid_essential = (
        invoice.isna() | invoice.eq("") | stock.isna() | stock.eq("")
        | country.isna() | country.eq("") | dates.isna()
        | quantity.isna() | ~np.isfinite(quantity)
        | price.isna() | ~np.isfinite(price)
    )
    duplicate_extra = frame.duplicated(keep="first")
    duplicate_any = frame.duplicated(keep=False)

    # A primeira regra aplicável decide o motivo único; as contagens não se somam duas vezes.
    rule_masks = [
        ("invalid_essential", "Campos essenciais ausentes, inválidos ou não finitos", invalid_essential),
        ("cancellation", "InvoiceNo começa com C", cancellation),
        ("nonpositive_quantity", "Quantity <= 0 após as regras anteriores", quantity.le(0)),
        ("nonpositive_price", "UnitPrice <= 0 após as regras anteriores", price.le(0)),
        ("missing_description", "Descrição ausente/vazia após as regras anteriores", blank_description),
        ("non_merchandise_code", "StockCode não corresponde a cinco dígitos com sufixo alfabético opcional", ~product_code),
    ]
    remaining = pd.Series(True, index=frame.index)
    sequential = []
    for rule_id, label, condition in rule_masks:
        selected = remaining & condition.fillna(False)
        before = int(remaining.sum())
        remaining &= ~selected
        sequential.append({
            "rule": rule_id,
            "description": label,
            "rows_before": before,
            "rows_excluded": int(selected.sum()),
            "rows_remaining": int(remaining.sum()),
            "samples": records(frame.loc[selected]),
        })
    prepared = frame.loc[remaining]
    assert len(frame) == len(prepared) + sum(rule["rows_excluded"] for rule in sequential)

    special_codes = []
    for code, group in frame.loc[~product_code].groupby(stock.loc[~product_code], sort=True, dropna=False):
        special_codes.append({
            "stock_code": json_value(code),
            "rows": int(len(group)),
            "description_examples": [json_value(x) for x in group["Description"].drop_duplicates().head(8)],
            "positive_quantity_and_price_rows": int((group["Quantity"].gt(0) & group["UnitPrice"].gt(0)).sum()),
        })

    numeric_profile = {}
    for column in ["Quantity", "UnitPrice"]:
        series = frame[column]
        numeric_profile[column] = {
            "min": json_value(series.min()),
            "max": json_value(series.max()),
            "quantiles": {str(q): json_value(series.quantile(q)) for q in [0.01, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999]},
            "negative": int(series.lt(0).sum()),
            "zero": int(series.eq(0).sum()),
            "positive": int(series.gt(0).sum()),
            "nonfinite": int((~np.isfinite(series)).sum()),
            "lowest_samples": records(frame.sort_values(column, kind="stable")),
            "highest_samples": records(frame.sort_values(column, ascending=False, kind="stable")),
        }

    leading_trailing = {}
    for column in ["InvoiceNo", "StockCode", "Description", "Country"]:
        strings = frame[column].astype("string")
        leading_trailing[column] = int(strings.ne(strings.str.strip()).fillna(False).sum())

    profile = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "RA1: diagnóstico de qualidade e proposta de preparação, sem agregações de negócio ou receita",
        "source": {
            **download_manifest,
            "citation": "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33.",
            "doi": "https://doi.org/10.24432/C5BW33",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "archive_path": archive_path.relative_to(ROOT).as_posix(),
            "archive_size_bytes": archive_path.stat().st_size,
            "archive_members": archive_members,
            "workbook_path": workbook_path.relative_to(ROOT).as_posix(),
            "workbook_size_bytes": workbook_path.stat().st_size,
            "workbook_sha256": sha256(workbook_path),
            "workbook_matches_original_archive_member": True,
            "sheet_names": sheet_names,
            "worksheet": sheet_names[0],
            "official_description": {
                "unit_of_observation": "Linha de item de transação, não pedido inteiro nem cliente único",
                "currency": "GBP (libra esterlina)",
                "supplier_country": "Reino Unido",
                "business": "Varejo online sem loja física de presentes, com muitos clientes atacadistas",
                "cancellation_rule": "InvoiceNo com prefixo c indica cancelamento (comparação sem diferenciar maiúscula/minúscula)",
                "metadata_caveat": "A página da UCI informa ausência de valores faltantes, mas o arquivo real tem lacunas; prevalece a inspeção do arquivo.",
            },
        },
        "runtime": {"python": platform.python_version(), "pandas": pd.__version__},
        "shape": {"rows": len(frame), "columns": len(frame.columns)},
        "schema": [
            {"column": column, "pandas_dtype": str(frame[column].dtype), "null_count": int(frame[column].isna().sum()), "distinct_non_null": int(frame[column].nunique(dropna=True))}
            for column in frame.columns
        ],
        "null_counts": {column: int(count) for column, count in frame.isna().sum().items()},
        "missing_description_count": int(blank_description.sum()),
        "leading_or_trailing_whitespace_counts": leading_trailing,
        "dates": {"min": json_value(dates.min()), "max": json_value(dates.max()), "unparseable_or_missing": int(dates.isna().sum()), "timezone": "Não informada na fonte; conservar horário ingênuo, sem inventar UTC"},
        "duplicates": {
            "definition": "Igualdade das oito colunas originais, antes de normalizar textos",
            "extra_rows_after_first": int(duplicate_extra.sum()),
            "all_rows_in_duplicate_groups": int(duplicate_any.sum()),
            "distinct_duplicate_groups": int(frame.loc[duplicate_any].drop_duplicates().shape[0]),
            "samples": records(frame.loc[duplicate_any], 10),
            "policy": "Manter e sinalizar. Igualdade não prova ingestão duplicada porque não existe identificador único de linha no arquivo. Não executar drop_duplicates automaticamente.",
        },
        "uniqueness": {
            "invoice_count": int(invoice.nunique(dropna=True)),
            "stock_code_count": int(stock.nunique(dropna=True)),
            "customer_count_non_null": int(customer.nunique(dropna=True)),
            "country_count": int(country.nunique(dropna=True)),
            "invoice_stock_pair_duplicate_extra_rows": int(frame.duplicated(subset=["InvoiceNo", "StockCode"]).sum()),
            "invoice_is_row_identifier": bool(invoice.is_unique),
            "invoice_stock_pair_is_row_identifier": not bool(frame.duplicated(subset=["InvoiceNo", "StockCode"]).any()),
            "proposed_technical_id": "source_row = índice original + 2, equivalente à linha da planilha, preservado após filtros",
        },
        "numeric_profile": numeric_profile,
        "cancellations": {
            "rows": int(cancellation.sum()),
            "invoices": int(invoice[cancellation].nunique()),
            "quantity_negative": int((cancellation & quantity.lt(0)).sum()),
            "quantity_zero": int((cancellation & quantity.eq(0)).sum()),
            "quantity_positive": int((cancellation & quantity.gt(0)).sum()),
            "negative_quantity_without_c_prefix": int((~cancellation & quantity.lt(0)).sum()),
            "samples": records(frame.loc[cancellation]),
        },
        "stock_codes": {
            "candidate_merchandise_pattern_fullmatch": PRODUCT_PATTERN,
            "matching_rows": int(product_code.sum()),
            "nonmatching_rows": int((~product_code).sum()),
            "nonmatching_distinct_codes": len(special_codes),
            "special_codes": special_codes,
            "alphabetic_suffix_matching_examples": stock[product_code & stock.str.contains(r"[A-Za-z]", na=False)].drop_duplicates().head(20).tolist(),
            "tradeoff": "Heurística operacional de escopo, não cadastro oficial de mercadorias. Mantém variantes alfabéticas e pode excluir códigos de produto válidos fora do padrão (por exemplo, DCGSSBOY e DCGSSGIRL); os excluídos permanecem rastreáveis para revisão.",
        },
        "quality_flags_overlapping_do_not_sum": {
            "invalid_essential": int(invalid_essential.sum()),
            "cancellation": int(cancellation.sum()),
            "quantity_nonpositive": int(quantity.le(0).sum()),
            "unit_price_nonpositive": int(price.le(0).sum()),
            "description_blank_or_null": int(blank_description.sum()),
            "non_merchandise_code_pattern": int((~product_code).sum()),
            "customer_id_missing": int(customer.isna().sum()),
            "exact_duplicate_extra_rows": int(duplicate_extra.sum()),
        },
        "rejected_regex_proposal": {
            "scope": "Itens de transações positivas com preço positivo e código de mercadoria no padrão selecionado; não representa vendas líquidas de devoluções/cancelamentos",
            "status": "REJECTED: alternativa diagnóstica substituída pela lista explícita da função prepare_data",
            "rejection_reason": "O formato do código não comprova a natureza da linha. A regex separava também 36 linhas positivas de oito códigos com descrições de mercadoria, incluindo DCGSSBOY e PADS.",
            "sequential_exclusions": sequential,
            "prepared_rows": int(remaining.sum()),
            "excluded_rows": int((~remaining).sum()),
            "balance_check": int(remaining.sum()) + int((~remaining).sum()) == len(frame),
            "prepared_null_counts": {column: int(count) for column, count in prepared.isna().sum().items()},
            "prepared_exact_duplicate_extra_rows": int(prepared.duplicated().sum()),
            "prepared_customer_missing_retained": int(prepared["CustomerID"].isna().sum()),
            "prepared_quantity_range": {"min": int(prepared["Quantity"].min()), "max": int(prepared["Quantity"].max())},
            "prepared_price_range": {"min": float(prepared["UnitPrice"].min()), "max": float(prepared["UnitPrice"].max())},
            "prepared_nonstandard_invoice_examples": records(prepared.loc[~invoice.loc[remaining].str.fullmatch(r"\d{6}", na=False)]),
            "retention_policies": {
                "raw": "Preservar ZIP e XLSX originais com hashes e origem",
                "excluded": "Exportar registros separados com source_row e primeiro motivo de exclusão, sem apagar o bruto",
                "customer_missing": "Preservar NA; não inventar cliente nem excluir venda por ausência de identificação",
                "duplicates": "Preservar e sinalizar igualdade nas oito colunas; avaliar impacto em etapa futura antes de deduplicar",
                "outliers": "Manter extremos positivos. O contexto atacadista torna cortes arbitrários por quantidade/preço inadequados sem confirmação externa",
                "text": "Remover somente espaços no início/fim, sem alterar nomes ou substituir descrições ausentes por suposição",
                "ids": "InvoiceNo, StockCode e CustomerID são identificadores categóricos, não medidas; converter CustomerID conhecido para texto inteiro sem .0",
                "time": "Preservar InvoiceDate como datetime sem timezone atribuído, porque a fonte não fornece fuso",
                "cancelled_originals": "Filtrar a linha C não desfaz automaticamente a venda original. Reconciliação entre venda e cancelamento requer regra específica e está fora do RA1",
            },
        },
    }
    # A proposta aceita é calculada pela implementação canônica, sem duplicar filtros.
    clean, excluded, preparation_summary = prepare_data(frame)
    final_rule_order = [
        ("cancellation", "InvoiceNo começa com C, sem diferenciar maiúsculas/minúsculas"),
        ("invalid_required_fields", "Campos essenciais inválidos, valores não finitos ou quantidade fracionária"),
        ("non_positive_quantity", "Quantity <= 0 após as regras anteriores"),
        ("non_positive_price", "UnitPrice <= 0 após as regras anteriores"),
        ("non_merchandise_code", "Código explicitamente identificado como frete, taxa, ajuste, desconto, amostra ou voucher"),
        ("missing_description", "Descrição ausente/vazia após as regras anteriores"),
    ]
    final_sequential = []
    rows_remaining = len(frame)
    for reason, label in final_rule_order:
        matches = excluded.loc[excluded["ExclusionReason"].eq(reason)]
        count = len(matches)
        source_indexes = matches["SourceRow"].sub(2).to_numpy()
        final_sequential.append({
            "rule": reason,
            "description": label,
            "rows_before": rows_remaining,
            "rows_excluded": count,
            "rows_remaining": rows_remaining - count,
            "samples": records(frame.loc[source_indexes]),
        })
        rows_remaining -= count
    assert rows_remaining == len(clean)
    profile["proposal"] = {
        "status": "ACCEPTED: execução real de scripts/data_preparation.py::prepare_data",
        "scope": "Linhas de mercadorias com quantidade e preço positivos; não representa vendas líquidas de cancelamentos/devoluções",
        "implementation_path": "scripts/data_preparation.py",
        "implementation_sha256": sha256(ROOT / "scripts" / "data_preparation.py"),
        "execution_creates_prepared_files": False,
        "rule": "Comparação case-insensitive com POST, DOT, C2, M, D, BANK CHARGES, AMAZONFEE, CRUK, B, S e prefixo GIFT_; formato fora do padrão numérico não causa exclusão",
        "sequential_exclusions": final_sequential,
        "preparation_summary": preparation_summary,
        "prepared_rows": len(clean),
        "excluded_rows": len(excluded),
        "balance_check": len(clean) + len(excluded) == len(frame),
        "prepared_null_counts": {column: int(count) for column, count in clean.isna().sum().items()},
        "prepared_schema": {column: str(dtype) for column, dtype in clean.dtypes.items()},
        "prepared_exact_duplicate_extra_rows": int(clean[EXPECTED_COLUMNS].duplicated().sum()),
        "prepared_customer_missing_retained": int(clean["CustomerID"].isna().sum()),
        "prepared_quantity_range": {"min": int(clean["Quantity"].min()), "max": int(clean["Quantity"].max())},
        "prepared_price_range": {"min": float(clean["UnitPrice"].min()), "max": float(clean["UnitPrice"].max())},
        "rare_merchandise_rows_retained": len(clean.loc[~clean["StockCode"].str.fullmatch(PRODUCT_PATTERN, na=False)]),
        "rare_merchandise_codes_retained": sorted(clean.loc[~clean["StockCode"].str.fullmatch(PRODUCT_PATTERN, na=False), "StockCode"].unique().tolist()),
        "retention_policies": {
            **profile["rejected_regex_proposal"]["retention_policies"],
            "excluded": "Segregar registros com SourceRow e primeiro motivo ExclusionReason, sem apagar o bruto",
            "rare_codes": "Preservar códigos raros de mercadoria. A lista explícita usa as descrições observadas; futuras bases requerem nova inspeção",
        },
        "limitations": [
            "O arquivo não fornece uma chave única original de linha; SourceRow é uma chave técnica para rastrear a origem.",
            "Duplicatas idênticas são mantidas e sinalizadas pelo diagnóstico, porque igualdade não prova erro de ingestão.",
            "A classificação dos códigos especiais deriva das descrições observadas, sem cadastro externo completo de produtos.",
            "Cancelar uma linha C não estorna automaticamente a linha de venda original; esse vínculo não é inferido no RA1.",
        ],
    }
    output_path = EVIDENCE / "source_profile.json"
    output_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "profile": output_path.relative_to(ROOT).as_posix(),
        "shape": profile["shape"],
        "null_counts": profile["null_counts"],
        "duplicates_extra": profile["duplicates"]["extra_rows_after_first"],
        "prepared_rows_proposed": profile["proposal"]["prepared_rows"],
        "sequential_exclusions": [{k: value for k, value in row.items() if k != "samples"} for row in final_sequential],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
