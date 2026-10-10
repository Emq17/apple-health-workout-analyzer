#!/usr/bin/env python3

"""Local Apple Health running cadence analyzer. Python 3.9+, standard library only."""

import argparse

from collections import defaultdict

from datetime import datetime, timedelta

from pathlib import Path

import sys

import xml.etree.ElementTree as ET



STEP_TYPE = 'HKQuantityTypeIdentifierStepCount'

RUNNING_TYPES = {'HKWorkoutActivityTypeRunning'}





def timestamp(s):

    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S %z')





def stream_elements(path, tag):

    # Only keep the current top-level child; do not retain the 100s of MB XML tree.

    context = ET.iterparse(str(path), events=('start', 'end'))

    _, root = next(context)

    for event, element in context:

        if event == 'end' and element.tag == tag:

            yield dict(element.attrib)

        if event == 'end' and element.tag in ('Record', 'Workout', 'Correlation', 'ActivitySummary'):

            root.clear()





def list_workouts(path):

    workouts = []

    for row in stream_elements(path, 'Workout'):

        if row.get('workoutActivityType') not in RUNNING_TYPES:

            continue

        try:

            start, end = timestamp(row['startDate']), timestamp(row['endDate'])

        except (KeyError, ValueError):

            continue

        if end > start:

            workouts.append({'start': start, 'end': end, 'source': row.get('sourceName', '')})

    return sorted(workouts, key=lambda w: w['start'], reverse=True)





def overlapping_steps(path, start, end):

    records = []

    for row in stream_elements(path, 'Record'):

        if row.get('type') != STEP_TYPE:

            continue

        try:

            a, b = timestamp(row['startDate']), timestamp(row['endDate'])

            steps = float(row['value'])

        except (KeyError, ValueError):

            continue

        if a < end and b > start and b > a and steps >= 0:

            records.append({'start': a, 'end': b, 'steps': steps, 'source': row.get('sourceName', '')})

    return records





def summarize(records, start, end):

    intervals = []

    steps = 0.0

    for r in records:

        a, b = max(r['start'], start), min(r['end'], end)

        if b <= a:

            continue

        duration = (r['end'] - r['start']).total_seconds()

        span = (b - a).total_seconds()

        steps += r['steps'] * span / duration

        intervals.append((a, b))

    intervals.sort()

    merged = []

    for a, b in intervals:

        if not merged or a > merged[-1][1]:

            merged.append([a, b])

        else:

            merged[-1][1] = max(merged[-1][1], b)

    covered = sum((b-a).total_seconds() for a, b in merged)

    summed = sum((b-a).total_seconds() for a, b in intervals)

    seconds = (end-start).total_seconds()

    return {'steps': steps, 'count': len(intervals), 'seconds': seconds,

            'covered': covered, 'missing': max(0.0, seconds-covered),

            'overlap': max(0.0, summed-covered),

            'cadence': steps/seconds*60 if seconds else None}





def choose_source(records, preferred, supplied, non_interactive):

    by_source = defaultdict(list)

    for r in records:

        by_source[r['source']].append(r)

    if not by_source:

        raise ValueError('No step-count records overlap this interval. The export may not contain them.')

    names = sorted(by_source)

    if supplied is not None:

        if supplied not in by_source:

            raise ValueError('Unknown source. Available sources: ' + ', '.join(repr(n) for n in names))

        return supplied, by_source[supplied]

    if preferred in by_source:

        return preferred, by_source[preferred]

    if len(names) == 1:

        print('Note: workout source differs from step source; using the only available step source.')

        return names[0], by_source[names[0]]

    if non_interactive or not sys.stdin.isatty():

        raise ValueError('Multiple step sources and no exact workout-source match. Rerun with --source NAME. Options: ' + ', '.join(repr(n) for n in names))

    print('Multiple step sources found. Choose one (do not combine sources):')

    for i, name in enumerate(names, 1):

        print(f'  {i}. {name or "(unnamed)"} ({len(by_source[name])} records)')

    answer = input('Source number: ').strip()

    if not answer.isdigit() or not 1 <= int(answer) <= len(names):

        raise ValueError('Invalid source selection')

    selected = names[int(answer)-1]

    return selected, by_source[selected]





