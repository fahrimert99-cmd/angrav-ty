# 🎬 Çizgi Film Otonom Üretim Sistemi

Aile temalı, orijinal karakterlerle **tamamen ücretsiz** araçlar kullanarak
otonom (kendi kendine çalışan) çizgi film / YouTube videosu üreten sistem.

> Senaryo → Seslendirme → Konuşan karakter animasyonu → Arka plan → Montaj →
> Altyazı → YouTube'a yükleme. Her adım ayrı bir modül; hepsi `main.py` ile
> zincirleme çalışır.

---

## 👨‍👩‍👧‍👦 Karakterler

| Kod (slug) | İsim | Rol | Görsel dosya |
| :--- | :--- | :--- | :--- |
| `nurcan` | Nurcan | Anne | `karakterler/nurcan.jpeg` |
| `mert` | Mert | Baba | `karakterler/mert.jpeg` |
| `batu` | Batu | Çocuk | `karakterler/batu.jpeg` |
| `can` | Can | Çocuk | `karakterler/can.jpeg` |
| `ece` | Ece | Kız çocuk | `karakterler/ece.jpeg` |
| `elif` | Elif Öğretmen | Öğretmen | `karakterler/elif.jpeg` |
| `dede` | Tonton Dede | Dede | `karakterler/dede.jpeg` |
| `nine` | Tonton Nine | Nine | `karakterler/nine.jpeg` |
| `bobi` | Bobi | Köpek (evcil hayvan) | `karakterler/bobi.jpeg` |
| `duru` | Duru | Kız çocuk | `karakterler/duru.jpeg` |
| `efe` | Efe | Erkek çocuk | `karakterler/efe.jpeg` |

Karakterlerin tüm özellikleri (görsel tanım, ses dosyası yolu, TTS sesi)
`config/karakterler.json` içinde tutulur. Görseller depoda hazır gelir.

> ⚠️ **Stil birliği notu:** Karakterlerin çoğu 3B (Pixar tarzı), `can` ve `ece`
> ise 2B çizgi roman tarzında. Aynı sahnede tutarlı görünüm için hepsini tek bir
> stile getirmeniz önerilir. `config/karakterler.json` içindeki `stil` alanına bakın.

---

## 🧠 Kullanılan Ücretsiz Yapay Zekâ Araçları

| Adım | Araç | Ücret | Not |
| :--- | :--- | :--- | :--- |
| Senaryo/diyalog | **Google Gemini API** (veya Groq) | Ücretsiz kota | Anahtar gerekir (ücretsiz) |
| Seslendirme | **edge-tts** (Microsoft) | Tamamen bedava | Anahtarsız, Türkçe sesler |
| Ses klonlama (ops.) | **Coqui XTTS-v2** | Bedava (yerel) | Kendi ses örneğinizden klon |
| Konuşan karakter | **SadTalker** | Bedava (yerel/Colab) | Görsel + ses → konuşan video |
| Dudak senkronu (alt.) | **Wav2Lip** | Bedava (yerel) | SadTalker alternatifi |
| Arka plan görseli | **Pollinations.ai** | Bedava, anahtarsız | Yerel SD de olur |
| Montaj | **MoviePy + FFmpeg** | Bedava | Videoları birleştirir |
| Altyazı | **faster-whisper** | Bedava (yerel) | Sesten otomatik altyazı |
| Yükleme | **YouTube Data API v3** | Bedava kota | Google Cloud'da proje açılır |

### 💡 "Bedava" ile ilgili dürüst not
Ağır işler (SadTalker, Whisper, Stable Diffusion) iyi bir bilgisayar, tercihen
**NVIDIA ekran kartı** ister. Ekran kartınız yoksa **Google Colab'ın ücretsiz
GPU'su** ile çalıştırın — `colab/README.md` dosyasına bakın. Kod GitHub'da durur,
ağır üretim Colab/yerel makinede çalışır.

---

## 🗂️ Klasör Yapısı

```
.
├── main.py                  # Ana orkestratör (tüm adımları sırayla çalıştırır)
├── requirements.txt         # Python bağımlılıkları
├── config/
│   ├── ayarlar.ornek.yaml   # Örnek ayar dosyası (kopyalayıp ayarlar.yaml yapın)
│   └── karakterler.json     # Karakter kayıt defteri
├── karakterler/             # Karakter görselleri (hazır gelir)
├── sesler/                  # Seslendirme örnekleri / hazır ses dosyaları
├── cikti/                   # Üretilen video, ses, altyazılar
├── colab/                   # Ücretsiz GPU ile çalıştırma rehberi
└── src/
    ├── senaryo.py           # Gemini/Groq ile senaryo üretimi
    ├── seslendirme.py       # edge-tts / XTTS / kullanıcı sesi
    ├── sahne.py             # Pollinations ile arka plan görseli
    ├── animasyon.py         # SadTalker ile konuşan karakter
    ├── montaj.py            # MoviePy ile video birleştirme
    ├── altyazi.py           # faster-whisper ile altyazı
    └── yukleme.py           # YouTube'a yükleme
```

---

## 🚀 Kurulum

```bash
git clone https://github.com/fahrimert99-cmd/-izgi-film.git
cd -izgi-film
pip install -r requirements.txt

cp config/ayarlar.ornek.yaml config/ayarlar.yaml
#  -> ayarlar.yaml içine Gemini API anahtarını yazın (ücretsiz: aistudio.google.com)
```

---

## ☁️ Colab'sız çalıştırma — GitHub Actions (bedava, GPU gerekmez)

`basit` animasyon motoru + Pollinations + edge-tts ile tüm adımlar **CPU'da**
çalışır; bu yüzden videoyu doğrudan **GitHub'ın bedava sunucusunda** üretebilirsin
— Colab'a da kendi bilgisayarına da gerek yok.

1. **Tek seferlik:** Repo → **Settings → Secrets and variables → Actions → New
   repository secret** → Ad: `GEMINI_API_KEY`, Değer: [ücretsiz anahtarın](https://aistudio.google.com).
2. Repo → **Actions** sekmesi → soldan **“Video Uret”** → **Run workflow**.
3. Konuyu/süreyi/karakterleri yaz → **Run workflow**.
4. İş bitince aynı çalıştırma sayfasında **Artifacts → `cizgi-film-video`**'yu indir.

> Görseller iş sırasında otomatik üretilir (Pollinations), YouTube'a yükleme için
> `youtube_yukle` sırrı ayrıca eklenebilir.

## ▶️ Yerel kullanım

```bash
python main.py --konu "Batu ve Bobi parkta kaybolan topu arıyor" --sure 60
```

Sistem sırasıyla: senaryo yazar → replikleri seslendirir → her karakteri
konuşturur → arka planları üretir → montajlar → altyazı ekler → (istenirse)
YouTube'a yükler. Çıktılar `cikti/` klasöründe oluşur.

YouTube'a yüklemek için: `--yukle` ekleyin veya `ayarlar.yaml`'da `yukleme.aktif: true`.

---

## 🗺️ Yol Haritası
- [x] Karakter görsellerini ekle (depoda hazır)
- [ ] Ses örneklerini `sesler/` klasörüne ekle
- [ ] Gemini API anahtarını al (ücretsiz)
- [ ] İlk deneme bölümünü üret
- [ ] YouTube API kimlik bilgilerini bağla
- [ ] Zamanlanmış otomatik üretim (Colab / cron / Make)

---
*Bu depo yalnızca kod ve yapı içindir; ağır AI üretimi yerel makinede veya
Colab'da çalışır.*
