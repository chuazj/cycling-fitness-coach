# Cycling Training Zones Reference

## Power Zones (FTP-Based)

| Zone | Name | % FTP | RPE | Description | Training Purpose |
|------|------|-------|-----|-------------|------------------|
| Z1 | Active Recovery | <55% | 1-2 | Very easy, conversational | Recovery, warm-up, cool-down |
| Z2 | Endurance | 56-75% | 3-4 | Comfortable, sustainable for hours | Aerobic base, fat oxidation |
| Z2-low | Recovery / Lower Endurance | 55-65% | 3 | Very conversational, no breath effort | Active recovery, cardiac output base |
| Z2-high | Upper Endurance | 65-75% | 4 | Conversational with mild effort | Fat-oxidation peak, mitochondrial signaling |
| Z3 | Tempo | 76-90% | 5-6 | "Comfortably hard" | Muscular endurance, efficiency |
| Z4 | Threshold | 91-105% | 7-8 | Race pace, 20-60min sustainable | FTP improvement, lactate tolerance |
| Z5 | VO2max | 106-120% | 9 | Hard, 3-8min efforts | Aerobic capacity, power at VO2max |
| Z6 | Anaerobic | 121-150% | 10 | Very hard, 30s-3min | Anaerobic capacity, repeatability |
| Z7 | Neuromuscular | >150% | 10+ | Max effort, <30s | Peak power, sprint ability |

## Zone 2 — Individual Variability Note

Z2 boundaries are population approximations. Meixner et al. (2025, *Translational Sports Medicine*, 50 trained cyclists) found coefficients of variation (CV) of 6–29% across Z2 boundary metrics — i.e., one athlete's "true Z2 ceiling" (VT1 / FatMax) may sit at 60% FTP while another's sits at 75%.

**Practical implication**: %FTP is the default prescription, but **anchor by RPE and breathing** when calibrating:

- **RPE 3 (very light, fully conversational, no breath effort)** → solidly Z2-low
- **RPE 4 (light with mild breath effort, still conversational)** → upper Z2 / approaching VT1
- **RPE 5+ (talking becomes choppy)** → drifted into Z3 — reduce power 5–10W

If Saturday Z2 sessions persistently feel >RPE 4 at 65–70% FTP, your individual Z2 ceiling is likely offset down — drop the power band rather than push through. The opposite (RPE 2 at 70% FTP) suggests room to push toward 73–75%.

This does not change the prescription default (56–75% FTP) but informs how to read your own signal.

---

## Sweet Spot Training

**Sweet Spot Zone**: 88-94% FTP (upper Z3 / lower Z4 overlap)

Benefits:
- High training stimulus with manageable fatigue
- Optimal "bang for buck" for FTP development
- Sustainable volume for time-crunched athletes

Typical protocols (shorter intervals can sit at the upper end of the band):
- 2x20min @ 88-92% FTP (core sweet spot)
- 3x15min @ 88-94% FTP (core sweet spot)
- 4x10min @ 90-94% FTP (upper sweet spot)

## Training Intensity Distribution

2024-2025 meta-analyses (Pla et al., *Sports Medicine*; Goulet et al., *JSMS*) show **no significant performance difference between polarized, pyramidal, and threshold-focused models** when total training load is matched. What matters more than the model is total load, consistency, and progressive overload.

WorldTour teams use a **pyramidal distribution** — most volume in Z1-Z2, moderate Z3-Z4 work, smaller Z5+ component — with progressive intensification toward competition (Mateo-March et al., 2025, *SJMSS*, 28 WorldTour cyclists).

### Training Models

- **Pyramidal (DEFAULT)**: Most training in Z1-Z2, meaningful Z3-Z4 (sweet spot/threshold), smaller Z5+ component. This is what the FTP Builder block implements. Validated by WorldTour practice and 2024 meta-analyses. Effective across all training volumes.
- **Polarized (HIGH-VOLUME ALTERNATIVE)**: ~80% Z1-Z2, ~0% Z3, ~20% Z4+. Eliminates the Z3 "no man's land." Supported by Seiler (2010) and Stoggl & Sperlich (2014). Consider when: training volume >8 hrs/week, plateau occurs on SS-heavy plans for 2+ blocks, or aerobic base needs development (high cardiac drift on Z2 rides).

