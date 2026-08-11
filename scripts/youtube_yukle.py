"""
YOUTUBE VIDEO YÜKLEME SCRIPTİ
==============================
GitHub Actions CI ortamında otomatik çalışır.
YOUTUBE_TOKEN_JSON ve YOUTUBE_OAUTH_JSON env değişkenlerini kullanır.

Kullanım (workflow içinden):
    python scripts/youtube_yukle.py \
        --video cikti/son_video.mp4 \
        --baslik "Pixar Çizgi Film - Bölüm 1" \
        --aciklama "Otomatik üretildi." \
        --etiketler "Çizgi Film,Pixar,AI,Otonom"

Gereksinimler:
    pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
MAX_RETRY = 5


def kimlik_bilgileri_al() -> Credentials:
    """
    Kimlik bilgilerini şu sırayla yükler:
    1) YOUTUBE_TOKEN_JSON ortam değişkeni (CI ortamı için)
    2) token.json dosyası (yerel geliştirme için)
    """
    token_json_str = os.environ.get("YOUTUBE_TOKEN_JSON", "").strip()
    oauth_json_str = os.environ.get("YOUTUBE_OAUTH_JSON", "").strip()

    if token_json_str:
        print("✅ YOUTUBE_TOKEN_JSON ortam değişkeninden token yükleniyor...")
        try:
            token_data = json.loads(token_json_str)
        except json.JSONDecodeError:
            # Dosya yolu olabilir
            with open(token_json_str, encoding="utf-8") as f:
                token_data = json.load(f)
    elif Path("token.json").exists():
        print("✅ token.json dosyasından token yükleniyor...")
        with open("token.json", encoding="utf-8") as f:
            token_data = json.load(f)
    else:
        print("❌ HATA: Token bilgisi bulunamadı!")
        print("   YOUTUBE_TOKEN_JSON ortam değişkeni veya token.json dosyası gerekli.")
        print("   Yerel ortamda python scripts/youtube_token_al.py çalıştırın.")
        sys.exit(1)

    # client_id / client_secret - önce token içinden, yoksa YOUTUBE_OAUTH_JSON'dan al
    client_id = token_data.get("client_id")
    client_secret = token_data.get("client_secret")

    if (not client_id or not client_secret) and oauth_json_str:
        try:
            oauth_data = json.loads(oauth_json_str)
            installed = oauth_data.get("installed", oauth_data.get("web", {}))
            client_id = client_id or installed.get("client_id")
            client_secret = client_secret or installed.get("client_secret")
        except json.JSONDecodeError:
            pass

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=client_id,
        client_secret=client_secret,
        scopes=token_data.get("scopes", SCOPES),
    )

    # Token süresi dolmuşsa otomatik yenile
    if creds.expired and creds.refresh_token:
        print("🔄 Token yenileniyor...")
        creds.refresh(Request())
        print("✅ Token yenilendi.")

    return creds


def video_yukle(
    video_yolu: str,
    baslik: str,
    aciklama: str,
    etiketler: list[str],
    kategori_id: str = "22",        # 22 = People & Blogs
    gizlilik: str = "public",
) -> str:
    """Videoyu YouTube'a yükler, video ID'sini döndürür."""

    if not Path(video_yolu).exists():
        print(f"❌ HATA: Video dosyası bulunamadı: {video_yolu}")
        sys.exit(1)

    creds = kimlik_bilgileri_al()
    youtube = build("youtube", "v3", credentials=creds)

    govde = {
        "snippet": {
            "title": baslik[:100],          # Maksimum 100 karakter
            "description": aciklama[:5000], # Maksimum 5000 karakter
            "tags": etiketler[:500],
            "categoryId": kategori_id,
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr",
        },
        "status": {
            "privacyStatus": gizlilik,
            "selfDeclaredMadeForKids": False,
        },
    }

    medya = MediaFileUpload(
        video_yolu,
        mimetype="video/mp4",
        chunksize=8 * 1024 * 1024,  # 8 MB parça
        resumable=True,
    )

    istek = youtube.videos().insert(
        part=",".join(govde.keys()),
        body=govde,
        media_body=medya,
    )

    print(f"\n🎬 YouTube yüklemesi başlıyor...")
    print(f"   Dosya : {video_yolu}")
    print(f"   Başlık: {baslik}")
    print(f"   Gizlilik: {gizlilik}")
    print()

    yanit = None
    yeniden_dene = 0
    hatalar = (HttpError,)

    while yanit is None:
        try:
            durum, yanit = istek.next_chunk()
            if durum:
                yuzde = int(durum.progress() * 100)
                print(f"   Yükleniyor... %{yuzde}", end="\r", flush=True)
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504] and yeniden_dene < MAX_RETRY:
                yeniden_dene += 1
                bekleme = 2 ** yeniden_dene
                print(f"\n⚠️  HTTP {e.resp.status} - {bekleme}s beklenip tekrar deneniyor...")
                time.sleep(bekleme)
            else:
                print(f"\n❌ YouTube yükleme hatası: {e}")
                raise

    video_id = yanit["id"]
    print(f"\n\n✅ Video başarıyla yüklendi!")
    print(f"   Video ID  : {video_id}")
    print(f"   YouTube   : https://www.youtube.com/watch?v={video_id}")
    print(f"   Studio    : https://studio.youtube.com/video/{video_id}/edit")
    return video_id


def main():
    p = argparse.ArgumentParser(description="Videoyu YouTube'a yükle")
    p.add_argument("--video",     required=True,  help="MP4 dosya yolu")
    p.add_argument("--baslik",    required=True,  help="Video başlığı")
    p.add_argument("--aciklama",  default="Bu video yapay zekâ ile otomatik üretilmiştir. 🤖✨\n\n"
                                          "#AI #Pixar #ÇizgiFilm #OtonomVideo",
                   help="Video açıklaması")
    p.add_argument("--etiketler", default="AI,Pixar,Çizgi Film,Otonom,YouTube",
                   help="Virgülle ayrılmış etiketler")
    p.add_argument("--gizlilik", default="public",
                   choices=["public", "private", "unlisted"],
                   help="Gizlilik ayarı (varsayılan: public)")
    args = p.parse_args()

    etiket_listesi = [e.strip() for e in args.etiketler.split(",") if e.strip()]
    video_id = video_yukle(
        video_yolu=args.video,
        baslik=args.baslik,
        aciklama=args.aciklama,
        etiketler=etiket_listesi,
        gizlilik=args.gizlilik,
    )

    # GitHub Actions için video ID'sini GITHUB_OUTPUT'a yaz
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"video_id={video_id}\n")
        print(f"\n📤 Video ID GitHub output'a yazıldı: video_id={video_id}")


if __name__ == "__main__":
    main()
