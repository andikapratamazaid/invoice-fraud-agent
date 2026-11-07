"""Lapisan AI: insight atas temuan pemeriksaan.

Menghasilkan untuk invoice yang tertandai:
- draf pertanyaan klarifikasi yang bisa dikirim ke vendor,
- opini kedua dalam JSON terstruktur (pola fraud terduga, bukti
  terkuat, langkah verifikasi),
- ringkasan eksekutif.

LLM bersifat opsional. Bila env INVOICE_FRAUD_LLM_API_KEY terisi, opini
kedua diminta dari endpoint yang kompatibel dengan OpenAI
(INVOICE_FRAUD_LLM_BASE_URL, INVOICE_FRAUD_LLM_MODEL). Tanpa key, modul
ini memakai templat deterministik dari temuan, sehingga seluruh alur
tetap berjalan dan teruji tanpa layanan eksternal.
"""

import json
import os
import urllib.request

from scoring import CHECK_LABELS

QUESTION_TEMPLATES = {
    "ganda_eksak": "Mohon konfirmasi, apakah invoice {no} memang diterbitkan dua kali? "
                   "Kami menerima dua pengajuan dengan nomor dan nominal yang sama.",
    "ganda_samar": "Mohon klarifikasi perbedaan nomor invoice {no} dengan invoice lain "
                   "bernominal sama yang kami terima dalam waktu berdekatan.",
    "tanpa_po": "Invoice {no} tidak mencantumkan nomor PO kami. Mohon sampaikan dasar "
                "penagihan dan dokumen pemesanan yang menjadi rujukan invoice ini.",
    "kelebihan_volume": "Pada invoice {no}, jumlah yang ditagih melebihi jumlah yang "
                        "tercantum pada berita acara penerimaan kami. Mohon sampaikan "
                        "bukti pengiriman tambahan bila ada.",
    "selisih_harga": "Harga satuan pada invoice {no} lebih tinggi dari harga pada PO. "
                     "Mohon sampaikan dasar penyesuaian harga tersebut.",
    "pecah_invoice": "Kami menerima beberapa invoice dalam waktu berdekatan yang "
                     "masing-masing berada di bawah batas persetujuan internal kami. "
                     "Mohon konfirmasi apakah penagihan ini dapat digabungkan per PO.",
    "melebihi_nilai_po": "Total tagihan untuk PO terkait telah melebihi nilai PO pada "
                         "invoice {no}. Mohon sampaikan penjelasan dan dokumen pendukungnya.",
    "angka_bulat": "Sebagian besar invoice Bapak/Ibu bernominal bulat penuh. Mohon "
                   "sampaikan rincian perhitungan volume dan harga per item untuk invoice {no}.",
    "benford": "Mohon sampaikan rincian perhitungan invoice {no} beserta dokumen "
               "pendukung pengiriman barangnya.",
}

PATTERN_GUESS = {
    "ganda_eksak": "penagihan ganda atas kewajiban yang sama",
    "ganda_samar": "penagihan ganda dengan nomor invoice yang diubah tipis",
    "tanpa_po": "penagihan tanpa dasar pemesanan yang tercatat",
    "kelebihan_volume": "penagihan atas barang yang belum diterima",
    "selisih_harga": "markup harga di atas kesepakatan PO",
    "pecah_invoice": "pemecahan tagihan untuk menghindari jenjang persetujuan",
    "melebihi_nilai_po": "penagihan melampaui nilai kontrak atau PO",
    "angka_bulat": "nominal karangan tanpa rincian perhitungan yang wajar",
    "benford": "pola angka nominal yang menyimpang dari distribusi alami",
}

VERIFY_STEPS = {
    "ganda_eksak": ["Cek riwayat pembayaran untuk nomor invoice yang sama",
                    "Minta vendor menarik salah satu pengajuan secara tertulis"],
    "ganda_samar": ["Bandingkan dokumen PDF kedua invoice baris per baris",
                    "Cek apakah ada dua pembayaran keluar untuk kewajiban yang sama"],
    "tanpa_po": ["Telusuri persetujuan lisan atau email pemesanan dari tim lapangan",
                 "Tahan pembayaran sampai dasar penagihan jelas"],
    "kelebihan_volume": ["Cocokkan ulang BAST dan surat jalan untuk item terkait",
                         "Minta bukti pengiriman tambahan dari vendor"],
    "selisih_harga": ["Bandingkan dengan lampiran penawaran harga yang disetujui",
                      "Minta nota koreksi atau credit note atas selisihnya"],
    "pecah_invoice": ["Gabungkan seluruh invoice satu PO dalam satu minggu dan nilai ulang",
                      "Periksa apakah ada persetujuan tertulis untuk penagihan terpisah"],
    "melebihi_nilai_po": ["Hitung ulang kumulatif pembayaran per PO",
                          "Minta addendum PO bila pekerjaan memang bertambah"],
    "angka_bulat": ["Minta rincian volume terpasang dan harga satuan per item",
                    "Bandingkan dengan progres fisik di lapangan"],
    "benford": ["Minta rincian perhitungan dan dokumen pendukung invoice besar vendor ini",
                "Sampel ulang beberapa invoice vendor yang sama dari periode lain"],
}


