# Data Quality Cleaning Pipeline

**Automated, production‑ready data cleaning for messy CSV files**  
Detect file structure, fix missing values, outliers, duplicates, text inconsistencies, and date logic errors – all with a single command and a full audit trail.

---

## Description

This Python tool implements a **complete, end‑to‑end data cleaning pipeline** for enterprise‑grade CSV datasets. It is designed to handle the real‑world messiness you find in raw data: inconsistent encodings, malformed lines, varied null representations, mixed casing, duplicate records, extreme outliers, and even chronological impossibilities.

The pipeline operates in six distinct phases:

1. **Pre‑Parse** – Automatically detects file encoding (using `chardet`) and delimiter (using `csv.Sniffer`). Checks delimiter consistency and warns about potential issues.
2. **Parse** – Loads the data robustly, skipping malformed lines without crashing.
3. **Header Sanitisation** – Cleans column names (whitespace, snake_case, duplicate handling).
4. **Metrics Computation** – Calculates null ratios, whitespace errors, outlier counts, and data types per column.
5. **Cleaning Logic** – Applies configurable transformations:
   - Replace custom null placeholders with `NaN`.
   - Drop columns with excessive nulls, impute others (median for numeric, mode for categorical).
   - Add quality‑flag columns for moderate null rates.
   - Remove duplicates (optionally using a primary key).
   - Cap outliers using IQR or Z‑score.
   - Standardise string casing and merge similar variants via fuzzy matching.
   - Validate and correct date order (e.g., ensure end date ≥ start date).
6. **Output** – Saves a cleaned CSV and a detailed JSON report with every transformation logged.

All steps are fully configurable via command‑line arguments, making the tool adaptable to any dataset and business rule.

---

## Features

- **Zero‑configuration start** – Just point to a CSV; the tool auto‑detects encoding, delimiter, and applies sensible defaults.
- **Complete transparency** – Every change (dropped columns, imputed values, capped outliers, merged strings, etc.) is recorded in a human‑readable JSON report.
- **Highly configurable** – Override thresholds, outlier methods, null placeholders, date formats, primary keys, and more.
- **Handles large datasets** – Built on `pandas` and `numpy`, efficient for millions of rows.
- **No external dependencies** – Only requires `pandas`, `numpy`, and `chardet` – all standard in the data science ecosystem.
- **Production‑ready** – Logging, error handling, and clear exit codes make it suitable for automated pipelines.

---

## Installation

### Prerequisites

- Python 3.6 or higher
- `pip` (Python package installer)

### Required Packages

Install the dependencies with:

```bash
pip install pandas numpy chardet


Or use a `requirements.txt`:

```
pandas>=1.3.0
numpy>=1.21.0
chardet>=4.0.0
```

Then:

```bash
pip install -r requirements.txt
```

The script is self‑contained – no further setup needed.

---

## Usage

```bash
python cleaner.py --input-file <path> [options]
```

### Command‑line arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--input-file` | str | **required** | Path to the input CSV file. |
| `--output-file` | str | `{input}_cleaned.csv` | Path for the cleaned output CSV. |
| `--delimiter` | str | auto‑detected | Explicit delimiter (e.g. `,`, `\t`, `;`). |
| `--encoding` | str | auto‑detected | Explicit encoding (e.g. `utf-8`, `latin-1`). |
| `--primary-key` | str | None | Comma‑separated column names used for deduplication. |
| `--datetime-format` | str | None | Explicit format string for date columns (e.g. `%Y-%m-%d`). |
| `--null-placeholders` | list | `NULL NA NaN - 999` | List of strings to treat as missing values. |
| `--drop-threshold` | float | 0.70 | Columns with null ratio > this are dropped. |
| `--impute-threshold` | float | 0.40 | Columns with null ratio ≤ this are imputed; between this and `drop-threshold` gets a quality flag. |
| `--outlier-method` | `iqr` or `zscore` | `iqr` | Method for outlier detection. |
| `--outlier-std` | float | 3.0 | Z‑score threshold when using `zscore`. |
| `--log-level` | `DEBUG`, `INFO`, `WARNING` | `INFO` | Verbosity of console logs. |

---

## Examples

All examples use the provided `dirty_enterprise_dataset.csv` file.

---

### Example 1 – Basic cleaning (auto‑detect everything)

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv
```

- **What it does**: Detects encoding and delimiter automatically, then runs the entire cleaning pipeline with default settings.
- **Output**: `dirty_enterprise_dataset_cleaned.csv` and `dirty_enterprise_dataset_cleaned_report.json`.
- **Use case**: Quick, first‑pass cleaning to get a baseline clean dataset and understand the quality issues.

---

### Example 2 – Specify output file

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --output-file enterprise_clean.csv
```

