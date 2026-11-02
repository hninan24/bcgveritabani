# Boykot Çalışma Grubu Veritabanı

İsrail boykot listelerinin marka bazında birleştirilmiş veritabanı. Site: **https://hninan24.github.io/ortak-kriter-veritabani/**

Veritabanında 21 listeden toplanan 10.874 kuruluş var. Her kuruluş için şunlar gösterilir:

- listelerin hükmü,
- açıklama metni,
- kaynak bağlantısı,
- çatı şirket ilişkisi,
- kategori (listelerin kendi kategorilerinden).

Kriter kodu yoktur. Kuruluşlar listelerin hükmüne ve kategoriye göre ayrılır.

## Listeler

| Liste | Kayıt |
|---|---:|
| Boykot Market (boykotmarket.com) | 6.342 |
| Boykot Dedektifi (boykotdedektifi.com) | 2.556 |
| No Thanks (iOS uygulaması, üç seviye) | 2.191 |
| DBIO — Don't Buy Into Occupation (2025) | 1.218 |
| bykt.org | 1.167 |
| Boykot.co (yalnız “Boykot” durumundakiler) | 934 |
| Abbott & Keefer | 687 |
| Who Profits | 472 |
| Kolay Boykot — Filistin İçin | 330 |
| Eczanede Boykot (ilaçlar, kök marka) | 316 |
| Bilinçli Tüketim | 296 |
| BM OHCHR A/HRC/63/20 (Liste A) | 219 |
| Boycat — uygulamadaki “En iyi markalar” (Watermelon) | 199 |
| Investigate (AFSC) | 187 |
| FDH — “Kolay Boykot” PDF kitapçığı, Türkçe rehberin “Utanç Listesi” ve çatı şirket görselleri (yalnız boykot tarafı) | 581 |
| Boykot Rehberi — Filistin İnisiyatifi'nin “Market Ürünleri Boykot Listesi” kitapçığı | 160 |
| BoykotListe (boykotliste.com) | 415 |
| Boycott Israel (boycott-israel.org; 74 şirket, 140 alt marka) | 214 |
| Genç Müslümanlar (gencmuslumanlar.com, sayfa Kasım 2023 tarihli) | 93 |
| AFSC — Gazze soykırımı şirketleri | 58 |
| Yerli Reçete — yerli ilaç rehberi; boykot listesi değil, yalnız çatıların eksik ilaçları için firma bilgisi | 437 |

Metinler ve hükümler ilgili listelere aittir. Her kaydın yanında kaynağına giden bağlantı vardır.

Son güncelleme: 2 Kasım 2026. Dört liste eklendi:

- **Boykot Market** (6.342 marka). Sitenin kendi BDS / AMP / Boykot Market etiketi solda filtre olarak var. Bu etiket derece değil; site boş kalan değerleri de BDS sayıyor.
- **BoykotListe** (415 satır). Yüksek / Orta / Düşük risk solda filtre olarak var.
- **Boycott Israel** (74 şirket, 140 alt marka). Çok yüksek / Yüksek / Orta / Düşük etki solda filtre olarak var. Sayfanın dipnotu GPT-4 ile derlenen veri de kullanıldığını söylüyor.
- **Genç Müslümanlar** (93 kayıt, tek düzey, sayfa Kasım 2023 tarihli).

3.610 kuruluş veritabanına yeni girdi. Metinler özgün hâliyle duruyor. Bu listeler mevcut kuruluşların çatısını değiştirmez; çatı ve kategori etiketi yalnız yeni kuruluşlarda kullanıldı. Boykot Market'in sahip alanı metinde “Sahip” satırı olarak durur; yatırımcı, distribütör ve çok sahipli yazımlar çatı sayılmadı.

Aynı gün önce **Yerli Reçete** (yerlirecete.com, veri Haziran 2024) 17. kaynak olarak eklendi: Eczanede Boykot'un sekiz boykot çatısının ve veritabanında bulunan diğer ilaç firmalarının (Abdi İbrahim, Sandoz, GSK, Viatris, Abbott, Eczacıbaşı, Roche, Nestle, Lilly, Danone…) veritabanında olmayan 437 ilacı kök marka olarak çatılarının altına girdi. Yerli Reçete boykot listesi değildir, yalnız ilacın firmasını gösterir; kayıttaki etiket hüküm değil, çatının geldiği gruptur.

