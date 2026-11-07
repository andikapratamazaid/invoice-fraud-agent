#!/usr/bin/env bash
# Demo ujung ke ujung Invoice Fraud & Three-Way Match Agent:
# generate data (bila belum ada) -> analisis -> evaluasi -> dashboard -> visual.
set -e
cd "$(dirname "$0")/.."

PY="python3"
if [ -x /tmp/if-venv/bin/python ]; then
  PY=/tmp/if-venv/bin/python
fi

if [ ! -f samples/invoices.csv ]; then
  echo "== Generate data contoh =="
  $PY generate_data.py
fi

echo "== Analisis invoice =="
$PY cli.py --samples samples --out hasil

echo "== Evaluasi terhadap label =="
$PY run_eval.py --samples samples

echo "== Bangun data dashboard =="
$PY build_dashboard_data.py

echo "== Bangun visual =="
$PY make_visuals.py

echo "== Selesai. Buka dashboard/index.html untuk melihat dashboard. =="
