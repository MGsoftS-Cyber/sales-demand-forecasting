"""Authorized series, immutable dataset versions and saved forecasting workflows."""

import csv
import io
import json
import hashlib
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from .database import get_db
from .security import current_user
from .models import SalesSeries, Dataset, Analysis
from .schemas import SeriesInput, DatasetInput, CsvInput, ForecastInput, ComparisonInput
from .services import mutation
from .imports import preview_sales, normalize
from .engine import evaluate, ENGINE_VERSION

router = APIRouter(prefix="/api/v1")
Key = Header(min_length=1, max_length=100)


def owned_series(db, identifier, user):
    obj = db.scalar(select(SalesSeries).where(SalesSeries.id == identifier, SalesSeries.user_id == user.id))
    if not obj:
        raise HTTPException(404, "Sales series not found in your account.")
    return obj


def series_view(x):
    return dict(id=x.id, sku=x.sku, name=x.name, location=x.location, unit=x.unit)


def dataset_view(x):
    return dict(
        id=x.id,
        series_id=x.series_id,
        source=x.source,
        missing_policy=x.missing_policy,
        quality=x.quality,
        observations=x.observations,
        created_at=x.created_at,
    )


def analysis_view(x):
    return dict(
        id=x.id,
        series_id=x.series_id,
        dataset_id=x.dataset_id,
        inputs=x.inputs,
        results=x.results,
        engine_version=x.engine_version,
        created_at=x.created_at,
    )


@router.get("/series")
def series(user=Depends(current_user), db=Depends(get_db)):
    return [series_view(x) for x in db.scalars(select(SalesSeries).where(SalesSeries.user_id == user.id))]


@router.post("/series", status_code=201)
def create_series(data: SeriesInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)):
    def work():
        obj = SalesSeries(user_id=user.id, **data.model_dump())
        db.add(obj)
        db.flush()
        return series_view(obj)

    return mutation(db, user, "series", idempotency_key, data.model_dump(mode="json"), work)


@router.post("/imports/sales/preview")
def preview(data: CsvInput, user=Depends(current_user)):
    return preview_sales(data.csv_text)


@router.get("/series/{identifier}/datasets")
def datasets(identifier: str, user=Depends(current_user), db=Depends(get_db)):
    owned_series(db, identifier, user)
    return [
        dataset_view(x)
        for x in db.scalars(select(Dataset).where(Dataset.series_id == identifier).order_by(Dataset.created_at.desc()))
    ]


@router.post("/series/{identifier}/datasets", status_code=201)
def create_dataset(
    identifier: str, data: DatasetInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)
):
    owned_series(db, identifier, user)
    try:
        rows, quality = normalize(data.observations, data.missing_policy)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    body = data.model_dump(mode="json")
    fingerprint = hashlib.sha256(
        json.dumps(dict(observations=rows, source=data.source, policy=data.missing_policy), sort_keys=True).encode()
    ).hexdigest()

    def work():
        existing = db.scalar(select(Dataset).where(Dataset.series_id == identifier, Dataset.fingerprint == fingerprint))
        if existing:
            return dataset_view(existing)
        obj = Dataset(
            series_id=identifier,
            source=data.source,
            observations=rows,
            quality=quality,
            missing_policy=data.missing_policy,
            fingerprint=fingerprint,
        )
        db.add(obj)
        db.flush()
        return dataset_view(obj)

    return mutation(db, user, "dataset:" + identifier, idempotency_key, body, work)


