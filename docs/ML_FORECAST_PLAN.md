# ML Forecasting Plan — Projects, Resources & Revenue (12-Month Prediction)

## Existing Forecast Model Analysis

### Source Files
- `docs/pricing/Cluster_Revenue_COE_Forecast.xlsx` — Working forecast model (7 sheets)
- `docs/pricing/Cluster_Revenue_Forecast_Flow.html` — Animated visual explainer of the methodology
- `docs/pricing/2511_JMAN Pricing Tool (aligned with new JIN).xlsx` — Rate card & billing details

### Current Methodology (6-Step Engine from Excel)

| Step | What Happens | Excel Sheet |
|------|-------------|-------------|
| 1 | Two inputs: 6-month actual revenue ($3.8M→$4.35M) + 293 pipeline role-lines by cluster | `Revenue_Trend` + `Pipeline_Data` |
| 2 | Role → Rate Mapping: Pipeline codes (SC, SSE, Sol Con) → standard role + location + COE + USD day rate | `Role_Mapping` + `Rate_Card` |
| 3 | Revenue per role line: `day_rate × working_days × allocation_%` | `Pipeline_Data` col N |
| 4 | Monthly proration: Spread deal revenue across months by `overlap_days / total_days` | `Pipeline_Data` cols Q–V |
| 5 | Top-down trend: `FORECAST.LINEAR` on 6 actual months → Jul–Dec ($4.48M→$4.94M) | `Revenue_Trend` |
| 6 | Cluster weight blend: Cluster share of bottom-up pipeline × top-down total. Fallback to 6-mo avg | `Cluster_Forecast` |

### Current Model Outputs
- **6-month total forecast**: $28.25M (Jul–Dec 2026)
- **Monthly growth**: $4.48M → $4.94M
- **5 clusters** revenue split
- **7 COEs** supply/demand gap (headcount vs pipeline FTE)

### Cluster Revenue Split (6-month total from Excel)

| Cluster | Revenue | Share |
|---------|---------|-------|
| Cluster 5 | $14.84M | 52.5% |
| Cluster 3 | $5.77M | 20.4% |
| Cluster 1 | $3.25M | 11.5% |
| Cluster 2 | $2.82M | 10.0% |
| Cluster 4 | $1.58M | 5.6% |

### COE Capacity Gap (Jul 2026, from Excel)

| COE | Gap (FTE) | Notes |
|-----|-----------|-------|
| Full Stack | -50.5 | Severe shortage |
| Consulting | -39.3 | Severe shortage |
| Power BI & Consulting | -13.1 | Moderate |
| Data Engineering | -11.4 | Moderate |
| GTM | -3.7 | Mild |
| Data Science & AI | -0.1 | Minimal |
| Techops & Automation | 0.0 | Balanced |

### Limitations of Current Excel Model

1. **No historical cluster data** — weights from current pipeline only, not trends
2. **Linear trend on 6 points** — no seasonality, no growth curves
3. **No probability weighting** — all deals treated as 100% likely
4. **Static COE supply** — assumes headcount unchanged for 6 months
5. **Only 286/665 employees have COE tags** — supply side incomplete
6. **6-month horizon only** — not 12 months
7. **No confidence bands** — single point estimate
8. **No attrition/hiring modeling** — headcount changes not factored

### Rate Card (USD Day Rates, from Excel)

| Role | Location | Day Rate (USD) |
|------|----------|----------------|
| Associate Partner | UK | $3,526 |
| Principal | UK | $3,234 |
| Manager | UK | $2,984 |
| Senior Consultant | UK | $2,798 |
| Consultant | UK | $2,457 |
| Sr Associate Consultant | UK | $1,979 |
| Associate Consultant | UK | $1,866 |
| Sr Solutions Consultant | IN | $715 |
| Solutions Consultant | IN | $683 |
| Solutions Enabler | IN | $683 |
| Senior Software Engineer | IN | $585 |
| Software Engineer | IN | $455 |
| Pr Technology Architect | IN | $845 |
| Tech Solutions Architect | IN | $748 |

