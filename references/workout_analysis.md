# Workout Analysis Framework

## Table of Contents

- [Activity Data Extraction](#activity-data-extraction)
- [Key Metrics to Analyze](#key-metrics-to-analyze)
- [Power Data Confidence](#power-data-confidence)
- [Indoor vs. Outdoor Context](#indoor-vs-outdoor-context)
- [FTP Test Detection & Post-Test Workflow](#ftp-test-detection--post-test-workflow)
- [Structured Workout Analysis](#structured-workout-analysis)
- [Common Issues & Coaching Feedback](#common-issues--coaching-feedback)
- [Session Rating Framework](#session-rating-framework)
- [Weekly Load Analysis](#weekly-load-analysis)
- [Post-Workout Questions](#post-workout-questions)

## Activity Data Extraction

### From API Output (intervals.icu)

The analysis script (`scripts/intervals_icu_api.py`) outputs JSON with pre-computed and derived metrics.

**Primary metrics (from API):**
- **Moving Time** / **Elapsed Time**
- **Distance**
- **Average Power** / **Normalized Power** (NP)
- **Average Heart Rate** / **Max Heart Rate**
- **Kilojoules** (helps estimate intensity)
- **Elevation Gain**

**Derived metrics (calculated or pre-computed by intervals.icu):**
- **IF (Intensity Factor)** = NP ÷ FTP
- **TSS** = from `icu_training_load` or computed: (Duration_seconds × NP × IF) ÷ (FTP × 3600) × 100
- **Variability Index** = NP ÷ Avg Power

For zone boundaries, see `references/training_zones.md` → Power Zones.

## Key Metrics to Analyze

### Power Metrics

| Metric | What It Tells You | Good Range |
|--------|-------------------|------------|
| Average Power | Overall intensity | Context-dependent |
| Normalized Power (NP) | Physiological cost accounting for variability | Higher = harder workout |
| Intensity Factor (IF) | NP ÷ FTP | 0.60-0.75 endurance, 0.85-0.95 threshold |
| Variability Index (VI) | NP ÷ Avg Power | <1.05 steady, >1.10 variable |
| Training Stress Score (TSS) | Training load | See ranges by type below |

**Typical TSS ranges by session type:**

| Session Type | TSS Range | Duration |
|--------------|-----------|----------|
| Recovery | 20-30 | 30-45min |
| Endurance (Z2) | 50-80 | 60-120min |
| Sweet Spot | 60-90 | 60-90min |
| Threshold | 60-90 | 60-75min |
| VO2max | 50-70 | 45-60min |
| Long Ride | 100-200 | 2-4hrs |

### Heart Rate Metrics

| Metric | Analysis Focus |
|--------|----------------|
| Average HR | Overall cardiovascular demand |
| Max HR | Peak effort detection |
| HR:Power Ratio | Efficiency (lower = better) |
| Cardiac Drift | HR rise at constant power (fatigue indicator) |
| Time in HR Zones | Distribution of cardiovascular stress |

### Performance Indicators

| Indicator | Formula/Method | What It Reveals |
|-----------|----------------|-----------------|
| Efficiency Factor (EF) | NP ÷ Avg HR | Aerobic fitness (higher = fitter) |
| Power:Weight | Avg Power ÷ Body Mass | Climbing ability |
| Decoupling | (EF first half - EF second half) ÷ EF first half | Aerobic endurance |
| Variability Index (VI) | NP ÷ Avg Power | Ride steadiness |

### Variability Index (VI) Analysis

VI indicates how "smooth" or "surgy" a ride was:

| VI Range | Interpretation | Common Causes |
|----------|----------------|---------------|
| 1.00-1.02 | Very steady | Flat TT, ERG mode trainer |
| 1.02-1.05 | Steady | Structured trainer ride, flat roads |
| 1.05-1.10 | Moderate | Rolling terrain, some traffic |
| 1.10-1.20 | Variable | Hilly terrain, group ride dynamics |
| 1.20-1.50 | Very variable | Stop-start traffic, crit racing |
| >1.50 | Extremely variable | Urban commute, heavy traffic, MTB |

**Coaching implications:**
- High VI (>1.20): NP overstates actual training stress; rider may feel less fatigued than TSS suggests
- Low VI (<1.05): Excellent for threshold/FTP work; continuous stress on energy systems
- Outdoor riding in urban environments (e.g., Singapore) typically VI 1.30-1.70 due to traffic lights and terrain

## Power Data Confidence

Check `power_data_quality` and `data_warnings` in the script output before analyzing.

| `power_data_quality` | Meaning | Reliable Metrics | Unreliable Metrics |
|----------------------|---------|------------------|--------------------|
| `measured` | Real power meter (has_power=true) | All: NP, IF, TSS, peaks, zones, VI | — |
| `estimated` | No power meter (has_power=false) | HR, duration, distance, cadence | NP, IF, TSS, peaks, zones, VI — treat as rough estimates only |

**When power is estimated:**
- Caveat all power-based analysis: "Note: power data is estimated (no power meter) — treat values as approximate"
- Focus feedback on HR, RPE, duration, and cadence instead
- Do NOT rate interval execution quality based on estimated power
- Do NOT recommend FTP changes based on estimated data

## Indoor vs. Outdoor Context

Check `context` field (`indoor` / `outdoor`) from the `trainer` flag.

| Metric | Indoor (Zwift/trainer) | Outdoor |
|--------|----------------------|---------|
| **VI** | 1.00-1.05 expected (ERG mode); >1.10 = ERG issue or mode off | 1.05-1.20 normal; urban stop-start traffic = 1.30-1.70 |
| **Pacing** | Near-perfect possible; assess strictly | Traffic, terrain, wind affect consistency; assess leniently |
| **Power fade** | Meaningful — controlled environment | May reflect route profile, not fatigue |
| **HR response** | Heat/cooling dependent on fan setup | Ambient conditions, wind cooling |
| **Cadence** | Very stable expected | Variable with terrain |

**Coaching implications:**
- Indoor VI > 1.10: Investigate ERG mode, gearing, or cadence instability
- Outdoor VI 1.10-1.30: Normal for rolling terrain, do not penalize
- Outdoor VI > 1.30 in urban environments: Expected due to traffic lights and frequent stops — focus on interval-specific power, not overall VI

## FTP Test Detection & Post-Test Workflow

The script auto-detects FTP tests via `metrics.ftp_test` when:
- Activity name contains FTP/ramp/test keywords
- 20-minute peak power exists within a 30-90min ride

### When FTP test is detected:

1. **Report test results:**
   - 20-min test: `estimated_ftp_20min` = 20min avg × 0.95
   - Ramp test: `estimated_ftp_ramp` = last 1min avg × 0.75
2. **Compare to current FTP:** Show old vs. new, percentage change
3. **Recommend action:**
   - If increase > 3%: "Update FTP to [new value] and recalibrate training zones"
   - If within 3%: "FTP stable — current setting is appropriate"
   - If decrease: "FTP may have dropped — consider fatigue, test execution, or rest before retesting"
4. **Recalculate zones:** Show new Z1-Z7 watt ranges at updated FTP
5. **Next steps:** 2-3 days easy riding before resuming structured training at new FTP

For FTP estimation formulas and individual variation ranges, see `references/training_zones.md` → FTP Estimation Methods.

### Testing Cadence

- **Build phases**: Retest every 4-6 weeks (aligns with end of training blocks)
- **Maintenance phases**: Retest every 6-8 weeks
- **Trigger-based retesting**: When performance data consistently suggests FTP has shifted >5% — e.g., workout targets feel too easy/hard for 2+ consecutive sessions, or peak power data shows sustained shift
- **Post-test protocol**: 2-3 days easy riding before resuming structured work at new FTP
- **Avoid retesting**: During recovery weeks (fatigue masks true FTP), within 48hrs of a hard session, or when illness/travel may skew results

## Structured Workout Analysis

### Interval Session Checklist

1. **Warm-up Quality**
   - Duration adequate? (10-15min minimum)
   - Gradual power increase?
   - Include openers/activation?

2. **Interval Execution**
   - Hit target power range?
   - Consistent across sets?
   - Pacing strategy (even vs. declining)?
   - Recovery quality between intervals?

3. **Fatigue Pattern**
   - Power decline set-to-set?
   - HR creep at same power?
   - RPE alignment with data?

4. **Cool-down**
   - Sufficient duration? (5-10min minimum)
   - Power reduction gradual?

5. **When to Modify or Stop**
   - Power >10% below target for 2+ consecutive intervals with elevated HR → stop main set, cool down
   - Unable to reach target power from interval 1 despite adequate warm-up → accumulated fatigue; convert to Z2 or rest
   - Unusual pain, dizziness, or chest tightness → stop immediately
   - HR fails to recover between intervals (stays >90% HRmax in rest) → reduce remaining interval count or extend recovery
   - Mental/motivation collapse → complete current interval, then reassess; converting to easier work is better than quitting entirely
   - **Rule of thumb**: A modified workout > a forced workout > a skipped workout. Adjust intensity down 5-10% rather than abandoning if the athlete is close to targets.

### Endurance Ride Analysis

1. **Zone Distribution**
   - Time in Z2: >80% for pure endurance
   - Avoid Z3 "gray zone" drift
   - Short Z4+ spikes acceptable

2. **Pacing**
   - VI < 1.05 for steady effort
   - Negative split power = strong finish
   - Cardiac drift scale: <5% = well-paced, good aerobic fitness; 5-8% = acceptable, consider fueling or extended warmup; >8% = flag for aerobic base needs, fueling, or accumulated fatigue

3. **Fueling Indicators**
   - Power fade in final third?
   - HR spike without power increase?

### Workout-Type-Specific Success Criteria

#### Sweet Spot Sessions (88-94% FTP)
- **Power**: Sustained within 88-94% FTP; minimal drift across intervals
- **HR**: Gradual rise to Z3-Z4 HR, then plateau — plateau indicates aerobic system handling load
- **Pacing**: Even or slight negative split preferred; >5% fade = started too hard or under-fueled
- **Cadence**: 85-95 rpm steady
- **Failure mode**: HR fails to plateau (keeps climbing) = intensity too high or fatigue; power sags in final third = fueling issue
- **Expected IF**: 0.80-0.88 | **Expected TSS/hr**: ~60-75

#### Threshold Sessions (90-105% FTP)
- **Power**: Even pacing critical; <3% variation across intervals
- **HR**: Should reach Z4 (95-105% LTHR) by mid-interval and hold; failure to reach = under-target; exceeding early = over-target
- **Pacing**: Negative splits ideal; positive split >3% = started too aggressively
- **Cadence**: 90-100 rpm
- **Failure mode**: Power drops >5% in final interval = reduce interval count or duration next session; HR at ceiling with power declining = session too hard for current fitness
- **Expected IF**: 0.85-0.95 | **Expected TSS/hr**: ~70-90

#### VO2max Sessions (105-120% FTP)
- **Power**: Target range more important than precision; +/-5% acceptable due to high intensity
- **HR**: Must reach >90% HRmax by end of interval — if not reaching this, intensity is too low or intervals too short
- **Recovery**: HR should drop to <75% HRmax between intervals; if not recovering, extend rest or reduce interval count
- **Cadence**: 95-105 rpm (high leg speed reduces peripheral fatigue)
- **Failure mode**: Unable to reach target power from interval 1 = accumulated fatigue, consider rest day; power OK but HR not reaching >90% HRmax = intervals may be too short
- **Expected IF**: 0.85-0.95 | **Expected TSS/hr**: ~70-90

#### Over-Under Sessions
- **Over segments** (105-110% FTP): Brief lactate accumulation; power precision less critical than sustaining effort
- **Under segments** (90-95% FTP): Partial lactate clearance under moderate stress — **HR recovery in under segments is the key metric**
- **Success criteria**: HR drops 5-10 bpm during under segments (shows clearance capacity); HR fails to drop = clearance overwhelmed, reduce over intensity or extend under duration
- **Pacing**: Smooth transitions critical; avoid spiking above over-target on transitions
- **Failure mode**: Under-segment HR stays pinned at over-segment levels = athlete has exceeded clearance capacity; stop or convert remaining to steady sweet spot
- **Expected IF**: 0.82-0.90 | **Expected TSS/hr**: ~65-80

## Common Issues & Coaching Feedback

### Issue: Power Fades in Later Intervals

**Possible Causes:**
- Starting too hard (pacing)
- Insufficient recovery between sets
- Accumulated fatigue (training load)
- Fueling/hydration issues

**Coaching Response:**
- Review target power vs. actual first interval
- Check recovery heart rate between sets
- Assess weekly training load context
- Recommend conservative start strategy

### Issue: HR Higher Than Expected at Power

**Possible Causes:**
- Accumulated fatigue
- Heat/humidity
- Dehydration
- Illness onset
- Overreaching

**Coaching Response:**
- Compare to similar recent sessions
- Check resting HR trend
- Assess sleep/recovery quality
- Consider backing off intensity

### Issue: Can't Reach Target Power

**Possible Causes:**
- FTP set too high
- Insufficient warm-up
- Fatigue from prior training
- Mental/motivational factors

**Coaching Response:**
- Review recent FTP test validity
- Extend warm-up with openers
- Check training load vs. recovery
- Adjust targets or reschedule

### Issue: High Variability Index

**Possible Causes:**
- Outdoor terrain/traffic
- Poor pacing discipline
- ERG mode not engaging
- Zwift course selection

**Coaching Response:**
- Choose flatter routes for steady work
- Use ERG mode for precision
- Practice pacing with shorter segments
- Review power smoothing/display

## Session Rating Framework

### Execution Score (1-5)

| Score | Description |
|-------|-------------|
| 5 | All intervals within 2% of target, perfect pacing |
| 4 | 90%+ intervals hit target, minor pacing issues |
| 3 | Most intervals close, some missed targets |
| 2 | Struggled significantly, multiple missed intervals |
| 1 | Unable to complete, major issues |

### Adaptation Signals

**Positive Adaptations:**
- Same power at lower HR over weeks
- Higher NP at same RPE
- Faster HR recovery between intervals
- Less power fade in later intervals
- PR on benchmark efforts

**Concern Signals:**
- Elevated HR at baseline powers
- Declining power at same RPE
- Slower HR recovery
- Increased perceived effort
- Motivation/mood decline

## Weekly Load Analysis

For CTL/ATL/TSB definitions, PMC formulas, and ACWR thresholds, see `references/periodization.md` → Adaptation Decision Trees.

### Load Recommendations

| TSB Range | Status | Recommendation |
|-----------|--------|----------------|
| > +25 | Very fresh | May be detrained, increase load |
| +10 to +25 | Fresh | Good for racing/testing |
| -10 to +10 | Neutral | Normal training |
| -10 to -30 | Fatigued | Monitor, plan recovery |
| < -30 | Very fatigued | Reduce load, recovery priority |

> **PMC limitations**: TSS is intensity-blind — a 100 TSS sweet spot ride and a 100 TSS VO2max session register identically in the PMC model despite very different physiological stress and recovery demands. Use RPE trends and HR indicators alongside PMC to capture what TSS alone cannot.

## Session RPE (Rate of Perceived Exertion)

After each workout analysis, prompt the athlete for session RPE on the modified Borg 1-10 scale:

| RPE | Descriptor | Typical Session |
|-----|-----------|-----------------|
| 1-2 | Very easy | Recovery spin, Z1 |
| 3-4 | Easy | Z2 endurance |
| 5-6 | Moderate | Tempo, sweet spot |
| 7-8 | Hard | Threshold, VO2max |
| 9 | Very hard | All-out intervals, FTP test |
| 10 | Maximal | Sprint, can't sustain |

### RPE:Power Mismatch Detection

Compare session RPE against objective intensity (IF) to detect fatigue, underestimated FTP, or other issues:

| Scenario | RPE | IF | Interpretation | Action |
|----------|-----|-----|----------------|--------|
| **Fatigue signal** | 7+ (hard) | < 0.75 | Perceived harder than data — likely accumulated fatigue, poor sleep, stress, or illness | Flag fatigue concern; ask about sleep/stress/recovery; consider extra rest day |
| **FTP underestimated** | ≤ 5 (easy) | > 0.85 | Session felt easy but was objectively hard — FTP may be set too low | Flag FTP retest; do not auto-adjust (confirm with actual test) |
| **Normal match** | 5-6 | 0.75-0.85 | RPE matches intensity — training appropriately calibrated | No action needed |
| **Normal match** | 7-8 | 0.85-1.00 | RPE matches intensity — hard session felt hard | No action needed |
| **Overcooking** | 9-10 | 0.75-0.85 | Extreme effort for moderate intensity — possible illness, deep fatigue, or dehydration | Strong fatigue flag; recommend 2-3 easy days before next hard session |

### RPE Trend Monitoring

Track session RPE over weeks:
- **Rising RPE at same IF for 2+ weeks**: Functional overreaching — recovery needed soon
- **Falling RPE at same IF**: Positive adaptation — fitness improving
- **Consistently high RPE (8+) for all sessions**: Training load too high or insufficient recovery

### Obsidian Frontmatter Integration

Store RPE in workout review frontmatter:
```yaml
rpe: 7
rpe_match: "normal"  # or "fatigue_signal", "ftp_underestimated", "overcooking"
```

## Post-Workout Questions

1. Did you hit your target power/HR?
2. **How hard did that feel? (1-10 RPE)** — use for RPE:Power mismatch detection
3. Any unusual sensations or discomfort?
4. Sleep/recovery quality leading in?
5. Nutrition/hydration before and during?
6. Equipment/setup issues?
