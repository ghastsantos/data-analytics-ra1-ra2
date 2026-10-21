"""Preparação para estudar registros positivos de mercadorias, não vendas líquidas."""
import numpy as np
import pandas as pd


COLUMNS = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
           "UnitPrice", "CustomerID", "Country"]


def prepare_data(raw):
    """Retorna dados preparados, linhas fora do recorte e balanço das decisões.

    SourceRow aponta para a linha do Excel original (cabeçalho na linha 1).
    Nenhuma linha é descartada sem aparecer no arquivo de exclusões.
    """
    missing = set(COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(missing)}")
    data = raw[COLUMNS].copy().reset_index(drop=True)
    data.insert(0, "SourceRow", np.arange(2, len(data) + 2))
    for column in ["InvoiceNo", "StockCode", "Description", "CustomerID", "Country"]:
        data[column] = data[column].astype("string").str.strip().replace("", pd.NA)
    # O Excel armazena IDs de cliente numéricos; o sufixo .0 vem da leitura com nulos.
    data["CustomerID"] = data["CustomerID"].str.replace(r"\.0$", "", regex=True)
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce")
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["UnitPrice"] = pd.to_numeric(data["UnitPrice"], errors="coerce")

    reasons = pd.Series(pd.NA, index=data.index, dtype="string")

    def exclude(mask, reason):
        # A primeira regra aplicável evita contar a mesma linha em dois motivos.
        reasons.loc[reasons.isna() & mask.fillna(False)] = reason

    exclude(data["InvoiceNo"].str.upper().str.startswith("C"), "cancellation")
    required = ["InvoiceNo", "StockCode", "InvoiceDate", "Quantity", "UnitPrice", "Country"]
    invalid = data[required].isna().any(axis=1)
    invalid |= ~np.isfinite(data["Quantity"]) | ~np.isfinite(data["UnitPrice"])
    invalid |= data["Quantity"].mod(1).ne(0)
    exclude(invalid, "invalid_required_fields")
    exclude(data["Quantity"].le(0), "non_positive_quantity")
    exclude(data["UnitPrice"].le(0), "non_positive_price")
    # As descrições observadas identificam estes códigos como frete, taxas,
    # descontos, ajustes manuais, amostras ou vouchers. Códigos raros de produtos
    # (por exemplo DCGSSBOY e PADS) são mantidos; formato sozinho não prova erro.
    other_codes = {"POST", "DOT", "C2", "M", "D", "BANK CHARGES", "AMAZONFEE",
                   "CRUK", "B", "S"}
    code = data["StockCode"].str.upper()
    exclude(code.isin(other_codes) | code.str.startswith("GIFT_"),
            "non_merchandise_code")
    exclude(data["Description"].isna(), "missing_description")

    clean = data.loc[reasons.isna()].copy()
    clean["Quantity"] = clean["Quantity"].astype("Int64")
    clean["UnitPrice"] = clean["UnitPrice"].astype("Float64")
    # Clientes ausentes, repetições exatas e extremos são preservados intencionalmente.
    excluded = data.loc[reasons.notna()].copy()
    excluded["ExclusionReason"] = reasons.loc[reasons.notna()]
    summary = {
        "input_rows": int(len(raw)), "prepared_rows": int(len(clean)),
        "excluded_rows": int(len(excluded)), "input_columns": int(raw.shape[1]),
        "prepared_columns": int(clean.shape[1]),
        "exclusions_by_reason": {k: int(v) for k, v in reasons.value_counts().items()},
        "missing_customers_kept": int(clean["CustomerID"].isna().sum()),
        "exact_duplicate_rows_kept": int(clean[COLUMNS].duplicated().sum()),
        "source_rows_unique": bool(clean["SourceRow"].is_unique),
        "date_min": str(clean["InvoiceDate"].min()),
        "date_max": str(clean["InvoiceDate"].max()),
    }
    assert len(clean) + len(excluded) == len(raw)
    assert not set(clean["SourceRow"]).intersection(excluded["SourceRow"])
    return clean, excluded, summary
