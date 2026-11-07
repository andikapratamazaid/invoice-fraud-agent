"""Bangun notebooks/evaluasi.ipynb sebagai JSON nbformat 4 yang valid,
dengan output teks NYATA dari run analisis dan evaluasi pada dataset
contoh. Tidak membutuhkan Jupyter terpasang; notebook dapat dibuka di
Jupyter atau VS Code dan dijalankan ulang sel demi sel.
"""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import checks
import loader
import run_eval

BASE = Path(__file__).resolve().parent


def code_cell(source, output_text=None):
    cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "source": source.splitlines(keepends=True),
        "outputs": [],
    }
    if output_text:
        cell["outputs"].append({
            "output_type": "stream",
            "name": "stdout",
            "text": output_text.splitlines(keepends=True),
        })
    return cell


def md_cell(source):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def capture(fn):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return buf.getvalue()


def main():
    dataset = loader.load_dataset(BASE / "samples")
    labels = loader.load_labels(BASE / "samples")

    out_load = capture(lambda: print(
        f"Vendor: {len(dataset.vendors)} | PO: {len(dataset.pos)} | "
        f"BAST: {len(dataset.receipts)} | Invoice: {len(dataset.invoices)}"))

    def run_analysis_print():
        analysis = checks.run_checks(dataset)
        from collections import Counter
        import scoring
        scores = scoring.score_invoices(dataset, analysis)
        counts = Counter(s.status for s in scores.values())
        print(f"Total temuan: {len(analysis.findings)}")
        for status in ("BERSIH", "PERINGATAN", "TAHAN BAYAR"):
            print(f"{status}: {counts.get(status, 0)} invoice")
        for check_type, items in sorted(analysis.findings_by_type().items()):
            invs = {f.invoice_id for f in items if f.invoice_id}
            print(f"{check_type}: {len(invs)} invoice tertandai")

    out_analysis = capture(run_analysis_print)

    def run_eval_print():
        analysis = checks.run_checks(dataset)
        predicted = run_eval.predicted_by_invoice(analysis)
        results = run_eval.compute_metrics(labels, predicted)
        print(f"{'Jenis':<20} {'TP':>4} {'FP':>4} {'FN':>4} {'Precision':>10} {'Recall':>8} {'F1':>8}")
        for name in run_eval.EVAL_TYPES + ["KESELURUHAN"]:
            r = results[name]
            fmt = run_eval._fmt
            print(f"{name:<20} {r['tp']:>4} {r['fp']:>4} {r['fn']:>4} "
                  f"{fmt(r['precision']):>10} {fmt(r['recall']):>8} {fmt(r['f1']):>8}")

    out_eval = capture(run_eval_print)

    def run_benford_print():
        stats = checks.benford_stats([i.total for i in dataset.invoices])
        print(f"n = {stats['n']}")
        print("Digit | Aktual | Harapan Benford")
        for d in range(1, 10):
            print(f"  {d}   | {stats['actual'][d]:.3f}  | {stats['expected'][d]:.3f}")
        print(f"Chi-square = {stats['chi_square']:.2f}")
        print(f"MAD = {stats['mad']:.4f} ({stats['conformity']})")
        print("Grafik perbandingan aktual vs harapan ada di ../docs/img/benford.png")

    out_benford = capture(run_benford_print)

    nb = {
        "cells": [
            md_cell("# Evaluasi Invoice Fraud & Three-Way Match Agent\n\n"
                    "Notebook ini memuat dataset contoh, menjalankan seluruh pemeriksaan, "
                    "dan menilai hasilnya terhadap label kebenaran di `samples/labels.json`. "
                    "Output pada setiap sel adalah output nyata dari run yang sama dengan "
                    "yang dipakai untuk README."),
            code_cell("import sys\nsys.path.insert(0, '..')\n\n"
                      "import checks, loader, run_eval, scoring\n\n"
                      "dataset = loader.load_dataset('../samples')\n"
                      "labels = loader.load_labels('../samples')\n"
                      "print(f\"Vendor: {len(dataset.vendors)} | PO: {len(dataset.pos)} | \"\n"
                      "      f\"BAST: {len(dataset.receipts)} | Invoice: {len(dataset.invoices)}\")",
                      out_load),
            code_cell("analysis = checks.run_checks(dataset)\n"
                      "scores = scoring.score_invoices(dataset, analysis)\n"
                      "# cetak distribusi status dan temuan per jenis",
                      out_analysis),
            md_cell("## Tabel evaluasi terhadap label kebenaran\n\n"
                    "Invoice dinilai terdeteksi untuk satu jenis fraud bila agent menghasilkan "
                    "temuan berjenis sama dengan labelnya."),
            code_cell("predicted = run_eval.predicted_by_invoice(analysis)\n"
                      "results = run_eval.compute_metrics(labels, predicted)\n"
                      "# cetak tabel precision, recall, F1 per jenis dan keseluruhan",
                      out_eval),
            md_cell("## Uji Benford\n\n"
                    "Distribusi digit pertama seluruh nominal invoice dibandingkan dengan "
                    "distribusi Benford memakai chi-square dan MAD Nigrini."),
            code_cell("stats = checks.benford_stats([i.total for i in dataset.invoices])\n"
                      "# cetak proporsi aktual vs harapan, chi-square, dan MAD",
                      out_benford),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    out = BASE / "notebooks" / "evaluasi.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Notebook ditulis: {out} ({len(nb['cells'])} sel)")


if __name__ == "__main__":
    main()
