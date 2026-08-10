"""
YouTube'a yukleme (YouTube Data API v3).
Ilk calistirmada tarayicidan izin ister, token'i config/token.json'a kaydeder.

Hazirlik:
  1. Google Cloud Console'da proje ac, "YouTube Data API v3"u etkinlestir.
  2. OAuth istemcisi (Masaustu) olustur, client_secret.json indir -> config/.
"""
import pickle
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

KAPSAM = ["https://www.googleapis.com/auth/youtube.upload"]


def _servis(ayar: dict):
    token = Path("config/token.json")
    kimlik = None
    if token.exists():
        import google.auth.transport.requests
        from google.oauth2.credentials import Credentials
        kimlik = Credentials.from_authorized_user_file(str(token), KAPSAM)
    if not kimlik or not kimlik.valid:
        akis = InstalledAppFlow.from_client_secrets_file(
            ayar["yukleme"]["client_secret"], KAPSAM)
        kimlik = akis.run_local_server(port=0)
        token.write_text(kimlik.to_json())
    return build("youtube", "v3", credentials=kimlik)


def yukle(video_yolu: str, baslik: str, aciklama: str, ayar: dict,
          etiketler=None) -> str:
    servis = _servis(ayar)
    govde = {
        "snippet": {
            "title": baslik,
            "description": aciklama,
            "tags": etiketler or ["cizgi film", "cocuk", "egitici"],
            "categoryId": "1",  # Film & Animation
        },
        "status": {"privacyStatus": ayar["yukleme"].get("gizlilik", "private"),
                   "selfDeclaredMadeForKids": True},
    }
    istek = servis.videos().insert(
        part="snippet,status", body=govde,
        media_body=MediaFileUpload(video_yolu, resumable=True),
    )
    yanit = istek.execute()
    return f"https://youtu.be/{yanit['id']}"
