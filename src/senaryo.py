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


def _gemini_anahtari_al(ayar: dict) -> str:
    """Gemini API anahtarini su oncelik sirasina gore cozer:

    1) GEMINI_API_KEY ortam degiskeni
    2) Colab Secrets (google.colab.userdata)
    3) config/ayarlar.yaml -> senaryo.gemini_api_key

    Anahtar hicbir zaman koda gomulu degildir; yalnizca bu kaynaklardan okunur.
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
        # Colab disinda calisiyoruz ya da secret tanimli degil; sessizce gec.
        pass

    # 3) config/ayarlar.yaml
    anahtar = ayar.get("senaryo", {}).get("gemini_api_key")
    if anahtar and anahtar != "BURAYA_GEMINI_ANAHTARINIZ":
        return anahtar

    raise RuntimeError(
        "Gemini API anahtari bulunamadi. Su sirayla arandi: "
        "GEMINI_API_KEY ortam degiskeni, Colab Secrets (userdata), "
        "config/ayarlar.yaml (senaryo.gemini_api_key)."
    )


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


def _saglayici_sirasi(ayar: dict) -> list:
    """Birincil saglayici + (kota yedegi olarak) varsa digerlerini dondurur."""
    s = ayar.get("senaryo", {})
    birincil = s.get("saglayici", "gemini")
    sira = [birincil]
    # Groq anahtari varsa kota yedegi olarak ekle (ucretsiz).
    if birincil != "groq" and (s.get("groq_api_key") or "").strip():
        sira.append("groq")
    # Pollinations (keyless bedava) her zaman en son yedek olarak eklenir.
    if "pollinations" not in sira:
        sira.append("pollinations")
    return sira


def _ham_uret(saglayici: str, istem: str, ayar: dict) -> str:
    """Secilen saglayicidan ham metin yanitini alir (JSON string beklenir)."""
    if saglayici == "gemini":
        import google.generativeai as genai
        from google.api_core.exceptions import NotFound, ResourceExhausted
        genai.configure(api_key=_gemini_anahtari_al(ayar))

        # Ayardaki modeli once dene; emekli/bulunamazsa guncel modellere dus.
        # (ornegin gemini-1.5-flash Google tarafindan emekliye ayrildi.)
        istenen = ayar["senaryo"].get("model", "gemini-2.5-flash")
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



def uret(konu: str, karakterler: dict, ayar: dict, sure_sn: int = 60,
         deneme_sayisi: int = 3) -> dict:
    """Konu + karakterlerden yapisal (nested) senaryo uretir.

    Model yaniti guvenli sekilde ayiklanip parse edilir; gecersiz JSON veya
    eksik sema durumunda ayni istem `deneme_sayisi` kadar tekrar denenir.
    """
    istem = _istem_olustur(konu, karakterler, sure_sn)
    saglayicilar = _saglayici_sirasi(ayar)

    son_hata = None
    kota_hatasi = False
    for saglayici in saglayicilar:
        for _ in range(max(1, deneme_sayisi)):
            try:
                ham = _ham_uret(saglayici, istem, ayar)
                senaryo = json.loads(_json_ayikla(ham))
                _dogrula(senaryo)
                return senaryo
            except (json.JSONDecodeError, ValueError) as e:
                son_hata = e  # gecersiz cikti: ayni saglayiciyla tekrar dene
                continue
            except KotaAsimi as e:
                son_hata, kota_hatasi = e, True
                break  # kota asildi -> (varsa) yedek saglayiciya gec

    if kota_hatasi:
        raise RuntimeError(
            "Senaryo uretilemedi: kota/hiz limiti asildi (429). Bir dakika "
            "bekleyip tekrar deneyin. Kalici cozum: config/ayarlar.yaml'a "
            "ucretsiz bir Groq anahtari ekleyin (senaryo.groq_api_key) - "
            "Gemini kotasi dolunca otomatik yedek olarak kullanilir."
        ) from son_hata

    raise RuntimeError(
        f"Gecerli senaryo JSON'i uretilemedi. Son hata: {son_hata}")


if __name__ == "__main__":
    # Hizli test (API anahtari gerekli):
    from src import ayarlari_yukle, karakterleri_yukle
    ayar = ayarlari_yukle()
    senaryo = uret("Batu ve Bobi kaybolan topu ariyor", karakterleri_yukle(), ayar, 45)
    print(json.dumps(senaryo, ensure_ascii=False, indent=2))
