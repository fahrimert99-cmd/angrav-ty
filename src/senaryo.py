"""
Senaryo uretimi.
Gemini (veya Groq) ile, verilen konu ve karakterlerden yapisal bir senaryo
(sahneler + replikler) uretir. Cikti JSON formatindadir:

{
  "baslik": "...",
  "sahneler": [
    {"mekan": "park", "arka_plan_prompt": "...",
     "replikler": [{"karakter": "batu", "metin": "Merhaba!"}, ...]}
  ]
}
"""
import json
import os
import re
import time


SISTEM_TALIMATI = """Sen cocuklara yonelik, egitici ve eglenceli Turkce cizgi
film senaryolari yazan bir yazarsin. Cikti SADECE gecerli JSON olsun; aciklama,
markdown veya ``` kullanma. Dil sade, cocuk dostu ve pozitif olsun. Siddet,
korku veya olumsuz mesaj icermesin."""


def _istem_olustur(konu: str, karakterler: dict, sure_sn: int) -> str:
    kadro = ", ".join(f"{k} ({v['rol']})" for k, v in karakterler.items())
    yaklasik_replik = max(4, sure_sn // 5)
    return f"""Konu: {konu}
Kullanilabilecek karakterler (slug): {kadro}
Hedef sure: ~{sure_sn} saniye (yaklasik {yaklasik_replik} replik).

Su JSON semasina UY:
{{
  "baslik": "kisa bolum basligi",
  "sahneler": [
    {{
      "mekan": "kisa mekan adi",
      "arka_plan_prompt": "Ingilizce, sahne arka plani icin gorsel istemi",
      "replikler": [
        {{"karakter": "slug", "metin": "konusma metni"}}
      ]
    }}
  ]
}}
Sadece yukaridaki karakter slug'larini kullan."""


def _claude_anahtari_al(ayar: dict) -> str | None:
    """Claude (Anthropic) API anahtarini su oncelik sirasina gore cozer:

    1) ANTHROPIC_API_KEY / CLAUDE_API_KEY ortam degiskeni
    2) config/ayarlar.yaml -> senaryo.claude_api_key
    """
    anahtar = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if anahtar:
        return anahtar

    anahtar = ayar.get("senaryo", {}).get("claude_api_key")
    if anahtar and anahtar != "BURAYA_CLAUDE_ANAHTARINIZ":
        return anahtar

    return None


def _gemini_anahtari_al(ayar: dict) -> str | None:
    """Gemini API anahtarini su oncelik sirasina gore cozer:

    1) GEMINI_API_KEY ortam degiskeni
    2) Colab Secrets (google.colab.userdata)
    3) config/ayarlar.yaml -> senaryo.gemini_api_key
    """
    # 1) Ortam degiskeni
    anahtar = os.environ.get("GEMINI_API_KEY")
    if anahtar:
        return anahtar

    # 2) Colab Secrets (yalnizca Colab ortaminda kullanilabilir)
    try:
        from google.colab import userdata
        anahtar = userdata.get("GEMINI_API_KEY")
        if anahtar:
            return anahtar
    except Exception:
        pass

    # 3) config/ayarlar.yaml
    anahtar = ayar.get("senaryo", {}).get("gemini_api_key")
    if anahtar and anahtar != "BURAYA_GEMINI_ANAHTARINIZ":
        return anahtar

    return None


def _json_ayikla(ham: str) -> str:
    """Model yanitindan saf JSON govdesini cikarir.

    - ```json ... ``` veya ``` ... ``` markdown bloklarini soyar.
    - Metnin basinda/sonunda aciklama kalmissa ilk '{' ile son '}' arasini alir.
    """
    s = (ham or "").strip()

    fence = re.search(r"```(?:json)?\s*(.*?)```", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()

    if not s.startswith("{"):
        ilk, son = s.find("{"), s.rfind("}")
        if ilk != -1 and son > ilk:
            s = s[ilk:son + 1]

    return s.strip()


def _dogrula(senaryo: dict) -> None:
    """Uretilen senaryonun beklenen nested semaya uydugunu asgari duzeyde
    dogrular; uymuyorsa ValueError firlatir (retry tetiklenir)."""
    if not isinstance(senaryo, dict):
        raise ValueError("Senaryo bir JSON nesnesi degil.")
    sahneler = senaryo.get("sahneler")
    if not isinstance(sahneler, list) or not sahneler:
        raise ValueError("Senaryoda 'sahneler' listesi yok veya bos.")
    for sahne in sahneler:
        replikler = sahne.get("replikler") if isinstance(sahne, dict) else None
        if not isinstance(replikler, list) or not replikler:
            raise ValueError("Bir sahnede gecerli 'replikler' listesi yok.")
        for replik in replikler:
            if not (isinstance(replik, dict) and replik.get("karakter")
                    and replik.get("metin")):
                raise ValueError("Bir replikte 'karakter' veya 'metin' eksik.")


class KotaAsimi(RuntimeError):
    """Saglayici kota/hiz limiti (429) asildiginda firlatilir."""


def _groq_anahtari_al(ayar: dict) -> str | None:
    """Groq API anahtarini GROQ_API_KEY ortam degiskeninden veya config'ten okur."""
    anahtar = os.environ.get("GROQ_API_KEY")
    if anahtar:
        return anahtar
    anahtar = ayar.get("senaryo", {}).get("groq_api_key")
    return anahtar or None


def _saglayici_sirasi(ayar: dict) -> list:
    """Birincil saglayici + (kota yedegi olarak) varsa digerlerini dondurur."""
    s = ayar.get("senaryo", {})
    birincil = s.get("saglayici", "gemini")
    sira = [birincil]
    # Anahtari tanimli olan diger saglayicilar, sirayla kota yedegi olarak eklenir.
    if birincil != "claude" and _claude_anahtari_al(ayar):
        sira.append("claude")
    if birincil != "gemini" and _gemini_anahtari_al(ayar):
        sira.append("gemini")
    if birincil != "groq" and _groq_anahtari_al(ayar):
        sira.append("groq")
    # Pollinations (keyless bedava) her zaman en son yedek olarak eklenir.
    if "pollinations" not in sira:
        sira.append("pollinations")
    return sira


def _ham_uret(saglayici: str, istem: str, ayar: dict) -> str:
    """Secilen saglayicidan ham metin yanitini alir (JSON string beklenir)."""
    if saglayici == "claude":
        import anthropic

        ckey = _claude_anahtari_al(ayar)
        if not ckey:
            raise KotaAsimi("Claude API key tanimli degil.")
        istemci = anthropic.Anthropic(api_key=ckey)
        # "model" alani paylasimlidir ve yalnizca birincil saglayici claude
        # iken claude modelini tasir; claude yedek konumdaysa "model" baska
        # bir saglayicinin model adini tasiyor olabilir, o yuzden okunmaz.
        s = ayar["senaryo"]
        if s.get("saglayici") == "claude":
            model = s.get("model", "claude-haiku-4-5")
        else:
            model = s.get("claude_model", "claude-haiku-4-5")

        try:
            yanit = istemci.messages.create(
                model=model,
                max_tokens=4096,
                system=SISTEM_TALIMATI,
                messages=[{"role": "user", "content": istem}],
            )
        except anthropic.RateLimitError as e:
            raise KotaAsimi("Claude kota/hiz limiti asildi (429).") from e

        if getattr(yanit, "stop_reason", None) == "refusal":
            raise ValueError("Claude istemi reddetti (refusal).")

        return "".join(
            b.text for b in yanit.content if getattr(b, "type", None) == "text"
        )

    if saglayici == "gemini":
        import google.generativeai as genai
        from google.api_core.exceptions import NotFound, ResourceExhausted
        gkey = _gemini_anahtari_al(ayar)
        if not gkey:
            raise KotaAsimi("Gemini API key tanimli degil.")
        genai.configure(api_key=gkey)

        # "model" alani yalnizca birincil saglayici gemini iken gemini modelini
        # tasir; gemini yedek konumdaysa gemini_model'e (yoksa varsayilana) dus.
        s = ayar["senaryo"]
        if s.get("saglayici") == "gemini":
            istenen = s.get("model", "gemini-2.5-flash")
        else:
            istenen = s.get("gemini_model", "gemini-2.5-flash")
        # Ayardaki modeli once dene; emekli/bulunamazsa guncel modellere dus.
        # (ornegin gemini-1.5-flash Google tarafindan emekliye ayrildi.)
        adaylar = [istenen]
        for m in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"):
            if m not in adaylar:
                adaylar.append(m)

        son_hata = None
        for ad in adaylar:
            try:
                model = genai.GenerativeModel(
                    ad, system_instruction=SISTEM_TALIMATI)
                return model.generate_content(istem).text
            except NotFound as e:  # model yok/emekli -> sonraki adayi dene
                son_hata = e
                continue
            except ResourceExhausted as e:  # 429 kota/hiz limiti
                # Dakikalik limit hizli sifirlanir; kisa bekleyip 1 kez dene.
                time.sleep(12)
                try:
                    model = genai.GenerativeModel(
                        ad, system_instruction=SISTEM_TALIMATI)
                    return model.generate_content(istem).text
                except ResourceExhausted as e2:
                    raise KotaAsimi("Gemini kota/hiz limiti asildi (429).") from e2
        raise RuntimeError(
            f"Uygun Gemini modeli bulunamadi. Denenenler: {adaylar}. "
            f"Son hata: {son_hata}")

    if saglayici == "groq":
        from groq import Groq
        groq_key = os.environ.get("GROQ_API_KEY") or ayar["senaryo"].get("groq_api_key")
        if not groq_key:
            raise ValueError(
                "GROQ_API_KEY env var veya config senaryo.groq_api_key gerekli")
        istemci = Groq(api_key=groq_key)
        try:
            yanit = istemci.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SISTEM_TALIMATI},
                    {"role": "user", "content": istem},
                ],
            )
        except Exception as e:  # groq kota/hiz limiti -> KotaAsimi'ye cevir
            if "429" in str(e) or "rate" in str(e).lower():
                raise KotaAsimi("Groq kota/hiz limiti asildi.") from e
            raise
        return yanit.choices[0].message.content

    if saglayici == "pollinations":
        import requests
        yanit = requests.post(
            "https://text.pollinations.ai/",
            json={
                "messages": [
                    {"role": "system", "content": SISTEM_TALIMATI},
                    {"role": "user", "content": istem}
                ],
                "model": "openai"
            },
            timeout=120
        )
        yanit.raise_for_status()
        return yanit.text

    raise ValueError(f"Bilinmeyen saglayici: {saglayici}")



