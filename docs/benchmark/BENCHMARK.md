# Benchmark Study: Ω-QFM vs. Baselines on 30 Public Repositories

**Working paper (reproducible artifact)**  
Omega Quality Field Manifold — empirical comparison against McCabe-only and optional SonarCloud.

---

## Abstract

We evaluate whether the Ω composite index (entropy, cyclomatic complexity, nesting, coupling, compression) aligns with **curator-assigned reference grades** on 30 public GitHub repositories, compared to a **cyclomatic-only** baseline on the same files. Reference grades are explicit consensus proxies—not a blind expert panel—documented to support reproducible rank-correlation analysis. Optional SonarCloud scans extend the comparison when `SONAR_TOKEN` and `sonar-scanner` are available.

---

## 1. Research questions

1. **RQ1:** Does Ω’s letter grade match reference grades more often than cyclomatic-only?
2. **RQ2:** Is Ω index rank-correlated with reference quality (Spearman ρ)?
3. **RQ3:** Does the multi-signal composite add value beyond a single McCabe mean?

---

## 2. Corpus

Thirty repositories are listed in `benchmark/corpus.json`. Each entry includes:

| Field | Description |
|-------|-------------|
| `id` | `owner/repo` on GitHub |
| `reference_grade` | A (best) … F (worst) |
| `notes` | Curator rationale (maintainer reputation, scope, known debt) |

**Threats to validity:** Reference labels are **not** ground-truth defect rates. They encode maintainer/community consensus and project reputation. Results measure *alignment with that proxy*, not predictive validity for production incidents.

---

## 3. Methods

### 3.1 Instrument: Ω-QFM (this repository)

Per-file local field (higher = worse):

\[
\Omega_{\text{local}} = 0.28 H_s + 0.25 C + 0.18 N + 0.17 K_{\text{out}} + 0.12 R
\]

Repository index: arithmetic mean of \(\Omega_{\text{local}}\) over analyzed files. Grades: A if \(\Omega_{\text{repo}} < 30\), stepping through B–F at fixed thresholds (see `omega/analyzer.py`).

Python files use full AST; other languages use heuristic proxies (`omega/metrics_heuristic.py`).

### 3.2 Baseline: cyclomatic-only

\[
\text{CycIndex} = \text{mean}_f \bigl( \min(100,\ 6 \cdot \text{McCabe}_f) \bigr)
\]

Same A–F thresholds applied to CycIndex for `cyclomatic_grade`.

Additional baselines computed in `omega/baselines.py`: LOC-only and entropy-only (reported in `results.json`).

### 3.3 Optional: SonarCloud

When `SONAR_TOKEN` is set and `sonar-scanner` is on `PATH`, the benchmark submits each clone to SonarCloud. Ratings are **not** fetched automatically (API/project setup varies); use Sonar UI for appendix comparison.

### 3.4 Procedure

```bash
cd omega
pip install -e ".[dev]"

# Fast pass (~400 files/repo cap)
python benchmark/run_benchmark.py --quick

# Full scan (slow; large repos)
python benchmark/run_benchmark.py --full

# Subset
python benchmark/run_benchmark.py --quick --repos psf/requests pallets/flask
```

Clones land in `$TMP/omega-benchmark/` by default (`--work-dir` to override).

### 3.5 Metrics

| Metric | Definition |
|--------|------------|
| Grade accuracy | Exact match of predicted A–F vs reference |
| Spearman ρ | Rank correlation (Ω index vs reference numeric score 4–0) |
| Mean \|grade error\| | Mean absolute difference on 0–4 grade scale |

---

## 4. Results

<!-- BENCHMARK_RESULTS_START -->

*Generated: 2026-06-01 12:14 UTC*

### Summary metrics

| Metric | Ω composite | Cyclomatic-only |
|--------|-------------|-----------------|
| Grade accuracy (exact A–F) | 0.452 | 0.129 |
| Spearman ρ vs reference | 0.048 | -0.025 |
| Mean |grade error| | 0.742 | 1.419 |

Successful runs: **31** / 31

### Per-repository results

