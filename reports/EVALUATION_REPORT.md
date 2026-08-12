# Evaluation Benchmark Report

**Generated:** 2026-08-13 00:40:34

## Overall Score: `10.71 / 21` (`50.99%`)

- **Answered Questions:** `21 / 21`

## Score Breakdown by Question Shape

| Shape | Score | Count | Accuracy |
|---|---:|---:|---:|
| `temporal_chain` | 1.98 | 2 | **98.8%** |
| `threshold_aggregate` | 1.83 | 2 | **91.4%** |
| `distinct_count` | 1.75 | 2 | **87.5%** |
| `avg_work_size` | 1.26 | 2 | **63.1%** |
| `rank_value` | 1.00 | 2 | **50.0%** |
| `hop_aggregate` | 0.92 | 2 | **46.2%** |
| `exclusion_aggregate` | 0.83 | 2 | **41.4%** |
| `date_span` | 0.64 | 2 | **32.0%** |
| `absence` | 0.50 | 2 | **25.0%** |
| `gap_to_threshold` | 0.00 | 1 | **0.0%** |
| `referenced_share` | 0.00 | 2 | **0.0%** |

## Score Breakdown by Answer Type

| Answer Type | Score | Count | Accuracy |
|---|---:|---:|---:|
| `money` | 7.82 | 13 | **60.1%** |
| `count` | 2.25 | 4 | **56.2%** |
| `days` | 0.64 | 2 | **32.0%** |
| `percent` | 0.00 | 2 | **0.0%** |

## Error Histogram

| Closeness Tier | Questions | Share |
|---|---:|---:|
| `exact (1.00)` | 4 | 19.0% |
| `95% - 99.9%` | 1 | 4.8% |
| `80% - 94.9%` | 3 | 14.3% |
| `50% - 79.9%` | 4 | 19.0% |
| `>0% - 49.9%` | 2 | 9.5% |
| `0% (Zero)` | 7 | 33.3% |

## High Priority Diagnostic Misses (Worst Performing)

| QID | Shape | Gold | Got | Score | Error % |
|---|---|---:|---:|---:|---:|
| `HS-IC-0001` | `absence` | 1.00 | 9.00 | 0.000 | 800.0% |
| `HS-IC-0004` | `date_span` | 646.00 | 3,742.00 | 0.000 | 479.3% |
| `HS-IC-0015` | `exclusion_aggregate` | 763,300,000.00 | 1,773,600,000.00 | 0.000 | 132.4% |
| `HS-IC-0017` | `gap_to_threshold` | 28,700,000.00 | 0.00 | 0.000 | 100.0% |
| `HS-IC-0018` | `rank_value` | 84,200,000.00 | 1,277,800,000.00 | 0.000 | 1417.6% |
| `HS-IC-0020` | `referenced_share` | 33.33 | 0.00 | 0.000 | 100.0% |
| `HS-IC-0021` | `referenced_share` | 66.67 | 0.00 | 0.000 | 100.0% |
| `HS-IC-0007` | `hop_aggregate` | 2,008,199,999.00 | 529,900,000.00 | 0.264 | 73.6% |
| `HS-IC-0011` | `avg_work_size` | 537,933,333.00 | 200,000,000.00 | 0.372 | 62.8% |
| `HS-IC-0002` | `absence` | 2.00 | 1.00 | 0.500 | 50.0% |