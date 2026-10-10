
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime

FILE = "data/export.xml"

DISTANCE = "HKQuantityTypeIdentifierDistanceSwimming"
STROKES = "HKQuantityTypeIdentifierSwimmingStrokeCount"


def parse_time(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")


def inspect():
    lengths = []
    strokes = []
    workouts = []

    context = ET.iterparse(FILE, events=("start", "end"))
    _, root = next(context)

    for event, elem in context:
        if event != "end":
            continue

        if elem.tag == "Record":
            kind = elem.get("type")

            if kind in (DISTANCE, STROKES):
                record = {
                    "start": parse_time(elem.get("startDate")),
                    "end": parse_time(elem.get("endDate")),
                    "value": float(elem.get("value", 0)),
                    "unit": elem.get("unit", ""),
                }

                if record["start"] and record["end"]:
                    if kind == DISTANCE:
                        lengths.append(record)
                    else:
                        strokes.append(record)

            root.clear()

        elif elem.tag == "Workout":
            if "Swimming" in elem.get("workoutActivityType", ""):
                events = []

                for child in elem:
                    if child.tag == "WorkoutEvent":
                        events.append({
                            "type": (
                                child.get("type")
                                or child.get("eventType")
                                or "unknown"
                            ),
                            "fields": tuple(sorted(child.attrib)),
                        })

                workouts.append({
                    "start": parse_time(elem.get("startDate")),
                    "end": parse_time(elem.get("endDate")),
                    "events": events,
                })

            root.clear()

    for index, workout in enumerate(workouts, 1):
        start, end = workout["start"], workout["end"]

        if not start or not end:
            continue

        swim_lengths = sorted(
            (r for r in lengths
             if start <= r["start"] <= r["end"] <= end),
            key=lambda r: (r["start"], r["end"])
        )

        swim_strokes = [
            r for r in strokes
            if start <= r["start"] <= r["end"] <= end
        ]

        length_times = Counter(
            (r["start"], r["end"]) for r in swim_lengths
        )
        stroke_times = Counter(
            (r["start"], r["end"]) for r in swim_strokes
        )

        matched = sum(
            min(count, stroke_times[key])
            for key, count in length_times.items()
        )

        gaps = []
        overlaps = 0

        for previous, current in zip(
            swim_lengths, swim_lengths[1:]
        ):
            gap = (
                current["start"] - previous["end"]
            ).total_seconds()

            if gap > 0:
                gaps.append(gap)
            elif gap < 0:
                overlaps += 1

        length_seconds = sum(
            (r["end"] - r["start"]).total_seconds()
            for r in swim_lengths
        )

        workout_seconds = (end - start).total_seconds()

        event_types = Counter(
            e["type"] for e in workout["events"]
        )

        pause_fields = Counter(
            e["fields"]
            for e in workout["events"]
            if "Pause" in e["type"] or "Resume" in e["type"]
        )

        print(f"\n=== SWIM {index} ===")
        print(
            f"Workout duration: {workout_seconds / 60:.1f} min"
        )
        print(f"Pool lengths completed: {len(swim_lengths)}")
        print(f"Lengths with stroke data: {len(swim_strokes)}")
        print(f"Matching length/stroke timestamps: {matched}")
        print(f"Overlapping pool lengths: {overlaps}")
        print(f"Gaps between lengths: {len(gaps)}")
        print(
            f"Time between lengths: {sum(gaps):.1f} sec"
        )
        print(
            f"Recorded length time: {length_seconds:.1f} sec"
        )
        print(
            f"Workout elapsed time: {workout_seconds:.1f} sec"
        )
        print(f"Recorded events: {dict(event_types)}")
        print(
            "Pause/resume field names:",
            dict(pause_fields)
        )

    print("\nTiming inspection complete.")


if __name__ == "__main__":
    inspect()
