#!/usr/bin/env python3

import os
import sys
import argparse
import warnings
import numpy  as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
warnings.filterwarnings("ignore")

FIGURES_DIR   = os.path.join(os.path.dirname(__file__), "figures")
DEFAULT_INPUT = os.path.join(os.path.dirname(__file__), "results", "raw_data.csv")

PDR_THRESHOLD = 70.0        # % — breaking point eşiği
DELAY_THR     = 150.0       # ms — kabul edilebilir maksimum gecikme

SPEED_LABELS  = {1: "Yavaş\n(1 m/s)", 5: "Orta\n(5 m/s)", 10: "Hızlı\n(10 m/s)"}
RSSI_ORDER    = ["Yuksek_RSSI", "Orta_RSSI", "Dusuk_RSSI"]
RSSI_LABELS_TR= {"Yuksek_RSSI": "Yüksek RSSI\n(txp=20 dBm)",
                  "Orta_RSSI":  "Orta RSSI\n(txp=15 dBm)",
                  "Dusuk_RSSI": "Düşük RSSI\n(txp=10 dBm)"}

PROTO_COLORS  = {"aodv": "#E74C3C", "olsrd": "#2980B9"}
RSSI_MARKERS  = {"Yuksek_RSSI": "o", "Orta_RSSI": "s", "Dusuk_RSSI": "^"}
RSSI_LS       = {"Yuksek_RSSI": "-",  "Orta_RSSI": "--", "Dusuk_RSSI": ":"}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "figure.dpi": 120,
})

# ─── Veri yükleme & ön işleme ──────────────────────────────────────────────────

def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        print(f"[HATA] Veri dosyası bulunamadı: {path}")
        print("  Önce simülasyonu çalıştırın: sudo bash run_all.sh")
        sys.exit(1)

    df = pd.read_csv(path)
    required = {"protocol", "speed_ms", "txpower_dbm", "rssi_label",
                "pdr_pct", "avg_delay_ms", "throughput_mbps"}
    missing = required - set(df.columns)
    if missing:
        print(f"[HATA] CSV'de eksik sütunlar: {missing}")
        sys.exit(1)

    # Ortalama: aynı (protocol, speed, txpower) için tüm run'ların ortalaması
    agg = df.groupby(["protocol", "speed_ms", "txpower_dbm", "rssi_label"]).agg(
        pdr_pct=("pdr_pct", "mean"),
        avg_delay_ms=("avg_delay_ms", "mean"),
        throughput_mbps=("throughput_mbps", "mean"),
        jitter_ms=("jitter_ms", "mean"),
        routing_overhead_pkts=("routing_overhead_pkts", "mean"),
        avg_rssi_dbm=("avg_rssi_dbm", "mean"),
        min_rssi_dbm=("min_rssi_dbm", "mean"),
        max_rssi_dbm=("max_rssi_dbm", "mean"),
        n_runs=("run", "count")
    ).reset_index()

    # RSSI kategorik sıra
    agg["rssi_cat"] = pd.Categorical(
        agg["rssi_label"], categories=RSSI_ORDER, ordered=True
    )
    agg = agg.sort_values(["protocol", "rssi_cat", "speed_ms"])
    print(f"[Veri] {len(df)} ham satır yüklendi → {len(agg)} ortalama nokta")
    return agg


# ─── Grafik 1 — PDR vs Mobilite Hızı ─────────────────────────────────────────