- **What it does**: Same as Example 1 but writes the cleaned data to `enterprise_clean.csv` and the report to `enterprise_clean_report.json`.
- **Output**: Custom‑named files.
- **Use case**: When you want to control file names for integration into a larger workflow.

---

### Example 3 – Set explicit delimiter and encoding

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --delimiter ',' --encoding 'utf-8'
```

- **What it does**: Overrides automatic detection; forces comma delimiter and UTF‑8 encoding.
- **Output**: Cleaned files as usual.
- **Use case**: When you know the exact file format and want to avoid detection errors or speed up parsing.

---

### Example 4 – Use a primary key for deduplication

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --primary-key "Transaction ID,Customer ID"
```

- **What it does**: Removes duplicate rows based on the combination of `Transaction ID` and `Customer ID`. Keeps the row with the most non‑null values for each key combination.
- **Output**: Deduplicated dataset and report indicating number of rows dropped.
- **Use case**: When you have a natural key and want to ensure one record per entity.

---

### Example 5 – Custom null placeholders

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv \
  --null-placeholders "NULL" "NA" "NaN" "-" "999" "Unknown" "N/A"
```

- **What it does**: Treats these specific strings as missing values. They are replaced with `NaN` and then subject to imputation or column dropping based on thresholds.
- **Output**: The cleaned dataset will have these values converted to proper missing values; report will reflect cells modified.
- **Use case**: When your dataset uses non‑standard codes for missing data (e.g., `"Unknown"` in categorical columns).

---

### Example 6 – Adjust drop and impute thresholds

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv \
  --drop-threshold 0.6 \
  --impute-threshold 0.3
```

- **What it does**: Drops any column with >60% nulls. Imputes columns with ≤30% nulls (median for numeric, mode for categorical). For columns with 30‑60% nulls, it adds a `_quality_flag` column indicating which rows were missing.
- **Output**: Dataset with columns dropped/imputed and additional flag columns; report details the decisions.
- **Use case**: When you want to be more aggressive about keeping columns (lower drop threshold) or more conservative about imputation (higher impute threshold).

---

### Example 7 – Use Z‑score outlier detection with custom standard deviation

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv \
  --outlier-method zscore \
  --outlier-std 2.5
```

- **What it does**: Detects outliers using Z‑score (values beyond 2.5 standard deviations from the mean). Outliers are capped to the upper/lower bound.
- **Output**: Outlier values clipped to the threshold; report shows how many outliers were capped per column.
- **Use case**: When your data distribution is approximately normal and you prefer Z‑score over IQR, or you want a stricter/looser outlier definition.

---

### Example 8 – Specify datetime format for chronological validation

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv \
  --datetime-format "%Y-%m-%d"
```

- **What it does**: Uses the given format to parse columns containing `"date"` or `"time"` in their names. It then checks for pairs of start/end date columns (e.g., `Order Open Date` and `Order Close Date`) and swaps values if the end date is earlier than the start date.
- **Output**: Dates are properly parsed and inverted chronologies are corrected. The report will note how many records were swapped.
- **Use case**: When your dataset has date fields in a known format and you need to ensure temporal consistency.

---

### Example 9 – Increase logging verbosity

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --log-level DEBUG
```

- **What it does**: Prints detailed debug messages during each phase (encoding detection, delimiter sniffing, per‑column metrics, cleaning steps, etc.).
- **Output**: No change to output files, but console output is much more detailed.
- **Use case**: Debugging unexpected behaviour, understanding why certain columns were dropped/imputed, or verifying the pipeline steps.

---

### Example 10 – Full customised pipeline

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv \
  --output-file final_clean.csv \
  --primary-key "Transaction ID" \
  --drop-threshold 0.65 \
  --impute-threshold 0.35 \
  --outlier-method iqr \
  --null-placeholders "NULL" "NA" "-" "999" \
  --datetime-format "%Y-%m-%d" \
  --log-level INFO
```

- **What it does**: Combines multiple customisations:
  - Defines output files.
  - Uses `Transaction ID` as primary key for deduplication.
  - Drops columns with >65% nulls, imputes ≤35% nulls, adds flags for the middle range.
  - Uses IQR for outlier capping.
  - Defines custom null placeholders.
  - Parses dates with `%Y-%m-%d` and corrects chronology.
  - Logs at INFO level.
- **Output**: `final_clean.csv` and `final_clean_report.json` with all these rules applied.
- **Use case**: A comprehensive, production‑ready cleaning job tailored to your specific data quality rules.