| Repository | Ref | Ω | Ω grade | Cyc | Cyc grade | Files |
|------------|-----|---|---------|-----|-----------|-------|
| psf/requests | A | 30.82 | B | 49.5 | C | 36 |
| pallets/flask | A | 26.46 | A | 39.45 | B | 83 |
| pallets/click | A | 30.03 | B | 53.0 | C | 62 |
| fastapi/fastapi | A | 18.21 | A | 18.95 | A | 400 |
| encode/httpx | A | 30.89 | B | 53.33 | C | 57 |
| encode/starlette | A | 38.68 | B | 58.09 | C | 65 |
| pytest-dev/pytest | A | 29.04 | A | 43.98 | B | 261 |
| Textualize/rich | A | 27.57 | A | 34.51 | B | 211 |
| python-attrs/attrs | A | 22.94 | A | 36.88 | B | 64 |
| pallets/jinja | A | 31.68 | B | 51.07 | C | 60 |
| pydantic/pydantic | A | 37.78 | B | 65.06 | D | 400 |
| tiangolo/sqlmodel | B | 16.27 | A | 19.97 | A | 231 |
| celery/celery | B | 33.31 | B | 51.46 | C | 389 |
| scrapy/scrapy | B | 33.28 | B | 46.77 | C | 400 |
| redis/redis-py | B | 36.46 | B | 57.59 | C | 286 |
| boto/boto3 | B | 25.0 | A | 36.93 | B | 101 |
| django/django | B | 49.4 | C | 89.97 | F | 400 |
| pallets/werkzeug | B | 33.52 | B | 56.79 | C | 134 |
| aio-libs/aiohttp | B | 37.26 | B | 62.63 | D | 167 |
| psf/black | A | 19.42 | A | 30.63 | B | 303 |
| python/mypy | B | 45.82 | C | 71.63 | D | 400 |
| pypa/pip | B | 40.44 | B | 68.23 | D | 400 |
| sqlalchemy/sqlalchemy | B | 49.74 | C | 83.73 | F | 400 |
| marshmallow-code/marshmallow | A | 26.54 | A | 47.57 | C | 37 |
| dbader/schedule | C | 26.04 | A | 54.5 | C | 4 |
| openai/tiktoken | B | 25.81 | A | 46.63 | C | 19 |
| cookiecutter/cookiecutter | B | 18.97 | A | 26.54 | A | 96 |
| faif/python-patterns | C | 16.67 | A | 20.33 | A | 66 |
| tox-dev/tox | B | 32.22 | B | 47.82 | C | 231 |
| mozillazg/python-pinyin | C | 17.69 | A | 20.91 | A | 97 |
| psf/cachetools | A | 0.0 | N/A | 0.0 | A | 0 |

<!-- BENCHMARK_RESULTS_END -->

Full machine-readable output: `benchmark/results.json`.

---

## 5. Discussion (interpretation guide)

- **ρ > 0.5:** Moderate alignment with curator proxy; useful for portfolio ranking, not certification.
- **Ω beats cyclomatic on accuracy:** Suggests entropy/coupling/nesting add discriminative signal for *this* label set.
- **Ω ≈ cyclomatic:** Composite may be redundant for shallow Python-only repos; investigate per-language strata.
- **Low accuracy overall:** Reference grades may be coarse (only 5 bins) or misaligned with static stress; consider continuous defect labels in future work.

---

## 6. Reproducibility checklist

- [ ] Python 3.10+, `git`, network for clones  
- [ ] `pip install -e ".[dev]"`  
- [ ] `pytest` passes (`tests/`)  
- [ ] `benchmark/run_benchmark.py --quick` completes  
- [ ] Commit `benchmark/results.json` for pinned artifact (optional)  

---

## 7. Future work

1. Blind expert panel (n ≥ 3) on stratified file samples  
2. Outcome labels: GitHub issue age, change-failure rate, Sonar ratings API  
3. Ablation study per Ω pillar (already supported via `omega/baselines.py`)  
4. Cross-language fairness weighting  

---

## References (conceptual lineage)

- McCabe, T. (1976). Complexity measure. *IEEE Transactions on Software Engineering.*  
- Shannon, C. (1948). Communication in the presence of noise. *Bell System Technical Journal.*  
- Chidamber, S. & Kemerer, C. (1994). CK metrics suite. *IEEE TSE.*  
- Basili, V. et al. — empirical validation of static metrics (meta-analyses, various).  

---

*This document is generated and updated by the benchmark harness; cite repository version and `results.json` `generated_at` when publishing figures.*