def plot_pdr_vs_speed(df: pd.DataFrame, out_dir: str):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    fig.suptitle("Paket Teslim Oranı (PDR) — Mobilite Hızı vs RSSI",
                 fontsize=14, fontweight="bold", y=1.01)

    for ax, rssi in zip(axes, RSSI_ORDER):
        sub = df[df["rssi_label"] == rssi]
        for proto in ["aodv", "olsrd"]:
            d = sub[sub["protocol"] == proto].sort_values("speed_ms")
            if d.empty:
                continue
            ax.plot(d["speed_ms"], d["pdr_pct"],
                    color=PROTO_COLORS[proto], marker="o",
                    label=proto.upper(), linewidth=2, markersize=8)
            for idx, (_, row) in enumerate(d.iterrows()):
                y_offset = 10 if proto == "aodv" else -18
                ax.annotate(f"{row.pdr_pct:.1f}%",
                            (row.speed_ms, row.pdr_pct),
                            textcoords="offset points", xytext=(-12 if proto=="olsrd" else 12, y_offset),
                            ha="center", fontsize=8, color=PROTO_COLORS[proto],
                            fontweight="bold")

        ax.axhline(PDR_THRESHOLD, color="gray", linestyle="--",
                   linewidth=1, label=f"Eşik ({PDR_THRESHOLD}%)")
        ax.axhspan(0, PDR_THRESHOLD, alpha=0.05, color="red")
        ax.set_title(RSSI_LABELS_TR[rssi])
        ax.set_xlabel("Mobilite Hızı (m/s)")
        ax.set_xticks([1, 5, 10])
        ax.set_ylim(0, 105)
        ax.set_yticks(range(0, 110, 10))
        ax.grid(True, alpha=0.3)
        ax.legend()

    axes[0].set_ylabel("PDR (%)")
    plt.tight_layout()
    path = os.path.join(out_dir, "01_pdr_vs_speed.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {path}")


# ─── Grafik 2 — Gecikme vs Mobilite Hızı ──────────────────────────────────────

def plot_delay_vs_speed(df: pd.DataFrame, out_dir: str):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    fig.suptitle("Uçtan Uca Gecikme — Mobilite Hızı vs RSSI",
                 fontsize=14, fontweight="bold", y=1.01)

    for ax, rssi in zip(axes, RSSI_ORDER):
        sub = df[df["rssi_label"] == rssi]
        for proto in ["aodv", "olsrd"]:
            d = sub[sub["protocol"] == proto].sort_values("speed_ms")
            if d.empty:
                continue
            ax.plot(d["speed_ms"], d["avg_delay_ms"],
                    color=PROTO_COLORS[proto], marker="s",
                    label=proto.upper(), linewidth=2, markersize=8)
            for _, row in d.iterrows():
                y_offset = 10 if proto == "aodv" else -18
                ax.annotate(f"{row.avg_delay_ms:.1f}",
                            (row.speed_ms, row.avg_delay_ms),
                            textcoords="offset points", xytext=(-10 if proto=="olsrd" else 10, y_offset),
                            ha="center", fontsize=8, color=PROTO_COLORS[proto],
                            fontweight="bold")

        ax.axhline(DELAY_THR, color="orange", linestyle="--",
                   linewidth=1, label=f"Eşik ({DELAY_THR} ms)")
        ax.set_title(RSSI_LABELS_TR[rssi])
        ax.set_xlabel("Mobilite Hızı (m/s)")
        ax.set_xticks([1, 5, 10])
        ax.grid(True, alpha=0.3)
        ax.legend()

    axes[0].set_ylabel("Ortalama Gecikme (ms)")
    plt.tight_layout()
    path = os.path.join(out_dir, "02_delay_vs_speed.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {path}")


# ─── Grafik 3b — Routing Overhead vs Mobilite Hızı ───────────────────────────

def plot_overhead_vs_speed(df: pd.DataFrame, out_dir: str):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    fig.suptitle(
        "Yönlendirme Yükü (Routing Overhead) — Mobilite Hızı vs RSSI\n"
        "AODV: reaktif RREQ/RREP/RERR + broadcast | OLSR: proaktif HELLO/TC mesajları",
        fontsize=13, fontweight="bold", y=1.03
    )

    for ax, rssi in zip(axes, RSSI_ORDER):
        sub = df[df["rssi_label"] == rssi]
        for proto in ["aodv", "olsrd"]:
            d = sub[sub["protocol"] == proto].sort_values("speed_ms")
            if d.empty or "routing_overhead_pkts" not in d.columns:
                continue
            ax.plot(d["speed_ms"], d["routing_overhead_pkts"],
                    color=PROTO_COLORS[proto], marker="D",
                    label=proto.upper(), linewidth=2, markersize=8)
            for _, row in d.iterrows():
                ax.annotate(f"{row.routing_overhead_pkts:.0f}",
                            (row.speed_ms, row.routing_overhead_pkts),
                            textcoords="offset points", xytext=(0, 8),
                            ha="center", fontsize=9, color=PROTO_COLORS[proto])

        ax.set_title(RSSI_LABELS_TR[rssi])
        ax.set_xlabel("Mobilite Hızı (m/s)")
        ax.set_xticks([1, 5, 10])
        ax.grid(True, alpha=0.3)
        ax.legend()

    axes[0].set_ylabel("Yönlendirme Paketi Sayısı (10 sn)")
    plt.tight_layout()
    path = os.path.join(out_dir, "03b_overhead_vs_speed.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {path}")


