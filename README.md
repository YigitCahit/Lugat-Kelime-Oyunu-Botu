# Discord Kelime Oyunu Botu (Python + MySQL)

Bu bot, sunucu bazli ayarlara sahip bir Discord kelime oyunu sunar.
Kurallar:
- Son kelimenin son harfi ile baslayan kelime yazilir.
- Sadece tek kelime kabul edilir.
- Girilen kelime otomatik kucuk harfe cevrilir.
- En az 2 harfli kelimeler kabul edilir.

## Ozellikler

- Sunucuya ozel ayarlar
- Yanlis kelime mesajini silme (opsiyonel)
- Yanlis kelime uyarisi gonderme (opsiyonel)
- Dogru kelimeye reaksiyon birakma (opsiyonel)
- Oyun disi mesajlar icin kacis karakteri ozellestirme
- Reaksiyon emojisi ozellestirme
- Kelime basina puan ayari
- Seviye atlama puan esigi ayari
- Turun kac kelimede sifirlanacagi ayari
- Ayni kullanicinin ust uste oynayabilmesi ayari
- Tur sifirlandiginda herkese acik tur liderligi duyurusu
- Sunucuya ozel toplam puan, gunluk, haftalik ve seviye liderlik tablolari
- Seviye komutu sonucu sadece komutu kullanan kisiye gorunur (ephemeral)

## Gereksinimler

- Python 3.10+
- MySQL 8+
- Discord Developer Portal uzerinde olusturulmus bot

## Kurulum

1. Paketleri yukleyin:

```bash
pip install -r requirements.txt
```

2. MySQL'de bir veritabani olusturun:

```sql
CREATE DATABASE kelime_botu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. `.env.example` dosyasini `.env` olarak kopyalayip doldurun:

- `DISCORD_TOKEN`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `WORD_LIST_DIR` (varsayilan: `Kelime-Listesi`)

4. Discord botunuzda **Message Content Intent** acik olsun.

5. Botu calistirin:

```bash
python main.py
```

## Komutlar

### Ayar Komutlari (yonetici)
- `/ayar_goster`
- `/ayar_kanal`
- `/ayar_yanlis_sil`
- `/ayar_uyari`
- `/ayar_dogru_reaksiyon`
- `/ayar_reaksiyon_emoji`
- `/ayar_kacis_karakteri`
- `/ayar_kelime_puani`
- `/ayar_seviye_puani`
- `/ayar_sifirlama_kelimesi`
- `/ayar_ardisik_oyun`

### Oyun Komutlari
- `/oyun_durum`
- `/oyun_sifirla`

### Profil / Liderlik
- `/seviye` (ephemeral)
- `/liderlik` (`puan`, `seviye`, `gunluk`, `haftalik` secenekleri)

### Yardim
- `/yardim`

## Notlar

- Kelime listeleri `Kelime-Listesi` klasorundeki `.list` ve `.txt` dosyalarindan yuklenir.
- Her sunucunun ayarlari ve istatistikleri birbirinden bagimsiz tutulur.
- Tur sifirlamada o turun liderligi herkese acik olarak duyurulur.
- Oyun kanalinda bir mesaji oyuna dahil etmeden yazmak icin mesajin basina kacis karakterini ekleyebilirsin.
- Varsayilan kacis karakteri `\\` olup `/ayar_kacis_karakteri` ile degistirilebilir.
