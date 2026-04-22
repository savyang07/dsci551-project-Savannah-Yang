"""
fitness_analyzer.py
DSCI 551 Fitness Data Analyzer Simulating DuckDB
Name: Savannah Yang

This script mimics what DuckDB does internally.
It shows columnar storage and vectorized (batch) execution in plain Python.

"""

import csv      
import os       
from collections import defaultdict  # built-in: handy dict that auto-creates missing keys


# SECTION 1 — COLUMNAR STORAGE ENGINE 
# As described in the Proposal: "the system will load workout data from a CSV file and store it
# internally using a column-oriented structure."
# "each column is stored as a separate list."
# Mapping: "Aggregation → columnar vs row-based execution"
#
# In a real row-oriented database (MySQL), data is stored:
#   Row 0: [alice, Running, 2025-01-03, 420, 35]
#   Row 1: [alice, Cycling, 2025-01-07, 310, 45]
#   ...
# Every query reads ALL columns.
#
# DuckDB stores data like this instead (one list per column):
#   user_col     = ["alice", "alice", ...]
#   workout_col  = ["Running", "Cycling", ...]
#   date_col     = ["2025-01-03", "2025-01-07", ...]
#   calories_col = [420, 310, ...]
#   duration_col = [35, 45, ...]
#
# A query that only needs workout_type and calories can ignore the other three.

class ColumnarStore:
   
    def __init__(self):
        self.user         = []   
        self.workout_type = []   
        self.date         = []   
        self.calories     = []  
        self.duration     = []   

    def load_from_csv(self, filepath):
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.user.append(row["user"])
                self.workout_type.append(row["workout_type"])
                self.date.append(row["date"])
                self.calories.append(int(row["calories"])) 
                self.duration.append(int(row["duration"]))  

    def total_rows(self):
        return len(self.calories)

    def get_column(self, name):
        """
        Return a column by name.
        only the needed columns enter the loop
        Column Pruning in DuckDB (Stage 4, Optimizer):
        the query optimizer strips out columns the query does not reference
        before the data even reaches the execution engine.
        """
        columns = {
            "user":         self.user,
            "workout_type": self.workout_type,
            "date":         self.date,
            "calories":     self.calories,
            "duration":     self.duration,
        }
        if name not in columns:
            raise ValueError(f"Unknown column: '{name}'. Available: {list(columns.keys())}")
        return columns[name]

# SECTION 2 — VECTORIZED BATCH EXECUTION ENGINE
# As described in the Proposal: "DuckDB is particularly effective for aggregation queries 
# like GROUP BY, SUM, and AVG because it uses columnar storage and a vectorized query execution design."
# As described in Midterm Report: "DuckDB further partitions columns into fixed-size 'vectors'.
# A vector represents an array of values of a single data type."
# "100,000 rows → ~98 batch operations instead of 100,000 individual function calls."
# "Execution occurs in cache-friendly batches (e.g., 1024 values of
# a specific column such as region & sales)"
#
# Instead of processing one value at a time, DuckDB groups values into
# DataChunks (we call ours a "batch") of BATCH_SIZE values and runs the
# aggregation operator over the whole chunk at once.
# This keeps the data in the CPU's L1/L2 cache and avoids per-row overhead.

BATCH_SIZE = 1024   # batch size is chosen to fit in the L1/L2 cache


def batch_sum(column_data):
    """
    Sum all values in a column using BATCH_SIZE-sized slices.

    Mimics DuckDB's vectorized SUM() operator pushing DataChunks
    through the execution pipeline.
    """
    total = 0
    total_rows = len(column_data)

    # Slice the column into chunks of BATCH_SIZE and sum each chunk.
    start = 0
    while start < total_rows:
        end = min(start + BATCH_SIZE, total_rows)  
        batch = column_data[start:end]             
        total += sum(batch)
        start = end

    return total


def batch_group_by_avg(group_column, value_column):
    """
    Compute AVG(value_column) GROUP BY group_column using batch processing.
    Mimics DuckDB vectorized GROUP BY + AVG() in the execution engine.

    Feature 2 runs SELECT workout_type, AVG(calories) on a 5-column
    table. The optimizer sees only two columns referenced and pushes column
    selection down to the scan.

    """
    group_sum   = defaultdict(int)  
    group_count = defaultdict(int)   

    total_rows = len(group_column)
    start = 0

    while start < total_rows:
        end = min(start + BATCH_SIZE, total_rows)

        batch_groups = group_column[start:end]
        batch_values = value_column[start:end]

        for g, v in zip(batch_groups, batch_values):
            group_sum[g]   += v
            group_count[g] += 1

        start = end

    result = {}
    for key in group_sum:
        result[key] = {
            "count": group_count[key],
            "avg":   round(group_sum[key] / group_count[key], 1),
        }

    return result


