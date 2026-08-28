# CLAUDE.md

Bu dosya, Claude Code'un bu depoda çalışırken izlemesi gereken standartları içerir.

---

## Görev Tanımı Dokümanları — Standart Kurallar (İstihsal Şube)

İstihsal Şube görev tanımı (`.docx`) dokümanları üzerinde çalışırken **aşağıdaki
kurallar her zaman uygulanır**. Kullanıcı tekrar belirtmese bile bu standarda göre
düzenle.

### 1. Genel Format
- Tüm gövde metni **Arial, 11 punto**. Başka yazı tipi kullanılmaz (belge teması ve
  `docDefaults` fontu Arial'e sabitlenir; tema `minorFont`/`majorFont` = Arial).
- Gövde tablosunun **sol sütunundaki etiketler** (Görev Ünvanı, Genel Tanım, Kurumsal
  Sorumluluklar, Yetkileri vb.) hücrenin **tam ortasında** olur: dikey ortalı
  (`vAlign=center`) **ve** yatay ortalı (`jc=center`).
- Değer (sağ sütun) hücreleri üstten hizalı; madde listeleri madde işaretli (bullet).
- Sayfa/kenar düzeni ve tablo genişliği (≈17,5 cm) korunur.

### 2. Başlık (Header)
- **İlk Yayın Tarihi = işlemin yapıldığı günün tarihi** (bu görevde: 27.08.2026).
  Etiketten sonra hangi tarih varsa (15.08.2022, 25.12.2025, boş vb.) bununla değiştirilir.
- Doküman Kodu: `ALİN.ORG` · Revizyon Tarihi: `İlk Yayın` · Revizyon No: `00`.

### 3. Satır Yapısı (Gövde Tablosu)
- **"Merkezde Bağlı Olduğu Yönetici" satırı kaldırılır.**
- **"Konu" etiketi "Genel Tanım" olarak değiştirilir** (satırın değeri korunur).
- Sıra: Görev Ünvanı → Bağlı Olduğu Yönetici → Vekâlet Durumu → Rapor içeriği/Periyodu
  → Sorumlu Olduğu Birim(ler) → Genel Tanım → [Görevler] → İş Becerileri/Nitelikler →
  Sorumlulukları → Kurumsal Sorumluluklar → Ortak Sorumluluklar → Yetkileri → Deneyim →
  İmza (Ad/Soyad/İmza).

### 4. İçerik Kuralları
- **Kurumsal Sorumluluklar** unvana göre eklenir ve **"Ortak Sorumluluklar" satırının
  hemen üstüne** yerleştirilir:
  - **Beyaz yaka** metni: yalnızca **Mühendis** ve **Başmühendis**.
  - **Mavi yaka** metni: diğer tüm unvanlar (vardiya amiri, formen, postabaşı, operatör,
    şoför, sürücü, işçi, görevli, çaycı, numuneci vb.).
- **Deneyim** her dokümanda: `Alanında minimum 3 yıl deneyime sahip olmak.`
- Boş kutular (**İş Becerileri**, **Yetkileri**) role uygun içerikle doldurulur;
  hâlihazırda dolu olanlar **korunur** (üzerine yazılmaz).

### 5. Footer — Onay / İmza Matrisi
- Saha dokümanları: **8 sütun**. İSTİHSAL ŞUBE dokümanları: **12 sütun** (Hazırlayan
  olarak 5 saha başmühendisinin tamamı).
- Matris satırları: **Rol · Unvan · İsim · İMZA** (İMZA satırı fiziksel imza için boş).
- Alt not: `Basılı ve imzasız dokümanlar kontrolsüz kopyadır.` + `Basım tarihi: <bugün>`
  + `Sayfa No: {PAGE}/{NUMPAGES}`.

**Onay Matrisi — Rol / Unvan / İsim:**

| Rol | Unvan | İsim |
| --- | --- | --- |
| Hazırlayan | İlgili saha Başmühendisi | Bant Yolları → Erkan Çelik · Döküm Sahası → Hulusi Daşgın · Hazırlık İşleri → Erdi Alpata · Kazı Sahası → Uğur Gökhan · Stok Sahası → Fatma Tıraş |
| Düzenleyen | KGK Uzman Yardımcısı | Ayşenur Çay |
| Kontrol Eden | KGK Yöneticisi | Fahri Mert |
| Kontrol Eden | KGK Direktörü | Özgür Yılmaz |
| Kontrol Eden | İstihsal Şube Müdürü | Ömer Burak Kandilli |
| Onaylayan | İşletme Müdürü (Teknik) | Fuat Yinanç |
| Onaylayan | Maden Müdürü | Ahmet Metin Özdamar |
| Onaylayan | Maden GMY | Cumali Taştekin |

### 6. Kapsam
Toplam **60 görev tanımı**: BANT YOLLARI (8), DÖKÜM DAHASI (10), HAZIRLIK İŞLERİ (16),
KAZI SAHASI (14), STOK SAHASI (7), İSTİHSAL ŞUBE (5).

### 7. Doğrulama
- Her düzenlemeden sonra OOXML (XSD) geçerliliği kontrol edilir (Word'de onarım uyarısı
  olmadan açılmalı).
- Türkçe karakterlere dikkat: `"İ".lower()` birleşik noktalı `i̇` üretir; unvan
  sınıflandırmasında Türkçe-uyumlu küçültme kullan (`İ→i`, `I→ı`).
