#!/usr/bin/env bash
set -e

# Default arguments
DOCS_DIR="documents"
QUESTIONS_FILE="questions.json"
OUT_FILE="submission.csv"

# Parse CLI flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --docs)
      DOCS_DIR="$2"
      shift 2
      ;;
    --questions)
      QUESTIONS_FILE="$2"
      shift 2
      ;;
    --out)
      OUT_FILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

echo "================================================="
echo " Starting End-to-End Hackathon Pipeline Run"
echo "   Docs Dir:      $DOCS_DIR"
echo "   Questions:     $QUESTIONS_FILE"
echo "   Output CSV:    $OUT_FILE"
echo "================================================="

# Stage 1: Extraction Stage (Generic Recursive Scan)
echo "[Stage 1/4] Running Generic Extraction Pipeline..."
python extract_pipeline.py --docs "$DOCS_DIR" --output-dir extracted

# Stage 2: Entity Resolution
echo "[Stage 2/4] Running Generalizable Entity Resolution..."
python build_entities.py --extracted-dir extracted --out entities.json

# Stage 3: Index Population
echo "[Stage 3/4] Building SQLite Index..."
python build_index.py --extracted-dir extracted --db estate_index.db

# Stage 4: Reasoning & Solver
echo "[Stage 4/4] Executing Reasoning Engine..."
python solve_questions.py --input "$QUESTIONS_FILE" --output "$OUT_FILE"

echo "================================================="
echo " Pipeline Complete! Submission saved to $OUT_FILE"
echo "================================================="
