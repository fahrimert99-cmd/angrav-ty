"""
ElevenLabs TTS: Turkce metin -> dogal ses (mp3).

edge-tts'e gore cok daha dogal Turkce ses uretir (eleven_multilingual_v2
modeli Turkce'yi destekler). Anahtar KODA GOMULMEZ; ELEVENLABS_API_KEY
ortam degiskeninden okunur (GitHub Actions secret'i).

Kullanim:
    export ELEVENLABS_API_KEY=...
    python ses_eleven.py --metin "Merhaba, ben Kaan!" --cikti klipler/ses.mp3 \
        --voice-id pNInz6obpgDQGcFmaJgB

Not: ElevenLabs ucretsiz katmani API'ye izin verir ama aylik kredi sinirlidir
ve TICARI kullanimda ucretli plan/atif gerekebilir.
"""
import argparse
import os
import sys
from pathlib import Path

import requests

# Varsayilan ses: "Adam" (ElevenLabs ortak/varsayilan erkek sesi). Kendi ses
# kutuphanenizdeki bir voice_id ile degistirebilirsiniz.
VARSAYILAN_VOICE = "pNInz6obpgDQGcFmaJgB"


def uret(metin: str, cikti: str, voice_id: str = VARSAYILAN_VOICE,
         model: str = "eleven_multilingual_v2") -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        sys.exit("HATA: ELEVENLABS_API_KEY ortam degiskeni yok "
                 "(GitHub Actions secret'i olarak ekleyin).")
    if not key.isascii():
        sys.exit("HATA: ELEVENLABS_API_KEY ASCII olmayan karakter iceriyor "
                 "(or. Turkce 'ı/ş/ğ'). Secret'i ElevenLabs'ten yeniden, "
                 "dogru kopyalayin: 'sk_' + sadece Ingilizce harf/rakam, "
                 "bosluk/Turkce karakter olmadan.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": metin,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    print(f"[eleven] seslendiriliyor (voice={voice_id}, model={model})...")
    r = requests.post(url, headers=headers, json=body, timeout=120)
    if r.status_code != 200:
        sys.exit(f"HATA: ElevenLabs (HTTP {r.status_code}): {r.text[:600]}")

    Path(cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(cikti).write_bytes(r.content)
    print(f"[eleven] BITTI -> {cikti} ({len(r.content)} byte)")
    return cikti


def main():
    p = argparse.ArgumentParser(description="ElevenLabs Turkce TTS")
    p.add_argument("--metin", required=True, help="Seslendirilecek Turkce metin")
    p.add_argument("--cikti", default="klipler/ses.mp3", help="Cikti mp3 yolu")
    p.add_argument("--voice-id", default=VARSAYILAN_VOICE, help="ElevenLabs voice_id")
    p.add_argument("--model", default="eleven_multilingual_v2",
                   help="ElevenLabs model (Turkce icin eleven_multilingual_v2)")
    args = p.parse_args()
    uret(args.metin, args.cikti, args.voice_id, args.model)


if __name__ == "__main__":
    sys.exit(main())
