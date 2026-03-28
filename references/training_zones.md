# Cycling Training Zones Reference

## Power Zones (FTP-Based)

| Zone | Name | % FTP | RPE | Description | Training Purpose |
|------|------|-------|-----|-------------|------------------|
| Z1 | Active Recovery | 0-55% | 1-2 | Very easy, conversational | Recovery, warm-up, cool-down |
| Z2 | Endurance | 55-75% | 3-4 | Comfortable, sustainable for hours | Aerobic base, fat oxidation |
| Z3 | Tempo | 75-90% | 5-6 | "Comfortably hard" | Muscular endurance, efficiency |
| Z4 | Threshold | 90-105% | 7-8 | Race pace, 20-60min sustainable | FTP improvement, lactate tolerance |
| Z5 | VO2max | 105-120% | 9 | Hard, 3-8min efforts | Aerobic capacity, power at VO2max |
| Z6 | Anaerobic | 120-150% | 10 | Very hard, 30s-3min | Anaerobic capacity, repeatability |
| Z7 | Neuromuscular | >150% | 10+ | Max effort, <30s | Peak power, sprint ability |

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

## Training Model Considerations

Two primary intensity distribution models are well-supported in sport science:

- **Sweet Spot / Threshold-focused**: High time-efficiency; most training stress at 88-105% FTP. Effective for time-crunched athletes (<6-8 hrs/week). Higher acute fatigue per session.
- **Polarized (80/20)**: ~80% Z1-Z2, ~20% Z4+, minimal Z3. Supported by Seiler (2010) and Stoggl & Sperlich (2014). May produce equal or superior long-term adaptations, especially when training volume is available (>8 hrs/week). Lower per-session fatigue, higher total volume.

Both approaches produce FTP gains. Sweet spot is the default in this program due to the athlete's time-constrained indoor setup, but consider shifting toward polarized distribution if: training volume increases, plateau occurs on SS-heavy plans, or aerobic base needs development (high cardiac drift on Z2 rides).

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
