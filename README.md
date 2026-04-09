# Lügat - Discord Kelime Oyunu Botu (Python + MySQL)

Lügat, sunucu bazlı ayarlara sahip bir Discord kelime oyunu botudur.

Kurallar:
- Son kelimenin son harfi ile başlayan kelime yazılır.
- Sadece tek kelime kabul edilir.
- Girilen kelime otomatik küçük harfe çevrilir.
- En az 2 harfli kelimeler kabul edilir.

## Bağlantılar

- Botu ekle: https://discord.com/api/oauth2/authorize?client_id=1490789485959450814&scope=bot%20applications.commands&permissions=355392
- Destek sunucusu: https://discord.gg/PvRAkwhfXq
- Açık kaynak kod: https://github.com/YigitCahit/Lugat-Kelime-Oyunu-Botu

## Özellikler

- Sunucuya özel ayarlar
- Yanlış kelime mesajını silme (opsiyonel)
- Yanlış kelime uyarısı gönderme (opsiyonel)
- Doğru kelimeye reaksiyon bırakma (opsiyonel)
- Oyun dışı mesajlar için kaçış karakteri özelleştirme
- Reaksiyon emojisi özelleştirme
- Kelime başına puan ayarı
- Seviye atlama puan eşiği ayarı
- Turun kaç kelimede sıfırlanacağı ayarı
- Aynı kullanıcının üst üste oynayabilmesi ayarı
- Tur sıfırlandığında herkese açık tur liderliği duyurusu
- Sunucuya özel toplam puan, günlük, haftalık ve seviye liderlik tabloları
- Seviye komutu sonucu sadece komutu kullanan kişiye görünür (ephemeral)

## Gereksinimler

- Python 3.10+
- MySQL 8+
- Discord Developer Portal üzerinde oluşturulmuş bot

## Kurulum

1. Paketleri yükleyin:

```bash
pip install -r requirements.txt
```

2. MySQL'de bir veritabanı oluşturun:

```sql
CREATE DATABASE kelime_botu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. `.env.example` dosyasını `.env` olarak kopyalayıp doldurun:

- `DISCORD_TOKEN`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `WORD_LIST_DIR` (varsayılan: `Kelime-Listesi`)

4. Discord botunuzda **Message Content Intent** açık olsun.

5. Botu çalıştırın:

```bash
python main.py
```

## Komutlar

### Ayar Komutları (yönetici)
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

### Oyun Komutları
- `/oyun_durum`
- `/oyun_sifirla`

### Profil / Liderlik
- `/seviye` (ephemeral)
- `/liderlik` (`puan`, `seviye`, `gunluk`, `haftalik` seçenekleri)

### Yardım
- `/yardim`

## Notlar

- Kelime listeleri `Kelime-Listesi` klasöründeki `.list` ve `.txt` dosyalarından yüklenir.
- Her sunucunun ayarları ve istatistikleri birbirinden bağımsız tutulur.
- Tur sıfırlamada o turun liderliği herkese açık olarak duyurulur.
- Oyun kanalında bir mesajı oyuna dahil etmeden yazmak için mesajın başına kaçış karakterini ekleyebilirsin.
- Varsayılan kaçış karakteri `\\` olup `/ayar_kacis_karakteri` ile değiştirilebilir.
