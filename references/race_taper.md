# Race / Event Peaking Protocol

Reference for Claude-as-coach: taper structures and TSB projection for reverse-engineering a race-day peak.

When an athlete has a target event, reverse-engineer the taper from the event date to achieve optimal freshness (TSB +5 to +15 on race day — the conservative central estimate per Mujika & Padilla 2003; see the over-taper guardrail below before pushing toward the fresh end).

- For weekly adaptation decisions during a taper week → `references/weekly_adaptation.md`.
- For block design and progressive overload → `references/block_templates.md`.
- For concurrent-strength frequency tapering → `references/durability_strength.md` → Concurrent Training.

> **Citation currency** — taper citations last verified **2026-07-18** (Mujika & Padilla 2003 volume/pages confirmed against the primary source; Mujika 2010 supplement issue confirmed). Re-verify against current literature at every skill audit. Anchor authorities: `governance/bibliography.md#mujika-inigo` (taper structure, volume-decay with intensity-preservation, "sharpening" principle).

---

## 2-Week Taper (Standard)

Use for A-priority events or when CTL > 50.

Both structures below follow the same evidence-backed shape: **cut volume, hold intensity, keep frequency roughly intact** (Mujika & Padilla 2003, *Med Sci Sports Exerc* 35(7):1182–1187 → `governance/bibliography.md#mujika-inigo`). That review found peak performance gains of roughly 0.5–6% from a 7–21 day taper, with volume reductions of ~40–60% outperforming both smaller cuts and complete rest. Intensity is the variable that must **not** drop — Mujika (2010, *Scand J Med Sci Sports* 20(Suppl 2):24–31) argues the retained high-intensity work is precisely what preserves the adaptations the volume cut is meant to unmask. That is why every week below keeps at least one hard session or opener rather than going fully easy.

| Week | Volume vs. Build | Intensity | Key Sessions |
|------|-----------------|-----------|--------------|
| Race -2 | -30% volume | Maintain intensity (2 hard sessions) | 1× race-pace intervals + 1× short VO2max/openers |
| Race -1 | -50% volume | Reduce intensity (1 hard session) | 1× openers (3×2min @ 105%) + easy rides only |
| Race day | — | — | TSB target: +5 to +15 |

**Week -2 detail:**
- Tue: Race-pace intervals — 3×8min @ 100-105% FTP, 5min recovery (maintain sharpness)
- Thu: Short VO2max openers — 4×2min @ 115%, 2min recovery (neuromuscular activation)
- Sat: Z2 endurance — 60min (reduced from typical long ride)
- Flex: Rest or very easy 30min spin

**Week -1 detail:**
- Tue: Openers — 30min easy + 3×2min @ 105% FTP with 2min recovery
- Thu: Rest or 20min very easy spin
- Sat (Race day -1): 20min easy spin + 2×30s @ race pace (activation only)

## 1-Week Mini-Taper

Use for B-priority events, shorter races, or when CTL < 50.

> **Selection tiebreak (priority wins over CTL):** A-priority with CTL < 50 still gets the 2-week structure — the lighter base just means smaller absolute reductions; B-priority with CTL > 50 stays on the 1-week mini-taper (a 2-week taper costs more training than a B race is worth). **Event < 7 days away:** skip straight to the final-week structure of the matching protocol — cut volume immediately (~40-50%), keep 2-3 short openers, add no new intensity.

| Week | Volume vs. Build | Intensity | Key Sessions |
|------|-----------------|-----------|--------------|
| Race -1 | -40% volume | 1 opener session mid-week | 1× openers (3×2min @ 105%) + easy rides |

**Detail:**
- Mon: Rest
- Tue/Wed: Openers — 30min easy + 3×2min @ 105% FTP
- Thu: Rest or 20min easy spin
- Fri: 20min easy spin + 2×30s race-pace activation
- Sat/Sun: Race day

## TSB Projection for Taper Planning

To determine when to start tapering, project forward from current PMC:
1. Current TSB = CTL - ATL
2. Each rest day: ATL decays faster than CTL → TSB rises ~2-4 points/day initially
3. Rule of thumb: ~1 week of reduced load raises TSB by 15-25 points
4. If current TSB = -15 and target = +10, need ~7-10 days of taper
5. If current TSB = -30 and target = +10, need ~14+ days of taper (use 2-week protocol)

**Watch out for**: Tapering too early → detraining (CTL drops, performance suffers). Tapering too late → still fatigued on race day. When in doubt, err toward slightly shorter taper.
