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

**Yellow Flags** (modify training):
- Resting HR elevated >5 bpm
- HRV depressed >10%
- Power:HR decoupling >5% early in ride
- Legs heavy at start of intervals
- Sleep quality declining

**Red Flags** (take recovery):
- Unable to hit target power
- HR elevated >10 bpm baseline
- Motivation significantly decreased
- Persistent muscle soreness
- Illness symptoms

## FTP Estimation Methods

1. **20-minute Test**: FTP = 20min avg power × 0.95 (range 0.90-0.98; athletes with high anaerobic capacity may need a lower multiplier)
2. **Ramp Test**: FTP = last completed minute avg × 0.75 (range 0.72-0.80; can overestimate FTP by 5-15% in some profiles)
4. **Hour of Power**: FTP = 60min avg power (gold standard)

For block templates, progression tables, and common prescriptions: see `references/periodization.md` → Training Blocks.
