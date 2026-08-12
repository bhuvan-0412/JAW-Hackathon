#!/usr/bin/env bash
set -euo pipefail

DOCS=""
QUESTIONS=""
OUT=""

# Parse CLI flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --docs)
      DOCS="$2"
      shift 2
      ;;
    --questions)
      QUESTIONS="$2"
      shift 2
      ;;
    --out)
      OUT="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$DOCS" || -z "$QUESTIONS" || -z "$OUT" ]]; then
  echo "Usage: ./run.sh --docs DIR --questions FILE --out FILE" >&2
  exit 1
fi

PYTHON_BIN=$(which python || which python3 || echo "python")

echo "================================================="
echo " Starting End-to-End Hackathon Pipeline Run"
echo "   Docs Dir:      $DOCS"
echo "   Questions:     $QUESTIONS"
echo "   Output CSV:    $OUT"
echo "   Python Bin:    $PYTHON_BIN"
echo "================================================="

# Stage 1: Document Ingestion
echo "[1/3] Ingesting documents from $DOCS ..."
$PYTHON_BIN extract_pipeline.py --docs "$DOCS" --output-dir ./extracted/

# Stage 2: Entity Graph & Database Index Population
echo "[2/3] Building entity graph & index database ..."
$PYTHON_BIN build_entities.py --extracted-dir ./extracted/ --out ./entities.json
$PYTHON_BIN build_index.py --extracted-dir ./extracted/ --db estate_index.db

# Stage 3: Question Answering Engine
echo "[3/3] Answering questions from $QUESTIONS ..."
$PYTHON_BIN solve_questions.py --input "$QUESTIONS" --output "$OUT"

echo "================================================="
echo " Done. Successfully wrote $OUT"
echo "================================================="
