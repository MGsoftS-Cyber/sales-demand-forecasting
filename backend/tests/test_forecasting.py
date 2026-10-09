from datetime import date, timedelta
from uuid import uuid4
import pytest
from app.engine import evaluate
from app.imports import normalize, preview_sales
from app.schemas import Observation


def inputs(n=180, pattern=None, **overrides):
    start = date.today() - timedelta(days=n - 1)
    history = [
        dict(
            date=str(start + timedelta(days=i)),
            quantity=pattern(i, start + timedelta(days=i)) if pattern else 10,
            imputed=False,
        )
        for i in range(n)
    ]
    return dict(
        history=history, model="auto", horizon=30, demand_multiplier=1, starting_stock=100, arrivals=[], **overrides
    )


def test_constant_forecast():
    r = evaluate(inputs())
    assert r["summary"]["total_forecast"] == 300
    assert r["validation"]["mae"] == 0
    assert r["forecast"][0]["lower"] == 10
    assert r["selected_model"] == "moving_average"


def test_weekday_selection():
    d = inputs(pattern=lambda i, day: [1, 2, 3, 4, 5, 10, 8][day.weekday()])
    r = evaluate(d)
    assert r["selected_model"] == "weekday"
    assert r["validation"]["mae"] == 0
    expected = [1, 2, 3, 4, 5, 10, 8][(date.today() + timedelta(days=1)).weekday()]
    assert r["forecast"][0]["forecast"] == expected


def test_trend_clamps_nonnegative():
    d = inputs(pattern=lambda i, day: max(0, 200 - i))
    d["model"] = "damped_trend"
    r = evaluate(d)
    assert all(x["forecast"] >= 0 for x in r["forecast"])


def test_training_prefix_has_no_future():
    d = inputs(90, pattern=lambda i, day: 10 if i < 80 else 10000)
    r = evaluate(d)
    origin = r["backtest"][4]  # day80, first extreme value
    assert origin["actual"] == 10000
    assert origin["predicted"] == pytest.approx(10)


def test_short_history():
    r = evaluate(inputs(14))
    assert r["validation"]["mae"] is None
    assert all(x["lower"] is None for x in r["forecast"])
    d = inputs(14)
    d["model"] = "weekday"
    with pytest.raises(ValueError):
        evaluate(d)


def test_stock_arrival_timing():
    d = inputs()
    d["horizon"] = 3
    d["starting_stock"] = 5
    d["arrivals"] = [dict(date=str(date.today() + timedelta(days=2)), quantity=20)]
    r = evaluate(d)
    assert r["forecast"][0]["unmet_demand"] == 5
    assert r["forecast"][1]["ending_stock"] == 10
    assert r["forecast"][2]["ending_stock"] == 0
    assert r["summary"]["total_unmet"] == 5


def test_scenario_multiplier():
    d = inputs()
    d["demand_multiplier"] = 1.5
    r = evaluate(d)
    assert r["summary"]["total_forecast"] == 450
    assert r["validation"]["mae"] == 0


def test_outside_arrival_rejected():
    d = inputs()
    d["arrivals"] = [dict(date=str(date.today()), quantity=20)]
    with pytest.raises(ValueError):
        evaluate(d)


def test_zero_demand_wape():
    r = evaluate(inputs(pattern=lambda i, day: 0))
    assert r["validation"]["wape"] is None
    assert r["summary"]["total_forecast"] == 0
    assert r["summary"]["first_shortage_date"] is None


def test_normalize_reject_zero_fill():
    rows = [Observation(date=date.today() - timedelta(days=i), quantity=1) for i in range(15) if i != 7]
    with pytest.raises(ValueError):
        normalize(rows, "reject")
    data, quality = normalize(rows, "zero_fill")
    assert quality["imputed_days"] == 1
    assert data[7]["quantity"] == 0 and data[7]["imputed"]


