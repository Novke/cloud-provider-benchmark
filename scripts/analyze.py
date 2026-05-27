"""Statisticka analiza benchmark rezultata.

Phase 3 deliverable. Cita iz DuckDB-a koji puni `aggregate.py`, generise:
  * Summary tabele sa medianom + p95 + p99 + 95% CI
  * Mann-Whitney U test za par-by-par poredjenje provajdera (non-parametric)
  * Kruskal-Wallis test za 4-way poredjenje (svi provajderi istovremeno)
  * Box plots latency distribucija po provajderima
  * Line plots latency over time (dnevno)
  * Heatmaps time-of-day × provider
  * LaTeX tabele za rad

Format: `# %%` cell markeri rade kao Jupyter notebook (jupytext/VSCode) ili kao
obican Python skript (`python scripts/analyze.py`).

Pre prvog koriscenja:
    pip install -r scripts/requirements.txt
    python scripts/aggregate.py
"""

# %% [markdown]
# # Cloud Provider Benchmark — Analiza
#
# Cita `benchmark.duckdb` (proizveden od `scripts/aggregate.py`) i generise
# statistike + grafikone za naucni rad.

# %%
from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# Konfiguracija
DB_PATH = "benchmark.duckdb"
OUTPUT_DIR = Path("k6/results/_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# %%
conn = duckdb.connect(DB_PATH, read_only=True)
df = conn.execute("SELECT * FROM runs WHERE NOT is_warmup").fetchdf()
print(f"Loaded {len(df)} measurement runs (warmups excluded)")
print(df[["provider", "arch", "scenario"]].value_counts().to_string())

# %% [markdown]
# ## Coverage matrix
#
# Koliko mjerenja imamo po provajderu / arhitekturi / scenariju? N >= 10 je
# preporuceni minimum za stabilan p95 i Mann-Whitney U test (vidi metodologija).

# %%
coverage = (
    df.groupby(["provider", "arch", "scenario"])
    .size()
    .reset_index(name="N")
    .pivot_table(index=["arch", "scenario"], columns="provider", values="N", fill_value=0)
)
print(coverage.to_string())

# %% [markdown]
# ## Summary tabela sa 95% CI
#
# Za svaku (provider, arch, scenario, metric) kombinaciju:
#   * Median je primarna statistika (latency je heavy-tailed, mean je biased)
#   * P95, P99 — tail latency
#   * 95% CI median-a kroz bootstrap (1000 iteracija)


# %%
def bootstrap_ci(values: np.ndarray, statistic, n_resamples: int = 1000, ci: float = 0.95) -> tuple[float, float]:
    """Bootstrap CI za bilo koju statistiku (median, p95, ...)."""
    if len(values) < 3:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(42)
    samples = rng.choice(values, size=(n_resamples, len(values)), replace=True)
    stats_dist = np.array([statistic(s) for s in samples])
    alpha = (1 - ci) / 2
    return (float(np.quantile(stats_dist, alpha)), float(np.quantile(stats_dist, 1 - alpha)))


def summarize(group: pd.DataFrame, metric: str) -> pd.Series:
    vals = group[metric].dropna().to_numpy()
    if len(vals) == 0:
        return pd.Series({"N": 0, "median": np.nan, "p95": np.nan, "p99": np.nan, "ci_lo": np.nan, "ci_hi": np.nan})
    med = float(np.median(vals))
    ci_lo, ci_hi = bootstrap_ci(vals, np.median)
    return pd.Series({
        "N": len(vals),
        "median": med,
        "p95": float(np.quantile(vals, 0.95)),
        "p99": float(np.quantile(vals, 0.99)),
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
    })


# Glavna metrika po scenariju
METRIC_BY_SCENARIO = {
    "mixed": "ttfb_p95",
    "low-traffic": "ttfb_p95",
    "high-traffic": "ttfb_p95",
    "heavy-compute": "ttfb_p95",
    "io-native": "latency_p95",
    "io-neutral": "latency_p95",
    "cold-start": "first_request_avg",
}

summaries = []
for (provider, arch, scenario), group in df.groupby(["provider", "arch", "scenario"]):
    metric = METRIC_BY_SCENARIO.get(scenario)
    if not metric or metric not in group.columns:
        continue
    s = summarize(group, metric)
    s["provider"] = provider
    s["arch"] = arch
    s["scenario"] = scenario
    s["metric"] = metric
    summaries.append(s)

summary_df = pd.DataFrame(summaries)[["provider", "arch", "scenario", "metric", "N", "median", "ci_lo", "ci_hi", "p95", "p99"]]
print(summary_df.to_string(index=False))
summary_df.to_csv(OUTPUT_DIR / "summary.csv", index=False)

# %% [markdown]
# ## Mann-Whitney U — par-by-par poredjenje provajdera
#
# Za svaki (arch, scenario) par, test-iramo da li distribucije latencije
# razlicitih provajdera dolaze iz iste populacije. Non-parametric — robusan na
# heavy tails (validno za latency podatke, t-test nije).
#
# p < 0.05 => odbacujemo null hipotezu (distribucije se razlikuju).


# %%
def mannwhitney_pairs(df_sub: pd.DataFrame, metric: str) -> pd.DataFrame:
    providers = sorted(df_sub["provider"].unique())
    rows = []
    for i, p1 in enumerate(providers):
        for p2 in providers[i + 1:]:
            v1 = df_sub[df_sub["provider"] == p1][metric].dropna().to_numpy()
            v2 = df_sub[df_sub["provider"] == p2][metric].dropna().to_numpy()
            if len(v1) < 3 or len(v2) < 3:
                continue
            u, p_value = stats.mannwhitneyu(v1, v2, alternative="two-sided")
            rows.append({
                "provider_1": p1,
                "provider_2": p2,
                "N_1": len(v1),
                "N_2": len(v2),
                "median_1": float(np.median(v1)),
                "median_2": float(np.median(v2)),
                "U": float(u),
                "p_value": float(p_value),
                "significant_at_0.05": p_value < 0.05,
            })
    return pd.DataFrame(rows)


mw_results = []
for (arch, scenario), group in df.groupby(["arch", "scenario"]):
    metric = METRIC_BY_SCENARIO.get(scenario)
    if not metric or metric not in group.columns:
        continue
    res = mannwhitney_pairs(group, metric)
    if res.empty:
        continue
    res["arch"] = arch
    res["scenario"] = scenario
    res["metric"] = metric
    mw_results.append(res)

if mw_results:
    mw_df = pd.concat(mw_results, ignore_index=True)
    mw_df = mw_df[["arch", "scenario", "metric", "provider_1", "provider_2", "N_1", "N_2", "median_1", "median_2", "U", "p_value", "significant_at_0.05"]]
    print(mw_df.to_string(index=False))
    mw_df.to_csv(OUTPUT_DIR / "mannwhitney_pairs.csv", index=False)
else:
    print("Nedovoljno podataka za Mann-Whitney")

# %% [markdown]
# ## Kruskal-Wallis — 4-way poredjenje
#
# Test za istovremeno poredjenje > 2 grupe (svih provajdera u istom arch x scenario).

# %%
kw_results = []
for (arch, scenario), group in df.groupby(["arch", "scenario"]):
    metric = METRIC_BY_SCENARIO.get(scenario)
    if not metric or metric not in group.columns:
        continue
    samples = []
    providers = []
    for provider, subgroup in group.groupby("provider"):
        vals = subgroup[metric].dropna().to_numpy()
        if len(vals) >= 3:
            samples.append(vals)
            providers.append(provider)
    if len(samples) < 2:
        continue
    h, p_value = stats.kruskal(*samples)
    kw_results.append({
        "arch": arch,
        "scenario": scenario,
        "metric": metric,
        "providers": ",".join(providers),
        "groups": len(samples),
        "H": float(h),
        "p_value": float(p_value),
        "significant_at_0.05": p_value < 0.05,
    })

if kw_results:
    kw_df = pd.DataFrame(kw_results)
    print(kw_df.to_string(index=False))
    kw_df.to_csv(OUTPUT_DIR / "kruskal_wallis.csv", index=False)

# %% [markdown]
# ## Box plots — latency distribucija po provajderima
#
# Po jedan plot za svaki (arch, scenario). X-osa = provajderi, Y-osa = metrika.
# Visually pokazuje median + IQR + outlier-e.

# %%
for (arch, scenario), group in df.groupby(["arch", "scenario"]):
    metric = METRIC_BY_SCENARIO.get(scenario)
    if not metric or metric not in group.columns:
        continue
    data = []
    labels = []
    for provider, sub in group.groupby("provider"):
        vals = sub[metric].dropna().to_numpy()
        if len(vals) > 0:
            data.append(vals)
            labels.append(provider)
    if len(data) < 2:
        continue

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot(data, tick_labels=labels)
    ax.set_title(f"{arch} / {scenario} — {metric}")
    ax.set_ylabel(f"{metric} (ms)")
    ax.set_xlabel("provider")
    ax.grid(True, alpha=0.3)
    out = OUTPUT_DIR / f"boxplot_{arch}_{scenario}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"Saved {out}")

# %% [markdown]
# ## Line plot — latency over time
#
# X-osa: timestamp_utc. Y-osa: metrika. Jedna linija po provajderu. Detektuje
# diurnal / weekly trendove (npr. AWS sporiji u peak hours).

# %%
for (arch, scenario), group in df.groupby(["arch", "scenario"]):
    metric = METRIC_BY_SCENARIO.get(scenario)
    if not metric or metric not in group.columns:
        continue
    g = group.dropna(subset=[metric, "timestamp_utc"]).sort_values("timestamp_utc")
    if g["provider"].nunique() < 2 or len(g) < 6:
        continue

    fig, ax = plt.subplots(figsize=(10, 4))
    for provider, sub in g.groupby("provider"):
        ax.plot(sub["timestamp_utc"], sub[metric], marker="o", linestyle="-", label=provider, alpha=0.7)
    ax.set_title(f"{arch} / {scenario} — {metric} kroz vreme")
    ax.set_ylabel(f"{metric} (ms)")
    ax.set_xlabel("timestamp (UTC)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    out = OUTPUT_DIR / f"timeline_{arch}_{scenario}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"Saved {out}")

# %% [markdown]
# ## Heatmap — time-of-day × provider
#
# Pokazuje da li latency varira po slot-u dana (morning/afternoon/evening/night).
# Korisno za "AWS je 30% sporiji u afternoon peak" tip nalaza.

# %%
slot_order = ["morning", "afternoon", "evening", "night"]

for (arch, scenario), group in df.groupby(["arch", "scenario"]):
    metric = METRIC_BY_SCENARIO.get(scenario)
    if not metric or metric not in group.columns:
        continue
    pivot = (
        group.dropna(subset=[metric, "time_of_day_slot"])
        .groupby(["time_of_day_slot", "provider"])[metric]
        .median()
        .unstack("provider")
    )
    if pivot.empty or pivot.shape[0] < 2 or pivot.shape[1] < 2:
        continue
    pivot = pivot.reindex([s for s in slot_order if s in pivot.index])

    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title(f"{arch} / {scenario} — median {metric} po time-of-day")
    fig.colorbar(im, ax=ax, label="ms")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.0f}", ha="center", va="center", color="black", fontsize=8)
    out = OUTPUT_DIR / f"heatmap_{arch}_{scenario}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"Saved {out}")