30 Ekim 2026: **FDH** 16. liste olarak eklendi: 11 çatı ve 570 marka; 452'si veritabanında zaten vardı, 129'u yeni (çoğu çatı görsellerindeki Kellogg's, General Mills, Kraft, Mondelēz, Nestlé markaları; General Mills yeni çatı). FDH üç görsel kaynaktan elle yazıya geçirildi:

- “Kolay Boykot” adlı PDF kitapçığın ALMA / AL sayfaları. Bu kitapçığın kolayboykot.com sitesiyle ilgisi yok.
- Türkçe rehberin “Utanç Listesi” sayfaları.
- Çatı şirketleri alt markalarıyla gösteren kampanya görselleri ve posteri.

Yalnız boykot tarafı alındı; kitapçığın önerdiği yerli alternatifler alınmadı. Dört seviye var: “Boykot”, “Tam boykot değil” (“tam boykot değildir ancak yine de kullanmayalım”), “Mümkünse alma” ve “Tavsiye edilmiyor” (kitapçığın “tavsiye etmiyoruz” ya da “yerli değil” notuyla andıkları). Sitede bir FDH seviyesi filtresi var. Kaynaklar internette yayımlanmadığı için kayıtlarda bağlantı yok.

Markalar görsellerdeki çatıya, veritabanındaki çatıyla aynıysa ya da kuruluşun veritabanında çatısı yoksa bağlandı. Farklıysa bağlanmadı ve açıklamada yazıyor; örneğin görseller KFC'yi PepsiCo, L'Oréal markalarını Nestlé altında gösteriyor. Görseller kısmen eski. Satıldığı bilinen markalar (Ferrero'ya geçen Butterfinger ve Wonka şekerlemeleri, Hormel'e geçen Planters gibi) eski çatıya bağlanmadı. Kitapçığın sayfa başlıkları (Kahve, Şampuan, Araba, Bankacılık…) kategori etiketi oldu. Görsellerden gelen ve etiketi olmayan 112 yeni markanın kategorisi web aramasından geldi; ikisi (Just for Me, Ombrelle) kategorisiz kaldı.

28 Ekim 2026'da iki değişiklik yapıldı:

- **Kategori.** Her kuruluşa listelerin kendi kategori alanlarından devralınan bir ana kategori verildi (aşağıda **Kategoriler**). Sitede Kategori filtresi var; ayrıntı panelinde hangi listenin hangi etiketi verdiği görünüyor; ÖBL'nin Excel dosyasındaki “Sektör” sütunu “Kategori” oldu. Kategori kontrolünde aynı adı taşıyan üç farklı marka ayrıldı: American Heritage Dergisi (Mars'ın çikolatası değil), Giotto Boya Kalemleri (Ferrero'nun gofreti değil), Bambi (Coca-Cola HBC) (Türk ayakkabı markası değil).
- **Boykot Rehberi.** Filistin İnisiyatifi'nin kitapçığı ([sayfalar](https://cetinkayakoc.net/earc/BoykotRehberi/)) 15. liste olarak eklendi: 9 çatı ve 151 marka, hepsi veritabanında zaten vardı. Markalar kitapçığın “Boykottaki üreticiler ve markaları” sayfalarında yazıldıkları çatıya bağlandı; kategori sayfalarının başlıkları (İçecekler, Yiyecekler, Kozmetik ve Kişisel Bakım, Temizlik, Bebek Ürünleri) kategori etiketi oldu. Kitapçıkta tek seviye (“Boykot”) var ve marka başına gerekçe yok; açıklama, rehberin markayla ilgili söylediklerinden (sayfa, kategori, çatı) derlendi ve bağlantı markanın geçtiği kitapçık sayfası.

26 Ekim 2026: No Thanks uygulamasının 2.191 kaydı eklendi (iOS uygulamasının 26 Ekim verisi): seviye (Level 1: Strong Connection to Israel, Level 2: Indirect Support for Israel, Level 3: No Known Connection to Israel), BDS işareti, uygulamadaki gerekçe metni ve kaynak bağlantıları. Level 3'teki üç marka (Temu, Dr. Bronner's, Ecostore) uygulamada “bilinen bağlantısı yok” seviyesinde ama gerekçe metinleri eleştirel; sitede nötr renkle gösterilir. Uygulamanın marka sayfası ve çatı alanı yok; 918 marka mevcut kuruluşlara bağlandı, 1.233'ü yeni. Aynı adı taşıyan farklı markalar ayrı tutuldu (ör. Silk (Danone), Brisa (Coca-Cola), Tic Tac).

