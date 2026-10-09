# Forecast methodology

## Data and chronology

Exact CSV header date,quantity; ISO calendar dates. At least 14 valid daily observations, maximum 1500 rows/calendar span, CSV text limit 200000 characters. Values are finite and nonnegative up to 1e9. Future dates and duplicates are rejected. Missing dates reject by default; zero_fill requires an explicit user choice and marks imputed rows. A new immutable dataset is created for each accepted revision. Forecast starts the day after its last observation, even if stale.

## Three models

Moving average: mean of the last min(28,n) observations, repeated for every lead.
Weekday profile: mean for the target weekday among the last 56 available dates; requires at least 28 history days.
Damped trend: OLS slope b on the last 28 days, fitted last-day level a, forecast max(0, a + b*0.85*(1-0.85^h)/(1-0.85)). The damping constant is fixed, not optimized.

Auto mode requires 56 days. It compares rolling one-day MAE on up to 28 historical origins strictly before the final 14-day evaluation segment. Lowest selection MAE wins; ties follow moving_average, weekday, damped_trend. Below 56 days auto explicitly falls back to moving_average.

## Evaluation and ranges

Final evaluation refits on prior observations for each of up to 14 last dates. MAE = mean absolute residual; RMSE = sqrt(mean squared residual); WAPE = sum absolute residual / sum actual, null when actual sum is zero. These are one-day historical metrics, not measured next-month-total accuracy. Actual forecasts fit all current history after selection.

For empirical ranges, collect signed actual-minus-predicted errors at up to 120 retrospective origins, separately by lead. Add the 10th and 90th interpolated error quantiles to the corresponding forecast, clamp to nonnegative, then scale by the scenario multiplier. At least 8 errors per lead are needed; otherwise lower/upper are null. Ranges have no guaranteed future 80% coverage. Model selection and calibration reuse past data; range performance is not independently validated. Do not add daily bounds and call them a probabilistic monthly interval.

Multiplier 0–3 scales future demand and ranges only. Original historical metrics remain unchanged. This represents an assumption, not a learned promotion effect.

## Stock planning

Arrivals become available at the start of their date. Available = prior stock + arrival. Unmet = max(0, forecast - available). Ending = max(0, available - forecast). Unmet demand is treated as lost, not accumulated backlog. First shortage date is the first day unmet is positive. Arrivals must fall within forecast dates and be unique by date. Stock is entered manually; no physical inventory write occurs.

## Boundaries

Weekly seasonality only; no annual/holiday/price/campaign features. No stockout correction, hierarchy reconciliation, intermittent-demand specialist, batch-size rounding or service-level optimization. 30-day horizon means the next 30 dates, not automatically the next calendar month. Imported data should use a consistent store timezone and unit; upstream order aggregation is external.

Reference for rolling-origin concepts: https://otexts.com/fpp3/tscv.html . Implementation details above describe this release.