# %% [markdown]
# ## LaTeX tabele za rad
#
# Generise gotov `.tex` snippet sa summary tabelom — direktno paste-uje u rad.

# %%
def to_latex(df_in: pd.DataFrame, caption: str, label: str, fmt: dict[str, str] | None = None) -> str:
    if df_in.empty:
        return ""
    fmt = fmt or {}
    cols = list(df_in.columns)
    col_spec = "l" * len(cols)
    lines = [
        r"\begin{table}[ht]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        r"\hline",
        " & ".join(cols) + r" \\",
        r"\hline",
    ]
    for _, row in df_in.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if isinstance(v, float):
                cells.append(fmt.get(c, "{:.1f}").format(v))
            elif isinstance(v, (np.integer, int)):
                cells.append(str(int(v)))
            elif v is None or (isinstance(v, float) and np.isnan(v)):
                cells.append("--")
            else:
                cells.append(str(v).replace("_", r"\_"))
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


tex_summary = to_latex(
    summary_df.copy(),
    caption="Median latencija sa 95\\% CI po provajderu i scenariju.",
    label="tab:summary",
)
(OUTPUT_DIR / "summary.tex").write_text(tex_summary, encoding="utf-8")
print(f"LaTeX summary saved: {OUTPUT_DIR / 'summary.tex'}")

# %% [markdown]
# ## Output overview
#
# Sve datoteke izlazne analize:

# %%
for p in sorted(OUTPUT_DIR.glob("*")):
    print(p)

conn.close()
