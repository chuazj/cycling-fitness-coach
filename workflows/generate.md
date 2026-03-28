# Workflow: Zwift Workout Generation

Covers Workflow 3 (single ZWO file generation).

---

## 3. Zwift Workout Generation

1. Clarify: type, duration, FTP, focus
2. Design with warm-up, main set, cool-down
3. Generate .zwo via `references/zwo_format.md` or `scripts/generate_zwo.py`
4. Power values as FTP fractions (0.88 = 88%); max 2.0; warmup ramps up, cooldown ramps down
5. See `references/training_zones.md` for zone boundaries, cadence targets, and common prescriptions
6. **ZWO tag reference**: When unsure about attribute names or supported elements, consult https://github.com/h4l/zwift-workout-file-reference/blob/master/zwift_workout_file_tag_reference.md — this is the canonical reference for all Zwift .zwo XML attributes

**Output template:**

```
## Workout: [Name]
**Duration**: Xmin | **Est. TSS**: X | **Target IF**: X.XX
**Structure**:
- Warmup: [duration, ramp range]
- Main Set: [intervals x duration @ intensity]
- Cooldown: [duration, ramp range]
**Execution Notes**: [Cadence targets, pacing tips, what to focus on]
**File**: [path to generated .zwo]
```
