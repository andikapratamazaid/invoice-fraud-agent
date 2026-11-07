"""Evaluasi hasil deteksi terhadap label kebenaran di samples/labels.json.

Invoice dinilai terdeteksi untuk satu jenis fraud bila agent menghasilkan
temuan dengan jenis yang sama dengan labelnya. Precision, recall, dan F1
dihitung per jenis fraud dan secara keseluruhan (mikro). Hasil dicetak
apa adanya tanpa pembulatan ke atas.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import checks
import loader

EVAL_TYPES = [
    "ganda_eksak",
    "ganda_samar",
    "pecah_invoice",
    "tanpa_po",
    "kelebihan_volume",
    "selisih_harga",
    "angka_bulat",
    "melebihi_nilai_po",
]


def compute_metrics(labels, predicted):
    """labels: {invoice_id: label}; predicted: {invoice_id: set(check_type)}.
    Mengembalikan dict per jenis berisi tp, fp, fn, precision, recall, f1."""
    results = {}
    for check_type in EVAL_TYPES:
        tp = fp = fn = 0
        for invoice_id, label in labels.items():
            gold = label == check_type
            pred = check_type in predicted.get(invoice_id, set())
            if gold and pred:
                tp += 1
            elif pred and not gold:
                fp += 1
            elif gold and not pred:
                fn += 1
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        if precision is None or recall is None or (precision + recall) == 0:
            f1 = None if (precision is None or recall is None) else 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)
        results[check_type] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
            "gold": tp + fn, "predicted": tp + fp,
        }
    tp = sum(r["tp"] for r in results.values())
    fp = sum(r["fp"] for r in results.values())
    fn = sum(r["fn"] for r in results.values())
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall else (0.0 if precision is not None and recall is not None else None))
    results["KESELURUHAN"] = {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "gold": tp + fn, "predicted": tp + fp,
    }
    return results


def predicted_by_invoice(analysis):
    predicted = defaultdict(set)
    for finding in analysis.findings:
        if finding.invoice_id is not None:
            predicted[finding.invoice_id].add(finding.check_type)
    return predicted


def _fmt(value):
    return "-" if value is None else f"{value:.3f}"


def main():
    parser = argparse.ArgumentParser(description="Evaluasi deteksi fraud terhadap label")
    parser.add_argument("--samples", default="samples")
    parser.add_argument("--json", default=None, help="simpan hasil evaluasi sebagai JSON")
    args = parser.parse_args()

    dataset = loader.load_dataset(args.samples)
    labels = loader.load_labels(args.samples)
    analysis = checks.run_checks(dataset)
    predicted = predicted_by_invoice(analysis)
    results = compute_metrics(labels, predicted)

    print(f"{'Jenis fraud':<20} {'Label':>6} {'Deteksi':>8} {'TP':>4} {'FP':>4} {'FN':>4} "
          f"{'Precision':>10} {'Recall':>8} {'F1':>8}")
    print("-" * 84)
    for check_type in EVAL_TYPES + ["KESELURUHAN"]:
        r = results[check_type]
        print(f"{check_type:<20} {r['gold']:>6} {r['predicted']:>8} {r['tp']:>4} {r['fp']:>4} "
              f"{r['fn']:>4} {_fmt(r['precision']):>10} {_fmt(r['recall']):>8} {_fmt(r['f1']):>8}")
    print()
    print(f"Rekening dipakai bersama terdeteksi: {'ya' if analysis.shared_accounts else 'tidak'} "
          f"({len(analysis.shared_accounts)} kelompok)")
    stats = analysis.benford_dataset
    print(f"Uji Benford dataset: n={stats['n']}, chi-square={stats['chi_square']:.2f}, "
          f"MAD={stats['mad']:.4f}, kesesuaian={stats['conformity']}")

    if args.json:
        serializable = {k: {kk: vv for kk, vv in v.items()} for k, v in results.items()}
        Path(args.json).write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    main()
