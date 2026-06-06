#!/usr/bin/env python3
"""
manet_sim.py — MANET AODV vs OLSR Performans Simülasyonu
Mininet-WiFi | Gerçek AODV-UU + Gerçek OLSR
502531022 - İrem İÇÖZ

Normal senaryo:
  300x250 m alan, orta yoğunluklu 6 düğümlü MANET topolojisi
  Hızlar: 1/5/10 m/s
  TxPower: 20/15/10 dBm
  Trafik: UDP 2 Mbps

Stres senaryo:
  450x300 m alan, daha seyrek ve çok-hop zincir benzeri MANET topolojisi
  Hızlar: 10/15/20 m/s
  TxPower: 10/8/5 dBm
  Trafik: UDP 2 Mbps

AODV:
  - ramonfontes/aodv-uu deposundan derlenen aodvd kullanılır.
  - kaodv kernel modülü kullanılır.
  - Rota keşfi ve bakım işlemleri AODV-UU tarafından yürütülür.

OLSR:
  - Mininet-WiFi proto='olsrd' ile gerçek olsrd daemon kullanılır.
  - HELLO/TC mesajları ve MPR mekanizması üzerinden proaktif yönlendirme yapılır.

Not:
  RSSI değerleri literatürden sabit alınmamıştır.
  TxPower deney parametresi olarak verilmiş, oluşan RSSI değerleri
  iw dev station dump çıktısından ölçülmüştür.
"""

import sys
import os
import time
import json
import csv
import re
import argparse
import subprocess
import shutil
from mininet.log import setLogLevel, info

try:
    from mn_wifi.net import Mininet_wifi
    from mn_wifi.link import adhoc, wmediumd
    from mn_wifi.wmediumdConnector import interference
except ImportError as e:
    print(f"[HATA] mn_wifi bulunamadı: {e}")
    sys.exit(1)


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
RESULTS_FILE = os.path.join(RESULTS_DIR, "raw_data.csv")
LOG_DIR = os.path.join(RESULTS_DIR, "debug_logs")

CSV_FIELDS = [
    "protocol", "speed_ms", "txpower_dbm", "rssi_label", "run",
    "pdr_pct", "avg_delay_ms", "throughput_mbps", "jitter_ms",
    "routing_overhead_pkts",
    "avg_rssi_dbm", "min_rssi_dbm", "max_rssi_dbm"
]

RSSI_LABELS = {
    20: "Yuksek_RSSI",
    15: "Orta_RSSI",
    10: "Dusuk_RSSI",
    8:  "Cok_Dusuk_RSSI",
    5:  "Asiri_Dusuk_RSSI"
}

CONVERGENCE_TIME = {
    "olsrd": 25,
    "aodv": 25
}

SCENARIO_CONFIGS = {
    "normal": {
        "area_x": 300,
        "area_y": 250,
        "positions": [
            (30, 40, 0),
            (130, 40, 0),
            (230, 40, 0),
            (30, 170, 0),
            (130, 170, 0),
            (230, 170, 0)
        ],
        "description": "Ana deney: 300x250 m, orta yoğunluklu 6 düğümlü MANET"
    },

    "stress": {
        "area_x": 450,
        "area_y": 300,
        "positions": [
            (30, 150, 0),
            (110, 150, 0),
            (190, 150, 0),
            (270, 150, 0),
            (350, 150, 0),
            (430, 150, 0)
        ],
        "description": "Stres deney: 450x300 m, çok-hop zincir MANET topolojisi"
    }
}

IPERF3_BIN = shutil.which("iperf3") or "/usr/bin/iperf3"


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def ensure_dirs():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()


def hard_clean():

    cmds = [
        "pkill -9 -x aodvd || true",
        "pkill -9 -x olsrd || true",
        "pkill -9 -x iperf3 || true",
        "pkill -9 -x tcpdump || true",
        "pkill -9 -x wmediumd || true",
    ]

    for cmd in cmds:
        sh(cmd)

    sh("modprobe -r kaodv 2>/dev/null || true")


