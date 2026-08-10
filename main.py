"""
Ana orkestrator.
Tek komutla bir cizgi film bolumu uretir:

    python main.py --konu "Batu ve Bobi parkta topu ariyor" --sure 60

Adimlar:  senaryo -> seslendirme -> sahneler -> animasyon -> montaj
          -> altyazi -> (opsiyonel) YouTube'a yukleme
"""
import argparse
import json
import re
import sys
from pathlib import Path

from src import ayarlari_yukle, karakterleri_yukle, cikti_klasoru
from src import senaryo as m_senaryo
from src import seslendirme as m_ses
from src import sahne as m_sahne
from src import animasyon as m_anim
from src import montaj as m_montaj
from src import altyazi as m_altyazi
from src import yukleme as m_yukleme


def slugla(metin: str) -> str:
    metin = re.sub(r"[^a-zA-Z0-9]+", "-", metin.lower()).strip("-")
    return metin[:40] or "bolum"


def main():
    p = argparse.ArgumentParser(description="Cizgi film bolumu uret")
    p.add_argument("--konu", required=True, help="Bolumun konusu")
    p.add_argument("--sure", type=int, default=300, help="Hedef sure (saniye - varsayilan 300s = 5dk)")
    p.add_argument("--karakterler", default="",
                   help="Sadece bu karakterleri kullan (virgulle: duru,efe). "
                        "Bos birakilirsa tum karakterler kullanilir.")
    p.add_argument("--yukle", action="store_true", help="Bitince YouTube'a yukle")
    args = p.parse_args()

    ayar = ayarlari_yukle()
    karakterler = karakterleri_yukle()

    # Istenirse kadroyu belirtilen karakterlerle sinirla.
    if args.karakterler.strip():
        secilen = [s.strip() for s in args.karakterler.split(",") if s.strip()]
        bilinmeyen = [s for s in secilen if s not in karakterler]
        if bilinmeyen:
            raise SystemExit(
                f"Bilinmeyen karakter(ler): {', '.join(bilinmeyen)}. "
                f"Mevcut: {', '.join(karakterler)}"
            )
        karakterler = {s: karakterler[s] for s in secilen}
        print(f"     Kadro sinirli: {', '.join(secilen)}")

    # On-kontrol: animasyon icin her karakterin gorsel dosyasi gerekli.
    # Eksikse bastan, acik bir mesajla dur (senaryo/ses uretmeden).
    eksik = [(s, karakterler[s].get("gorsel", ""))
             for s in karakterler
             if not Path(karakterler[s].get("gorsel", "")).exists()]
    if eksik:
        satirlar = "\n".join(f"  - {s}: {g or '(gorsel alani bos)'}"
                             for s, g in eksik)
        raise SystemExit(
            "Su karakterlerin gorsel dosyasi bulunamadi. Once bu dosyalari "
            "yukleyin (Colab'da sol dosya panelinden karakterler/ klasorune "
            f"surukleyin):\n{satirlar}"
        )

    print("1/7  Senaryo yaziliyor...")
    senaryo = m_senaryo.uret(args.konu, karakterler, ayar, args.sure)
    cikti = cikti_klasoru(slugla(senaryo["baslik"]))
    (cikti / "senaryo.json").write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"     Baslik: {senaryo['baslik']}")

    print("2/7  Replikler seslendiriliyor...")
    m_ses.senaryoyu_seslendir(senaryo, karakterler, ayar, cikti)

    print("3/7  Arka plan sahneleri uretiliyor...")
    m_sahne.sahneleri_uret(senaryo, ayar, cikti)

    print("4/7  Karakterler canlandiriliyor (dudak senkronu)...")
    m_anim.senaryoyu_canlandir(senaryo, karakterler, ayar, cikti)

    print("5/7  Montaj yapiliyor...")
    video = m_montaj.birlestir(senaryo, ayar, cikti)

    if ayar["altyazi"].get("aktif", True):
        print("6/7  Altyazi ekleniyor...")
        srt = m_altyazi.srt_uret(str(video), ayar)
        video = m_altyazi.altyaziyi_goem(str(video), str(srt))
    else:
        print("6/7  Altyazi atlandi.")

    if args.yukle or ayar["yukleme"].get("aktif"):
        print("7/7  YouTube'a yukleniyor...")
        url = m_yukleme.yukle(str(video), senaryo["baslik"],
                              f"{args.konu}\n\n#cizgifilm #cocuk", ayar)
        print(f"     Yuklendi: {url}")
    else:
        print("7/7  Yukleme atlandi (--yukle ile acabilirsiniz).")

    # Videonun gercekten olustugunu dogrula; sessizce videosuz bitmeyi onle.
    video_yolu = Path(video)
    if not video_yolu.exists() or video_yolu.stat().st_size == 0:
        raise RuntimeError(
            f"Islem bitti ama video dosyasi olusmadi/bos: {video_yolu.resolve()}"
        )
    print(f"\nBITTI ✅  Video: {video_yolu.resolve()} "
          f"({video_yolu.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
