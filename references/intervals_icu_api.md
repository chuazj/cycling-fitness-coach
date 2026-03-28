# intervals.icu API Reference for Cycling Coach

## Authentication

intervals.icu uses **HTTP Basic Auth** with a permanent API key — no token refresh needed.

- **Username**: `API_KEY` (literal string)
- **Password**: Your API key from https://intervals.icu/settings
- **Athlete ID**: Found in your intervals.icu profile URL (e.g., `i22439`)

Credentials stored in `.env` at project root:
```
INTERVALS_ICU_ATHLETE_ID=i22439
INTERVALS_ICU_API_KEY=your_key_here
```

---

## Key Endpoints for Workout Analysis

### 1. Get Activity Detail
```
GET /api/v1/activity/{id}
```
**Key fields returned (verified):**
- `name`, `type`, `start_date_local`
- `distance` (meters), `moving_time` (seconds), `elapsed_time` (seconds)
- `icu_average_watts`, `icu_weighted_avg_watts` (= NP)
- `p_max` (max power), `icu_joules` (energy in joules)
- `average_heartrate`, `max_heartrate`
- `average_cadence`
- `device_watts` (boolean: real power meter data)
- `trainer` (boolean: indoor trainer ride)
- `icu_training_load` (= TSS)
- `icu_intensity` (= IF as percentage, e.g. 89 = 0.89 IF)
- `total_elevation_gain`, `icu_ftp`, `icu_weight`

### 2. Get Activity Intervals
```
GET /api/v1/activity/{id}/intervals
```
Response: `{ icu_intervals: [...], icu_groups: [...] }` — use `icu_intervals` array.

Per-interval fields (verified):
- `label` (may be null), `type` (WORK/RECOVERY), `distance`, `elapsed_time`, `moving_time`
- `average_watts`, `weighted_average_watts` (= interval NP)
- `average_heartrate`, `max_heartrate`
- `average_cadence`
- `max_watts`, `intensity`

### 3. Get Activity Streams
```
GET /api/v1/activity/{id}/streams.json?types=watts&types=heartrate&types=cadence
```
Second-by-second time-series data for zone distribution and cardiac drift computation.

**Note:** `types` is an array parameter (repeat per value, not CSV). The `{ext}` path suffix (`.json`) is **required** — the extensionless path only supports PUT.

**Available stream types:**
| Stream Key | Data | Unit |
|------------|------|------|
| `watts` | Power | watts |
| `heartrate` | Heart rate | bpm |
| `cadence` | Cadence | rpm |
| `velocity_smooth` | Speed | m/s |
| `altitude` | Elevation | meters |
| `distance` | Cumulative distance | meters |

### 4. Get Power Curve
```
GET /api/v1/activity/{id}/power-curve.json
```
Pre-computed peak powers at all durations from the original .fit file. More accurate than stream-based computation.

**Note:** The `{ext}` path suffix (`.json`) is **required** — no extensionless GET exists in the spec.

### 5. Get Athlete Profile
```
GET /api/v1/athlete/{athlete_id}
```
Returns: `icu_ftp`, `icu_weight`, configured zones, etc.

### 6. List Athlete Activities
```
GET /api/v1/athlete/{athlete_id}/activities?oldest=DATE&newest=DATE&limit=N
```
- `oldest` — **required** (ISO-8601 date/time, e.g. `2024-01-01T00:00:00`)
- `newest` — optional (defaults to now)
- `limit` — optional integer, limits number of activities returned server-side

---

## Data Mapping: API → Coach Analysis

| Coach Metric | intervals.icu Field (verified) | Source Endpoint |
|-------------|---------------------|----------------|
| Normalized Power (NP) | `icu_weighted_avg_watts` | Activity |
| Average Power | `icu_average_watts` | Activity |
| Intensity Factor (IF) | `icu_intensity` (percentage, ÷100 for decimal) | Activity |
| TSS | `icu_training_load` | Activity |
| Energy (kJ) | `icu_joules` (÷1000 for kJ) | Activity |
| Max Power | `p_max` or 5s peak from power curve | Activity / Power Curve |
| Power Meter | `device_watts` (boolean) | Activity |
| Interval Power | `average_watts` per interval | Intervals (`icu_intervals`) |
| Interval NP | `weighted_average_watts` per interval | Intervals |
| Interval Duration | `elapsed_time` / `moving_time` per interval | Intervals |
| Interval HR | `average_heartrate` per interval | Intervals |
| Peak Powers | `secs` + `watts` arrays | Power Curve |
| Zone Distribution | Computed from `watts` stream | Streams |
| Cardiac Drift | Computed from `watts` + `heartrate` streams | Streams |

### Extracting Activity ID from URL
Pattern: `https://intervals.icu/activities/i{numeric_id}` or `https://intervals.icu/activities/{numeric_id}`
Regex: `intervals\.icu/activities/(i?\d+)`
Also accepts plain numeric IDs (e.g., `17478304236`).

---

## API Calls Per Analysis

1. `GET /activity/{id}` — core metrics + metadata
2. `GET /activity/{id}/intervals` — interval/lap data
3. `GET /activity/{id}/power-curve.json` — peak powers
4. `GET /activity/{id}/streams.json?types=watts&types=heartrate&types=cadence` — zones + drift

**Total: 4 calls per activity** (no rate limit concerns)

---

## Advantages Over Strava API

- **No token expiry** — API key is permanent
- **Pre-computed metrics** — NP, IF, TSS available directly from activity endpoint
- **Power curve endpoint** — accurate peak powers from .fit data
- **Richer interval data** — per-interval NP, intensity, and more
- **No rate limits** — practical usage has no restrictions
