"""
Konusan karakter animasyonu.
Karakter GORSELI + REPLIK SESI -> konusan (dudak senkronlu) video klip.

Motorlar:
  - "basit"        : dudak senkronu YOK; gorsel + ses -> mp4 (GPU/kurulum
                     gerekmez, garanti calisir, uctan uca testi hizlandirir)
  - "sadtalker"    : SadTalker ile dudak senkronu (bedava, yerel/Colab, GPU)
  - "wav2lip"      : Wav2Lip ile dudak senkronu (alternatif)
  - "sadtalker_hf" : SadTalker'i bir Hugging Face (Gradio) Space uzerinden
                     UZAKTAN calistirir (yerel GPU/kurulum gerekmez). Space
                     adi/token/parametreleri config'ten okunur; API imzasi
                     calisma aninda kesfedilir. Hata olursa "basit"e duser.

SadTalker/Wav2Lip yerel kurulumu icin bkz. colab/README.md
Bu modul agir motorlari alt surec (subprocess) veya HF Space olarak cagirir.
"""
import os
import shutil
import subprocess
from pathlib import Path


def _basit(gorsel: str, ses: str, hedef: Path, fps: int = 24) -> Path:
    """Dudak senkronu olmadan gorsel + ses'ten mp4 uretir (moviepy).

    Ses suresince sabit karakter gorseli gosterir. Kurulum/GPU gerektirmez;
    SadTalker calismadiginda uctan uca videoyu garanti eder.
    """
    from src.video_araci import moviepy_yukle, sure_ver, ses_ver

    mp = moviepy_yukle()
    ses_klip = mp.AudioFileClip(ses)
    gorsel_klip = sure_ver(mp.ImageClip(gorsel), ses_klip.duration)
    gorsel_klip = ses_ver(gorsel_klip, ses_klip)

    hedef.parent.mkdir(parents=True, exist_ok=True)
    gorsel_klip.write_videofile(
        str(hedef), fps=fps, codec="libx264", audio_codec="aac",
        logger=None)
    return hedef


def _sadtalker(gorsel: str, ses: str, sadtalker_yolu: str, hedef_klasor: Path) -> Path:
    komut = [
        "python", f"{sadtalker_yolu}/inference.py",
        "--source_image", gorsel,
        "--driven_audio", ses,
        "--result_dir", str(hedef_klasor),
        "--still", "--preprocess", "full", "--enhancer", "gfpgan",
    ]
    subprocess.run(komut, check=True)
    # SadTalker sonucu klasore .mp4 olarak yazar; en yeni mp4'u bul:
    mp4ler = sorted(hedef_klasor.glob("**/*.mp4"), key=lambda p: p.stat().st_mtime)
    if not mp4ler:
        raise FileNotFoundError(
            f"SadTalker {hedef_klasor} klasörüne video yazmadı. "
            f"Girdi dosyalarını (gorsel={gorsel}, ses={ses}) kontrol edin."
        )
    return mp4ler[-1]


def _hf_sonuc_yolu(sonuc):
    """gradio_client dönüşünden (str / dict / list / tuple) video dosya yolunu
    cikarir. Video uzantili yolu oncelikler; bulamazsa ilk yolu dener."""
    if isinstance(sonuc, str):
        return sonuc
    if isinstance(sonuc, dict):
        return sonuc.get("video") or sonuc.get("name") or sonuc.get("path")
    if isinstance(sonuc, (list, tuple)):
        # Once video uzantili bir yol ara.
        for x in sonuc:
            y = _hf_sonuc_yolu(x)
            if y and str(y).lower().endswith((".mp4", ".webm", ".mov", ".mkv")):
                return y
        for x in sonuc:  # olmadi, ilk gecerli yolu dondur
            y = _hf_sonuc_yolu(x)
            if y:
                return y
    return None