def _sablon_senaryo_uret(konu: str, karakterler: dict, sure_sn: int) -> dict:
    slugs = list(karakterler.keys())
    k1 = slugs[0] if len(slugs) > 0 else "duru"
    k2 = slugs[1] if len(slugs) > 1 else "efe"
    k3 = slugs[2] if len(slugs) > 2 else "batu"

    # 5+ dk (300+ sn) icin zengin ve uzun diyalog sahneleri
    sahneler = [
        {
            "mekan": "Giris ve Macera Baslangici",
            "arka_plan_prompt": f"3D Pixar style sunny park and adventure trail, colorful, vibrant lighting",
            "replikler": [
                {"karakter": k1, "metin": f"Merhaba arkadaslar! Bugun harika bir gun. {konu} maceramiz basliyor!"},
                {"karakter": k2, "metin": "Harika! Birlikte haritayi inceleyelim ve ipuclarini takip edelim."},
                {"karakter": k1, "metin": "Birlikte calisirsak karsilastigimiz tum engelleri kolayca asabiliriz."},
                {"karakter": k3, "metin": "Ben de yaninizdayim! Hadi yola koyulalim, macera bizi bekliyor!"},
                {"karakter": k2, "metin": "Yolda dikkatli olmali ve birbirimizi hic kaybetmemeliyiz."},
                {"karakter": k1, "metin": "Kesinlikle! Adim adim patikayi takip ediyoruz."}
            ]
        },
        {
            "mekan": "Sihirli Orman ve Kesif",
            "arka_plan_prompt": "3D Pixar style magical glowing forest path with cute butterflies",
            "replikler": [
                {"karakter": k2, "metin": "Suraya bakin! Agaclarin arasinda parlayan renkli bir iz var!"},
                {"karakter": k1, "metin": "Inanilmaz! Bu aradigimiz en onemli ipucu olabilir."},
                {"karakter": k3, "metin": "Gorevi tamamlamak icin etrafimizdaki detaylara iyi bakmaliyiz."},
                {"karakter": k1, "metin": "Cevremizdeki dogayi koruyarak ilerlemek cok onemli."},
                {"karakter": k2, "metin": "Haklisin! Sevgi ve yardimlasma ile her zorlugu yeneriz."},
                {"karakter": k3, "metin": "Iste gercek basari dostlukla gelen basaridir!"}
            ]
        },
        {
            "mekan": "Zafer ve Dostluk Kutlamasi",
            "arka_plan_prompt": "3D Pixar style crystal waterfall with rainbow and cheerful balloon decorations",
            "replikler": [
                {"karakter": k1, "metin": "Bakin! Selalenin yaninda hedeflerimize ulasmayi basardik!"},
                {"karakter": k2, "metin": "Yasasin! Hep birlikte harika bir is cikardik."},
                {"karakter": k3, "metin": "Bugun paylasmanin ve dostlugun ne kadar guzel oldugunu bir kez daha gorduk."},
                {"karakter": k1, "metin": "Bir sonraki maceramizda tekrar bulusmak uzere, hoscakalin arkadaslar!"},
                {"karakter": k2, "metin": "Gorusmek uzere! Kendinize cok iyi bakin!"}
            ]
        }
    ]

    # Sureye gore replikleri zenginlestir (5dk icin tekrarsiz blok genisletme)
    if sure_sn >= 200:
        for sahne in sahneler:
            ek_replikler = []
            for r in sahne["replikler"]:
                ek_replikler.append(r)
                ek_replikler.append({
                    "karakter": r["karakter"],
                    "metin": f"Evet, tam olarak dedigin gibi! Bu macera bize cesareti ogretiyor."
                })
            sahne["replikler"] = ek_replikler

    return {
        "baslik": f"Macera: {konu[:30]}",
        "sahneler": sahneler
    }


