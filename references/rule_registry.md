# Rule Registry — Orphan-Prevention Catalogue

This registry catalogues every **orphan-prone standing rule** in the skill's reference docs and maps each to the workflow that surfaces it. It exists so no conditional coaching rule depends on the coach remembering a reference doc. Built by audit workstream W4 (`audits/cycling-coach-w4-orphaning-design-2026-05-21.md`).

## What "orphan-prone" means

A rule is orphan-prone when ALL hold: it is a standing/situational coaching rule (a guardrail, a conditional adjustment, an abort criterion, a hygiene rule); it is **conditional** — applies only in specific circumstances, so it is easy to forget; it lives in a reference doc; and it is not already explicitly surfaced in a workflow. Core mechanics used on every task (zone boundaries, NP/IF/TSS formulas, progression tables) are NOT orphan-prone — they are the substance of the work and cannot be forgotten.

## Two rule classes, two surfacing mechanisms

- **coach-internal** — a process/design decision the coach acts on. Surfaces as a `Checks applied` checklist line inside the relevant workflow step. The athlete sees only the result.
- **athlete-facing** — a calibration/expectation the athlete must read directly. Surfaces inline + conditional in the workflow's output template. No standing block.

## Maintenance convention

**New standing rule → registry.** When a new conditional/situational coaching rule is added to any `references/` doc, add a row here AND wire its workflow surface point in the same change. A rule with no surface point is orphaned by definition.

## Status values

- `wired` — surfaced in its named workflow.
- `partial` — referenced somewhere but weakly; acceptable, lower priority. A future audit may promote it.
- `tracked` — catalogued, not yet wired.

## Tier 1 — fully orphaned (wired by W4)

| Rule | Source § | Class | Trigger | Surface point | Status |
|---|---|---|---|---|---|
| Realistic-gain guardrail | `periodization.md` → FTP Builder → Block-level coaching notes | athlete-facing | Plan creation; goal implies >4% FTP gain in one block | `plan.md` Step 9 plan summary — inline note after Block Structure | wired |
| ERG-variety Flex-day session | `periodization.md` → FTP Builder block notes | coach-internal | Designing any block with a Flex day | `plan.md` Step 5 Checks applied; `generate.md` Step 2 note | wired |
| Stimulus rotation | `periodization.md` → Block Selection Logic §5 | coach-internal | 2+ consecutive same-type blocks in `block_history.md` | `plan.md` Step 5 Checks applied | wired |
| Tropical / indoor heat-adaptation offer | `periodization.md` → Block Selection Logic §6 | athlete-facing | Athlete trains primarily indoors in a hot-humid climate | `plan.md` Step 5 Checks applied (decision) + Step 9 summary (offer) | wired |
| VO2max RPE persistence gate | `periodization.md` → VO2max Block notes | coach-internal | VO2max session analysed; RPE ≥9 or HR fails to reach range | `analyze.md` Analysis Checklist | wired |
| Max one progression level per week | `periodization.md` → Progressive Overload Tables | coach-internal | Designing the next week's interval progression | `plan.md` Step 5 Checks applied | wired |
| Aerobic base-squeeze flag | `periodization.md` → FTP Builder block notes | coach-internal | Weekly review; Z1–Z2 share < ~55% | `plan.md` Weekly Review Step 4 Checks applied | wired |
| 5-min peak gain continuity | `periodization.md` → Adaptation Decision Trees → Performance Indicators | coach-internal | Weekly review; 5-min peak up >5% week-over-week | `plan.md` Weekly Review Step 4 Checks applied | wired |
| FOR / NFOR / OTS tiering | `periodization.md` → Adaptation Decision Trees → RPE Trend Escalation | coach-internal | Elevated RPE persists after a 5-day FOR de-load | `plan.md` Weekly Review Step 4 Checks applied | wired |
| Durability metric (final-third) | `periodization.md` → Durability (Emerging Concept) | coach-internal | Analysing a ride >90 min | `analyze.md` Analysis Checklist | wired |
| Heat-block abort criteria | `periodization.md` → Heat Adaptation → Monitoring & Abort | coach-internal | Athlete is running a Heat Adaptation overlay | `analyze.md` Analysis Checklist | wired |
| Menstrual symptom autoregulation tiering | `menstrual_cycle_training.md` §4 | coach-internal | Female athlete logs menstrual symptoms | `advise.md` → Menstrual Cycle section — tier table | wired |

## Tier 2 — partially surfaced