Aynı gün Boykot.co'nun “Boykot” durumundaki 934 markası eklendi (24 Ekim taraması; “Boykot değil” markalar alınmadı): sitedeki gerekçe metni, marka sayfası ve kanıt bağlantısı; 865'i mevcut kuruluşlara bağlandı, 29'u yeni. Metinler sitenin kendi metinleridir ve kaynak sayfasıyla birlikte verilir.

24 Ekim 2026: Boycat uygulamasının “En iyi markalar” listesi (199 marka) eklendi: uygulamadaki seviye (Official BDS Priority Campaign, Level 2, Level 3), research.boycat.io'daki gerekçe metni ve şirket sayfası; 116'sı mevcut kuruluşlara bağlandı, 82'si yeni. Ayrıntı panelinde çatının alt markalarından ve alt markanın çatısından devraldığı listeler de gösteriliyor. bykt'nin listeden çıkardığı Damla Minera “geri çekildi” olarak işaretlendi.

20 Ekim 2026: bykt 20 Ekim, Bilinçli Tüketim 18 Ekim verisine geçirildi: Lefties, Derimod ve Philips eklendi, 27 bykt gerekçesi güncellendi. Who Profits'in kaldırdığı Aldo ve SEMI kayıtları “geri çekildi” olarak işaretlendi.

## Kategoriler

Kategoriler önce listelerin kendi etiketlerinden devralınır. Ana kategori sayısı 23'tür: Gıda & İçecek, Kozmetik & Kişisel Bakım, Temizlik & Ev Bakımı, Giyim & Aksesuar, Teknoloji & Elektronik, Sağlık & İlaç, Anne-Bebek & Oyuncak, Evcil Hayvan, Ev & Yaşam, Market & Perakende, Otomotiv, Ulaşım, Turizm & Lojistik, Medya & Eğlence, Finans & Sigorta, Enerji, İnşaat, Yapı & Emlak, Sanayi & Kimya, Savunma & Güvenlik, Tarım, Kırtasiye & Kitap, Tütün, Hizmet & Danışmanlık, Lobi, Dernek & Kurum.

