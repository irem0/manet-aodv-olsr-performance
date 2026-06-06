#!/bin/bash
# ============================================================
# run_stress.sh — Breaking point aramak için ek stres senaryosu
# 502531022 - İrem İÇÖZ
#
# Amaç:
# Ana deneyde PDR < 70% oluşmadığı için ağı daha zorlamak.
#
# ============================================================

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SIM="$SCRIPT_DIR/manet_sim.py"
RESULTS_DIR="$SCRIPT_DIR/results"
LOG_DIR="$RESULTS_DIR/logs_stress"
RUNS=3

PROTOCOLS=("aodv" "olsrd")
SPEEDS=(10 15 20)
TXPOWERS=(10 8 5)

mkdir -p "$LOG_DIR"
mkdir -p "$RESULTS_DIR"

clean_network() {
    pkill -9 -x aodvd    2>/dev/null || true
    pkill -9 -x olsrd    2>/dev/null || true
    pkill -9 -x iperf3   2>/dev/null || true
    pkill -9 -x tcpdump  2>/dev/null || true
    pkill -9 -x wmediumd 2>/dev/null || true
    pkill -9 -x hostapd  2>/dev/null || true
    modprobe -r kaodv 2>/dev/null || true
    mn -c > /dev/null 2>&1 || true
}

if [[ $EUID -ne 0 ]]; then
    echo "[HATA] sudo ile çalıştırın: sudo bash run_stress.sh"
    exit 1
fi

if [[ ! -f "$SIM" ]]; then
    echo "[HATA] manet_sim.py bulunamadı: $SIM"
    exit 1
fi

echo "============================================================"
echo " STRES SENARYOSU — Breaking Point Arama"
echo " Alan      : 450x300 m"
echo " Hızlar    : ${SPEEDS[*]} m/s"
echo " TxPower   : ${TXPOWERS[*]} dBm"
echo " Trafik    : 2M UDP"
echo " Tekrar    : $RUNS"
echo "============================================================"

# Mevcut ana deney varsa yedekle
if [[ -f "$RESULTS_DIR/raw_data.csv" ]]; then
    echo "[*] Mevcut raw_data.csv, raw_data_main.csv olarak yedekleniyor..."
    cp "$RESULTS_DIR/raw_data.csv" "$RESULTS_DIR/raw_data_main.csv"
fi

# Stres testi için yeni raw_data.csv başlat
rm -f "$RESULTS_DIR/raw_data.csv"

clean_network
systemctl stop network-manager 2>/dev/null || true

counter=0
TOTAL=$(( ${#PROTOCOLS[@]} * ${#SPEEDS[@]} * ${#TXPOWERS[@]} ))

for PROTO in "${PROTOCOLS[@]}"; do
    for SPEED in "${SPEEDS[@]}"; do
        for TXPOW in "${TXPOWERS[@]}"; do

            counter=$((counter + 1))
            LOGFILE="$LOG_DIR/${PROTO}_stress_v${SPEED}_tx${TXPOW}.log"

            echo ""
            echo "──────────────────────────────────────────────────────"
            echo "[$counter/$TOTAL] STRESS | Protokol: $PROTO | Hız: $SPEED m/s | TxPower: $TXPOW dBm"
            echo "  Log: $LOGFILE"
            echo "──────────────────────────────────────────────────────"

            CMD="python3 $SIM --protocol $PROTO --speed $SPEED --txpower $TXPOW --runs $RUNS --scenario stress --bitrate 2M"
            if $CMD 2>&1 | tee -a "$LOGFILE"; then
                echo "  ✓ Stres senaryosu tamamlandı" | tee -a "$LOGFILE"
            else
                echo "  ✗ Stres senaryosu başarısız" | tee -a "$LOGFILE"
            fi

            clean_network
            sleep 8
        done
    done
done

# Stres sonucunu ayrı dosyaya kopyala
if [[ -f "$RESULTS_DIR/raw_data.csv" ]]; then
    cp "$RESULTS_DIR/raw_data.csv" "$RESULTS_DIR/raw_data_stress.csv"
fi

systemctl start network-manager 2>/dev/null || true

echo ""
echo "============================================================"
echo " STRES TESTİ TAMAMLANDI"
echo " Aktif ham veri : $RESULTS_DIR/raw_data.csv"
echo " Stres yedeği   : $RESULTS_DIR/raw_data_stress.csv"
echo " Ana deney      : $RESULTS_DIR/raw_data_main.csv"
echo " Loglar         : $LOG_DIR"
echo "============================================================"