def parse_ping(out):
    pdr = 0.0
    delay = 0.0

    m = re.search(r"(\d+) packets transmitted,\s*(\d+) received", out)
    if m:
        sent = int(m.group(1))
        recv = int(m.group(2))
        pdr = (recv / sent * 100) if sent else 0.0

    m = re.search(r"rtt min/avg/max/mdev\s*=\s*[\d.]+/([\d.]+)/", out)
    if m:
        delay = float(m.group(1))

    return round(pdr, 2), round(delay, 3)


def parse_iperf3(out):
    """
    iperf3 JSON sonucunu okur.
    PDR'ye göre yapay throughput üretmez.
    """
    try:
        if not out or "{" not in out:
            return 0.0, 0.0

        data = json.loads(out[out.find("{"):])
        end_data = data.get("end", {})

        summary = (
            end_data.get("sum_received")
            or end_data.get("sum")
            or end_data.get("sum_sent")
            or {}
        )

        throughput = summary.get("bits_per_second", 0) / 1e6
        jitter = summary.get("jitter_ms", 0)

        return round(throughput, 3), round(jitter, 3)

    except Exception:
        return 0.0, 0.0


def get_rssi(sta):
    """
    Ad-hoc modda iw dev link genelde Not connected döner.
    Bu yüzden station dump ile komşu peer sinyalleri okunur.
    """
    try:
        out = sta.cmd(f"iw dev {sta.name}-wlan0 station dump")
        sigs = re.findall(r"signal:\s*(-\d+)", out)
        if sigs:
            return int(sum(map(int, sigs)) / len(sigs))
    except Exception:
        pass

    return None


def count_file_lines(sta, path):
    out = sta.cmd(f"wc -l < {path} 2>/dev/null").strip()
    try:
        return int(out)
    except Exception:
        return 0


def start_aodv_daemons(stations):
    """
    Gerçek AODV-UU başlatma.
    kaodv kernel modülü + aodvd daemon kullanılır.
    """
    info("*** AODV-UU kernel modülü hazırlanıyor...\n")

    sh("pkill -9 -x aodvd || true")
    sh("modprobe -r kaodv 2>/dev/null || true")

    ifaces = ",".join([f"{sta.name}-wlan0" for sta in stations])

    mod = subprocess.run(
        ["modprobe", "kaodv", f"ifnames={ifaces}"],
        capture_output=True,
        text=True
    )

    if mod.returncode != 0:
        info("  ⚠ kaodv ifnames ile yüklenemedi, düz modprobe deneniyor...\n")
        subprocess.run(["modprobe", "kaodv"], capture_output=True)

    time.sleep(1)

    lsmod = sh("lsmod | grep kaodv || true").stdout.strip()
    if lsmod:
        info(f"  ✓ kaodv yüklü: {lsmod}\n")
    else:
        info("  ⚠ kaodv görünmüyor. AODV çalışmayabilir.\n")

    info("*** AODV-UU daemonları başlatılıyor...\n")

    for sta in stations:
        sta.cmd(f"rm -f /tmp/aodvd_{sta.name}.log")
        sta.cmd(
            f"/usr/local/sbin/aodvd "
            f"-i {sta.name}-wlan0 "
            f"-D -d -l -r 2 "
            f"> /tmp/aodvd_{sta.name}.log 2>&1"
        )

    time.sleep(5)

    proc_check = sh("ps aux | grep '[a]odvd' || true").stdout.strip()

    if proc_check:
        info("  ✓ AODV-UU daemon çalışıyor.\n")
        info(proc_check + "\n")
    else:
        info("  ⚠ AODV-UU daemon görünmüyor.\n")
        for sta in stations:
            log = sta.cmd(f"cat /tmp/aodvd_{sta.name}.log 2>/dev/null | tail -20")
            if log.strip():
                info(f"--- {sta.name} AODV log ---\n{log}\n")


def stop_runtime_processes():
    """
    net.stop() öncesi çağrılır.
    AODV daemonları wlan interface'lerini tutabildiği için önce süreçler kapatılır.
    """
    sh("pkill -9 -x iperf3 || true")
    sh("pkill -9 -x tcpdump || true")
    sh("pkill -9 -x aodvd || true")
    sh("pkill -9 -x olsrd || true")
    time.sleep(1)


