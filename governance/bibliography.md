# Bibliography — Methodology Authorities

Central index of the sports-science authorities this skill grounds its recommendations on. Per-authority entries list primary works, what they ground in this skill, where currently cited, and the date the citation was last verified. The quarterly audit (`governance/audit_protocol.md`) refreshes the verification dates and flags new editions / refuting evidence.

**How to use this file:**
- A methodology reference doc cites an authority inline (short form, e.g., `Seiler (2010)`), then links here for full provenance via `→ bibliography.md#seiler-stephen`.
- The "Currently cited at" rows are the source of truth for where each authority shows up — keep them in sync when adding or removing inline cites.
- Anything labelled **needs verification** has not been confirmed against the primary source in this verification cycle. Re-verify before relying on it for an athlete-facing claim.
- Citations are listed in shortest defensible form; full DOIs are intentionally omitted (paste-friendly format prioritised over machine-readable). When auditing, follow the journal + year + first author to the canonical record.

## Table of Contents

- [Authorities (alphabetical)](#authorities-alphabetical)
  - [Allen, Hunter (with Coggan)](#allen-hunter-with-coggan)
  - [Coggan, Andrew](#coggan-andrew)
  - [Mujika, Inigo](#mujika-inigo)
  - [Ronnestad, Bent](#ronnestad-bent)
  - [San Millan, Inigo](#san-millan-inigo)
  - [Seiler, Stephen](#seiler-stephen)
  - [Stoggl, Thomas & Sperlich, Billy](#stoggl-thomas--sperlich-billy)

> **Anchor encoding note:** Section headings below use ASCII-only forms so the slug generators in GitHub, Obsidian, and Pandoc all produce identical anchors. The proper-diacritical names (Mujika, Iñigo; Rønnestad, Bent; San Millán, Iñigo; Stöggl, Thomas & Sperlich, Billy) appear in the first paragraph of each section.
- [Auxiliary citations](#auxiliary-citations) — peer-reviewed papers cited in the skill but not in the framework-authority set
- [Currency log](#currency-log)
- [Evidence-level conventions](#evidence-level-conventions)

---

## Authorities (alphabetical)

### Allen, Hunter (with Coggan)

**Primary works:**
- Allen, H., & Coggan, A. R. (2010, 2nd ed.). *Training and Racing with a Power Meter*. VeloPress. **Needs verification** — the 3rd edition (Allen, Coggan, & McGregor, 2019) is the current edition and supersedes some chapters; re-anchor to 3rd ed. if it materially changes the cited framework.

**Grounds in this skill:**
- The PMC framework as practitioner-accessible methodology: CTL/ATL/TSB language, training-stress philosophy, power-zone training conventions.
- Coggan-style zone definitions (Z1–Z7 + neuromuscular) used in `references/training_zones.md`.

**Currently cited at:** Framework is pervasive but the book itself is **not anchored** in any reference doc — claim shows up implicitly. Action: add a footer cite to `references/training_zones.md` and `references/plan_state_schema.md`.

**Last verified:** *not yet verified against primary source — listed for first inclusion 2026-05-26*

---

### Coggan, Andrew

**Primary works:**
- Coggan, A. R. — namesake of TSS (Training Stress Score), NP (Normalized Power), IF (Intensity Factor), and the PMC (Performance Management Chart) framework. The formal definitions are distributed across his TrainingPeaks blog posts and the *Training and Racing with a Power Meter* book (see Allen, Hunter (with Coggan) above).
- Power Profile Chart — a sprint/1-min/5-min/FTP W/kg classification table disseminated via TrainingPeaks; categorical thresholds form the basis of the rider-type classifier in `scripts/intervals_icu/metrics.py`.

**Grounds in this skill:**
- TSS, NP, IF as the unit currency of training load (every script and reference uses these).
- PMC bootstrap + weekly update logic in `scripts/pmc_calculator.py`.
- Power profile classification (sprinter / time_trialist / pursuiter / all_rounder) in `analyze_power_profile()`.

**Currently cited at:**
- `references/internals.md:15` — "Coggan-based W/kg thresholds at 5s, 1min, 5min, 20min".
- `references/internals.md:17` — "Coggan classification" for power profile.
- Framework name (PMC, NP, IF, TSS) is used pervasively without an explicit cite.

**Last verified:** *not yet verified — listed for first inclusion 2026-05-26*

---

### Mujika, Inigo

*(Iñigo Mujika — proper diacritical form.)*

**Primary works:**
- Mujika, I. (2009). *Tapering and Peaking for Optimal Performance*. Human Kinetics.
- Mujika, I., & Padilla, S. (2003). "Scientific bases for precompetition tapering strategies." *Medicine & Science in Sports & Exercise*, 35(7), 1182–1187.
- Mujika, I. (2010). "Intense training: the key to optimal performance before and during the taper." *Scandinavian Journal of Medicine & Science in Sports*, 20(Suppl 2), 24–31. **Needs verification** of exact volume/pages.

**Grounds in this skill:**
- Race-taper structure (volume reduction with intensity preservation, fast-decay vs slow-decay protocols, optimal 7–21 day window).
- "Sharpening" principle — short, high-intensity work during taper preserves neuromuscular capacity.
- Used as the methodology backbone of `references/race_taper.md`.

**Currently cited at:**
- `references/race_taper.md:11` (citation-currency preamble — taper structure, volume-decay with intensity-preservation, "sharpening" principle).
- `references/race_taper.md:5,23` (race-day TSB target band — conservative +5 to +15 per Mujika & Padilla 2003).

**Last verified:** *not yet verified — listed for first inclusion 2026-05-26*

---

### Ronnestad, Bent

*(Bent Rønnestad — proper diacritical form.)*

**Primary works:**
- Rønnestad, B. R., Hansen, E. A., & Raastad, T. (2010). "Effect of heavy strength training on thigh muscle cross-sectional area, performance determinants, and performance in well-trained cyclists." *European Journal of Applied Physiology*, 108(5), 965–975.
- Rønnestad, B. R., & Mujika, I. (2014). "Optimizing strength training for running and cycling endurance performance: A review." *Scandinavian Journal of Medicine & Science in Sports*, 24(4), 603–612.
- Rønnestad, B. R., Hansen, J., Vegge, G., Tønnessen, E., & Slettaløkken, G. (2015). "Short intervals induce superior training adaptations compared with long intervals in cyclists — an effort-matched approach." *Scandinavian Journal of Medicine & Science in Sports*, 25(2), 143–151.
- Rønnestad, B. R., et al. (2020). Subsequent work on VO2max short-interval protocols and power production in well-trained cyclists. **Needs verification** of exact paper(s) cited in `block_templates.md`.

**Grounds in this skill:**
- 30/15s short-interval protocol as the default VO2max stimulus (block_templates.md → VO2max Block).
- Heavy strength training improves cycling economy, time-to-exhaustion, and sprint power without compromising aerobic capacity (durability_strength.md → Concurrent Training).
- "Effort-matched" comparison framing — short intervals vs long intervals at equivalent total work.

**Currently cited at:**
- `references/block_templates.md:65,230,243` (short intervals + 30/15s protocol).
- `references/block_templates.md:329` (strength → neuromuscular transfer, "Rønnestad 2010, 2015").
- `references/durability_strength.md:15` (concurrent strength evidence).

**Last verified:** **2026-05-20** (per block_templates.md citation-currency note).

---

### San Millan, Inigo

*(Iñigo San Millán — proper diacritical form.)*

**Primary works:**
- San Millán, I., & Brooks, G. A. (2018). "Assessment of metabolic flexibility by means of measuring blood lactate, fat, and carbohydrate oxidation responses to exercise in professional endurance athletes and less-fit individuals." *Sports Medicine*, 48(2), 467–479.
- Brooks, G. A. (1986, and subsequent). Lactate shuttle hypothesis — San Millán's Z2 / mitochondrial-function framework derives from Brooks' broader work; San Millán is the practitioner-side popularizer in elite cycling (notably WorldTour-level coaching).

**Grounds in this skill:**
- Z2 (low-intensity, lactate-clearance-zone) as the primary aerobic-base stimulus — distinct from "easy spinning" because the upper Z2 boundary is bracketed by lactate threshold 1, not by an arbitrary % FTP.
- Polarized + base-building rationale in `references/training_zones.md` and `references/block_templates.md` → Endurance Block.

**Currently cited at:**
- `references/training_zones.md:3` (citation-currency preamble — Z2 / mitochondrial framing, POPULAR-MEDIA tier).
- `references/training_zones.md` → Zone 2 section (Z2 base / mitochondrial-density rationale, with the Brooks lactate-shuttle mechanism caveat).

**Evidence-level caveat:** A substantial portion of San Millán's coaching framework is disseminated via podcasts (Peter Attia, Rich Roll, others) and interviews rather than primary literature. When citing his Z2 framework for an athlete-facing claim, prefer Brooks (lactate shuttle, peer-reviewed) as the underlying mechanism and treat San Millán as the cycling-specific application authority. This skill is honest about that distinction; the audit protocol surfaces it as a recurring re-verification item.

**Last verified:** *not yet verified — listed for first inclusion 2026-05-26*

---

### Seiler, Stephen

**Primary works:**
- Seiler, S. (2010). "What is best practice for training intensity and duration distribution in endurance athletes?" *International Journal of Sports Physiology and Performance*, 5(3), 276–291.
- Seiler, S., & Tønnessen, E. (2009). "Intervals, thresholds, and long slow distance: the role of intensity and duration in endurance training." *Sportscience*, 13, 32–53. **Needs verification** — Sportscience is online-only and Seiler's content is occasionally edited post-publication.

**Grounds in this skill:**
- Polarized training distribution (~80% Z1–Z2, ~0% Z3, ~20% Z4+) as a high-volume alternative to sweet-spot-dominant blocks.
- "Z3 no-man's-land" framing — the argument that moderate-intensity Z3/tempo work is the least efficient stimulus per fatigue cost.
- Minimum-volume rationale for the Polarized Block (≥6 h/week threshold — Z2 portion must be long enough to drive aerobic adaptations).

**Currently cited at:**
- `references/block_templates.md:116` ("Based on Seiler (2010) and Stoggl & Sperlich (2014)").
- `references/training_zones.md:56` (polarized as high-volume alternative).

**Last verified:** **2026-05-20** (per block_templates.md citation-currency note).

---

### Stoggl, Thomas & Sperlich, Billy

*(Thomas Stöggl — proper diacritical form.)*

**Primary works:**
- Stöggl, T., & Sperlich, B. (2014). "Polarized training has greater impact on key endurance variables than threshold, high intensity, or high volume training." *Frontiers in Physiology*, 5, 33.

**Grounds in this skill:**
- Direct experimental support for the polarized-superiority claim in well-trained endurance athletes (cross-country skiers, runners, cyclists, triathletes). Co-cited with Seiler (2010) wherever polarized rationale is invoked.

**Currently cited at:**
- `references/block_templates.md:116` (co-cited with Seiler).
- `references/training_zones.md:56` (co-cited with Seiler).

**Last verified:** **2026-05-20** (per block_templates.md citation-currency note).

---

## Auxiliary citations

Peer-reviewed papers cited in this skill but not in the framework-authority set. Listed in alphabetical order by first author.

- **Beattie, K., Carson, B. P., Lyons, M., Rossiter, A., & Kenny, I. C. (2014).** "The effect of strength training on performance indicators in distance runners." Cited at `references/durability_strength.md:15` (strength + endurance evidence). **Needs verification** — confirm exact title/journal; some accounts cite this as JSCR.
- **Clark, S. A., & Macdermid, P. W. (2025).** Cited at `references/block_templates.md:263` (VLaMax framework, *RQES* — Research Quarterly for Exercise and Sport). **Needs verification** — confirm volume/issue once published.
- **Impellizzeri, F. M., et al. (2020).** Critique of acute:chronic workload ratio (ACWR) methodology. Cited at `references/weekly_adaptation.md:49`.
- **Llanos-Lagos, C., Ramírez-Campillo, R., & Sáez de Villarreal, E. (2025).** "Cycling-specific systematic review with meta-analysis on strength training for cyclists." *European Journal of Applied Physiology*, [PMID 40632222](https://pubmed.ncbi.nlm.nih.gov/40632222/). Cited at `references/durability_strength.md:15`. **GRADE certainty: low** (per source). First cycling-specific meta-analysis of strength training.
- **Lolli, L., et al. (2019).** Mathematical-coupling critique of acute:chronic workload ratio. Cited at `references/weekly_adaptation.md:49`.
- **Quittmann, O. J., et al. (2025).** VLaMax (maximum lactate accumulation rate) framework, *Sports Medicine*. Cited at `references/block_templates.md:263`. **Needs verification** — confirm volume/issue.

---

## Currency log

A single row per authority. The quarterly audit (`governance/audit_protocol.md`) reads this table and refreshes the "Last verified" column.

| Authority | Last verified | Verifier | Next due | Notes |
|-----------|--------------:|----------|----------|-------|
| Allen, Hunter (with Coggan) | — | — | 2026-Q3 | First-inclusion 2026-05-26; needs primary-source check (2nd vs 3rd ed.) |
| Coggan, Andrew | — | — | 2026-Q3 | First-inclusion 2026-05-26; framework is implicit-anchored, no formal cite yet |
| Mujika, Iñigo | — | — | 2026-Q3 | Cited 2026-05-30 at race_taper.md:11,5,23 (taper structure + conservative TSB band) — was flagged. |
| Rønnestad, Bent | 2026-05-20 | ZJ | 2026-Q3 | Anchored at 3 sites; OK |
| San Millán, Iñigo | — | — | 2026-Q3 | Cited 2026-05-30 at training_zones.md (Z2 framing, POPULAR-MEDIA→Brooks) — was flagged. |
| Seiler, Stephen | 2026-05-20 | ZJ | 2026-Q3 | Anchored at 2 sites; OK |
| Stöggl, Thomas & Sperlich, Billy | 2026-05-20 | ZJ | 2026-Q3 | Anchored at 2 sites; OK |

---

## Evidence-level conventions

Used by this skill when describing the strength of a recommendation:

| Tier | Definition | Example |
|------|------------|---------|
| **ESTABLISHED** | Peer-reviewed meta-analysis or multiple converging RCTs in the target population (well-trained cyclists). | Heavy strength → cycling neuromuscular transfer (Llanos-Lagos 2025; Rønnestad 2010, 2015). |
| **SUPPORTED** | At least one peer-reviewed RCT in the target or near-target population. | Polarized distribution superior to threshold (Stöggl & Sperlich 2014). |
| **CONTESTED** | Mixed evidence — some studies support, others refute or fail to replicate. State explicitly. | Short-interval superiority for VO2max (Rønnestad cycling work supportive; 2025 running study refutes). |
| **PRACTITIONER CONSENSUS** | Widely adopted by coaches but lacking peer-reviewed RCT in the target population. State explicitly. | Specific on-bike sprint protocols (Llanos-Lagos 2025 notes no formal RCT). |
| **POPULAR-MEDIA** | Disseminated primarily via podcasts/interviews/blogs by a credible practitioner. Treat as practitioner heuristic; cite the underlying mechanism (peer-reviewed) where possible. | San Millán Z2 framework — anchor to Brooks lactate shuttle for the mechanism. |

When a coaching response cites an authority, **the evidence tier should be visible** (either inline or via the link to this file). An athlete reading "Z2 base work raises mitochondrial density (San Millán)" should be able to follow the link and see the POPULAR-MEDIA caveat.
