```markdown
#Data Quality Cleaning Pipeline

A production‑grade automated data quality cleaning tool built in Python.  
It ingests messy CSV files, performs a comprehensive set of cleaning and transformation steps, and outputs a cleaned dataset along with a detailed JSON report of all changes made.

---

##Description

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
```

Alternatively, create a `requirements.txt`:

```
pandas>=1.3.0
numpy>=1.21.0
chardet>=4.0.0
```

Then run:

```bash
pip install -r requirements.txt
```

No additional setup is required – the script is self‑contained.

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

## Examples (using `dirty_enterprise_dataset.csv`)

Below are 10 example invocations that demonstrate various features of the tool.

### 1. Basic cleaning (auto‑detect everything)

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv
```

- Detects encoding, delimiter, parses file, performs all default cleaning steps.
- Outputs `dirty_enterprise_dataset_cleaned.csv` and `dirty_enterprise_dataset_cleaned_report.json`.

---

### 2. Specify output file

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --output-file enterprise_clean.csv
```

- Writes cleaned data to `enterprise_clean.csv` and report to `enterprise_clean_report.json`.

---

### 3. Set explicit delimiter and encoding

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --delimiter ',' --encoding 'utf-8'
```

- Overrides automatic detection.

---

### 4. Use a primary key for deduplication

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --primary-key "Transaction ID,Customer ID"
```

- Removes duplicate rows based on the combination of `Transaction ID` and `Customer ID`, keeping the row with most non‑null values.

---

### 5. Custom null placeholders

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --null-placeholders "NULL" "NA" "NaN" "-" "999" "Unknown"
```

- Treats these strings as missing values; they will be replaced by `NaN` and later imputed or handled.

---

### 6. Adjust drop and impute thresholds

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --drop-threshold 0.6 --impute-threshold 0.3
```

- Drops columns with >60% nulls; imputes columns with ≤30% nulls; adds flag columns for columns with 30‑60% nulls.

---

### 7. Use Z‑score outlier detection with custom standard deviation

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --outlier-method zscore --outlier-std 2.5
```

- Flags values beyond 2.5 standard deviations from the mean as outliers and caps them.

---

### 8. Specify datetime format for chronological validation

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --datetime-format "%Y-%m-%d"
```

- Enables proper parsing of date columns (e.g., `Order Open Date`, `Order Close Date`) and corrects inverted date ranges.

---

### 9. Increase logging verbosity

```bash
python cleaner.py --input-file dirty_enterprise_dataset.csv --log-level DEBUG
```

- Prints detailed debug information during each phase, useful for troubleshooting.

---

### 10. Combine multiple options

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

- Runs a fully customised cleaning pipeline with deduplication, custom thresholds, outlier capping, and date validation.

---

## What the Tool Does – Detailed Cleaning Logic

1. **Pre‑Parse**  
   - Reads the first 100KB to detect encoding (using `chardet`) and removes BOM if present.  
   - Sniffs the delimiter from the first 50 lines.

2. **Parse**  
   - Loads the CSV with `pandas.read_csv`; skips malformed lines (logged and counted).

3. **Header Sanitisation**  
   - Strips whitespace, converts to snake_case, and ensures uniqueness.

4. **Compute Metrics**  
   - For each column: null ratio, whitespace errors, outlier count, data type.

5. **Cleaning Logic**  
   - Replace all user‑defined null placeholders with `NaN`.  
   - **Drop columns** whose null ratio exceeds `--drop-threshold`.  
   - **Impute** columns with null ratio ≤ `--impute-threshold` (numeric → median; categorical → mode).  
   - **Quality flags** added for columns with null ratio between thresholds.  
   - **Deduplication** – either using a primary key (if given) or full row deduplication.  
   - **Outlier capping** – using IQR or Z‑score, values outside bounds are clipped.  
   - **String standardisation** – trim whitespace, convert to `lower`/`upper`/`title` based on majority, and perform fuzzy grouping to merge near‑identical variants.  
   - **Chronological validation** – automatically detects date columns (containing `date` or `time`) and, if both start and end date columns exist, swaps values where the end date is earlier than the start date.

6. **Output**  
   - Saves the cleaned DataFrame to a CSV (same delimiter as input).  
   - Writes a JSON report with details of all transformations (dropped columns, imputations, outlier caps, fuzzy groupings, rows dropped, cells modified, etc.).  
   - Prints an executive summary to the console.

---

## Application

This tool is ideal for:

- **Data engineering teams** – as a pre‑processing step in ETL pipelines to standardise and clean incoming data.
- **Data science projects** – to quickly produce a reliable, clean dataset for analysis or modelling.
- **Data quality audits** – to understand the extent of issues in a dataset and track improvements over time.
- **Operational reporting** – ensures that dashboards and reports are fed with consistent, cleansed data.

It reduces manual data cleaning effort and provides full visibility into what changes were applied, making it transparent and repeatable.

---

## License

This tool is open‑source and provided as‑is. Feel free to modify and use it in your own projects.
```
