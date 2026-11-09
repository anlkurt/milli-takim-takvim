# Milli Takım Takvimleri

Türkiye **A Milli Erkek Basketbol** ve **A Milli Kadın Voleybol** takımlarının maçlarını
Apple Takvim'e abone olunabilir iki takvim olarak ekler. Maçlar açıklandıkça veya saatleri
değiştikçe takvimler kendiliğinden güncellenir. Her maçtan **1 saat** ve **5 dakika** önce
hatırlatma gelir.

| Takvim | Adres |
|---|---|
| 🏀 Basketbol (A Erkek) | `https://anlkurt.github.io/milli-takim-takvim/basketbol.ics` |
| 🏐 Voleybol (A Kadın) | `https://anlkurt.github.io/milli-takim-takvim/voleybol.ics` |

## Apple Takvim'e ekleme

Her iki adres için ayrı ayrı:

1. Mac'te Takvim → **Dosya → Yeni Takvim Aboneliği…** → adresi yapıştırın → Abone Ol.
2. Açılan pencerede:
   - **Konum:** iCloud (iPhone ve iPad'de de görünmesi için)
   - **Sil: Uyarıları** ve **Uyarıları yok say** kutuları **işaretsiz** olmalı (yoksa hatırlatmalar gelmez)
   - **Otomatik yenile:** Her saat

## Hangi maçlar var?

| Takım | Kaynak | Kapsanan organizasyonlar |
|---|---|---|
| Basketbol | [FIBA](https://www.fiba.basketball/en/events) | Dünya Kupası ve elemeleri, EuroBasket ve elemeleri, Olimpiyatlar |
| Voleybol | [Volleyball World](https://en.volleyballworld.com/global-schedule) | Milletler Ligi (VNL), Dünya Şampiyonası, Olimpiyatlar |
| Voleybol | [CEV](https://livescores.cev.eu/) | Avrupa Şampiyonası ve elemeleri, Avrupa Ligi |

Hazırlık maçları ve özel turnuvalar bu kaynaklarda yer almadığı için takvimde yoktur.

## Nasıl çalışır?

- `milli_takvim.py` maçları yukarıdaki kaynaklardan çeker. FIBA'nın etkinlik listesine yeni
  bir turnuva (ör. EuroBasket elemeleri) eklendiğinde kendiliğinden taranır.
- GitHub Actions bunu her saat çalıştırır ve fikstür değiştiyse `docs/` altındaki `.ics`
  dosyalarını günceller; GitHub Pages dosyaları yukarıdaki adreslerden yayınlar.
- Saati henüz açıklanmamış maçlar o güne "(saat belli değil)" etiketiyle tüm gün etkinliği
  olarak eklenir; saat açıklanınca aynı etkinlik güncellenir.
- Bir takvimin kaynağı çalışmazsa o takvim eski haliyle kalır ve workflow hata verir
  (GitHub e-postayla haber verir).