### Role Mapping (Pipeline Code → Standard, 28 mappings)

Examples: `SC` → Senior Consultant (UK, Consulting), `SSE` → Senior Software Engineer (IN, Full Stack), `Sol Con` → Solutions Consultant (IN, Power BI & Consulting), `Enabler` → Solutions Enabler (IN, Data Engineering)

---

## Data Available

| Signal | Range | Depth |
|--------|-------|-------|
| Projects started per month | Jan 2019 → Jun 2026 (90 months) | ~20-45/month recently |
| Allocations (resource demand) | Jan 2024 → Jun 2026 (30 months) | 200-800/month |
| Headcount growth | Jan 2024 → Jul 2026 | 184 → 665 |
| Timesheets (hours) | Jan 2026 → Jun 2026 (6 months only) | 430-574 employees |
| Pipeline (future demand) | Current snapshot | 293 requests |
| Rate card | 30 roles × 3 locations × 3 currencies | Daily billing rates |

## Rate Card Summary (from pricing tool)

Source: `docs/pricing/2511_JMAN Pricing Tool (aligned with new JIN).xlsx`

| Role | Location | Billing (GBP/day) | Cost (GBP/day) | Margin |
|------|----------|-------------------|----------------|--------|
| Associate Partner | UK | £2,250 | £1,145 | 49% |
| Principal | UK | £1,950 | £780 | 60% |
| Manager | UK | £1,750 | £585 | 67% |
| Senior Consultant | UK | £1,500 | £480 | 68% |
| Consultant | UK | £1,350 | £425 | 69% |
| Sr Solutions Consultant | IN | £550 | £110 | 80% |
| Solutions Consultant | IN | £525 | £85 | 84% |
| Senior Software Engineer | IN | £450 | £45 | 90% |
| Software Engineer | IN | £350 | £35 | 90% |

### Additional Pricing Factors
- **Engagement styles**: Project, Secondment, Managed Services
- **Project type multipliers**: Core Reporting (1×), Data Advisory (1×), Due Diligence (1×), Value Creation (1×), Managed Services (1×)
- **FX rates**: GBP→USD = 1.3, GBP→EUR = 1.2
- **Discount reasons**: Long duration (-10%), New client (-30%), Strategic opportunity (-20%), Charity (-100%)
- **Managed Services out-of-hour premium**: 3%
- **Holidays**: UK, USA, IN holiday calendars included

## ML Enhancement Architecture

### What We Keep (from the Excel model)
- Rate card (USD day rates by role × location)
- Role mapping (pipeline codes → standard roles + COE)
- Monthly proration logic (day-overlap spreading)
- Cluster weight concept (but make it learnable)

### What We Replace/Enhance

| Excel Approach | ML Enhancement |
|----------------|----------------|
| Linear trend on 6 points | Prophet/SARIMA on 30+ months of allocation-derived revenue |
| No probability weighting | Weight by `probability_weight` from pipeline |
| Static cluster weights | Time-series cluster share model (seasonal patterns) |
| Fixed headcount supply | Headcount growth model + attrition prediction |
| 6-month horizon | 12-month horizon with confidence bands |
| No seasonality | Q1 ramp-up, Q3 dip, Q4 surge patterns detected |
| Single point estimate | P10/P50/P90 confidence intervals |

