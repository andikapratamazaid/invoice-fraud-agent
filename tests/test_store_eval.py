import json
from pathlib import Path

import ai_insight
import checks
import loader
import run_eval
import scoring
import store
from checks import Finding
from conftest import make_invoice
from datetime import date

BASE = Path(__file__).resolve().parent.parent


def test_store_simpan_dan_rekap(tmp_path):
    dataset = loader.load_dataset(BASE / "samples")
    analysis = checks.run_checks(dataset)
    scores = scoring.score_invoices(dataset, analysis)
    vendor_rows = scoring.vendor_risk(dataset, analysis, scores)
    conn = store.connect(tmp_path / "uji.db")
    try:
        store.save_results(conn, dataset, analysis, scores, vendor_rows)
        recap = store.recap_by_status(conn)
        assert sum(r["jumlah_invoice"] for r in recap) == len(dataset.invoices)
        vendors = store.recap_by_vendor(conn)
        assert len(vendors) == 10
        assert vendors[0]["risk_score"] >= vendors[-1]["risk_score"]
        types = store.findings_by_type(conn)
        assert sum(r["jumlah_temuan"] for r in types) > 0
    finally:
        conn.close()


def test_eval_metrik_kasus_campuran():
    labels = {"A": "ganda_eksak", "B": "clean", "C": "tanpa_po", "D": "clean"}
    predicted = {"A": {"ganda_eksak"}, "B": {"ganda_eksak"}, "C": set(), "D": set()}
    results = run_eval.compute_metrics(labels, predicted)
    assert results["ganda_eksak"]["tp"] == 1
    assert results["ganda_eksak"]["fp"] == 1
    assert results["ganda_eksak"]["precision"] == 0.5
    assert results["ganda_eksak"]["recall"] == 1.0
    assert results["tanpa_po"]["fn"] == 1
    assert results["tanpa_po"]["recall"] == 0.0
    overall = results["KESELURUHAN"]
    assert overall["tp"] == 1 and overall["fp"] == 1 and overall["fn"] == 1
    assert overall["precision"] == 0.5 and overall["recall"] == 0.5


def test_eval_metrik_sempurna():
    labels = {"A": "pecah_invoice", "B": "clean"}
    predicted = {"A": {"pecah_invoice"}, "B": set()}
    results = run_eval.compute_metrics(labels, predicted)
    assert results["KESELURUHAN"]["f1"] == 1.0


def test_ai_insight_fallback_templat(monkeypatch):
    monkeypatch.delenv("INVOICE_FRAUD_LLM_API_KEY", raising=False)
    inv = make_invoice("I1", "V1", "", date(2026, 2, 1), [(1, "A", 2, 5000)],
                       invoice_no="INV/2026/0101")
    findings = [Finding("ganda_eksak", "V1", "Nomor invoice muncul 2 kali.", "I1"),
                Finding("tanpa_po", "V1", "Tidak ada referensi PO.", "I1")]
    insight = ai_insight.invoice_insight(inv, findings, 100)
    assert len(insight["pertanyaan_klarifikasi"]) == 2
    opinion = insight["opini_kedua"]
    assert opinion["sumber"] == "templat"
    assert "pola_fraud_terduga" in opinion
    assert "bukti_terkuat" in opinion
    assert len(opinion["langkah_verifikasi"]) >= 2
    json.dumps(insight)  # harus bisa diserialisasi ke JSON


def test_ai_insight_invoice_bersih():
    inv = make_invoice("I1", "V1", "PO-1", date(2026, 2, 1), [(1, "A", 2, 5000)])
    insight = ai_insight.invoice_insight(inv, [], 0)
    assert insight["pertanyaan_klarifikasi"] == []
    assert insight["opini_kedua"]["pola_fraud_terduga"].startswith("tidak ada")
