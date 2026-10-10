# Apple Health Workout Analyzer

A privacy-first Python command-line tool for estimating **running cadence (steps per minute)** from an Apple Health XML export. Analyze an entire running workout or a selected time interval.

The analysis runs locally. No account, API key, external service, or third-party Python package is required.

## Features

- Finds running workouts in an Apple Health export and lists them by date and time.
- Interactive selection of an entire workout or a custom interval.
- Estimates steps within the chosen interval, including prorating step-count records that cross its boundaries.
- Displays one estimated average cadence in steps per minute (SPM).
- Supports command-line arguments for repeatable analysis.
- Processes large XML exports incrementally rather than loading the entire file into memory.

## Requirements

- Python 3.9 or newer
- An Apple Health export containing running workouts and step-count records

## Getting started

1. Download or clone this repository.
2. Export your health data from the Health app on your iPhone: tap your profile picture, then **Export All Health Data**. Unzip the export locally.
3. Place `export.xml` at `data/export.xml` inside the project folder. Create the `data` folder if needed. **Never commit your personal export.**
4. From the repository root, run:

   ```bash
   python3 src/extract_cadence.py
   ```

5. Select a running workout, then enter **1** for the entire workout or **2** for a specific section. Section offsets are measured from the beginning of the workout, for example `00:15` to `08:15`.

You can also point to an export elsewhere on your computer:

```bash
python3 src/extract_cadence.py --file /path/to/export.xml
```

## Command-line examples

List workouts:

```bash
python3 src/extract_cadence.py --list-workouts
```

Analyze a whole workout without prompts:

```bash
python3 src/extract_cadence.py --workout 1 --non-interactive
```

Analyze a section without prompts:

```bash
python3 src/extract_cadence.py --workout 1 --start 00:15 --end 08:15 --non-interactive
```

For exports with ambiguous step-count sources, use `--source "EXACT SOURCE NAME"` to select one source rather than combining data from multiple devices.

Run `python3 src/extract_cadence.py --help` for all options.

## Example output

*Illustrative values only; not taken from a real person's health data.*

```text
=== RUNNING ANALYSIS ===
Workout Duration: 10:00
Average Cadence: 180.00 SPM
Estimated Steps: 1,800

Analysis Complete!
```

## How cadence is estimated

The analyzer identifies exported step-count records overlapping the selected time interval. When a record crosses the interval boundary, its steps are prorated according to the overlapping duration. It then calculates:

```text
Estimated average cadence (SPM) = estimated steps / interval duration in minutes
```

**Important limitations:** This is an estimate based on exported step counts, not a direct Apple Watch running-cadence sensor measurement. It may differ from the Apple Fitness app. If step-count records are missing for part of the interval, the estimate can be low because the calculation still uses the full selected duration. Records from multiple devices or duplicate/overlapping records may also affect accuracy. Results are intended for personal fitness exploration, not medical use.

## Privacy

Apple Health exports may contain sensitive personal information. This tool processes files on your own computer and does not send data over the network. Keep real exports in `data/` or outside the repository, and verify they are excluded before publishing. Do not include screenshots of personal workout details or actual exports in Git commits.

## Tests

If the repository includes `tests/test_analyzer.py`, run the tests from the project root:

```bash
python3 -m unittest discover -s tests -v
```

## Project structure

```text
apple-health-workout-analyzer/
├── src/
│   └── extract_cadence.py
├── tests/
│   └── test_analyzer.py
├── examples/
│   └── synthetic_sample.xml
├── data/                  # Local exports; do not commit
├── .gitignore
└── README.md
```

The example and test files are optional for running the analyzer. If you include the synthetic XML example in the public repository, make sure your `.gitignore` allows that specific file while continuing to ignore personal exports.
