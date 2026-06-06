#!/usr/bin/env python3

import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "results", "raw_data_stress.csv")
OUT_DIR = os.path.join(BASE_DIR, "figures_stress")

os.makedirs(OUT_DIR, exist_ok=True)

if not os.path.exists(DATA_FILE):
    print(f"[HATA] Dosya bulunamadı: {DATA_FILE}")
    print("Önce stres testini çalıştır:")
    print("  sudo bash run_stress.sh")
    raise SystemExit(1)

df = pd.read_csv(DATA_FILE)

# Ortalama değerler
g = (
    df.groupby(["protocol", "speed_ms", "txpower_dbm", "rssi_label"])
      [["pdr_pct", "avg_delay_ms", "throughput_mbps",
        "jitter_ms", "routing_overhead_pkts", "avg_rssi_dbm"]]
      .mean()
      .reset_index()
)

g["protocol_label"] = g["protocol"].str.upper()

tx_order = sorted(g["txpower_dbm"].unique(), reverse=True)
protocols = sorted(g["protocol"].unique())


def savefig(name):
    path = os.path.join(OUT_DIR, name)
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[✓] Kaydedildi: {path}")


# ------------------------------------------------------------
# 1. PDR vs Speed
# ------------------------------------------------------------
plt.figure(figsize=(10, 6))

for proto in protocols:
    for txp in tx_order:
        sub = g[(g["protocol"] == proto) & (g["txpower_dbm"] == txp)]
        if sub.empty:
            continue
        label = f"{proto.upper()} - {txp} dBm"
        plt.plot(sub["speed_ms"], sub["pdr_pct"], marker="o", label=label)

plt.axhline(70, linestyle="--", linewidth=1, label="Breaking threshold: 70%")
plt.title("Stres Senaryosu: Mobilite Hızına Göre PDR")
plt.xlabel("Mobilite hızı (m/s)")
plt.ylabel("PDR (%)")
plt.ylim(0, 105)
plt.grid(True, alpha=0.3)
plt.legend(fontsize=8)
savefig("01_stress_pdr_vs_speed.png")


# ------------------------------------------------------------
# 2. Throughput vs Speed
# ------------------------------------------------------------
plt.figure(figsize=(10, 6))

for proto in protocols:
    for txp in tx_order:
        sub = g[(g["protocol"] == proto) & (g["txpower_dbm"] == txp)]
        if sub.empty:
            continue
        label = f"{proto.upper()} - {txp} dBm"
        plt.plot(sub["speed_ms"], sub["throughput_mbps"], marker="o", label=label)

plt.title("Stres Senaryosu: Mobilite Hızına Göre Throughput")
plt.xlabel("Mobilite hızı (m/s)")
plt.ylabel("Throughput (Mbps)")
plt.grid(True, alpha=0.3)
plt.legend(fontsize=8)
savefig("02_stress_throughput_vs_speed.png")


# ------------------------------------------------------------
# 3. Delay vs Speed
# ------------------------------------------------------------
plt.figure(figsize=(10, 6))

for proto in protocols:
    for txp in tx_order:
        sub = g[(g["protocol"] == proto) & (g["txpower_dbm"] == txp)]
        if sub.empty:
            continue
        label = f"{proto.upper()} - {txp} dBm"
        plt.plot(sub["speed_ms"], sub["avg_delay_ms"], marker="o", label=label)

plt.title("Stres Senaryosu: Mobilite Hızına Göre Ortalama Gecikme")
plt.xlabel("Mobilite hızı (m/s)")
plt.ylabel("Ortalama gecikme (ms)")
plt.grid(True, alpha=0.3)
plt.legend(fontsize=8)
savefig("03_stress_delay_vs_speed.png")


# ------------------------------------------------------------
# 4. Routing overhead vs Speed
# ------------------------------------------------------------
plt.figure(figsize=(10, 6))

for proto in protocols:
    for txp in tx_order:
        sub = g[(g["protocol"] == proto) & (g["txpower_dbm"] == txp)]
        if sub.empty:
            continue
        label = f"{proto.upper()} - {txp} dBm"
        plt.plot(sub["speed_ms"], sub["routing_overhead_pkts"], marker="o", label=label)

plt.title("Stres Senaryosu: Routing Overhead Karşılaştırması")
plt.xlabel("Mobilite hızı (m/s)")
plt.ylabel("Ortalama routing overhead (paket)")
plt.grid(True, alpha=0.3)
plt.legend(fontsize=8)
savefig("04_stress_overhead_vs_speed.png")


# ------------------------------------------------------------
# 5. PDR heatmap: protocol + txpower rows, speed columns
# ------------------------------------------------------------
heat = g.copy()
heat["row_label"] = heat["protocol"].str.upper() + " / " + heat["txpower_dbm"].astype(str) + " dBm"

pivot = heat.pivot_table(
    index="row_label",
    columns="speed_ms",
    values="pdr_pct",
    aggfunc="mean"
)

plt.figure(figsize=(9, 5))
plt.imshow(pivot.values, aspect="auto")

plt.colorbar(label="PDR (%)")
plt.xticks(range(len(pivot.columns)), [f"{c:g}" for c in pivot.columns])
plt.yticks(range(len(pivot.index)), pivot.index)
plt.title("Stres Senaryosu: PDR Heatmap")
plt.xlabel("Mobilite hızı (m/s)")
plt.ylabel("Protokol / TxPower")

for i in range(pivot.shape[0]):
    for j in range(pivot.shape[1]):
        val = pivot.values[i, j]
        plt.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=8)

savefig("05_stress_pdr_heatmap.png")


# ------------------------------------------------------------
# 6. Summary table image
# ------------------------------------------------------------
summary = g[[
    "protocol", "speed_ms", "txpower_dbm", "rssi_label",
    "pdr_pct", "avg_delay_ms", "throughput_mbps",
    "jitter_ms", "routing_overhead_pkts", "avg_rssi_dbm"
]].copy()

summary = summary.round({
    "pdr_pct": 2,
    "avg_delay_ms": 2,
    "throughput_mbps": 3,
    "jitter_ms": 2,
    "routing_overhead_pkts": 2,
    "avg_rssi_dbm": 1
})

summary["breaking_status"] = summary["pdr_pct"].apply(
    lambda x: "KIRILMA" if x < 70 else ("BOZULMA" if x < 90 else "DAYANIKLI")
)

fig, ax = plt.subplots(figsize=(14, 5))
ax.axis("off")

table = ax.table(
    cellText=summary.values,
    colLabels=summary.columns,
    loc="center",
    cellLoc="center"
)

table.auto_set_font_size(False)
table.set_fontsize(7)
table.scale(1, 1.4)

plt.title("Stres Senaryosu Ortalama Sonuç Tablosu", fontsize=12, pad=15)
savefig("06_stress_summary_table.png")


# ------------------------------------------------------------
# Text summary
# ------------------------------------------------------------
print("\n============================================================")
print(" STRES ÖZETİ")
print("============================================================")
print(summary.to_string(index=False))

print("\nPDR < 70 kırılma koşulları:")
breaks = summary[summary["pdr_pct"] < 70]
if breaks.empty:
    print("Bu stres setinde PDR < 70 kırılma koşulu yok.")
else:
    print(breaks[["protocol", "speed_ms", "txpower_dbm", "rssi_label", "pdr_pct"]].to_string(index=False))

print(f"\n[✓] Tüm stres grafikleri: {OUT_DIR}")