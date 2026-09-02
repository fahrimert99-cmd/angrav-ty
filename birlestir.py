"""
Klip birlestirme orkestratoru.

Kullanicinin repoya yukledigi gunluk video kliplerini (klipler/ klasoru) alir,
yumusak gecisle birlestirir ve hedef sureye DONGULENMIS uzun bir ASMR videosu
uretir. Klip sesleri KORUNUR (config klip.ses ile degistirilebilir).

    python birlestir.py                               # klipler/ , 30 dk
    python birlestir.py --klasor klipler --sure 3600  # 60 dk
    python birlestir.py --sure 1800 --yukle           # bitince YouTube'a yukle

Cizgi film (main.py) / masal (masal.py) / asmr (asmr.py) hatlarindan
bagimsizdir; kaynak uretmez, hazir klipleri isler.
"""
import argparse
import sys
from pathlib import Path

from src import ayarlari_yukle, cikti_klasoru
from src import klip_montaj as m_klip


def main():
    p = argparse.ArgumentParser(description="Kliplerden uzun ASMR videosu birlestir")
    p.add_argument("--klasor", default="klipler",
                   help="Klip klasoru (tarih alt-klasoru varsa en yenisi kullanilir)")
    p.add_argument("--sure", type=int, default=None,
                   help="Hedef sure (sn). Bos ise config klip.sure (varsayilan 1800=30dk)")
    p.add_argument("--yukle", action="store_true", help="Bitince YouTube'a yukle")
    args = p.parse_args()

    ayar = ayarlari_yukle()
    ayar.setdefault("klip", {})
    sure = args.sure or int(ayar["klip"].get("sure", 1800))

    print(f"Klip birlestirme  |  klasor: {args.klasor}  |  hedef sure: {sure} sn")
    klipler = m_klip.klipleri_bul(args.klasor)

    cikti = cikti_klasoru("birlesik-asmr")
    print("Montaj yapiliyor (birlestir + hedef sureye dongule)...")
    video = m_klip.birlestir(klipler, sure, ayar, cikti)

    if args.yukle or ayar.get("yukleme", {}).get("aktif"):
        from src import yukleme as m_yukleme
        print("YouTube'a yukleniyor...")
        url = m_yukleme.yukle(str(video), "ASMR",
                              "ASMR\n\n#asmr #rahatlama #uyku", ayar)
        print(f"Yuklendi: {url}")

    video_yolu = Path(video)
    if not video_yolu.exists() or video_yolu.stat().st_size == 0:
        raise RuntimeError(f"Islem bitti ama video olusmadi/bos: {video_yolu}")
    print(f"\nBITTI ✅  Birlesik ASMR videosu: {video_yolu.resolve()} "
          f"({video_yolu.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