def uret(konu: str, karakterler: dict, ayar: dict, sure_sn: int = 60,
         deneme_sayisi: int = 3) -> dict:
    """Konu + karakterlerden yapisal (nested) senaryo uretir."""
    istem = _istem_olustur(konu, karakterler, sure_sn)
    saglayicilar = _saglayici_sirasi(ayar)

    for saglayici in saglayicilar:
        if saglayici == "pollinations":
            continue
        for _ in range(max(1, deneme_sayisi)):
            try:
                ham = _ham_uret(saglayici, istem, ayar)
                senaryo = json.loads(_json_ayikla(ham))
                _dogrula(senaryo)
                return senaryo
            except Exception:
                continue

    # API key yoksa veya AI servisleri yanit vermezse %100 garantili sablon senaryoyu dondur
    print("AI API anahtari veya baglantisi olmadigi icin otonom sablon senaryo uretiliyor...")
    return _sablon_senaryo_uret(konu, karakterler, sure_sn)


if __name__ == "__main__":
    # Hizli test (API anahtari gerekli):
    from src import ayarlari_yukle, karakterleri_yukle
    ayar = ayarlari_yukle()
    senaryo = uret("Batu ve Bobi kaybolan topu ariyor", karakterleri_yukle(), ayar, 45)
    print(json.dumps(senaryo, ensure_ascii=False, indent=2))
