"""Deterministic daily forecasts, rolling-origin checks and transparent stock plans.

Forecasts describe observed sold quantities. They cannot infer unmet stockout
 demand. Historical errors are empirical ranges, not guaranteed probabilities.
"""

from datetime import date, timedelta
import math
from statistics import mean

ENGINE_VERSION = "1.0.0"
MODELS = ("moving_average", "weekday", "damped_trend")


def predict(values, dates, horizon, model):
    """Fit only the supplied prefix. No future values are used at an origin."""
    tail = values[-28:]
    level = mean(tail)
    if model == "weekday":
        groups = {i: [] for i in range(7)}
        for day, value in zip(dates[-56:], values[-56:]):
            groups[day.weekday()].append(value)
        return [mean(groups[(dates[-1] + timedelta(days=h)).weekday()]) for h in range(1, horizon + 1)]
    if model == "damped_trend":
        center = (len(tail) - 1) / 2
        slope = sum((i - center) * (v - level) for i, v in enumerate(tail)) / sum(
            (i - center) ** 2 for i in range(len(tail))
        )
        fitted_end = level + slope * center
        return [max(0, fitted_end + slope * 0.85 * (1 - 0.85**h) / (1 - 0.85)) for h in range(1, horizon + 1)]
    return [level] * horizon


def scores(errors, actual):
    if not errors:
        return dict(mae=None, rmse=None, wape=None, samples=0)
    total = sum(actual)
    return dict(
        mae=mean(abs(x) for x in errors),
        rmse=math.sqrt(mean(x * x for x in errors)),
        wape=sum(abs(x) for x in errors) / total if total > 0 else None,
        samples=len(errors),
    )


def quantile(values, q):
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lo = math.floor(position)
    hi = math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def evaluate(data):
    values = [x["quantity"] for x in data["history"]]
    dates = [date.fromisoformat(x["date"]) for x in data["history"]]
    n = len(values)
    requested = data["model"]
    warnings = []
    candidates = []
    chosen = requested
    if requested == "auto":
        chosen = "moving_average"
        if n >= 56:
            # Tune on prefixes before the final 14-day evaluation segment.
            validation_end = n - 14
            for model in MODELS:
                errors = []
                actual = []
                for origin in range(max(28, validation_end - 28), validation_end):
                    pred = predict(values[:origin], dates[:origin], 1, model)[0]
                    errors.append(values[origin] - pred)
                    actual.append(values[origin])
                candidates.append(dict(model=model, **scores(errors, actual)))
            chosen = min(candidates, key=lambda x: (x["mae"], MODELS.index(x["model"])))["model"]
        else:
            warnings.append("Auto uses moving_average because fewer than 56 calendar days are available.")
    if chosen == "weekday" and n < 28:
        raise ValueError("Weekday model requires at least 28 daily observations.")
    min_train = 28 if chosen == "weekday" else 14
    # Final-segment evaluation: each origin refits using only earlier observations.
    errors = []
    actual = []
    backtest = []
    for origin in range(max(min_train, n - 14), n):
        pred = predict(values[:origin], dates[:origin], 1, chosen)[0]
        errors.append(values[origin] - pred)
        actual.append(values[origin])
        backtest.append(dict(date=str(dates[origin]), actual=values[origin], predicted=pred))
    metrics = scores(errors, actual)
    # Horizon-specific retrospective errors. At most 120 origins bound CPU work.
    by_lead = {h: [] for h in range(1, data["horizon"] + 1)}
    for origin in range(max(min_train, n - 120), n):
        length = min(data["horizon"], n - origin)
        pred = predict(values[:origin], dates[:origin], length, chosen)
        for j, value in enumerate(pred):
            by_lead[j + 1].append(values[origin + j] - value)
    points = predict(values, dates, data["horizon"], chosen)
    arrivals = {date.fromisoformat(x["date"]): x["quantity"] for x in data["arrivals"]}
    forecast_dates = [dates[-1] + timedelta(days=h) for h in range(1, data["horizon"] + 1)]
    if any(day not in forecast_dates for day in arrivals):
        raise ValueError("Arrival dates must fall within the future forecast horizon.")
    stock = data["starting_stock"]
    unmet = 0
    future = []
    first_shortage = None
    for h, day in enumerate(forecast_dates, 1):
        point = points[h - 1] * data["demand_multiplier"]
        residuals = by_lead[h]
        lower = upper = None
        if len(residuals) >= 8:
            lower = max(0, points[h - 1] + quantile(residuals, 0.10)) * data["demand_multiplier"]
            upper = max(0, points[h - 1] + quantile(residuals, 0.90)) * data["demand_multiplier"]
        # Inventory is a scenario: arrivals at start of day, demand afterwards.
        available = stock + arrivals.get(day, 0)
        shortage = max(0, point - available)
        stock = max(0, available - point)
        unmet += shortage
        if shortage > 0 and first_shortage is None:
            first_shortage = str(day)
        future.append(
            dict(
                date=str(day),
                forecast=point,
                lower=lower,
                upper=upper,
                range_samples=len(residuals),
                arrival=arrivals.get(day, 0),
                ending_stock=stock,
                unmet_demand=shortage,
            )
        )
    if any(x["lower"] is None for x in future):
        warnings.append("Some lead times have fewer than eight historical errors; their ranges are unavailable.")
    if not errors:
        warnings.append("No evaluation origins are available; historical error metrics are unavailable.")
    if data["demand_multiplier"] != 1:
        warnings.append(
            "Scenario multiplier scales the forecast and ranges. Accuracy metrics describe the unscaled historical model."
        )
    warnings.extend(
        [
            "Empirical 10th/90th percentile ranges have no guaranteed future 80% coverage.",
            "Forecasts are sold quantities; stockouts, promotions and unknown holidays are not corrected automatically.",
        ]
    )
    return dict(
        selected_model=chosen,
        candidate_scores=candidates,
        validation=metrics,
        backtest=backtest,
        forecast=future,
        summary=dict(
            total_forecast=sum(x["forecast"] for x in future),
            daily_average=mean(x["forecast"] for x in future),
            first_shortage_date=first_shortage,
            total_unmet=unmet,
            ending_stock=stock,
        ),
        diagnostics=dict(
            history_days=n,
            recent_daily_average=mean(values[-28:]),
            previous_daily_average=mean(values[-56:-28]) if n >= 56 else None,
            zero_day_share=sum(x == 0 for x in values) / n,
        ),
        warnings=warnings,
        conventions=dict(
            frequency="daily calendar",
            forecast_origin=str(dates[-1]),
            model_selection="Pre-final-14-day rolling one-step MAE; fixed simple candidates",
            evaluation="Final up-to-14 rolling one-step origins, refitted each day",
            ranges="Retrospective lead-specific errors; 10/90 empirical quantiles; at least 8 samples",
            inventory="Start-of-day arrivals, then demand; no backlog carry; base scenario",
            seasonality="Weekday pattern only; no annual or holiday model",
        ),
    )
