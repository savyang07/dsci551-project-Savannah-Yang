Fitness Data Analyzer — DSCI 551 Final Project
Name: Savannah Yang
Database System: DuckDB

Project Overview
This project simulates DuckDB's internal query execution mechanisms using plain Python. The goal is to demonstrate how DuckDB's two core design choices,columnar storage and vectorized batch execution, improve performance on analytical queries compared to row-oriented databases like MySQL.
The application analyzes a synthetic fitness dataset and runs two features:

Feature 1: Weekly calorie summary per user
Feature 2: Workout type breakdown with session counts and average calories

Repository Contents
/
├── fitness_analyzer.py   # Main script (all simulation logic)
├── workouts.csv          # Synthetic fitness dataset (274 records)
└── README.md             # This file

Dataset
workouts.csv is a synthetic dataset with 274 records across 3 users (alice, bob, carol) and 5 columns

Setup Instructions

Python 3.7 or higher
No external libraries required (only built-in modules: csv, os, collections, datetime)

Steps

Clone the repository:

bash   git clone <your-repo-url>
   cd <your-repo-folder>

Confirm both files are in the same folder:

   fitness_analyzer.py
   workouts.csv

Run the script:

bash   python fitness_analyzer.py

How to Run
From the terminal, navigate to the folder containing the files and run:
bash python fitness_analyzer.py