# ─── Grafik 3 — Throughput vs Mobilite Hızı ───────────────────────────────────

def plot_throughput_vs_speed(df: pd.DataFrame, out_dir: str):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    fig.suptitle("Throughput — Mobilite Hızı vs RSSI",
                 fontsize=14, fontweight="bold", y=1.01)

    for ax, rssi in zip(axes, RSSI_ORDER):
        sub = df[df["rssi_label"] == rssi]
        for proto in ["aodv", "olsrd"]:
            d = sub[sub["protocol"] == proto].sort_values("speed_ms")
            if d.empty:
                continue
            ax.bar(
                np.array([1, 5, 10]) + (0.3 if proto == "olsrd" else -0.3),
                d.set_index("speed_ms").reindex([1, 5, 10])["throughput_mbps"],
                width=0.55, color=PROTO_COLORS[proto], alpha=0.85,
                label=proto.upper()
            )

        ax.set_title(RSSI_LABELS_TR[rssi])
        ax.set_xlabel("Mobilite Hızı (m/s)")
        ax.set_xticks([1, 5, 10])
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend()

    axes[0].set_ylabel("Throughput (Mbps)")
    plt.tight_layout()
    path = os.path.join(out_dir, "03_throughput_vs_speed.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {path}")


# ─── Grafik 4 — PDR Isı Haritaları ────────────────────────────────────────────

def plot_pdr_heatmaps(df: pd.DataFrame, out_dir: str):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("PDR (%) Isı Haritası — Hız × RSSI",
                 fontsize=14, fontweight="bold")

    cmap = LinearSegmentedColormap.from_list(
        "pdr", ["#2C3E50", "#2980B9", "#AED6F1", "#F8F9FA", "#F5B7B1", "#E74C3C", "#922B21"],
        N=256
    )

    for ax, proto in zip(axes, ["aodv", "olsrd"]):
        sub = df[df["protocol"] == proto]
        pivot = sub.pivot_table(
            index="rssi_label", columns="speed_ms",
            values="pdr_pct", aggfunc="mean"
        ).reindex(RSSI_ORDER)

        if pivot.empty:
            ax.set_title(f"{proto.upper()} — Veri Yok")
            continue

        im = ax.imshow(pivot.values, cmap=cmap, vmin=30, vmax=100, aspect="auto")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f"{v} m/s" for v in pivot.columns])
        ax.set_yticks(range(len(RSSI_ORDER)))
        ax.set_yticklabels([RSSI_LABELS_TR.get(r, r) for r in RSSI_ORDER])
        ax.set_title(f"{proto.upper()}", fontsize=14, fontweight="bold", pad=10)
        ax.set_xlabel("Mobilite Hızı")
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)

        for i in range(len(RSSI_ORDER)):
            for j in range(len(pivot.columns)):
                val = pivot.values[i, j]
                if not np.isnan(val):
                    below = val < PDR_THRESHOLD
                    txt = f"{val:.1f}%"
                    suffix = "\n⚠ BP" if below else ""
                    text_color = "white" if (val < 55 or val > 85) else "#1A252F"
                    ax.text(j, i, txt + suffix, ha="center", va="center",
                            color=text_color, fontsize=11, fontweight="bold",
                            linespacing=1.4)

        plt.colorbar(im, ax=ax, label="PDR (%)", fraction=0.046, pad=0.04)

    plt.tight_layout()
    path = os.path.join(out_dir, "04_pdr_heatmap.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {path}")


