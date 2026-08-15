# 📚 Masallar — kendi senaryolarınız

Her masal için buraya **bir klasör** açın. Sistem o klasördeki **senaryo metnini**
ve **görselleri** kullanarak videoyu üretir (yapay zekâya gerek kalmadan; metinle
görseller birebir eşleşir).

## Klasör yapısı

```
masallar/
└── kayip-zamanin-aynasi/        <- masal klasörü (adı size kalmış)
    ├── masal.md                 <- senaryo metni (.md, .txt veya .docx)
    ├── 1.jpg                    <- Bölüm 1'in görseli
    ├── 2.jpg                    <- Bölüm 2'nin görseli
    └── ...
```

- **Görseller bölüm sırasına göre numaralandırılır:** `1.jpg`, `2.jpg`, `3.jpg` …
  (`.jpg`, `.jpeg`, `.png`, `.webp` olur). 1. görsel 1. bölüme, 2. görsel 2. bölüme…
- Görsel sayısı bölüm sayısından azsa, kalan bölümlerde son görsel kullanılır.

## Senaryo metni biçimi

İlk satır **masalın başlığı**. Sonra her bölüm `Bölüm N:` ile başlar ve altına
anlatım paragrafları gelir:

```markdown
Kayıp Zamanın Aynası

Bölüm 1: Sisli Vadi ve Çarkların Sırrı

Dünyanın en uzak köşelerinden birinde, haritalarda yeri bile olmayan
Tıkırtı Vadisi adında bir yer vardı...

Bu köyün en genç ve en meraklı çırağı Leo'ydu...

Bölüm 2: Zamanın Durduğu An

Leo, nefes nefese ustasının yanına koştu...
```

**Her paragraf bir sahne olur** (görsel aynı kalır, altyazı ve yavaş zoom devam
eder). Böylece anlatım ile görsel her zaman uyumludur.

### Görsel yönergeleri otomatik atlanır
Belgede `Bölüm N: Görsel Tasarımı ve Yönergeleri` gibi bölümler, `Atmosfer:`,
`Odak Noktası:`, `Detaylı Betimleme:` satırları ve İngilizce AI promptları
**anlatıma dahil edilmez** — yani hazırladığınız taslak belgeyi olduğu gibi
koyabilirsiniz.

## Videoyu üretme

**GitHub Actions:** Actions → **Masalname** → *Run workflow* → `masal_klasoru`
alanına klasör adını yazın (boş bırakırsanız `masallar/` altındaki ilk masal
seçilir).

**Yerel:**
```bash
python masal.py --klasor masallar/kayip-zamanin-aynasi
python masal.py --klasor auto        # ilk masalı otomatik seç
```

> Not: Bir masalı yayınladıktan sonra klasörünü silebilir veya adının başına
> `_` koyarak (`_kayip-zamanin-aynasi`) sıradan çıkarabilirsiniz.
