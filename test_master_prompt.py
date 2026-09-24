"""master_prompt.py icin hizli testler (API gerektirmez)."""

import json

import master_prompt as mp


def test_sablon_ve_gorev_prompta_girer():
    cevaplar = dict(mp.SABLONLAR["kalite"], gorev="5S denetim proseduru hazirla")
    metin = mp.prompt_olustur(cevaplar)
    assert metin.startswith("# MASTER PROMPT")
    assert "<gorev>\n5S denetim proseduru hazirla\n</gorev>" in metin
    assert "Fahri Mert" in metin
    assert "1. Yonetim raporu" in metin  # kurallar numaralanir


def test_bos_bolum_atlanir_ve_oneri_verir():
    cevaplar = {"rol": "Asistan", "gorev": "Kisa"}
    assert "<baglam>" not in mp.prompt_olustur(cevaplar)
    puan, oneriler = mp.degerlendir(cevaplar)
    assert 0 < puan < 100
    assert any("Gorev tanimi cok kisa" in o for o in oneriler)


def test_sessiz_mod_dosya_yazar(tmp_path):
    cikti = tmp_path / "p.md"
    kod = mp.main(["--sablon", "masal", "--gorev", "Paylasma uzerine bir masal",
                   "--sessiz", "--cikti", str(cikti), "--kaydet"])
    assert kod == 0
    assert "Paylasma uzerine bir masal" in cikti.read_text(encoding="utf-8")
    kayit = json.loads(cikti.with_suffix(".json").read_text(encoding="utf-8"))
    assert kayit["gorev"] == "Paylasma uzerine bir masal"
