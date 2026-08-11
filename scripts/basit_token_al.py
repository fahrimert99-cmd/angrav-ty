"""
Basit YouTube OAuth Token Alma Scripti
PKCE olmadan, doğrudan requests ile token alır.
"""
import json
import sys
import webbrowser
from urllib.parse import urlencode

import requests

# client_secret.json oku
with open("client_secret.json", "r", encoding="utf-8") as f:
    data = json.load(f)

installed = data.get("installed", data.get("web", {}))
CLIENT_ID = installed["client_id"]
CLIENT_SECRET = installed["client_secret"]
TOKEN_URI = installed.get("token_uri", "https://oauth2.googleapis.com/token")
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"

# 1) Yetkilendirme URL'si olustur (PKCE yok, basit)
params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPE,
    "access_type": "offline",
    "prompt": "consent",
}
auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

print("=" * 60)
print("YOUTUBE YETKILENDIRME")
print("=" * 60)
print()
print("Tarayicinizda acilan sayfada izin verin.")
print("Sayfada gosterilen KODU buraya yapisitirin.")
print()

# Tarayici ac
webbrowser.open(auth_url)

# 2) Kullanicidan kodu al
code = input("Yetkilendirme kodunu yapisitirin: ").strip()
if not code:
    print("Kod bos, iptal edildi.")
    sys.exit(1)

# 3) Kodu token'a cevir (PKCE yok, basit POST)
token_response = requests.post(TOKEN_URI, data={
    "code": code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
})

if token_response.status_code != 200:
    print(f"HATA: {token_response.status_code}")
    print(token_response.text)
    sys.exit(1)

token_data = token_response.json()

# 4) token.json olarak kaydet
result = {
    "token": token_data["access_token"],
    "refresh_token": token_data.get("refresh_token"),
    "token_uri": TOKEN_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scopes": [SCOPE],
}

with open("token.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print()
print("=" * 60)
print("TOKEN BASARIYLA OLUSTURULDU!")
print("=" * 60)
print(f"Refresh Token: {result['refresh_token'][:20]}...")
print("token.json dosyasi kaydedildi.")