def batch_group_by_sum(group_column, value_column):
    """
    Compute SUM(value_column) GROUP BY group_column using batch processing.

    Used by Feature 1 (weekly calorie summary per user).
    """
    group_sum = defaultdict(int)
    total_rows = len(group_column)
    start = 0

    while start < total_rows:
        end = min(start + BATCH_SIZE, total_rows)
        batch_groups = group_column[start:end]
        batch_values = value_column[start:end]

        for g, v in zip(batch_groups, batch_values):
            group_sum[g] += v

        start = end

    return group_sum

def date_to_week(date_str):
    """
    Convert "2025-01-03" → "2025-W01".
    %W starts weeks on Monday.
    We use Python's isocalendar() which always follows ISO 8601 (week 1 is
    the first week that contains a Thursday). This avoids the "Week 0" issue
    mentioned in the Midterm Report.
    """
    from datetime import date
    year, month, day = map(int, date_str.split("-"))
    d = date(year, month, day)
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


# SECTION 3 — APPLICATION FEATURES

def feature1_weekly_calorie_summary(store):
    """
    FEATURE 1 — Weekly Calorie Summary (per user)

    "Edit Feature 1 to do a Weekly Calorie Summary for each user name,not across all users"
    Mapping: "Aggregation → columnar vs row-based execution"


    Groups workout records by (user, ISO week) and sums calories for each group.

    DuckDB internal operation:
        1. Column pruning (Stage 4, Optimizer): only 'user', 'date', and 'calories'
           are loaded — 'workout_type' and 'duration' are never read.
        2. Vectorized SUM (Stage 7, Execution Engine): values are aggregated in
           DataChunks of BATCH_SIZE, keeping data in the CPU cache.
        3. Hash-aggregate operator: results are collected into a hash table keyed
           on (user, week) before the final sort.

    Advantage:
        MySQL reads all 5 columns * 274 rows for this query. Our simulation reads
        only 3 columns, matching DuckDB's I/O cost that scales with columns used,
        not columns stored.
    """

    # Column pruning: pull only the 3 needed columns
    user_col     = store.get_column("user")     
    date_col     = store.get_column("date")      
    calories_col = store.get_column("calories")  

    group_keys = [
        f"{user_col[i]}|{date_to_week(date_col[i])}"
        for i in range(len(user_col))
    ]

    result = batch_group_by_sum(group_keys, calories_col)

    sorted_result = sorted(result.items(), key=lambda x: (x[0].split("|")[0], x[0].split("|")[1]))

    print()
    print("=" * 60)
    print("FEATURE 1: Weekly Calorie Summary (per user)")
    print("=" * 60)
    print(f"  Columns read: user, date, calories")
    print(f"  Batch size  : {BATCH_SIZE}  (DataChunk equivalent)")
    print()
    print(f"  {'User':<12} {'Week':<12} {'Calories':>10}")
    print(f"  {'-'*12} {'-'*12} {'-'*10}")

    current_user = None
    for key, total in sorted_result:
        user, week = key.split("|")
        if user != current_user:
            if current_user is not None:
                print()   
            current_user = user
        print(f"  {user:<12} {week:<12} {total:>10}")


