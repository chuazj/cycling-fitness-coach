# Block Templates, Progressions, and Plan Design

Reference for Claude-as-coach: block templates, TSS distribution, interval progressions, warmup/cooldown standards, FTP test protocols, and goal-based block selection logic. This is the primary file for Create Plan and for any block-rollover decision.

- For weekly adaptation decision trees (load, ACWR, TSB, RPE, illness/injury, peak-power deltas) → `references/weekly_adaptation.md`.
- For race / event taper protocols → `references/race_taper.md`.
- For concurrent strength training, heat adaptation, and durability → `references/durability_strength.md`.

> **Citation currency** — physiology citations in this doc last verified **2026-05-20** (VO2max short-vs-long interval evidence, VLaMax framework). Re-verify against current literature at every skill audit; interval-format and fuelling evidence move fastest, so treat anything older than ~12 months as provisional. Anchor authorities: `references/bibliography.md#seiler-stephen` and `references/bibliography.md#stoggl-thomas--sperlich-billy` (polarized basis); `references/bibliography.md#ronnestad-bent` (VO2max short intervals, 30/15s); auxiliary VLaMax citations at `references/bibliography.md#auxiliary-citations`.

## Table of Contents

- [Training Blocks](#training-blocks) — FTP Builder, VO2max, Endurance Base, Polarized block templates
- [TSS Distribution (4-Day Week)](#tss-distribution-4-day-week) — Per-session TSS allocation rules
- [Progressive Overload Tables](#progressive-overload-tables) — Interval progression by type and level
- [Warmup and Cooldown Standards](#warmup-and-cooldown-standards) — Standard ramp protocols
- [FTP Test Protocols](#ftp-test-protocols) — 20-min, ramp, and CP/eFTP procedures
- [Block Selection Logic](#block-selection-logic) — Goal-based block type selection

## Training Blocks

### FTP Builder (4 weeks)

The primary block for systematic FTP improvement. Progressive overload through increasing duration and intensity, culminating in a recovery/test week.

| Week | Phase | Focus | TSS vs Baseline | Key Sessions |
|------|-------|-------|-----------------|--------------|
| 1 | Build 1 | SS + Threshold intro | Baseline (100%) | 2× Sweet Spot + 1× Threshold intro |
| 2 | Build 2 | SS longer + VO2max intro | +10% | 2× Sweet Spot (longer) + 1× VO2max intro |
| 3 | Build 3 | Threshold + VO2max | +10-15% vs W2 | 2× Threshold + 1× VO2max |
| 4 | Recovery | Test FTP | -45% vs W1 | Recovery rides + FTP test |

**Week 1 detail (Build 1):**
- Tue: Sweet Spot — 2×15min @ 88-94% FTP, 5min recovery
- Thu: Threshold intro — 3×8min @ 100-105% FTP, 5min recovery
- Sat: Endurance + Sweet Spot — 60min Z2 with 1×20min SS block
- Flex: Easy endurance or VO2max intro (3×3min @ 115%)

**Week 2 detail (Build 2):**
- Tue: Sweet Spot — 2×20min @ 88-94% FTP, 5min recovery
- Thu: VO2max intro — 4×3min @ 115-120% FTP, 3min recovery
- Sat: Endurance + Sweet Spot — 60min Z2 with 2×15min SS blocks
- Flex: Easy endurance or tempo

**Week 3 detail (Build 3):**
- Tue: Threshold — 3×10min @ 100-105% FTP, 5min recovery
- Thu: VO2max — 4×4min @ 115-120% FTP, 4min recovery
- Sat: Threshold + Sweet Spot — 2×12min threshold + 1×15min SS
- Flex: Easy endurance

**Week 4 detail (Recovery + Test):**
- Tue: Easy endurance — 45min Z1-Z2
- Thu: Openers — 30min easy + 3×1min @ 105% with 2min rest
- Sat: FTP Test — 20-minute test protocol
- Flex: Rest or very easy spin

**Block-level coaching notes:**
- **Expected outcome — set realistic expectations.** One 4-week FTP Builder block typically yields **2–4% FTP gain** for an intermediate athlete on this sweet-spot-focused stimulus. Novice or detrained riders may see 4–6%; advanced riders near their ceiling often gain <2%. Larger targets (e.g. +6–8%) are **multi-block goals** — budget 2–3 blocks (8–12 weeks). State this up front (Coaching Process Rule 1) so the test result is read correctly: a 192–195W result off a 188W FTP is a *successful* block, not a failure. If the athlete frames a goal implying >4% in 4 weeks, reframe it to a realistic per-block rate before building the plan.
- **Target intensity distribution (pyramidal).** Across the week aim ~60–70% Z1–Z2, ~25–35% Z3–Z4 (sweet spot/threshold), ~5% Z5+. This is a pyramid, not polarized — the Z3–Z4 content is intentional. Flag drift if Z1–Z2 falls below ~55% (aerobic base being squeezed) or if Flex/endurance days creep above Z2 (easy days not easy).
- **ERG variety.** At least one Flex-day session per block should be sim-mode or free-ride (not ERG) — develops the power-modulation and self-pacing skills ERG suppresses. See `references/workout_analysis.md` → ERG Mode.
- Hard sessions are Tue + Thu — never back-to-back. Sat is the volume anchor with a moderate-intensity insertion.

### VO2max Block (3 weeks + 1 recovery)

For athletes who need top-end power development after establishing a solid sweet spot base. Default uses short intervals (30/15s) as the primary VO2max format — time-efficient, well-tolerated, and supported by Rønnestad's cycling work for performance gains; classic long intervals are included for sustained-effort capacity and remain at least equally effective for VO2max itself.

| Week | Phase | Focus | TSS vs Baseline |
|------|-------|-------|-----------------|
| 1 | VO2 Build 1 | Short intervals introduction (30/30s) + Threshold support | Baseline |
| 2 | VO2 Build 2 | Short intervals progression (30/15s) + Classic intro | +10% |
| 3 | VO2 Build 3 | Mixed: short intervals peak + classic 4-5min | +10% vs W2 |
| 4 | Recovery | Deload + retest | -45% |

**Week 1 detail (VO2 Build 1):**
- Tue: SVO2-1 (30/30s 2×8, 3min set rest) — 8min total work @ 120-130% FTP
- Thu: Threshold — 3×8min @ 100-105% FTP, 5min recovery (sustains FTP base while VO2 work begins)
- Sat: Endurance + threshold — 60-90min Z2 with 1×15min @ 95-100% FTP block
- Flex: Easy endurance 45min Z1-Z2

**Week 2 detail (VO2 Build 2):**
- Tue: SVO2-2 or SVO2-3 (30/15s 2×8 or 30/30s 2×10, 3min set rest) — 8-10min total work @ 120-130% FTP
- Thu: Classic VO2max intro — 4×3min @ 115-120% FTP, 3min recovery
- Sat: Endurance + sweet spot — 75-100min Z2 with 1×20min SS block
- Flex: Easy endurance or recovery spin

**Week 3 detail (VO2 Build 3):**
- Tue: SVO2-5 (30/15s 3×8, 3min set rest) — 12min total work @ 120-130% FTP
- Thu: Classic VO2max — 4-5×4min @ 115-120% FTP, 4min recovery
- Sat: Endurance + threshold — 80-100min Z2 with 2×10min @ 95-100% FTP
- Flex: Easy endurance

**Week 4 detail (Recovery + Test):**
- Tue: Easy endurance — 45min Z1-Z2
- Thu: Openers — 30min easy + 3×1min @ 105% FTP with 2min rest (neuromuscular activation pre-test)
- Sat: FTP Test — 20-minute test protocol (or alternative ramp test)
- Flex: Rest or 20-30min very easy spin

**Block-level coaching notes:**
- Hard sessions are Tue + Thu — never back-to-back. Sat long ride is volume anchor with moderate intensity insertion.
- VO2max work strongly fatiguing — if RPE persistently ≥9 on short intervals or HR fails to reach expected levels, drop one progression level rather than push through.
- VO2max block typically yields +2–4% FTP gain when stacked after a sweet-spot base — use as a "ceiling-raising" block, not a standalone FTP builder.

### Endurance Block (4 weeks)

Volume-focused block with tempo integration. Use when building aerobic base or recovering from high-intensity phases.

| Week | Phase | Focus | TSS vs Baseline |
|------|-------|-------|-----------------|
| 1 | Base 1 | Z2 endurance | Baseline |
| 2 | Base 2 | Z2 + tempo blocks | +10% |
| 3 | Base 3 | Longer Z2 + tempo | +10% vs W2 |
| 4 | Recovery | Deload | -40% |

### Polarized Block (4 weeks)

Distribution: ~80% Z1-Z2, ~0% Z3 (tempo), ~20% Z4+ (threshold/VO2max). Based on Seiler (2010) and Stoggl & Sperlich (2014) showing equal or superior adaptations to sweet spot training, particularly at higher training volumes.

**Minimum volume threshold**: 6+ hours/week recommended. Below 6h/week, the Z2 sessions become too short to produce meaningful aerobic adaptations — consider FTP Builder (sweet spot) block instead.

| Week | Phase | Focus | TSS vs Baseline |
|------|-------|-------|-----------------|
| 1 | Polarized 1 | 3×Z2 long + 1×VO2max | Baseline |
| 2 | Polarized 2 | 3×Z2 longer + 1×VO2max + 1×Threshold | +10% |
| 3 | Polarized 3 | 3×Z2 longest + 2×VO2max/Threshold | +10% vs W2 |
| 4 | Recovery | Deload | -45% |

**Week 1 detail:**
- Tue: VO2max — 4×4min @ 115-120% FTP, 4min recovery (sole hard session this week)
- Thu: Z2 Endurance — 60-75min @ 60-70% FTP, strict Z2 only (no tempo drift)
- Sat: Z2 Long Ride — 90-120min @ 60-70% FTP
- Flex: Z1-Z2 easy spin — 30-45min @ <65% FTP

**Week 2 detail:**
- Tue: VO2max — 5×4min @ 115-120% FTP, 4min recovery
- Thu: Threshold — 2×12min @ 100-105% FTP, 5min recovery
- Sat: Z2 Long Ride — 100-130min @ 60-70% FTP
- Flex: Z1-Z2 easy endurance — 45-60min

**Week 3 detail:**
- Tue: VO2max — 5×5min @ 115-120% FTP, 4min recovery
- Thu: Threshold — 3×10min @ 100-105% FTP, 5min recovery
- Sat: Z2 Long Ride — 110-140min @ 60-70% FTP
- Flex: Z1-Z2 easy endurance — 45-60min

**Week 4 detail (Recovery):**
- Tue: Easy endurance — 45min Z1-Z2
- Thu: Openers — 30min easy + 3×1min @ 105% with 2min rest
- Sat: Z2 endurance — 60min easy
- Flex: Rest or very easy spin

**Key coaching points:**
- Z2 sessions must be genuinely easy (conversational pace). If HR drifts into Z3, reduce power.
- The hard sessions must be genuinely hard (Z4+). The "no man's land" of Z3 should be avoided.
- Expect perceived effort paradox: athletes often feel like Z2 days are "too easy" — this is correct and intentional.
- Monitor weekly zone distribution: target 80/0/20 (Z1-2 / Z3 / Z4+). If Z3 exceeds 5%, the athlete is drifting.

---

## TSS Distribution (4-Day Week)

Training days: **Tuesday, Thursday, Saturday, + 1 Flex day**

| Day | Role | % Weekly TSS | Session Character |
|-----|------|-------------|-------------------|
| Tue | Hard (intensity) | 25-30% | Intervals: SS, Threshold, or VO2max |
| Thu | Hard (intensity) | 25-30% | Intervals: complementary to Tue |
| Sat | Long (volume) | 30-35% | Endurance base + intensity block |
| Flex | Easy/moderate | 10-20% | Recovery, easy endurance, or light intensity |

### Distribution Rules

- **No back-to-back high-intensity days** — at least 1 rest/easy day between hard sessions
- **Tue + Thu should target different energy systems** where possible (e.g., SS + VO2max, not SS + SS)
- **Saturday is the longest session** — volume anchor of the week
- **Flex day placement**: prefer Monday or Wednesday; avoid day before/after Saturday
- **Recovery week**: all sessions drop to Z1-Z2 except openers and test day

### TSS Baseline Calculation

When creating a plan, baseline weekly TSS = athlete's recent 4-week average weekly TSS from intervals.icu bootstrap data. If no history available, estimate from:
- 4 sessions/week × ~60min average = ~240min
- Average IF ~0.70 → baseline weekly TSS ≈ 200-250

### Weekly Ramp Rate

Block templates step weekly TSS up by ~10% on consecutive build weeks. **+10%/week is the aggressive end** — classic guidance is a ~5–8%/week CTL ramp, and a +10% TSS step on an already-elevated base can push ACWR into the >1.3 caution zone (see `references/weekly_adaptation.md` → Workload Ratio). Treat +10% as a ceiling, not a default: for athletes with CTL <30, an inconsistent training history, or any ACWR/RPE/HRV yellow flag, ramp **5–8%/week** instead. The ACWR tree is the backstop — but prefer not to design a block that needs the backstop every week.

---

## Progressive Overload Tables

### Sweet Spot Progression

| Level | Interval Structure | Total Work Time | Est. TSS (session) |
|-------|-------------------|-----------------|---------------------|
| SS-1 | 2×15min @ 88-94% | 30min | 55-65 |
| SS-2 | 2×20min @ 88-94% | 40min | 65-75 |
| SS-3 | 3×15min @ 88-94% | 45min | 70-80 |
| SS-4 | 2×25min @ 88-94% | 50min | 75-85 |
| SS-5 | 3×20min @ 88-94% | 60min | 85-95 |

Progression: advance one level per week if execution quality is good (power within ±3% target, <5% fade).

### Threshold Progression

| Level | Interval Structure | Total Work Time | Est. TSS (session) |
|-------|-------------------|-----------------|---------------------|
| TH-1 | 3×8min @ 100-105% | 24min | 60-70 |
| TH-2 | 3×10min @ 100-105% | 30min | 70-80 |
| TH-3 | 3×12min @ 100-105% | 36min | 75-85 |
| TH-4 | 4×10min @ 100-105% | 40min | 80-90 |
| TH-5 | 2×20min @ 100-105% | 40min | 85-95 |

Progression: advance one level per week. If athlete can hold 105%+ consistently, flag FTP retest.

### VO2max Progression — Classic (Long Intervals)

| Level | Interval Structure | Total Work Time | Est. TSS (session) |
|-------|-------------------|-----------------|---------------------|
| VO2-1 | 3×3min @ 115-120% | 9min | 45-55 |
| VO2-2 | 4×3min @ 115-120% | 12min | 55-65 |
| VO2-3 | 4×4min @ 115-120% | 16min | 60-70 |
| VO2-4 | 5×4min @ 115-120% | 20min | 70-80 |
| VO2-5 | 5×5min @ 115-120% | 25min | 75-85 |

Recovery between classic VO2max intervals: equal to work duration (1:1 work:rest ratio). Recovery power: 40-50% FTP.

### VO2max Progression — Short Intervals (PRIMARY)

Short intervals (30s work bouts) keep VO2 elevated through the brief recovery — the rationale for using them as a time-efficient VO2max stimulus. Whether they accumulate *more* time above 90% VO2max than classic long intervals is **contested**: Rønnestad's cycling work supported it, but a 2025 running study found the opposite. The advantage, if any, is protocol- and modality-dependent — treat short intervals as a strong, efficient option, not a categorically superior one.

**Evidence**: Rønnestad et al. (2015, *SJMSS*, [PMID 24382021](https://pubmed.ncbi.nlm.nih.gov/24382021/)) showed short intervals produced 8.7% vs 2.6% VO2max improvement compared to effort-matched long intervals in trained cyclists — the canonical figure underpinning the short-interval literature. The 8.7% result has not been shown to generalise upward: the 2020 follow-up ([PMID 31977120](https://pubmed.ncbi.nlm.nih.gov/31977120/)) tested *elite* cyclists — a higher-trained population, not a repeat of the 2015 design — and found **no VO2max difference**, consistent with a ceiling effect at the elite level rather than a failed replication; short intervals still kept a peak-power edge (+3.7% vs -0.3%). On the underlying "more time >90% VO2max" mechanism, Fleckenstein et al. (2025, *Front Sports Act Living*, [PMID 39835194](https://pubmed.ncbi.nlm.nih.gov/39835194/)) found 4×3min intervals accumulated *more* time >90% VO2max than 24×30s intervals (328s vs 201s) in trained runners — the opposite of the canonical claim. Two interval-training meta-analyses — Norte et al. 2024 ([*Int J Strength Cond* 4(1)](https://journal.iusca.org/index.php/Journal/article/view/271), endurance-trained cyclists) and Yang et al. 2025 ([*BMC Sports Sci Med Rehabil*](https://doi.org/10.1186/s13102-025-01191-6), a network meta-analysis of interval methods across athletes) — report no clear duration-related superiority. **Bottom line**: short intervals are an effective, time-efficient, well-tolerated VO2max format — not a categorically superior one; long intervals are at least equivalent and may accumulate more time >90% VO2max depending on the protocol.

| Format | Interval Structure | Total Work Time | Rest | Power Target | Est. TSS (session) |
|--------|-------------------|-----------------|------|-------------|---------------------|
| 30/15s | 10-20× (30s on / 15s off) | 5-10min | 15s @ 45% | 120-130% FTP | 40-60 |
| 30/30s | 10-20× (30s on / 30s off) | 5-10min | 30s @ 45% | 120-130% FTP | 40-60 |
| 40/20s | 8-12× (40s on / 20s off) | 5.3-8min | 20s @ 40% | 115-125% FTP | 40-55 |
| 15/15s | 20-30× (15s on / 15s off) | 5-7.5min | 15s @ 40% | 130-140% FTP | 35-50 |

> **Format metabolic profile (Quittmann 2025; INSCYD 2025)**: 30/15s and 30/30s at 120–130% FTP with mid-cadence (90–100 rpm) are **aerobic-dominant** — they target VO2max with minimal glycolytic load. 15/15s @ 130–140% FTP is **glycolytic-dominant** — supramaximal intensity with brief recovery raises VLaMax (max lactate accumulation rate). For a primarily endurance-focused athlete, prefer 30/15s and 30/30s; reserve 15/15s for sprint-specific demands or variety, and avoid stacking it with other high-glycolytic work (Tabata, max-effort sprints) in the same week.

The **30/15s format** (2:1 work:rest ratio) is the specific protocol used in Rønnestad's landmark studies and should be the default starting point for VO2max development.

**Short interval progression:**

| Level | Format | Sets × Reps | Total Work |
|-------|--------|-------------|------------|
| SVO2-1 | 30/30s | 2×8 (3min set rest) | 8min |
| SVO2-2 | 30/15s | 2×8 (3min set rest) | 8min |
| SVO2-3 | 30/30s | 2×10 (3min set rest) | 10min |
| SVO2-4 | 40/20s | 2×8 (3min set rest) | 10.7min |
| SVO2-5 | 30/15s | 3×8 (3min set rest) | 12min |
| SVO2-6 | 40/20s | 3×8 (3min set rest) | 16min |

**When to use short vs. classic:**
- **Short intervals (DEFAULT)**: Primary VO2max development format — at-least-equivalent adaptations to long intervals with greater time-efficiency and lower session RPE. Two interval-training meta-analyses (Norte et al. 2024, *Int J Strength Cond*; Yang et al. 2025, *BMC Sports Sci Med Rehabil*) found no clear duration-related superiority across HIIT/SIT methods, so frame short intervals as the more time-efficient default — not categorically superior, and not assumed to accumulate more time >90% VO2max. Use for all standard VO2max training.
- **Classic intervals (COMPLEMENTARY)**: Race-specific for sustained climbing/TT efforts where the ability to hold high power for 4-5+ continuous minutes matters. Use when developing sustained-effort capacity, not raw VO2max.
- **Mix both**: Alternate weekly (e.g., Tue = short, Thu = classic) for complementary stimulus — short intervals build the aerobic ceiling, classic intervals build the ability to use it in sustained efforts.

### VLaMax — Conceptual Frame for Format Selection

**VLaMax** (maximum lactate accumulation rate, mmol·L⁻¹·s⁻¹) is the glycolytic-system analogue to VO2max — it represents maximum glycolytic flux. Typical endurance-trained cyclists: 0.3–0.6; sprint specialists: 0.8–1.0+ (Quittmann et al., 2025, *Sports Medicine*; Clark & Macdermid 2025, *RQES*).

**For an endurance-focused rider (this athlete profile)**, a *lower* VLaMax is generally advantageous:
- Less lactate accumulation at submaximal intensities → higher sustainable power per mmol blood lactate
- Lower carbohydrate cost per watt → better glycogen endurance
- FTP / MLSS settles at a higher fraction of VO2max

**Training implications (no testing required):**
- **Default toward aerobic-dominant short intervals**: 30/15s and 30/30s at 120–130% FTP with 85–100 rpm mid-cadence are aerobic-dominant — they raise VO2max without disproportionately raising VLaMax.
- **Use glycolytic-dominant formats sparingly**: 15/15s at supramaximal intensity, all-out 10–15s sprints, and Tabata-style 20s/10s sets all stress the glycolytic system. They have a place (sprint-specific preparation, race demands) but stacking them weekly can erode aerobic efficiency at the margin.
- **Cadence matters**: Same power at high cadence (>105 rpm) tends to be more aerobic; at low cadence (<70 rpm) more glycolytic/neuromuscular. Default to 95–105 rpm for VO2max work.
- **Sweet spot session at moderate cadence (85–95 rpm)** keeps glycolytic contribution low while delivering muscular-endurance stimulus.

**No formal VLaMax testing needed at this level** (no INSCYD subscription, no lab access required). The conceptual awareness is sufficient: don't add pure glycolytic work for its own sake unless training a sprint-specific demand.

**Evidence confidence**: STRONG EMERGING for VLaMax as a conceptual framework; PRELIMINARY for VLaMax-guided prescription algorithms (no head-to-head RCTs vs standard %FTP-based prescription as of 2026-05).

### VO2max Progression — Advanced Formats

| Format | Structure | When to Use |
|--------|-----------|-------------|
| Decreasing rest | 4×4min @ 115%, rest: 4/3/2/1min | Late in VO2max block; builds fatigue resistance |
| Ramp-to-VO2max | 3-4× (5min ramp 90%→120%) + 3min rest | Teaches progressive effort; good for pacing practice |
| Tabata-style | 6-8× (20s max / 10s rest) | Anaerobic + VO2max crossover; use sparingly (high neuromuscular stress) |

**Cadence guidance for VO2max:** 95-105 rpm preferred — high leg speed reduces peripheral fatigue and shifts stress to central cardiorespiratory system.

### Over-Under Progression

| Level | Interval Structure | Total Work Time | Est. TSS (session) |
|-------|-------------------|-----------------|---------------------|
| OU-1 | 3×(2min over + 2min under) | 12min | 55-65 |
| OU-2 | 3×(3min over + 2min under) | 15min | 65-75 |
| OU-3 | 4×(3min over + 2min under) | 20min | 70-80 |
| OU-4 | 4×(4min over + 2min under) | 24min | 75-85 |

Over = 105-110% FTP. Under = 90-95% FTP.

### Neuromuscular Sprints (Optional)

Neuromuscular work develops peak power output and recruits Type II fibers without significant cardiovascular cost. Heavy strength training (see `references/durability_strength.md` → Concurrent Training) is the primary neuromuscular driver; on-bike sprints supplement and translate strength to cycling-specific recruitment patterns.

**When to include:**
- Race preparation for events with sprints, attacks, or punchy climbs
- Outdoor riding readiness (the Block 2/3 outdoor rides showed peak sprints to 514W and 624W — latent neuromuscular capacity that ERG training does not develop)
- Variety / mental break during a SS-heavy block
- Once every 1–2 weeks; never the day before a key VO2max or threshold session

**When NOT to include:**
- During recovery weeks
- During VO2max blocks where short intervals already provide neuromuscular stimulus
- When fatigued (RPE elevated, TSB <−25)

| Level | Format | Sets × Reps | Recovery | Cadence |
|-------|--------|-------------|----------|---------|
| NM-1 | Standing-start sprints | 4–6× (10s all-out) | 3min full Z1 | Self-selected (start ~50 rpm, accelerate) |
| NM-2 | Seated sprints | 6–8× (10–15s all-out) | 3–5min full Z1 | 100–120 rpm |
| NM-3 | Mixed sprint sets | 2 sets × 4× (15s all-out) | 5min between sets, 3min between reps | Vary each rep |
| NM-4 | Torque sprints | 6× (10s @ low cadence 50–60 rpm, max effort) | 5min full Z1 | <60 rpm — emphasizes force |

**Coaching points:**
- "All-out" means *truly* all-out — no pacing. Power output >150% FTP expected; 200%+ for trained sprinters.
- Full recovery between reps. If power on rep 4 is >10% below rep 1, recovery was insufficient — extend rest or reduce volume.
- Total session TSS is low (30–50) — these are not load-building sessions, they are skill/capacity sessions.
- Pair with a Z2 endurance session before or after on the same day if total TSS is too low (e.g., 20min Z2 → sprint set → 20min Z2 cooldown).

**Evidence confidence**: ESTABLISHED for heavy strength → on-bike neuromuscular transfer (Llanos-Lagos 2025; Rønnestad 2010, 2015). PRACTITIONER CONSENSUS for specific on-bike sprint protocols — no formal RCT validates one format over another.

---

## Warmup and Cooldown Standards

### Standard Warmup (10 minutes)
1. 5min ramp 40% → 65% FTP
2. 2min @ 75% FTP
3. 2min ramp 75% → 95% FTP
4. 1min @ 50% FTP (recovery before main set)

### Short Warmup (5 minutes)
1. 3min ramp 40% → 70% FTP
2. 2min @ 75-80% FTP

### Standard Cooldown (5 minutes)
1. 5min ramp 55% → 35% FTP

### Recovery Intervals
- Between SS intervals: 5min @ 50-55% FTP
- Between Threshold intervals: 5min @ 50-55% FTP
- Between VO2max intervals: equal to work duration @ 40-50% FTP
- Between Over-Under sets: 5min @ 50-55% FTP

---

## FTP Test Protocols

### 20-Minute Test
- 10min warmup (ramp 40% → 70%)
- 3×1min @ 100% with 1min rest (openers)
- 5min easy
- 20min all-out (target: highest sustainable power)
- 5min cooldown
- **FTP estimate**: 20min average × 0.95
- **Individual variation**: The 0.95 multiplier is a population average. Athletes with high anaerobic capacity (strong 1-5min power relative to FTP) may need 0.90-0.93; those with low anaerobic capacity may need 0.96-0.98. If prescribed threshold intervals consistently feel too easy or too hard after a test, adjust FTP by 2-3% rather than retesting.
- **ZWO**: set `ftptest="1"` on workout element

### Ramp Test
- Start at 100W, increase 20W every minute until failure
- **FTP estimate**: last completed 1-minute average × 0.75
- **Individual variation**: The 0.75 multiplier is a population average (range 0.72-0.80). Athletes with high VO2max relative to FTP may overestimate by 5-15% (Lillo-Beviá & Pallarés, 2020). Cross-validate with session RPE — if threshold sessions feel like RPE 9-10 instead of 7-8, FTP is likely overestimated.
- **ZWO**: set `ftptest="1"` on workout element

### Critical Power (CP) / eFTP — No Extra Test Required

intervals.icu continuously fits a power-duration curve from all rides and derives an **eFTP** (estimated FTP) and Critical Power. CP is the asymptote of the power-duration relationship — arguably the most defensible threshold model — and updates whenever the athlete produces a hard 3–12 min effort in normal training. Use it as a **zero-cost cross-check**: if eFTP and the last field test agree within ~3%, zones are solid; if eFTP runs persistently above the set FTP, the field test (or its pacing) under-represented true threshold.

A deliberate **CP test** — a fresh ~3–5 min max effort plus a ~12–20 min max effort, well-spaced or on separate days — yields a clean two-point CP and removes the single-effort pacing dependency of the 20-min test.

### Choosing a Protocol

| Use… | When |
|---|---|
| **20-minute test** | Athlete paces well off a known FTP; wants a single-session number; rides with a `show_avg` HUD to pace by average. |
| **Ramp test** | Athlete has a **history of mis-pacing the 20-min test** (starting too hard or too soft); wants a pacing-independent number; is time-limited. The ramp removes the pacing variable — you simply ride to failure. |
| **CP / eFTP (intervals.icu)** | Always available as a free cross-check. Prefer as the *primary* threshold source for athletes who train consistently with hard 3–12 min efforts, or whenever a field test's validity is in doubt. |

**Decision rule:** if the athlete has mis-paced the 20-min test on 2+ occasions, switch them to the **ramp test** as the standard protocol, or adopt **intervals.icu eFTP/CP** as primary with the 20-min as occasional confirmation. Do not keep re-running a protocol whose dominant error source is a pacing skill the athlete has repeatedly shown they lack.

### Mid-Plan FTP Update

When an FTP test occurs mid-plan (e.g., scheduled Week 4 test, or user does an ad-hoc test):

1. **Update `active_plan.md`**: Set new FTP value and Last Tested date in Athlete Profile section
2. **Power targets auto-adjust**: .zwo files use % FTP — regenerate remaining workouts with new FTP value
3. **TSS target recalculation**:
   - If FTP change > 5%: recalculate remaining weeks' target TSS to maintain intended training stress relative to new threshold
   - If FTP change ≤ 5%: keep existing TSS targets (the absolute watt shift is small enough that session difficulty stays appropriate)
4. **Regenerate .zwo files**: Regenerate current week's remaining pending sessions and all future weeks with new FTP

> **FTP rounding**: Setting a working FTP slightly above or below the test-estimated value is a valid coaching decision (e.g., estimated 198W → set 200W to target next-block progression). Document the rationale in the Adaptation Log when rounding by more than 2W.

---

## Block Selection Logic

### Sub-prompt contract

- **Inputs:** athlete goal (one of the 5-goal taxonomy below — `ftp_improvement`, `gravel_endurance`, `criterium`, `tt`, `base`); CTL/ATL/TSB from `pmc_calculator.py --bootstrap`; weeks since last FTP test (or `unknown`); recent training history (Z2-heavy vs intensity-heavy vs mixed); last 2–3 completed blocks from `plans/block_history.md` (if present); climate context (tropical / indoor — relevant for Heat Adaptation overlay).
- **Outputs:** block type recommendation (primary block + any secondary work) + block length (3 / 4 / 5 weeks) + key metric to track + any overlays (Heat Adaptation, concurrent strength). Stimulus-rotation flag fires when last 2–3 blocks were sweet-spot-dominant; surfaces a VO2max or Polarized rotation option with rationale rather than auto-routing to another FTP Builder.
- **Invocation:** `workflows/plan.md` → Create Plan Step 4 (Design block structure). Selection produces a *proposal*; athlete confirms before `plans/active_plan.md` is written (Coaching Process Rule 1 / Step 2b Validation Gate).

When creating a plan, Claude routes on the athlete's **goal** first, then applies fitness-state modifiers (CTL, TSB, FTP test recency).

### Goal taxonomy (5 goals — pick the closest match)

| Goal ID | Athlete intent | Primary Block | Secondary Work | Default Block Length | Key Metric to Track |
|---|---|---|---|---|---|
| `ftp_improvement` *(default)* | Raise 20-min sustainable power. Athlete has no specific event; just wants to "get fitter." | FTP Builder (4-wk) | None — focused stimulus | 4 wk | 20-min peak power; FTP retest at week 4 |
| `gravel_endurance` | Long mixed-surface events (2–6 h gran fondos, gravel races, sportives). Durability matters more than peak power. | Endurance Block + extended Saturday long-ride progression | Sweet Spot 1×/wk for FTP support; concurrent strength 2×/wk | 6–12 wk (key to event date) | Sat long-ride NP and cardiac drift; durability = power in final 1/3 of long ride; CTL build |
| `criterium` | Short repeated-attack racing (40–90 min crits with surges, sprints). Needs anaerobic capacity and repeatability. | VO2max Block | Sprint/neuromuscular (NM-2 or NM-3) 1×/wk; Threshold 1×/wk to maintain FTP base | 4 wk (repeated 2–3 cycles for crit season) | 1-min and 5-min peaks; sprint repeatability (rep-4 power vs rep-1) |
| `tt` | Sustained threshold events (20–60 min individual time trials, hill climbs). Pure threshold + aero hold. | FTP Builder + extended Threshold intervals (2×20 → 2×30 → 2×40) | VO2max once every 2 weeks (ceiling-raising); aero-position practice on Sat long ride | 4–6 wk | 20-min and 60-min FTP; sustained aero-position power hold |
| `base` | Off-season or post-event aerobic base building. No event in next 12 weeks. | Polarized Block (or Endurance for athletes <6 h/wk) | Concurrent strength 2×/wk | 8–12 wk continuous (no taper needed) | CTL build trajectory; resting HR trend; cardiac drift trend on Z2 rides |

**Selection notes:**
- If the athlete's intent doesn't fit cleanly, ask: "Are you targeting a specific event in the next 12 weeks?" Yes → match goal to event type. No → `ftp_improvement` (default) or `base`.
- Goal can change between blocks (e.g., `base` → `ftp_improvement` → `criterium` over 6 months). Each block creation is an independent goal selection.
- Goal is recorded in `plans/active_plan.md` → Athlete Profile → Goal field. Used by the Weekly Review workflow to interpret peak-power deltas in the right context (e.g., 1-min peak gain matters more for `criterium` than for `tt`).

### Fitness-state modifiers (apply AFTER goal selection)

These adjust the block volume/intensity once the block type is picked.

1. **Recent training history**: if athlete has been doing primarily Z2 work → start with one extra SS-focused week before main goal block (avoids intensity shock).
2. **Current FTP test recency**: if >8 weeks since last test → start with FTP test in Week 1.
   - Also applies when FTP is self-reported with no test history — see SKILL.md → Coaching Process Rules → Rule 4
   - Frame as "baseline assessment ride" to reduce test anxiety
   - All power targets are **provisional** until field test is completed
3. **CTL level**:
   - CTL < 30: start conservative (reduce baseline TSS by 10%)
   - CTL 30-60: normal progression
   - CTL > 60: can handle aggressive progression (+5% additional)
4. **TSB at plan start**:
   - TSB < -20: add recovery week before starting build
   - TSB -20 to +10: normal start
   - TSB > +10: can start at slightly elevated TSS
5. **Block-history rotation**: check the last 2–3 completed blocks in `plans/block_history.md`. If the athlete has done **2+ consecutive FTP Builder (or otherwise sweet-spot-dominant) blocks**, do NOT auto-route `ftp_improvement` → another FTP Builder. After ~8–12 weeks of the same stimulus the higher-yield move is a **stimulus rotation** — a VO2max block (raise the aerobic ceiling) or a Polarized block, then return to FTP Builder to convert the raised ceiling. Present the rotation option to the athlete with the rationale. A stalled FTP across consecutive same-shaped blocks is a stimulus-monotony signal, not a reason to build a fourth identical block.
6. **Tropical / indoor-climate athletes**: for an athlete who trains primarily indoors in a hot-humid climate (Singapore, SE Asia), proactively offer a **Heat Adaptation overlay** (see `references/durability_strength.md` → Heat Adaptation) at plan creation — air-conditioned indoor training "loses" the free climate stimulus, and the plasma-volume gain transfers partially to cool-condition performance. Surface it as a standing option; don't wait for the athlete to ask.

### Flexible Block Lengths

Default block length is 4 weeks (3 build + 1 recovery). Adjust based on athlete response:

| Block Length | Structure | When to Use |
|-------------|-----------|-------------|
| **3-week** | 2 build + 1 recovery | Completion rate <85% in Week 3 across 2+ blocks; athlete consistently fatigues before recovery week; age 50+; returning from injury/illness |
| **4-week** (default) | 3 build + 1 recovery | Standard for most athletes; CTL 30-60; consistent training history |
| **5-week** | 4 build + 1 recovery | CTL >60 + completion rate >95% across 2+ blocks; experienced athlete with high training age (5+ years); handles progressive overload well without performance decline in Week 3 |

**Selection heuristics:**
- After completing a 4-week block: if completion rate was <85% in Week 3, suggest switching to 3-week blocks
- After completing two 4-week blocks at >95% completion: offer 5-week block option
- If athlete explicitly reports feeling run down by Week 3 in multiple blocks: switch to 3-week
- 3-week blocks have faster recovery cycles but slower total progression; 5-week blocks offer more stimulus per cycle but higher fatigue risk
