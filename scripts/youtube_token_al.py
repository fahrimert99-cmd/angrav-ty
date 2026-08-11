"""
YOUTUBE TOKEN OLUŞTURUCU
========================
Bu scripti YEREL BİLGİSAYARINIZDA sadece BİR KEZ çalıştırın.
Tarayıcı açılır, Google hesabınızla giriş yapın ve izin verin.
Oluşturulan token.json dosyasının içeriğini kopyalayıp
GitHub Secrets → YOUTUBE_TOKEN_JSON olarak kaydedin.

Kurulum:
    pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client

Kullanım:
    python scripts/youtube_token_al.py
"""

import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

CLIENT_SECRET_DOSYA = Path(__file__).parent.parent / "client_secret.json"
TOKEN_DOSYA = Path(__file__).parent.parent / "token.json"


def token_al():
    # client_secret.json'u kontrol et
    if not CLIENT_SECRET_DOSYA.exists():
        print(f"HATA: {CLIENT_SECRET_DOSYA} bulunamadı!")
        print("Lütfen Google Cloud Console'dan indirdiğiniz client_secret.json dosyasını")
        print("proje kök dizinine koyun.")
        return

    print("=" * 60)
    print("YouTube OAuth Yetkilendirmesi Başlıyor...")
    print("=" * 60)
    print()
    print("Tarayıcınızda bir pencere açılacak.")
    print("Google hesabınızla giriş yapın ve YouTube erişimine izin verin.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_DOSYA), SCOPES
    )

    try:
        # Tarayıcı üzerinden yetkilendirme al
        creds = flow.run_local_server(port=0)
    except Exception:
        print("Tarayıcı açılamadı. Konsol modunda deneniyor...")
        creds = flow.run_console()

    # Token'ı kaydet
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else list(SCOPES),
    }

    with open(TOKEN_DOSYA, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print(f"✅ Token başarıyla kaydedildi: {TOKEN_DOSYA}")
    print("=" * 60)
    print()
    print("ŞİMDİ YAPMANIZ GEREKEN:")
    print("1. token.json dosyasını açın")
    print("2. İçeriğini kopyalayın")
    print("3. GitHub → Repo → Settings → Secrets and variables → Actions")
    print("4. 'New repository secret' tıklayın")
    print("   Ad:    YOUTUBE_TOKEN_JSON")
    print("   Değer: token.json içeriği (tam metin)")
    print("5. 'Add secret' ile kaydedin")
    print()
    print("Refresh token:")
    print(f"  {creds.refresh_token}")


if __name__ == "__main__":
    token_al()
