"""First-mile pool swim analysis from a local Apple Health XML export.

Uses the Python standard library. Does not upload or modify health data.
"""
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

MILE_METERS = 1609.344
DISTANCE = 'HKQuantityTypeIdentifierDistanceSwimming'
STROKES = 'HKQuantityTypeIdentifierSwimmingStrokeCount'
HEART_RATE = 'HKQuantityTypeIdentifierHeartRate'
PAUSE_TYPES = {'HKWorkoutEventTypePause', 'HKWorkoutEventTypeMotionPaused'}
RESUME_TYPES = {'HKWorkoutEventTypeResume', 'HKWorkoutEventTypeMotionResumed'}


def timestamp(value):
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S %z')


def seconds_label(seconds):
    seconds = max(0, round(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f'{hours}:{minutes:02d}:{secs:02d}' if hours else f'{minutes}:{secs:02d}'


def distance_meters(value, unit):
    factors = {'m': 1.0, 'km': 1000.0, 'yd': 0.9144, 'mi': 1609.344}
    if unit not in factors:
        raise ValueError(f'Unsupported distance unit: {unit}')
    return float(value) * factors[unit]


def read_export(path):
    workouts, lengths, strokes, heart_rates = [], [], [], []
    context = ET.iterparse(path, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event != 'end':
            continue
        if elem.tag == 'Record':
            kind = elem.get('type')
            if kind in (DISTANCE, STROKES, HEART_RATE):
                try:
                    record = {
                        'start': timestamp(elem.attrib['startDate']),
                        'end': timestamp(elem.attrib['endDate']),
                        'value': float(elem.attrib['value']),
                        'unit': elem.get('unit', ''),
                    }
                except (KeyError, ValueError):
                    record = None
                if record is not None:
                    if kind == DISTANCE:
                        lengths.append(record)
                    elif kind == STROKES:
                        strokes.append(record)
                    else:
                        heart_rates.append(record)
            root.clear()
        elif elem.tag == 'Workout':
            if 'Swimming' in elem.get('workoutActivityType', ''):
                try:
                    events = []
                    for child in elem:
                        if child.tag != 'WorkoutEvent':
                            continue
                        kind = child.get('type') or child.get('eventType')
                        date = child.get('date')
                        if kind and date:
                            try:
                                events.append((timestamp(date), kind))
                            except ValueError:
                                pass
                    workouts.append({
                        'start': timestamp(elem.attrib['startDate']),
                        'end': timestamp(elem.attrib['endDate']),
                        'events': events,
                    })
                except (KeyError, ValueError):
                    pass
            root.clear()
    workouts.sort(key=lambda w: w['start'], reverse=True)
    return workouts, lengths, strokes, heart_rates


def inside(record, workout):
    return (workout['start'] <= record['start']
            and record['end'] <= workout['end']
            and record['end'] >= record['start'])


def recorded_pause_intervals(workout, crossing):
    """Return confirmed pause/resume pairs, plus event-sequence completeness."""
    events = sorted((date, kind) for date, kind in workout.get('events', [])
                    if workout['start'] <= date <= crossing
                    and kind in PAUSE_TYPES | RESUME_TYPES)
    paused_at = None
    intervals = []
    complete = True
    for date, kind in events:
        if kind in PAUSE_TYPES:
            if paused_at is not None:
                complete = False
            else:
                paused_at = date
        elif paused_at is None:
            complete = False
        else:
            intervals.append((paused_at, date))
            paused_at = None
    if paused_at is not None:
        complete = False
    return intervals, complete


def overlap_seconds(start, end, intervals):
    return sum(max(0.0, (min(end, b) - max(start, a)).total_seconds())
               for a, b in intervals)


def analyze_first_mile(workout, all_lengths, all_strokes, all_heart_rates):
    lengths = sorted((r for r in all_lengths if inside(r, workout)),
                     key=lambda r: (r['start'], r['end']))
    if not lengths:
        return None
    try:
        total = sum(distance_meters(r['value'], r['unit']) for r in lengths)
    except ValueError:
        return None
    if total < MILE_METERS - 1e-6:
        return {'short': True, 'total': total}

    cumulative = 0.0
    crossing = None
    swim_seconds = 0.0
    included = []
    estimated = False
    for length in lengths:
        meters = distance_meters(length['value'], length['unit'])
        if meters <= 0:
            continue
        duration = (length['end'] - length['start']).total_seconds()
        if duration < 0:
            continue
        portion = min(1.0, (MILE_METERS - cumulative) / meters)
        swim_seconds += duration * portion
        length_end = length['start'] + timedelta(seconds=duration * portion)
        included.append((length, portion, length_end))
        cumulative += meters * portion
        if cumulative >= MILE_METERS - 1e-6:
            crossing = length['start'] + timedelta(seconds=duration * portion)
            estimated = portion < 1 - 1e-6
            break
    if crossing is None:
        return None

    elapsed = (crossing - workout['start']).total_seconds()
    if elapsed <= 0 or swim_seconds > elapsed + 1e-6:
        return None
    pause_intervals, pauses_complete = recorded_pause_intervals(workout, crossing)
    pauses = overlap_seconds(workout['start'], crossing, pause_intervals)
    pause_during_lengths = sum(
        overlap_seconds(length['start'], length_end, pause_intervals)
        for length, portion, length_end in included
    )
    # Partition the timeline without counting any paused second twice.
    unpaused_swimming = max(0.0, swim_seconds - pause_during_lengths)
    unpaused_other = max(0.0, elapsed - pauses - unpaused_swimming)
    unpaused = max(0.0, elapsed - pauses)

    stroke_lookup = {}
    for r in all_strokes:
        if inside(r, workout):
            stroke_lookup.setdefault((r['start'], r['end']), []).append(r['value'])
    stroke_total = 0.0
    stroke_complete = True
    for length, portion, length_end in included:
        values = stroke_lookup.get((length['start'], length['end']))
        if not values or len(values) != 1:
            stroke_complete = False
            break
        stroke_total += values[0] * portion

    hr = [r['value'] for r in all_heart_rates
          if inside(r, workout) and r['unit'] == 'count/min'
          and workout['start'] <= r['start'] <= crossing]
    return {
        'short': False,
        'elapsed': elapsed,
        'swimming': swim_seconds,
        'unpaused_swimming': unpaused_swimming,
        'unpaused_other': unpaused_other,
        'unpaused': unpaused,
        'recorded_pauses': pauses,
        'pauses_complete': pauses_complete,
        'elapsed_pace_100m': elapsed / (MILE_METERS / 100),
        'swimming_pace_100m': swim_seconds / (MILE_METERS / 100),
        'heart_rate': sum(hr) / len(hr) if hr else None,
        'strokes': stroke_total if stroke_complete else None,
        'estimated': estimated,
    }


def main():
    parser = argparse.ArgumentParser(description='First-mile pool swimming report')
    parser.add_argument('--file', default='data/export.xml', help='Apple Health export XML')
    parser.add_argument('--workout', type=int, help='Workout number (newest first)')
    args = parser.parse_args()
    try:
        workouts, lengths, strokes, hr = read_export(args.file)
    except (OSError, ET.ParseError, ValueError) as exc:
        parser.exit(1, f'Could not read export: {exc}\n')
    if not workouts:
        parser.exit(1, 'No swimming workouts found.\n')

    print('\nSwimming workouts (newest first):')
    for i, w in enumerate(workouts, 1):
        print(f"  {i}. {w['start'].strftime('%B %d, %Y')} — "
              f"{seconds_label((w['end'] - w['start']).total_seconds())}")
    choice = args.workout
    if choice is None:
        try:
            choice = int(input('\nChoose a workout number: '))
        except (ValueError, EOFError, KeyboardInterrupt):
            parser.exit(1, '\nPlease enter a valid workout number.\n')
    if not 1 <= choice <= len(workouts):
        parser.exit(1, 'Invalid workout number.\n')
    result = analyze_first_mile(workouts[choice - 1], lengths, strokes, hr)
    if result is None:
        parser.exit(1, 'Not enough valid length timing data to analyze this swim.\n')
    if result['short']:
        print(f"\nThis swim covered {result['total']:.0f} m, less than one mile (1,609 m).")
        return

    print('\n=== FIRST-MILE SWIMMING REPORT ===')
    print(f"Mile Time: {seconds_label(result['elapsed'])}" +
          (' (estimated)' if result['estimated'] else ''))
    if result['pauses_complete']:
        print(f"Unpaused Time: {seconds_label(result['unpaused'])}")
        print(f"Swimming Time: {seconds_label(result['unpaused_swimming'])}")
        print(f"Unpaused Rest / Other: {seconds_label(result['unpaused_other'])}")
        print(f"Paused Time: {seconds_label(result['recorded_pauses'])}")
    else:
        print(f"Recorded Length Time: {seconds_label(result['swimming'])}")
        print('Pause breakdown unavailable: pause/resume history is incomplete.')
        if result['recorded_pauses']:
            print(f"Confirmed Paused Time (minimum): {seconds_label(result['recorded_pauses'])}")
    print(f"Overall Pace: {seconds_label(result['elapsed_pace_100m'])} /100 m (includes breaks)")
    print(f"Swimming Pace: {seconds_label(result['swimming_pace_100m'])} /100 m (recorded lengths)")
    if result['heart_rate'] is not None:
        print(f"Average Heart Rate: {result['heart_rate']:.0f} bpm")
    if result['strokes'] is not None:
        print(f"Estimated Strokes: {result['strokes']:.0f}")
    if result['pauses_complete']:
        print('Timing categories do not overlap.')
    else:
        print('Recorded length time may include paused intervals;')
        print('a complete unpaused/rest breakdown cannot be verified.')
    if result['estimated']:
        print('Mile crossing is estimated within a pool length.')


if __name__ == '__main__':
    main()