def _sadtalker_hf(gorsel: str, ses: str, ayar: dict, hedef: Path,
                  fps: int = 24) -> Path:
    """SadTalker'i bir Hugging Face Gradio Space uzerinden uzaktan calistirir.

    Space'in API imzasi calisma aninda `view_api` ile kesfedilir: parametreler
    icindeki ilk Image bileseni gorsel, ilk Audio bileseni ses ile doldurulur;
    geri kalanlar config'teki `hf_params` (parametre adi -> deger) ile veya
    Space'in kendi varsayilanlariyla gecilir. Ureti len video `hedef`e kopyalanir.
    Herhangi bir hata olursa (Space uyuyor/kuyruk/imza uyumsuz/anahtar yok)
    sessizce "basit" motora dusulur; boylece uctan uca uretim durmaz.
    """
    a = ayar["animasyon"]
    space = a.get("hf_space", "kevinwang676/SadTalker")
    token = a.get("hf_token") or os.environ.get("HF_TOKEN") or None
    istenen_api = a.get("hf_api_name")            # orn. "/test" (ops.)
    override = a.get("hf_params", {}) or {}       # {parametre_adi: deger}

    try:
        import inspect

        from gradio_client import Client, handle_file

        print(f"     [sadtalker_hf] {space} Space'ine baglaniliyor "
              f"(uyuyorsa uyanmasi ~30-60sn surebilir)...")
        # Token argumaninin adi surumden surume degisiyor
        # (eski: hf_token, yeni: token). Imzaya bakip dogru olani gec.
        client_kw = {}
        if token:
            params = inspect.signature(Client.__init__).parameters
            if "hf_token" in params:
                client_kw["hf_token"] = token
            elif "token" in params:
                client_kw["token"] = token
        client = Client(space, **client_kw)
        api = client.view_api(return_format="dict")
        uclar = api.get("named_endpoints", {}) or {}

        # Gorsel + ses bileseni iceren bir endpoint sec (config verdiyse onu).
        def _uygun(param_listesi):
            bilesenler = [(p.get("component") or "").lower() for p in param_listesi]
            return (any(b in ("image", "imageeditor") for b in bilesenler)
                    and any(b == "audio" for b in bilesenler))

        secilen_ad, secilen = None, None
        if istenen_api and istenen_api in uclar:
            secilen_ad, secilen = istenen_api, uclar[istenen_api]
        else:
            for ad, tanim in uclar.items():
                if _uygun(tanim.get("parameters", [])):
                    secilen_ad, secilen = ad, tanim
                    break
        if secilen is None:
            raise RuntimeError(
                f"Space'te gorsel+ses alan endpoint bulunamadi. "
                f"Mevcut uclar: {list(uclar)}")

        # Parametreleri sirayla doldur.
        args = []
        gorsel_kondu = ses_kondu = False
        for p in secilen.get("parameters", []):
            bilesen = (p.get("component") or "").lower()
            ad = p.get("parameter_name")
            if bilesen in ("image", "imageeditor") and not gorsel_kondu:
                deger, gorsel_kondu = handle_file(gorsel), True
            elif bilesen == "audio" and not ses_kondu:
                deger, ses_kondu = handle_file(ses), True
            elif ad and ad in override:
                deger = override[ad]
            elif p.get("parameter_has_default"):
                deger = p.get("parameter_default")
            elif p.get("example_input") is not None:
                deger = p.get("example_input")
            else:
                deger = None
            args.append(deger)

        print(f"     [sadtalker_hf] '{secilen_ad}' cagriliyor "
              f"({len(args)} parametre)...")
        sonuc = client.predict(*args, api_name=secilen_ad)

        yol = _hf_sonuc_yolu(sonuc)
        if not yol or not Path(yol).exists():
            raise RuntimeError(f"Space video dondurmedi (donen: {sonuc!r})")

        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(yol, hedef)
        return hedef

    except Exception as e:
        print(f"     [sadtalker_hf uyarisi] uzak uretim basarisiz ({e}); "
              f"'basit' motora dusuluyor.")
        return _basit(gorsel, ses, hedef, fps)


def _wav2lip(gorsel: str, ses: str, hedef: Path) -> Path:
    komut = [
        "python", "Wav2Lip/inference.py",
        "--checkpoint_path", "Wav2Lip/checkpoints/wav2lip_gan.pth",
        "--face", gorsel, "--audio", ses, "--outfile", str(hedef),
    ]
    subprocess.run(komut, check=True)
    return hedef


def replik_animasyonu(gorsel: str, ses: str, ayar: dict, hedef_klasor: Path,
                      ad: str) -> Path:
    motor = ayar["animasyon"]["motor"]
    if motor == "basit":
        fps = ayar.get("montaj", {}).get("fps", 24)
        return _basit(gorsel, ses, hedef_klasor / f"{ad}.mp4", fps)
    if motor == "sadtalker":
        return _sadtalker(gorsel, ses, ayar["animasyon"]["sadtalker_yolu"],
                          hedef_klasor)
    if motor == "sadtalker_hf":
        fps = ayar.get("montaj", {}).get("fps", 24)
        return _sadtalker_hf(gorsel, ses, ayar, hedef_klasor / f"{ad}.mp4", fps)
    if motor == "wav2lip":
        return _wav2lip(gorsel, ses, hedef_klasor / f"{ad}.mp4")
    raise ValueError(f"Bilinmeyen animasyon motoru: {motor}")


def senaryoyu_canlandir(senaryo: dict, karakterler: dict, ayar: dict, cikti: Path):
    """Her replik icin konusan karakter klibi uretir; 'klip_yolu' ekler.
    
    Hata kontrolü: Karakterlerin gorsel/ses dosyaları kontrol edilir.
    """
    from pathlib import Path as P
    
    sayac = 0
    for sahne in senaryo["sahneler"]:
        for replik in sahne["replikler"]:
            sayac += 1
            karakter_slug = replik["karakter"]
            if karakter_slug not in karakterler:
                raise ValueError(f"Bilinmeyen karakter: {karakter_slug}")
            
            k = karakterler[karakter_slug]
            
            # Gorsel ve ses dosyalarini kontrol et
            gorsel_path = P(k.get("gorsel", ""))
            if not gorsel_path.exists():
                raise FileNotFoundError(
                    f"Karakter '{karakter_slug}' görsel bulunamadı: {k.get('gorsel')}"
                )
            
            ses_path = P(replik.get("ses_yolu", ""))
            if not ses_path.exists():
                raise FileNotFoundError(
                    f"Replik {sayac} ses dosyası bulunamadı: {replik.get('ses_yolu')}"
                )
            
            replik["klip_yolu"] = str(replik_animasyonu(
                gorsel=k["gorsel"], ses=replik["ses_yolu"], ayar=ayar,
                hedef_klasor=cikti / "video", ad=f"{sayac:03d}_{karakter_slug}",
            ))
    return senaryo
