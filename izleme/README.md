# Kaynak izleme

Veritabanındaki listelerin çoğu internette canlı ve değişiyor: markalar ekleniyor, çıkarılıyor, hükümleri ve gerekçe metinleri güncelleniyor. Bu klasördeki betik kaynak siteleri düzenli olarak kontrol eder ve bir önceki kontrolden bu yana neyin değiştiğini raporlar.

Sitelerin hiçbiri değişiklik bildirimi (webhook, RSS) sunmadığı için betik siteleri belli aralıklarla kendisi okur. Değişiklikler veritabanına **kendiliğinden işlenmez**. Rapor okunur, değişiklikler gözden geçirilir ve veritabanı yeniden üretilir.

## Ne zaman çalışır

GitHub Actions'taki **Kaynak izleme** iş akışı (`.github/workflows/izleme.yml`) iki zamanda çalışır:

| Zaman | Kontrol edilen kaynaklar |
|---|---|
| Her gün 07:17 (TSİ) | bykt, Bilinçli Tüketim, Eczanede Boykot, Who Profits, AFSC Gazze listesi, DBIO, AFSC Investigate, Abbott & Keefer, BoykotListe, Genç Müslümanlar, Boycott Israel, Yerli Reçete, No Thanks |
| Pazartesi 07:47 (TSİ) | Yukarıdakiler ve tam tarama gerektiren Boykot Dedektifi, Kolay Boykot, Boykot.co, Boykot Market ve Boycat |

GitHub zamanlanmış çalışmaları yoğunluğa göre birkaç dakika ile bir saat arasında geciktirebilir. Elle çalıştırmak için deponun **Actions** sekmesinde **Kaynak izleme → Run workflow** seçilir. Kutuya `hizli`, `tam` ya da virgülle kaynak adları (örneğin `bd,kb`) yazılır.

## Neler izlenir

| Kaynak | Nasıl | Kapsam (veritabanına alınan) |
|---|---|---|
| bykt.org | Sitenin bütün veritabanı tek bir JSON dosyası. Önce dosyanın parmak izine bakılır, değiştiyse indirilir. | Kesin Boykot, İnsafa Bağlı |
| Bilinçli Tüketim | Sitenin veri dosyası (snapshot.json) | çatısı 1–3 çarpılı ve sitede listelenen markalar |
| Boykot Dedektifi | Site haritası ve bütün marka sayfaları (yaklaşık 4.000 sayfa, 20–25 dakika) | Boykot, İkincil Boykot, Şüpheli |
| Kolay Boykot | “Filistin İçin” ve beş seviye kategorisi, marka sayfaları | listenin tamamı |
| Boykot.co | 26 kategori sayfası, marka sayfaları ve sayfalardaki “Diğer … markaları” kartları (yaklaşık 1.600 sayfa), kanıt bağlantıları (yalnız değişenler yeniden okunur); 15–25 dakika | “Boykot” durumundakiler (“Boykot değil” markalar da izlenir; “Boykot değil”den “Boykot”a geçen marka kapsama girer) |
| Eczanede Boykot | Ana sayfadaki boykot firmaları, firmaların ürün sayfaları, sitedeki liste tarihi | boykot firmaları ve ilaçları |
| Who Profits | Şirket dizini | yalnız eklenen ve çıkan şirketler |
| AFSC Gazze listesi | Liste sayfası (şirketler, türleri, ülkeleri, kategorileri, metinleri) | listenin tamamı |
| DBIO | Veri sayfasındaki CSV dosyaları (ad ve içerik) | yeni ya da değişen veri dosyası |
| AFSC Investigate | İndirme sayfasındaki veri seti (ad ve içerik) | yeni ya da değişen veri seti |
| Abbott & Keefer | Site haritasındaki marka sayfaları | yalnız eklenen ve çıkan markalar |
| Boykot Market | Arama dosyası ve bütün marka sayfaları (yaklaşık 6.300 sayfa, 10–15 dakika) | listenin tamamı |
| Boycat | research.boycat.io'daki şirket sayfaları: seviye ve gerekçe | veritabanındaki 199 marka; listeye yeni giren marka görülmez |
| BoykotListe | Site haritasındaki marka sayfaları. Veriyi veren `/api/` yolu robots.txt ile botlara kapalı, sayfalar da veriyi oradan yüklüyor. | yalnız eklenen ve çıkan markalar; hüküm ve metin değişikliği görülmez |
| Genç Müslümanlar | Liste sayfası (başlıklar, metinler, bağlantılar) | listenin tamamı |
| Boycott Israel | Liste sayfası (şirketler, seviyeler, metinler, alt markalar) | listenin tamamı |
| Yerli Reçete | Sitenin veri paketi. Paket adı aynıysa indirilmez. | veritabanına ilaçları alınan 24 firma |
| No Thanks | App Store'daki sürüm. Liste Mac'teki uygulamanın klasöründe (`nothanks.db`), buradan erişilmez. Uygulama listeyi sunucudan eşitlediği için liste yeni sürüm çıkmadan da değişebilir. Karşılaştırmak için güncel `nothanks.db` kopyası `listeler/No Thanks/` altına eklenir. | yalnız uygulama sürümü (zayıf işaret) |