@router.post("/series/{identifier}/analyses", status_code=201)
def run_analysis(
    identifier: str, data: ForecastInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)
):
    series = owned_series(db, identifier, user)
    dataset = db.scalar(select(Dataset).where(Dataset.id == data.dataset_id, Dataset.series_id == series.id))
    if dataset is None:
        raise HTTPException(404, "Dataset not found in this sales series.")

    def work():
        frozen = dict(
            **data.model_dump(mode="json"),
            history=dataset.observations,
            source=dataset.source,
            quality=dataset.quality,
            series=series_view(series),
        )
        try:
            results = evaluate(frozen)
            json.dumps(results, allow_nan=False)
        except (ValueError, OverflowError) as exc:
            raise HTTPException(422, str(exc)) from None
        obj = Analysis(
            series_id=series.id, dataset_id=dataset.id, inputs=frozen, results=results, engine_version=ENGINE_VERSION
        )
        db.add(obj)
        db.flush()
        return analysis_view(obj)

    return mutation(db, user, "forecast:" + identifier, idempotency_key, data.model_dump(mode="json"), work)


@router.get("/analyses")
def analyses(user=Depends(current_user), db=Depends(get_db)):
    return [
        analysis_view(x)
        for x in db.scalars(
            select(Analysis)
            .join(SalesSeries, Analysis.series_id == SalesSeries.id)
            .where(SalesSeries.user_id == user.id)
            .order_by(Analysis.created_at.desc())
            .limit(100)
        )
    ]


def owned_analysis(db, identifier, user):
    obj = db.get(Analysis, identifier)
    if obj is None:
        raise HTTPException(404, "Analysis not found.")
    owned_series(db, obj.series_id, user)
    return obj


@router.post("/comparisons")
def compare(data: ComparisonInput, user=Depends(current_user), db=Depends(get_db)):
    records = [owned_analysis(db, x, user) for x in data.analysis_ids]
    if len({(x.series_id, x.inputs["history"][-1]["date"], x.inputs["horizon"]) for x in records}) != 1:
        raise HTTPException(422, "Compare the same sales series, origin date and horizon.")
    return dict(
        analyses=[analysis_view(x) for x in records],
        message="Compare model, dataset source, multiplier and inventory assumptions. Historical accuracy describes the unscaled model.",
    )


@router.get("/analyses/{identifier}/report")
def report(identifier: str, format: str = "json", user=Depends(current_user), db=Depends(get_db)):
    obj = owned_analysis(db, identifier, user)
    if format == "json":
        text = json.dumps(analysis_view(obj), indent=2)
        media = "application/json"
    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        keys = ["date", "forecast", "lower", "upper", "range_samples", "arrival", "ending_stock", "unmet_demand"]
        writer.writerow(keys)
        for row in obj.results["forecast"]:
            writer.writerow([row[k] for k in keys])
        text = output.getvalue()
        media = "text/csv"
    else:
        raise HTTPException(422, "Use json or csv format.")
    return Response(
        text,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="demand-forecast-{obj.id}.{format}"'},
    )


@router.post("/demo", status_code=201)
def demo(idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)):
    def work():
        if db.scalar(select(SalesSeries).where(SalesSeries.user_id == user.id)):
            raise HTTPException(409, "Demo data requires an empty account catalog.")
        obj = SalesSeries(user_id=user.id, sku="SKU-A", name="Wireless keyboard", location="Main store", unit="unit")
        db.add(obj)
        db.flush()
        end = date.today()
        rows = []
        for i in range(180):
            day = end - timedelta(days=179 - i)
            # Deterministic weekly profile, small trend and noise; no private data.
            qty = max(0, [12, 13, 14, 15, 21, 31, 25][day.weekday()] + int(i / 40) + [0, 2, -1, 1, -2][i % 5])
            rows.append(dict(date=str(day), quantity=qty, imputed=False))
        quality = dict(
            count=len(rows), start=rows[0]["date"], end=rows[-1]["date"], imputed_days=0, zero_days=0, warnings=[]
        )
        dataset = Dataset(
            series_id=obj.id,
            source="Synthetic demonstration",
            observations=rows,
            quality=quality,
            missing_policy="reject",
            fingerprint=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
        )
        db.add(dataset)
        db.flush()
        return dict(
            series_id=obj.id,
            dataset_id=dataset.id,
            message="Synthetic daily sales created. No external store was connected.",
        )

    return mutation(db, user, "demo", idempotency_key, {}, work)
