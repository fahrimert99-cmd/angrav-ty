# Google Colab ile Ücretsiz GPU'da Çalıştırma

Ağır adımlar (SadTalker animasyonu, Whisper altyazı, Stable Diffusion) ekran
kartı ister. Bilgisayarınızda güçlü bir GPU yoksa **Google Colab'ın ücretsiz
GPU'sunu** kullanın.

## Adımlar

1. https://colab.research.google.com adresine gidin → yeni not defteri.
2. Menü: **Çalışma zamanı → Çalışma zamanı türünü değiştir → T4 GPU**.
3. Depoyu klonlayın ve bağımlılıkları kurun:

```python
!git clone https://github.com/fahrimert99-cmd/-izgi-film.git
%cd -izgi-film
!pip install -r requirements.txt
```

4. **(Önce bunu deneyin)** İlk uçtan uca videoyu **kurulumsuz** almak için
   `config/ayarlar.yaml` içinde `animasyon.motor: "basit"` bırakın. Bu, dudak
   senkronu olmadan görsel + ses'ten videoyu garanti üretir. Her şeyin çalıştığını
   gördükten sonra aşağıdaki SadTalker kurulumunu yapıp `motor: "sadtalker"`e
   geçebilirsiniz.

4b. **SadTalker** kurulumu (dudak senkronlu konuşan karakter için, opsiyonel):

```python
!git clone https://github.com/OpenTalker/SadTalker.git
%cd SadTalker
!pip install -r requirements.txt
!bash scripts/download_models.sh
%cd ..
```

4c. **XTTS ses klonlama** kurulumu (bir karakterin sesini kendi ses örneğinizden
    klonlamak için, opsiyonel). Orijinal `TTS` (Coqui) paketi 2024'te durduruldu
    ve artık güncel Python sürümleriyle (yerel Python 3.14 dahil) kurulmuyor;
    bunun yerine topluluk tarafından sürdürülen **`coqui-tts`** paketini kurun
    (aynı kod tabanı, aynı `from TTS.api import TTS` importu):

```python
!pip install coqui-tts
```

`sesler/<slug>.wav` altına 10-30 saniyelik net, tek kişilik bir ses örneği
koyun (örn. `sesler/kaan.wav` — depoda hazır), ilgili karakterin
`config/karakterler.json` içindeki `"ses"` alanının bu dosyayı gösterdiğinden
emin olun, ve `config/ayarlar.yaml` içinde `seslendirme.motor: "xtts"` yapın.
Bu motor **tüm** karakterler için geçerli olur — klonlanmamış diğer
karakterlerin de `sesler/<slug>.wav` örneği olmalı, yoksa hata verir.

5. `config/ayarlar.yaml` dosyasını oluşturup Claude/Gemini anahtarınızı girin
   (Colab'da sol paneldeki dosya gezgininden düzenleyebilirsiniz).

6. Bir bölüm üretin:

```python
!python main.py --konu "Kaan ve Selin'in çocukları Mira ile Ege bahçede saklambaç oynuyor" --sure 60
```

7. Çıktı `cikti/` klasöründe oluşur; sol panelden indirebilirsiniz.

## Not
- Ücretsiz Colab oturumları zaman sınırlıdır; uzun işleri parça parça çalıştırın.
- Model dosyaları büyük olduğundan `.gitignore` bunları GitHub'a göndermez;
  her Colab oturumunda yeniden indirilir.