def clarification_questions(invoice, findings):
    questions = []
    seen = set()
    for finding in findings:
        template = QUESTION_TEMPLATES.get(finding.check_type)
        if template and finding.check_type not in seen:
            seen.add(finding.check_type)
            questions.append(template.format(no=invoice.invoice_no))
    return questions


def second_opinion(invoice, findings, score):
    """Opini kedua terstruktur. Mengembalikan dict JSON-able."""
    if not findings:
        return {
            "pola_fraud_terduga": "tidak ada pola fraud yang terdeteksi",
            "bukti_terkuat": "seluruh pemeriksaan lulus",
            "langkah_verifikasi": ["tidak ada tindakan lanjutan"],
            "skor_risiko": score,
            "status": "BERSIH",
        }
    main = max(findings, key=lambda f: len(f.detail))
    types = sorted({f.check_type for f in findings})
    return {
        "pola_fraud_terduga": "; ".join(PATTERN_GUESS.get(t, t) for t in types),
        "bukti_terkuat": main.detail,
        "langkah_verifikasi": [step for t in types for step in VERIFY_STEPS.get(t, [])],
        "skor_risiko": score,
        "jenis_temuan": types,
    }


def _llm_opinion(invoice, findings, score):
    """Minta opini kedua dari LLM bila env key tersedia. None bila gagal."""
    api_key = os.environ.get("INVOICE_FRAUD_LLM_API_KEY")
    if not api_key:
        return None
    base_url = os.environ.get("INVOICE_FRAUD_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("INVOICE_FRAUD_LLM_MODEL", "gpt-4o-mini")
    facts = {
        "invoice_no": invoice.invoice_no,
        "vendor_id": invoice.vendor_id,
        "total": invoice.total,
        "skor_risiko": score,
        "temuan": [{"jenis": f.check_type, "detail": f.detail} for f in findings],
    }
    prompt = (
        "Kamu adalah auditor internal. Berdasarkan temuan pemeriksaan invoice berikut, "
        "tulis opini kedua dalam JSON dengan kunci pola_fraud_terduga, bukti_terkuat, "
        "dan langkah_verifikasi (array string). Jangan menambah fakta di luar data.\n"
        + json.dumps(facts, ensure_ascii=False)
    )
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        opinion = json.loads(content)
        opinion["skor_risiko"] = score
        opinion["sumber"] = "llm"
        return opinion
    except Exception:
        return None


def invoice_insight(invoice, findings, score):
    """Insight lengkap satu invoice: pertanyaan klarifikasi + opini kedua."""
    opinion = _llm_opinion(invoice, findings, score)
    if opinion is None:
        opinion = second_opinion(invoice, findings, score)
        opinion["sumber"] = "templat"
    return {
        "pertanyaan_klarifikasi": clarification_questions(invoice, findings),
        "opini_kedua": opinion,
    }


def executive_summary(dataset, scores, vendor_rows):
    total = len(dataset.invoices)
    tahan = sum(1 for s in scores.values() if s.status == "TAHAN BAYAR")
    peringatan = sum(1 for s in scores.values() if s.status == "PERINGATAN")
    bersih = total - tahan - peringatan
    nilai_tahan = sum(s.invoice.total for s in scores.values() if s.status == "TAHAN BAYAR")
    lines = [
        f"Dari {total} invoice vendor yang diperiksa, {tahan} invoice berstatus "
        f"TAHAN BAYAR dengan nilai total Rp{nilai_tahan:,}, {peringatan} invoice "
        f"berstatus PERINGATAN, dan {bersih} invoice BERSIH.",
    ]
    if vendor_rows:
        top = vendor_rows[0]
        lines.append(
            f"Vendor dengan risiko tertinggi adalah {top['name']} "
            f"(skor risiko {top['risk']}, {top['findings']} temuan, "
            f"{top['tahan_bayar']} invoice ditahan)."
        )
    return " ".join(lines)
