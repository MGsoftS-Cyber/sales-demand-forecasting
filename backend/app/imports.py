"""CSV review and explicit daily-calendar normalization."""

import csv
import io
from datetime import date, timedelta
from .schemas import Observation


def preview_sales(text):
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != ["date", "quantity"]:
        return dict(rows=[], errors=[dict(row=1, message="Required header: date,quantity")], valid=False)
    rows = []
    errors = []
    seen = set()
    for index, row in enumerate(reader, 2):
        if index > 1501:
            errors.append(dict(row=index, message="Maximum 1,500 observations."))
            break
        try:
            item = Observation.model_validate(row)
            if item.date in seen:
                raise ValueError("Duplicate date")
            seen.add(item.date)
            rows.append(item.model_dump(mode="json"))
        except Exception:
            errors.append(
                dict(row=index, message="Use a unique ISO date no later than today and a finite, nonnegative quantity.")
            )
    if len(rows) < 14:
        errors.append(dict(row=1, message="At least 14 valid observations are required."))
    return dict(rows=rows, errors=errors, valid=not errors)


def normalize(observations, policy):
    """Missing days are never treated as zero without an explicit user policy."""
    ordered = sorted(observations, key=lambda x: x.date)
    mapping = {x.date: x.quantity for x in ordered}
    if len(mapping) != len(ordered):
        raise ValueError("Each date must occur once; aggregate same-day orders first.")
    span = (ordered[-1].date - ordered[0].date).days + 1
    if span > 1500:
        raise ValueError("The full daily calendar must not exceed 1,500 days.")
    days = [ordered[0].date + timedelta(days=i) for i in range(span)]
    missing = [day for day in days if day not in mapping]
    if missing and policy == "reject":
        raise ValueError(
            "Missing calendar days. Supply explicit zero-sales rows or choose zero_fill after verifying source completeness."
        )
    rows = [dict(date=str(day), quantity=mapping.get(day, 0), imputed=day in missing) for day in days]
    warnings = []
    if missing:
        warnings.append(
            f"{len(missing)} dates explicitly zero-filled; this can lower forecasts if data was incomplete."
        )
    if (date.today() - days[-1]).days > 7:
        warnings.append(
            "Dataset ends more than seven days ago. Forecast dates start after that dataset, not after today."
        )
    if len(rows) < 56:
        warnings.append("Short history: automatic model selection needs at least 56 calendar days.")
    return rows, dict(
        count=len(rows),
        start=str(days[0]),
        end=str(days[-1]),
        imputed_days=len(missing),
        zero_days=sum(x["quantity"] == 0 for x in rows),
        warnings=warnings,
    )
