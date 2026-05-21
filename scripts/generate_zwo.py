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
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, fields
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring

# Force UTF-8 on Windows (default cp1252 cannot encode CJK workout names or Unicode
# in error messages routed through stderr).
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')


@dataclass
class TextEvent:
    """Text message displayed during workout"""
    timeoffset: int  # seconds from interval start
    message: str
    duration: int = 10  # display duration in seconds


def _validate_power(value, name="power"):
    if not (0.0 <= value <= 2.0):
        raise ValueError(f"{name}={value} out of range — must be 0.0 <= {name} <= 2.0 (fraction of FTP)")

# Placeholder power for unstructured intervals — FreeRide/MaxEffort have no
# prescribed target, so NP/TSS for them is a guess.
FREERIDE_POWER_PLACEHOLDER = 0.6
MAXEFFORT_POWER_PLACEHOLDER = 1.5

# ERG-mode design thresholds. A Wahoo KICKR settles a power step in ~3-5s, so a
# short high-intensity rep loses its opening seconds. See project CLAUDE.md.
ERG_MICRO_MAX = 30        # seconds — at/below this a high-intensity rep is a "micro" rep
ERG_SHORT_MAX = 120       # seconds — at/below this (above micro) it is a "short" rep
ERG_INTENSITY_MIN = 1.05  # FTP fraction — only reps at/above this intensity matter

