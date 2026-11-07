import hashlib
from collections import Counter
from pathlib import Path

import generate_data
import loader

BASE = Path(__file__).resolve().parent.parent
SAMPLE_FILES = ["vendors.json", "pos.csv", "receipts.csv", "invoices.csv", "labels.json"]


def _hash_samples():
    return {name: hashlib.sha256((BASE / "samples" / name).read_bytes()).hexdigest()
            for name in SAMPLE_FILES}


def test_generator_deterministik():
    generate_data.main()
    first = _hash_samples()
    generate_data.main()
    second = _hash_samples()
    assert first == second


def test_generator_struktur_dan_label():
    generate_data.main()
    dataset = loader.load_dataset(BASE / "samples")
    labels = loader.load_labels(BASE / "samples")
    assert len(dataset.vendors) == 10
    assert len(dataset.pos) == 24
    assert len(dataset.receipts) == 24
    assert 135 <= len(dataset.invoices) <= 165
    assert set(labels) == {inv.invoice_id for inv in dataset.invoices}
    counts = Counter(labels.values())
    assert counts["ganda_eksak"] >= 6
    assert counts["ganda_samar"] >= 6
    assert counts["pecah_invoice"] >= 7
    assert counts["tanpa_po"] >= 3
    assert counts["kelebihan_volume"] >= 4
    assert counts["selisih_harga"] >= 4
    assert counts["angka_bulat"] >= 9
    assert counts["clean"] >= 100


def test_generator_kumulatif_tidak_melebihi_po():
    generate_data.main()
    dataset = loader.load_dataset(BASE / "samples")
    billed = Counter()
    for inv in dataset.invoices:
        if inv.po_id:
            billed[inv.po_id] += inv.total
    for po_id, amount in billed.items():
        assert amount <= dataset.pos[po_id].total


def test_generator_rekening_sama_hanya_satu_pasangan():
    generate_data.main()
    dataset = loader.load_dataset(BASE / "samples")
    accounts = Counter(v.bank_account for v in dataset.vendors.values())
    shared = {acc: n for acc, n in accounts.items() if n > 1}
    assert len(shared) == 1
