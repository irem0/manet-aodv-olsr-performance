#!/usr/bin/env python3
"""
stress_summary.py — Stres testi hızlı sonuç özeti
502531022 - İrem İÇÖZ

Kullanım:
    python3 stress_summary.py

Okunan dosya:
    results/raw_data_stress.csv
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
STRESS_FILE = os.path.join(BASE_DIR, "results", "raw_data_stress.csv")

if not os.path.exists(STRESS_FILE):
    print(f"[HATA] Dosya bulunamadı: {STRESS_FILE}")
    print("Önce şunu çalıştır:")
    print("  sudo bash run_stress.sh")
    raise SystemExit(1)

df = pd.read_csv(STRESS_FILE)

print("\n============================================================")
print(" STRES TESTİ HAM SONUÇLAR")
print("============================================================")
print(df[[
    "protocol", "speed_ms", "txpower_dbm", "rssi_label", "run",
    "pdr_pct", "avg_delay_ms", "throughput_mbps", "jitter_ms",
    "routing_overhead_pkts", "avg_rssi_dbm"
]].to_string(index=False))

print("\n============================================================")
print(" PDR < 70 OLAN KIRILMA ADAYLARI")
print("============================================================")

break_df = df[df["pdr_pct"] < 70]

if break_df.empty:
    print("PDR < 70 olan satır yok. Bu stres aralığında da PDR tabanlı breaking point oluşmadı.")
else:
    print(break_df[[
        "protocol", "speed_ms", "txpower_dbm", "rssi_label", "run",
        "pdr_pct", "throughput_mbps", "avg_delay_ms"
    ]].to_string(index=False))

print("\n============================================================")
print(" ORTALAMA STRES SONUÇLARI")
print("============================================================")

summary = (
    df.groupby(["protocol", "speed_ms", "txpower_dbm", "rssi_label"])
      [["pdr_pct", "avg_delay_ms", "throughput_mbps", "jitter_ms",
        "routing_overhead_pkts", "avg_rssi_dbm"]]
      .mean()
      .round(2)
      .reset_index()
)

print(summary.to_string(index=False))

print("\n============================================================")
print(" KISA YORUM")
print("============================================================")

for _, row in summary.iterrows():
    proto = row["protocol"].upper()
    speed = row["speed_ms"]
    txp = row["txpower_dbm"]
    pdr = row["pdr_pct"]
    tp = row["throughput_mbps"]

    if pdr < 70:
        status = "KIRILMA VAR"
    elif pdr < 90:
        status = "PERFORMANS BOZULMASI VAR"
    else:
        status = "PDR DAYANIKLI"

    print(f"{proto} | hız={speed} m/s | txpower={txp} dBm | PDR={pdr}% | TP={tp} Mbps → {status}")