### 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ML FORECASTING SERVICE                                │
├───────────────────────────┬─────────────────────────┬───────────────────────┤
│  Layer 1: REVENUE ENGINE  │  Layer 2: CLUSTER       │  Layer 3: COE SUPPLY/ │
│  (extends Excel logic)    │  DECOMPOSITION          │  DEMAND GAP           │
│                           │                         │                       │
│  Inputs:                  │  Inputs:                │  Inputs:              │
│  - 30-mo historical       │  - Pipeline by cluster  │  - Headcount growth   │
│    revenue (reconstructed │  - Historical share     │  - Attrition rates    │
│    from allocs × rates)   │    patterns             │  - COE tagging (infer │
│  - 6-mo actuals (Jan-Jun) │  - Seasonal pipeline    │    for 379 untagged)  │
│  - Pipeline (probability- │    patterns             │  - Billability trend  │
│    weighted, prorated)    │                         │  - Pipeline FTE demand│
│  - Rate card × working    │  Output:                │                       │
│    days                   │  - Time-varying cluster │  Output:              │
│                           │    weights              │  - FTE gap × COE ×    │
│  Output:                  │  - Revenue × cluster    │    month              │
│  - Total revenue/month    │    × month              │  - Hiring recs        │
│    (next 12 months)       │  - Smoothed fallback    │  - Dynamic supply     │
│  - Confidence bands       │    for sparse months    │    projection         │
│    (P10/P50/P90)          │                         │                       │
└───────────────────────────┴─────────────────────────┴───────────────────────┘
```

### Legacy 3-Model View (also built)

```
┌─────────────────────────────────────────────────────────────────┐
│  Model 1: PROJECTS  │  Model 2: RESOURCES  │  Model 3: REVENUE  │
│  (Time series)      │  (Multi-variate)     │  (Composite)       │
│                     │                      │                    │
│  Input:             │  Input:              │  Input:            │
│  - Monthly project  │  - Monthly allocs    │  - Rate card ×     │
│    start counts     │  - Headcount growth  │    role FTE ×      │
│  - Seasonality      │  - COE distribution  │    working days    │
│  - Growth trend     │  - Role breakdown    │  - Project model   │
│  - Pipeline stage   │  - Bench rate        │    output          │
│    conversion       │  - Attrition signal  │  - Resource model  │
│                     │                      │    output          │
│  Output:            │  Output:             │  - Location mix    │
│  - Projects/month   │  - FTE demand/month  │  - Billability %   │
│    (next 12 months) │  - Role-wise split   │                    │
│  - By COE           │  - Hiring needs      │  Output:           │
│  - Confidence bands │  - Bench forecast    │  - Revenue/month   │
│                     │                      │  - By role & COE   │
│                     │                      │  - Margin forecast │
│                     │                      │  - Confidence bands│
└─────────────────────┴──────────────────────┴────────────────────┘
```

## Model 1: Project Forecast

**Method**: Prophet (Facebook) or SARIMA — seasonal time series

**Training data**: 90 months of project starts (Jan 2019 → Jun 2026)

**Features**:
- Monthly project count (target variable)
- Year-over-year growth rate
- Seasonal decomposition (Q1 ramp-up, Q4 surge visible in data)
- Pipeline conversion rate (deal stages → actual projects)
- COE-level sub-forecasts (Data Engineering, BI, Consulting, etc.)

**Output**: 12-month forecast of new projects starting per month, broken by COE

## Model 2: Resource Demand Forecast

**Method**: Multi-variate regression + exponential smoothing

**Training data**: 30 months of allocation data (Jan 2024 → Jun 2026)

**Features**:
- Monthly FTE demand (billable + shadow)
- Role-wise breakdown (15 canonical roles)
- Headcount trajectory (strong growth: 184 → 665 in 30 months)
- Bench rate (available vs allocated)
- Attrition signal (resignation dates)
- Average allocation % trend (declining: 71% → 61%)
- Pipeline demand signal (293 pending roles)

**Output**:
- Total FTE demand per month (next 12)
- Per-role FTE breakdown
- Hiring gap (demand − headcount × utilization target)
- Bench forecast

## Model 3: Revenue Forecast

**Method**: Bottom-up calculation model using Model 1 + Model 2 outputs + rate card

**Formula**:
```
Monthly Revenue = Σ (role_fte × billing_rate × working_days × billability_rate)

Where:
  role_fte      = from Resource Model output
  billing_rate  = from pricing tool (role × location × currency)
  working_days  = calendar days − holidays − weekends (from Holiday table in pricing)
  billability   = historical ratio (BILLABLE allocs / total allocs)

  Location mix:  70% IN (Chennai), 24% UK (London), 6% US (New York)
  Engagement multiplier: 1.0 (project), varies for Managed Services
  Discount: -10% to -30% depending on reason (from pricing tool)
