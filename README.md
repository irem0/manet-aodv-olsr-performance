# MANET AODV vs OLSR Performans Analizi

Bu proje, Mininet-WiFi ortamında AODV ve OLSR yönlendirme protokollerinin MANET koşullarındaki performansını karşılaştırmak için hazırlanmıştır.

Çalışmada mobilite hızı, TxPower/RSSI seviyesi ve topoloji zorluğu değiştirilerek PDR, gecikme, throughput, jitter, routing overhead ve kırılma noktası davranışları incelenmiştir.

## Kullanılan Protokoller

* **AODV:** Reaktif protokoldür. Rotalar ihtiyaç olduğunda RREQ, RREP ve RERR mesajlarıyla oluşturulur.
* **OLSR:** Proaktif protokoldür. Rotalar HELLO ve TC mesajlarıyla güncel tutulur. MPR mekanizmasıyla broadcast yükü azaltılır.

## Proje Dosyaları

```text
manet_sim.py          # Ana simülasyon kodu
run_all.sh            # Ana deneyleri çalıştırır
run_stress.sh         # Stres deneylerini çalıştırır
analyze.py            # Ana deney grafiklerini üretir
analyze_stress.py     # Stres deney grafiklerini üretir
stress_summary.py     # Stres sonuçlarını özetler
results/              # CSV sonuçları
figures/              # Ana deney grafikleri
figures_stress/       # Stres deney grafikleri
report/               # Rapor ve sunum
```

## Gereksinimler

Bu proje Linux tabanlı Mininet-WiFi ortamında çalıştırılmalıdır.

Gerekli araçlar:

```text
Mininet-WiFi
AODV-UU (aodvd + kaodv)
OLSRD
iperf3
tcpdump
Python 3
pandas
matplotlib
```

AODV-UU bazı sistemlerde manuel derleme gerektirebilir.

## Deney Senaryoları

### Ana Deney

| Parametre    | Değer          |
| ------------ | -------------- |
| Alan         | 300 × 250 m    |
| Düğüm sayısı | 6              |
| Hızlar       | 1, 5, 10 m/s   |
| TxPower      | 20, 15, 10 dBm |
| Trafik       | UDP 2 Mbps     |
| Tekrar       | 3              |
| Bekleme      | 25 sn          |

### Stres Deneyi

| Parametre    | Değer          |
| ------------ | -------------- |
| Alan         | 450 × 300 m    |
| Düğüm sayısı | 6              |
| Hızlar       | 10, 15, 20 m/s |
| TxPower      | 10, 8, 5 dBm   |
| Trafik       | UDP 2 Mbps     |
| Tekrar       | 3              |
| Bekleme      | 25 sn          |

## Çalıştırma

Ana deneyleri çalıştırmak için:

```bash
sudo bash run_all.sh
```

Stres deneylerini çalıştırmak için:

```bash
sudo bash run_stress.sh
```

Tek senaryo örneği:

```bash
sudo python3 manet_sim.py --protocol aodv --speed 1 --txpower 20 --runs 3 --scenario normal --bitrate 2M
```

```bash
sudo python3 manet_sim.py --protocol olsrd --speed 10 --txpower 5 --runs 3 --scenario stress --bitrate 2M
```

## Analiz

Ana deney grafikleri:

```bash
python3 analyze.py --input results/raw_data_main.csv
```

Stres deney grafikleri:

```bash
python3 analyze_stress.py
```

Stres sonuç özeti:

```bash
python3 stress_summary.py
```

## Ölçülen Metrikler

* **PDR:** Paket teslim oranı
* **Gecikme:** Ping RTT ortalaması
* **Throughput:** iperf3 UDP çıktısı
* **Jitter:** iperf3 UDP çıktısı
* **Routing overhead:** tcpdump ile yakalanan kontrol trafiği
* **RSSI:** `iw dev station dump` ile ölçülen alıcı sinyal gücü

RSSI değerleri literatürden sabit alınmamıştır. TxPower deney parametresi olarak kullanılmış, RSSI ise deney sırasında ölçülmüştür.

## Temel Bulgular

* Ana deneyde her iki protokol de yüksek PDR sağlamıştır.
* OLSR ana deneyde tüm koşullarda %100 PDR sağlamıştır.
* AODV düşük TxPower/RSSI koşulunda %93.3 PDR’ye düşmüş ancak kırılmamıştır.
* Stres deneyinde AODV tüm koşullarda %90 üzeri PDR korumuştur.
* OLSR, 5 dBm TxPower koşulunda kırılma yaşamıştır.
* Throughput, RSSI düşüşünden PDR’ye göre daha erken etkilenmiştir.
* AODV, OLSR’ye göre daha yüksek routing overhead üretmiştir.
* Protokol seçimi koşula bağlıdır.

## Sonuç

OLSR bağlantılı ve kararlı topolojilerde yüksek PDR sağlamıştır.
AODV ise düşük TxPower/RSSI ve seyrek topoloji koşullarında daha dayanıklı davranmıştır.

Bu nedenle MANET ortamında protokol seçimi; mobilite, RSSI, topoloji yoğunluğu ve performans önceliğine göre yapılmalıdır.
