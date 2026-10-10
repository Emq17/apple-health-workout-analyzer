# Apple Health Workout Analyzer

A privacy-first **Python command-line tool** for analyzing running and pool-swimming workouts from an Apple Health XML export.

- **Running:** Estimate average cadence (steps per minute) for an entire run or a chosen time interval.
- **Pool swimming:** Estimate your **first-mile split**, even if you swam farther than a mile, with pace, swimming time, pauses, heart rate, and stroke counts when available.

**Version 1 runs locally in Terminal.** No website, mobile app, account, API key, or third-party Python package is required.

## Requirements

- Python 3.9 or newer
- An Apple Health `export.xml` file containing the relevant workouts and measurements
- Terminal (macOS, Linux, or Windows with Python installed)

## Setup

1. Download or clone this repository and open Terminal in the `apple-health-workout-analyzer` folder.
2. On your iPhone, open **Health**, tap your profile picture, and choose **Export All Health Data**.
3. Unzip the exported archive on your computer.
4. Create a `data` folder inside the project if needed, and copy `export.xml` into it, so the path is `data/export.xml`.
5. Choose a running or swimming command below.

**Privacy:** Your Apple Health export contains sensitive personal information. Never commit or upload `data/export.xml` to GitHub. You can also leave the export elsewhere on your computer and use the `--file` option.

## Running cadence

Start the interactive running analyzer:

```bash
python3 src/extract_cadence.py
```

Choose a workout, then select either the **entire workout** or a **specific section**. Section times are offsets from the beginning of the workout.

Other commands:

```bash
# List running workouts
python3 src/extract_cadence.py --list-workouts

# Analyze the newest listed workout without prompts
python3 src/extract_cadence.py --workout 1 --non-interactive

# Analyze a specific section (15 seconds through 8 minutes 15 seconds)
python3 src/extract_cadence.py --workout 1 --start 00:15 --end 08:15 --non-interactive

# Use an export stored elsewhere
python3 src/extract_cadence.py --file /path/to/export.xml
```

If multiple devices contribute overlapping step records, use `--source "EXACT SOURCE NAME"` to select a source. Run `python3 src/extract_cadence.py --help` for the full list of options.

**Example running output** (fictional):

```text
=== RUNNING ANALYSIS ===
Workout Duration: 10:00
Average Cadence: 180.00 SPM
Estimated Steps: 1,800

Analysis Complete!
```

## Swimming: first-mile analysis

Start the swimming analyzer:

```bash
python3 src/analyze_swimming.py
```

The program lists swimming workouts **newest first**. Enter a workout number to see the first-mile report. If the swim was shorter than one mile, it tells you rather than inventing a split.

To select a workout directly:

```bash
# Newest swim
python3 src/analyze_swimming.py --workout 1

# Second-newest swim
python3 src/analyze_swimming.py --workout 2

# Read an export stored elsewhere
python3 src/analyze_swimming.py --file /path/to/export.xml --workout 1
```

**Example swimming output** (fictional values):

```text
=== FIRST-MILE SWIMMING REPORT ===
Mile Time: 1:05:00 (estimated)
Unpaused Time: 1:02:00
Swimming Time: 45:00
Unpaused Rest / Other: 17:00
Paused Time: 3:00
Overall Pace: 4:02 /100 m (includes breaks)
Swimming Pace: 2:48 /100 m (recorded lengths)
Average Heart Rate: 140 bpm
Estimated Strokes: 1,100
Timing categories do not overlap.
Mile crossing is estimated within a pool length.
```

**What the swimming results mean:**

| Metric | Meaning |
| --- | --- |
| Mile Time | Elapsed time from workout start to the first mile, including breaks |
| Unpaused Time | Mile time minus identifiable recorded pauses |
| Swimming Time | Time attributed to swimming pool lengths, excluding identified pauses when the pause history is complete |
| Unpaused Rest / Other | Unpaused time outside recorded swimming lengths; not necessarily all rest |
| Paused Time | Time identified from workout pause/resume events |
| Overall Pace | First-mile elapsed time per 100 meters, including breaks |
| Swimming Pace | Pace calculated from recorded pool-length timing |
| Average Heart Rate | Average of available heart-rate readings during the analyzed interval |
| Estimated Strokes | Stroke count estimated through the first mile, including a proportional partial length when needed |

A **mile means 1,609.344 meters (1,760 yards)**, not 1,500 meters. Because a mile often falls partway through a pool length, the crossing time is estimated. If pause/resume records are incomplete, the program shows a limited breakdown rather than presenting an unsupported exact split. The current swimming tool focuses on **the first mile of pool swims**; it does not yet calculate custom-distance or fastest-mile splits.

## How the calculations work

**Running cadence:** The analyzer finds step-count measurements overlapping the selected interval, prorates measurements crossing its boundaries, and divides estimated steps by the selected interval's duration in minutes. This is an estimate from step-count records, not a direct Apple Watch cadence reading. Missing or overlapping records can affect accuracy.

**Swimming:** The analyzer orders timestamped pool-length distance measurements, adds them until reaching one mile, and estimates the crossing point within the final length. It combines matching stroke-count measurements, heart-rate readings, and workout pause events when available. Swimming time and pause breakdowns depend on the completeness and accuracy of exported measurements.

These results are for personal fitness analysis, not medical use.

## Try running analysis without personal data

The repository includes a fictional Apple Health XML sample for testing the running analyzer:

```bash
python3 src/extract_cadence.py --file examples/synthetic_sample.xml --workout 1 --non-interactive
```

This sample is **not** intended to demonstrate the swimming report. Swimming analysis currently requires an export containing suitable swimming workouts and length records.

## Tests

Run the existing automated running-analyzer tests from the project root:

```bash
python3 -m unittest discover -s tests -v
```

The swimming analyzer has been exercised against sample calculations and real local exports, but a committed swimming-specific test suite is still planned.

## Project structure

```text
apple-health-workout-analyzer/
├── src/
│   ├── extract_cadence.py
│   ├── analyze_swimming.py
│   ├── inspect_swimming.py        # Development diagnostics
│   └── verify_swimming_timing.py  # Development diagnostics
├── tests/
│   └── test_analyzer.py
├── examples/
│   └── synthetic_sample.xml
├── data/                          # Private exports; ignored by Git
├── .gitignore
└── README.md
```

The two swimming diagnostic scripts help inspect exported data during development; **regular users only need `analyze_swimming.py`**. If your checkout does not include the diagnostic scripts, they are not required for analysis.

## Privacy

All analysis runs on your computer. The scripts do not upload health data or require network access. Keep real Apple Health exports in the ignored `data/` directory or outside the repository. Before pushing to GitHub, verify that no private exports are staged:

```bash
git diff --cached --name-only
```
