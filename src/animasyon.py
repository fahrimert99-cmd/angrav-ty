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


# Ken Burns hareketi: klip suresince yavas zoom orani (1.0 -> 1+ZOOM).
# 0 verilirse gorsel tamamen sabit kalir (eski davranis).
KEN_BURNS_ZOOM = 0.10


def _hareketli_gorsel(mp, gorsel: str, sure: float, zoom: float = KEN_BURNS_ZOOM):
    """Sabit gorseli 'canli' hale getirir: klip suresince yavas bir zoom-in
    (Ken Burns) uygular ve sonucu ORIJINAL cerceveye kirpar. Boylece video
    'slayt' gibi durmaz. Zoom herhangi bir sebeple yapilamazsa sabit gorsele
    duser."""
    from src.video_araci import sure_ver, konum_ver

    taban = mp.ImageClip(gorsel)
    if not zoom or zoom <= 0:
        return sure_ver(taban, sure)

    w, h = taban.size
    # t=0'da 1.0, t=sure'de 1+zoom olacak sekilde lineer buyume.
    olcek = lambda t: 1.0 + zoom * (t / max(sure, 0.1))
    try:
        buyuyen = None
        for ad in ("resized", "resize"):
            m = getattr(taban, ad, None)
            if callable(m):
                buyuyen = m(olcek)
                break
        if buyuyen is None:
            return sure_ver(taban, sure)
        # Buyuyen goruntuyu orijinal cerceveye ortala + kirp.
        buyuyen = konum_ver(buyuyen, ("center", "center"))
        kare = mp.CompositeVideoClip([buyuyen], size=(w, h))
        return sure_ver(kare, sure)
    except Exception:
        return sure_ver(taban, sure)


def _basit(gorsel: str, ses: str, hedef: Path, fps: int = 24) -> Path:
    """Dudak senkronu olmadan gorsel + ses'ten mp4 uretir (moviepy).

    Ses suresince karakter gorselini gosterir; gorsele yavas bir zoom (Ken
    Burns) uygulanir ki video 'slayt' gibi durmasin. Kurulum/GPU gerektirmez;
    SadTalker calismadiginda uctan uca videoyu garanti eder.
    """
    from src.video_araci import moviepy_yukle, ses_ver

    mp = moviepy_yukle()
    ses_klip = mp.AudioFileClip(ses)
    gorsel_klip = _hareketli_gorsel(mp, gorsel, ses_klip.duration)
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
    import time

    a = ayar["animasyon"]
    space = a.get("hf_space", "kevinwang676/SadTalker")
    token = a.get("hf_token") or os.environ.get("HF_TOKEN") or None
    istenen_api = a.get("hf_api_name")            # orn. "/test" (ops.)
    override = a.get("hf_params", {}) or {}       # {parametre_adi: deger}
    deneme_sayisi = int(a.get("hf_retries", 2))   # rate-limit'te tekrar dene
    bekleme = float(a.get("hf_bekleme", 15))      # denemeler arasi saniye

    def _gorsel_ses_var(param_listesi):
        bilesenler = [(p.get("component") or "").lower() for p in param_listesi]
        return (any(b in ("image", "imageeditor") for b in bilesenler)
                and any(b == "audio" for b in bilesenler))

    def _arg_kur(parametreler):
        from gradio_client import handle_file
        args = []
        gorsel_kondu = ses_kondu = False
        for p in parametreler:
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
        return args

    def _bir_deneme():
        import inspect

        from gradio_client import Client

        # Token argumaninin adi surumden surume degisiyor (hf_token/token).
        client_kw = {}
        if token:
            params = inspect.signature(Client.__init__).parameters
            if "hf_token" in params:
                client_kw["hf_token"] = token
            elif "token" in params:
                client_kw["token"] = token
        client = Client(space, **client_kw)
        api = client.view_api(return_format="dict")
        adli = api.get("named_endpoints", {}) or {}
        adsiz = api.get("unnamed_endpoints", {}) or {}

        # Once config'te istenen adli endpoint; sonra gorsel+ses alan ilk
        # adli endpoint; olmazsa ilk uygun ADSIZ (fn_index) endpoint.
        cagri_kw, parametreler = None, None
        if istenen_api and istenen_api in adli:
            cagri_kw = {"api_name": istenen_api}
            parametreler = adli[istenen_api].get("parameters", [])
        if parametreler is None:
            for ad, tanim in adli.items():
                if _gorsel_ses_var(tanim.get("parameters", [])):
                    cagri_kw = {"api_name": ad}
                    parametreler = tanim.get("parameters", [])
                    break
        if parametreler is None:
            for idx, tanim in adsiz.items():
                if _gorsel_ses_var(tanim.get("parameters", [])):
                    try:
                        cagri_kw = {"fn_index": int(idx)}
                    except (TypeError, ValueError):
                        cagri_kw = {"fn_index": idx}
                    parametreler = tanim.get("parameters", [])
                    break
        if parametreler is None:
            raise RuntimeError(
                f"Space'te gorsel+ses alan endpoint bulunamadi. "
                f"Adli: {list(adli)} | Adsiz: {list(adsiz)}")

        args = _arg_kur(parametreler)
        print(f"     [sadtalker_hf] {cagri_kw} cagriliyor ({len(args)} parametre)...")
        sonuc = client.predict(*args, **cagri_kw)

        yol = _hf_sonuc_yolu(sonuc)
        if not yol or not Path(yol).exists():
            raise RuntimeError(f"Space video dondurmedi (donen: {sonuc!r})")
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(yol, hedef)
        return hedef

    print(f"     [sadtalker_hf] {space} Space'ine baglaniliyor "
          f"(uyuyorsa uyanmasi ~30-60sn surebilir)...")
    son_hata = None
    for deneme in range(1, deneme_sayisi + 1):
        try:
            return _bir_deneme()
        except Exception as e:
            son_hata = e
            # Rate-limit ("too many requests") ise bekleyip tekrar dene.
            if "too many requests" in str(e).lower() and deneme < deneme_sayisi:
                print(f"     [sadtalker_hf] rate-limit; {bekleme:.0f}sn bekleyip "
                      f"tekrar deneniyor ({deneme}/{deneme_sayisi})...")
                time.sleep(bekleme)
                continue
            break

    print(f"     [sadtalker_hf uyarisi] uzak uretim basarisiz ({son_hata}); "
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
