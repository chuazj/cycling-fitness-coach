# Menstrual Cycle & Training

Reference for Claude-as-coach: how to handle the menstrual cycle and hormonal contraceptives when coaching a female athlete. Covers the evidence stance, individualized autoregulation, symptom management, and the amenorrhea / low-energy-availability red flag.

> **Citation currency** — physiology citations last verified **2026-05-20**. Fast-moving field (the IMPACT phase-periodization trial reports ~2025–26); re-verify at every skill audit. Anchor authorities: McNulty et al. (2020) and *Strength & Conditioning Journal* 2025 reviews are cited inline (§1 Evidence stance); not yet routed through `references/bibliography.md` — adding female-athlete authorities is queued for the 2026-Q3 audit per `references/audit_protocol.md`.

> **Scope** — this is *training* guidance, not medical advice. Where this doc says "refer to a doctor," that is a hard gate, not a suggestion.

## 1. Evidence stance (read first)

The headline is counterintuitive: **the menstrual cycle is a weak basis for *periodizing* training, and a strong basis for *individualized autoregulation*.**

- **Phase has only a trivial average effect on performance.** The largest meta-analysis (McNulty et al. 2020, *Sports Medicine*) found performance *may* be trivially reduced in the early follicular phase (effect size −0.14), with large between-study variation and low-quality evidence. Its own conclusion: general phase-based guidelines cannot be formed — **take a personalised approach.**
- **Phase-based periodization is not evidence-supported.** Reviews through 2025 (*Strength & Conditioning Journal* 2025) find no benefit to periodizing strength or endurance training by cycle phase over standard periodization; acute strength and resistance-training adaptations show no consistent phase effect. The confirmatory trial (IMPACT) is still in progress — treat phase-periodization as **unproven**, not recommended.
- **What does matter: symptoms and the individual's own pattern.** Menstrual symptoms — especially period pain (dysmenorrhea) — are a documented cause of missed and degraded training. The actionable signal is *this athlete's* symptoms and her own performance response, tracked over several cycles.

**Coaching implication:** do not restructure a plan around cycle phase. Keep standard periodization (`block_templates.md`) and autoregulate to symptoms and wellness — the same reactive logic the skill already applies to readiness.

**Evidence confidence:** ESTABLISHED that phase has at most a trivial average performance effect, and that symptoms disrupt training. UNPROVEN that phase-based periodization helps.

## 2. The cycle — brief reference

A natural ("eumenorrheic") cycle runs ~21–35 days; "28 days" is a textbook average, not a norm. Two phases, split by ovulation:

| Phase | Timing (28-day example) | Hormones | What can change |
|---|---|---|---|
| **Follicular** (includes menstruation) | Day 1 (first day of bleeding) → ovulation ~day 14 | Low early, then rising estrogen | Menstruation (days ~1–5): bleeding, possible cramps/pain |
| **Luteal** | Ovulation → next period (~14 days, fairly fixed) | Estrogen + progesterone elevated | Progesterone raises resting core temperature ~0.3°C and resting HR slightly; can raise ventilation and perceived effort; late luteal = premenstrual symptoms |

Cycle length varies between women and between cycles. The **luteal phase is relatively stable (~14 days)**; most variation is in follicular length — relevant for tracking (§7).

## 3. Default approach

For most athletes, most of the time:

1. **Keep standard periodization.** Build the plan as `block_templates.md` prescribes. Do not pre-emptively schedule hard work into one phase or easy work into another.
2. **Autoregulate to wellness + symptoms, not to the calendar.** The readiness system (`--readiness-check`) and the adaptation rules already do reactive load management — menstrual symptoms are just another input.
3. **Account for the luteal hormonal baseline when reading wellness data.** Progesterone elevates resting HR and core temperature and can nudge HRV down. A modest luteal-phase RHR rise or HRV dip is partly hormonal — do not automatically read it as fatigue. Compare against the athlete's *own* luteal-phase baseline once a few cycles are logged.
4. **Expect individual variation.** Some athletes report meaningful symptom-driven dips (often during menstruation, or late luteal); many report none. The plan adapts to *her* pattern, established from tracking — not from a population template.

## 4. Individualized symptom-based autoregulation

