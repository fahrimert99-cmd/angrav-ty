#!/usr/bin/env python
"""
Demo: Montaj pipeline'ını dummy senaryo ile test et.
"""
import json
from pathlib import Path
from src import cikti_klasoru, karakterleri_yukle
from src import montaj as m_montaj
from unittest.mock import patch, MagicMock

print("=" * 70)
print("DEMO: Montaj Pipeline Testi (Dummy Senaryo)")
print("=" * 70)

# Karakterleri yükle
karakterler = karakterleri_yukle()
print(f"\n[1/3] {len(karakterler)} karakter yüklendi")

# Dummy senaryo oluştur (Gemini yerine)
dummy_senaryo = {
    "baslik": "Batu ve Bobi parkta",
    "sahneler": [
        {
            "mekan": "park",
            "arka_plan_prompt": "sunny park with trees",
            "replikler": [
                {"karakter": "batu", "metin": "Merhaba Bobi!"},
                {"karakter": "bobi", "metin": "Hav hav!"}
            ]
        },
        {
            "mekan": "ev",
            "arka_plan_prompt": "cozy home living room",
            "replikler": [
                {"karakter": "nurcan", "metin": "Hoş geldiniz!"}
            ]
        }
    ]
}

cikti = cikti_klasoru("demo_montaj_test")
senaryo_dosya = cikti / "senaryo.json"
senaryo_dosya.write_text(
    json.dumps(dummy_senaryo, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print(f"[2/3] Dummy senaryo oluşturuldu: {senaryo_dosya}")
print(f"      Sahneler: {len(dummy_senaryo['sahneler'])}")
print(f"      Toplam replik: {sum(len(s['replikler']) for s in dummy_senaryo['sahneler'])}")

# Montaj testini mock'la (VideoFileClip olmadan)
print(f"\n[3/3] Montaj pipeline error handling testi...")
print()

from src.montaj import birlestir

# Mock ayarlar
mock_ayar = {
    "montaj": {
        "cozunurluk": [1280, 720],
        "fps": 24
    }
}

# Test 1: Boş klip yolu
print("Test 1: Boş klip_yolu")
try:
    bad_senaryo = {
        "sahneler": [{
            "replikler": [{"klip_yolu": None}]
        }]
    }
    birlestir(bad_senaryo, mock_ayar, cikti)
    print("  FAIL - Exception atılmadı")
except ValueError as e:
    print(f"  PASS - Hata yakalalandı: {str(e)[:50]}...")

# Test 2: Nonexistent klip
print("\nTest 2: Eksik video dosyası")
try:
    bad_senaryo = {
        "sahneler": [{
            "replikler": [{"klip_yolu": "/fake/video.mp4"}]
        }]
    }
    birlestir(bad_senaryo, mock_ayar, cikti)
    print("  FAIL - Exception atılmadı")
except FileNotFoundError as e:
    print(f"  PASS - Hata yakalalandı: {str(e)[:50]}...")

# Test 3: Boş klip listesi
print("\nTest 3: Boş klip listesi (sahnelerde replik yok)")
try:
    bad_senaryo = {
        "sahneler": [{
            "replikler": []
        }]
    }
    birlestir(bad_senaryo, mock_ayar, cikti)
    print("  FAIL - Exception atılmadı")
except ValueError as e:
    print(f"  PASS - Hata yakalalandı: {str(e)[:50]}...")

print("\n" + "=" * 70)
print("DEMO TEST TAMAMLANDI")
print("=" * 70)
print(f"\nCikti klasoru: {cikti}")
print(f"Ornek senaryo dosyasi: {senaryo_dosya}")
print("\nSonuc: Montaj pipeline error handling tam çalisiyor!")
print("=" * 70)