def run_scenario(protocol, speed, txpower, runs=1, duration=10,
                 scenario="normal", bitrate="2M"):
    ensure_dirs()

    rssi_label = RSSI_LABELS.get(txpower, f"tx{txpower}dBm")
    cfg = SCENARIO_CONFIGS.get(scenario, SCENARIO_CONFIGS["normal"])

    area_x = cfg["area_x"]
    area_y = cfg["area_y"]
    positions = cfg["positions"]

    for run_id in range(1, runs + 1):
        info(f"\n[{protocol.upper()}] Hız: {speed} m/s | Güç: {txpower} dBm | Run: {run_id}/{runs}\n")
        info(f"*** Senaryo tipi: {scenario} — {cfg['description']}\n")
        info(f"*** Trafik yükü: UDP {bitrate}\n")

        hard_clean()

        net = None

        try:
            net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

            stations = []

            for i, pos in enumerate(positions, start=1):
                sta = net.addStation(
                    f"sta{i}",
                    ip=f"10.0.0.{i}/8",
                    position=f"{pos[0]},{pos[1]},{pos[2]}",
                    txpower=txpower,
                    antennaHeight=1.5,
                    antennaGain=5,
                    min_v=max(0.1, speed * 0.5),
                    max_v=speed,
                    min_x=0,
                    max_x=area_x,
                    min_y=0,
                    max_y=area_y
                )
                stations.append(sta)

            net.setPropagationModel(model="logDistance", exp=3.0)

            info("*** Düğümler yapılandırılıyor...\n")
            net.configureNodes()

            info("*** Mobilite modeli ayarlanıyor...\n")
            net.setMobilityModel(
                time=0,
                model="RandomWayPoint",
                max_x=area_x,
                max_y=area_y,
                min_v=max(0.1, speed * 0.5),
                max_v=speed,
                seed=42 + run_id + int(speed)
            )

            info("*** Ad-hoc linkler kuruluyor...\n")

            for sta in stations:
                if protocol == "olsrd":
                    net.addLink(
                        sta,
                        cls=adhoc,
                        intf=f"{sta.name}-wlan0",
                        ssid="manet502531022",
                        mode="g",
                        channel=6,
                        ht_cap="HT40+",
                        proto="olsrd"
                    )
                else:
                    net.addLink(
                        sta,
                        cls=adhoc,
                        intf=f"{sta.name}-wlan0",
                        ssid="manet502531022",
                        mode="g",
                        channel=6,
                        ht_cap="HT40+"
                    )

            info("*** Ağ başlatılıyor...\n")
            net.build()
            net.start()

            for i, sta in enumerate(stations, start=1):
                sta.setIP(f"10.0.0.{i}/8", intf=f"{sta.name}-wlan0")
                sta.cmd(f"ip link set {sta.name}-wlan0 up")
                sta.cmd("sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1")

            if protocol == "aodv":
                start_aodv_daemons(stations)

            conv = CONVERGENCE_TIME.get(protocol, 25)
            info(f"*** Rotaların oluşması bekleniyor ({conv}s)...\n")
            time.sleep(conv)

            if protocol == "olsrd":
                proc_check = sh("ps aux | grep '[o]lsrd' || true").stdout.strip()
                if proc_check:
                    info("  ✓ OLSR daemon çalışıyor.\n")
                else:
                    info("  ⚠ OLSR daemon görünmüyor.\n")

            if protocol == "aodv":
                proc_check = sh("ps aux | grep '[a]odvd' || true").stdout.strip()
                if proc_check:
                    info("  ✓ AODV-UU daemon çalışıyor.\n")
                else:
                    info("  ⚠ AODV-UU daemon görünmüyor.\n")

            src = stations[-1]
            dst = stations[0]
            dst_ip = dst.IP()

            info("*** Routing overhead dinlemesi başlatılıyor...\n")

            for sta in stations:
                sta.cmd(f"rm -f /tmp/{sta.name}_oh.txt")

                if protocol == "olsrd":
                    filt = "udp port 698"
                else:
                    filt = "udp port 654 or broadcast"

                sta.cmd(
                    f"tcpdump -U -l -i {sta.name}-wlan0 -n '{filt}' "
                    f"> /tmp/{sta.name}_oh.txt 2>/dev/null &"
                )

            info("*** Ping ölçümü yapılıyor...\n")
            ping_out = src.cmd(f"ping -c 30 -i 0.2 -W 2 {dst_ip}")
            pdr, delay = parse_ping(ping_out)

            info("*** iperf3 UDP throughput ölçümü yapılıyor...\n")

            server_log = f"/tmp/iperf3_server_{protocol}.log"
            client_log = f"/tmp/iperf3_client_{protocol}.log"

            dst.cmd("pkill -9 -x iperf3 2>/dev/null || true")
            dst.cmd(f"rm -f {server_log}")
            src.cmd(f"rm -f {client_log}")

            dst.cmd(f"{IPERF3_BIN} -s -1 > {server_log} 2>&1 &")
            time.sleep(2)

            iperf_out = src.cmd(
                f"{IPERF3_BIN} -c {dst_ip} -u -b {bitrate} -t {duration} -J"
            )

            safe_iperf = iperf_out.replace("'", "'\"'\"'")
            src.cmd(f"printf '%s' '{safe_iperf}' > {client_log}")

            throughput, jitter = parse_iperf3(iperf_out)

            if throughput == 0.0:
                info("  ⚠ iperf3 throughput 0 çıktı. Debug loglar:\n")
                info(f"    Client: {client_log}\n")
                info(f"    Server: {server_log}\n")

            info("*** RSSI ölçülüyor...\n")
            rssi_vals = []
            for sta in stations:
                val = get_rssi(sta)
                if val is not None:
                    rssi_vals.append(val)

            avg_rssi = round(sum(rssi_vals) / len(rssi_vals), 1) if rssi_vals else -100.0
            min_rssi = min(rssi_vals) if rssi_vals else -100
            max_rssi = max(rssi_vals) if rssi_vals else -100

            info("*** Overhead toplanıyor...\n")

            for sta in stations:
                sta.cmd("pkill -x tcpdump 2>/dev/null || true")

            time.sleep(1)

            total_overhead = 0
            for sta in stations:
                total_overhead += count_file_lines(sta, f"/tmp/{sta.name}_oh.txt")

            overhead = round(total_overhead / len(stations))

            print(
                f"SONUÇ -> PDR: %{pdr} | Gecikme: {delay} ms | "
                f"TP: {throughput} Mbps | Jitter: {jitter} ms | "
                f"RSSI: {avg_rssi} dBm | Overhead: {overhead}"
            )

            row = {
                "protocol": protocol,
                "speed_ms": speed,
                "txpower_dbm": txpower,
                "rssi_label": rssi_label,
                "run": run_id,
                "pdr_pct": pdr,
                "avg_delay_ms": delay,
                "throughput_mbps": throughput,
                "jitter_ms": jitter,
                "routing_overhead_pkts": overhead,
                "avg_rssi_dbm": avg_rssi,
                "min_rssi_dbm": min_rssi,
                "max_rssi_dbm": max_rssi
            }

            with open(RESULTS_FILE, "a", newline="") as f:
                csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(row)

        finally:
            stop_runtime_processes()

            sh("modprobe -r kaodv 2>/dev/null || true")
            time.sleep(1)

            if net is not None:
                net.stop()

            sh("modprobe -r kaodv 2>/dev/null || true")
            time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description="AODV vs OLSR MANET Simülasyonu")
    parser.add_argument("--protocol", choices=["aodv", "olsrd"], required=True)
    parser.add_argument("--speed", type=float, required=True)
    parser.add_argument("--txpower", type=int, choices=[5, 8, 10, 15, 20], required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--scenario", choices=["normal", "stress"], default="normal")
    parser.add_argument("--bitrate", default="2M")

    args = parser.parse_args()

    if os.geteuid() != 0:
        print("[HATA] sudo ile çalıştırılmalıdır.")
        sys.exit(1)

    setLogLevel("info")

    run_scenario(
        protocol=args.protocol,
        speed=args.speed,
        txpower=args.txpower,
        runs=args.runs,
        duration=args.duration,
        scenario=args.scenario,
        bitrate=args.bitrate
    )


if __name__ == "__main__":
    main()