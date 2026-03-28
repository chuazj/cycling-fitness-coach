# Zwift Workout File (.zwo) Format Reference

## File Structure

```xml
<?xml version="1.0" ?>
<workout_file>
  <author>Author Name</author>
  <name>Workout Name</name>
  <description>Workout description text</description>
  <sportType>bike</sportType>
  <category>Optional Category</category>
  <tags>
    <tag name="FTP"/>
    <tag name="Intervals"/>
  </tags>
  <workout>
    <!-- Workout intervals go here -->
  </workout>
  <!-- For FTP test workouts, add ftptest="1" to the workout element: -->
  <!-- <workout ftptest="1"> -->
</workout_file>
```

## Interval Types

### Warmup

Ramp from low to high power.

```xml
<Warmup Duration="300" PowerLow="0.25" PowerHigh="0.75"/>
```

- `Duration`: seconds
- `PowerLow`: starting power as decimal of FTP (0.25 = 25%)
- `PowerHigh`: ending power as decimal of FTP

### Cooldown

Ramp from high to low power.

```xml
<Cooldown Duration="300" PowerLow="0.75" PowerHigh="0.25"/>
```

Note: In Cooldown, `PowerLow` is the starting (higher) value, `PowerHigh` is ending (lower) value.

### SteadyState

Constant power interval.

```xml
<SteadyState Duration="600" Power="0.88" Cadence="90"/>
```

- `Power`: target power as decimal of FTP
- `Cadence`: optional target cadence (rpm)

### Ramp

Power ramp (can go up or down).

```xml
<Ramp Duration="60" PowerLow="0.80" PowerHigh="1.00"/>
```

### IntervalsT

Repeated on/off intervals.

```xml
<IntervalsT Repeat="5" OnDuration="60" OffDuration="60" 
            OnPower="1.20" OffPower="0.50" 
            Cadence="100" CadenceResting="85"/>
```

- `Repeat`: number of repetitions
- `OnDuration`/`OffDuration`: seconds
- `OnPower`/`OffPower`: decimal of FTP
- `CadenceResting`: cadence during off periods

### FreeRide

No ERG mode, rider controls effort.

```xml
<FreeRide Duration="600" FlatRoad="1" show_avg="1"/>
```

- `FlatRoad`: "1" for flat virtual terrain, "0" for course terrain
- `show_avg`: "1" to display running average power on the Zwift HUD for this segment. Essential for FTP tests so the rider can pace by average, not instantaneous power.
- `ftptest`: "1" to mark this segment as an FTP test effort (undocumented — may help Zwift auto-detect FTP)

### MaxEffort

All-out effort (no specific power target).

```xml
<MaxEffort Duration="30"/>
```

## Cadence Targets

### Fixed Cadence
```xml
<SteadyState Duration="600" Power="0.90" Cadence="90"/>
```

### Cadence Range
Use `CadenceLow` and `CadenceHigh` for a target range instead of a fixed value:
```xml
<SteadyState Duration="600" Power="0.90" CadenceLow="85" CadenceHigh="95"/>
```

### IntervalsT with Cadence
```xml
<IntervalsT Repeat="4" OnDuration="240" OffDuration="120"
            OnPower="1.15" OffPower="0.50"
            Cadence="100" CadenceResting="85"/>
```

**Important:** Do not set both `Cadence` (fixed) and `CadenceLow`/`CadenceHigh` (range) on the same interval — Zwift behavior is undefined. Use one or the other.

## Text Events

Add motivational messages during intervals.

```xml
<SteadyState Duration="300" Power="0.90">
  <textevent timeoffset="0" message="Start strong!"/>
  <textevent timeoffset="60" message="Find your rhythm"/>
  <textevent timeoffset="240" message="Last minute - push!"/>
</SteadyState>
```

- `timeoffset`: seconds from interval start
- `message`: text to display

## FTP Test Attribute

**Workout level** — tags the activity as an FTP test post-ride:
```xml
<workout ftptest="1">
```

**Segment level** — use `show_avg="1"` to display running average power on the HUD during the test block:
```xml
<FreeRide Duration="1200" FlatRoad="1" ftptest="1" show_avg="1"/>
```

- `ftptest="1"` on `<workout>`: Zwift recognizes activity as FTP test, may auto-detect new FTP
- `ftptest="1"` on `<FreeRide>`: Undocumented, may assist FTP detection for that segment
- `show_avg="1"` on `<FreeRide>`: **Shows running average power on the HUD** — essential for pacing

`show_avg` is also supported on `SteadyState` and `Ramp` elements.

## Common Tags

Useful for filtering workouts in Zwift:

- `FTP` - Threshold work
- `Recovery` - Easy sessions
- `Intervals` - Interval training
- `TT` - Time trial prep
- `Race` - Race simulation
- `Endurance` - Long steady rides
- `VO2max` - High intensity
- `Sweet Spot` - Sweet spot training

## Power Value Guidelines

| % FTP | Decimal | Typical Use |
|-------|---------|-------------|
| 25% | 0.25 | Easy warmup start |
| 40% | 0.40 | Recovery |
| 55% | 0.55 | Active recovery |
| 65% | 0.65 | Z2 Endurance |
| 75% | 0.75 | Upper Endurance |
| 85% | 0.85 | Tempo |
| 90% | 0.90 | Sweet Spot |
| 95% | 0.95 | Sweet Spot/Threshold |
| 100% | 1.00 | FTP |
| 105% | 1.05 | Threshold |
| 115% | 1.15 | VO2max |
| 120% | 1.20 | VO2max |
| 150% | 1.50 | Anaerobic |

For a complete example .zwo file, see `assets/template_sweetspot.zwo`.

## File Installation

Save `.zwo` files to:
- **Windows**: `Documents\Zwift\Workouts\<your_zwift_id>\`
- **Mac**: `Documents/Zwift/Workouts/<your_zwift_id>/`

Restart Zwift to load new workouts. They appear under "Custom Workouts".
