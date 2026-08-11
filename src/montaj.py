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


def _parcayi_olustur(mp, sahne, replik, en, boy):
    """Tek bir replik icin (arka plan + konusan karakter) birlesik kareyi kurar."""
    arka = sahne.get("arka_plan_yolu")
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
    return kare, [zemin, konusan]


def birlestir(senaryo: dict, ayar: dict, cikti: Path) -> Path:
    """Her repligi ayri ayri diske yazip bellekten dusurur, sonra dosyalari
    birlestirir. Tum repliklerin birlesik karelerini ayni anda RAM'de tutmak
    (eski yaklasim) uzun bolumlerde bellek tasmasina (ArrayMemoryError) yol
    aciyordu; bu yuzden akis parca-parca (streaming) hale getirildi.
    """
    mp = moviepy_yukle()
    en, boy = ayar["montaj"]["cozunurluk"]
    fps = ayar["montaj"].get("fps", 24)

    gecici = cikti / "video" / "_montaj_parca"
    gecici.mkdir(parents=True, exist_ok=True)

    parca_yollari = []
    sayac = 0
    for sahne in senaryo["sahneler"]:
        for replik in sahne["replikler"]:
            sayac += 1
            kare, alt_klipler = _parcayi_olustur(mp, sahne, replik, en, boy)
            parca_yolu = gecici / f"{sayac:03d}.mp4"
            kare.write_videofile(str(parca_yolu), fps=fps, codec="libx264",
                                 audio_codec="aac", logger=None)
            parca_yollari.append(parca_yolu)
            # Bu repligin klip nesnelerini kapat, bellegi serbest birak.
            for k in (*alt_klipler, kare):
                try:
                    k.close()
                except Exception:
                    pass

    if not parca_yollari:
        raise ValueError("Montaj icin hic klip bulunamadi")

    klipler = [mp.VideoFileClip(str(p)) for p in parca_yollari]
    film = mp.concatenate_videoclips(klipler, method="compose")

    muzik = ayar["montaj"].get("arka_plan_muzik")
    if muzik and Path(muzik).exists():
        arka_ses = sure_ver(ses_olcek(mp.AudioFileClip(muzik), 0.15), film.duration)
        film = ses_ver(film, mp.CompositeAudioClip([film.audio, arka_ses]))

    hedef = cikti / "bolum.mp4"
    film.write_videofile(str(hedef), fps=fps, codec="libx264", audio_codec="aac")

    for k in klipler:
        try:
            k.close()
        except Exception:
            pass

    return hedef
