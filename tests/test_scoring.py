import scoring
from checks import Finding
from conftest import make_invoice
from datetime import date


def test_ambang_status():
    assert scoring.status_for_score(0) == "BERSIH"
    assert scoring.status_for_score(29) == "BERSIH"
    assert scoring.status_for_score(30) == "PERINGATAN"
    assert scoring.status_for_score(59) == "PERINGATAN"
    assert scoring.status_for_score(60) == "TAHAN BAYAR"
    assert scoring.status_for_score(100) == "TAHAN BAYAR"


def test_temuan_keras_memaksa_tahan_bayar():
    assert scoring.status_for_score(10, has_hard=True) == "TAHAN BAYAR"


def test_skor_dibatasi_100():
    inv = make_invoice("I1", "V1", "PO-1", date(2026, 2, 1), [(1, "A", 1, 1000)])
    findings = [Finding("ganda_eksak", "V1", "x", "I1"),
                Finding("tanpa_po", "V1", "x", "I1"),
                Finding("kelebihan_volume", "V1", "x", "I1")]
    score = scoring.InvoiceScore(inv, findings)
    assert score.score == 100
    assert score.status == "TAHAN BAYAR"
    assert score.has_hard is True


def test_skor_tanpa_temuan():
    inv = make_invoice("I1", "V1", "PO-1", date(2026, 2, 1), [(1, "A", 1, 1000)])
    score = scoring.InvoiceScore(inv, [])
    assert score.score == 0
    assert score.status == "BERSIH"
