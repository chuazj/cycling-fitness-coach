# Cycling Fitness Coach

A [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) that turns Claude into a data-driven cycling coach. It connects to [intervals.icu](https://intervals.icu) for real training data, generates [Zwift](https://www.zwift.com/) workouts, builds periodized training plans, and provides weekly adaptive reviews — all through natural conversation.

## What It Does

| Capability | Description |
|------------|-------------|
| **Ride Analysis** | Fetch activity data from intervals.icu and get coaching feedback with execution ratings, interval review, and next-session recommendations |
| **Weekly Summary** | Aggregate the past 7 days — total TSS, zone distribution, power profile, FTP detection |
| **Training Plans** | Multi-week periodized plans with PMC tracking (CTL/ATL/TSB/ACWR), progressive overload, and block periodization |
| **Weekly Reviews** | Compare planned vs actual training load, apply adaptation decision trees, adjust the next week |
| **Zwift Workouts** | Generate `.zwo` workout files with structured warm-up, intervals, and cool-down — single or batch |
| **Training Advice** | Zone/FTP questions, race peaking & taper protocols, mid-week check-ins |
| **Power Profiling** | Coggan-based W/kg classification (sprinter, pursuiter, time trialist, all-rounder) with strength/weakness analysis |

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) (CLI, desktop app, or IDE extension)
- Python 3.9+
- An [intervals.icu](https://intervals.icu) account with API key

```bash
pip install requests
```

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/chuazj/cycling-fitness-coach.git
```

### 2. Install as a Claude Code skill

Copy or symlink into your Claude Code skills directory:

```bash
# macOS / Linux
cp -r cycling-fitness-coach ~/.claude/skills/cycling-fitness-coach

# Windows (PowerShell)
Copy-Item -Recurse cycling-fitness-coach "$env:USERPROFILE\.claude\skills\cycling-fitness-coach"
```

### 3. Configure intervals.icu credentials

Create a `.env` file in the skill directory:

```
INTERVALS_ICU_ATHLETE_ID=i12345
INTERVALS_ICU_API_KEY=your_api_key_here
```

Get your API key from [intervals.icu Settings](https://intervals.icu/settings) (permanent key, no refresh needed).

## Usage

Once installed, Claude Code automatically activates the skill when you mention cycling topics. Just talk to it naturally:

### Analyze a ride

```
Analyze my workout: https://intervals.icu/activities/i126468486
```

or just paste an activity ID:

```
How did my ride go? i126468486
```

Claude fetches the data via API, computes NP/IF/TSS/zones/peaks, and returns coaching analysis with an execution rating and next-session recommendation.

### Weekly summary

```
How was my training week?
```

Aggregates the last 7 days: total TSS, zone distribution, power profile, and auto-FTP detection.

### Create a training plan

```
Build me a 6-week training plan to improve my FTP
```

Claude bootstraps your PMC from 90-day history, selects the appropriate periodization block, designs week-by-week TSS progression, and generates Zwift workouts for Week 1.

### Weekly check-in

```
Review my week — how did I do?
```

Compares planned vs actual training load, checks CTL/ATL/TSB trends, applies adaptation decision trees, and adjusts the upcoming week.

### Generate a Zwift workout

```
Create a sweet spot workout, 60 minutes
```

Generates a `.zwo` file with structured warm-up, main set, and cool-down. Power targets are expressed as FTP fractions for automatic scaling in Zwift.

### Training advice

```
I have a race in 3 weeks — help me peak
```

```
What zone should I focus on if I plateau at sweet spot?
```

```
My RPE was 9 but IF was only 0.72 — what's going on?
```

## Architecture

```
SKILL.md                        <- Skill entry point (triggers, coaching rules, workflow dispatch)
workflows/
  analyze.md                    <- Activity analysis + weekly summary
  plan.md                       <- Plan creation + weekly review
  generate.md                   <- Zwift workout generation
  advise.md                     <- Training advice + mid-week check-in + race peaking
scripts/
  intervals_icu_api.py          <- intervals.icu API client + metrics (NP, IF, TSS, zones, peaks, cardiac drift)
  generate_zwo.py               <- Zwift .zwo XML generator
  pmc_calculator.py             <- PMC bootstrap (90-day history) + weekly update (planned vs actual)
  batch_generate_zwo.py         <- Batch .zwo generation from JSON array
references/
  training_zones.md             <- Power/HR zone definitions, weekly structure
  workout_analysis.md           <- Analysis framework, coaching response templates
  zwo_format.md                 <- Zwift XML element spec and examples
  intervals_icu_api.md          <- intervals.icu API endpoints and data models
  periodization.md              <- Block templates, TSS distribution, adaptation decision trees
  plan_state_schema.md          <- Structure spec for active training plan state
plans/
  active_plan.md                <- Active training plan (generated, not pre-existing)
  workouts/                     <- Generated .zwo files organized by week
tests/                          <- Unit tests (pure functions, mocks, CLI, PMC integration)
assets/
  template_sweetspot.zwo        <- Example Zwift workout XML
```

### Data Flows

**Activity analysis:**
intervals.icu link -> `intervals_icu_api.py` fetches activity/intervals/streams/power-curve -> computes metrics -> JSON output -> Claude provides coaching analysis

**Plan creation:**
`pmc_calculator.py --bootstrap` -> PMC baseline -> Claude designs periodized block -> writes `plans/active_plan.md` -> `batch_generate_zwo.py` generates week's .zwo files

**Weekly review:**
`pmc_calculator.py --weekly-update` -> planned vs actual comparison -> Claude applies adaptation rules -> updates plan -> generates next week's workouts

## Scripts Reference

### intervals_icu_api.py

```bash
# Analyze a single activity
python scripts/intervals_icu_api.py --activity i126468486 --ftp 192 --weight 74

# Auto-fetch FTP/weight from athlete profile
python scripts/intervals_icu_api.py --activity i126468486 --use-athlete-profile

# List recent activities
python scripts/intervals_icu_api.py --list-recent 10

# Weekly summary (last 7 days)
python scripts/intervals_icu_api.py --weekly-summary -o summary.json

# Compact output (fewer tokens for LLM consumption)
python scripts/intervals_icu_api.py --activity i126468486 --compact
```

### pmc_calculator.py

```bash
# Bootstrap: 90-day history with current CTL/ATL/TSB + peak powers
python scripts/pmc_calculator.py --bootstrap --days 90

# Weekly update: compare planned vs actual
python scripts/pmc_calculator.py --weekly-update \
  --week 1 --plan-start 2025-03-16 \
  --prev-ctl 42.3 --prev-atl 51.2 \
  --planned-tss '{"Tue":65,"Thu":70,"Sat":80,"Flex":55}'
```

### generate_zwo.py

```bash
# Generate a single Zwift workout from JSON definition
python scripts/generate_zwo.py --json workout_def.json --output workout.zwo --ftp 200
```

### batch_generate_zwo.py

```bash
# Generate all .zwo files for a training week
python scripts/batch_generate_zwo.py --input week_workouts.json --output-dir plans/workouts/week1/ --ftp 192

# Dry run (validate + compute stats without writing files)
python scripts/batch_generate_zwo.py --input week_workouts.json --dry-run --ftp 192
```

## Training Methodology

The coaching approach is grounded in established sport science:

- **Power zones**: 7-zone model based on FTP (Coggan)
- **Sweet spot training**: 88-94% FTP — high stimulus, manageable fatigue, optimal for time-crunched athletes
- **Periodization**: Block periodization with base, build, peak, and recovery phases
- **Load management**: PMC-based tracking with CTL (fitness), ATL (fatigue), TSB (form), and ACWR (acute:chronic workload ratio)
- **Adaptation**: Decision trees for weekly plan adjustments based on compliance, RPE:IF mismatch, and TSB trends
- **Race peaking**: Taper protocols with progressive volume reduction while maintaining intensity

## Coaching Process

The skill follows strict coaching process rules:

1. **Validate before prescribing** — presents an assessment of the athlete's current state and waits for confirmation before making recommendations
2. **Establish zones first** — never prescribes zone-specific workouts without confirmed FTP; recommends field tests for unvalidated zones
3. **Explain the "why"** — every prescription includes the physiological purpose and how it connects to the athlete's goal
4. **Adaptation requires approval** — proposes changes based on data but waits for athlete confirmation before modifying the plan

## Optional Integrations

| Integration | Purpose |
|-------------|---------|
| [Obsidian](https://obsidian.md/) | Persistent storage for workout analyses, plans, and weekly reviews with frontmatter metadata |
| [Zwift](https://www.zwift.com/) | Load generated `.zwo` files into custom workouts |

## Running Tests

```bash
python -m unittest discover tests -v
```

Tests include pure function unit tests, mocked HTTP responses, CLI argument parsing, and PMC integration tests.

## Customization

To adapt this skill for your own use:

1. **FTP/Weight**: Update your values in `CLAUDE.md` under "User's current FTP" — or let the skill auto-fetch from your intervals.icu profile
2. **Training days**: The skill auto-detects your pattern from activity history, or you can specify during plan creation
3. **Obsidian vault**: Update the vault path in `SKILL.md` if you use Obsidian for note storage
4. **Zwift workout folder**: Update the Zwift path in `SKILL.md` to match your Zwift ID

## License

MIT
