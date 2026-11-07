"""Bangun dashboard/data.js dari hasil analisis nyata atas folder samples."""

import json
from collections import Counter
from pathlib import Path

import checks
import loader
import scoring
from scoring import CHECK_LABELS

BASE = Path(__file__).resolve().parent


def build_data(samples_dir):
    dataset = loader.load_dataset(samples_dir)
    analysis = checks.run_checks(dataset)
    scores = scoring.score_invoices(dataset, analysis)
    vendor_rows = scoring.vendor_risk(dataset, analysis, scores)

    status_counts = Counter(s.status for s in scores.values())
    type_rows = []
    by_type = analysis.findings_by_type()
    for check_type, label in CHECK_LABELS.items():
        invs = {f.invoice_id for f in by_type.get(check_type, []) if f.invoice_id}
        if invs:
            type_rows.append({"type": check_type, "label": label, "invoices": len(invs)})
    type_rows.sort(key=lambda r: -r["invoices"])

    tahan = []
    for s in sorted(scores.values(), key=lambda x: (-x.score, -x.invoice.total)):
        if s.status != "TAHAN BAYAR":
            continue
        inv = s.invoice
        tahan.append({
            "invoice_id": inv.invoice_id,
            "invoice_no": inv.invoice_no,
            "vendor": dataset.vendors[inv.vendor_id].name if inv.vendor_id in dataset.vendors else inv.vendor_id,
            "date": inv.invoice_date.isoformat(),
            "total": inv.total,
            "score": s.score,
            "findings": [CHECK_LABELS.get(f.check_type, f.check_type) for f in s.findings],
        })

    return {
        "generated_from": "samples",
        "total_invoices": len(dataset.invoices),
        "total_vendors": len(dataset.vendors),
        "total_pos": len(dataset.pos),
        "total_amount": sum(i.total for i in dataset.invoices),
        "status_counts": {
            "BERSIH": status_counts.get("BERSIH", 0),
            "PERINGATAN": status_counts.get("PERINGATAN", 0),
            "TAHAN BAYAR": status_counts.get("TAHAN BAYAR", 0),
        },
        "findings_by_type": type_rows,
        "vendor_ranking": [
            {
                "vendor_id": r["vendor_id"], "name": r["name"], "risk": r["risk"],
                "invoice_count": r["invoice_count"], "total_amount": r["total_amount"],
                "findings": r["findings"], "tahan_bayar": r["tahan_bayar"],
                "shared_account": r["shared_account"],
            }
            for r in vendor_rows
        ],
        "tahan_bayar": tahan,
        "benford": {
            "n": analysis.benford_dataset["n"],
            "chi_square": round(analysis.benford_dataset["chi_square"], 2),
            "mad": round(analysis.benford_dataset["mad"], 4),
            "conformity": analysis.benford_dataset["conformity"],
        },
        "shared_accounts": [
            {"account": acc, "vendors": [v.name for v in vendors]}
            for acc, vendors in analysis.shared_accounts
        ],
    }


def main():
    data = build_data(BASE / "samples")
    out = BASE / "dashboard" / "data.js"
    out.write_text("const DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n",
                   encoding="utf-8")
    print(f"data.js ditulis: {data['total_invoices']} invoice, "
          f"{len(data['tahan_bayar'])} TAHAN BAYAR, "
          f"{len(data['vendor_ranking'])} vendor.")


if __name__ == "__main__":
    main()
