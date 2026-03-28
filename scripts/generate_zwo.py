#!/usr/bin/env python3
"""
Zwift Workout (.zwo) File Generator

Generates valid Zwift workout XML files from structured workout definitions.
Power values are expressed as decimal fractions of FTP (e.g., 0.75 = 75% FTP).
Duration values are in seconds.

Usage:
    python generate_zwo.py --output workout.zwo --json workout_def.json
    OR import and use programmatically
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, fields
from typing import Optional
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring

# Force UTF-8 stdout on Windows (default cp1252 cannot encode CJK workout names)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class TextEvent:
    """Text message displayed during workout"""
    timeoffset: int  # seconds from interval start
    message: str
    duration: int = 10  # display duration in seconds


def _validate_power(value, name="power"):
    if not (0.0 <= value <= 2.0):
        raise ValueError(f"{name}={value} out of range — must be 0.0 <= {name} <= 2.0 (fraction of FTP)")

@dataclass
class WorkoutInterval:
    """Base class for workout intervals"""
    duration: int  # seconds
    text_events: list = field(default_factory=list)
    cadence: Optional[int] = None
    cadence_low: Optional[int] = None
    cadence_high: Optional[int] = None

    def __post_init__(self):
        if self.duration <= 0:
            raise ValueError(f"duration must be > 0, got {self.duration}")
        if self.cadence is not None and (self.cadence_low is not None or self.cadence_high is not None):
            raise ValueError("Cannot set both cadence (fixed) and cadence_low/cadence_high (range) — use one or the other")


@dataclass
class SteadyState(WorkoutInterval):
    """Constant power interval"""
    power: float = 0.75  # fraction of FTP

    def __post_init__(self):
        super().__post_init__()
        _validate_power(self.power, "power")


@dataclass
class Warmup(WorkoutInterval):
    """Ramp from low to high power.

    power_low = start power (lower), power_high = end power (higher).
    Matches Zwift XML attribute names AND magnitude ordering.
    """
    power_low: float = 0.25
    power_high: float = 0.75

    def __post_init__(self):
        super().__post_init__()
        _validate_power(self.power_low, "power_low")
        _validate_power(self.power_high, "power_high")
        if self.power_low > self.power_high:
            raise ValueError(f"Warmup must ramp up: power_low ({self.power_low}) > power_high ({self.power_high})")


@dataclass
class Cooldown(WorkoutInterval):
    """Ramp from high to low power.

    Note: power_low/power_high match Zwift XML attribute names, NOT magnitudes.
    power_low = start power (higher), power_high = end power (lower).
    """
    power_low: float = 0.75
    power_high: float = 0.25

    def __post_init__(self):
        super().__post_init__()
        _validate_power(self.power_low, "power_low")
        _validate_power(self.power_high, "power_high")
        if self.power_low < self.power_high:
            raise ValueError(f"Cooldown must ramp down: power_low ({self.power_low}) < power_high ({self.power_high})")


@dataclass
class Ramp(WorkoutInterval):
    """Ramp between two power values"""
    power_low: float = 0.5
    power_high: float = 1.0

    def __post_init__(self):
        super().__post_init__()
        _validate_power(self.power_low, "power_low")
        _validate_power(self.power_high, "power_high")


@dataclass
class IntervalsT(WorkoutInterval):
    """Repeated on/off intervals"""
    duration: int = 0  # Auto-calculated from repeat * (on + off); no need to pass explicitly
    repeat: int = 1
    on_duration: int = 30
    off_duration: int = 30
    on_power: float = 1.2
    off_power: float = 0.5
    cadence_resting: Optional[int] = None

    def __post_init__(self):
        # Auto-calculate duration before parent validation
        calculated = self.repeat * (self.on_duration + self.off_duration)
        if self.duration != 0 and self.duration != calculated:
            import warnings
            warnings.warn(
                f"IntervalsT: explicit duration={self.duration}s ignored, "
                f"using calculated {calculated}s "
                f"(repeat={self.repeat} x (on={self.on_duration} + off={self.off_duration}))",
                stacklevel=2,
            )
        self.duration = calculated
        super().__post_init__()
        _validate_power(self.on_power, "on_power")
        _validate_power(self.off_power, "off_power")
        if self.on_duration <= 0:
            raise ValueError(f"on_duration must be > 0, got {self.on_duration}")
        if self.off_duration <= 0:
            raise ValueError(f"off_duration must be > 0, got {self.off_duration}")
        if self.repeat <= 0:
            raise ValueError(f"repeat must be > 0, got {self.repeat}")


@dataclass
class FreeRide(WorkoutInterval):
    """Free ride section (no ERG mode)"""
    flat_road: bool = False
    ftptest: bool = False
    show_avg: bool = False


@dataclass
class MaxEffort(WorkoutInterval):
    """Maximum effort interval"""
    pass


@dataclass
class ZwiftWorkout:
    """Complete Zwift workout definition"""
    name: str
    author: str = "Cycling Fitness Coach"
    description: str = ""
    sport_type: str = "bike"
    tags: list = field(default_factory=list)
    intervals: list = field(default_factory=list)
    category: Optional[str] = None
    is_ftp_test: bool = False


def create_zwo_xml(workout: ZwiftWorkout) -> str:
    """Generate ZWO XML from workout definition"""
    root = Element("workout_file")
    
    # Metadata
    SubElement(root, "author").text = workout.author
    SubElement(root, "name").text = workout.name
    SubElement(root, "description").text = workout.description
    SubElement(root, "sportType").text = workout.sport_type
    
    if workout.category:
        SubElement(root, "category").text = workout.category
    
    # Tags
    tags_elem = SubElement(root, "tags")
    for tag in workout.tags:
        SubElement(tags_elem, "tag", name=tag)
    
    # Workout intervals
    workout_elem = SubElement(root, "workout")
    if workout.is_ftp_test:
        workout_elem.set("ftptest", "1")
    
    for interval in workout.intervals:
        interval_elem = _create_interval_element(interval)
        workout_elem.append(interval_elem)
        
        # Add text events
        for event in interval.text_events:
            text_elem = SubElement(interval_elem, "textevent")
            text_elem.set("timeoffset", str(event.timeoffset))
            text_elem.set("message", event.message)
            if event.duration != 10:
                text_elem.set("duration", str(event.duration))
    
    # Format with pretty printing
    ET.indent(root, space="  ")
    xml_str = tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str


def _create_interval_element(interval: WorkoutInterval) -> Element:
    """Create XML element for a workout interval.

    Order matters: check specific subclasses (Warmup, Cooldown, Ramp) before
    the generic SteadyState, since all share similar attributes.
    """
    if isinstance(interval, Warmup):
        elem = Element("Warmup")
        elem.set("Duration", str(interval.duration))
        elem.set("PowerLow", f"{interval.power_low:.2f}")
        elem.set("PowerHigh", f"{interval.power_high:.2f}")
        
    elif isinstance(interval, Cooldown):
        elem = Element("Cooldown")
        elem.set("Duration", str(interval.duration))
        elem.set("PowerLow", f"{interval.power_low:.2f}")
        elem.set("PowerHigh", f"{interval.power_high:.2f}")
        
    elif isinstance(interval, Ramp):
        elem = Element("Ramp")
        elem.set("Duration", str(interval.duration))
        elem.set("PowerLow", f"{interval.power_low:.2f}")
        elem.set("PowerHigh", f"{interval.power_high:.2f}")
        
    elif isinstance(interval, IntervalsT):
        elem = Element("IntervalsT")
        elem.set("Repeat", str(interval.repeat))
        elem.set("OnDuration", str(interval.on_duration))
        elem.set("OffDuration", str(interval.off_duration))
        elem.set("OnPower", f"{interval.on_power:.2f}")
        elem.set("OffPower", f"{interval.off_power:.2f}")
        if interval.cadence_resting is not None:
            elem.set("CadenceResting", str(interval.cadence_resting))
            
    elif isinstance(interval, FreeRide):
        elem = Element("FreeRide")
        elem.set("Duration", str(interval.duration))
        if interval.flat_road:
            elem.set("FlatRoad", "1")
        if interval.ftptest:
            elem.set("ftptest", "1")
        if interval.show_avg:
            elem.set("show_avg", "1")
            
    elif isinstance(interval, MaxEffort):
        elem = Element("MaxEffort")
        elem.set("Duration", str(interval.duration))
        
    elif isinstance(interval, SteadyState):
        elem = Element("SteadyState")
        elem.set("Duration", str(interval.duration))
        elem.set("Power", f"{interval.power:.2f}")
        
    else:
        raise ValueError(f"Unknown interval type: {type(interval)}")
    
    # Add cadence if specified
    if interval.cadence is not None:
        elem.set("Cadence", str(interval.cadence))
    if interval.cadence_low is not None:
        elem.set("CadenceLow", str(interval.cadence_low))
    if interval.cadence_high is not None:
        elem.set("CadenceHigh", str(interval.cadence_high))
    
    return elem


def workout_from_dict(data: dict) -> ZwiftWorkout:
    """Create workout from dictionary (e.g., parsed JSON)"""
    intervals = []
    interval_classes = {
        "warmup": Warmup,
        "cooldown": Cooldown,
        "steadystate": SteadyState,
        "ramp": Ramp,
        "intervals": IntervalsT,
        "intervalst": IntervalsT,
        "freeride": FreeRide,
        "maxeffort": MaxEffort,
    }
    for idx, interval_data in enumerate(data.get("workout", data.get("intervals", []))):
        interval_data = dict(interval_data)  # shallow copy to avoid mutating caller's data
        if "type" not in interval_data:
            raise ValueError(f"Interval #{idx} missing required 'type' field: {interval_data}")
        interval_type = interval_data.pop("type")
        text_events = [
            TextEvent(**e) for e in interval_data.pop("text_events", [])
        ]

        cls = interval_classes.get(interval_type.lower())
        if not cls:
            raise ValueError(f"Unknown interval type: {interval_type}")
        
        try:
            interval = cls(**interval_data, text_events=text_events)
        except TypeError as e:
            valid_fields = [f.name for f in fields(cls)]
            raise ValueError(
                f"Interval #{idx} ({interval_type}): {e}. Valid fields: {valid_fields}"
            ) from e
        intervals.append(interval)
    
    return ZwiftWorkout(
        name=data.get("name", "Custom Workout"),
        author=data.get("author", "Cycling Fitness Coach"),
        description=data.get("description", ""),
        sport_type=data.get("sport_type", "bike"),
        tags=data.get("tags", []),
        category=data.get("category"),
        is_ftp_test=data.get("is_ftp_test", False),
        intervals=intervals,
    )


def calculate_workout_stats(workout: ZwiftWorkout, ftp: int = 200) -> dict:
    """Calculate workout statistics"""
    total_duration = 0
    total_work = 0  # kJ approximation
    
    for interval in workout.intervals:
        if isinstance(interval, IntervalsT):
            avg_power = (interval.on_power * interval.on_duration +
                        interval.off_power * interval.off_duration) / (interval.on_duration + interval.off_duration)
        elif isinstance(interval, (Warmup, Cooldown, Ramp)):
            avg_power = (interval.power_low + interval.power_high) / 2
        elif isinstance(interval, SteadyState):
            avg_power = interval.power
        elif isinstance(interval, FreeRide):
            avg_power = 0.6  # Estimate
        elif isinstance(interval, MaxEffort):
            avg_power = 1.5  # Estimate
        else:
            avg_power = 0.7

        total_duration += interval.duration
        total_work += avg_power * ftp * interval.duration / 1000  # kJ
    
    # Estimate IF using average power (not NP — accurate for structured workouts with low variability)
    avg_intensity = total_work * 1000 / (ftp * total_duration) if total_duration > 0 else 0

    # Estimated TSS (uses avg-power-based IF; actual TSS may differ due to power variability)
    tss = (total_duration * avg_intensity * avg_intensity) / 3600 * 100
    
    return {
        "total_duration_min": round(total_duration / 60, 1),
        "estimated_kj": round(total_work),
        "estimated_avg_intensity": round(avg_intensity, 2),
        "estimated_tss": round(tss),
        "tss_method": "avg_power (not NP — actual TSS may differ with high power variability)",
    }


def main():
    parser = argparse.ArgumentParser(description="Generate Zwift workout files")
    parser.add_argument("--json", "-j", required=True, help="JSON workout definition file")
    parser.add_argument("--output", "-o", required=True, help="Output .zwo file path")
    parser.add_argument("--ftp", type=int, default=200,
                        help="FTP for stats calculation (generic default; user provides actual FTP via --ftp, must be > 0)")
    args = parser.parse_args()
    
    if not (50 <= args.ftp <= 500):
        parser.error(f"--ftp must be between 50 and 500 watts (got {args.ftp})")

    try:
        with open(args.json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {args.json}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {args.json}: {e}", file=sys.stderr)
        sys.exit(1)

    workout = workout_from_dict(data)
    xml_content = create_zwo_xml(workout)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(xml_content)
    except OSError as e:
        print(f"ERROR: Cannot write output file {args.output}: {e}", file=sys.stderr)
        sys.exit(1)

    stats = calculate_workout_stats(workout, args.ftp)
    print(f"Created: {args.output}")
    print(f"   Duration: {stats['total_duration_min']} min")
    print(f"   Est. TSS: {stats['estimated_tss']}")
    print(f"   Est. Avg Intensity: {stats['estimated_avg_intensity']}")


if __name__ == "__main__":
    main()