def test_normalize_duplicate():
    row = Observation(date=date.today(), quantity=0)
    with pytest.raises(ValueError):
        normalize([row, row], "reject")


@pytest.mark.parametrize(
    "text", ["wrong", "date,quantity\n2026-01-01,-1", "date,quantity\n2026-01-01,NaN", "date,quantity\n2999-01-01,1"]
)
def test_csv_bad(text):
    assert not preview_sales(text)["valid"]


def write(client, path, body=None, key=None):
    return client.post("/api/v1" + path, json=body, headers={"Idempotency-Key": key or uuid4().hex})


def register(client, email="owner@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "test-long-password"})
    assert r.status_code == 201
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]


def setup(client):
    register(client)
    demo = write(client, "/demo").json()
    return demo


def run(client, demo, **change):
    data = dict(dataset_id=demo["dataset_id"], starting_stock=100, **change)
    return write(client, "/series/" + demo["series_id"] + "/analyses", data)


def test_demo_forecast_reports(client):
    d = setup(client)
    a = run(client, d)
    assert a.status_code == 201
    result = a.json()
    assert len(result["results"]["forecast"]) == 30
    assert client.get("/api/v1/analyses").json()[0]["id"] == result["id"]
    assert client.get("/api/v1/analyses/" + result["id"] + "/report").status_code == 200
    assert "ending_stock" in client.get("/api/v1/analyses/" + result["id"] + "/report?format=csv").text


def test_forecast_replay_conflict(client):
    d = setup(client)
    path = "/series/" + d["series_id"] + "/analyses"
    body = {"dataset_id": d["dataset_id"]}
    a = write(client, path, body, key="same").json()
    assert write(client, path, body, key="same").json()["id"] == a["id"]
    body["horizon"] = 20
    assert write(client, path, body, key="same").status_code == 409


def test_dataset_duplicate_and_snapshot(client):
    d = setup(client)
    a = run(client, d).json()
    history = inputs(30)["history"]
    observations = [{k: x[k] for k in ["date", "quantity"]} for x in history]
    body = {"source": "Test", "observations": observations, "missing_policy": "reject"}
    path = "/series/" + d["series_id"] + "/datasets"
    one = write(client, path, body).json()
    two = write(client, path, body).json()
    assert one["id"] == two["id"]
    assert client.get("/api/v1/analyses").json()[0]["inputs"]["history"] == a["inputs"]["history"]


def test_dataset_foreign_account(client):
    d = setup(client)
    a = run(client, d).json()
    client.post("/api/auth/logout")
    register(client, "other@example.com")
    assert client.get("/api/v1/series").json() == []
    assert client.get("/api/v1/series/" + d["series_id"] + "/datasets").status_code == 404
    assert run(client, d).status_code == 404
    assert client.get("/api/v1/analyses/" + a["id"] + "/report").status_code == 404


def test_comparison_contract(client):
    d = setup(client)
    a = run(client, d).json()
    b = run(client, d, demand_multiplier=1.2).json()
    assert write(client, "/comparisons", {"analysis_ids": [a["id"], b["id"]]}).status_code == 200
    c = run(client, d, horizon=15).json()
    assert write(client, "/comparisons", {"analysis_ids": [a["id"], c["id"]]}).status_code == 422


def test_schema_validation(client):
    d = setup(client)
    assert run(client, d, horizon=91).status_code == 422
    assert run(client, d, demand_multiplier=-1).status_code == 422
    assert run(client, d, model="unknown").status_code == 422
    assert (
        client.post("/api/v1/series/" + d["series_id"] + "/analyses", json={"dataset_id": d["dataset_id"]}).status_code
        == 422
    )


def test_csrf_and_auth(client):
    assert client.get("/api/v1/series").status_code == 401
    register(client)
    client.headers.pop("X-CSRF-Token")
    assert write(client, "/series", {"sku": "A", "name": "A"}).status_code == 403
