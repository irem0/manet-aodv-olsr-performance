# MANET Protokol Performans Analizi
## 502531022 — İrem İÇÖZ · Telsiz Ağ Protokolleri Dersi

> **AODV ve OLSR protokollerinin Mininet-WiFi ortamında farklı mobilite hızı  
> ve RSSI koşulları altında breaking-point analizi + adaptif seçim matrisi**

---

## İÇİNDEKİLER
1. [Proje Yapısı](#1-proje-yapısı)
2. [Bilgisayarınıza Ne Kurmanız Gerekiyor](#2-bilgisayarınıza-ne-kurmanız-gerekiyor)
3. [Adım Adım Kurulum ve Çalıştırma](#3-adım-adım-kurulum-ve-çalıştırma)
4. [Hangi GitHub Kaynaklarını Kullandım — Neye Dayanarak Yazdım](#4-hangi-github-kaynaklarını-kullandım)
5. [Literatür ve Kaynakça](#5-literatür-ve-kaynakça)
6. [Beklenen Çıktılar](#6-beklenen-çıktılar)
7. [Sık Karşılaşılan Sorunlar](#7-sık-karşılaşılan-sorunlar)

---

## 1. Proje Yapısı

```
manet_project/
│
├── install.sh              ← Mininet-WiFi + tüm bağımlılıkları kurar
├── run_all.sh              ← 18 senaryonun tamamını sırayla çalıştırır
│
├── manet_sim.py            ← TEK senaryo simülasyonu (protokol/hız/RSSI)
├── analyze.py              ← Sonuçları analiz eder, 6 grafik üretir
├── generate_mock_data.py   ← Gerçek sim olmadan analizi test etmek için
│
├── results/
│   ├── raw_data.csv        ← Tüm ölçüm verileri (simülasyon sonrası dolar)
│   └── logs/               ← Her senaryo için ayrı log dosyası
│
└── figures/                ← Tüm grafikler ve tablolar (analiz sonrası dolar)
    ├── 01_pdr_vs_speed.png
    ├── 02_delay_vs_speed.png
    ├── 03_throughput_vs_speed.png
    ├── 04_pdr_heatmap.png
    ├── 05_breaking_point_table.png
    └── 06_protocol_matrix.png
```

---

## 2. Bilgisayarınıza Ne Kurmanız Gerekiyor

### İşletim Sistemi
**Zorunlu: Ubuntu 20.04 veya 22.04 LTS** (64-bit)

> ⚠️ Mininet-WiFi, Linux çekirdeğinin `mac80211_hwsim` modülüne doğrudan
> erişir. **Windows veya macOS üzerinde çalışmaz.** Seçenekleriniz:
>
> | Seçenek | Öneri |
> |---------|-------|
> | **Çift önyükleme (dual-boot)** | En iyi performans |
> | **VirtualBox / VMware VM** | Kolay kurulum, yeterli |
> | **WSL2 (Windows Subsystem for Linux)** | `mac80211_hwsim` sorunları çıkabilir, önerilmez |
> | **Doğal Ubuntu makinesi** | İdeal |

### Donanım Gereksinimleri (minimum)
| Kaynak | Minimum | Önerilen |
|--------|---------|---------|
| RAM | 4 GB | 8 GB |
| CPU | 2 çekirdek | 4 çekirdek |
| Disk | 10 GB boş | 20 GB boş |
| Ağ adaptörü | Gerekmiyor (emülasyon) | — |

### Yazılım (install.sh otomatik kurar)
- **Python 3.8+** (Ubuntu'da genelde yüklü)
- **Mininet-WiFi** (intrig-unicamp/mininet-wifi)
- **wmediumd** (kablosuz ortam emülatörü)
- **olsrd** (OLSR daemon)
- **aodv-uu** (AODV kernel modülü)
- **iperf3** (throughput ölçümü)
- **numpy, pandas, matplotlib** (analiz)

---

## 3. Adım Adım Kurulum ve Çalıştırma

### ADIM 1 — Ubuntu'da terminal açın ve projeyi indirin

```bash
# Proje klasörünü doğru yere kopyalayın (USB'den / GitHub'dan / doğrudan)
# Örnek: /home/irem/manet_project/ içinde olduğunuzu varsayıyoruz

cd /home/irem/manet_project
```

### ADIM 2 — Mininet-WiFi ve bağımlılıkları kurun (bir kere)

```bash
sudo bash install.sh
```

Bu işlem **15-30 dakika** sürebilir (internet hızına bağlı).  
Kurulum sırasında "Do you want to continue? [Y/n]" sorularına **Enter** basın.

Kurulum başarılı mı kontrol edin:
```bash
sudo mn --wifi --version    # "Mininet-WiFi X.X" çıktısı görmeli
olsrd -v                    # OLSR versiyon bilgisi
iperf3 --version            # iperf3 versiyonu
```

### ADIM 3 — (İsteğe bağlı) Analiz pipeline'ını test edin

Gerçek simülasyon yapmadan grafiklerin düzgün oluştuğunu test etmek için:

```bash
python3 generate_mock_data.py    # Gerçekçi sahte veri üretir
python3 analyze.py               # 6 grafik oluşturur
ls figures/                      # PNG dosyalarını görmeli
```

### ADIM 4 — Tek senaryo testi (simülasyonu tanımak için)

Tüm 18 senaryoyu çalıştırmadan önce tek bir senaryo çalıştırın:

```bash
sudo python3 manet_sim.py \
    --protocol olsrd \
    --speed 1 \
    --txpower 20 \
    --runs 1
```

Başarılı çıktı şöyle görünür:
```
*** Düğümler oluşturuluyor...
*** Log-distance yayılım modeli ayarlandı
*** olsrd konverjans bekleniyor (20s)...
  ✓ Bağlantı mevcut, ölçüme geçiliyor.
*** iperf3 ölçümü başlıyor...
*** Ping ölçümü başlıyor...
  PDR: 91.3%  |  Gecikme: 8.2 ms  |  Throughput: 1.65 Mbps  |  Jitter: 1.4 ms
```

### ADIM 5 — Tüm 18 senaryoyu çalıştırın

```bash
sudo bash run_all.sh
```

Senaryo listesi (2 protokol × 3 hız × 3 RSSI = 18 senaryo, her biri 3 tekrar):

| # | Protokol | Hız (m/s) | TxPower (dBm) | RSSI Seviyesi |
|---|----------|-----------|---------------|---------------|
| 1 | AODV | 1 | 20 | Yüksek |
| 2 | AODV | 5 | 20 | Yüksek |
| 3 | AODV | 10 | 20 | Yüksek |
| 4 | AODV | 1 | 15 | Orta |
| 5 | AODV | 5 | 15 | Orta |
| 6 | AODV | 10 | 15 | Orta |
| 7 | AODV | 1 | 10 | Düşük |
| 8 | AODV | 5 | 10 | Düşük |
| 9 | AODV | 10 | 10 | Düşük |
| 10–18 | OLSR | (aynı kombinasyonlar) | | |

> ⏱️ **Toplam süre:** ~4-6 saat (her senaryo ~15 dk konverjans + ölçüm süresi)  
> Gerekirse gece çalıştırın veya `--runs 1` ile hızlandırın.

### ADIM 6 — Analiz ve görselleştirme

```bash
python3 analyze.py
```

Çıktılar `figures/` klasörüne kaydedilir.

### ADIM 7 — Sonuçları raporunuza ekleyin

```bash
ls figures/
# 01_pdr_vs_speed.png       → "PDR vs Mobilite Hızı" grafiği
# 02_delay_vs_speed.png     → "Gecikme vs Mobilite Hızı" grafiği  
# 03_throughput_vs_speed.png→ "Throughput" karşılaştırması
# 04_pdr_heatmap.png        → AODV ve OLSR PDR ısı haritaları
# 05_breaking_point_table.png→ Breaking point tablosu
# 06_protocol_matrix.png    → Adaptif protokol seçim matrisi
```

---

## 4. Hangi GitHub Kaynaklarını Kullandım

Bu proje **sıfırdan yazılmıştır**, ancak şu resmi kaynaklara dayanılarak tasarlanmıştır:

### A) intrig-unicamp/mininet-wifi (Resmi Mininet-WiFi repo)
**URL:** https://github.com/intrig-unicamp/mininet-wifi

Kullanılan spesifik dosyalar:

| Dosya | Ne için |
|-------|---------|
| `examples/adhoc.py` | Ad-hoc topoloji kurulumu, AODV/OLSR'nin `addLink(proto=...)` ile nasıl çalıştırıldığı |
| `examples/propagationModel.py` | `net.setPropagationModel(model="logDistance", exp=4)` kullanımı |
| `examples/mobilityModel.py` | `net.setMobilityModel(model='RandomWayPoint', min_v=..., max_v=...)` API'si |
| `mn_wifi/link.py` | `wmediumd`, `adhoc`, `interference` import'ları |
| `mn_wifi/net.py` | `Mininet_wifi` sınıfı, `configureNodes()`, `build()` |

**adhoc.py'den aldığım temel yapı:**
```python
# Mininet-WiFi'nin kendi örneğinden — protokol geçirme yöntemi:
net.addLink(sta1, cls=adhoc, intf='sta1-wlan0',
            ssid='adhocNet', mode='g', channel=5, proto='olsrd')
# AODV için özel modül yükleme:
from mn_wifi.manetRoutingProtocols import aodv
aodv.load_module("sta1-wlan0,sta2-wlan0,sta3-wlan0")
```

### B) maahmed24712/Comparison-of-Manet-Routing-Protocols (NS3 referans)
**URL:** https://github.com/maahmed24712/Comparison-of-Manet-Routing-Protocols  
Senaryo parametrelerini (PDR, throughput, loss ölçümü) nasıl raporlayacağıma dair fikir.

### C) Mininet-WiFi Dokümantasyonu (hackmd.io/@ramonfontes)
Mobilite modeli parametrelerini doğrulayan resmi eğitim materyali.

### Orijinal Katkım (tamamen sıfırdan yazılan kısımlar)
- `manet_sim.py` — 6 düğümlü otomatik senaryo çalıştırıcı, `popen`/`cmd` ile ölçüm toplama, CSV kaydetme
- `analyze.py` — Tüm grafikler, breaking-point algoritması, seçim matrisi mantığı
- `run_all.sh` — 18 senaryolu otomasyon scripti
- `generate_mock_data.py` — Literatür değerlerine dayalı gerçekçi test verisi modeli

---

## 5. Literatür ve Kaynakça

Aşağıdaki kaynaklar hem proje önerisinde yer almakta hem de simülasyon parametrelerinin belirlenmesinde kullanılmıştır.

### Temel Kaynaklar (Proje Önerisindekiler)

**[1] Perkins & Royer (1999) — AODV**  
> C. E. Perkins and E. M. Royer, "Ad-hoc On-Demand Distance Vector Routing,"  
> *Proc. 2nd IEEE Workshop on Mobile Computing Systems and Applications*, 1999.

- AODV'nin temel RFC'si (RFC 3561)
- **Simülasyona yansıması:** Reaktif yapısı → rota keşfi sırasında RREQ/RREP flood
- Yüksek mobilite → RREQ sıklığı artar → overhead artar → simülasyonda yüksek hızda PDR düşüşü

**[2] Clausen & Jacquet (2003) — OLSR RFC**  
> T. Clausen and P. Jacquet, "Optimized Link State Routing Protocol (OLSR),"  
> *IETF RFC 3626*, Oct. 2003.

- OLSR'nin hello mesaj aralığı: **2 saniye** (varsayılan)
- Topoloji kontrol (TC) mesaj aralığı: **5 saniye**
- **Simülasyona yansıması:** 5 m/s hızda düğümler 10 saniyede 50m hareket eder;
  TC mesajları eskir → topoloji tablosu yanlış yönlendirme yapar → PDR düşer

**[3] Fontes et al. (2015) — Mininet-WiFi**  
> R. Fontes et al., "Mininet-WiFi: Emulating Software-Defined Wireless Networks,"  
> *IEEE/IFIP CNSM*, 2015.  
> GitHub: https://github.com/intrig-unicamp/mininet-wifi

- **wmediumd interference modu** — gerçekçi paket kaybı ve sinyal zayıflaması
- **log-distance propagation model** — `exp=4` (şehir içi ortam)
- Bu parametreler doğrudan simülasyonda kullanıldı

**[4] Mohapatra & Kanungo (2012) — NS2 Karşılaştırma**  
> S. Mohapatra and P. Kanungo, "Performance Analysis of AODV, DSR, OLSR and DSDV  
> Routing Protocols using NS2 Simulator," *Procedia Engineering*, vol. 30, 2012.

- PDR değerleri: AODV düşük mobilite → ~%90-95, yüksek mobilite → %65-75
- OLSR düşük mobilite → ~%88-93, yüksek mobilite → %55-70
- **Mock veri modelinin dayandığı temel referans**

---

### Ek Destekleyici Kaynaklar (Bulguları güçlendirmek için)

**[5] Abolhasan et al. (2004) — MANET Protokol Surveyı**  
> M. Abolhasan, T. Wysocki, E. Dutkiewicz, "A Review of Routing Protocols for  
> Mobile Ad Hoc Networks," *Ad Hoc Networks*, vol. 2, no. 1, 2004.  
> DOI: 10.1016/S1570-8705(03)00043-X

- Proaktif vs reaktif protokollerin genel karşılaştırması
- Tablo 1-3: PDR, delay, overhead değerleri için temel referans
- **Raporunuzda:** "Bulgularımız Abolhasan et al.'ın gözlemleriyle örtüşmektedir"

**[6] Broch et al. (1998) — İlk kapsamlı MANET karşılaştırması**  
> J. Broch, D.A. Maltz, D.B. Johnson, Y.C. Hu, J. Jetcheva,  
> "A Performance Comparison of Multi-Hop Wireless Ad Hoc Network Routing Protocols,"  
> *ACM MobiCom*, 1998.

- Random Waypoint mobilite modelinin AODV ve DSR'a etkisi
- **Simülasyona yansıması:** Random Waypoint modelinin seçimi bu çalışmaya dayanır

**[7] Bai & Helmy (2004) — Mobilite Model Etkisi**  
> F. Bai and A. Helmy, "A Survey of Mobility Models," in  
> *Wireless Ad Hoc Networks*, University of Southern California, 2004.

- Random Waypoint modelinin MANET simülasyonunda en yaygın model olduğunu doğrular
- "Duraksama noktası" etkisi ve hız dağılımı

**[8] Kotz et al. (2004) — RSSI Ölçüm Çalışması**  
> D. Kotz, C. Newport, R.S. Gray, J. Liu, Y. Yuan, C. Elliott,  
> "Experimental Evaluation of Wireless Simulation Assumptions,"  
> *ACM MSWiM*, 2004.

- Gerçek ortamda RSSI ile PDR ilişkisi
- **RSSI eşiklerinin simülasyon karşılığı:** txpower=20→Yüksek, 15→Orta, 10→Düşük seçiminin gerekçesi

**[9] Roy (2011) — AODV vs OLSR Kapsamlı Karşılaştırma**  
> R. R. Roy, "Handbook on Mobile Ad Hoc Networks for Mobility Models,"  
> *Springer*, 2011. ISBN: 978-1-4419-6048-1

- Farklı mobilite hızlarında AODV ve OLSR PDR karşılaştırma tabloları
- Breaking point kavramının literatürdeki tanımı

---

### Simülasyon Parametreleri — Literatür Gerekçeleri

| Parametre | Değer | Kaynak |
|-----------|-------|--------|
| Yayılım modeli | log-distance, exp=4 | Fontes 2015 [3] |
| Mobilite modeli | Random Waypoint | Broch 1998 [6], Bai 2004 [7] |
| Hız seviyeleri | 1, 5, 10 m/s | Mohapatra 2012 [4] |
| PDR eşiği | %70 | Abolhasan 2004 [5] |
| iperf3 trafik | UDP, 2 Mbps | Fontes 2015 [3] |
| Tekrar sayısı | 3 | İstatistiksel güvenilirlik |
| Konverjans süresi | 20s (OLSR hello=2s × 10) | Clausen 2003 [2] |
| Ağ alanı | 200×200 m | Mohapatra 2012 [4] |
| Düğüm sayısı | 6 | Proje önerisi |

---

## 6. Beklenen Çıktılar

Başarılı bir simülasyon sonucunda aşağıdaki çıktıların tamamı elde edilir:

### Simülasyon Çıktıları
- `results/raw_data.csv` — 54 satır (18 senaryo × 3 tekrar), 8 metrik sütunu
- `results/logs/` — Her senaryo için ayrı log (hata ayıklama için)

### Grafik Çıktıları (`figures/`)

| Dosya | İçerik | Proje Önerisindeki Karşılık |
|-------|--------|----------------------------|
| `01_pdr_vs_speed.png` | PDR vs Mobilite Hızı (her RSSI seviyesi) | ✅ "Mobilite Hızı vs PDR" |
| `02_delay_vs_speed.png` | Gecikme vs Mobilite Hızı | ✅ "RSSI vs Gecikme" |
| `03_throughput_vs_speed.png` | Throughput karşılaştırması | ✅ "Mobilite Hızı vs Throughput" |
| `04_pdr_heatmap.png` | PDR ısı haritası (2D: hız × RSSI) | ✅ Breaking point görselleştirmesi |
| `05_breaking_point_table.png` | Breaking point analiz tablosu | ✅ "Breaking point analiz tablosu" |
| `06_protocol_matrix.png` | Adaptif protokol seçim matrisi | ✅ "Adaptif seçim matrisi (3×3)" |

### Başarı Kriterleri Kontrol Listesi
- [ ] Simülasyonlar hatasız tamamlandı
- [ ] AODV ve OLSR arasında **PDR** metriğinde ölçülebilir fark var
- [ ] AODV ve OLSR arasında **gecikme** metriğinde ölçülebilir fark var
- [ ] Her protokol için breaking point nicel olarak belirlendi
- [ ] Adaptif seçim matrisi veri odaklı gerekçeyle sunuldu

---

## 7. Sık Karşılaşılan Sorunlar

### "mn_wifi bulunamadı" hatası
```bash
sudo pip3 install mininet-wifi  # Bu işe YARAMAZ
# Doğrusu:
sudo bash install.sh            # Kaynak koddan derler
```

### "RTNETLINK answers: File exists" hatası
Önceki simülasyon düzgün kapanmamış demektir:
```bash
sudo mn -c    # Mininet kalıntılarını temizler
```

### AODV modülü yüklenemiyor
```bash
sudo modprobe aodv  # Manuel yükle
lsmod | grep aodv   # Yüklü mü?
```

### wmediumd başlatılamıyor
```bash
sudo pkill wmediumd  # Önceki süreci öldür
sudo mn -c
```

### VirtualBox'ta mac80211_hwsim çalışmıyor
```bash
sudo modprobe mac80211_hwsim radios=6  # Elle yükle (6 düğüm için)
lsmod | grep mac80211_hwsim
```

---

## Hızlı Başlangıç (TL;DR)

```bash
# 1. Ubuntu 20.04/22.04 terminali aç
sudo bash install.sh          # ~20 dk, bir kere

# 2. Test et
python3 generate_mock_data.py && python3 analyze.py

# 3. Gerçek simülasyon
sudo bash run_all.sh          # ~5 saat (gece çalıştır)

# 4. Analiz
python3 analyze.py            # figures/ klasöründe 6 grafik
```