The core of the protocol. Track the cycle and symptoms; once 2–3 cycles are logged, look for *her* pattern; adjust reactively.

**Inputs to log** (intervals.icu wellness — see §7): cycle day, bleeding (none / light / heavy), symptom load (pain/cramps, fatigue, mood, sleep disruption, bloating, headache).

**Reactive adjustments — apply by symptom severity, not by phase:**

| Symptom state | Training adjustment |
|---|---|
| None / mild | Train as planned. |
| Moderate (noticeable pain/fatigue, manageable) | Keep the session but autoregulate: drop intensity targets one tier or shorten; prioritise the key set over full volume. Same logic as a yellow readiness day. |
| Severe (pain limiting movement, heavy bleeding with fatigue, disrupted sleep) | Swap to easy Z1–Z2 or rest; reschedule the quality session. Do not "push through" severe dysmenorrhea — it degrades execution and the data is not useful. |

**Pattern use:** after 2–3 logged cycles, if the athlete shows a *consistent* dip at a predictable point (e.g. the first 1–2 days of menstruation), it is reasonable to *plan* a recovery day or lighter session there — individualized scheduling from her data, which is different from applying a generic phase template.

**Do not** downgrade a quality session purely because the athlete is in the luteal phase, or is menstruating with no symptoms. Phase without symptoms is not a reason to change the plan.

## 5. Symptom management

Training accommodation only — for medical management, refer to a doctor.

- **Dysmenorrhea (period pain):** very common. Light exercise often *reduces* cramping; many athletes train well on days 1–2 with mild cramps. If pain is limiting, see the severe row in §4. Persistent severe dysmenorrhea, or pain that is new or worsening, warrants a medical review — it can have treatable underlying causes.
- **Heavy menstrual bleeding:** can cause iron deficiency, which degrades endurance directly (low ferritin impairs oxygen transport even before anemia). If the athlete reports heavy bleeding *and* unexplained fatigue or declining performance, recommend she ask her doctor for an iron / ferritin check. Iron status is a genuine, fixable performance limiter — flag it.
- **Premenstrual symptoms (PMS):** mood, fatigue, bloating, sleep disruption in the late luteal phase. Manage by autoregulation (§4); if symptoms are severe enough to disrupt daily function, refer to a doctor.
- **Hydration / heat:** the luteal core-temperature rise modestly raises heat strain. For a hot-climate or indoor athlete, apply the existing heat guidance (`durability_strength.md` → Heat Adaptation; the Evening Workout Energy Playbook) a little more conservatively in the luteal phase.

## 6. Hormonal contraceptives

An athlete on a hormonal contraceptive (HC) — combined pill, progestogen-only pill, hormonal intrauterine device (IUD), implant, injection, ring, patch — does **not** have a natural cycle; the contraceptive hormones override it.

- **Performance:** at the population level, hormonal contraceptives show **no consistent effect** on aerobic or anaerobic performance, or on strength/hypertrophy adaptations (Elliott-Sale et al. 2020 oral-contraceptive meta-analysis; 2023 HC strength meta-analysis). Individual variation exists — some report small VO2max differences of ~2–4%.
- **Antiandrogenic progestins:** some pills use antiandrogenic progestins (e.g. cyproterone acetate, drospirenone, dienogest), which *may* slightly blunt strength/power gains. If an athlete on HC is in a strength-focused block and gains lag expectations, the progestin type is worth her raising with her doctor — but do not advise changing contraception for performance.
- **Withdrawal bleed:** the bleed in the pill-free / placebo week is not a true menstrual period. Some athletes get withdrawal symptoms (headache, cramps) that week — autoregulate to those symptoms exactly as in §4.
- **No phase to track:** for HC users, skip cycle-phase logging — track symptoms and the standard wellness signals only.
- **Important:** HC can **mask amenorrhea** — a withdrawal bleed still occurs on a combined pill even if the athlete has low energy availability that would otherwise have stopped her periods. For HC users the RED-S screen (§7) relies on other signs, not on "is she menstruating."

## 7. The red flag — amenorrhea and Relative Energy Deficiency in Sport (RED-S)

**The most important section in this document.** A missing or lost period is a health warning sign, not a training convenience.

