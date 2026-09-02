# 🎞️ klipler/ — Günlük ASMR klipleriniz

Bu klasör, **kendi ürettiğiniz kısa video kliplerini** koyduğunuz yerdir. Buraya
klip yükleyip **push** ettiğinizde `Klip Birlestir - ASMR` iş akışı **otomatik**
çalışır: klipleri sırayla birleştirir, hedef süreye (varsayılan **30 dk**)
**döngüler** ve tek bir uzun ASMR videosu üretir. **Klip sesleri korunur.**

## Nasıl yüklerim?

İki yol var — ikisi de çalışır:

**1) Doğrudan bu klasöre (en basit):**
```
klipler/
├── 01.mp4
├── 02.mp4
├── 03.mp4
└── 04.mp4
```

**2) Tarih alt-klasörü ile (geçmişi saklamak için — önerilen):**
```
klipler/
├── 2026-09-02/
│   ├── 01.mp4
│   ├── 02.mp4
│   └── 03.mp4
└── 2026-09-03/
    ├── 01.mp4
    └── 02.mp4
```
> Tarih alt-klasörü kullanırsanız sistem **en yeni** (ada göre en sondaki)
> klasörü işler. Böylece eski günlerin klipleri repoda kalır.

## Sıralama

Klipler **doğal sırayla** (dosya adına göre) birleştirilir: `01, 02, 03, 10`
(yani `10.mp4`, `2.mp4`'ten sonra gelir). Adları `01, 02, 03…` gibi verin.

## Desteklenen biçimler

`.mp4` · `.mov` · `.webm` · `.mkv` · `.m4v` · `.avi`
Klipler farklı çözünürlükte olsa da otomatik olarak ortak çözünürlüğe getirilir.

## Ayarlar

Süre, geçiş, ses modu gibi ayarlar `config/ayarlar.ornek.yaml` içindeki **`klip`**
bölümündedir:
- `sure`: hedef süre (1800 = 30 dk, 3600 = 60 dk)
- `gecis_sn`: klipler arası yumuşak geçiş (0 = sert kesim)
- `ses`: `koru` (klip sesi) · `ambient_ekle` · `ambient_degistir`

## Manuel çalıştırma

Otomatik beklemek istemezseniz: **Actions → "Klip Birlestir - ASMR" → Run
workflow** (süre ve gizlilik seçebilirsiniz).

Çıktı her zaman **Actions → ilgili çalışma → Artifacts → `birlesik-asmr-video`**
altında olur; YouTube sırları ekliyse otomatik yüklenir.