```

**Revenue calculation example**:
```python
# Senior Software Engineer, IN, GBP billing
daily_rate = 450  # GBP
working_days_per_month = 22  # avg
fte_count = 54.1  # current from resource model
monthly_revenue = daily_rate * working_days_per_month * fte_count
# = 450 * 22 * 54.1 = £535,290/month just for Sr SW Eng IN
```

## Implementation Plan

### Phase 1: Data Pipeline & Models

```
backend/
├── ml/
│   ├── __init__.py
│   ├── data_prep.py              ← Extract & transform 30-month historical features
│   ├── rate_card.py              ← Parse BOTH pricing XLSX files → unified rate lookup
│   ├── role_mapping.py           ← Pipeline code → role/location/COE (from Excel)
│   ├── proration.py              ← Monthly revenue spreading (replicate Excel Step 4)
│   ├── models/
│   │   ├── project_forecast.py   ← Prophet/SARIMA for project counts
│   │   ├── resource_forecast.py  ← Multi-variate FTE demand
│   │   ├── revenue_forecast.py   ← Time-series on reconstructed + actual revenue
│   │   ├── cluster_model.py      ← Time-varying cluster weight decomposition
│   │   └── coe_gap_model.py      ← COE supply/demand with headcount growth
│   ├── train.py                  ← Train/retrain all models
│   ├── predict.py                ← Generate 12-month predictions
│   └── evaluate.py               ← Backtest accuracy (MAPE, MAE)
```

### Phase 2: Database Schema

```sql
CREATE TABLE IF NOT EXISTS ml_forecasts (
    id              SERIAL PRIMARY KEY,
    forecast_type   VARCHAR NOT NULL,  -- 'project' | 'resource' | 'revenue' | 'cluster' | 'coe_gap'
    month           DATE NOT NULL,
    dimension       VARCHAR,           -- role, coe, cluster, location, or 'total'
    predicted_value NUMERIC(12,2),
    lower_bound     NUMERIC(12,2),     -- P10 confidence
    upper_bound     NUMERIC(12,2),     -- P90 confidence
    model_version   VARCHAR,
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    metadata        JSONB              -- model params, features used
);