# ─── Grafik 5 — RSSI vs Throughput & PDR ─────────────────────────────

def plot_rssi_vs_metrics(df: pd.DataFrame, out_dir: str):
    if "avg_rssi_dbm" not in df.columns:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "Gerçek RSSI (dBm) vs Performans Metrikleri\n"
        "Mininet-WiFi'dan `iw dev` komutuyla ölçülmüştür",
        fontsize=13, fontweight="bold", y=1.02
    )

    for proto in ["aodv", "olsrd"]:
        sub = df[df["protocol"] == proto].sort_values("avg_rssi_dbm")
        if sub.empty:
            continue
        col = PROTO_COLORS[proto]

        # PDR vs RSSI
        ax1.scatter(sub["avg_rssi_dbm"], sub["pdr_pct"],
                    color=col, alpha=0.7, s=80, label=proto.upper())
        ax1.plot(sub["avg_rssi_dbm"], sub["pdr_pct"],
                 color=col, linewidth=1.5, linestyle="--", alpha=0.5)

        # Throughput vs RSSI
        ax2.scatter(sub["avg_rssi_dbm"], sub["throughput_mbps"],
                    color=col, alpha=0.7, s=80, label=proto.upper())
        ax2.plot(sub["avg_rssi_dbm"], sub["throughput_mbps"],
                 color=col, linewidth=1.5, linestyle="--", alpha=0.5)

    ax1.axhline(PDR_THRESHOLD, color="gray", linestyle="--", linewidth=1,
                label=f"Eşik ({PDR_THRESHOLD}%)")
    ax1.set_xlabel("Ortalama RSSI (dBm)"); ax1.set_ylabel("PDR (%)")
    ax1.set_title("RSSI vs PDR"); ax1.legend(); ax1.grid(True, alpha=0.3)
    ax1.invert_xaxis()   # dBm: sola gidince sinyal zayıflar

    ax2.set_xlabel("Ortalama RSSI (dBm)"); ax2.set_ylabel("Throughput (Mbps)")
    ax2.set_title("RSSI vs Throughput"); ax2.legend(); ax2.grid(True, alpha=0.3)
    ax2.invert_xaxis()

    plt.tight_layout()
    path = os.path.join(out_dir, "07_rssi_vs_metrics.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {path}")


# ─── Breaking Point Analizi ────────────────────────────────────────────────────

