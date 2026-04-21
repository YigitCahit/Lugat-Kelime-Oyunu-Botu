# Lügat Botu Komut Rehberi

Burada, botta bulunan tüm slash komutların nasıl kullanılacağı açıklanmıştır.

## Genel Kullanım

- Discord'da komut kullanmak için mesaj kutusuna `/` yazıp komutu seçin.
- Parametre isteyen komutlarda zorunlu alanları doldurun.
- `aktif` parametresi olan komutlarda:
  - `true` = açar
  - `false` = kapatır
- Aksi belirtilmedikçe komutlar sadece sunucuda (DM dışında) çalışır.

## Yetki Kuralları

- `Sunucuyu Yönet` izni **veya ayarlanmış yetkili rol** gerektiren komutlar:
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
  - `/oyun_sifirla`

- Sadece `Sunucuyu Yönet` izni gerektiren komut:
  - `/ayar_yetkili_rol`

## Ayar Komutları

### /ayar_goster
Sunucuya ait mevcut oyun ayarlarını gösterir.

Kullanım:
```text
/ayar_goster
```

Not: Cevap sadece komutu kullanan kişiye görünür (ephemeral).

### /ayar_kanal
Oyunun oynanacağı metin kanalını ayarlar.

Kullanım:
```text
/ayar_kanal kanal:#kanal-adi
```

Örnek:
```text
/ayar_kanal kanal:#kelime-oyunu
```

### /ayar_yanlis_sil
Geçersiz kelime mesajlarının silinmesini açar/kapatır.

Kullanım:
```text
/ayar_yanlis_sil aktif:true|false
```

### /ayar_uyari
Geçersiz kelime girildiğinde uyarı mesajı gönderimini açar/kapatır.

Kullanım:
```text
/ayar_uyari aktif:true|false
```

### /ayar_dogru_reaksiyon
Doğru kelime mesajlarına reaksiyon bırakılmasını açar/kapatır.

Kullanım:
```text
/ayar_dogru_reaksiyon aktif:true|false
```

### /ayar_reaksiyon_emoji
Doğru kelimelerde kullanılacak emojiyi ayarlar.

Kullanım:
```text
/ayar_reaksiyon_emoji emoji:<emoji>
```

Örnek:
```text
/ayar_reaksiyon_emoji emoji:✅
```

Kısıt: `emoji` uzunluğu 1-64 karakter olmalıdır.

### /ayar_kacis_karakteri
Oyun kanalında, oyuna dahil edilmeyecek mesajları başlatmak için kaçış karakteri belirler.

Kullanım:
```text
/ayar_kacis_karakteri karakter:<tek-karakter>
```

Örnek:
```text
/ayar_kacis_karakteri karakter:!
```

Kısıt:
- Tam olarak 1 karakter olmalı.
- Boşluk karakteri olamaz.

### /ayar_kelime_puani
Her doğru kelimede verilecek puanı ayarlar.

Kullanım:
```text
/ayar_kelime_puani puan:<1-10000>
```

Örnek:
```text
/ayar_kelime_puani puan:10
```

### /ayar_seviye_puani
Seviye atlamak için gereken puanı ayarlar.

Kullanım:
```text
/ayar_seviye_puani puan:<1-100000>
```

Örnek:
```text
/ayar_seviye_puani puan:250
```

### /ayar_sifirlama_kelimesi
Turun kaç kelimede bir otomatik sıfırlanacağını ayarlar.

Kullanım:
```text
/ayar_sifirlama_kelimesi adet:<1-100000>
```

Örnek:
```text
/ayar_sifirlama_kelimesi adet:75
```

### /ayar_ardisik_oyun
Aynı kullanıcının art arda kelime oynayıp oynayamayacağını ayarlar.

Kullanım:
```text
/ayar_ardisik_oyun aktif:true|false
```

### /ayar_yetkili_rol
`Sunucuyu Yönet` izni gerektiren komutlarda kullanılabilecek yetkili rolü ekler veya çıkarır.

Kullanım (ekleme):
```text
/ayar_yetkili_rol islem:ekle rol:@rol
```

Kullanım (çıkarma):
```text
/ayar_yetkili_rol islem:cikar
```

Notlar:
- Bu komutu sadece `Sunucuyu Yönet` izni olanlar kullanabilir.
- Ayarlanan rol sadece ayarın yapıldığı sunucuda geçerlidir.
- `@everyone` rolü yetkili rol olarak ayarlanamaz.

## Oyun Komutları

### /oyun_durum
Aktif turun durumunu gösterir:
- Oyun kanalı
- Tur numarası
- Turdaki kelime sayısı
- Beklenen başlangıç harfi

Kullanım:
```text
/oyun_durum
```

### /oyun_sifirla
Mevcut turu manuel olarak bitirir, tur liderliğini kanala gönderir ve yeni tur başlatır.

Kullanım:
```text
/oyun_sifirla
```

Notlar:
- Liderlik tablosu önce ayarlı oyun kanalına gönderilmeye çalışılır.
- Oyun kanalı ayarlı değilse, komutun yazıldığı metin kanalı kullanılır.

## Profil ve Liderlik Komutları

### /seviye
Kullanıcının seviye ve puan bilgilerini gösterir.

Kullanım:
```text
/seviye
```

Başka bir kullanıcı için kullanım:
```text
/seviye kullanici:@kullanici
```

Not: Cevap sadece komutu kullanan kişiye görünür (ephemeral).

### /liderlik
Sunucu liderlik tablosunu gösterir.

Kullanım:
```text
/liderlik tur:<puan|seviye|gunluk|haftalik>
```

Seçenekler:
- `puan`: Toplam puan liderliği
- `seviye`: Seviye liderliği
- `gunluk`: Son 24 saat
- `haftalik`: Son 7 gün

Not:
- `seviye` türü sadece komutu kullanan kişiye görünür.
- Diğer türler kanalda herkese açık görünür.

## Yardım Komutu

### /yardim
Komutların kısa özetini gösterir.

Kullanım:
```text
/yardim
```

Not: Cevap sadece komutu kullanan kişiye görünür (ephemeral).

## Oyun Akışı (Komut Dışı)

Komutlar dışında oyunu sürdürmek için oyun kanalına doğrudan kelime yazılır.

Kurallar:
- Tek kelime olmalı.
- En az 2 harf olmalı.
- Kelime listede bulunmalı.
- Kelime, beklenen harfle başlamalı.
- Tur içinde aynı kelime tekrar kullanılamaz.
- `ayar_ardisik_oyun` kapalıysa aynı kullanıcı art arda oynayamaz.

Kaçış karakteri kullanımı:
- Oyun kanalında normal mesaj atmak için mesajın başına kaçış karakterini ekleyin.
- Varsayılan kaçış karakteri: `\`
