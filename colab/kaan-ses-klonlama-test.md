# Kaan'ın klonlanmış sesini Colab'da test etme

> ⚡ **Kolay yol:** Hazır not defteri [`colab/kaan_ses_klonlama.ipynb`](kaan_ses_klonlama.ipynb).
> Colab'da aç:
> [![Colab'da Aç](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fahrimert99-cmd/angrav-ty/blob/main/colab/kaan_ses_klonlama.ipynb)
> Depoda `sesler/kaan.wav` hazır geldiği için ayrıca dosya yüklemene bile gerek yok.
>
> ⚠️ **Lisans:** XTTS-v2 (CPML) yalnızca **ticari olmayan** kullanım içindir; monetize kanal için Kaan'ı da `edge-tts`'e alın.

Aşağıdaki elle adımlar da aynı işi yapar:

1. https://colab.research.google.com → **Yeni not defteri**
2. Menü: **Çalışma zamanı → Çalışma zamanı türünü değiştir → T4 GPU** → Kaydet
3. Aşağıdaki 3 hücreyi sırayla yapıştırıp çalıştırın (▶️).

## Hücre 1 — Kurulum
```python
!pip install -q coqui-tts
```
(2-3 dakika sürer, birkaç uyarı normaldir)

## Hücre 2 — Ses örneğinizi yükleyin
```python
from google.colab import files
print("kaan.wav dosyasini secin (WhatsApp sesli mesajindan turetilen ornek):")
yuklenen = files.upload()   # acilan pencereden sesler/kaan.wav dosyasini secin
ornek_ses = list(yuklenen.keys())[0]
print("Yuklendi:", ornek_ses)
```

## Hücre 3 — Klonla ve test et
```python
from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
tts.tts_to_file(
    text="Merhaba! Ben Kaan, bu ailenin babasiyim. Bugun cok guzel bir gun.",
    speaker_wav=ornek_ses,
    language="tr",
    file_path="kaan_klon_test.wav",
)

from IPython.display import Audio
Audio("kaan_klon_test.wav")   # tarayicida dinleyebilirsiniz
```

Ses beğenilirse, tüm bölümü Kaan'ın klonlanmış sesiyle üretmek için:

## Hücre 4 (opsiyonel) — Tüm projeyi klonla ve tam üretim yap
```python
!git clone https://github.com/fahrimert99-cmd/angrav-ty.git
%cd angrav-ty
!pip install -r requirements.txt
!pip install -q coqui-tts   # requirements.txt'te opsiyonel oldugu icin ayrica kurulur

# sesler/kaan.wav'i az once yukledigimiz dosyayla degistir
import shutil
shutil.copy(f"../{ornek_ses}", "sesler/kaan.wav")

# config/ayarlar.yaml'i olusturup Claude anahtarinizi girin (sol panelden
# dosya gezgininde config/ayarlar.ornek.yaml'i kopyalayip duzenleyebilirsiniz)
!cp config/ayarlar.ornek.yaml config/ayarlar.yaml
# -> config/ayarlar.yaml icinde claude_api_key alanina kendi anahtarinizi yazin

!python main.py --konu "Kaan ve Selin'in cocuklari Mira ile Ege bahcede saklambac oynuyor" --sure 60
```

Çıktı `cikti/` klasöründe oluşur; sol panelden indirebilirsiniz.
