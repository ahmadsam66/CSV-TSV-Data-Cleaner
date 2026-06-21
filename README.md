# Data Quality Cleaning Pipeline

A production‑grade automated data quality cleaning tool built in Python.  
It ingests messy CSV files, performs a comprehensive set of cleaning and transformation steps, and outputs a cleaned dataset along with a detailed JSON report of all changes made.

---

## Description

This tool is designed to handle real‑world, “dirty” enterprise datasets. It automates the following tasks:

- **Encoding and delimiter detection** – uses `chardet` to detect file encoding and `csv.Sniffer` to guess the delimiter.
- **Robust parsing** – skips malformed lines gracefully.
- **Header sanitisation** – strips whitespace, converts to snake_case, handles duplicates.
- **Data quality metrics** – computes null ratios, whitespace errors, outlier counts, and inferred types per column.
- **Intelligent cleaning**:
  - Replaces null placeholders with `NaN`.
  - Drops columns exceeding a null‑ratio threshold.
  - Imputes numeric columns with median, categorical with mode.
  - Adds quality‑flag columns for columns with moderate null ratios.
  - Removes duplicate rows (optionally using a primary key).
  - Caps outliers using IQR or Z‑score.
  - Standardises string casing (lower, upper, title) based on majority.
  - Performs fuzzy grouping of string values (Levenshtein‑based) to merge similar variants.
  - Validates chronological order between date columns and swaps if inverted.
- **Reporting** – generates a JSON report summarising all transformations and modifications.

---

## Features

- **Full pipeline** – from raw file to cleaned dataset and audit report.
- **Configurable** – many command‑line options to tailor the cleaning strategy.
- **Production ready** – handles large files, logs progress, and reports detailed metrics.
- **No external dependencies beyond standard data science libraries** – uses `pandas`, `numpy`, `chardet`.

---

## Installation

### Prerequisites

- Python 3.6 or higher
- pip

### Required packages

Install the dependencies using pip:

```bash
pip install pandas numpy chardet