Both approaches produce FTP gains. The FTP Builder block is pyramidal by design — it includes Z2 endurance days, Z3-Z4 sweet spot/threshold work, and Z5+ VO2max sessions within the same block.

## Heart Rate Zones (LTHR-Based)

| Zone | Name | % LTHR | Use When |
|------|------|--------|----------|
| Z1 | Recovery | <68% | Power data unavailable |
| Z2 | Aerobic | 69-83% | Long endurance rides |
| Z3 | Tempo | 84-94% | Tempo/SST validation |
| Z4 | Threshold | 95-105% | FTP efforts |
| Z5 | Anaerobic | >105% | VO2max+ efforts |

## Cadence Guidelines

| Workout Type | Target Cadence | Rationale |
|--------------|----------------|-----------|
| Endurance | 85-95 rpm | Efficient, aerobic |
| Sweet Spot | 85-95 rpm | Sustainable, moderate force |
| Threshold | 90-100 rpm | Higher turnover, less fatigue |
| VO2max | 95-105 rpm | Fast leg speed, cardiac focus |
| Force Work | 60-75 rpm | Strength emphasis |
| Spin-ups | 100-120 rpm | Neuromuscular, efficiency |

## Weekly Training Structure

### Build Phase (4-Day Default)

The canonical training week uses 4 days (matching `periodization.md` TSS distribution). Athletes with more availability can add sessions; this is the minimum effective structure.

| Day | Session Type | Duration | Key Metric | TSS Share |
|-----|--------------|----------|------------|-----------|
| Tue | Intervals (Threshold/VO2) | 60-75min | IF 0.85-0.95 | 25-30% |
| Thu | Sweet Spot or Intervals | 60-90min | IF 0.80-0.90 | 25-30% |
| Sat | Long Ride / Volume | 90-180min | IF 0.65-0.75 | 30-35% |
| Flex | Easy Endurance or Moderate | 45-60min | IF <0.75 | 10-20% |

No back-to-back hard days. Tue and Thu should target different energy systems when possible.

### Recovery Week

- Reduce volume by 40-50%
- Reduce intensity (no threshold+ work)
- Focus on technique, spin-ups
- Test FTP at end if adaptation plateau suspected

## Fatigue Indicators

> Flag rules below mirror the `--readiness-check` and `--wellness` script output. When this doc and the script disagree, the script wins — fix this doc.

**Yellow Flags** (modify training):
- RHR elevated ≥5 bpm vs 14-day baseline (requires ≥7 days of baseline history; flag is suppressed at shorter windows because daily RHR swings of 3-5 bpm are normal noise)
- **HRV below 7-day rolling band** (μ − 0.5σ, Plews/Buchheit methodology) — single-day below band fires yellow; requires ≥7 days of HRV history (same maturity guard)
- **HRV CV-trend rising**: last-7d CV ≥ prior-7d CV + 2.0pp (14-day split-window) — informational yellow, early autonomic-strain signal (CV widens before mean drops). Requires ≥14 days of HRV history
- Recovery score 34–66 (Whoop band; moderate readiness) — fires regardless of baseline depth (absolute thresholds). For session prescription, the coaching framework subdivides this at 50: Yellow-high 50-66 passes Threshold/SS; Yellow-low 34-49 caps at SS
- **Respiration +1.0/min above 14-day baseline** (early illness-onset signal; requires ≥7 days of baseline)
- **SpO2 nightly average <95%** — fires regardless of baseline depth (absolute threshold). Apply Apple Watch tiebreaker before holding: 3 spot readings ≥96% clears as wrist-PPG artifact (see `workflows/advise.md` → SpO2 cross-check)
- Sleep <6h last night — fires regardless of baseline depth
- Subjective fatigue / soreness / stress ≥4 (worst tier on intervals.icu 1–4 scale)
- Power:HR decoupling >5% early in ride (post-hoc, from activity analysis)
- Legs heavy at start of intervals
- Sleep quality declining