CREATE TABLE IF NOT EXISTS ml_rate_card (
    id              SERIAL PRIMARY KEY,
    role            VARCHAR NOT NULL,
    location        VARCHAR NOT NULL,  -- UK, IN, USA
    day_rate_usd    NUMERIC(8,2),
    day_rate_gbp    NUMERIC(8,2),
    cost_gbp        NUMERIC(8,2),
    margin_pct      NUMERIC(5,2),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_role_mapping (
    id              SERIAL PRIMARY KEY,
    pipeline_code   VARCHAR NOT NULL UNIQUE,
    mapped_role     VARCHAR NOT NULL,
    default_location VARCHAR NOT NULL,
    mapped_coe      VARCHAR NOT NULL,
    confidence      VARCHAR,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_revenue_actuals (
    id              SERIAL PRIMARY KEY,
    month           DATE NOT NULL UNIQUE,
    actual_revenue_usd NUMERIC(14,2),
    source          VARCHAR,           -- 'pipeline_details' | 'reconstructed'
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Phase 3: API Endpoints

```
GET /api/forecast/ml/revenue          → 12-month total revenue forecast with P10/P50/P90
GET /api/forecast/ml/revenue/clusters → Revenue decomposed by cluster × month
GET /api/forecast/ml/projects         → 12-month project start predictions by COE
GET /api/forecast/ml/resources        → 12-month FTE demand by role + hiring gap
GET /api/forecast/ml/coe-gap          → COE supply vs demand gap (dynamic, not static)
GET /api/forecast/ml/summary          → Combined dashboard KPIs
POST /api/forecast/ml/retrain         → Trigger model retrain (admin)
GET /api/forecast/ml/actuals          → Historical revenue actuals (for chart overlay)
```

### Phase 4: Frontend (new tab on Forecast page)

Add an **"AI Forecast"** tab to the existing Forecast page with:
- 12-month revenue projection chart (line + P10/P50/P90 confidence bands)
- Actuals overlay (Jan–Jun 2026 known points)
- Cluster revenue breakdown (stacked area chart, 5 clusters)
- Resource demand heatmap (role × month)
- COE supply/demand gap chart (bar chart, negative = shortfall)
- Hiring gap analysis table
- Project pipeline conversion prediction
- What-if scenario sliders (win rate, attrition, growth rate, rate card adjustment)

## Dependencies (new packages)

```txt
prophet>=1.1.5          # Time series (revenue + project forecast)
scikit-learn>=1.5.0     # Regression, evaluation, ensemble
statsmodels>=0.14.0     # SARIMA, exponential smoothing, trend decomposition
pandas>=2.2.0           # Data manipulation
openpyxl>=3.1.0         # Rate card & forecast XLSX parsing
numpy>=1.26.0           # Numerical operations
```

## Training Strategy

| Model | Retrain Frequency | Method |
|-------|-------------------|--------|
| Project | Weekly (Sunday night) | Prophet with yearly + quarterly seasonality |
| Resource | Weekly | Exponential smoothing + linear regression ensemble |
| Revenue | Daily (after allocation changes) | Deterministic calculation (no ML, just formula) |

## Current Metrics (baseline)

- **Active headcount**: 665 employees (IN: 463, UK: 162, US: 39)
- **Billable FTE**: ~496 (Jun 2026)
- **Active projects**: ~146 (non-BAU, Jun 2026)
- **Top COEs**: Data Engineering (419), BI & Reporting (389), Consulting (143)
- **Top roles (by FTE)**: Sr SW Eng (54), SW Eng (44), Solutions Enabler (42)
- **Pipeline**: 293 requests, 139 in "Build the Proposition" stage
- **Billability ratio**: ~95% of allocations are BILLABLE

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Only 6 months of timesheet data | Use allocation data (30 months) as proxy for hours |
| Headcount growth is non-linear (rapid recent scaling) | Use piecewise growth model, weight recent data 3× |
| Rate card has no historical pricing | Assume rates are current; add inflation factor (5% YoY) |
| BAU skews allocation numbers | Already excluded in all queries (existing pattern) |
| Small n for UK/US roles | Pool IN+UK for trend, split for revenue calc only |
| No historical cluster tagging | Use pipeline cluster tags + infer from client history |
| Only 286/665 employees have COE tags | Infer COE from skills data for remaining 379 |
| Excel model assumes 100% deal conversion | Apply probability_weight from pipeline_requests |
| Sparse pipeline for later months | Smoothed cluster fallback (6-mo avg, matching Excel approach) |

## Priority Order

1. **Revenue forecast** (highest business value — extends Excel model to 12 months with ML)
2. **Cluster decomposition** (management visibility by business unit)
3. **COE supply/demand** (hiring decisions)
4. **Resource demand** (role-level planning)
5. **Project volume** (capacity planning)

## Execution Sequence

1. **Rate card parser** — parse BOTH pricing XLSX files into unified rate + role mapping lookup
2. **Monthly proration engine** — replicate Excel Step 4 logic in Python (day-overlap spreading)
3. **Historical revenue reconstruction** — allocations × rate card × working days for 30 months
4. **Revenue time-series model** — Prophet on reconstructed + 6 actual months (Jan–Jun 2026)
5. **Pipeline revenue calculator** — prorate pipeline deals with probability weighting
6. **Cluster weight model** — time-varying cluster shares with smoothed fallback
7. **COE supply/demand model** — dynamic headcount + attrition + tagging inference
8. **Resource demand model** — FTE by role, 12-month forecast
9. **Project volume model** — 90-month time series of project starts
10. **API endpoints** — serve all layers with caching
11. **Frontend "AI Forecast" tab** — interactive charts with confidence bands
12. **Backtest & accuracy evaluation** — MAPE, MAE on holdout months
