// Merender dashboard dari DATA pada data.js (hasil analisis nyata).
(function () {
  const fmtRp = (n) => "Rp" + n.toLocaleString("id-ID");

  const cards = [
    { value: DATA.total_invoices, label: "Invoice dianalisis" },
    { value: DATA.total_vendors, label: "Vendor" },
    { value: DATA.total_pos, label: "Purchase order" },
    { value: fmtRp(DATA.total_amount), label: "Total nilai tagihan" },
    { value: DATA.status_counts["TAHAN BAYAR"], label: "Invoice TAHAN BAYAR" },
  ];
  document.getElementById("summary-cards").innerHTML = cards
    .map((c) => `<div class="card"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`)
    .join("");

  const statusStyle = { "BERSIH": "good", "PERINGATAN": "warn", "TAHAN BAYAR": "bad" };
  const maxStatus = Math.max(...Object.values(DATA.status_counts));
  document.getElementById("status-bars").innerHTML = Object.entries(DATA.status_counts)
    .map(([status, count]) => `
      <div class="bar-row">
        <div class="bar-label">${status}</div>
        <div class="bar-track"><div class="bar-fill ${statusStyle[status]}" style="width:${(count / maxStatus) * 100}%"></div></div>
        <div class="bar-count">${count} invoice</div>
      </div>`)
    .join("");

  const maxFinding = Math.max(...DATA.findings_by_type.map((r) => r.invoices));
  document.getElementById("finding-bars").innerHTML = DATA.findings_by_type
    .map((r) => `
      <div class="bar-row">
        <div class="bar-label">${r.label}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${(r.invoices / maxFinding) * 100}%"></div></div>
        <div class="bar-count">${r.invoices} invoice</div>
      </div>`)
    .join("");

  const riskClass = (risk) => (risk >= 40 ? "high" : risk >= 25 ? "mid" : "");
  document.querySelector("#vendor-table tbody").innerHTML = DATA.vendor_ranking
    .map((v, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${v.name}</td>
        <td><span class="risk-chip ${riskClass(v.risk)}">${v.risk}</span></td>
        <td class="num">${v.invoice_count}</td>
        <td class="num">${fmtRp(v.total_amount)}</td>
        <td class="num">${v.findings}</td>
        <td class="num">${v.tahan_bayar}</td>
        <td>${v.shared_account ? "ya" : "tidak"}</td>
      </tr>`)
    .join("");

  document.querySelector("#tahan-table tbody").innerHTML = DATA.tahan_bayar
    .map((t) => `
      <tr>
        <td>${t.invoice_no}</td>
        <td>${t.vendor}</td>
        <td>${t.date}</td>
        <td class="num">${fmtRp(t.total)}</td>
        <td class="num">${t.score}</td>
        <td>${t.findings.join("; ")}</td>
      </tr>`)
    .join("");

  const notes = [];
  const b = DATA.benford;
  notes.push(`Uji Benford atas ${b.n} invoice: chi-square ${b.chi_square}, MAD ${b.mad}, kesesuaian ${b.conformity}.`);
  DATA.shared_accounts.forEach((g) => {
    notes.push(`Rekening ${g.account} dipakai bersama oleh ${g.vendors.join(" dan ")}.`);
  });
  document.getElementById("pattern-notes").innerHTML = notes
    .map((n) => `<div class="note-box">${n}</div>`)
    .join("");
})();
