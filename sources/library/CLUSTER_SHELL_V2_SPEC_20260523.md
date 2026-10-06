# Cluster Shell v2 — Multi-Surface Specialist Spec

Date: 2026-05-23
Status: DRAFT — supersedes v1 directional-only design after eval-surface audit

## Why v1 was wrong

v1 cluster trained five specialists, three of which were the same task on different data slices:

- `q_penny_v1` — direction on penny rows
- `q_2yr_v1` — direction on large-cap multi-day rows
- `q_180d_v1` — direction on 180d intraday rows (only ~58 days of past stock market data — degenerate window)
- `q_veto_v1` — hard-boundary TRADE vs VETO governor (legitimate task)
- `q_router_v1` — picks which of the above (built to serve a flawed roster)

The operator surfaced the architectural problem during run 1: three directional
specialists are *data-slice clones*, not different *tasks*. They all consume
OHLCV + indicators; they all output BUY/SELL/HOLD/NO_TRADE. The split is by
universe band and lookback window, not by decision surface.

Worse, the eval audit on `E:\vfai-x_3.5_9b` and `E:\Bleeding_edge` revealed
the system actually measures **eight or more distinct surfaces**:

- Market regime / directional (OHLCV + indicators)
- Chart vision (224×224 candlestick composites)
- Options Greeks (Δ Γ Θ Vega Rho + IV + chains)
- Fundamentals (earnings, EPS, balance sheet)
- News / sentiment (5-level sentiment + market-impact level)
- Macro indicators (economic calendar + halts + short interest)
- Events (S-1, dilution, halts, earnings windows)
- Calibration (confidence-to-win-rate alignment)

v1 trained on one of these (directional) three times and ignored the other
seven.

## Salvaged from v1

Two specialists are kept because they correspond to real, distinct surfaces:

- **Q-Penny** (lives) — penny universe genuinely IS a different beast.
  Different microstructure, different volatility envelope, different fail
  modes (halts, dilutions, S-1 cascades). Keep as its own seat.
- **Q-Veto** (lives) — hard-boundary TRADE vs VETO governor. Universal across
  tiers. Cannot drift. Trains on adversarial / red-flag rows.

The remaining three v1 specialists are abandoned:

- **Q-2yr** — KILL. Pure directional duplicate.
- **Q-180d** — KILL. Pure directional duplicate, *and* the 180-day window
  contains only ~58 trading days of past market data — too narrow to learn
  multi-regime structure.
- **Q-Router** — KILL. Built to route between three duplicate directional
  models. v2 router roster will look completely different; rebuild from
  scratch.

## v2 specialist roster

Eight specialists, organized by **decision surface**, not data slice. Each
one corresponds to an eval surface the broader system already measures.

| Seat | ID | Surface | Input modality | Output |
|---|---|---|---|---|
| 1 | **Q-Penny** ✅ kept | Penny-universe direction | OHLCV + pattern + RSI + microstructure | BUY/SELL/HOLD/NO_TRADE + conviction |
| 2 | **Q-Direction** | Universal direction (non-penny) | OHLCV + pattern + RSI + price_band feature | BUY/SELL/HOLD/NO_TRADE + conviction |
| 3 | **Q-Chart-Vision** | Chart pattern recognition (visual) | 224×224 candlestick PNG + OHLCV | pattern_label + visual_conviction |
| 4 | **Q-Options** | Options-aware decision | Greeks + IV + chain + underlying OHLCV | CALL/PUT/STRADDLE/NO_TRADE + structure |
| 5 | **Q-Fundamentals** | Earnings + balance sheet | EPS history + earnings cal + revenue + balance sheet | BULL/BEAR/NEUTRAL + horizon |
| 6 | **Q-News-Sentiment** | News / sentiment | News text + 5-level sentiment + impact level | POSITIVE/NEGATIVE/NEUTRAL + decay_horizon |
| 7 | **Q-Macro** | Macro regime | Economic cal + halts + short interest | REGIME tag + risk-on/risk-off score |
| 8 | **Q-Veto** ✅ kept | Hard-boundary governor | All-surface microstructure + event flags | TRADE / VETO + reason_code |

Plus the deterministic shell:

- **Q-Router** (rebuilt) — picks which seat(s) handle a row
- **Verifier** — hard schema checks (deterministic)
- **Calibrator** — confidence bucket mapping (deterministic)
- **Veto Governor** (Q-Veto + deterministic rules combined as a single hard gate)
- **Fusion head** — when multiple seats fire, combines their outputs into a
  single shell action (deterministic ensemble logic)

## Modality fusion at the shell

The shell becomes a **multi-modal fusion gate**. A typical row may activate:

- Q-Direction (always)
- Q-Chart-Vision (if chart image is available)
- Q-Fundamentals (if earnings is within 14d)
- Q-News-Sentiment (if symbol has fresh news ≤24h)
- Q-Macro (if today is on the macro calendar)
- Q-Options (if user has options exposure or row is options-tagged)
- Q-Veto (always — final gate)

The router picks which seats activate. The fusion head combines them into a
single action. The veto can refuse regardless.

**This is the real Cluster Shell.** v1 was a single-surface cluster
pretending to be multi-surface by slicing data three ways.

## Per-specialist training corpus design

Each specialist gets its own crystal corpus with deterministic rule tables,
controlled label noise, and a tabular baseline gate. Same discipline as v1.
Different *what* is being trained:

### Q-Direction (replaces Q-2yr + Q-180d)
- Rule table: universal pattern × trend × rsi × vol × relvol matrix
- New feature: `price_band` (penny / mid / large) — informative, not label leak
- Rule table size: ~60-80 rules
- Noise rate: 0.43 (4-class)
- Target HGB ceiling: 73-75%
- Rows: 300K