İzlenmeyen listeler: BM OHCHR (A/HRC/63/20, yıllık rapor), Boykot Rehberi (Filistin İnisiyatifi, görsel kitapçık) ve FDH (kaynakları internette yayımlanmayan PDF ve görseller).

## Değişiklikler nereye yazılır

- **Olay kaydı ve sitenin Güncellemeler sekmesi:** `olaylar.json`, listelerin her adımını tarihiyle tutar: ekleme, çıkarma, seviye yükseltme ya da düşürme, metin düzeltme, kaynak güncelleme, çatı ve ad değişikliği. Yalnız veritabanının kapsamına dokunan değişiklikler olaydır. Sitenin **Güncellemeler** sekmesi bu kaydı gösterir. GitHub Pages'teki site kaydı her açılışta yeniden okur, böylece sitenin son derlenmesinden sonra tespit edilen olaylar da “henüz işlenmedi” durumuyla görünür.
- **Issue:** Değişiklik bulunan her çalışma, `izleme` etiketli açık Issue'ya yorum ekler. Açık Issue yoksa yenisini açar. Depoyu izleyenlere (Watch) GitHub bildirimi gider. Değişiklikler işlendikten sonra Issue kapatılabilir; sonraki değişiklik yeni bir Issue açar.
- **Rapor:** `raporlar/YYYY-MM-DD-SSDD.md`. Bildirimde kaynak başına en çok 25 madde gösterilir; tam liste rapordadır.
- **Anlık görüntü:** `veri/<kaynak>.json`, her kaynağın son okunan hâli. Git geçmişi aynı zamanda değişiklik arşividir.
- **Durum:** `durum.json`, her kaynağın son kontrol zamanı, son değişikliği ve durumu.

Bir kaynak okunamazsa (site kapalıysa ya da sayfa yapısı değiştiyse) diğerleri yine işlenir. O çalışma hatalı (kırmızı) görünür, GitHub da iş akışını son değiştirene e-posta gönderir. Okunamayan kaynağın önceki anlık görüntüsü korunur; kısmi okuma “kalkan marka” diye raporlanmaz. Bazı siteler GitHub'ın sunucu adreslerinden gelen isteklere zaman zaman bot doğrulama sayfası döndürür (DBIO'nun barındığı SiteGround'un HTTP 202'si gibi). Bu durum son başarılı kontrolden bu yana 7 günden kısa sürüyorsa geçici sayılır: çalışma yeşil kalır, özette “geçici olarak okunamayan” diye not edilir. 7 günü aşarsa hata verir. DBIO ve Investigate'in veri sayfası engellenirse bilinen veri dosyaları doğrudan indirilip kontrol edilir.

## Rapor nasıl okunur

Her kaynak için önce veritabanının kapsamındaki değişiklikler, önem sırasıyla listelenir:

1. **Yeni kayıt**, **Kapsama girdi** (ör. Alınabilir → İnsafa Bağlı): veritabanına eklenmesi gerekir.
2. **Kapsamdan çıktı**, **Listeden kalktı**: veritabanından çıkarılması ya da hükmünün düzeltilmesi gerekir.
3. **Hüküm**, **çatı** ya da **ad değişti**: kayıt güncellenmeli. Çatı değişikliği alt markaların bağlandığı çatıyı da etkileyebilir.
4. **Gerekçe metni** ya da **kaynak bağlantıları değişti**: açıklama güncellenmeli. “Metin farkı” açıldığında değişen bölüm görünür: ~~silinen~~, **eklenen**.