1. Her listenin kategori etiketi bir eşleme tablosuyla ana kategoriye bağlandı (ör. Boykot.co “Kişisel Bakım” ve No Thanks “Personal Care” → Kozmetik & Kişisel Bakım). Sektör bildirmeyen ya da birbirinden farklı şeyleri toplayan etiketler (“Şirket”, “Holding”, “Other”, “İşletme”) kategori vermez.
2. Kategori alanı olmayan listelerde listenin yapısı kullanıldı: Eczanede Boykot'un ilaçları Sağlık & İlaç, DBIO'nun finans kuruluşları Finans & Sigorta.
3. Kendi etiketi olmayan çatı şirket, alt markalarının kategorilerini alır.
4. Listeler bir kuruluşa birbiriyle ilgisiz kategoriler veriyorsa (ör. bir şampuana “Gıda”) kontrol listesiyle karar verildi; komşu kategoriler (ör. Kozmetik ile Sağlık) birlikte kalır.
5. Listelerde kullanılabilir etiketi olmayan kuruluşların her biri için bir web araması yapıldı. Bulunan kategori sitede “web araması” kaynağıyla, gerekçesi ve kaynak bağlantısıyla görünür. Aramanın bir şey bulmadığı kuruluşlara ve bazı başka kuruluşlara kategoriyi çalışma grubu verdi (“çalışma grubu kararı”).
6. Ticari olmayan kuruluşlar (siyasi lobiler ve PAC'ler, dernek, vakıf ve hayır kurumları, üniversiteler, devlet kurumları) “Lobi, Dernek & Kurum” kategorisinde toplanır.
7. Her kategori kendi içinde tek tek gözden geçirildi. Kategoriyi tek bir listenin etiketinden alan ama kategoriye uymayan kuruluşlar o kategoriden çıkarıldı ya da doğru kategoriye taşındı (ör. No Thanks'in “Food & Beverages” etiketindeki kedi-köpek mamaları Evcil Hayvan'a, Bilinçli Tüketim'in “Temizlik” etiketindeki şampuan ve deodorantlar yalnız Kozmetik & Kişisel Bakım'a). Kullanılmayan etiket ayrıntı panelinde görünür.

Sonuç: kuruluşların çoğunun kategorisi kendi liste etiketinden, 1.403'ünün listenin yapısından, bir kısmının da alt markalarından geliyor. 460 kuruluşun kategorisi web aramasından, bir kısmının kategorisi de çalışma grubu kararından geliyor. İki kuruluş kategorisiz (Just for Me, Ombrelle). Bir kuruluş birden çok kategoride olabilir.

## Kaynak izleme

Listelerin çoğu canlı sitelerde değişiyor. `izleme/` klasöründeki betik bu siteleri GitHub Actions üzerinden her gün (Boykot Dedektifi, Kolay Boykot ve Boykot.co'yu her pazartesi) kontrol eder. Bir önceki kontrolden bu yana eklenen, çıkan, hükmü ya da gerekçesi değişen kayıtları raporlar ve [`izleme` etiketli Issue](https://github.com/hninan24/ortak-kriter-veritabani/issues?q=label%3Aizleme)'ya yazar. Her değişiklik olay kaydına (`izleme/olaylar.json`) da girer ve sitenin **Güncellemeler** sekmesinde marka, liste, değişiklik türü ve tarihiyle görünür. Bir listenin geri çektiği kanıt silinmez, “geri çekildi” diye işaretlenir. Yeni veri veritabanına kendiliğinden işlenmez. Ayrıntı: [izleme/README.md](izleme/README.md).

## Öncelikli Boykot Listesi (ÖBL) nasıl hazırlanır

1. Siteyi açın. **Kuruluşlar** sekmesinde bir markanın sağındaki **“Öncelikli Boykot Listesine Ekle”** düğmesine basın. Marka, çatı şirketi ve çatının bütün alt markalarıyla birlikte listeye girer.
2. **Öncelikli Boykot Listesi** sekmesinde yalnızca çatı şirketler görünür; alt markalar kuruluşa tıklayınca açılan panelde listelenir. Yanlış eklediğiniz bir kuruluşu **“Listeden çıkar”** ile kaldırabilirsiniz.
3. Kampanya önceliği vermek istediğiniz çatının sağındaki **yıldıza** basın. Yıldız kırmızıya döner ve kuruluş listenin başındaki “Kampanya önceliği” bölümüne geçer. Yıldızsızlar, suçu sabit olduğu hâlde günlük tüketimde olmadığı için aşağıda kalır. Yıldızı kaldırmak için yeniden basın.
4. Seçimleriniz **yalnızca kendi tarayıcınızda** saklanır. Başka bir tarayıcıda ya da cihazda görünmez. Tarayıcı verisini silerseniz liste de silinir.
5. Listeniz bitince ÖBL sekmesindeki **“Excel olarak dışa aktar”** düğmesine basın. Dosyayı gruba gönderin; listeler sonra birleştirilir.

Excel dosyasında şu sayfalar var:

- **Kampanya:** yıldızladığınız çatılar, alt markalarının adlarıyla.
- **Çatılar:** her çatı için listelerin hükmü, seçtiğiniz marka ve kampanya önceliği.
- **Tüm kuruluşlar:** çatılar ve bütün alt markaları.
- **Açıklamalar:** listelerin metinleri ve bağlantıları.
- **Bilgi**

## Dosyalar

- `izleme/`: kaynak izleme betiği, anlık görüntüler ve raporlar.
- `index.html`: sitenin tamamı. Veri sayfanın içindedir. Dosyayı indirip internet olmadan da açabilirsiniz; bu durumda seçimleriniz o tarayıcının yerel belleğinde tutulur.
