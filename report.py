"""Pembuat laporan Markdown: per invoice tertandai, rekap vendor, ringkasan."""

from collections import defaultdict

import ai_insight
from scoring import CHECK_LABELS


def fmt_rp(amount):
    return f"Rp{amount:,}"


def invoice_report(invoice, match, findings, score_obj, vendor_name):
    lines = []
    lines.append(f"# Laporan Pemeriksaan Invoice {invoice.invoice_no}")
    lines.append("")
    lines.append(f"- ID invoice: {invoice.invoice_id}")
    lines.append(f"- Vendor: {vendor_name} ({invoice.vendor_id})")
    lines.append(f"- Tanggal invoice: {invoice.invoice_date.isoformat()}")
    lines.append(f"- Referensi PO: {invoice.po_id or 'tidak ada'}")
    lines.append(f"- Nilai invoice: {fmt_rp(invoice.total)}")
    lines.append(f"- Skor risiko: {score_obj.score} dari 100")
    lines.append(f"- Status: **{score_obj.status}**")
    lines.append("")
    lines.append("## Perbandingan Three-Way (PO vs BAST vs Invoice)")
    lines.append("")
    lines.append("| Item | Harga PO | Harga invoice | Qty PO | Qty diterima (BAST) | Qty ditagih | Kumulatif ditagih |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for line in match.lines:
        lines.append(
            f"| {line.item_name} | {fmt_rp(line.po_price) if line.po_price else '-'} | "
            f"{fmt_rp(line.billed_price)} | {line.po_qty or '-'} | "
            f"{line.received_qty if match.receipt else '-'} | {line.billed_qty} | "
            f"{line.cum_billed_qty or '-'} |"
        )
    lines.append("")
    if match.po is not None:
        lines.append(f"Nilai PO {match.po.po_id}: {fmt_rp(match.po.total)}. "
                     f"Kumulatif tagihan termasuk invoice ini: {fmt_rp(match.cum_amount_after)}.")
        lines.append("")
    lines.append("## Temuan")
    lines.append("")
    if findings:
        lines.append("| Pemeriksaan | Detail |")
        lines.append("| --- | --- |")
        for finding in findings:
            lines.append(f"| {CHECK_LABELS.get(finding.check_type, finding.check_type)} | {finding.detail} |")
    else:
        lines.append("Tidak ada temuan. Invoice lulus seluruh pemeriksaan.")
    lines.append("")
    insight = ai_insight.invoice_insight(invoice, findings, score_obj.score)
    lines.append("## Insight AI")
    lines.append("")
    if insight["pertanyaan_klarifikasi"]:
        lines.append("Draf pertanyaan klarifikasi ke vendor:")
        lines.append("")
        for q in insight["pertanyaan_klarifikasi"]:
            lines.append(f"- {q}")
        lines.append("")
    opinion = insight["opini_kedua"]
    lines.append(f"- Pola fraud terduga: {opinion.get('pola_fraud_terduga', '-')}")
    lines.append(f"- Bukti terkuat: {opinion.get('bukti_terkuat', '-')}")
    steps = opinion.get("langkah_verifikasi", [])
    if steps:
        lines.append("- Langkah verifikasi:")
        for step in steps:
            lines.append(f"  - {step}")
    lines.append(f"- Sumber opini: {opinion.get('sumber', 'templat')}")
    lines.append("")
    return "\n".join(lines)


def vendor_recap_report(dataset, vendor_rows, analysis):
    lines = []
    lines.append("# Rekap Risiko Vendor")
    lines.append("")
    lines.append("| Peringkat | Vendor | Skor risiko | Invoice | Nilai tagihan | Temuan | Temuan keras | Tahan bayar | Peringatan | Bersih | Rekening bersama |")
    lines.append("| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for i, row in enumerate(vendor_rows, start=1):
        lines.append(
            f"| {i} | {row['name']} | {row['risk']} | {row['invoice_count']} | "
            f"{fmt_rp(row['total_amount'])} | {row['findings']} | {row['hard_findings']} | "
            f"{row['tahan_bayar']} | {row['peringatan']} | {row['bersih']} | "
            f"{'ya' if row['shared_account'] else 'tidak'} |"
        )
    lines.append("")
    if analysis.shared_accounts:
        lines.append("## Rekening bank yang dipakai bersama")
        lines.append("")
        for account, vendors in analysis.shared_accounts:
            names = ", ".join(f"{v.name} ({v.vendor_id})" for v in vendors)
            lines.append(f"- Rekening {account}: {names}")
        lines.append("")
    lines.append("## Uji Benford (seluruh dataset)")
    lines.append("")
    stats = analysis.benford_dataset
    lines.append(f"- Jumlah invoice dinilai: {stats.get('n', 0)}")
    lines.append(f"- Chi-square: {stats.get('chi_square', 0):.2f}")
    lines.append(f"- MAD: {stats.get('mad', 0):.4f}")
    lines.append(f"- Kesesuaian: {stats.get('conformity', '-')}")
    lines.append("")
    return "\n".join(lines)


def summary_report(dataset, analysis, scores, vendor_rows):
    status_counts = defaultdict(int)
    for s in scores.values():
        status_counts[s.status] += 1
    type_counts = defaultdict(int)
    for finding in analysis.findings:
        if finding.invoice_id is not None:
            type_counts[finding.check_type] += 1
    lines = []
    lines.append("# Ringkasan Analisis Invoice")
    lines.append("")
    lines.append(ai_insight.executive_summary(dataset, scores, vendor_rows))
    lines.append("")
    lines.append("## Distribusi status invoice")
    lines.append("")
    lines.append("| Status | Jumlah |")
    lines.append("| --- | ---: |")
    for status in ("BERSIH", "PERINGATAN", "TAHAN BAYAR"):
        lines.append(f"| {status} | {status_counts.get(status, 0)} |")
    lines.append("")
    lines.append("## Temuan per jenis pemeriksaan")
    lines.append("")
    lines.append("| Pemeriksaan | Invoice tertandai |")
    lines.append("| --- | ---: |")
    for check_type in sorted(type_counts):
        lines.append(f"| {CHECK_LABELS.get(check_type, check_type)} | {type_counts[check_type]} |")
    lines.append("")
    return "\n".join(lines)
