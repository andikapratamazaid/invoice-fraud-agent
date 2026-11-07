const DATA = {
  "generated_from": "samples",
  "total_invoices": 148,
  "total_vendors": 10,
  "total_pos": 24,
  "total_amount": 4828692997,
  "status_counts": {
    "BERSIH": 118,
    "PERINGATAN": 17,
    "TAHAN BAYAR": 13
  },
  "findings_by_type": [
    {
      "type": "angka_bulat",
      "label": "Pola nominal bulat berulang",
      "invoices": 9
    },
    {
      "type": "benford",
      "label": "Catatan uji Benford",
      "invoices": 9
    },
    {
      "type": "pecah_invoice",
      "label": "Pecah invoice hindari persetujuan",
      "invoices": 7
    },
    {
      "type": "ganda_eksak",
      "label": "Invoice ganda eksak",
      "invoices": 6
    },
    {
      "type": "ganda_samar",
      "label": "Invoice ganda samar",
      "invoices": 6
    },
    {
      "type": "kelebihan_volume",
      "label": "Kelebihan volume tagih",
      "invoices": 4
    },
    {
      "type": "selisih_harga",
      "label": "Selisih harga di atas toleransi",
      "invoices": 4
    },
    {
      "type": "tanpa_po",
      "label": "Invoice tanpa PO",
      "invoices": 3
    }
  ],
  "vendor_ranking": [
    {
      "vendor_id": "V04",
      "name": "PT Elektrikal Nusantara Jaya",
      "risk": 44,
      "invoice_count": 13,
      "total_amount": 472896166,
      "findings": 1,
      "tahan_bayar": 1,
      "shared_account": true
    },
    {
      "vendor_id": "V10",
      "name": "PT Kaca Bangun Persada",
      "risk": 43,
      "invoice_count": 14,
      "total_amount": 529593521,
      "findings": 3,
      "tahan_bayar": 0,
      "shared_account": true
    },
    {
      "vendor_id": "V05",
      "name": "CV Plumbing Sejahtera",
      "risk": 38,
      "invoice_count": 13,
      "total_amount": 150778186,
      "findings": 5,
      "tahan_bayar": 2,
      "shared_account": false
    },
    {
      "vendor_id": "V08",
      "name": "CV Alat Berat Rentindo",
      "risk": 38,
      "invoice_count": 12,
      "total_amount": 388366650,
      "findings": 4,
      "tahan_bayar": 2,
      "shared_account": false
    },
    {
      "vendor_id": "V06",
      "name": "PT Cat Warna Prima",
      "risk": 36,
      "invoice_count": 13,
      "total_amount": 172521340,
      "findings": 3,
      "tahan_bayar": 2,
      "shared_account": false
    },
    {
      "vendor_id": "V01",
      "name": "PT Sumber Material Nusantara",
      "risk": 35,
      "invoice_count": 19,
      "total_amount": 256393690,
      "findings": 4,
      "tahan_bayar": 3,
      "shared_account": false
    },
    {
      "vendor_id": "V02",
      "name": "PT Baja Perkasa Abadi",
      "risk": 35,
      "invoice_count": 18,
      "total_amount": 707754654,
      "findings": 3,
      "tahan_bayar": 3,
      "shared_account": false
    },
    {
      "vendor_id": "V03",
      "name": "CV Karya Betonindo",
      "risk": 24,
      "invoice_count": 19,
      "total_amount": 993487140,
      "findings": 4,
      "tahan_bayar": 0,
      "shared_account": false
    },
    {
      "vendor_id": "V07",
      "name": "PT Kayu Jati Makmur",
      "risk": 22,
      "invoice_count": 18,
      "total_amount": 308901650,
      "findings": 3,
      "tahan_bayar": 0,
      "shared_account": false
    },
    {
      "vendor_id": "V09",
      "name": "PT Granit Alam Sejahtera",
      "risk": 15,
      "invoice_count": 9,
      "total_amount": 848000000,
      "findings": 18,
      "tahan_bayar": 0,
      "shared_account": false
    }
  ],
  "tahan_bayar": [
    {
      "invoice_id": "F-0088",
      "invoice_no": "INV/2026/0109",
      "vendor": "PT Cat Warna Prima",
      "date": "2026-03-30",
      "total": 22429500,
      "score": 70,
      "findings": [
        "Invoice ganda eksak"
      ]
    },
    {
      "invoice_id": "F-0094",
      "invoice_no": "INV/2026/0109",
      "vendor": "PT Cat Warna Prima",
      "date": "2026-04-03",
      "total": 22429500,
      "score": 70,
      "findings": [
        "Invoice ganda eksak"
      ]
    },
    {
      "invoice_id": "F-0135",
      "invoice_no": "INV/2026/0114",
      "vendor": "PT Baja Perkasa Abadi",
      "date": "2026-05-15",
      "total": 21756000,
      "score": 70,
      "findings": [
        "Invoice ganda eksak"
      ]
    },
    {
      "invoice_id": "F-0136",
      "invoice_no": "INV/2026/0114",
      "vendor": "PT Baja Perkasa Abadi",
      "date": "2026-05-19",
      "total": 21756000,
      "score": 70,
      "findings": [
        "Invoice ganda eksak"
      ]
    },
    {
      "invoice_id": "F-0131",
      "invoice_no": "INV/2026/0115",
      "vendor": "PT Sumber Material Nusantara",
      "date": "2026-05-10",
      "total": 10780000,
      "score": 70,
      "findings": [
        "Invoice ganda eksak"
      ]
    },
    {
      "invoice_id": "F-0132",
      "invoice_no": "INV/2026/0115",
      "vendor": "PT Sumber Material Nusantara",
      "date": "2026-05-14",
      "total": 10780000,
      "score": 70,
      "findings": [
        "Invoice ganda eksak"
      ]
    },
    {
      "invoice_id": "F-0076",
      "invoice_no": "INV/2026/0107",
      "vendor": "CV Alat Berat Rentindo",
      "date": "2026-03-21",
      "total": 35100000,
      "score": 65,
      "findings": [
        "Invoice tanpa PO"
      ]
    },
    {
      "invoice_id": "F-0020",
      "invoice_no": "INV/2026/0103",
      "vendor": "PT Elektrikal Nusantara Jaya",
      "date": "2026-01-29",
      "total": 27400000,
      "score": 65,
      "findings": [
        "Invoice tanpa PO"
      ]
    },
    {
      "invoice_id": "F-0069",
      "invoice_no": "INV/2026/0108",
      "vendor": "CV Plumbing Sejahtera",
      "date": "2026-03-16",
      "total": 19425000,
      "score": 65,
      "findings": [
        "Invoice tanpa PO"
      ]
    },
    {
      "invoice_id": "F-0126",
      "invoice_no": "INV/2026/0112",
      "vendor": "PT Baja Perkasa Abadi",
      "date": "2026-05-03",
      "total": 68257500,
      "score": 60,
      "findings": [
        "Kelebihan volume tagih"
      ]
    },
    {
      "invoice_id": "F-0049",
      "invoice_no": "INV/2026/0105",
      "vendor": "CV Alat Berat Rentindo",
      "date": "2026-02-23",
      "total": 42750000,
      "score": 60,
      "findings": [
        "Kelebihan volume tagih"
      ]
    },
    {
      "invoice_id": "F-0118",
      "invoice_no": "INV/2026/0113",
      "vendor": "PT Sumber Material Nusantara",
      "date": "2026-04-25",
      "total": 12892500,
      "score": 60,
      "findings": [
        "Kelebihan volume tagih"
      ]
    },
    {
      "invoice_id": "F-0097",
      "invoice_no": "INV/2026/0112",
      "vendor": "CV Plumbing Sejahtera",
      "date": "2026-04-05",
      "total": 12195000,
      "score": 60,
      "findings": [
        "Kelebihan volume tagih"
      ]
    }
  ],
  "benford": {
    "n": 148,
    "chi_square": 14.9,
    "mad": 0.0221,
    "conformity": "tidak sesuai (nonconformity)"
  },
  "shared_accounts": [
    {
      "account": "8801234567",
      "vendors": [
        "PT Elektrikal Nusantara Jaya",
        "PT Kaca Bangun Persada"
      ]
    }
  ]
};