@dataclass
class WorkoutInterval:
    """Base class for workout intervals"""
    duration: int  # seconds
    text_events: list[TextEvent] = field(default_factory=list)
    cadence: Optional[int] = None
    cadence_low: Optional[int] = None
    cadence_high: Optional[int] = None

    def __post_init__(self):
        if self.duration <= 0:
            raise ValueError(f"duration must be > 0, got {self.duration}")
        if self.cadence is not None and (self.cadence_low is not None or self.cadence_high is not None):
            raise ValueError("Cannot set both cadence (fixed) and cadence_low/cadence_high (range) — use one or the other")
        # D3-5: a text event at/past the interval's end never fires in Zwift.
        for ev in self.text_events:
            if ev.timeoffset >= self.duration:
                warnings.warn(
                    f"text event at timeoffset={ev.timeoffset}s is at or beyond the "
                    f"interval duration ({self.duration}s) — Zwift will not fire it",
                    stacklevel=2,
                )


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
        # D3-1: Zwift's firing semantics for <textevent> inside <IntervalsT> are
        # unspecified (block- vs rep-relative offset is undocumented; mid-rep cues
        # at offsets > rep duration may never fire). Refuse the pattern outright —
        # flatten to explicit SteadyState work+recovery pairs and cue those.
        if self.text_events:
            raise ValueError(
                "IntervalsT cannot carry text_events — cue-firing semantics for "
                "<textevent> inside <IntervalsT> are unspecified in Zwift. Flatten "
                "the interval into explicit SteadyState work+recovery pairs and put "
                "the cues on those. See references/zwo_format.md → IntervalsT."
            )
        # Auto-calculate duration before parent validation
        calculated = self.repeat * (self.on_duration + self.off_duration)
        if self.duration != 0 and self.duration != calculated:
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
    tags: list[str] = field(default_factory=list)
    intervals: list[WorkoutInterval] = field(default_factory=list)
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
    """Dispatch concrete interval type to its XML element.

    All interval classes are siblings of WorkoutInterval (none subclass each other),
    so the isinstance check order is independent — each branch matches exactly one type.
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


def _interval_from_element(elem: Element) -> WorkoutInterval:
    """Build a WorkoutInterval from a parsed .zwo XML element. Raises ValueError
    for unknown element types or missing required attributes."""
    tag = elem.tag

    def _f(attr):
        v = elem.get(attr)
        if v is None:
            raise ValueError(f"<{tag}> missing required attribute {attr}")
        return float(v)

    def _i(attr):
        v = elem.get(attr)
        if v is None:
            raise ValueError(f"<{tag}> missing required attribute {attr}")
        return int(v)

    text_events = [
        TextEvent(
            timeoffset=int(te.get("timeoffset", "0")),
            message=te.get("message", ""),
            duration=int(te.get("duration", "10")),
        )
        for te in elem.findall("textevent")
    ]
    cadence = elem.get("Cadence")
    cadence_low = elem.get("CadenceLow")
    cadence_high = elem.get("CadenceHigh")
    common = dict(
        text_events=text_events,
        cadence=int(cadence) if cadence is not None else None,
        cadence_low=int(cadence_low) if cadence_low is not None else None,
        cadence_high=int(cadence_high) if cadence_high is not None else None,
    )

    if tag == "Warmup":
        return Warmup(duration=_i("Duration"), power_low=_f("PowerLow"),
                      power_high=_f("PowerHigh"), **common)
    if tag == "Cooldown":
        return Cooldown(duration=_i("Duration"), power_low=_f("PowerLow"),
                        power_high=_f("PowerHigh"), **common)
    if tag == "Ramp":
        return Ramp(duration=_i("Duration"), power_low=_f("PowerLow"),
                    power_high=_f("PowerHigh"), **common)
    if tag == "SteadyState":
        return SteadyState(duration=_i("Duration"), power=_f("Power"), **common)
    if tag == "IntervalsT":
        cr = elem.get("CadenceResting")
        return IntervalsT(
            repeat=_i("Repeat"), on_duration=_i("OnDuration"),
            off_duration=_i("OffDuration"), on_power=_f("OnPower"),
            off_power=_f("OffPower"),
            cadence_resting=int(cr) if cr is not None else None, **common)
    if tag == "FreeRide":
        return FreeRide(duration=_i("Duration"),
                        flat_road=elem.get("FlatRoad") == "1",
                        ftptest=elem.get("ftptest") == "1",
                        show_avg=elem.get("show_avg") == "1", **common)
    if tag == "MaxEffort":
        return MaxEffort(duration=_i("Duration"), **common)
    raise ValueError(f"Unknown interval element: <{tag}>")


def workout_from_xml(xml_string: str) -> ZwiftWorkout:
    """Parse a .zwo XML string into a ZwiftWorkout — the inverse of create_zwo_xml.

    Strict: raises ValueError on malformed XML, a wrong root element, a missing
    <workout>, unknown interval types, or invalid attribute values.
    """
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        raise ValueError(f"Malformed XML: {e}") from e
    if root.tag != "workout_file":
        raise ValueError(f"Root element is <{root.tag}>, expected <workout_file>")

    def _text(tag, default=""):
        el = root.find(tag)
        return el.text if (el is not None and el.text is not None) else default

    workout_elem = root.find("workout")
    if workout_elem is None:
        raise ValueError("No <workout> element found")

    intervals = [_interval_from_element(e) for e in workout_elem]
    category = _text("category", "")

    return ZwiftWorkout(
        name=_text("name", "Custom Workout"),
        author=_text("author", "Cycling Fitness Coach"),
        description=_text("description", ""),
        sport_type=_text("sportType", "bike"),
        tags=[t.get("name", "") for t in root.findall("tags/tag")],
        category=category or None,
        is_ftp_test=workout_elem.get("ftptest") == "1",
        intervals=intervals,
    )


def synthesize_power_timeline(workout: ZwiftWorkout) -> list[float]:
    """Build a per-second FTP-fraction power array from the workout structure.

    One sample per second — the input for Normalised-Power-based TSS estimation.
    SteadyState -> constant; Warmup/Cooldown/Ramp -> linear sweep; IntervalsT ->
    expanded on/off square wave; FreeRide/MaxEffort -> placeholder power.
    """
    timeline: list[float] = []
    for interval in workout.intervals:
        if isinstance(interval, SteadyState):
            timeline.extend([interval.power] * interval.duration)
        elif isinstance(interval, (Warmup, Cooldown, Ramp)):
            d = interval.duration
            lo, hi = interval.power_low, interval.power_high
            # Sample at the midpoint of each second so the mean is symmetric.
            timeline.extend(lo + (hi - lo) * (t + 0.5) / d for t in range(d))
        elif isinstance(interval, IntervalsT):
            for _ in range(interval.repeat):
                timeline.extend([interval.on_power] * interval.on_duration)
                timeline.extend([interval.off_power] * interval.off_duration)
        elif isinstance(interval, FreeRide):
            timeline.extend([FREERIDE_POWER_PLACEHOLDER] * interval.duration)
        elif isinstance(interval, MaxEffort):
            timeline.extend([MAXEFFORT_POWER_PLACEHOLDER] * interval.duration)
        else:
            timeline.extend([0.7] * interval.duration)
    return timeline


def _compute_np(timeline: list[float]) -> Optional[float]:
    """Normalised Power from a per-second power array (FTP fractions in, fraction out).

    30s rolling average -> 4th power -> mean -> 4th root. Returns None if the
    timeline is shorter than the 30s window. No intermediate rounding — the
    NP -> IF -> TSS chain magnifies precision loss; round only at display.
    """
    if len(timeline) < 30:
        return None
    window_sum = sum(timeline[:30])
    rolling_fourth = (window_sum / 30) ** 4
    for i in range(1, len(timeline) - 29):
        window_sum += timeline[i + 29] - timeline[i - 1]
        rolling_fourth += (window_sum / 30) ** 4
    n_windows = len(timeline) - 29
    return (rolling_fourth / n_windows) ** 0.25


def calculate_workout_stats(workout: ZwiftWorkout, ftp: int = 200) -> dict:
    """Calculate workout statistics using NP-based TSS estimation.

    TSS is derived from Normalised Power computed over a synthesized per-second
    power timeline, so interval variability is captured directly (no avg-power
    under-report). For ftptest workouts the test effort is rider-controlled, so
    TSS is reported as unmodeled rather than as a misleading placeholder number.
    """
    timeline = synthesize_power_timeline(workout)
    total_duration = len(timeline)
    total_work = sum(frac * ftp for frac in timeline) / 1000  # kJ

    has_unstructured = any(
        isinstance(i, (FreeRide, MaxEffort)) for i in workout.intervals
    )

    # FTP-test workouts: the main effort is a rider-controlled FreeRide — an
    # NP estimate off the 0.6 placeholder would be badly wrong. Report unmodeled.
    if workout.is_ftp_test:
        return {
            "total_duration_min": round(total_duration / 60, 1),
            "estimated_kj": round(total_work),
            "estimated_if": None,
            "estimated_tss": None,
            "tss_method": "unmodeled (FTP test — rider-controlled effort)",
            "tss_estimated": True,
            "tss_warning": ("FTP-test workout — TSS depends on rider execution "
                            "and is not modeled."),
        }

    np_frac = _compute_np(timeline)
    if np_frac is not None:
        tss_method = "np_modeled — assumes prescribed-power execution"
    else:
        # Workout shorter than the 30s NP window — fall back to mean power.
        np_frac = (sum(timeline) / total_duration) if total_duration > 0 else 0.0
        tss_method = "avg_power (<30s — NP window not reached)"

    # NP is already in FTP-fraction units, so IF = NP / FTP = np_frac directly.
    if_value = np_frac
    tss = (total_duration * if_value * if_value) / 3600 * 100

    tss_warning = None
    if has_unstructured:
        tss_warning = (
            f"FreeRide/MaxEffort intervals present — TSS uses placeholder power "
            f"({FREERIDE_POWER_PLACEHOLDER} FTP FreeRide, "
            f"{MAXEFFORT_POWER_PLACEHOLDER} FTP MaxEffort). Actual TSS depends "
            f"on rider effort and may vary by ±50%."
        )

    return {
        "total_duration_min": round(total_duration / 60, 1),
        "estimated_kj": round(total_work),
        "estimated_if": round(if_value, 2),
        "estimated_tss": round(tss),
        "tss_method": tss_method,
        "tss_estimated": has_unstructured,
        "tss_warning": tss_warning,
    }


def erg_rep_severity(duration_s: int, power_frac: float) -> Optional[str]:
    """Classify an ERG work rep's design risk.

    Returns "micro" (<=30s), "short" (31-120s), or None. Only high-intensity
    reps (power >= 1.05 FTP) are flagged — a short Z2 block is unaffected by
    ERG settling lag.
    """
    if power_frac < ERG_INTENSITY_MIN:
        return None
    if duration_s <= ERG_MICRO_MAX:
        return "micro"
    if duration_s <= ERG_SHORT_MAX:
        return "short"
    return None


def check_erg_design(workout: ZwiftWorkout) -> list[str]:
    """Return ERG-design warning strings for short high-intensity reps.

    Checks IntervalsT on-reps and SteadyState blocks. Used to surface the ERG
    long-rep design rule on generator output.
    """
    out: list[str] = []
    for interval in workout.intervals:
        if isinstance(interval, IntervalsT):
            dur, pw = interval.on_duration, interval.on_power
        elif isinstance(interval, SteadyState):
            dur, pw = interval.duration, interval.power
        else:
            continue
        sev = erg_rep_severity(dur, pw)
        if sev == "micro":
            out.append(
                f"ERG micro-interval: {dur}s rep at {pw:.2f} FTP — the trainer "
                f"cannot track a step this short. Design >=2-3min reps, or label "
                f"the file for resistance/non-ERG riding."
            )
        elif sev == "short":
            out.append(
                f"ERG short rep: {dur}s rep at {pw:.2f} FTP — the first ~3-5s are "
                f"lost to ERG settling. >=2-3min reps recommended for VO2max work."
            )
    return out


def build_parser():
    """Build the CLI argument parser. Exposed for tests and reuse."""
    parser = argparse.ArgumentParser(description="Generate Zwift workout files")
    parser.add_argument("--json", "-j", required=True, help="JSON workout definition file")
    parser.add_argument("--output", "-o", required=True, help="Output .zwo file path")
    parser.add_argument("--ftp", type=int, default=None,
                        help="FTP in watts for stats calculation (50-500). If omitted, "
                             "defaults to 200 with a warning — always pass the athlete's "
                             "real FTP or the TSS/intensity estimates will be wrong.")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    
    if args.ftp is None:
        print("WARNING: --ftp not supplied — using 200W for stats. TSS and intensity "
              "estimates will be wrong unless 200W is the athlete's actual FTP. "
              "Re-run with --ftp <actual> for accurate numbers.", file=sys.stderr)
        args.ftp = 200

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
    tss = stats["estimated_tss"]
    print(f"   Est. TSS: {tss if tss is not None else 'unmodeled (FTP test)'}")
    if stats["estimated_if"] is not None:
        print(f"   Est. IF: {stats['estimated_if']}")
    print(f"   TSS method: {stats['tss_method']}")
    for erg_warning in check_erg_design(workout):
        print(f"   ERG-design warning: {erg_warning}", file=sys.stderr)


if __name__ == "__main__":
    main()
