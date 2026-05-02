# Workflow: Training Advice, Mid-Week Check-In & Race Peaking

Covers Workflow 2 (training advice), Workflow 6 (mid-week check-in), and Workflow 7 (race/event peaking).

---

## 2. Training Advice

**Step 1:** Assess context before responding:
- Current FTP, weight, training age (check `plans/active_plan.md` → Athlete Profile; if no active plan, ask the athlete or check intervals.icu profile via `--use-athlete-profile`)
- Current block and phase (check `plans/active_plan.md` → Plan Overview + Current Week Schedule)
- Recent session load: count hard sessions in last 7 days, check for back-to-back intensity
- Fatigue signals: RPE trends, HR:Power drift, missed targets in recent sessions
- Schedule constraints: available days/hours this week

**Step 2:** Present your athlete situation assessment and confirm before prescribing (Coaching Process Rule 1). Verify zone confidence — if zones are unvalidated, flag uncertainty before using power targets (Rule 2).

**Step 3:** Reference zones and training blocks from `references/training_zones.md` and `references/periodization.md`.

**Step 4:** Prescribe with power targets as % FTP AND watts. Explain the "why" (Rule 3).

**Step 5:** Include fatigue watch-list for the prescription.

### Common Advice Scenarios

**"Should I lower my FTP?"** — Decision tree:
1. Check recent execution data: Are targets being hit within ±3%?
2. If yes → FTP is correct. Elevated RPE may be fatigue, heat, sleep, not FTP.
3. If no (missing by >5% on 2+ consecutive clean sessions) → consider lowering 3-5%
4. If disrupted sessions (bathroom break, ERG issues, schedule problems) → external cause, not FTP issue. Keep current.
5. **Never lower based on a single bad session.** Look for patterns across 2+ sessions.

**"I'm tired, should I train today?"** — Fatigue assessment:
1. Check resting HR — if +5 bpm above baseline → modify or rest
2. Ask about sleep quality (last 2 nights) and life stress
3. Prescribe based on fatigue level using the Recovery Prescription table below
4. **Rule of thumb**: Modified workout > forced workout > skipped workout

**Recovery Prescription table (fatigue → action):**

| Fatigue signal | Action | Session adjustment |
|---|---|---|
| Mild (RPE +1 vs typical, sleep ok) | Train as planned, monitor first 15 min | None — abort if RPE doesn't settle |
| Moderate (RHR +5 bpm OR poor sleep 1 night OR HRV down 5–10%) | Modify down one tier | SS → endurance Z2; threshold → SS; VO2max → threshold; cut duration 20% |
| High (RHR +5–10 bpm AND poor sleep 2+ nights, OR HRV down >10%, OR motivation absent) | Replace with active recovery | 30–45 min Z1, no intervals |
| Severe (RHR +10 bpm OR illness symptoms OR TSB <−30) | Full rest | No bike. Reassess next day. |
| Sick (above-neck only) | Rest 1–2 days then Z1–Z2 only | Per `references/periodization.md` → Illness/Injury rules |
| Sick (below-neck or systemic) | Full rest until 48h symptom-free | Per `references/periodization.md` → Illness/Injury rules |

**"Can I swap/skip a session?"** — Schedule adaptation:
1. Identify what the session targets (energy system, training stimulus)
2. Check if the stimulus is covered elsewhere this week
3. If swapping: keep hard/easy balance, avoid back-to-back hard days
4. If skipping: assess weekly TSS impact — one skipped session rarely matters; two+ may need week restructuring

**Output template:**

```
## Training Recommendation
**Context**: [Current FTP, available time, recent load/TSB]
**Assessment**: [Athlete's current state — fatigue, fitness, readiness]
**This Week's Plan**:
| Day | Session | Duration | Key Interval |
|-----|---------|----------|--------------|
| ... | ...     | ...      | ...          |
**Key Focus**: [Target adaptation and why this matters now]
**Watch For**: [Fatigue signals that would trigger plan adjustment]
```

---

## 6. Mid-Week Check-In

When user asks about plan status ("check my plan", "what's next", "plan status"):

**Step 1:** Read `plans/active_plan.md`. If the file does not exist, inform user that no active plan is found and suggest creating one via Workflow 4.

**Step 2:** Present current status:
```
## Plan Status: {Plan Type} — Week {N} ({Phase})

### This Week
| Day | Session | Target TSS | Status |
|-----|---------|------------|--------|
| ... | ...     | ...        | ...    |

### Next Session
**{Day}: {Session Name}**
- Key interval: {description}
- Duration: {X}min | Target TSS: {X}
- Execution notes: {pacing tips, cadence targets}
- ZWO file: {filename}

### PMC Snapshot
CTL: {X} | ATL: {X} | TSB: {X}
Status: {interpretation}
```

No data fetching or API calls needed — this is a read-only status check from the plan file.

---

## 7. Race/Event Peaking

When user mentions a target event ("I have a race on DATE", "peak for event", "taper for race"):

**Step 1:** Confirm event date and priority (A = primary event, B = secondary/fun).

**Step 2:** Read `references/periodization.md` → Race/Event Peaking Protocol.

**Step 3:** If `plans/active_plan.md` exists, read current PMC snapshot (CTL, ATL, TSB).
Otherwise, bootstrap PMC:
```bash
python scripts/pmc_calculator.py --bootstrap --days 90
```

**Step 4:** Calculate taper timing:
- Determine current TSB and target TSB (+5 to +20)
- Select protocol: 2-week taper (A-priority, CTL >50) or 1-week mini-taper (B-priority, CTL <50)
- Project TSB forward to confirm the taper duration achieves target freshness

**Step 5:** Present taper plan:
```
## Race Peaking: {Event Name} — {Date}
**Current**: CTL {X} | ATL {X} | TSB {X}
**Target race-day TSB**: +5 to +20
**Protocol**: {2-week / 1-week} taper starting {date}

### Taper Schedule
| Week | Day | Session | TSS |
|------|-----|---------|-----|
| ... | ... | ... | ... |

**Projected race-day TSB**: ~{X}
```

**Step 6:** Generate taper week .zwo files and update plan if active.
