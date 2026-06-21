#!/usr/bin/env python3
"""
Production-Grade Automated Data Quality Cleaning Pipeline.
Author: Senior Data Engineer / Python Developer
"""

import argparse
import csv
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import chardet
import numpy as np
import pandas as pd


class DataQualityEngine:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.logger = logging.getLogger("DataQualityEngine")
        self.metrics: Dict[str, Any] = {}
        self.report: Dict[str, Any] = {
            "transformations": {
                "columns_dropped": [],
                "columns_imputed": {},
                "outliers_capped": {},
                "fuzzy_groupings": {},
                "rows_dropped_count": 0,
                "cells_modified_count": 0
            }
        }
        self.cells_modified = 0

    def increment_modified(self, count: int = 1):
        self.cells_modified += count
        self.report["transformations"]["cells_modified_count"] = self.cells_modified

    def run_pipeline(self) -> None:
        self.logger.info(f"Starting cleaning process for '{self.args.input_file}'...")
        
        # Phase 1: Pre-Parse
        encoding, delimiter = self._phase_1_pre_parse()
        
        # Phase 2: Parse
        df, skipped_lines = self._phase_2_parse(encoding, delimiter)
        self.report["original_shape"] = {"rows": df.shape[0], "columns": df.shape[1]}
        self.report["skipped_malformed_lines"] = skipped_lines
        
        if df.empty:
            self.logger.error("DataFrame is empty after parsing. Exiting pipeline.")
            return

        # Phase 3: Header Sanitization
        df = self._phase_3_header_sanitization(df)
        
        # Phase 4: Compute Metrics
        self._phase_4_compute_metrics(df)
        
        # Phase 5: Apply Cleaning Logic
        df = self._phase_5_cleaning_logic(df)
        
        # Phase 6: Generate Outputs
        self._phase_6_generate_outputs(df, delimiter)

    def _phase_1_pre_parse(self) -> Tuple[str, str]:
        self.logger.info("Phase 1: Starting Pre-Parse Analysis.")
        
        # 1. Detect Encoding & Strip BOM via Chardet
        with open(self.args.input_file, "rb") as f:
            raw_data = f.read(100000)  # sample first 100k bytes
            if not raw_data:
                raise ValueError("Input file is empty.")
            
        detected = chardet.detect(raw_data)
        encoding = self.args.encoding or detected["encoding"] or "utf-8"
        
        # Check for BOM signatures and adapt encoding string
        if encoding.lower() in ["utf-8", "ascii"]:
            with open(self.args.input_file, "rb") as f:
                sig = f.read(3)
                if sig == b'\xef\xbb\xbf':
                    encoding = "utf-8-sig"
                    
        self.logger.info(f"Detected/Assigned encoding: '{encoding}'")

        # 2. Delimiter consistency checking
        with open(self.args.input_file, "r", encoding=encoding, errors="replace") as f:
            lines = [f.readline() for _ in range(50)]
            lines = [line for line in lines if line.strip()]

        if self.args.delimiter:
            delimiter = self.args.delimiter
        else:
            try:
                sample_text = "".join(lines)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample_text, delimiters=[",", "\t", ";", "|"])
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ","  # Default fallback
        
        # Calculate Row length consistency
        counts = [line.count(delimiter) for line in lines]
        if counts:
            mean_delims = np.mean(counts)
            variance = np.var(counts) if len(counts) > 1 else 0.0
            inconsistency_rate = (variance / mean_delims) if mean_delims > 0 else 0.0
            self.logger.info(f"Detected delimiter: '{repr(delimiter)}' | Row delimiter variance rate: {inconsistency_rate:.2%}")
            
            if inconsistency_rate > 0.05:
                self.logger.warning("Delimiter inconsistency is > 5%. The schema may be unstable or contain raw unquoted text breaks.")
        
        return encoding, delimiter

    def _phase_2_parse(self, encoding: str, delimiter: str) -> Tuple[pd.DataFrame, int]:
        self.logger.info("Phase 2: Loading data into Pandas DataFrame.")
        
        # Custom bad line handler to log skipped items without crashing
        skipped_lines = 0
        def bad_line_handler(line: List[str]) -> Optional[List[str]]:
            nonlocal skipped_lines
            skipped_lines += 1
            return None # Skips the line cleanly
            
        try:
            df = pd.read_csv(
                self.args.input_file,
                sep=delimiter,
                encoding=encoding,
                on_bad_lines=bad_line_handler,
                engine="python" # python engine supports the callable on_bad_lines logic fully
            )
            self.logger.info(f"Loaded {df.shape[0]} rows, {df.shape[1]} columns. Skipped {skipped_lines} malformed lines.")
            return df, skipped_lines
        except Exception as e:
            self.logger.error(f"Critical failure parsing DataFrame: {str(e)}")
            raise e

    def _phase_3_header_sanitization(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Phase 3: Sanitizing Column Headers.")
        original_headers = list(df.columns)
        sanitized_headers: List[str] = []
        
        stripped_count = 0
        rename_count = 0

        for col in original_headers:
            col_str = str(col).strip()
            if col_str != str(col):
                stripped_count += 1
            
            # Snake_case conversion
            col_str = re.sub(r'[\s\-]+', '_', col_str)
            col_str = re.sub(r'(?<!^)(?=[A-Z])', '_', col_str)
            col_str = re.sub(r'[^a-zA-Z0-9_]', '', col_str).lower()
            col_str = re.sub(r'_+', '_', col_str).strip('_')
            
            if not col_str:
                col_str = "unnamed_column"

            # Handle Duplicates safely
            base_col = col_str
            counter = 1
            while col_str in sanitized_headers:
                col_str = f"{base_col}_{counter}"
                counter += 1
                rename_count += 1
                
            sanitized_headers.append(col_str)

        df.columns = sanitized_headers
        self.logger.info(f"Renamed {rename_count} duplicate headers. Stripped/Formatted {stripped_count} column names.")
        return df

    def _phase_4_compute_metrics(self, df: pd.DataFrame) -> None:
        self.logger.info("Phase 4: Running comprehensive data quality metric analysis.")
        self.metrics["per_column"] = {}
        
        # Clean null placeholders universally to get real baseline metrics
        temp_df = df.copy()
        if self.args.null_placeholders:
            placeholders = self.args.null_placeholders
            temp_df = temp_df.replace(placeholders, np.nan)
            
        total_rows = len(temp_df)
        if total_rows == 0:
            return

        for col in temp_df.columns:
            null_count = temp_df[col].isna().sum()
            null_ratio = float(null_count / total_rows)
            
            # String matching/type checks
            string_series = temp_df[col].astype(str).str.strip()
            whitespace_issues = int((string_series.str.len() != temp_df[col].astype(str).str.len()).sum())
            
            # Infer Data Types / Outlier profiles
            is_numeric = pd.api.types.is_numeric_dtype(temp_df[col])
            outlier_count = 0
            
            if is_numeric and null_count < total_rows:
                clean_series = temp_df[col].dropna()
                if self.args.outlier_method == 'iqr':
                    q1 = clean_series.quantile(0.25)
                    q3 = clean_series.quantile(0.75)
                    iqr = q3 - q1
                    outlier_count = int(((clean_series < (q1 - 1.5 * iqr)) | (clean_series > (q3 + 1.5 * iqr))).sum())
                else: # zscore
                    std = clean_series.std()
                    if std > 0:
                        mean = clean_series.mean()
                        z_scores = (clean_series - mean) / std
                        outlier_count = int((np.abs(z_scores) > self.args.outlier_std).sum())

            self.metrics["per_column"][col] = {
                "null_ratio": null_ratio,
                "whitespace_errors_count": whitespace_issues,
                "outliers_count": outlier_count,
                "inferred_type": str(temp_df[col].dtype)
            }
            
            if null_ratio > self.args.drop_threshold:
                self.logger.info(f"Metric Flag: Column '{col}' presents a null ratio of {null_ratio:.2%} (Exceeds drop threshold).")

    def _phase_5_cleaning_logic(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Phase 5: Executing algorithmic data transformation strategies.")
        
        # 1. Standardize Placeholders to true NaN
        if self.args.null_placeholders:
            for ph in self.args.null_placeholders:
                # Count changes roughly
                matches = (df == ph).sum().sum()
                if matches > 0:
                    df = df.replace(ph, np.nan)
                    self.increment_modified(int(matches))

        # 2. Evaluate drop/impute thresholds per column
        cols_to_drop = []
        for col in list(df.columns):
            metrics = self.metrics["per_column"].get(col, {})
            null_ratio = metrics.get("null_ratio", 0.0)
            
            if null_ratio > self.args.drop_threshold:
                cols_to_drop.append(col)
                self.report["transformations"]["columns_dropped"].append({"column": col, "reason": f"Null ratio ({null_ratio:.2%}) higher than threshold."})
                continue
                
            # Create a flag array if it sits between thresholds
            if self.args.impute_threshold < null_ratio <= self.args.drop_threshold:
                flag_col = f"{col}_quality_flag"
                if flag_col not in df.columns:
                    df[flag_col] = df[col].isna().astype(int)
                    self.increment_modified(int(df[flag_col].sum()))
            
            # Impute below threshold
            elif 0.0 < null_ratio <= self.args.impute_threshold:
                null_mask = df[col].isna()
                null_fill_count = int(null_mask.sum())
                if null_fill_count > 0:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        median_val = df[col].median()
                        df[col] = df[col].fillna(median_val)
                        self.report["transformations"]["columns_imputed"][col] = {"method": "median", "value": float(median_val)}
                    else:
                        mode_res = df[col].mode()
                        mode_val = mode_res.iloc[0] if not mode_res.empty else "Unknown"
                        df[col] = df[col].fillna(mode_val)
                        self.report["transformations"]["columns_imputed"][col] = {"method": "mode", "value": str(mode_val)}
                    self.increment_modified(null_fill_count)

        if cols_to_drop:
            df.drop(columns=cols_to_drop, inplace=True)
            self.logger.info(f"Dropped {len(cols_to_drop)} columns due to excessive empty datasets: {cols_to_drop}")

        # 3. Handle Deduplication via Primary Keys if requested
        original_row_count = len(df)
        if self.args.primary_key:
            pk_cols = [pk.strip() for pk in self.args.primary_key.split(",") if pk.strip() in df.columns]
            if pk_cols:
                # Add columns assessing row completeness to sort valid records to the top
                df["__non_null_count"] = df.notna().sum(axis=1)
                df.sort_values(by=["__non_null_count"], ascending=False, inplace=True)
                df.drop_duplicates(subset=pk_cols, keep="first", inplace=True)
                df.drop(columns=["__non_null_count"], inplace=True)
        else:
            df.drop_duplicates(keep="first", inplace=True)
            
        rows_dropped = original_row_count - len(df)
        self.report["transformations"]["rows_dropped_count"] = rows_dropped

        # 4. Outlier Winsorization / Advanced Capping
        for col in df.select_dtypes(include=[np.number]).columns:
            clean_series = df[col].dropna()
            if clean_series.empty:
                continue
                
            if self.args.outlier_method == 'iqr':
                q1 = clean_series.quantile(0.25)
                q3 = clean_series.quantile(0.75)
                iqr = q3 - q1
                lower_bound, upper_bound = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            else:
                std = clean_series.std()
                mean = clean_series.mean()
                lower_bound, upper_bound = mean - (self.args.outlier_std * std), mean + (self.args.outlier_std * std)
                
            # Mask tracking mutations
            outliers_low = (df[col] < lower_bound)
            outliers_high = (df[col] > upper_bound)
            total_outliers = int(outliers_low.sum() + outliers_high.sum())
            
            if total_outliers > 0:
                df[col] = np.clip(df[col], lower_bound, upper_bound)
                self.increment_modified(total_outliers)
                self.report["transformations"]["outliers_capped"][col] = total_outliers

        # 5. String / Categorical Standardization & Fuzzy Grouping via Built-In Difflib
        from difflib import get_close_matches
        
        for col in df.select_dtypes(include=['object', 'string']).columns:
            # Strip whitespace safely
            before_strip_nulls = df[col].isna().sum()
            df[col] = df[col].astype(str).str.strip()
            # If original cell was NaN, it becomes text "nan". Convert back.
            df[col] = df[col].replace(["nan", "NaN", "None", "<na>"], np.nan)
            
            # Apply Majority Case Strategy
            non_nulls = df[col].dropna()
            if not non_nulls.empty:
                upper_count = non_nulls.str.isupper().sum()
                lower_count = non_nulls.str.islower().sum()
                title_count = non_nulls.str.istitle().sum()
                
                # Default to lowercase transformation unless title or upper significantly dominates
                if upper_count > lower_count and upper_count > title_count:
                    df[col] = df[col].str.upper()
                elif title_count > lower_count:
                    df[col] = df[col].str.title()
                else:
                    df[col] = df[col].str.lower()
            
            # Fuzzy Levenshtein Merging Variant groupings (using pure python fallback safely)
            non_null_unique = df[col].dropna().unique()
            if len(non_null_unique) > 1 and len(non_null_unique) < 200: # Limit footprint over large structures
                mapping_replacements = {}
                seen = set()
                
                # Sort values by frequency to merge elements into the dominant variant
                val_counts = df[col].value_counts()
                sorted_vals = list(val_counts.index)
                
                for item in sorted_vals:
                    if item in seen:
                        continue
                    # Match words within a cutoff matching a ~0.85 Levenshtein calculation metric
                    matches = get_close_matches(item, sorted_vals, n=5, cutoff=0.85)
                    for match in matches:
                        if match != item and match not in seen:
                            mapping_replacements[match] = item
                            seen.add(match)
                    seen.add(item)
                
                if mapping_replacements:
                    df[col] = df[col].replace(mapping_replacements)
                    self.increment_modified(len(mapping_replacements))
                    self.report["transformations"]["fuzzy_groupings"][col] = {str(k): str(v) for k, v in mapping_replacements.items()}

        # 6. Cross-field logic: Chronological Validation Safeguards
        # Locate potential datetime columns to enforce end > start rules
        date_cols = []
        for col in df.columns:
            if "date" in col or "time" in col:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce', format=self.args.datetime_format)
                    date_cols.append(col)
                except Exception:
                    pass
                    
        if len(date_cols) >= 2:
            # Check pairing logic matches start vs end names
            starts = [c for c in date_cols if "start" in c or "open" in c or "begin" in c]
            ends = [c for c in date_cols if "end" in c or "close" in c or "stop" in c]
            
            if starts and ends:
                s_col, e_col = starts[0], ends[0]
                chronology_violation = (df[s_col].notna()) & (df[e_col].notna()) & (df[e_col] < df[s_col])
                violation_count = int(chronology_violation.sum())
                if violation_count > 0:
                    # Logic: Swap positions if inverted chronologically
                    self.logger.warning(f"Chronology inversion found on {violation_count} records between '{s_col}' and '{e_col}'. Adjusting values.")
                    temp_store = df.loc[chronology_violation, s_col].copy()
                    df.loc[chronology_violation, s_col] = df.loc[chronology_violation, e_col]
                    df.loc[chronology_violation, e_col] = temp_store
                    self.increment_modified(violation_count * 2)

        return df

    def _phase_6_generate_outputs(self, df: pd.DataFrame, original_delimiter: str) -> None:
        self.logger.info("Phase 6: Emitting analytical artifacts.")
        
        # Format default clean out path if none specified
        if not self.args.output_file:
            base, ext = os.path.splitext(self.args.input_file)
            output_filepath = f"{base}_cleaned{ext}"
        else:
            output_filepath = self.args.output_file
            
        base_output, _ = os.path.splitext(output_filepath)
        report_filepath = f"{base_output}_report.json"
        
        # 1. Save Clean DataFrame
        df.to_csv(output_filepath, sep=original_delimiter, index=False)
        self.logger.info(f"Cleaned data structural arrays saved to '{output_filepath}'")
        
        # 2. Finalize JSON Metric calculations
        self.report["final_shape"] = {"rows": df.shape[0], "columns": df.shape[1]}
        with open(report_filepath, "w", encoding="utf-8") as json_file:
            json.dump(self.report, json_file, indent=4)
        self.logger.info(f"Metadata lifecycle structural report written to '{report_filepath}'")
        
        # 3. Print out structural dashboard log metrics
        print("\n" + "="*60)
        print("                 DATA CLEANING EXECUTIVE SUMMARY        ")
        print("="*60)
        print(f" Original Shape      : {self.report['original_shape']['rows']} Rows | {self.report['original_shape']['columns']} Columns")
        print(f" Cleaned Shape       : {self.report['final_shape']['rows']} Rows | {self.report['final_shape']['columns']} Columns")
        print(f" Malformed Lines Rows Dropped: {self.report['skipped_malformed_lines']}")
        print(f" Duplicate Records Removed   : {self.report['transformations']['rows_dropped_count']}")
        print(f" Columns Completely Dropped  : {len(self.report['transformations']['columns_dropped'])}")
        print(f" Direct Internal Target Cells Modified: {self.report['transformations']['cells_modified_count']}")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Production-Grade Engineered Data Quality and Cleaning Engine Command Line Interface.")
    parser.add_argument("--input-file", required=True, help="Path to raw source file dataset.")
    parser.add_argument("--output-file", default=None, help="Destination target path file execution output.")
    parser.add_argument("--delimiter", default=None, help="Explicit dataset delimiter symbol choice override (, or \\t).")
    parser.add_argument("--encoding", default=None, help="Explicit file text codec interpretation override system (e.g. utf-8).")
    parser.add_argument("--primary-key", default=None, help="Comma separated string sequence declaring deterministic key values.")
    parser.add_argument("--datetime-format", default=None, help="Explicit format template rules string sequence (e.g. %%Y-%%m-%%d).")
    parser.add_argument("--null-placeholders", nargs="+", default=["NULL", "NA", "NaN", "-", "999"], help="Dynamic list defining empty text representations.")
    parser.add_argument("--drop-threshold", type=float, default=0.70, help="Column Null drop standard limit constraint.")
    parser.add_argument("--impute-threshold", type=float, default=0.40, help="Column Null input value data resolution threshold marker.")
    parser.add_argument("--outlier-method", choices=["zscore", "iqr"], default="iqr", help="Outlier structural estimation selection formula framework.")
    parser.add_argument("--outlier-std", type=float, default=3.0, help="Z-score absolute limit validation margin constraint standard.")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING"], default="INFO", help="Global messaging verbosity logging tracker configuration details.")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="[%(levelname)s] %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    try:
        engine = DataQualityEngine(args)
        engine.run_pipeline()
    except Exception as e:
        logging.critical(f"Pipeline process collapsed due to an unhandled exception runtime: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
