
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime

EXPORT_FILE = "data/export.xml"

SWIM_DISTANCE = "HKQuantityTypeIdentifierDistanceSwimming"
SWIM_STROKES = "HKQuantityTypeIdentifierSwimmingStrokeCount"
HEART_RATE = "HKQuantityTypeIdentifierHeartRate"


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")


def inspect_export(path):
    workouts = []
    distance_records = []
    stroke_records = []
    heart_rates = []

    # Stream the XML so we don't load the entire export into memory.
    context = ET.iterparse(path, events=("start", "end"))
    _, root = next(context)

    for event, elem in context:
        if event != "end":
            continue

        if elem.tag == "Record":
            record_type = elem.get("type")

            if record_type in (SWIM_DISTANCE, SWIM_STROKES, HEART_RATE):
                record = {
                    "start": parse_date(elem.get("startDate")),
                    "end": parse_date(elem.get("endDate")),
                    "value": float(elem.get("value", 0)),
                    "unit": elem.get("unit", ""),
                }

                if record_type == SWIM_DISTANCE:
                    distance_records.append(record)
                elif record_type == SWIM_STROKES:
                    stroke_records.append(record)
                else:
                    heart_rates.append(record)

        elif elem.tag == "Workout":
            if "Swimming" in elem.get("workoutActivityType", ""):
                event_counts = Counter()

                for child in elem:
                    if child.tag == "WorkoutEvent":
                        event_type = (
                            child.get("type")
                            or child.get("eventType")
                            or "unknown"
                        )
                        event_counts[event_type] += 1

                workouts.append({
                    "start": parse_date(elem.get("startDate")),
                    "end": parse_date(elem.get("endDate")),
                    "events": event_counts,
                })

        # Clear only top-level elements after they are processed.
        # Clearing every nested element would erase workout events.
        if elem.tag in ("Record", "Workout"):
            root.clear()

    print("\n=== SWIMMING DATA INSPECTION ===")

    for index, workout in enumerate(workouts, start=1):
        start = workout["start"]
        end = workout["end"]

        distances = [
            r for r in distance_records
            if start <= r["start"] and r["end"] <= end
        ]
        strokes = [
            r for r in stroke_records
            if start <= r["start"] and r["end"] <= end
        ]
        hr = [
            r for r in heart_rates
            if start <= r["start"] and r["end"] <= end
        ]

        duration = (end - start).total_seconds()

        distance_units = Counter(r["unit"] for r in distances)
        distance_values = Counter(
            (r["value"], r["unit"]) for r in distances
        )

        print(f"\nWorkout {index}")
        print(f"Duration: {duration / 60:.1f} minutes")
        print(f"Distance records: {len(distances)}")
        print(f"Stroke records: {len(strokes)}")
        print(f"Heart-rate records: {len(hr)}")
        print(f"Distance units: {dict(distance_units)}")
        print(f"Common length values: {distance_values.most_common(3)}")
        print(f"Workout events: {dict(workout['events'])}")

    print("\nInspection complete. No health data was modified.")


if __name__ == "__main__":
    inspect_export(EXPORT_FILE)