def feature2_workout_type_breakdown(store):
    """
    FEATURE 2 — Workout Type Breakdown (Vectorized Batch Execution)
 
    Groups workouts by type, returns session count and average calories per type.
    This feature makes DuckDB's vectorized batch execution visible: with 2000+
    rows, the data is split across multiple DataChunks and processed batch by batch.
 
    DuckDB internal operation:
        1. Column pruning (Stage 4, Optimizer): only 'workout_type' and 'calories'
           are scanned. user, date, and duration storage blocks are skipped entirely.
        2. Vectorized AVG (Stage 7, Execution Engine): accumulates SUM and COUNT
           in DataChunk batches of BATCH_SIZE, then divides at the end.
           No per-row function call overhead.
        3. Hash-aggregate operator: each batch's results merge into a running
           hash table keyed on workout_type.
        4. Sort operator: final result ordered by avg descending.
 
    Advantage:
        With 5 columns, MySQL reads 5x as much data per row.
        DuckDB (and this simulation) reads 2/5 of the data — only the
        two columns the query actually needs.
    """
 
    # Column pruning: pull only the 2 needed columns
    workout_col  = store.get_column("workout_type")
    calories_col = store.get_column("calories")
 
    print()
    print("=" * 60)
    print("FEATURE 2: Workout Type Breakdown (Vectorized Batch Execution)")
    print("=" * 60)
    print(f"  Columns read    : workout_type, calories")
    print(f"  Columns skipped : user, date, duration")
    print()
 
    result = batch_group_by_avg(workout_col, calories_col)
 
    sorted_result = sorted(result.items(), key=lambda x: x[1]["avg"], reverse=True)
 
    print()
    print(f"  {'Workout Type':<20} {'Sessions':>10} {'Avg Calories':>14}")
    print(f"  {'-'*20} {'-'*10} {'-'*14}")
    for workout, stats in sorted_result:
        print(f"  {workout:<20} {stats['count']:>10} {stats['avg']:>14.1f}")
 
 
# SECTION 4 — QUERY PIPELINE TRACE  (7-stage DuckDB pipeline)
 
def print_pipeline_trace(query_label, sql, columns_pruned_away, columns_used):
    """
    Based on "every SQL query passes through seven distinct stages before
    producing a result: Parser, Binder, Logical Planner, Optimizer,
    Column Binding Resolver, Physical Planner, Execution Engine."
    """
    print()
    print(f"  DuckDB 7-Stage Pipeline Trace: {query_label}")
    print(f"  SQL (conceptual): {sql}")
    print()
    stages = [
        ("1. Parser",                 "Tokenizes SQL into an abstract syntax tree. No catalog lookups yet."),
        ("2. Binder",                 f"Resolves column names → confirms {columns_used} exist in 'workouts'."),
        ("3. Logical Planner",        "Builds logical plan: Scan → Filter → Aggregate → Sort."),
        ("4. Optimizer",              f"Column pruning: removes {columns_pruned_away} from the scan. "
                                       "Only loads columns actually referenced."),
        ("5. Column Binding Resolver", "Replaces column names with integer indices for the execution engine."),
        ("6. Physical Planner",        "Chooses physical operators: ColumnScan → HashAggregate → Sort."),
        ("7. Execution Engine",        f"Pushes DataChunks of {BATCH_SIZE} values through the operator tree."),
    ]
    for stage, desc in stages:
        print(f"    {stage:<32} {desc}")
 
 
def main():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()
    csv_path = os.path.join(script_dir, "workouts_2000.csv")
 
    print()
    print("=" * 60)
    print("DSCI 551 Fitness Data Analyzer (DuckDB simulation)")
    print("=" * 60)
    print()
    print("  Load workouts.csv into columnar store.")
 
    store = ColumnarStore()
    store.load_from_csv(csv_path)
 
    print(f"  Loaded {store.total_rows()} workout records.")
    print(f"  Columns stored  : user, workout_type, date, calories, duration")
    print(f"  Storage layout  : one Python list per column (NOT row-by-row)")
 
    print()
    print("=" * 60)
    print("DuckDB Query Traces")
    print("=" * 60)
 
    print_pipeline_trace(
        query_label         = "Feature 1",
        sql                 = "SELECT user, strftime(date,'%Y-W%W'), SUM(calories) "
                              "FROM workouts GROUP BY user, week ORDER BY user, week",
        columns_pruned_away = "workout_type, duration",
        columns_used        = "user, date, calories",
    )
 
    print_pipeline_trace(
        query_label         = "Feature 2",
        sql                 = "SELECT workout_type, COUNT(*), AVG(calories) "
                              "FROM workouts GROUP BY workout_type ORDER BY avg DESC",
        columns_pruned_away = "user, date, duration",
        columns_used        = "workout_type, calories",
    )
 
    feature1_weekly_calorie_summary(store)
 
    feature2_workout_type_breakdown(store)
 
    print()
    print("=" * 60)
    print("Done.")
    print("=" * 60)
    print()
 
 
if __name__ == "__main__":
    main()
 