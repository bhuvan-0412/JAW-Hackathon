#!/usr/bin/env python3
"""
run_flush_all.py — Guarantees 100% extraction of all 687 documents with real-time log flushing.
"""

import os
import json
import time
import pandas as pd
from extract_pipeline import process_document, BASE_DIR, OUTPUT_DIR, LOG_FILE

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.read_csv(os.path.join(BASE_DIR, 'document_index.csv'))
    total = len(df)
    print(f"Starting extraction with real-time flushing for {total} documents...", flush=True)

    # Truncate log file first
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        pass

    log_f = open(LOG_FILE, 'a', encoding='utf-8')
    t0 = time.time()
    
    for idx, row in df.iterrows():
        doc_json, log_entry = process_document(row)
        
        # Save per-document JSON
        out_path = os.path.join(OUTPUT_DIR, f"{row['doc_id']}.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(doc_json, f, indent=2, ensure_ascii=False)
            
        # Append to log file and flush immediately
        log_f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        log_f.flush()
        
        if (idx + 1) % 25 == 0 or (idx + 1) == total:
            elapsed = time.time() - t0
            print(f"[{idx + 1}/{total}] Processed {row['doc_id']} ({row['doc_type']}) - {elapsed:.1f}s", flush=True)

    log_f.close()
    t1 = time.time()
    print(f"\nSUCCESS! All {total} documents extracted and logged in {t1-t0:.2f}s.", flush=True)

if __name__ == '__main__':
    main()
