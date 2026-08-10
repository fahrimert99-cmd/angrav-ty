"""
Montaj.
Konusan karakter kliplerini, sahnelerin arka planlari uzerine yerlestirip
sirayla birlestirir; opsiyonel arka plan muzigi ekler. Cikti: tek mp4.

moviepy 1.x ve 2.x ile calisir (bkz. src/video_araci.py).
"""
from pathlib import Path

from src.video_araci import (
    moviepy_yukle, sure_ver, konum_ver, ses_ver, boyutlandir, ses_olcek,
)


def birlestir(senaryo: dict, ayar: dict, cikti: Path) -> Path:
    mp = moviepy_yukle()
    en, boy = ayar["montaj"]["cozunurluk"]
    klipler = []

    for sahne in senaryo["sahneler"]:
        arka = sahne.get("arka_plan_yolu")
        for replik in sahne["replikler"]:
            klip_yolu = replik.get("klip_yolu")
            if not klip_yolu:
                raise ValueError(f"Replikte 'klip_yolu' eksik: {replik}")
            if not Path(klip_yolu).exists():
                raise FileNotFoundError(f"Video klip bulunamadi: {klip_yolu}")

            konusan = boyutlandir(mp.VideoFileClip(klip_yolu), height=boy)
            if arka:
                if not Path(arka).exists():
                    raise FileNotFoundError(f"Arka plan gorseli bulunamadi: {arka}")
                zemin = boyutlandir(
                    sure_ver(mp.ImageClip(arka), konusan.duration),
                    (en, boy))
                # konusan karakteri arka planin ortasina/altina yerlestir
                konusan = konum_ver(konusan, ("center", "bottom"))
                kare = mp.CompositeVideoClip([zemin, konusan], size=(en, boy))
            else:
                zemin = sure_ver(
                    mp.ColorClip(size=(en, boy), color=(20, 20, 30)),
                    konusan.duration)
                konusan = konum_ver(konusan, ("center", "bottom"))
                kare = ses_ver(
                    mp.CompositeVideoClip([zemin, konusan], size=(en, boy)),
                    konusan.audio)
            klipler.append(kare)

    if not klipler:
        raise ValueError("Montaj icin hic klip bulunamadi")

    film = mp.concatenate_videoclips(klipler, method="compose")

    muzik = ayar["montaj"].get("arka_plan_muzik")
    if muzik and Path(muzik).exists():
        arka_ses = sure_ver(ses_olcek(mp.AudioFileClip(muzik), 0.15), film.duration)
        film = ses_ver(film, mp.CompositeAudioClip([film.audio, arka_ses]))

    hedef = cikti / "bolum.mp4"
    film.write_videofile(str(hedef), fps=ayar["montaj"].get("fps", 24),
                         codec="libx264", audio_codec="aac")
    return hedef
