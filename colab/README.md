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

5. `config/ayarlar.yaml` dosyasını oluşturup Gemini anahtarınızı girin
   (Colab'da sol paneldeki dosya gezgininden düzenleyebilirsiniz).

6. Bir bölüm üretin:

```python
!python main.py --konu "Batu ve Bobi parkta topu arıyor" --sure 60
```

7. Çıktı `cikti/` klasöründe oluşur; sol panelden indirebilirsiniz.

## Not
- Ücretsiz Colab oturumları zaman sınırlıdır; uzun işleri parça parça çalıştırın.
- Model dosyaları büyük olduğundan `.gitignore` bunları GitHub'a göndermez;
  her Colab oturumunda yeniden indirilir.
