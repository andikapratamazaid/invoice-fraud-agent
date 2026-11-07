"""CLI Invoice Fraud & Three-Way Match Agent.

Menjalankan analisis atas folder samples dan menulis laporan Markdown:
- ringkasan.md        : ringkasan eksekutif dan distribusi status
- rekap-vendor.md     : peringkat risiko vendor
- invoice-<id>.md     : satu laporan per invoice yang memiliki temuan

Contoh:
    python cli.py --samples samples --out hasil
"""

import argparse
from pathlib import Path

import checks
import loader
import report
import scoring


def run_analysis(samples_dir):
    dataset = loader.load_dataset(samples_dir)
    analysis = checks.run_checks(dataset)
    scores = scoring.score_invoices(dataset, analysis)
    vendor_rows = scoring.vendor_risk(dataset, analysis, scores)
    return dataset, analysis, scores, vendor_rows


def main():
    parser = argparse.ArgumentParser(description="Invoice Fraud & Three-Way Match Agent")
    parser.add_argument("--samples", default="samples", help="folder data masukan")
    parser.add_argument("--out", default="hasil", help="folder laporan keluaran")
    args = parser.parse_args()

    dataset, analysis, scores, vendor_rows = run_analysis(args.samples)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    (out / "ringkasan.md").write_text(
        report.summary_report(dataset, analysis, scores, vendor_rows), encoding="utf-8")
    (out / "rekap-vendor.md").write_text(
        report.vendor_recap_report(dataset, vendor_rows, analysis), encoding="utf-8")

    flagged = 0
    for inv in dataset.invoices:
        score_obj = scores[inv.invoice_id]
        findings = analysis.findings_for_invoice(inv.invoice_id)
        if not findings:
            continue
        flagged += 1
        vendor_name = dataset.vendors[inv.vendor_id].name if inv.vendor_id in dataset.vendors else inv.vendor_id
        text = report.invoice_report(inv, analysis.matches[inv.invoice_id], findings,
                                     score_obj, vendor_name)
        (out / f"invoice-{inv.invoice_id}.md").write_text(text, encoding="utf-8")

    status_counts = {}
    for s in scores.values():
        status_counts[s.status] = status_counts.get(s.status, 0) + 1
    print(f"Invoice dianalisis : {len(dataset.invoices)}")
    print(f"BERSIH             : {status_counts.get('BERSIH', 0)}")
    print(f"PERINGATAN         : {status_counts.get('PERINGATAN', 0)}")
    print(f"TAHAN BAYAR        : {status_counts.get('TAHAN BAYAR', 0)}")
    print(f"Laporan per invoice: {flagged} berkas di {out}/")


if __name__ == "__main__":
    main()
