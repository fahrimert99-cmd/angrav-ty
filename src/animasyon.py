"""
Konusan karakter animasyonu.
Karakter GORSELI + REPLIK SESI -> konusan (dudak senkronlu) video klip.

Motorlar:
  - "basit"     : dudak senkronu YOK; gorsel + ses -> mp4 (GPU/kurulum gerekmez,
                  garanti calisir, uctan uca testi hizlandirir)
  - "sadtalker" : SadTalker ile dudak senkronu (bedava, yerel/Colab, GPU onerilir)
  - "wav2lip"   : Wav2Lip ile dudak senkronu (alternatif)

SadTalker/Wav2Lip kurulumu icin bkz. colab/README.md
Bu modul agir motorlari alt surec (subprocess) olarak cagirir.
"""
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