- **Amenorrhea** = no menstrual period for **3+ consecutive months** (not pregnant, not on an HC that suppresses bleeding). **Oligomenorrhea** = infrequent periods, cycles consistently longer than ~35 days.
- In athletes the common cause is **functional hypothalamic amenorrhea** — the brain switching off the menstrual cycle in response to an energy shortfall — driven by **low energy availability (LEA)**, i.e. not eating enough to cover the energy cost of training. LEA is the root cause of **Relative Energy Deficiency in Sport (RED-S)**, which also harms bone health, immunity, iron status, and performance.
- **A lost period is the body down-regulating reproductive function to conserve energy. It is a symptom of an energy-deficit problem, and it is fixed by correcting the energy deficit — not by a training adjustment.**

**Hard gate — if a female athlete reports amenorrhea or oligomenorrhea** (or, on an HC, reports LEA signs: unexplained performance decline, frequent illness or injury, stress fractures, persistent fatigue, disordered-eating signs):

1. **Do not** prescribe a training fix and move on. Do not increase load.
2. **Refer her to a sports physician / doctor** for evaluation, and ideally a sports dietitian for an energy-availability assessment. State this plainly and supportively.
3. Until she has medical guidance, **hold intensity and volume at maintenance, not progression** — adding load to an athlete in energy deficit deepens the problem.
4. Treat it as any other medical red flag in the skill (`weekly_adaptation.md` → Illness / Injury): a hard safety gate, never "push through."

This applies **regardless of the athlete's body size or weight** — RED-S occurs across all body types.

## 8. How to track

- **intervals.icu** supports menstrual-cycle and wellness logging. Have the athlete log daily: cycle day / bleeding status, plus the symptom set from §4. The `--wellness` and `--readiness-check` modes already pull subjective wellness — menstrual symptoms sit alongside them as another input.
- **Minimum useful history: 2–3 cycles.** Below that, treat any "pattern" as provisional — the protocol is individualized, and the individual's pattern needs data.
- **What to look for:** a *consistent, repeating* relationship between a cycle point and a symptom or performance dip. Found → individualize scheduling around it (§4). Not found → standard periodization, autoregulate reactively.
- **HC users:** log symptoms only (no phase); watch the withdrawal-bleed week.

## How this connects to the workflows

- **Plan creation (`workflows/plan.md`):** for a female athlete, ask once — respectfully — about menstrual status (natural cycle vs hormonal contraceptive, cycle regularity, training-affecting symptoms). Default to standard periodization + symptom tracking. Screen the §7 amenorrhea gate.
- **Advice / check-in (`workflows/advise.md`):** treat menstrual symptoms as a wellness input in autoregulation (§4). If amenorrhea / oligomenorrhea / LEA signs surface, apply the §7 gate.

## Sources

- McNulty et al. (2020) — *The Effects of Menstrual Cycle Phase on Exercise Performance in Eumenorrheic Women: A Systematic Review and Meta-Analysis*, **Sports Medicine** 50:1813–1827. [PMC7497427](https://pmc.ncbi.nlm.nih.gov/articles/PMC7497427/)
- Elliott-Sale et al. (2020) — *The Effects of Oral Contraceptives on Exercise Performance in Women: A Systematic Review and Meta-analysis*, **Sports Medicine** 50:1785–1812. [PMC7497464](https://pmc.ncbi.nlm.nih.gov/articles/PMC7497464/)
- Systematic review & meta-analysis (2023) — *Effect of Hormonal Contraceptive Use on Skeletal Muscle Hypertrophy, Power and Strength Adaptations to Resistance Exercise Training*. [PMID 37755666](https://pubmed.ncbi.nlm.nih.gov/37755666/)
- *Strength & Conditioning Journal* (2025), 47(6) — *Evidence for Periodizing Strength and/or Endurance Training According to Menstrual Cycle Phases*. [journals.lww.com/nsca-scj](https://journals.lww.com/nsca-scj/fulltext/2025/12000/evidence_for_periodizing_strength_and_or_endurance.4.aspx)
- Mountjoy et al. (2023) — *2023 IOC consensus statement on Relative Energy Deficiency in Sport (REDs)*, **British Journal of Sports Medicine** 57(17):1073–1097. [DOI 10.1136/bjsports-2023-106994](https://doi.org/10.1136/bjsports-2023-106994)
