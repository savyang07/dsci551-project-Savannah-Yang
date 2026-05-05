DSCI 551 Final Project: Fitness Data Analyzer
Name: Savannah Yang
Database System: DuckDB

This project simulates DuckDB's internal query execution mechanisms in plain Python. The goal is to show how DuckDB's two core design choices, columnar storage and vectorized batch execution, improve performance on analytical queries compared to row-oriented databases like MySQL.

The application analyzes a synthetic fitness dataset and runs two features:

Feature 1: Weekly calorie summary per user
Feature 2: Workout type breakdown with session counts and average calories


Repository Contents
/

├── final_fitness_analyzer.py   # Main script (all simulation logic)

├── workouts_2000.csv           # Synthetic fitness dataset (2000 records)

└── README.md                   # This file


Dataset:
workouts_2000.csv is a synthetic dataset with 2000 records across 5 users (alice, bob, carol, david, emma) and 5 columns: user, workout_type, date, calories, duration.


Environment Setup:
Python version: 3.7 or higher

Dependencies: None. The script uses only Python built-in modules: csv, os, collections, and datetime. No pip install required.


Configuration:
No configuration file is needed. The only requirement is that final_fitness_analyzer.py and workouts_2000.csv are in the same folder. The script resolves the CSV path automatically relative to its own location, so it works regardless of what directory you run it from.


How to Run:
Clone the repository:

git clone https://github.com/savyang07/dsci551-project-Savannah-Yang.git

cd dsci551-project-Savannah-Yang

Confirm both files are present in the same folder:

final_fitness_analyzer.py

workouts_2000.csv

Run the script:

python final_fitness_analyzer.py


Expected Output:
Running the script produces four sections. The beginning of each section should look like this:

```
============================================================
DSCI 551 Fitness Data Analyzer (DuckDB simulation)
============================================================

  Load workouts.csv into columnar store.
  Loaded 2000 workout records.
  Columns stored  : user, workout_type, date, calories, duration
  Storage layout  : one Python list per column (NOT row-by-row)

============================================================
DuckDB Query Traces
============================================================
  DuckDB 7-Stage Pipeline Trace: Feature 1
  ...

============================================================
FEATURE 1: Weekly Calorie Summary (per user)
============================================================
  Columns read: user, date, calories
  Batch size  : 1024  (DataChunk equivalent)
  
  User         Week           Calories
  ------------ ------------ ----------
  alice        2025-W01           2089
  alice        2025-W02           ...
  ...

============================================================
FEATURE 2: Workout Type Breakdown (Vectorized Batch Execution)
============================================================
  Columns read    : workout_type, calories
  Columns skipped : user, date, duration

  Workout Type              Sessions    Avg Calories
  -------------------- ---------- --------------
  Swimming                      ...            ...
  Running                       ...            ...
  ...

============================================================
Done.
============================================================
```
The exact calorie numbers will match the values in workouts_2000.csv. Feature 2 results are sorted by average calories descending.


How to Reproduce Results
The dataset is fully synthetic and deterministic. Running python final_fitness_analyzer.py on the included workouts_2000.csv will always produce the same output. No random seed or external setup is needed.

