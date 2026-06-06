#!/bin/bash
# ============================================================
# run_all.sh — Tüm 18 senaryoyu sırayla çalıştır
# 2 protokol × 3 hız × 3 RSSI seviyesi = 18 senaryo
# 502531022 - İrem İÇÖZ
#
# Kullanım:
#   sudo bash run_all.sh
#   sudo bash run_all.sh --dry-run
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SIM="$SCRIPT_DIR/manet_sim.py"
LOG_DIR="$SCRIPT_DIR/results/logs"
RUNS=3

# Senaryo parametreleri
PROTOCOLS=("aodv" "olsrd")
SPEEDS=(1 5 10)
TXPOWERS=(20 15 10)

DRY_RUN=false
[[ "$1" == "--dry-run" ]] && DRY_RUN=true

# ─── Yardımcı temizlik fonksiyonu ───────────────────────────
clean_network() {
    echo "  [Temizlik] Eski süreçler temizleniyor..."

    pkill -9 -x aodvd    2>/dev/null || true
    pkill -9 -x olsrd    2>/dev/null || true
    pkill -9 -x iperf3   2>/dev/null || true
    pkill -9 -x tcpdump  2>/dev/null || true
    pkill -9 -x wmediumd 2>/dev/null || true
    pkill -9 -x hostapd  2>/dev/null || true

    modprobe -r kaodv 2>/dev/null || true

    mn -c > /dev/null 2>&1 || true
}

# ─── Ön kontroller ──────────────────────────────────────────
if [[ $EUID -ne 0 && "$DRY_RUN" == "false" ]]; then
    echo "[HATA] Gerçek çalıştırma için: sudo bash run_all.sh"
    exit 1
fi

if [[ ! -f "$SIM" ]]; then
    echo "[HATA] manet_sim.py bulunamadı: $SIM"
    exit 1
fi

mkdir -p "$LOG_DIR"

# ─── Ön hazırlık ────────────────────────────────────────────
if [[ "$DRY_RUN" == "false" ]]; then
    echo "[*] Network Manager durduruluyor..."
    systemctl stop network-manager 2>/dev/null || true

    echo "[*] Başlangıç temizliği yapılıyor..."
    clean_network

    echo "[*] mac80211_hwsim kontrol ediliyor..."
    modprobe mac80211_hwsim radios=6 2>/dev/null || true

    sleep 3
fi

TOTAL=$(( ${#PROTOCOLS[@]} * ${#SPEEDS[@]} * ${#TXPOWERS[@]} ))

echo "============================================================"
echo " MANET Simülasyon Koşucusu — Toplam $TOTAL senaryo"
echo " Protokoller : ${PROTOCOLS[*]}"
echo " Hızlar (m/s): ${SPEEDS[*]}"
echo " TxPower(dBm): ${TXPOWERS[*]}"
echo " Tekrar      : $RUNS"
echo "============================================================"

counter=0
FAILED=()

# ─── Senaryo döngüsü ────────────────────────────────────────
for PROTO in "${PROTOCOLS[@]}"; do
    for SPEED in "${SPEEDS[@]}"; do
        for TXPOW in "${TXPOWERS[@]}"; do

            counter=$((counter + 1))
            LOGFILE="$LOG_DIR/${PROTO}_v${SPEED}_tx${TXPOW}.log"

            echo ""
            echo "──────────────────────────────────────────────────────"
            echo "[$counter/$TOTAL] Protokol: $PROTO | Hız: $SPEED m/s | TxPower: $TXPOW dBm"
            echo "  Log: $LOGFILE"
            echo "──────────────────────────────────────────────────────"

            CMD="python3 $SIM --protocol $PROTO --speed $SPEED --txpower $TXPOW --runs $RUNS"

            if [[ "$DRY_RUN" == "true" ]]; then
                echo "  [DRY-RUN] $CMD"
                continue
            fi

            echo "  Başlangıç: $(date '+%H:%M:%S')" | tee -a "$LOGFILE"

            if $CMD 2>&1 | tee -a "$LOGFILE"; then
                echo "  ✓ Senaryo tamamlandı — $(date '+%H:%M:%S')" | tee -a "$LOGFILE"
            else
                echo "  ✗ Senaryo BAŞARISIZ — sonraki senaryoya geçiliyor" | tee -a "$LOGFILE"
                FAILED+=("${PROTO}_v${SPEED}_tx${TXPOW}")
            fi

            clean_network
            sleep 8
        done
    done
done

# ─── Özet ───────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " TAMAMLANDI: $counter/$TOTAL senaryo işlendi"

if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo " Başarısız senaryolar:"
    for f in "${FAILED[@]}"; do
        echo "   - $f"
    done
else
    echo " Tüm senaryolar başarılı ✓"
fi

echo ""
echo " Ham veriler : $SCRIPT_DIR/results/raw_data.csv"
echo " Loglar      : $LOG_DIR/"
echo ""
echo " Analiz için çalıştırın:"
echo "   python3 $SCRIPT_DIR/analyze.py"
echo "============================================================"

# Network Manager'ı geri başlat
systemctl start network-manager 2>/dev/null || true
echo "[*] Network Manager yeniden başlatıldı."