def mmss(value):

    parts = value.split(':')

    if len(parts) == 1:

        return float(parts[0])

    if len(parts) == 2:

        return int(parts[0])*60 + float(parts[1])

    if len(parts) == 3:

        return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])

    raise ValueError('Use seconds, MM:SS, or HH:MM:SS')







def format_duration(seconds):

    whole = int(seconds)

    hours, remainder = divmod(whole, 3600)

    minutes, secs = divmod(remainder, 60)

    return f'{hours:02}:{minutes:02}:{secs:02}' if hours else f'{minutes:02}:{secs:02}'





def select_interval(length, start_arg=None, end_arg=None, interactive=True, workout_start=None):

    """Choose whole workout or a custom section, returning offsets in seconds."""

    if start_arg is not None or end_arg is not None or not interactive:

        a = mmss(start_arg) if start_arg is not None else 0.0

        b = mmss(end_arg) if end_arg is not None else length

    else:

        if workout_start is not None:
            print(f'\nSelected workout: {workout_start:%B %d, %Y at %I:%M %p}')
        else:
            print('\nSelected workout')

        print('What would you like to analyze?')

        print('  1. Entire workout')

        print('  2. Specific section')

        choice = input('Selection (1 or 2): ').strip()

        if choice == '1':

            a, b = 0.0, length

        elif choice == '2':

            print('Enter times measured from the start of the workout (MM:SS or HH:MM:SS).')

            a = mmss(input('Section start (e.g. 00:17): ').strip())

            b = mmss(input('Section end (e.g. 08:27): ').strip())

        else:

            raise ValueError('Choose 1 for entire workout or 2 for a specific section.')

    if not 0 <= a < b <= length + 0.001:

        raise ValueError(f'Section must be within the workout (00:00 to {format_duration(length)}).')

    return a, b





def main():

    parser = argparse.ArgumentParser(description='Private, local running cadence analysis from Apple Health XML')

    parser.add_argument('--file', type=Path, default=Path('data/export.xml'), help='Path to Apple Health export.xml')

    parser.add_argument('--list-workouts', action='store_true')

    parser.add_argument('--workout', type=int, help='1-based workout number from --list-workouts')

    parser.add_argument('--start', help='Optional section start from workout beginning (seconds or MM:SS)')

    parser.add_argument('--end', help='Optional section end from workout beginning (seconds or MM:SS)')

    parser.add_argument('--source', help='Exact step-count source name if automatic matching is ambiguous')

    parser.add_argument('--non-interactive', action='store_true')

    args = parser.parse_args()

    if not args.file.is_file():

        parser.error(f'XML file not found: {args.file}')

    try:

        workouts = list_workouts(args.file)

        if not workouts:

            raise ValueError('No running workouts found in the export.')

        if args.list_workouts or args.workout is None:

            print(f'Found {len(workouts)} running workouts:')

            for i, w in enumerate(workouts, 1):

                print(f'{i:3}. {w["start"]:%Y-%m-%d %H:%M} | {(w["end"]-w["start"]).total_seconds()/60:.1f} min')

            if args.list_workouts:

                return

            if args.non_interactive or not sys.stdin.isatty():

                raise ValueError('Specify --workout NUMBER')

            selected = input('Workout number: ').strip()

            if not selected.isdigit():

                raise ValueError('Invalid workout number')

            args.workout = int(selected)

        if not 1 <= args.workout <= len(workouts):

            raise ValueError('Workout number out of range')

        w = workouts[args.workout-1]

        length = (w['end']-w['start']).total_seconds()

        a, b = select_interval(

            length, args.start, args.end,

            interactive=not args.non_interactive and sys.stdin.isatty(),
            workout_start=w['start']

        )

        start, end = w['start']+timedelta(seconds=a), w['start']+timedelta(seconds=b)

        records = overlapping_steps(args.file, start, end)

        source, selected = choose_source(records, w['source'], args.source, args.non_interactive)

        result = summarize(selected, start, end)

        print('\n=== RUNNING ANALYSIS ===')
        print(f'Workout Duration: {format_duration(result["seconds"])}')
        print(f'Average Cadence: {result["cadence"]:.2f} SPM')
        print(f'Estimated Steps: {result["steps"]:,.0f}')
        print('\nAnalysis Complete!')
    except (ValueError, ET.ParseError, OSError) as exc:

        parser.exit(1, f'Error: {exc}\n')





if __name__ == '__main__':

    main()