**Red Flags** (take recovery):
- Unable to hit target power
- RHR elevated ≥10 bpm vs 14-day baseline (requires ≥7 days of baseline history)
- **HRV below 7-day band 2 consecutive days** (de-load trigger; escalation, not duplicate — only the red fires, not yellow + red on the same day)
- Recovery score <34 (Whoop band; low readiness) — fires regardless of baseline depth
- **Respiration +2.0/min above 14-day baseline** (likely active illness; Z1 30min or full rest)
- **SpO2 nightly average <92%** — fires regardless of baseline depth. Significant desaturation; rest and check for illness / altitude / sleep apnea
- Motivation significantly decreased
- Persistent muscle soreness
- Illness symptoms

**Progression Signal** (positive — green-lights a TSS bump):
- **HRV ≥3 consecutive days above (μ + 0.5σ) of 7-day band AND CTL rising over last 7 days** → +5-10% TSS on next quality session. Mostly dormant in maintenance; matters during build blocks.

**Baseline maturity note:** `wellness_summary()` reports `baseline_maturity` and per-metric `baseline_sample_sizes`. Deviation-based flags (RHR, HRV, respiration) are auto-suppressed below n=7 history to avoid acting on single-night noise (HRV can swing ±15-25% night-to-night for healthy individuals). Recovery + sleep + subjective flags use absolute thresholds and fire regardless. n≥14 is the target for a "stable" baseline (HRV4Training convention).

**Recovery score notes:**
- Sourced from intervals.icu's `readiness` wellness field. Whoop populates this with its Recovery score (HRV + RHR + sleep + respiration roll-up, already baseline-calibrated, so absolute bands apply).
- Whoop bands: 0–33 red, 34–66 yellow, 67–100 green. `wellness_summary()` emits red/yellow flags at these thresholds; green produces no flag.
- For athletes on other wearables (Garmin Body Battery, Oura Readiness) that also push to intervals.icu via the same `readiness` field, the same thresholds apply — but recalibrate if their scoring distribution differs noticeably from Whoop's.
- **Recovery lag**: Whoop Recovery is computed from *last night's sleep* — which primarily processed *yesterday's* training. A yellow/red Recovery this morning usually reflects yesterday's session load, not today's plan. When you see a Recovery drop, interrogate yesterday's training first (load, intensity, late finish, alcohol, illness) before second-guessing today's planned session. The corollary: a hard session done in the evening will not show up as Recovery suppression until ~24h later.
- **3-day Recovery slope**: `recovery_slope_3day` in wellness output. A drop ≥10pt over 3 days is an early-warning trend that often precedes a single-day Recovery red — fires its own `recovery_slope` yellow flag.

**Respiration notes:**
- Sourced from Whoop via the `respiration` wellness field (breaths/min during sleep, typically 12-16 for healthy adults). Whoop folds it into the Recovery score, but a standalone deviation flag is more sensitive to illness onset because respiration rises 24-48h before Recovery formally drops.
- Flag fires when latest > baseline + 2.0/min AND baseline has ≥7 days of history. CV is typically <3% for healthy individuals — even +1.5/min is unusual.

## FTP Estimation Methods

1. **20-minute Test**: FTP = 20min avg power × 0.95 (range 0.90-0.98; athletes with high anaerobic capacity may need a lower multiplier)
2. **Ramp Test**: FTP = last completed minute avg × 0.75 (range 0.72-0.80; can overestimate FTP by 5-15% in some profiles)
3. **8-minute Test**: FTP = 8min avg power × 0.90 (range 0.86-0.92; Carmichael / Time-Crunched Cyclist protocol — useful when 20min is too long for the available session window)
4. **Hour of Power**: FTP = 60min avg power (gold standard)

For block templates, progression tables, and common prescriptions: see `references/periodization.md` → Training Blocks.
