-- Rekap jumlah invoice dan nilai tagihan per status
SELECT status, COUNT(*) AS jumlah_invoice, SUM(total) AS total_nilai
FROM invoices
GROUP BY status
ORDER BY jumlah_invoice DESC;

-- Peringkat risiko vendor beserta jumlah invoice yang ditahan
SELECT v.vendor_id, v.name, v.risk_score,
       COUNT(i.invoice_id) AS jumlah_invoice,
       SUM(CASE WHEN i.status = 'TAHAN BAYAR' THEN 1 ELSE 0 END) AS tahan_bayar,
       SUM(i.total) AS total_nilai
FROM vendors v
LEFT JOIN invoices i ON i.vendor_id = v.vendor_id
GROUP BY v.vendor_id, v.name, v.risk_score
ORDER BY v.risk_score DESC;

-- Jumlah temuan per jenis pemeriksaan
SELECT check_type, COUNT(*) AS jumlah_temuan,
       COUNT(DISTINCT invoice_id) AS invoice_tertandai
FROM findings
WHERE invoice_id IS NOT NULL
GROUP BY check_type
ORDER BY jumlah_temuan DESC;

-- Daftar invoice TAHAN BAYAR beserta temuan terberatnya
SELECT i.invoice_no, i.vendor_id, i.total, i.score,
       GROUP_CONCAT(f.check_type, ', ') AS jenis_temuan
FROM invoices i
JOIN findings f ON f.invoice_id = i.invoice_id
WHERE i.status = 'TAHAN BAYAR'
GROUP BY i.invoice_id, i.invoice_no, i.vendor_id, i.total, i.score
ORDER BY i.score DESC, i.total DESC;

-- Vendor yang berbagi nomor rekening dengan vendor lain
SELECT bank_account, COUNT(*) AS jumlah_vendor, GROUP_CONCAT(name, '; ') AS nama_vendor
FROM vendors
WHERE bank_account IS NOT NULL AND bank_account <> ''
GROUP BY bank_account
HAVING COUNT(*) > 1;
