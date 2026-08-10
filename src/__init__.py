"""Cizgi Film Otonom Uretim Sistemi - ortak yardimcilar."""
import json
import os
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


def ayarlari_yukle(yol: str = "config/ayarlar.yaml") -> dict:
    """ayarlar.yaml dosyasini okur. Yoksa ornek dosyaya yonlendirir."""
    import yaml
    tam = KOK / yol
    if not tam.exists():
        tam = KOK / "config/ayarlar.ornek.yaml"
    with open(tam, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def karakterleri_yukle(yol: str = "config/karakterler.json") -> dict:
    """Karakter kayit defterini dondurur (slug -> ozellikler)."""
    with open(KOK / yol, "r", encoding="utf-8") as f:
        return json.load(f)["karakterler"]


def cikti_klasoru(bolum_adi: str) -> Path:
    """Bir bolum icin cikti klasoru olusturur ve dondurur."""
    yol = KOK / "cikti" / bolum_adi
    (yol / "ses").mkdir(parents=True, exist_ok=True)
    (yol / "video").mkdir(parents=True, exist_ok=True)
    (yol / "sahne").mkdir(parents=True, exist_ok=True)
    return yol