---

## What the Tool Does – Detailed Cleaning Logic

The cleaning pipeline consists of six phases:

1. **Pre‑Parse**  
   - Reads the first 100KB to detect encoding using `chardet` and strips BOM if present.  
   - Sniffs the delimiter from the first 50 lines using `csv.Sniffer`.  
   - Checks delimiter consistency and warns if variance >5%.

2. **Parse**  
   - Loads the CSV with `pandas.read_csv` using the detected encoding and delimiter.  
   - Skips malformed lines (logged and counted).

3. **Header Sanitisation**  
   - Strips leading/trailing whitespace.  
   - Converts to snake_case (e.g., `"Transaction ID"` → `transaction_id`).  
   - Handles duplicate headers by appending `_1`, `_2`, etc.

4. **Compute Metrics**  
   - For each column: null ratio, number of whitespace errors, outlier count (based on chosen method), and inferred data type.

5. **Cleaning Logic** (the core transformations)  
   - Replace all user‑defined null placeholders with `NaN`.  
   - **Drop columns** whose null ratio exceeds `--drop-threshold`.  
   - **Impute** columns with null ratio ≤ `--impute-threshold` (numeric → median; categorical → mode).  
   - **Add quality flags** for columns with null ratio between the two thresholds (indicates rows with missing values).  
   - **Deduplicate** – either using a primary key (keeping the row with most non‑nulls) or full row deduplication (keeping first).  
   - **Outlier capping** – using IQR (1.5×IQR) or Z‑score (user‑defined std). Values outside bounds are clipped to the bounds.  
   - **String standardisation** – trim whitespace, convert to `lower`/`upper`/`title` based on majority case, and perform fuzzy grouping (using `difflib.get_close_matches` with cutoff 0.85) to merge near‑identical variants (e.g., `"Smart Watch V2"` and `"Smart Watch v2"`).  
   - **Chronological validation** – automatically finds date columns (containing `"date"` or `"time"`). If both start and end date columns exist (based on names like `start`/`end`, `open`/`close`, `begin`/`stop`), it swaps values where the end date is earlier than the start date.

6. **Output**  
   - Saves the cleaned DataFrame to a CSV (using the same delimiter).  
   - Writes a JSON report containing: original shape, final shape, number of malformed lines skipped, rows dropped (duplicates), columns dropped, imputation details, outlier caps, fuzzy groupings, and total cells modified.  
   - Prints an executive summary to the console.

---

## Application

This tool is ideal for:

- **Data engineering** – as a reliable pre‑processing step in ETL pipelines.
- **Data science** – to quickly produce a clean, consistent dataset for modelling.
- **Data quality audits** – to assess and document the extent of issues in a dataset.
- **Operational reporting** – ensures dashboards receive cleansed data.
By automating these common data cleaning tasks, the tool saves hours of manual work and provides complete transparency into what changes were made.


---

📊 Pipeline Architecture Blueprint
[ Messy Input File ]  --->  (CSV, TSV, or corrupted text stream)
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 1: PRE-PARSE ANALYSIS                           │
│  ├── Codec Sniffing (chardet) -> [utf-8 / latin-1]     │
│  └── Layout Inferences (csv.Sniffer) -> [ , | \t ]     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 2: ROBUST STREAM PARSING                        │
│  └── Isolated Line Filter (on_bad_lines)               │
└───────────────────────┬────────────────────────────────┘
                        │  Dropped Malformed Lines Logged
                        ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 3: HEADER SANITIZATION                          │
│  └── Regex Trimming -> [ clean_snake_case_labels ]     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 4: METRICS PROFILING AUDIT                      │
│  └── Telemetry Scan -> Computes Baseline Null Ratios   │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 5: AUTOMATED TRANSFORMATION ENGINE              │
│  ├── Column Pruning (Drop Threshold Evaluation)       │
│  ├── Missing Value Imputation (Median / Mode)          │
│  ├── Duplication Scoring (Context-Key Constraints)     │
│  ├── Outlier Winsorization (IQR / Z-Score Clipping)    │
│  └── Fuzzy Text Normalization (Levenshtein 85% Match)  │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 6: OPERATIONAL ARTIFACT GENERATION              │
│  ├── Pristine Output Flat Table (.csv)                 │
│  └── Comprehensive JSON Diagnostic Ledger              │
└────────────────────────────────────────────────────────┘
           │
           ├──> [ master_clean_dataset.csv ]
           └──> [ master_clean_dataset_report.json ]

## License

This tool is open‑source and provided as‑is. Feel free to modify and use it in your own projects.
```
