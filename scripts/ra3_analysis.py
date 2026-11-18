"""Estatística descritiva e previsão diária para o RA3."""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def add_item_value(data):
    """Copia os registros e calcula o valor bruto dos itens positivos em GBP."""
    result = data.copy()
    result["ItemValueGBP"] = (
        pd.to_numeric(result["Quantity"], errors="raise").astype(float)
        * pd.to_numeric(result["UnitPrice"], errors="raise").astype(float)
    )
    return result


def descriptive_statistics(prepared):
    """Resume medidas numéricas sem remover observações extremas."""
    valued = add_item_value(prepared)
    rows = []
    for column, label in [
        ("Quantity", "Quantidade por linha (unidades)"),
        ("UnitPrice", "Preço unitário (GBP)"),
        ("ItemValueGBP", "Valor por linha (GBP)"),
    ]:
        values = pd.to_numeric(valued[column], errors="raise").astype(float)
        rows.append({
            "Medida": label,
            "Média": values.mean(),
            "Mediana": values.median(),
            "Desvio padrão": values.std(),
            "Mínimo": values.min(),
            "P90": values.quantile(0.90),
            "P99": values.quantile(0.99),
            "Máximo": values.max(),
        })
    return pd.DataFrame(rows).round(4)


def build_daily_dataset(prepared):
    """Agrega valor e linhas por dia e inclui dias sem registros como zero."""
    valued = add_item_value(prepared)
    valued["Date"] = pd.to_datetime(valued["InvoiceDate"]).dt.normalize()
    daily = valued.groupby("Date").agg(
        DailyValueGBP=("ItemValueGBP", "sum"),
        ItemLines=("InvoiceNo", "size"),
    )
    calendar = pd.date_range(daily.index.min(), daily.index.max(), freq="D", name="Date")
    daily = daily.reindex(calendar, fill_value=0)
    daily["ItemLines"] = daily["ItemLines"].astype(int)
    daily["DailyValueGBP"] = daily["DailyValueGBP"].astype(float)
    return daily


def fit_daily_value_model(prepared, test_fraction=0.20):
    """Forecasta valor diário em GBP com divisão temporal e baseline semanal."""
    if not 0 < test_fraction < 0.5:
        raise ValueError("test_fraction deve estar entre 0 e 0,5.")

    daily = build_daily_dataset(prepared)
    target = daily["DailyValueGBP"]
    features = pd.DataFrame(index=daily.index)
    features["lag_1"] = target.shift(1)
    features["lag_7"] = target.shift(7)
    features["rolling_mean_7"] = target.shift(1).rolling(7, min_periods=7).mean()
    weekday = daily.index.dayofweek
    features["weekday_sin"] = np.sin(2 * np.pi * weekday / 7)
    features["weekday_cos"] = np.cos(2 * np.pi * weekday / 7)
    model_data = features.assign(target=target).dropna()

    split_index = int(len(model_data) * (1 - test_fraction))
    if split_index < 30 or len(model_data) - split_index < 14:
        raise ValueError("Histórico insuficiente para a divisão temporal definida.")

    x_train = model_data.iloc[:split_index].drop(columns="target")
    y_train = model_data.iloc[:split_index]["target"]
    x_test = model_data.iloc[split_index:].drop(columns="target")
    y_test = model_data.iloc[split_index:]["target"]
    model = RandomForestRegressor(
        n_estimators=300, min_samples_leaf=5, random_state=42, n_jobs=-1
    )
    model.fit(x_train, y_train)
    predictions = pd.Series(model.predict(x_test), index=x_test.index, name="Modelo")
    baseline = model_data.iloc[split_index:]["lag_7"].rename("Baseline semanal")

    metrics = pd.DataFrame([
        {
            "Abordagem": "Regressão Random Forest",
            "MAE (GBP)": mean_absolute_error(y_test, predictions),
            "RMSE (GBP)": np.sqrt(mean_squared_error(y_test, predictions)),
        },
        {
            "Abordagem": "Baseline: mesmo dia da semana anterior",
            "MAE (GBP)": mean_absolute_error(y_test, baseline),
            "RMSE (GBP)": np.sqrt(mean_squared_error(y_test, baseline)),
        },
    ]).round(2)
    comparison = pd.DataFrame({
        "Real (GBP)": y_test,
        "Modelo (GBP)": predictions,
        "Baseline semanal (GBP)": baseline,
    })
    importance = pd.Series(
        model.feature_importances_, index=x_train.columns, name="Importância"
    ).sort_values(ascending=False).to_frame()

    if not x_train.index.max() < x_test.index.min():
        raise AssertionError("A divisão precisa manter o teste depois do treino.")
    if features.loc[x_test.index, ["lag_1", "lag_7", "rolling_mean_7"]].isna().any().any():
        raise AssertionError("A previsão não pode usar histórico incompleto.")

    return {
        "daily": daily,
        "metrics": metrics,
        "comparison": comparison,
        "importance": importance,
        "train_end": x_train.index.max(),
        "test_start": x_test.index.min(),
        "test_end": x_test.index.max(),
        "train_days": len(x_train),
        "test_days": len(x_test),
    }