def find_breaking_points(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for proto in ["aodv", "olsrd"]:
        for rssi in RSSI_ORDER:
            sub = df[(df["protocol"] == proto) & (df["rssi_label"] == rssi)]
            sub = sub.sort_values("speed_ms")
            bp_speed = None
            for _, row in sub.iterrows():
                if row["pdr_pct"] < PDR_THRESHOLD:
                    bp_speed = row["speed_ms"]
                    break
            rows.append({
                "Protokol": proto.upper(),
                "RSSI Seviyesi": RSSI_LABELS_TR.get(rssi, rssi),
                "Kırılma Noktası (m/s)": bp_speed if bp_speed else "> 10",
                "PDR@1m/s": f"{sub[sub.speed_ms==1]['pdr_pct'].values[0]:.1f}%"
                    if not sub[sub.speed_ms==1].empty else "—",
                "PDR@5m/s": f"{sub[sub.speed_ms==5]['pdr_pct'].values[0]:.1f}%"
                    if not sub[sub.speed_ms==5].empty else "—",
                "PDR@10m/s": f"{sub[sub.speed_ms==10]['pdr_pct'].values[0]:.1f}%"
                    if not sub[sub.speed_ms==10].empty else "—",
            })
    return pd.DataFrame(rows)


def plot_breaking_point_table(bp_df: pd.DataFrame, out_dir: str):
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.axis("off")
    fig.suptitle(
        f"Breaking Point Analizi (PDR < {PDR_THRESHOLD}% eşiği)\n"
        "Kırmızı hücreler kırılma noktasını gösterir",
        fontsize=13, fontweight="bold"
    )

    cols = bp_df.columns.tolist()
    table = ax.table(
        cellText=bp_df.values,
        colLabels=cols,
        cellLoc="center",
        loc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 2.0)

    # Başlık satırı rengi
    for j in range(len(cols)):
        table[0, j].set_facecolor("#2C3E50")
        table[0, j].set_text_props(color="white", fontweight="bold")

    for i in range(1, len(bp_df) + 1):
        row_color = "#EBF5FB" if i % 2 == 0 else "white"
        for j in range(len(cols)):
            table[i, j].set_facecolor(row_color)

        bp_val = bp_df.iloc[i - 1]["Kırılma Noktası (m/s)"]
        if bp_val != "> 10":
            table[i, 2].set_facecolor("#FADBD8")
            table[i, 2].set_text_props(color="#C0392B", fontweight="bold")

    plt.tight_layout()
    path = os.path.join(out_dir, "05_breaking_point_table.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {path}")


# ─── Adaptif Protokol Seçim Matrisi ───────────────────────────────────────────

def build_selection_matrix(df: pd.DataFrame) -> dict:
    """
    Her (speed, rssi) kombinasyonu için hangi protokolün daha yüksek PDR
    ürettiğini belirle. Eşitlik durumunda gecikmeye bak.
    """
    matrix = {}
    for speed in [1, 5, 10]:
        for rssi in RSSI_ORDER:
            sub = df[(df["speed_ms"] == speed) & (df["rssi_label"] == rssi)]
            if sub.empty:
                matrix[(speed, rssi)] = "—"
                continue
            aodv_pdr  = sub[sub.protocol == "aodv"]["pdr_pct"].values
            olsrd_pdr = sub[sub.protocol == "olsrd"]["pdr_pct"].values

            if not len(aodv_pdr) or not len(olsrd_pdr):
                matrix[(speed, rssi)] = "—"
                continue

            diff = aodv_pdr[0] - olsrd_pdr[0]
            if abs(diff) < 3.0:          
                aodv_d  = sub[sub.protocol == "aodv"]["avg_delay_ms"].values[0]
                olsrd_d = sub[sub.protocol == "olsrd"]["avg_delay_ms"].values[0]
                winner = "AODV" if aodv_d <= olsrd_d else "OLSR"
            else:
                winner = "AODV" if diff > 0 else "OLSR"

            both_bad = aodv_pdr[0] < PDR_THRESHOLD and olsrd_pdr[0] < PDR_THRESHOLD
            matrix[(speed, rssi)] = f"[ZAYIF]\n{winner}" if both_bad else winner

    return matrix


def plot_selection_matrix(matrix: dict, df: pd.DataFrame, out_dir: str):
    speeds = [1, 5, 10]
    rssis  = RSSI_ORDER

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(-0.5, len(speeds) - 0.5)
    ax.set_ylim(-0.5, len(rssis) - 0.5)
    ax.set_xticks(range(len(speeds)))
    ax.set_xticklabels([f"Yavaş\n(1 m/s)", "Orta\n(5 m/s)", "Hızlı\n(10 m/s)"],
                       fontsize=12)
    ax.set_yticks(range(len(rssis)))
    ax.set_yticklabels([RSSI_LABELS_TR.get(r, r) for r in rssis], fontsize=11)
    ax.set_title("Adaptif Protokol Seçim Matrisi\n"
                 "(Veri odaklı — PDR ve gecikmeye göre)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Mobilite Hızı", fontsize=12)
    ax.set_ylabel("RSSI Seviyesi", fontsize=12)

    for xi, speed in enumerate(speeds):
        for yi, rssi in enumerate(rssis):
            winner = matrix.get((speed, rssi), "—")
            is_weak = "[ZAYIF]" in winner
            clean   = winner.replace("[ZAYIF]\n", "")

            if "AODV" in clean:
                color = "#FADBD8"
                border_color = "#E74C3C"
                text_color   = "#C0392B"
            elif "OLSR" in clean:
                color = "#D6EAF8"
                border_color = "#2980B9"
                text_color   = "#1A5276"
            else:
                color = "#F5F5F5"
                border_color = "#AAAAAA"
                text_color   = "#555555"

            if is_weak:
                color = "#FDFEFE"
                border_color = "#E74C3C"
                text_color   = "#E74C3C"

            rect = mpatches.FancyBboxPatch(
                (xi - 0.42, yi - 0.42), 0.84, 0.84,
                boxstyle="round,pad=0.05",
                facecolor=color, edgecolor=border_color, linewidth=2.5
            )
            ax.add_patch(rect)

            label = ("⚠ " if is_weak else "✓ ") + clean
            ax.text(xi, yi, label, ha="center", va="center",
                    fontsize=14, fontweight="bold", color=text_color)

            sub = df[(df["speed_ms"] == speed) & (df["rssi_label"] == rssi)]
            for proto in ["aodv", "olsrd"]:
                pdr_val = sub[sub.protocol == proto]["pdr_pct"].values
                if len(pdr_val):
                    offset_y = -0.28 if proto == "olsrd" else 0.22
                    col = PROTO_COLORS[proto]
                    ax.text(xi, yi + offset_y,
                            f"{proto.upper()} PDR: {pdr_val[0]:.1f}%",
                            ha="center", va="center", fontsize=8, color=col)

    # Lejant
    aodv_patch  = mpatches.Patch(color=PROTO_COLORS["aodv"],  label="AODV tercih edildi")
    olsrd_patch = mpatches.Patch(color=PROTO_COLORS["olsrd"], label="OLSR tercih edildi")
    weak_patch  = mpatches.Patch(color="#FDFEFE", edgecolor="#E74C3C",
                                  label=f"Her iki protokol PDR < {PDR_THRESHOLD}%")
    ax.legend(handles=[aodv_patch, olsrd_patch, weak_patch],
              loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)

    plt.tight_layout()
    path = os.path.join(out_dir, "06_protocol_matrix.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {path}")


# ─── Rapor özeti ──────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame, bp_df: pd.DataFrame, matrix: dict):
    print("\n" + "=" * 65)
    print("  ÖZET RAPOR — AODV vs OLSR Performans Karşılaştırması")
    print("=" * 65)

    for proto in ["aodv", "olsrd"]:
        sub = df[df["protocol"] == proto]
        print(f"\n  {proto.upper()}:")
        print(f"    Ortalama PDR         : {sub.pdr_pct.mean():.1f}%")
        print(f"    Ortalama Gecikme     : {sub.avg_delay_ms.mean():.1f} ms")
        print(f"    Ortalama Throughput  : {sub.throughput_mbps.mean():.3f} Mbps")

    print(f"\n  Breaking Point Eşiği: PDR < {PDR_THRESHOLD}%")
    print(bp_df.to_string(index=False))
    print("\n  Adaptif Seçim Matrisi:")
    for speed in [1, 5, 10]:
        for rssi in RSSI_ORDER:
            winner = matrix.get((speed, rssi), "—")
            print(f"    {speed:2d} m/s | {rssi:<18s} → {winner}")
    print("=" * 65)


# ─── Ana akış ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MANET Sonuç Analizi")
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help="Ham veri CSV dosyası")
    args = parser.parse_args()

    os.makedirs(FIGURES_DIR, exist_ok=True)

    print(f"[*] Veri yükleniyor: {args.input}")
    df = load_data(args.input)

    print("[*] Grafikler oluşturuluyor...")
    plot_pdr_vs_speed(df, FIGURES_DIR)
    plot_delay_vs_speed(df, FIGURES_DIR)
    plot_overhead_vs_speed(df, FIGURES_DIR)
    plot_throughput_vs_speed(df, FIGURES_DIR)
    plot_rssi_vs_metrics(df, FIGURES_DIR)
    plot_pdr_heatmaps(df, FIGURES_DIR)

    bp_df = find_breaking_points(df)
    plot_breaking_point_table(bp_df, FIGURES_DIR)

    matrix = build_selection_matrix(df)
    plot_selection_matrix(matrix, df, FIGURES_DIR)

    print_summary(df, bp_df, matrix)

    print(f"\n[✓] Tüm çıktılar: {FIGURES_DIR}/")


if __name__ == "__main__":
    main()
