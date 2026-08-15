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
| `kaan` | Kaan | Baba | `karakterler/kaan.jpeg` |
| `selin` | Selin | Anne | `karakterler/selin.jpeg` |
| `mira` | Mira | Kız çocuk | `karakterler/mira.jpeg` |
| `ege` | Ege | Erkek çocuk | `karakterler/ege.jpeg` |
| `dede` | Ihsan Dede | Dede | `karakterler/dede.jpeg` |

Karakterlerin tüm özellikleri (görsel tanım, ses dosyası yolu, TTS sesi)
`config/karakterler.json` içinde tutulur. Görseller depoda hazır gelir.

> Tüm karakterler tutarlı, tek bir stilde: 3B (Pixar tarzı).

---

## 🧠 Kullanılan Ücretsiz Yapay Zekâ Araçları

| Adım | Araç | Ücret | Not |
| :--- | :--- | :--- | :--- |
| Senaryo/diyalog | **Claude API** (Haiku 4.5) — yedek: Gemini / Groq | Ücretli (küçük tutar) | Anahtar gerekir; ücretsiz Gemini/Groq'a otomatik düşer |
| Seslendirme | **edge-tts** (Microsoft) | Tamamen bedava | Anahtarsız, Türkçe sesler |
| Ses klonlama (ops.) | **Coqui XTTS-v2** | Bedava (yerel) | Kendi ses örneğinizden klon |
| Konuşan karakter | **SadTalker** | Bedava (yerel/Colab) | Görsel + ses → konuşan video |
| Konuşan karakter (uzak) | **SadTalker HF Space** | Bedava (kota/kuyruk) | Yerel GPU'suz; `sadtalker_hf` motoru bir Hugging Face Space'i çağırır |
| Dudak senkronu (alt.) | **Wav2Lip** | Bedava (yerel) | SadTalker alternatifi |
| Arka plan görseli | **Pollinations.ai** | Bedava, anahtarsız | Yerel SD de olur |
| Arka plan (stok) | **Pexels** foto/video | Bedava (API anahtarı) | `pexels_foto` (sabit) veya `pexels_video` (hareketli) arka plan |
| Montaj | **MoviePy + FFmpeg** | Bedava | Videoları birleştirir |
| Altyazı | **faster-whisper** | Bedava (yerel) | Sesten otomatik altyazı |
| Yükleme | **YouTube Data API v3** | Bedava kota | Google Cloud'da proje açılır |

### 💡 "Bedava" ile ilgili dürüst not
Ağır işler (SadTalker, Whisper, Stable Diffusion) iyi bir bilgisayar, tercihen
**NVIDIA ekran kartı** ister. Ekran kartınız yoksa **Google Colab'ın ücretsiz
GPU'su** ile çalıştırın — `colab/README.md` dosyasına bakın. Kod GitHub'da durur,
ağır üretim Colab/yerel makinede çalışır.

---

## 🌙 Masalname — Uyku Masalı Videosu (15+ dk)

Çizgi film hattından ayrı, **uzun uyku masalı** videoları üretir (shorts değil).
Tek sakin **anlatıcı** (edge-tts), masalın içeriğine uygun **storybook illüstrasyonları**
(Pollinations AI) ve **tam ekran yavaş Ken Burns akışı** ile huzurlu bir video.

```bash
python masal.py --klasor masallar/kayip-zamanin-aynasi   # kendi senaryonuzdan (önerilen)
python masal.py --tema "yıldızları toplayan minik tavşan" --sure 900   # AI ile üret
```

### 📚 Kendi senaryonuzdan video (önerilen)
`masallar/` altına her masal için bir klasör açın: içine **senaryo metni**
(`.md`, `.txt` veya `.docx`) ve **bölüm görselleri** (`1.jpg`, `2.jpg` …) koyun.
Sistem metni bölümlere ayırır, her bölümü kendi görseliyle eşleştirir ve videoyu
üretir. Ayrıntı: [`masallar/README.md`](masallar/README.md).

- Tema boş bırakılırsa rastgele bir uyku teması seçilir.
- Masal metni **AI** üretir (Claude/Gemini/Groq; anahtar yoksa güvenli şablon masal).
- Görseller AI illüstrasyon (masal/suluboya tarzı); anlatıcı sesi ve tempo
  `config/ayarlar.yaml`'daki `masal` bölümünden ayarlanır.
- **GitHub Actions:** `Masalname` iş akışı **haftada 3** (Pzt/Çrş/Cum ~20:00 TR)
  otomatik çalışır; manuel de tetiklenebilir. Çıktı `Artifacts → masalname-video`.

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
#  -> ayarlar.yaml içine Claude API anahtarınızı yazın (console.anthropic.com)
#  -> anahtar yoksa/kota dolarsa Gemini (ücretsiz: aistudio.google.com) veya Groq'a otomatik düşer
```

---

## ☁️ Colab'sız çalıştırma — GitHub Actions (bedava, GPU gerekmez)

`basit` animasyon motoru + Pollinations + edge-tts ile tüm adımlar **CPU'da**
çalışır; bu yüzden videoyu doğrudan **GitHub'ın bedava sunucusunda** üretebilirsin
— Colab'a da kendi bilgisayarına da gerek yok.

1. **Tek seferlik:** Repo → **Settings → Secrets and variables → Actions → New
   repository secret** → Ad: `ANTHROPIC_API_KEY`, Değer: [Claude anahtarınız](https://console.anthropic.com).
   (`GEMINI_API_KEY` veya `GROQ_API_KEY` eklerseniz otomatik yedek olarak kullanılır.)
   `PEXELS_API_KEY` ([ücretsiz](https://www.pexels.com/api/)) eklerseniz arka planlar
   **hareketli Pexels stok videosundan** üretilir; eklemezseniz varsayılan Pollinations kalır.
2. Repo → **Actions** sekmesi → soldan **“Video Uret”** → **Run workflow**.
3. Konuyu/süreyi/karakterleri yaz → **Run workflow**.
4. İş bitince aynı çalıştırma sayfasında **Artifacts → `cizgi-film-video`**'yu indir.

> Görseller iş sırasında otomatik üretilir (Pollinations), YouTube'a yükleme için
> `youtube_yukle` sırrı ayrıca eklenebilir.

## ▶️ Yerel kullanım

```bash
python main.py --konu "Kaan ve Selin ailesiyle Mira ve Ege'nin bahçede topu arayışı" --sure 60
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
