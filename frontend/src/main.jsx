/** Dashboard state coordinates API workflows; forecasting mathematics remains in Python. */
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, setCsrfToken } from "./api";
import AuthScreen from "./components/AuthScreen";
import "./styles.css";
const num = (v) =>
  v == null
    ? "Unavailable"
    : Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 });
const pct = (v) => (v == null ? "Unavailable" : (v * 100).toFixed(1) + "%");
const modelName = {
  auto: "Automatic comparison",
  moving_average: "28-day moving average",
  weekday: "Weekday profile",
  damped_trend: "Damped linear trend",
};
function Field({ label, children }) {
  return (
    <label>
      {label}
      {children}
    </label>
  );
}
function ForecastChart({ record }) {
  const past = record.inputs.history.slice(-60),
    future = record.results.forecast,
    all = [
      ...past.map((x) => x.quantity),
      ...future.map((x) => x.upper ?? x.forecast),
    ],
    max = Math.max(1, ...all) * 1.12,
    count = past.length + future.length;
  const x = (i) => 55 + (i * 810) / (count - 1),
    y = (v) => 240 - (v / max) * 200;
  const actual = past.map((v, i) => `${x(i)},${y(v.quantity)}`).join(" "),
    forecast = [
      `${x(past.length - 1)},${y(past.at(-1).quantity)}`,
      ...future.map((v, i) => `${x(past.length + i)},${y(v.forecast)}`),
    ].join(" ");
  const bands = future
      .map((v, i) => ({ ...v, i }))
      .filter((v) => v.lower != null),
    polygon = [
      ...bands.map((v) => `${x(past.length + v.i)},${y(v.upper)}`),
      ...bands
        .slice()
        .reverse()
        .map((v) => `${x(past.length + v.i)},${y(v.lower)}`),
    ].join(" ");
  return (
    <svg
      viewBox="0 0 900 290"
      role="img"
      aria-label="Historical sales and future forecast with empirical ranges"
    >
      {[0, 0.25, 0.5, 0.75, 1].map((v) => (
        <g key={v}>
          <line
            x1="55"
            x2="870"
            y1={y(max * v)}
            y2={y(max * v)}
            stroke="#e7edf5"
          />
          <text
            x="43"
            y={y(max * v) + 4}
            textAnchor="end"
            fontSize="11"
            fill="#8494a7"
          >
            {num(max * v)}
          </text>
        </g>
      ))}
      <polygon points={polygon} fill="#cceee8" />
      <line
        x1={x(past.length - 1)}
        x2={x(past.length - 1)}
        y1="30"
        y2="240"
        stroke="#93a5bb"
        strokeDasharray="5 5"
      />
      <polyline
        points={actual}
        fill="none"
        stroke="#254e75"
        strokeWidth="2.5"
      />
      <polyline
        points={forecast}
        fill="none"
        stroke="#078c80"
        strokeWidth="3"
        strokeDasharray="6 4"
      />
      <text x="55" y="268" fill="#7c8da2" fontSize="11">
        {past[0].date}
      </text>
      <text
        x={x(past.length - 1)}
        y="268"
        textAnchor="middle"
        fill="#7c8da2"
        fontSize="11"
      >
        Forecast origin
      </text>
      <text x="865" y="268" textAnchor="end" fill="#7c8da2" fontSize="11">
        {future.at(-1).date}
      </text>
    </svg>
  );
}
function App() {
  const [user, U] = useState(null),
    [busy, B] = useState(false),
    [error, E] = useState(""),
    [message, M] = useState(""),
    [tab, T] = useState("Overview"),
    [series, S] = useState([]),
    [selected, P] = useState(""),
    [datasets, D] = useState([]),
    [dataset, K] = useState(""),
    [analyses, A] = useState([]),
    [result, R] = useState(null),
    [preview, V] = useState(null),
    [source, O] = useState("User sales CSV"),
    [policy, Z] = useState("reject"),
    [horizon, H] = useState(30),
    [model, Q] = useState("auto"),
    [multiplier, F] = useState(1),
    [stock, G] = useState(300),
    [arrivals, I] = useState([]),
    [scenario, N] = useState("Base forecast"),
    [checked, C] = useState([]),
    [comparison, J] = useState(null);
  async function task(fn) {
    B(true);
    E("");
    M("");
    try {
      await fn();
    } catch (e) {
      E(e.message);
    } finally {
      B(false);
    }
  }
  const write = (path, body) =>
    api("/v1" + path, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  async function load() {
    const [s, a] = await Promise.all([api("/v1/series"), api("/v1/analyses")]);
    S(s);
    A(a);
    P((old) => old || s[0]?.id || "");
  }
  useEffect(() => {
    api("/auth/session")
      .then(async (s) => {
        U(s.user);
        setCsrfToken(s.csrf_token);
        await load();
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!selected) {
      D([]);
      K("");
      return;
    }
    let active = true;
    api("/v1/series/" + selected + "/datasets")
      .then((d) => {
        if (active) {
          D(d);
          K(d[0]?.id || "");
        }
      })
      .catch((e) => {
        if (active) E(e.message);
      });
    return () => {
      active = false;
    };
  }, [selected]);
  async function auth(registering, body) {
    await task(async () => {
      const s = await api("/auth/" + (registering ? "register" : "login"), {
        method: "POST",
        body: JSON.stringify(body),
      });
      U(s.user);
      setCsrfToken(s.csrf_token);
      await load();
    });
  }
  async function run() {
    await task(async () => {
      const a = await write("/series/" + selected + "/analyses", {
        dataset_id: dataset,
        scenario_name: scenario,
        horizon: Number(horizon),
        model,
        demand_multiplier: Number(multiplier),
        starting_stock: Number(stock),
        arrivals,
      });
      R(a);
      await load();
      T("Overview");
    });
  }
  const current = datasets.find((x) => x.id === dataset),
    activeSeries = series.find((x) => x.id === selected);
  if (!user) return <AuthScreen onSubmit={auth} busy={busy} error={error} />;
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <span>◴</span>
          <div>
            DemandIQ<small>Sales & demand forecasting</small>
          </div>
        </div>
        <nav>
          {[
            "Overview",
            "Sales data",
            "Forecast setup",
            "Stock planning",
            "Scenarios & reports",
          ].map((t) => (
            <button
              className={tab === t ? "active" : ""}
              key={t}
              onClick={() => T(t)}
            >
              {t}
            </button>
          ))}
        </nav>
        <div className="account">
          <small>{user.email}</small>
          <button
            onClick={() =>
              task(async () => {
                await api("/auth/logout", { method: "POST" });
                U(null);
                setCsrfToken("");
              })
            }
          >
            Sign out
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">PLANNING / {tab.toUpperCase()}</p>
            <h1>
              {tab === "Overview"
                ? "See demand before you make your next move"
                : tab}
            </h1>
            <p className="muted">
              Historical validation, clear assumptions, and forecasts you can
              review.
            </p>
          </div>
          <Field label="Active sales series">
            <select
              aria-label="Active sales series"
              value={selected}
              onChange={(e) => P(e.target.value)}
            >
              <option value="">Select a product and location</option>
              {series.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.location}
                </option>
              ))}
            </select>
          </Field>
        </header>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {message && (
          <p className="success" role="status">
            {message}
          </p>
        )}
        {busy && (
          <p className="muted" role="status">
            Calculating or saving…
          </p>
        )}
        {tab === "Overview" && (
          <>
            <section className="card">
              <div className="section-head">
                <div>
                  <h2>Demand outlook</h2>
                  <p className="muted">
                    {activeSeries?.name || "Choose a product series"} ·{" "}
                    {activeSeries?.location || "Create your first dataset"}
                  </p>
                </div>
                <div className="controls">
                  {!series.length ? (
                    <button
                      disabled={busy}
                      onClick={() =>
                        task(async () => {
                          const d = await write("/demo");
                          await load();
                          P(d.series_id);
                          M(d.message);
                        })
                      }
                    >
                      Load demo data
                    </button>
                  ) : (
                    <button disabled={busy || !dataset} onClick={run}>
                      Run demand forecast
                    </button>
                  )}
                  <button
                    className="text-button"
                    onClick={() => T("Forecast setup")}
                  >
                    Edit assumptions
                  </button>
                </div>
              </div>
            </section>
            {result ? (
              <>
                <div className="metrics">
                  {[
                    [
                      "Forecast units",
                      num(result.results.summary.total_forecast),
                    ],
                    [
                      "Daily average",
                      num(result.results.summary.daily_average),
                    ],
                    ["Historical MAE", num(result.results.validation.mae)],
                    [
                      "First stock shortage",
                      result.results.summary.first_shortage_date ||
                        "None in this scenario",
                    ],
                  ].map(([k, v]) => (
                    <div className="metric" key={k}>
                      <small>{k}</small>
                      <strong>{v}</strong>
                    </div>
                  ))}
                </div>
                <section className="card">
                  <div className="section-head">
                    <div>
                      <h2>Historical sales & future demand</h2>
                      <p className="muted">
                        {result.inputs.series.name} · saved{" "}
                        {result.inputs.scenario_name} · {result.inputs.horizon}{" "}
                        daily estimates
                      </p>
                    </div>
                    <span className="pill">
                      {modelName[result.results.selected_model]}
                    </span>
                  </div>
                  <div className="legend">
                    <span>
                      <i className="actual" />
                      Observed sales
                    </span>
                    <span>
                      <i className="future" />
                      Forecast
                    </span>
                    <span>
                      <i className="range" />
                      Empirical range
                    </span>
                  </div>
                  <ForecastChart record={result} />
                  <p className="muted">
                    Shading uses lead-specific historical errors. It has no
                    guaranteed future 80% coverage; unavailable ranges are not
                    filled.
                  </p>
                </section>
                <div className="grid two">
                  <section className="card">
                    <h2>Model comparison</h2>
                    <p className="muted">
                      Selection uses historical prefixes before the final
                      evaluation segment.
                    </p>
                    <table>
                      <thead>
                        <tr>
                          <th>Candidate</th>
                          <th>Selection MAE</th>
                          <th>Choice</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.results.candidate_scores.length ? (
                          result.results.candidate_scores.map((x) => (
                            <tr key={x.model}>
                              <td>{modelName[x.model]}</td>
                              <td>{num(x.mae)}</td>
                              <td>
                                {x.model === result.results.selected_model ? (
                                  <span className="pill">Selected</span>
                                ) : (
                                  "Compared"
                                )}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan="3">
                              Manual model or short-history fallback
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </section>
                  <section className="card">
                    <h2>Validation & data context</h2>
                    <p>
                      Final rolling one-day RMSE{" "}
                      <b>{num(result.results.validation.rmse)}</b> · WAPE{" "}
                      <b>{pct(result.results.validation.wape)}</b>
                    </p>
                    <p>
                      {result.results.validation.samples} evaluation dates ·{" "}
                      {result.results.diagnostics.history_days} history days
                    </p>
                    <p>Source: {result.inputs.source}</p>
                    <p className="muted">
                      Metrics describe the unscaled model. They are not a
                      measured accuracy score for next month's total.
                    </p>
                  </section>
                </div>
                <section className="card">
                  <h2>Interpretation notes</h2>
                  {[
                    ...result.inputs.quality.warnings,
                    ...result.results.warnings,
                  ].map((w, i) => (
                    <p className="muted" key={i}>
                      {w}
                    </p>
                  ))}
                </section>
              </>
            ) : (
              <section className="empty card">
                <h2>Start with daily sales, then evaluate</h2>
                <p>
                  Load synthetic demo data or create a product series and import
                  a CSV. Review the history before running a forecast.
                </p>
              </section>
            )}
          </>
        )}
        {tab === "Sales data" && (
          <>
            <section className="card">
              <h2>Create a sales series</h2>
              <p className="muted">
                Keep each product and location in its own daily time series.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = e.currentTarget,
                    body = Object.fromEntries(new FormData(form));
                  task(async () => {
                    const s = await write("/series", body);
                    P(s.id);
                    await load();
                    form.reset();
                    M("Sales series created. Add a dataset below.");
                  });
                }}
              >
                <div className="grid four">
                  {[
                    ["SKU", "sku", ""],
                    ["Product name", "name", ""],
                    ["Location", "location", "Main store"],
                    ["Unit", "unit", "unit"],
                  ].map(([label, name, value]) => (
                    <Field label={label} key={name}>
                      <input
                        aria-label={label}
                        name={name}
                        defaultValue={value}
                        required
                      />
                    </Field>
                  ))}
                </div>
                <button disabled={busy}>Create sales series</button>
              </form>
            </section>
            <section className="card">
              <h2>Review and import daily sales</h2>
              <p>
                CSV header: <code>date,quantity</code>. Aggregate orders by day
                before importing; include explicit zero-sales days.
              </p>
              <div className="grid three">
                <Field label="Dataset source">
                  <input
                    aria-label="Dataset source"
                    value={source}
                    onChange={(e) => O(e.target.value)}
                  />
                </Field>
                <Field label="Missing-day policy">
                  <select
                    aria-label="Missing-day policy"
                    value={policy}
                    onChange={(e) => Z(e.target.value)}
                  >
                    <option value="reject">Reject missing dates</option>
                    <option value="zero_fill">
                      Fill missing dates with zero
                    </option>
                  </select>
                </Field>
                <Field label="Sales CSV">
                  <input
                    aria-label="Sales CSV"
                    type="file"
                    accept=".csv,text/csv"
                    onChange={(e) => {
                      const file = e.target.files[0];
                      if (file)
                        task(async () => {
                          if (file.size > 200000)
                            throw Error("Maximum CSV size is 200 KB.");
                          V(
                            await write("/imports/sales/preview", {
                              csv_text: await file.text(),
                            }),
                          );
                        });
                    }}
                  />
                </Field>
              </div>
              {policy === "zero_fill" && (
                <p className="warning">
                  Use zero-filling only when the source is complete and missing
                  dates mean zero sales.
                </p>
              )}
              {preview && (
                <div className="import-preview">
                  <p>{preview.rows.length} valid observations</p>
                  {preview.errors.map((x, i) => (
                    <p className="error" key={i}>
                      Row {x.row}: {x.message}
                    </p>
                  ))}
                  <button
                    disabled={busy || !selected || !preview.valid}
                    onClick={() =>
                      task(async () => {
                        const d = await write(
                          "/series/" + selected + "/datasets",
                          {
                            source,
                            missing_policy: policy,
                            observations: preview.rows,
                          },
                        );
                        const list = await api(
                          "/v1/series/" + selected + "/datasets",
                        );
                        D(list);
                        K(d.id);
                        V(null);
                        M(
                          "Immutable dataset saved. Forecasts will start after its last observation.",
                        );
                      })
                    }
                  >
                    Save reviewed dataset
                  </button>
                </div>
              )}
            </section>
            <section className="card">
              <h2>Dataset versions</h2>
              {datasets.map((d) => (
                <div className="saved" key={d.id}>
                  <div>
                    <b>{d.source}</b>
                    <small>
                      {d.quality.start} to {d.quality.end} · {d.quality.count}{" "}
                      days · {d.quality.imputed_days} zero-filled ·{" "}
                      {d.quality.zero_days} zero-sale days
                    </small>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => {
                      K(d.id);
                      T("Forecast setup");
                    }}
                  >
                    Use dataset
                  </button>
                </div>
              ))}
            </section>
          </>
        )}
        {tab === "Forecast setup" && (
          <section className="card">
            <h2>Forecast assumptions</h2>
            <div className="grid three">
              <Field label="Dataset version">
                <select
                  aria-label="Dataset version"
                  value={dataset}
                  onChange={(e) => K(e.target.value)}
                >
                  <option value="">Select dataset</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.source} · {d.quality.end}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Scenario name">
                <input
                  aria-label="Scenario name"
                  value={scenario}
                  onChange={(e) => N(e.target.value)}
                />
              </Field>
              <Field label="Forecast horizon days">
                <input
                  aria-label="Forecast horizon days"
                  type="number"
                  min="1"
                  max="90"
                  value={horizon}
                  onChange={(e) => H(e.target.value)}
                />
              </Field>
              <Field label="Forecast model">
                <select
                  aria-label="Forecast model"
                  value={model}
                  onChange={(e) => Q(e.target.value)}
                >
                  {Object.entries(modelName).map(([key, name]) => (
                    <option key={key} value={key}>
                      {name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Demand multiplier">
                <input
                  aria-label="Demand multiplier"
                  type="number"
                  min="0"
                  max="3"
                  step=".05"
                  value={multiplier}
                  onChange={(e) => F(e.target.value)}
                />
              </Field>
              <Field label="Starting stock">
                <input
                  aria-label="Starting stock"
                  type="number"
                  min="0"
                  step="1"
                  value={stock}
                  onChange={(e) => G(e.target.value)}
                />
              </Field>
            </div>
            {current && (
              <p className="muted">
                Forecast origin: {current.quality.end}. Horizon begins the next
                day. {current.quality.count} calendar days available.
              </p>
            )}
            <p>
              Automatic comparison requires 56 days. Weekday profile requires
              28. Shorter histories use the moving-average baseline. This
              release models weekday patterns, not annual seasonality or
              holidays.
            </p>
            <p className="muted">
              A multiplier of 1.20 is your hypothetical 20% demand increase.
              Validation remains based on the original historical model.
            </p>
            <button disabled={busy || !dataset || !selected} onClick={run}>
              Analyze and save forecast
            </button>
          </section>
        )}
        {tab === "Stock planning" && (
          <>
            <section className="card">
              <h2>Stock planning assumptions</h2>
              <p>
                Arrival quantities become available at the start of the selected
                day. Demand then consumes stock. Unmet demand is counted as lost
                units and does not carry forward as backlog.
              </p>
              <Field label="Planning starting stock">
                <input
                  aria-label="Planning starting stock"
                  type="number"
                  min="0"
                  value={stock}
                  onChange={(e) => G(e.target.value)}
                />
              </Field>
              {arrivals.map((a, i) => (
                <div className="grid three" key={i}>
                  <Field label={"Arrival date " + (i + 1)}>
                    <input
                      aria-label={"Arrival date " + (i + 1)}
                      type="date"
                      value={a.date}
                      onChange={(e) =>
                        I(
                          arrivals.map((v, j) =>
                            j === i ? { ...v, date: e.target.value } : v,
                          ),
                        )
                      }
                    />
                  </Field>
                  <Field label={"Arrival quantity " + (i + 1)}>
                    <input
                      aria-label={"Arrival quantity " + (i + 1)}
                      type="number"
                      min="1"
                      value={a.quantity}
                      onChange={(e) =>
                        I(
                          arrivals.map((v, j) =>
                            j === i
                              ? { ...v, quantity: Number(e.target.value) }
                              : v,
                          ),
                        )
                      }
                    />
                  </Field>
                  <button
                    className="text-button"
                    onClick={() => I(arrivals.filter((_, j) => j !== i))}
                  >
                    Remove arrival {i + 1}
                  </button>
                </div>
              ))}
              <button
                className="text-button"
                disabled={arrivals.length >= 90 || !current}
                onClick={() => {
                  const date = current
                    ? new Date(current.quality.end + "T00:00:00Z")
                    : new Date();
                  date.setUTCDate(date.getUTCDate() + 7);
                  I([
                    ...arrivals,
                    { date: date.toISOString().slice(0, 10), quantity: 200 },
                  ]);
                }}
              >
                Add scheduled arrival
              </button>
              <button disabled={busy || !dataset} onClick={run}>
                Save planning scenario
              </button>
            </section>
            {result && (
              <section className="card">
                <h2>Saved stock projection</h2>
                <p>
                  Forecast {num(result.results.summary.total_forecast)} units ·
                  projected unmet {num(result.results.summary.total_unmet)} ·
                  ending stock {num(result.results.summary.ending_stock)}
                </p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {[
                          "Date",
                          "Demand",
                          "Arrival",
                          "Ending stock",
                          "Unmet units",
                        ].map((x) => (
                          <th key={x}>{x}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.results.forecast.map((x) => (
                        <tr key={x.date}>
                          <td>{x.date}</td>
                          <td>{num(x.forecast)}</td>
                          <td>{num(x.arrival)}</td>
                          <td>{num(x.ending_stock)}</td>
                          <td>{num(x.unmet_demand)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="muted">
                  This is the saved scenario's projection, not live InventoryIQ
                  stock. The inventory connector is a documented future
                  integration.
                </p>
              </section>
            )}
          </>
        )}
        {tab === "Scenarios & reports" && (
          <section className="card">
            <h2>Saved forecasts and comparisons</h2>
            <p className="muted">
              Compare the same series, origin date and horizon. Every saved
              record preserves its dataset and assumptions.
            </p>
            {analyses.map((a) => (
              <div className="saved" key={a.id}>
                <input
                  type="checkbox"
                  aria-label={"Compare " + a.inputs.scenario_name}
                  checked={checked.includes(a.id)}
                  onChange={(e) =>
                    C(
                      e.target.checked
                        ? [...checked, a.id]
                        : checked.filter((x) => x !== a.id),
                    )
                  }
                />
                <div>
                  <b>{a.inputs.scenario_name}</b>
                  <small>
                    {a.inputs.series.name} · origin{" "}
                    {a.inputs.history.at(-1).date} · {a.inputs.horizon} days ·{" "}
                    {modelName[a.results.selected_model]}
                  </small>
                </div>
                <button
                  className="text-button"
                  onClick={() => {
                    R(a);
                    T("Overview");
                  }}
                >
                  Open forecast
                </button>
                <a href={"/api/v1/analyses/" + a.id + "/report"}>JSON report</a>
                <a href={"/api/v1/analyses/" + a.id + "/report?format=csv"}>
                  CSV report
                </a>
              </div>
            ))}
            <button
              disabled={busy || checked.length < 2 || checked.length > 10}
              onClick={() =>
                task(async () =>
                  J(await write("/comparisons", { analysis_ids: checked })),
                )
              }
            >
              Compare selected forecasts
            </button>
            {comparison && (
              <div>
                <h3>Forecast comparison</h3>
                <p className="muted">{comparison.message}</p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Scenario</th>
                        <th>Forecast units</th>
                        <th>Unmet units</th>
                        <th>Historical MAE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparison.analyses.map((a) => (
                        <tr key={a.id}>
                          <td>{a.inputs.scenario_name}</td>
                          <td>{num(a.results.summary.total_forecast)}</td>
                          <td>{num(a.results.summary.total_unmet)}</td>
                          <td>{num(a.results.validation.mae)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>
        )}
        <footer>
          DemandIQ v1.0 · Daily sales forecasts and saved stock scenarios
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
