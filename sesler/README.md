# Sesler

İki kullanım şekli var:

1. **Kendi seslerinizi kullanma (`kullanici` modu):** Her replik için hazır
   ses dosyanız varsa buraya koyun.

2. **Ses klonlama (`xtts` modu):** Her karakter için 6–15 saniyelik temiz bir
   ses örneği koyun; dosya adı `config/karakterler.json` içindeki `ses` alanıyla
   aynı olsun (örn. `nurcan.wav`, `mert.wav`). Sistem bu örnekten sesi klonlar.

3. **Hiç ses vermezseniz (`edge` modu):** Microsoft'un ücretsiz Türkçe sesleri
   kullanılır (her karaktere `tts_ses` atanmıştır). Anahtar/dosya gerekmez.

Arka plan müziği için isterseniz `muzik.mp3` ekleyip `ayarlar.yaml` içinde
belirtebilirsiniz.
