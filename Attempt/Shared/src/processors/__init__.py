"""Processors package: normalization, cleaning, anomaly detection, quality checks."""

from processors.normalize import (
    save_records_to_jsonl,
    load_jsonl,
    merge_records_by_source,
    create_pivot_table,
    build_feature_matrix,
    robust_scale,
    rank_normalize,
    log1p_normalize,
    standardize_pivot,
)
from processors.cleaner import (
    filter_failed_records,
    filter_anomalous_pivot_rows,
    fill_missing_windows,
    smooth_signal,
    clean_records,
    save_cleaning_log,
)
from processors.detector import (
    detect_zscore_outliers,
    detect_iqr_outliers,
    detect_consecutive_zeros,
    detect_sudden_drop,
    tag_anomalies_in_pivot,
    summarize_anomalies,
)
from processors.quality_checker import (
    check_data_quality,
    save_quality_report,
)
