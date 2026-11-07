"""Hasilkan empat visual README dari angka analisis nyata ke docs/img:
- temuan-per-jenis.png    : jumlah invoice tertandai per jenis pemeriksaan
- benford.png             : distribusi digit pertama aktual vs harapan Benford
- distribusi-skor.png     : histogram skor risiko invoice
- arsitektur.png          : diagram lima tahap cara kerja agent
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import checks
import loader
import scoring
from scoring import CHECK_LABELS

BASE = Path(__file__).resolve().parent
OUT = BASE / "docs" / "img"
NAVY = "#12355b"
ORANGE = "#e8871e"


def chart_findings(analysis):
    by_type = analysis.findings_by_type()
    rows = []
    for check_type, label in CHECK_LABELS.items():
        invs = {f.invoice_id for f in by_type.get(check_type, []) if f.invoice_id}
        if invs:
            rows.append((label, len(invs)))
    rows.sort(key=lambda r: r[1])
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bars = ax.barh(labels, values, color=NAVY)
    bars[-1].set_color(ORANGE)
    for bar, value in zip(bars, values):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                str(value), va="center", fontsize=10)
    ax.set_xlabel("Jumlah invoice tertandai")
    ax.set_title("Temuan per jenis pemeriksaan", color=NAVY, fontsize=13, weight="bold")
    ax.set_xlim(0, max(values) * 1.18)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "temuan-per-jenis.png", dpi=130)
    plt.close(fig)


def chart_benford(analysis):
    stats = analysis.benford_dataset
    digits = list(range(1, 10))
    actual = [stats["actual"][d] * 100 for d in digits]
    expected = [stats["expected"][d] * 100 for d in digits]
    x = range(len(digits))
    width = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar([i - width / 2 for i in x], actual, width=width, color=NAVY, label="Aktual")
    ax.bar([i + width / 2 for i in x], expected, width=width, color=ORANGE, label="Harapan Benford")
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(d) for d in digits])
    ax.set_xlabel("Digit pertama nominal invoice")
    ax.set_ylabel("Proporsi (%)")
    ax.set_title(f"Uji Benford atas {stats['n']} invoice (MAD {stats['mad']:.4f}, "
                 f"chi-square {stats['chi_square']:.2f})",
                 color=NAVY, fontsize=12, weight="bold")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "benford.png", dpi=130)
    plt.close(fig)


def chart_scores(scores):
    values = [s.score for s in scores.values()]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 101]
    ax.hist(values, bins=bins, color=NAVY, edgecolor="white")
    ax.axvline(30, color=ORANGE, linestyle="--", linewidth=1.6, label="Ambang PERINGATAN (30)")
    ax.axvline(60, color="#b3261e", linestyle="--", linewidth=1.6, label="Ambang TAHAN BAYAR (60)")
    ax.set_xlabel("Skor risiko invoice")
    ax.set_ylabel("Jumlah invoice")
    ax.set_title("Distribusi skor risiko invoice", color=NAVY, fontsize=13, weight="bold")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "distribusi-skor.png", dpi=130)
    plt.close(fig)


def chart_architecture():
    stages = [
        ("1. Dokumen", "PO, BAST, dan invoice\ndibaca dari CSV dan JSON"),
        ("2. Pencocokan", "Three-way match per item:\nharga, qty PO, qty terima"),
        ("3. Pemeriksaan", "9 pemeriksaan fraud dan\nselisih plus pola vendor"),
        ("4. Skor risiko", "Bobot temuan menjadi skor\n0 sampai 100 dan status"),
        ("5. Laporan + AI", "Laporan Markdown, insight,\npertanyaan klarifikasi"),
    ]
    fig, ax = plt.subplots(figsize=(11, 2.9))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 2.9)
    ax.axis("off")
    for i, (title, desc) in enumerate(stages):
        x = 0.25 + i * 2.14
        box = FancyBboxPatch((x, 0.75), 1.95, 1.45,
                             boxstyle="round,pad=0.06,rounding_size=0.08",
                             facecolor=NAVY if i % 2 == 0 else "white",
                             edgecolor=NAVY, linewidth=1.4)
        ax.add_patch(box)
        text_color = "white" if i % 2 == 0 else NAVY
        ax.text(x + 0.975, 1.78, title, ha="center", va="center",
                fontsize=10.5, weight="bold", color=text_color)
        ax.text(x + 0.975, 1.18, desc, ha="center", va="center",
                fontsize=7.6, color=text_color)
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + 2.12, 1.48), xytext=(x + 1.97, 1.48),
                        arrowprops=dict(arrowstyle="->", color=ORANGE, lw=2))
    ax.set_title("Arsitektur Invoice Fraud & Three-Way Match Agent",
                 color=NAVY, fontsize=13, weight="bold", pad=10)
    fig.tight_layout()
    fig.savefig(OUT / "arsitektur.png", dpi=130)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dataset = loader.load_dataset(BASE / "samples")
    analysis = checks.run_checks(dataset)
    scores = scoring.score_invoices(dataset, analysis)
    chart_findings(analysis)
    chart_benford(analysis)
    chart_scores(scores)
    chart_architecture()
    print("Visual ditulis ke docs/img/: temuan-per-jenis.png, benford.png, "
          "distribusi-skor.png, arsitektur.png")


if __name__ == "__main__":
    main()
