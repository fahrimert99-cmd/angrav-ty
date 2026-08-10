#!/usr/bin/env python
"""
Test: Senaryo oluştur + Seslendirme (bez animation/montage)
Animation ve montage için SadTalker gerekli.
"""
import json
from pathlib import Path
from src import ayarlari_yukle, karakterleri_yukle, cikti_klasoru
from src import senaryo as m_senaryo
from src import seslendirme as m_ses

def test_senaryo_ve_seslendirme():
    print("=" * 70)
    print("TEST: Senaryo Uretimi + Seslendirme Pipeline")
    print("=" * 70)
    
    # 1. Ayarları ve karakterleri yükle
    ayar = ayarlari_yukle()
    karakterler = karakterleri_yukle()
    print(f"\n[1/3] Ayarlar ve karakterler yuklendi ({len(karakterler)} karakter)")
    
    # 2. Senaryo oluştur (Gemini API ile)
    konu = "Batu ve Bobi parkta oynamıyorlar"
    sure_sn = 30
    
    print(f"\n[2/3] Senaryo olusturuluyor...")
    print(f"      Konu: {konu}")
    print(f"      Sure: {sure_sn} saniye")
    
    try:
        senaryo = m_senaryo.uret(konu, karakterler, ayar, sure_sn, deneme_sayisi=1)
        print(f"      Baslik: {senaryo['baslik']}")
        print(f"      Sahneler: {len(senaryo['sahneler'])}")
        
        # Senaryo yapısını doğrula
        for i, sahne in enumerate(senaryo['sahneler'], 1):
            replik_sayisi = len(sahne.get('replikler', []))
            print(f"        Sahne {i}: {sahne.get('mekan', 'N/A')} ({replik_sayisi} replik)")
        
        # Çıktı klasörü oluştur
        cikti = cikti_klasoru(f"test_{senaryo['baslik'][:20]}")
        
        # Senaryo JSON'ı kaydet
        senaryo_dosya = cikti / "senaryo.json"
        senaryo_dosya.write_text(
            json.dumps(senaryo, ensure_ascii=False, indent=2), 
            encoding="utf-8"
        )
        print(f"\n      Senaryo kaydedildi: {senaryo_dosya}")
        
        # 3. Seslendirme (edge-tts ile - SadTalker olmadan)
        print(f"\n[3/3] Replikler seslendiriliyor (edge-tts)...")
        try:
            senaryo = m_ses.senaryoyu_seslendir(senaryo, karakterler, ayar, cikti)
            print(f"      Ses dosyaları uretildi!")
            
            # Ses dosyalarını listele
            ses_klasor = cikti / "ses"
            ses_dosyalari = sorted(ses_klasor.glob("*.mp3"))
            print(f"      {len(ses_dosyalari)} ses dosyasi:")
            for ses in ses_dosyalari[:3]:
                size_kb = ses.stat().st_size / 1024
                print(f"        - {ses.name} ({size_kb:.1f} KB)")
            
            # Tamamlanan senaryo (ses_yolu'ları içeriyor)
            senaryo_son = cikti / "senaryo_ses.json"
            senaryo_son.write_text(
                json.dumps(senaryo, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"\n      Tamamlanan senaryo kaydedildi: {senaryo_son}")
            
            print("\n" + "=" * 70)
            print("TEST BASARILI!")
            print("=" * 70)
            print(f"\nCikti klasoru: {cikti}")
            print("\nSonraki adimlar:")
            print("  1. SadTalker/Wav2Lip ile animasyon")
            print("  2. MoviePy ile montaj")
            print("  3. Altyazi ve YouTube yukleme")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"\n[HATA] Seslendirme basarisiz: {e}")
            return False
    
    except Exception as e:
        print(f"\n[HATA] Senaryo uretimi basarisiz: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_senaryo_ve_seslendirme()
    exit(0 if success else 1)