Kapsam dışındaki değişiklikler (ör. bykt'de Alınabilir markalar) en sonda kapalı bir bölümde sayılır.

Her maddedeki **veritabanında** notu, kaydın adının sitedeki bir kuruluşun adıyla ya da diğer adlarından biriyle eşleşip eşleşmediğini gösterir. Eşleşme yalnız yazıma bakar. “Veritabanında yok” bir markanın yeni olduğunu, ya da veritabanında başka bir yazımla geçtiğini gösterebilir.

## Geri çekilen kanıtlar

Bir liste bir kaydı çıkardığında ya da hükmünü veritabanının kapsamı dışına indirdiğinde (ör. bykt'de “Kesin Boykot” → “Alınabilir”), kuruluş veritabanından silinmez. Listenin kaydı, ayrıntı panelinde geri çekilme tarihiyle ve geri çekilmeden önceki metniyle **“geri çekildi”** diye işaretli kalır. Bu kayıt kanıt sayılmaz, kod vermez ve liste sayısına girmez. Kuruluşun başka listelerdeki kayıtları geçerliliğini korur. Başka listede kaydı olmayan kuruluş da veritabanında kalır ve “geri çekildi” rozetiyle görünür. İlk örnekler: Who Profits'in 20.10.2026'da kaldırdığı Aldo (Boykot Dedektifi kaydıyla duruyor) ve SEMI.

## Değişiklikler veritabanına nasıl işlenir

Veritabanı bu depoda değil, yerel çalışma klasöründe üretilir (`listeler/Ortak Kriter Veritabanı/kaynak/`):

Geri çekmeler, veritabanı derlenirken olay kaydından kendiliğinden işaretlenir (`olay_uygula.py`). Diğer değişiklikler listenin yeni verisiyle gelir:

1. Değişen listenin güncel verisi indirilir ya da yeniden taranır (bykt ve Bilinçli Tüketim için `listeler/bykt/kod/disa_aktar.py` ve `listeler/bilinclituketim/kod/disa_aktar.py`).
2. `variants.py`'de V ve VI'nın kaynak dosyası yeni dışa aktarıma çevrilir.
3. `python3 build_db.py v && python3 build_outputs.py v`, ardından `python3 build_db.py vi && python3 build_outputs.py vi`.
4. VI'nın html'i bu depoda `index.html` olarak güncellenir ve gönderilir.

İlk anlık görüntüler, veritabanının o gün kullandığı yerel dışa aktarımlardan kuruldu (`izleme_tohum.py`). Böylece izlemenin ilk raporu, veritabanına henüz işlenmemiş değişiklikleri gösterir. Bu dışa aktarımlar şunlardır: bykt 20.10.2026, Bilinçli Tüketim 18.10.2026, Boykot Dedektifi 07.10.2026, Kolay Boykot ve Eczanede Boykot 19.10.2026, Boykot.co 24.10.2026 (izlemeye 26.10.2026'da eklendi), Who Profits 19.10.2026, AFSC Gazze 05.10.2026, Abbott & Keefer 02.10.2026, DBIO 2025, AFSC Investigate Temmuz 2025. Sonradan eklenenler: Boycat 24.10.2026, No Thanks 26.10.2026 (uygulama sürümü 3.5.0), Yerli Reçete 30.10.2026, Boykot Market, Genç Müslümanlar ve Boycott Israel 02.11.2026, BoykotListe 03.11.2026 (site haritası).

## Sınırlar

- Who Profits ve Abbott & Keefer'da yalnız eklenen ve çıkan kayıtlar izlenir. Şirket metinlerindeki ya da etiketlerdeki değişiklikler görünmez.
- DBIO ve Investigate'te yalnız veri dosyasının değişip değişmediğine bakılır. Değişirse yeni dosya elle incelenir.
- Boykot.co'da bazı marka sayfaları sürekli sunucu hatası (500) verir. Bu markalar kategori satırındaki ya da yan karttaki bilgiyle (ad, durum, kısaltılmış metin) kaydedilir. Daha önce tam okunmuş bir sayfa bozulursa önceki kaydı korunur. Kategori sayfaları yalnız boykottaki markaları listelediği için “Boykot değil” markalar yalnız kartlardan bulunur; hiçbir karta düşmeyen “Boykot değil” kaydı görülmez.
- Boycat'in sitesi (research.boycat.io) GitHub'ın sunucularına HTTP 403 ile bot koruması döndürüyor (03.11.2026'da iki deneme). Aynı sayfalar başka adreslerden açılıyor. GitHub'da okunamadığı sürece Boycat kontrol edilmiş sayılmaz; son başarılı kontrolün üzerinden 7 gün geçince haftalık çalışma hata verir. Yerelde çalıştırmak için: `python izleme/izle.py bc`, ardından değişen dosyalar gönderilir.
- Boykot Dedektifi Cloudflare arkasındadır. GitHub'ın sunucularını engellerse haftalık tarama hata verir. Bu durumda tarama yerelde çalıştırılır: `python izleme/izle.py bd`, ardından değişen dosyalar gönderilir.
- Bir sitenin sayfa yapısı değişirse ayrıştırıcı kayıtları okuyamaz ya da yanlış okur. Okunan kayıt sayısı önceki kontrole göre çok düşükse ya da kayıtların yarısından fazlası birden değişmiş görünüyorsa kaynak “kontrol edilemedi” sayılır ve anlık görüntüsü güncellenmez. Değişiklik gerçekse iş akışı **zorla** kutusu işaretlenerek yeniden çalıştırılır. Ayrıştırıcı bozulduysa `izleme/kaynaklar.py` düzeltilir.