Catalogued for completeness. The 8 `wired` rows below are cheap one-line sharpens applied by W4; the 11 `partial` rows are referenced weakly but acceptably — a future audit may promote them.

| Rule | Source § | Class | Trigger | Surface point | Status |
|---|---|---|---|---|---|
| Estimated-power analysis caveat | `workout_analysis.md` → Power Data Confidence | athlete-facing | Activity has no power meter (estimated power) | `analyze.md` Analysis Checklist — sharpened | wired |
| Ramp-test FTP individual variation | `periodization.md` → FTP Test Protocols → Ramp Test | athlete-facing | Interpreting a ramp-test FTP estimate | `analyze.md` Step 6 — sharpened | wired |
| Post-FTP-test protocol (2–3 days easy) | `workout_analysis.md` → FTP Test Post-Test Workflow | athlete-facing | An FTP test was detected and propagated | `analyze.md` Step 6 change summary — sharpened | wired |
| Polarized minimum-volume gate | `periodization.md` → Polarized Block intro | coach-internal | Athlete <6 h/week considering a Polarized block | `plan.md` Step 5 Checks applied — sharpened | wired |
| 3+ missed sessions = involuntary rest | `periodization.md` → Adaptation → Training Load Adaptation | coach-internal | 3+ sessions skipped in one week | `plan.md` Weekly Review Step 4 Checks applied — sharpened | wired |
| ACWR safe-zone pass | `periodization.md` → Adaptation → Workload Ratio | coach-internal | Weekly review; ACWR lands 0.8–1.3 | `plan.md` Weekly Review Step 4 Checks applied — sharpened | wired |
| Recovery-interval power targets | `periodization.md` → Warmup/Cooldown Standards | coach-internal | Designing interval recovery segments | `generate.md` Step 4 validation table — sharpened | wired |
| Pre-threshold low-fiber rule | `fueling.md` → Pre-Ride Nutrition → Key Rules | athlete-facing | Prescribing a Threshold/VO2max session | `advise.md` Training Advice fueling line — sharpened | wired |
| Z2-strict RPE anchor | `training_zones.md` → Z2 Variability; `periodization.md` → Polarized | coach-internal | Every Z2 endurance ride | `advise.md` Recovery Prescription mentions RPE — no explicit anchor rule | partial |
| Individual Z2-ceiling offset (Meixner) | `training_zones.md` → Z2 Individual Variability Note | coach-internal | Calibrating an athlete's Z2 band | Stated in ref doc; absent from output templates | partial |
| Back-to-back intensity enforcement | `periodization.md` → TSS Distribution | coach-internal | Scheduling hard sessions within a week | Mentioned in `plan.md`; not a Step 5 validation check | partial |
| FTP retest trigger (20-min peak +3% w/w) | `periodization.md` → Adaptation → Performance Indicators | coach-internal | Weekly review; 20-min peak +3% week-over-week | `adaptation_rules.md` §6 has a stricter 2-session variant | partial |
| Concurrent strength frequency taper | `periodization.md` → Concurrent Training → Scheduling | coach-internal | Peaking/taper with concurrent strength | Stated in ref doc; absent from Race/Event Peaking workflow | partial |
| Concurrent strength phase pairing | `periodization.md` → Concurrent Training → Periodization | coach-internal | Athlete does concurrent strength; block transition | Table in ref doc; not referenced in `plan.md` | partial |
| Cadence-glycolytic modulation | `periodization.md` → VLaMax section | coach-internal | Prescribing VO2max / sweet-spot cadence | Cadence targets in zones table; rationale not surfaced | partial |
| Outdoor VI normalcy frame | `workout_analysis.md` → Indoor vs Outdoor Context | coach-internal | Analysing an outdoor ride | Guidance in ref doc; no VI line in `analyze.md` output | partial |
| Dual-transportable carb ratio (2:1) | `fueling.md` → Multiple Transportable Carbs | athlete-facing | Fuelling a session >90 min or >60 g/h | Explained in ref doc; not in fuel cues | partial |
| Gut-training progression | `fueling.md` → Gut Training Protocol | athlete-facing | New athlete / pre-race fuelling strategy | `plan.md` Step 9 has a fuel reference link only | partial |
| ERG-mode limitations education | `workout_analysis.md` → ERG Mode: Strengths & Limitations | coach-internal | Recommending sim/free-ride variety | Flex-day ERG-variety rule exists; the *why* is not surfaced | partial |

---
*Created by W4, 2026-05-21. Out of scope: the ERG long-rep design rule — owned by roadmap W6; it will be added here when W6 wires it.*