### Q-Chart-Vision (new)
- Input: 224×224 candlestick PNG + OHLCV vector
- Use Qwen3.5-9B native vision tokenizer path (already in VFAi-X)
- Rule table: visual_pattern × structural_position
- Synthetic charts generated from rule-driven OHLCV (already have
  `/dev/image_capture/synthetic/` 769MB)
- Rule table size: ~40 visual patterns
- Noise: 0.30 (3-class: bullish_pattern / bearish_pattern / consolidation)
- Target HGB ceiling: 72%
- Rows: 200K (image+OHLCV pairs)

### Q-Options (new)
- Input: Greeks (Δ Γ Θ Vega) + IV + DTE + spot + strike
- Rule table: IV-rank × DTE-band × Greek-profile × underlying-direction
- Output: CALL / PUT / STRADDLE / IRON_CONDOR / NO_TRADE + leg-structure
- Rule table size: ~50 options setups
- Noise: 0.35 (5-class)
- Rows: 200K

### Q-Fundamentals (new)
- Input: EPS history (8 quarters) + revenue trend + earnings-cal-distance
- Rule table: earnings_proximity × surprise_history × revenue_growth
- Output: BULL_HORIZON / BEAR_HORIZON / NEUTRAL + horizon_days
- Rule table size: ~30
- Noise: 0.40
- Rows: 150K

### Q-News-Sentiment (new)
- Input: news headline + 5-level sentiment + market-impact level
- Rule table: sentiment × impact × decay
- Output: POSITIVE / NEGATIVE / NEUTRAL + decay_hours
- Rule table size: ~25
- Noise: 0.40
- Rows: 150K

### Q-Macro (new)
- Input: macro calendar event tag + halt flag + short-interest delta
- Rule table: event-type × proximity × magnitude
- Output: regime tag {risk_on, risk_off, neutral} + confidence
- Rule table size: ~30
- Noise: 0.30
- Rows: 100K

### Q-Penny (kept from v1)
- Already trained — keep checkpoint
- Eval against Q-Direction on penny rows to confirm Q-Penny still wins on
  its specialty

### Q-Veto (training now)
- Will finish in current run
- Keep — universal hard-boundary governor

### Q-Router (rebuild)
- Output space: subset of {q_penny, q_direction, q_chart_vision, q_options,
  q_fundamentals, q_news, q_macro, q_veto}
- Multi-label, not single-label — a row may activate 3-5 seats
- Rule table: input modality presence → relevant seats
- Rows: 200K
- Output is multi-hot binary vector, not 5-class softmax

## Param budget

v1 cluster: 5 × 47M = 237M trainable.

v2 cluster (eight seats):

| Seat | Size | Why |
|---|---:|---|
| Q-Penny | 50M | Kept from v1 |
| Q-Direction | 100M | Bigger — universe of tickers, broader pattern surface |
| Q-Chart-Vision | 150M | Visual encoder + decision head |
| Q-Options | 100M | Greek surfaces + chain reasoning |
| Q-Fundamentals | 50M | Compact — structured table input |
| Q-News-Sentiment | 50M | Compact — text input but narrow output |
| Q-Macro | 50M | Compact — small input space |
| Q-Veto | 50M | Kept from v1 |
| **Cluster total** | **600M** | **trainable across all seats** |

Active params per decision (router-dependent): 50-300M depending on how many
modalities the row activates. Still vastly less than a 9B Franken-B or
500B-class frontier monolith.

VRAM at inference (worst case all seats loaded): ~3-4 GB. Still fits a
consumer GPU.

## Training plan v2

After Q-Veto finishes current run:

1. **Kill Q-Router, Q-2yr, Q-180d jobs** (queued after Q-Veto)
2. **Eval Q-Penny + Q-Veto checkpoints** against the existing v4 streams to
   confirm they clear HGB parity gates
3. **If they pass:** keep them, build v2 corpora for the six new specialists,
   train each through the same crystal → HGB-gate → train pipeline
4. **If they fail:** the v1 architecture probe failed and we revise the
   crystal recipe before training v2 on the same defective recipe

## Falsifiability gates v2

Same five gates as v1, applied per-seat plus cluster-level:

- **G1 per seat:** HGB baseline parity on its own crystal corpus
- **G2 per seat:** beats ALWAYS_NO_TRADE at 10bps
- **G3 per seat:** beats AN_AM_SHELL at 10bps
- **G4 cluster:** fused decision beats best individual seat
- **G5 cluster:** fused decision beats AN_AM_SHELL at 10bps with bootstrap
  lower bound > 0

Q-Router gate: top-2 ≥ 95% on multi-label set assignment (different metric
from v1's 5-class top-2).

## What stays the same

- `QShellDecisionRecord` schema and contract
- Crystal corpus discipline (rule-first, deliberate noise floor, HGB gate)
- Deterministic verifier + calibrator + veto governor
- Promotion ladder G1-G5
- Local sovereignty + consumer-GPU constraint

The architecture's first-principle commitments are preserved. Only the
*roster of seats* is being rebuilt around the actual eval surfaces.

## Open questions for run 2

- Should Q-Penny be retrained against the new Q-Direction with `price_band`
  as a feature, or is the penny-specific specialist genuinely additive?
- Should chart vision be a *seat* or a *feature* that other seats consume?
- Should Q-Options be one seat or split (calls / puts / spreads)?
- Does Q-News-Sentiment need an LLM-tokenizer-based encoder or can it
  consume pre-scored sentiment levels?
- Q-Router as multi-label vs as a graph (seats with dependencies)?

These get answered before run 2 launches.
