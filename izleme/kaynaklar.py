"""Kaynak sitelerin çekicileri ve normalleştiricileri.

Her kaynak `cek(onceki)` ile güncel durumu alır ve ortak biçimde döndürür:
    {"kayitlar": {kimlik: kayit}, "parmak_izi": str|None, "meta": {...}, "uyarilar": [...]}
ya da parmak izi önceki kontrolle aynıysa {"degismedi": True, "parmak_izi": ...}.

Kayıt alanları (hepsi isteğe bağlı): ad, hukum, kapsam (veritabanının aldığı hükümlerden biri mi), cati,
metin (gerekçe/açıklama), kaynaklar (kanıt bağlantıları), url, ek (kaynağa özgü diğer alanlar).
`normalle_*` işlevleri hem canlı çekimde hem de ilk anlık görüntüyü yerel dışa aktarımlardan kurarken kullanılır; böylece
ikisi aynı biçimde karşılaştırılır.
"""
import datetime as dt
import hashlib
import html as H
import json
import random
import re
import threading
import time
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
_yerel = threading.local()


class KaynakHatasi(Exception):
    pass


class EngelHatasi(KaynakHatasi):
    """Site isteği bot korumasıyla geri çevirdi: SiteGround'un HTTP 202 doğrulama sayfası, Cloudflare'in 403/503 sayfası.
    Çoğunlukla GitHub'ın sunucu adreslerine özgü ve geçicidir (aynı sayfa başka yerden açılır)."""


ENGEL_IZI = ("sgcaptcha", "cf-chl", "challenge-platform", "just a moment", "cf_chl", "imunify")


def oturum():
    if not hasattr(_yerel, "s"):
        _yerel.s = requests.Session()
        _yerel.s.headers.update({"User-Agent": UA, "Accept-Language": "tr,en;q=0.8"})
    return _yerel.s


def al(url, deneme=5, bekle=5, kabul=(200,), **kw):
    """GET; geçici hatalarda artan beklemeyle yeniden dener. 404 gibi kabul edilen kodlar dışındakilerde hata verir."""
    son, engel = None, False
    for i in range(deneme):
        try:
            r = oturum().get(url, timeout=60, **kw)
            if r.status_code in kabul or r.status_code == 404:
                return r
            son = f"HTTP {r.status_code}"
            engel = r.status_code in (202, 406) or (r.status_code in (403, 415, 429, 503) and any(x in r.text[:20000].lower() for x in ENGEL_IZI))
            if engel and i >= 1:           # doğrulama sayfası: bir kez daha denenir, sonra uzun beklemeden bırakılır
                break
        except requests.RequestException as e:
            son, engel = type(e).__name__, False
        time.sleep(min(120, bekle * 2 ** i))
    if engel:
        raise EngelHatasi(f"{url}: {son}, sitenin bot koruması")
    raise KaynakHatasi(f"{url}: {son}")


def metin_coz(r):
    """Yanıtın metni. Başlıkta karakter kümesi yoksa requests Latin-1 varsayar ve Türkçe harfler bozulur: UTF-8 okunur."""
    if "charset" not in r.headers.get("content-type", "").lower():
        r.encoding = "utf-8"
    return r.text


def sayfa_metni(url, **kw):
    """Sayfanın metni; satır sonları \\n'e çevrilir (yerel dışa aktarımlar dosyadan okunduğu için öyle)."""
    return metin_coz(al(url, **kw)).replace("\r\n", "\n").replace("\r", "\n")


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


def tekil(xs):
    return list(dict.fromkeys(x.strip() for x in xs if isinstance(x, str) and x.strip()))


def bos(x):
    x = (x or "").strip() if isinstance(x, str) else x
    return x or None


def kayit(ad, hukum=None, kapsam=True, cati=None, metin=None, kaynaklar=(), url=None, *, tarih=None, eklenme=None, **ek):
    """tarih / eklenme: kaydın listedeki son güncelleme ve eklenme tarihi (biliniyorsa). Karşılaştırmaya girmez, yalnız
    olay tarihinde kullanılır."""
    r = {"ad": bos(ad), "hukum": bos(hukum), "kapsam": bool(kapsam), "cati": bos(cati), "metin": bos(metin),
         "kaynaklar": tekil(kaynaklar), "url": bos(url), "tarih": bos(tarih), "eklenme": bos(eklenme)}
    ek = {k: v for k, v in ek.items() if v not in (None, "", [], {})}
    if ek:
        r["ek"] = ek
    return {k: v for k, v in r.items() if v not in (None, [])}


# ===================================================================== bykt.org
BYKT_META = "https://firebasestorage.googleapis.com/v0/b/boykot-listesi-e7b96.firebasestorage.app/o/brands.json"
BYKT_DURUM = {"red": "Kesin Boykot", "orange": "İnsafa Bağlı", "green": "Alınabilir"}


def bykt_url(ad):
    s = re.sub(r"[\W_]+", "-", ad.strip().replace("İ", "i").lower()).strip("-")
    return "https://bykt.org/marka/" + urllib.parse.quote(s)


def _fb_tarih(u):
    if isinstance(u, dict) and "_seconds" in u:
        return dt.datetime.fromtimestamp(u["_seconds"], dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    return None


def normalle_bykt(veri):
    out = {}
    for b in veri:
        ad = (b.get("name") or "").strip()
        if not ad:
            continue
        out[b["id"]] = kayit(ad, BYKT_DURUM.get(b.get("status"), b.get("status")), b.get("status") in ("red", "orange"),
                             b.get("parentCompany"), b.get("reason"),
                             [s.get("url") for s in (b.get("reasonSources") or [])], bykt_url(ad),
                             tarih=_fb_tarih(b.get("updatedAt")), eklenme=_fb_tarih(b.get("createdAt")))
    return out


def cek_bykt(onceki):
    meta = al(BYKT_META).json()
    iz = meta.get("md5Hash")
    if not iz:
        raise KaynakHatasi("bykt: dosya bilgisi okunamadı")
    if iz == onceki.get("parmak_izi"):
        return {"degismedi": True, "parmak_izi": iz}
    veri = al(BYKT_META + "?alt=media").json()
    return {"kayitlar": normalle_bykt(veri), "parmak_izi": iz, "meta": {"dosya_guncelleme": meta.get("updated")}}


# ===================================================================== Bilinçli Tüketim
BT_URL = "https://api.bilinclituketim.com/data/snapshot.json"


def normalle_bt(d):
    B = {b["id"]: b for b in d["all_brands"]}
    goster = {b["id"] for b in d["brands"]}
    derece = {r["rate"]: r["name"] for r in d["rates"]}

    def kok(b):
        while b.get("parent") in B:
            b = B[b["parent"]]
        return b

    out = {}
    for b in B.values():
        k = kok(b)
        ust = B.get(b.get("parent"))
        out[str(b["id"])] = kayit(
            b["name"], derece.get(b["rate"]) or f"Listede değil ({b['rate']})",
            k["rate"] in (1, 2, 3) and k["id"] in goster, ust["name"] if ust else None, b.get("explanation"),
            list(b.get("other_links") or []) + list(b.get("image_links") or []),
            "https://bilinclituketim.com/brand/" + b["key"], tarih=(b.get("date_updated") or "")[:10],
            eklenme=(b.get("date_added") or "")[:10], sitede="Evet" if b["id"] in goster else "Hayır")
    return out


def cek_bt(onceki):
    r = al(BT_URL)
    d = r.json()
    iz = d.get("version") or sha(r.content)
    if iz == onceki.get("parmak_izi"):
        return {"degismedi": True, "parmak_izi": iz}
    return {"kayitlar": normalle_bt(d), "parmak_izi": iz, "meta": {"uretim": d.get("generated_at")}}


# ===================================================================== Boykot Dedektifi
BD = "https://boykotdedektifi.com"
BD_KAPSAM = ("Boykot", "İkincil Boykot", "Şüpheli")
URL_RE = re.compile(r'https?://[^\s<>"\'\)\]]+')


def _para_text(el):
    """Paragrafları satır olarak koruyarak düz metin (yerel tarayıcının parse.py'siyle aynı)."""
    if el is None:
        return ""
    el = BeautifulSoup(str(el), "html.parser")
    for br in el.find_all("br"):
        br.replace_with("\n")
    for td in el.find_all(["td", "th"]):
        td.insert_after(" | ")
    for b in el.find_all(["tr", "p", "li", "blockquote", "figure", "div", "h1", "h2", "h3", "h4", "h5", "h6"]):
        b.insert_before("\n")
        b.insert_after("\n")
    t = el.get_text("").replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", x).strip() for x in t.split("\n")]
    return "\n".join(x for x in lines if x)


def bd_ayristir(raw, slug):
    soup = BeautifulSoup(raw, "html.parser")
    main = soup.find("main")
    canon = soup.find("link", rel="canonical")
    m = re.search(r"-(\d+)$", slug)
    rec = {"id": int(m.group(1)) if m else None, "slug": slug, "url": canon["href"] if canon else ""}
    h1 = main.find("h1")
    sp = h1.find("span")
    if sp:
        sp.extract()
    rec["marka"] = h1.get_text(" ", strip=True)
    badge = main.select_one(".status-badge-premium")
    rec["durum"] = badge.get_text(" ", strip=True) if badge else ""
    parent = h1.find_next_sibling("p")
    rec["cati_sirket"] = parent.get_text(" ", strip=True) if parent else ""
    alert = main.select_one("div.alert")
    body = alert.select_one("div.text-muted") if alert else None
    rec["gerekce"] = _para_text(body)
    links = []
    if body:
        links += [a["href"].strip() for a in body.find_all("a", href=True)]
        links += [i["src"].strip() for i in body.find_all("img", src=True)]
        links += [u.rstrip(".,;:") for u in URL_RE.findall(body.get_text(" "))]
    rec["gerekce_linkleri"] = tekil(links)
    rec["kanit"] = [a["href"] for a in main.select("a.btn-brand-primary") if "Kan" in a.get_text() and a.get("href")]
    return rec


def normalle_bd(markalar):
    return {str(r["id"]): kayit(r["marka"], r["durum"], r["durum"] in BD_KAPSAM, r.get("cati_sirket"), r.get("gerekce"),
                                list(r.get("kanit") or []) + list(r.get("gerekce_linkleri") or []), r.get("url"))
            for r in markalar if r.get("id") is not None}


def cek_bd(onceki, isci=3):
    sm = al(BD + "/site-haritasi").text
    yollar = sorted(set(re.findall(r'href="(/b/[^"]+)"', sm)))
    eski = onceki.get("kayitlar") or {}
    if len(yollar) < 0.8 * max(len(eski), 1000):
        raise KaynakHatasi(f"Boykot Dedektifi: site haritasında yalnız {len(yollar)} marka (önceki {len(eski)})")
    recs, alinamayan, yok = [], [], []
    kilit = threading.Lock()

    def getir(p):
        for i in range(5):
            try:
                r = oturum().get(BD + p, timeout=60)
                if r.status_code == 200 and "<main" in r.text:
                    rec = bd_ayristir(r.text.replace("\r\n", "\n").replace("\r", "\n"), p.split("/b/", 1)[1].replace("/", "_"))
                    with kilit:
                        recs.append(rec)
                    time.sleep(0.3 + random.random() * 0.4)
                    return
                if r.status_code == 404:
                    with kilit:
                        yok.append(p)
                    return
            except requests.RequestException:
                pass
            time.sleep(min(120, 5 * 2 ** i))
        with kilit:
            alinamayan.append(p)

    with ThreadPoolExecutor(isci) as ex:
        list(ex.map(getir, yollar))
    if len(alinamayan) > 0.05 * len(yollar):
        raise KaynakHatasi(f"Boykot Dedektifi: {len(alinamayan)}/{len(yollar)} marka sayfası alınamadı")
    yeni = normalle_bd(recs)
    uyari = []
    if alinamayan:
        # alınamayan sayfaların önceki kaydı korunur (kalkmış sayılmaz)
        ids = {re.search(r"-(\d+)$", p).group(1) for p in alinamayan if re.search(r"-(\d+)$", p)}
        for i in ids:
            if i in eski:
                yeni[i] = eski[i]
        uyari.append(f"{len(alinamayan)} marka sayfası alınamadı; önceki kayıtları korundu")
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)),
            "meta": {"site_haritasi": len(yollar)}, "uyarilar": uyari}


# ===================================================================== Kolay Boykot
KB = "https://www.kolayboykot.com/"
KB_KATEGORI = {843: "filistin-icin", 844: "boykot-farkinda", 845: "boykot-kararli", 846: "boykot-oncu",
               847: "boykot-iradeli", 848: "boykot-mucahit"}


def _kb_text(node):
    if node is None:
        return ""
    for br in node.find_all("br"):
        br.replace_with("\n")
    for p in node.find_all("p"):
        p.append("\n")
    t = H.unescape(node.get_text(" "))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    return re.sub(r"\n{2,}", "\n", t).strip()


def _kb_kartlar(h):
    out = []
    for parca in h.split('<div class="card-product style-8"')[1:]:
        m = re.search(r'href="https://www\.kolayboykot\.com/marka/([^"]+)"', parca)
        if not m:
            continue
        etiket = re.search(r'<div class="on-sale-item[^"]*"[^>]*>\s*([^<]*?)\s*</div>', parca)
        ad = re.search(r'class="title link">\s*([^<]*?)\s*</a>', parca)
        kim = re.search(r"upsertLike\((\d+),\s*1", parca)
        out.append((m.group(1), etiket.group(1) if etiket else "", H.unescape(ad.group(1)) if ad else "",
                    int(kim.group(1)) if kim else 0))
    return out


def kb_marka(h):
    s = BeautifulSoup(h, "html.parser")
    rozet = [_kb_text(b) for b in s.select(".kb-brand-badges .kb-badge")]
    sec = s.select_one("#neden-boykot")
    return {"rozet_durum": re.sub(r"[^\w ]", "", rozet[0]).strip() if rozet else "",     # 🚫 🌍 🇹🇷
            "gerekce": re.sub(r"^Boykot Bildirisi\s*", "", _kb_text(sec.select_one(".announcement-box"))) if sec else ""}


def _kb_api_gerekce(ad, kim):
    """Sayfası açılmayan markanın gerekçesi yalnız arama API'sinde."""
    try:
        satirlar = al(f"{KB}api/app/Search.php", params={"name": ad, "type": 1}).json()
    except ValueError:
        return None
    return next((x.get("announcement") for x in satirlar if x.get("type") == 1 and x.get("id") == kim), None)


def normalle_kb(markalar):
    """Anahtar sitenin kayıt numarası: adres değişse de kayıt aynı kalır, ad değişikliği geri çekme sayılmaz (2026-11-03:
    Loreal → L'Oréal, Nestle → Nestlé...). Kapsam: sayfası açılan ve rozeti "Boykot" olan markalar; seviye kategorisinde
    durup rozeti Yabancı ya da Yerli olan (Capri-Sun, Flormar) ve sayfası açılmayan (iPhone, Whopper) kapsam dışı."""
    return {str(r["id"]): kayit(r["ad"], r.get("seviye") or "Seviyesiz", r.get("rozet_durum") == "Boykot", None,
                                r.get("gerekce"), (), r.get("url"), durum=r.get("rozet_durum"))
            for r in markalar}


def cek_kb(onceki):
    kartlar = {}
    for cid, slug in KB_KATEGORI.items():
        s = 1
        while True:
            h = sayfa_metni(f"{KB}{slug}-c-{cid}?s={s}")
            k = _kb_kartlar(h)
            if not k:
                break
            kartlar.setdefault(cid, []).extend(k)
            s += 1
            time.sleep(0.3)
    if not kartlar.get(843):
        raise KaynakHatasi("Kolay Boykot: Filistin İçin listesi okunamadı")
    seviye = {ms: etiket for cid, ks in kartlar.items() if cid != 843 for ms, etiket, _, _ in ks}
    # Aynı adreste iki kayıt olabilir (26.10.2026 toplu eklemesi: "Capri Sun" 8361, "Capri-Sun" 1389): küçük numaralı eski kayıt
    fil = {}
    for ms, _, ad, kim in sorted(kartlar[843], key=lambda x: -x[3]):
        fil[ms] = (kim, ad)
    # numarası değişip adresi aynı kalan kayıt önceki anahtarını korur
    eski = {v.get("url"): k for k, v in (onceki.get("kayitlar") or {}).items()}

    def getir(ms):
        kim, ad = fil[ms]
        url = f"{KB}marka/{ms}"
        r = al(url)
        d = kb_marka(r.text.replace("\r\n", "\n").replace("\r", "\n")) if r.status_code == 200 else {}
        if not d.get("rozet_durum"):
            d["gerekce"] = _kb_api_gerekce(ad, kim)
        return dict(id=eski.get(url, kim), slug=ms, ad=ad, seviye=seviye.get(ms, ""), url=url, **d)

    with ThreadPoolExecutor(3) as ex:
        markalar = list(ex.map(getir, fil))
    yeni = normalle_kb(markalar)
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)),
            "meta": {"marka": len(yeni)}}


# ===================================================================== Eczanede Boykot
EB = "https://eczanedeboykot.com"
EB_TOHUM = ["bayer", "pfizer", "teva", "novartis", "msd", "organon", "merck", "johnson"]


def _eb_text(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _eb_kart(li, body):
    k = {"durum": "boykot" if "is-boycott" in li else ("boykot değil" if "is-clear" in li else li)}
    m = re.search(r"<strong>(.*?)</strong>", body, re.S)
    k["ad"] = _eb_text(m.group(1)) if m else ""
    m = re.search(r'<strong><a href="([^"]+)"', body)
    k["link"] = H.unescape(m.group(1)) if m else ""
    m = re.search(r'<a class="manufacturer-link" href="([^"]+)"[^>]*>(.*?)</a>', body, re.S)
    k["firma"] = _eb_text(m.group(2)) if m else ""
    k["firma_link"] = H.unescape(m.group(1)) if m else ""
    if not m:
        m = re.search(r"<small>(.*?)</small>", body, re.S)
        k["firma"] = _eb_text(m.group(1)) if m else ""
    m = re.search(r'data-boycott-manufacturer="([^"]*)"', body)
    k["boykot_firmasi"] = H.unescape(m.group(1)) if m else ""
    return k


def _eb_kartlar(t, ana=False):
    """Sonuç bölümündeki ilaç kartları. ana=True: yalnız her grubun ana listesi (yerel tarayıcıdaki firma sayfası okuması
    gibi; eşdeğer ve ATC bölümleri hariç)."""
    s = t[t.find('<section class="site-shell search-results"'):]
    if '<aside class="medical-warning"' in s:
        s = s[:s.find('<aside class="medical-warning"')]
    if ana:
        s = "".join(re.split(r'<header class="equivalent-group-heading">\s*<div>\s*<h4>', a)[0]
                    for a in re.findall(r'<article class="equivalent-group">(.*?)</article>', s, re.S))
    return [_eb_kart(a, b) for a, b in re.findall(r'<li class="drug-status-card([^"]*)">(.*?)</li>', s, re.S)]


def _eb_ana(t):
    firmalar = []
    for attrs, body in re.findall(r"<button([^>]*data-company-evidence[^>]*)>(.*?)</button>", t, re.S):
        a = dict((k, H.unescape(v)) for k, v in re.findall(r'(data-company-[a-z-]+)="([^"]*)"', attrs))
        m = re.search(r"data-company-full-reason[^>]*>(.*?)</", body, re.S)
        firmalar.append({"firma": a.get("data-company-name", ""),
                         "gerekce": H.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""})
    m = re.search(r'<time datetime="([^"]+)"', t)
    return firmalar, (m.group(1) if m else "")


def normalle_eb(firmalar, urunler, liste_tarihi):
    out = {f"firma:{f['firma']}": kayit(f["firma"], "Boykot firması", True, None, f.get("gerekce"), (), EB + "/tr")
           for f in firmalar}
    for u in urunler:
        out[u["link"]] = kayit(u["ad"], "Boykot", True, u.get("firma"), None, (), EB + u["link"])
    out["_liste"] = kayit("Sitedeki liste güncelleme tarihi", None, True, url=EB + "/tr", tarih=liste_tarihi)
    return out


def cek_eb(onceki):
    def sayfa(url):
        t = sayfa_metni(url)
        time.sleep(1)
        return t

    ana = sayfa(EB + "/tr")
    firmalar, tarih = _eb_ana(ana)
    if not firmalar:
        raise KaynakHatasi("Eczanede Boykot: ana sayfada boykot firması okunamadı")
    ureticiler = {}
    for q in EB_TOHUM + [f["firma"].lower() for f in firmalar]:
        for k in _eb_kartlar(sayfa(EB + "/tr?q=" + urllib.parse.quote(q))):
            if k["boykot_firmasi"]:
                link = k["firma_link"] if k["firma"] == k["boykot_firmasi"] and k["firma_link"] else ""
                if link or k["boykot_firmasi"] not in ureticiler:
                    ureticiler[k["boykot_firmasi"]] = EB + link if link else (
                        EB + "/tr?company=" + urllib.parse.quote(k["boykot_firmasi"], safe=""))
    urunler = {}
    for ad, url in sorted(ureticiler.items()):
        t = sayfa(url)
        if not tarih:                      # liste güncelleme tarihi arama/firma sayfalarının başlığında
            m = re.search(r'<time datetime="([^"]+)"', t)
            tarih = m.group(1) if m else ""
        for k in _eb_kartlar(t, ana=True):
            if k["durum"] == "boykot" and k["link"]:
                urunler[k["link"]] = k
    if len(urunler) < 100:
        raise KaynakHatasi(f"Eczanede Boykot: yalnız {len(urunler)} boykot ürünü okundu")
    yeni = normalle_eb(firmalar, urunler.values(), tarih)
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)),
            "meta": {"uretici": sorted(ureticiler), "urun": len(urunler)}}


# ===================================================================== Who Profits
WP = "https://www.whoprofits.org/companies?page={}"
IBRANICE = re.compile(r"[\u0590-\u05ff\u0600-\u06ff]")


def _wp_ad(t):
    t = H.unescape(re.sub(r"<[^>]+>", " ", t))
    m = IBRANICE.search(t)
    return re.sub(r"\s+", " ", t[:m.start()] if m else t).strip(" (")


def cek_wp(onceki):
    """Şirket dizini (site haritası eski: silinmiş sayfalar var, bazı şirketler yok). Son sayfadan sonra dizin başa döner."""
    eski = onceki.get("kayitlar") or {}
    gor = {}
    for p in range(1, 80):
        L = re.findall(r'<a[^>]*href="https://www\.whoprofits\.org/companies/company/(\d+)\?[^"]*"[^>]*>(.*?)</a>',
                       al(WP.format(p)).text, re.S)
        if not [i for i, _ in L if i not in gor]:
            break
        for i, ad in L:
            gor.setdefault(i, _wp_ad(ad))
        time.sleep(1)
    if len(gor) < 0.8 * max(len(eski), 300):
        raise KaynakHatasi(f"Who Profits: dizinde yalnız {len(gor)} şirket okundu")
    yeni = {i: eski.get(i) or kayit(gor[i], None, True, None, None, (), f"https://www.whoprofits.org/companies/company/{i}")
            for i in sorted(gor, key=int)}
    return {"kayitlar": yeni, "parmak_izi": sha(",".join(sorted(gor))), "meta": {"sirket": len(gor)}}


# ===================================================================== AFSC Gazze
AFSC = "https://afsc.org/gaza-genocide-companies"


def normalle_afsc(t):
    s = BeautifulSoup(t, "html.parser")
    out = {}
    for it in s.select("div.item[data-uri]"):
        ad = it.select_one("h3.big-title")
        bilgi = {}
        for d in it.select(".details-holder .details"):
            k, v = d.select_one(".detail-label"), d.select_one(".small-title")
            if k and v:
                bilgi[k.get_text(strip=True).rstrip(":")] = v.get_text(" ", strip=True)
        rt = it.select_one(".offcanvas-item-content .block-richtext")
        metin = re.sub(r"[ \t\xa0]+", " ", rt.get_text("\n")).strip() if rt else ""
        metin = re.sub(r"\s*\n\s*", "\n", metin)
        linkler = [a["href"] for a in rt.select("a[href]")] if rt else []
        uri = it["data-uri"]
        out[uri] = kayit(ad.get_text(" ", strip=True) if ad else uri, None, True, None, metin, linkler,
                         "https://afsc.org" + uri, tur=bilgi.get("Type"), ulke=bilgi.get("Location"),
                         kategori=bilgi.get("Category"))
    return out


def cek_afsc(onceki):
    yeni = normalle_afsc(sayfa_metni(AFSC))
    if len(yeni) < 20:
        raise KaynakHatasi(f"AFSC: sayfada yalnız {len(yeni)} şirket okundu")
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)),
            "meta": {"sirket": len(yeni)}}


# ===================================================================== DBIO
DBIO = "https://dontbuyintooccupation.org/dbio-data-2025/"


def dosya_kaydi(ad, icerik, url):
    return kayit(ad, None, True, None, None, (), url, sha256=sha(icerik), boyut=len(icerik))


def dosyalar(onceki, sayfa, bul, ad):
    """Veri dosyası kaynakları (DBIO, Investigate): dosya bağlantıları sayfadan okunur. Sayfa bot korumasına takılırsa
    önceki kontroldeki dosyalar doğrudan indirilir; sayfaya yeni dosya eklendiyse sayfa açıldığı ilk gün görülür."""
    uyari = []
    try:
        urls = bul(al(sayfa).text)
        if not urls:
            raise KaynakHatasi(f"{ad}: sayfada veri dosyası bağlantısı bulunamadı")
    except EngelHatasi:
        urls = [r["url"] for r in (onceki.get("kayitlar") or {}).values() if r.get("url")]
        if not urls:
            raise
        uyari.append("veri sayfası sitenin bot korumasına takıldı; bilinen veri dosyaları doğrudan kontrol edildi")
    yeni = {}
    for u in urls:
        n = u.rsplit("/", 1)[-1]
        yeni[n] = dosya_kaydi(n, al(u).content, u)
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True)), "meta": {"dosya": len(yeni)},
            "uyarilar": uyari}


def cek_dbio(onceki):
    return dosyalar(onceki, DBIO, lambda t: tekil(re.findall(r'sourceFile\s*=\s*"([^"]+\.csv)"', t)), "DBIO")


# ===================================================================== AFSC Investigate
INV = "https://investigate.info/downloads"


def cek_inv(onceki):
    return dosyalar(onceki, INV, lambda t: tekil(re.findall(r'href="(https?://[^"]+\.(?:xlsx|csv|zip))"', t)), "Investigate")


# ===================================================================== Abbott & Keefer
AK_SM = "https://directory.abbottandkeefer.com/sitemap.xml"


def cek_ak(onceki):
    xml = al(AK_SM).text
    urls = sorted(set(re.findall(r"<loc>(https://directory\.abbottandkeefer\.com/brand-entry/[^<]+)</loc>", xml)))
    eski = onceki.get("kayitlar") or {}
    if len(urls) < 0.8 * max(len(eski), 500):
        raise KaynakHatasi(f"Abbott & Keefer: site haritasında yalnız {len(urls)} marka")
    yeni, n = {}, 0
    for u in urls:
        slug = u.rsplit("/", 1)[-1]
        if slug in eski:
            yeni[slug] = eski[slug]
            continue
        ad = slug.replace("-", " ")
        if n < 60:                         # yeni sayfaların adı sayfa başlığından (toplu değişimde ilk 60)
            n += 1
            m = re.search(r"<title>(.*?)</title>", al(u).text, re.S)
            ad = re.sub(r"\s*[|–-]\s*Abbott.*$", "", H.unescape(m.group(1)).strip()) if m else ad
            time.sleep(1)
        yeni[slug] = kayit(ad, None, True, None, None, (), u)
    return {"kayitlar": yeni, "parmak_izi": sha(",".join(urls)), "meta": {"marka": len(urls)}}


# ===================================================================== Boykot.co
# Sunucu tarafında üretilen PHP. Kategori sayfaları (/c/<ad>-<id>) yalnız boykottaki markaları listeler; "Boykot değil"
# markalar yalnız marka sayfalarının "Diğer … markaları" kartlarında (göreli /d/ bağlantıları) geçer. Kanıt bağlantısı
# /r/<id> sayfasının "refresh: 0; url=…" başlığındadır. Bazı marka sayfaları sürekli 500 verir: bunlar kategori satırı ya
# da yan kart bilgisiyle (ad, durum, kısa metin) kaydedilir. Ayrıştırma, yerel dışa aktarımı üreten
# listeler/Boykot.co/kod/build.py ile aynıdır (ilk anlık görüntü o dosyadan kuruldu).
BCO = "https://www.boykot.co"
BCO_KATEGORI = {1: "Otomotiv", 2: "Giyim - Tekstil", 3: "Kahve", 4: "İşletme", 5: "Kozmetik", 6: "İçecek", 7: "Enerji",
                8: "Medya / Eğlence", 9: "Moda", 10: "Finans", 11: "Gıda", 12: "Sağlık", 13: "Temizlik", 14: "Sigorta",
                15: "Lüks", 16: "Üretici Firma", 17: "İlaç", 18: "Siyaset", 19: "Süpermarket", 20: "Teknoloji",
                21: "Silah", 25: "Kişisel Bakım", 26: "Konaklama", 27: "Oyuncak", 28: "Hurma", 29: "Kırtasiye"}
_BCO_SATIR = re.compile(r'<h6 class="mb-0 ms-lg-3 mt-2 mt-lg-0">\s*<a href="https://www\.boykot\.co/d/([^"]+)">([^<]*)</a>')
_BCO_LINK = re.compile(r'href="(?:https://www\.boykot\.co)?/d/([^"\s]+)"')
_BCO_KART = re.compile(r'<a href="/d/([^"]+)" class="text-dark[^"]*">([^<]*)</a></h5>\s*<span>(.*?)</span>\s*'
                       r'<span class="badge ([^"]+)"', re.S)


def _bco_metin(fragment):
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", fragment, flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n• ", s, flags=re.I)
    s = re.sub(r"</(p|h[1-6]|li|ul|ol|div|tr)>|<(p|h[1-6]|ul|ol|div|tr)[^>]*>", "\n", s, flags=re.I)
    s = H.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return re.sub(r"\n{2,}", "\n\n", s).strip()


def bco_marka(html, slug):
    """Marka sayfası → kayıt sözlüğü (build.py'nin marka() işleviyle aynı alanlar); başlık yoksa None."""
    h1 = re.search(r'<h1 class="(text-[a-z]+)">(.*?)</h1>', html, re.S)
    if not h1:
        return None
    renk, ic = h1.groups()
    ad = H.unescape(re.split(r"<i ", ic)[0]).strip()
    son = re.search(r"Boykot ediliyor mu\?\s*<strong>(.*?)</strong>", html, re.S)
    cumle = _bco_metin(son.group(1)) if son else ""
    if "boykot ediliyor!" in cumle.lower() or renk == "text-danger":
        durum = "Boykot"
    elif "boykot edilmiyor" in cumle.lower() or renk == "text-success":
        durum = "Boykot değil"
    else:
        durum = cumle or renk
    sonra = html[h1.end():]
    tanim = re.match(r"\s*<p>(.*?)</p>", sonra, re.S)
    kat = re.findall(r'<a href="(https://www\.boykot\.co/c/[^"]+)" class="btn btn-primary ml-0">([^<]+)</a>', sonra[:3000])
    bas, bit = sonra.find("<hr>"), sonra.find("Boykot ediliyor mu?")
    gerekce = _bco_metin(sonra[bas + 4:bit]) if bas >= 0 and bit > bas else ""
    gerekce = re.sub(r"\n*<hr>\s*$", "", gerekce)
    rid = re.search(r'href="https://www\.boykot\.co/r/(\d+)"', html)
    return {"slug": slug, "ad": ad, "durum": durum, "tanim": _bco_metin(tanim.group(1)) if tanim else "",
            "kategoriler": [H.unescape(k[1]).strip() for k in kat], "gerekce": gerekce,
            "kanit_id": rid.group(1) if rid else "", "kanit": "", "url": f"{BCO}/d/{slug}", "not": ""}


def bco_kartlar(html):
    """Sayfadaki "Diğer … markaları" kartları: {slug: (ad, kısa metin, durum, kategori)}."""
    out = {}
    for bolum in re.split(r"<h5>Diğer ", html)[1:]:
        kat = bolum.split(" Markaları</h5>")[0]
        for slug, ad, ozet, rozet in _BCO_KART.findall(bolum):
            d = "Boykot" if "danger" in rozet else "Boykot değil" if "success" in rozet else rozet
            out.setdefault(slug, (H.unescape(ad).strip(), _bco_metin(ozet), d, kat))
    return out


def normalle_bco(markalar):
    """Hem yerel dışa aktarım (boykotco_<tarih>.json "markalar") hem canlı çekim aynı alanları kullanır.
    Kapsam: sitede "Boykot" durumundakiler (veritabanı "Boykot değil" markaları almaz)."""
    return {r["slug"]: kayit(r["ad"], r["durum"], r["durum"] == "Boykot", None, r.get("gerekce") or r.get("tanim"),
                             [r["kanit"]] if (r.get("kanit") or "").startswith("http") else [], r.get("url"),
                             kategori=", ".join(r.get("kategoriler") or []), kanit_id=r.get("kanit_id"),
                             sayfa="açılmıyor" if r.get("not") else None)
            for r in markalar}


def cek_bco(onceki, isci=3):
    eski = onceki.get("kayitlar") or {}
    home = sayfa_metni(BCO + "/")
    linked = {int(i): f"/c/{s}-{i}" for s, i in re.findall(r'href="https://www\.boykot\.co/c/([a-z0-9-]+)-(\d+)"', home)}
    kat_satir = {}                                   # slug → (ad, kategori) kategori sayfalarından (hepsi "Boykot")
    for i, ad in BCO_KATEGORI.items():
        yol = linked.get(i) or f"/c/{_slug_tr(ad)}-{i}"
        r = al(BCO + yol)
        if r.status_code != 200:
            continue
        for s, n in _BCO_SATIR.findall(r.text):
            kat_satir.setdefault(s, (H.unescape(n).strip(), ad))
        time.sleep(0.3)
    eski_boykot = sum(1 for v in eski.values() if v.get("hukum") == "Boykot")
    if len(kat_satir) < 0.8 * max(eski_boykot, 500):
        raise KaynakHatasi(f"Boykot.co: kategori sayfalarında yalnız {len(kat_satir)} marka (önceki {eski_boykot})")
    sayfalar, kartlar, bozuk, yok, alinamayan = {}, {}, set(), set(), set()
    kilit = threading.Lock()

    def getir(s):
        for i in range(4):
            try:
                r = oturum().get(f"{BCO}/d/{s}", timeout=60)
                if r.status_code == 200:
                    h = r.text.replace("\r\n", "\n").replace("\r", "\n")
                    with kilit:
                        sayfalar[s] = h
                    time.sleep(0.3 + random.random() * 0.4)
                    return
                if r.status_code == 404 and i >= 1:             # sayfa kaldırılmış
                    with kilit:
                        yok.add(s)
                    return
                if r.status_code == 500 and i >= 1:             # sitede kalıcı bozuk sayfa (örn. /d/colorado hep 500)
                    with kilit:
                        bozuk.add(s)
                    return
            except requests.RequestException:
                pass
            time.sleep(min(60, 5 * 2 ** i))
        with kilit:
            alinamayan.add(s)

    # önceki anlık görüntüdeki markalar da her seferinde doğrudan okunur: "Boykot değil" markalar yalnız rastgele seçilen yan
    # kartlarda geçtiği için, yalnız kartlardan gidilirse her tarama farklı bir alt kümeyi bulur
    kuyruk, gorulen = list(kat_satir) + [s for s in eski if s not in kat_satir], set()
    while kuyruk:                                     # dalga dalga: yeni sayfalardaki kart bağlantıları sonraki dalga
        dalga = [s for s in dict.fromkeys(kuyruk) if s not in gorulen]
        gorulen.update(dalga)
        with ThreadPoolExecutor(isci) as ex:
            list(ex.map(getir, dalga))
        kuyruk = []
        for s in dalga:
            h = sayfalar.get(s)
            if h:
                kartlar.update({k: v for k, v in bco_kartlar(h).items() if k not in kartlar})
                kuyruk += [x for x in _BCO_LINK.findall(h) if x not in gorulen]
    if len(alinamayan) > 0.05 * max(len(gorulen), 1):
        raise KaynakHatasi(f"Boykot.co: {len(alinamayan)}/{len(gorulen)} marka sayfası alınamadı")
    markalar = []
    for s in sorted(gorulen):
        if s in sayfalar:
            r = bco_marka(sayfalar[s], s)
            if r:
                markalar.append(r)
                continue
        k = kat_satir.get(s)
        c = kartlar.get(s)
        if not (k or c):
            if s in eski and s not in yok:           # okunamadı, hiçbir kartta da yok: önceki kaydı korunur (aşağıda)
                alinamayan.add(s)
            continue
        ad, ozet, durum, kat = (k[0], (c[1] if c else ""), "Boykot", k[1]) if k else c
        markalar.append({"slug": s, "ad": ad, "durum": durum, "tanim": ozet, "kategoriler": [kat] if kat else [],
                         "gerekce": "", "kanit_id": "", "kanit": "", "url": f"{BCO}/d/{s}",
                         "not": "Marka sayfası açılmıyor (sunucu hatası 500)"})

    def kanit(m):                                     # kanıt adresi: kimlik değişmediyse önceki anlık görüntüden
        if not m["kanit_id"]:
            return
        e = eski.get(m["slug"]) or {}
        if (e.get("ek") or {}).get("kanit_id") == m["kanit_id"] and e.get("kaynaklar"):
            m["kanit"] = e["kaynaklar"][0]
            return
        try:
            r = oturum().get(f"{BCO}/r/{m['kanit_id']}", timeout=60, allow_redirects=False,
                             headers={"Referer": m["url"]})
            u = re.match(r"\s*\d+\s*;\s*url=(.*)$", r.headers.get("refresh") or "", re.I)
            m["kanit"] = u.group(1).strip() if u else ""
            time.sleep(0.3)
        except requests.RequestException:
            m["kanit"] = (e.get("kaynaklar") or [""])[0]

    with ThreadPoolExecutor(isci) as ex:
        list(ex.map(kanit, markalar))
    yeni = normalle_bco(markalar)
    uyari = []
    if alinamayan:                                    # alınamayan sayfaların önceki kaydı korunur (kalkmış sayılmaz)
        for s in alinamayan:
            if s in eski:
                yeni[s] = eski[s]
        uyari.append(f"{len(alinamayan)} marka sayfası alınamadı; önceki kayıtları korundu")
    for s in bozuk:                                   # sayfası bozuk ama önceki kaydı tam olan marka: önceki metin korunur
        if s in yeni and s in eski and not (eski[s].get("ek") or {}).get("sayfa"):
            yeni[s] = eski[s]
    if bozuk:
        uyari.append(f"{len(bozuk)} marka sayfası sitede açılmıyor (500); kategori satırı ya da yan kart bilgisiyle alındı")
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)),
            "meta": {"marka": len(yeni), "boykot": sum(1 for v in yeni.values() if v.get("hukum") == "Boykot")},
            "uyarilar": uyari}


def _slug_tr(s):
    s = s.replace("ı", "i").replace("İ", "I").replace("/", " ")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# ===================================================================== Boycott Israel
# Tek statik sayfa. Okuma, yerel dışa aktarımı üreten Boycott Israel/kod/build.py ile aynı.
BI = "https://boycott-israel.org/boycott.html"
BI_SEVIYE = {"very high": "Çok yüksek", "high": "Yüksek", "medium": "Orta", "low": "Düşük"}


def _h_duz(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def bi_ayristir(h):
    bolumler = [(m.start(), _h_duz(m.group(1))) for m in re.finditer(r'<h3[^>]*class="[^"]*boycott-category[^"]*"[^>]*>(.*?)</h3>', h, re.S)] or \
               [(m.start(), _h_duz(m.group(1))) for m in re.finditer(r"<h3[^>]*>(.*?)</h3>", h, re.S)]
    parcalar = list(re.finditer(r'<div class="md:flex items-center" id="([^"]*)">', h))
    out = []
    for i, m in enumerate(parcalar):
        blok = h[m.end():parcalar[i + 1].start() if i + 1 < len(parcalar) else h.find("<h2", m.end())]
        blok = blok[:blok.find("</li>")] if "</li>" in blok else blok
        ad = re.search(r"<h4>(.*?)<span class=\"label ([^\"]+)\">", blok, re.S)
        if not ad:
            continue
        icerik = blok[blok.find("</h4>"):]
        alt = re.search(r'<div class="subbrands">(.*?</div>)\s*</div>', icerik, re.S)
        k = dict(id=m.group(1), ad=_h_duz(ad.group(1)), seviye=ad.group(2), bolum=[n for p, n in bolumler if p < m.start()][-1],
                 metin=" ".join(_h_duz(x) for x in re.findall(r"<p(?![^>]*class=)[^>]*>(.*?)</p>", icerik, re.S)),
                 alt_markalar=[_h_duz(x) for x in re.findall(r"<div>(.*?)</div>", alt.group(1), re.S)] if alt else [],
                 ulke=" ".join(_h_duz(x) for x in re.findall(r'<p class="country">(.*?)</p>', icerik, re.S)),
                 alternatif=" ".join(_h_duz(x) for x in re.findall(r'<p class="alternative">(.*?)</p>', icerik, re.S)),
                 linkler=[dict(ad=_h_duz(a), url=H.unescape(u)) for u, a in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', icerik, re.S)])
        if k["ad"] == "Imperva" and not k["ulke"]:      # kaynak hatası: Imperva'da ülke, alternatif etiketiyle yazılmış
            k["ulke"], k["alternatif"] = k["alternatif"], ""
        out.append(k)
    return out


def normalle_bi(sirketler):
    out = {}
    for k in sirketler:
        sv, url = BI_SEVIYE.get(k["seviye"], k["seviye"]), f"{BI}#{k['id']}"
        out[k["id"]] = kayit(k["ad"], sv, True, None, k["metin"], [x["url"] for x in k["linkler"]], url, bolum=k["bolum"],
                             ulke=k["ulke"], alternatif=k["alternatif"])
        for a in k["alt_markalar"]:
            out[f"{k['id']}:{a}"] = kayit(a, sv, True, k["ad"], None, (), url)
    return out


def cek_bi(onceki):
    yeni = normalle_bi(bi_ayristir(sayfa_metni(BI)))
    if len(yeni) < 0.8 * max(len(onceki.get("kayitlar") or {}), 100):
        raise KaynakHatasi(f"Boycott Israel: sayfada yalnız {len(yeni)} kayıt okundu")
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)), "meta": {"kayit": len(yeni)}}


# ===================================================================== BoykotListe
# Sitenin kendi "Veriyi İndir" dosyası: /api/export (tek JSON). robots.txt /api/ yolunu botlara kapatıyor; kullanıcı kararıyla
# (2026-11-03: "BoykotListe verisini de oku") bu dosya günde bir kez okunur. Marka sayfaları veriyi tarayıcıda yüklediği için
# başka yol yok. Dosyada kimlik yok: anahtar ad + kategori; aynı ad ve kategoride iki satır varsa metne göre sıralanıp numaralanır
# (Bounty, Magnum, Fa, NYX, Protex, Veet, Lucky Strike). exported_at her istekte değişir, karşılaştırmaya girmez.
BL = "https://boykotliste.com/api/export"
BL_RISK = {"high": "Yüksek", "medium": "Orta", "low": "Düşük"}


def normalle_bl(brands):
    gr = {}
    for b in brands:
        gr.setdefault(f"{b['name']}|{b['category']['tr']}", []).append(b)
    out = {}
    for k0, L in gr.items():
        for n, b in enumerate(sorted(L, key=lambda b: b["reasons"]["tr"]), 1):
            out[k0 if n == 1 else f"{k0}|{n}"] = kayit(
                b["name"], BL_RISK.get(b["risk_level"], b["risk_level"]), True, None, b["reasons"]["tr"], [b.get("source_url")],
                "https://boykotliste.com/?search=" + re.sub(r"\s+", "+", b["name"]), kategori=b["category"]["tr"],
                alternatifler=b["alternatives"]["tr"])
    return out


def cek_bl(onceki):
    d = json.loads(metin_coz(al(BL)))
    yeni = normalle_bl(d["brands"])
    if len(yeni) < 0.8 * max(len(onceki.get("kayitlar") or {}), 300):
        raise KaynakHatasi(f"BoykotListe: dosyada yalnız {len(yeni)} satır okundu")
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)), "meta": {"satir": len(yeni)}}


# ===================================================================== Genç Müslümanlar
# Tek WordPress sayfası (bölüm başlıkları ve açılır kutular). Okuma Genç Müslümanlar/kod/build.py ile aynı. Aynı başlık iki
# bölümde geçebilir (Chanel, Sudocrem): tek kayıt.
GM = "https://gencmuslumanlar.com/boykot-listesi/"


def gm_ayristir(h):
    basliklar = [(m.start(), H.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()) for m in re.finditer(r"<h3[^>]*>(.*?)</h3>", h, re.S)]
    ham = []
    for m in re.finditer(r'<div class="su-spoiler-title"[^>]*><span class="su-spoiler-icon"></span>(.*?)</div><div class="su-spoiler-content[^>]*>(.*?)</div></div>', h, re.S):
        ham.append(dict(bolum=[n for p, n in basliklar if p < m.start()][-1], ad=H.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip(),
                        metin=H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2)))).strip(),
                        linkler=re.findall(r'href="([^"]+)"', m.group(2))))
    return ham


def normalle_gm(ham, tarih=None):
    gr = {}
    for r in ham:
        g = gr.setdefault(r["ad"], dict(metin=[], linkler=[], bolum=[]))
        for a, v in (("metin", [r["metin"]]), ("bolum", [r["bolum"]]), ("linkler", r["linkler"])):
            g[a] += [x for x in v if x not in g[a]]
    return {a: kayit(a, "Boykot", True, None, " | ".join(g["metin"]), g["linkler"], GM, tarih=(tarih or "")[:10], bolum=" + ".join(g["bolum"]))
            for a, g in gr.items()}


def cek_gm(onceki):
    h = sayfa_metni(GM)
    ham = gm_ayristir(h)
    if len(ham) < 0.8 * max(len(onceki.get("kayitlar") or {}), 60):
        if "imunify" in h.lower():         # sunucunun bot doğrulama sayfası
            raise EngelHatasi(f"{GM}: sitenin bot koruması")
        raise KaynakHatasi(f"Genç Müslümanlar: sayfada yalnız {len(ham)} başlık okundu")
    m = re.search(r'article:modified_time" content="([^"]+)"', h)
    yeni = normalle_gm(ham, m.group(1) if m else None)
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)), "meta": {"baslik": len(ham)}}


# ===================================================================== Boykot Market
# brands-search.json bütün markaları verir ama metni 199 karakterde keser ve tarih içermez; tam veri her markanın statik
# sayfasındaki brand-data JSON'unda. Okuma, yerel dışa aktarımı üreten Boykot Market/kod/build.py ile aynı.
BMK = "https://www.boykotmarket.com"
_BMK_DATA = re.compile(r'<script id="brand-data"[^>]*>(.*?)</script>', re.S)
_KONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _bmk_duz(h):
    h = re.sub(r"</(h\d|p|li|ol|ul)>|<br\s*/?>", "\n", h or "")
    t = H.unescape(re.sub(r"<[^>]+>", "", h))
    return _KONTROL.sub("", re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t))).strip()


def bmk_marka(slug, b):
    return dict(ad=b["name"], slug=slug, url=f"{BMK}/tr/brand/{slug}/", kategori=b.get("category"), liste=b.get("boycottList"),
                sahip=b.get("owner") or "", alternatifler=b.get("alternatives") or "", kaynak=b.get("source") or "",
                guncelleme=(b.get("updatedAt") or "")[:10], gerekce_tr=_bmk_duz(b.get("description_tr")),
                metin_linkleri=tekil(re.findall(r'href="(https?://[^"]+)"', b.get("description_tr") or "")))


def normalle_bmk(markalar):
    return {m["slug"]: kayit(m["ad"], m["liste"], True, m["sahip"], m["gerekce_tr"], [m["kaynak"]] + m["metin_linkleri"], m["url"],
                             tarih=m["guncelleme"], kategori=m["kategori"], alternatifler=m["alternatifler"]) for m in markalar}


def cek_bmk(onceki, isci=4):
    slugs = [b["slug"] for b in al(BMK + "/brands-search.json").json()["brands"]]
    eski = onceki.get("kayitlar") or {}
    if len(slugs) < 0.8 * max(len(eski), 3000):
        raise KaynakHatasi(f"Boykot Market: arama dosyasında yalnız {len(slugs)} marka (önceki {len(eski)})")
    recs, alinamayan = [], []
    kilit = threading.Lock()

    def getir(s):
        url = f"{BMK}/tr/brand/{urllib.parse.quote(s)}/"
        for i in range(4):
            try:
                r = oturum().get(url, timeout=60)
                if r.status_code == 404:
                    return
                m = _BMK_DATA.search(metin_coz(r)) if r.status_code == 200 else None
                if m:
                    rec = bmk_marka(s, json.loads(m.group(1))["brand"])
                    with kilit:
                        recs.append(rec)
                    time.sleep(0.1)
                    return
            except (requests.RequestException, ValueError, KeyError):
                pass
            time.sleep(3 * (i + 1))
        with kilit:
            alinamayan.append(s)

    with ThreadPoolExecutor(isci) as ex:
        list(ex.map(getir, slugs))
    if len(alinamayan) > 0.05 * len(slugs):
        raise KaynakHatasi(f"Boykot Market: {len(alinamayan)}/{len(slugs)} marka sayfası okunamadı")
    yeni = normalle_bmk(recs)
    for s in alinamayan:                   # okunamayan sayfanın önceki kaydı korunur (kalkmış sayılmaz)
        if s in eski:
            yeni[s] = eski[s]
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)), "meta": {"marka": len(yeni)},
            "uyarilar": [f"{len(alinamayan)} marka sayfası okunamadı; önceki kayıtları korundu"] if alinamayan else []}


# ===================================================================== Yerli Reçete
# Bütün veri Next.js sayfa paketine gömülü (JSON.parse('{"_Y":[ilaçlar],"kI":[firma kategorileri]}')). Paket adı içerik
# değişince değişir: adı aynıysa indirilmez. Boykot listesi değildir; veritabanına yalnız aşağıdaki firmaların (Yerli Reçete/
# kod/yr_vt.py FIRMA) eksik ilaçları alındı, bu yüzden kapsam bu firmalardır.
YR = "https://yerlirecete.com"
YR_FIRMA = {"BAYER", "JOHNSON", "ACTELION", "MERCK", "MERCK_SHARP", "NOVARTIS", "ORGANON", "PFIZER", "TEVA", "NESTLE", "RECKITT_BENCKISER",
            "PROCTER_GAMBLE", "GLAXOSMITHKLINE", "ECZACIBASI", "ABDI_IBRAHIM", "ABBOTT", "LILLY", "PERRIGO", "NUMIL", "ROCHE", "ALCON", "SANDOZ",
            "VIATRIS", "MEDA"}


def normalle_yr(ilaclar, firmalar):
    kat = {f["slug"]: f["categ"] for f in firmalar}
    return {i["barcode"]: kayit(i["name"], None, i.get("cSlug") in YR_FIRMA, i.get("cName"), None, (), YR,
                                firma_kategori=kat.get(i.get("cSlug"), "K"), esdeger=i.get("equiv")) for i in ilaclar}


def cek_yr(onceki):
    m = re.search(r"/_next/static/chunks/app/page-[0-9a-f]+\.js", al(YR + "/").text)
    if not m:
        raise KaynakHatasi("Yerli Reçete: ana sayfada veri paketi bulunamadı")
    iz = m.group(0)
    if iz == onceki.get("parmak_izi"):
        return {"degismedi": True, "parmak_izi": iz}
    js = al(YR + iz).content.decode("utf-8")
    raw = js[js.index("JSON.parse('") + 12: js.index("}')") + 1]
    d = json.loads(re.sub(r"\\x([0-9a-f]{2})", lambda x: chr(int(x.group(1), 16)), raw).replace("\\'", "'"))
    return {"kayitlar": normalle_yr(d["_Y"], d["kI"]), "parmak_izi": iz, "meta": {"ilac": len(d["_Y"]), "firma": len(d["kI"])}}


# ===================================================================== Boycat
# Tam veritabanı şifreli uygulama uçlarında (kullanılmaz). Veritabanındaki 199 marka (Top Companies) research.boycat.io'daki
# şirket sayfalarından kontrol edilir: seviye ve gerekçe. Listeye yeni giren marka buradan görülmez; uygulamadaki kaynak alan
# adları sayfada yok.
BC_SEVIYE = {"tier-1": "Official BDS Priority Campaign", "tier-2": "Level 2: Connected Companies", "tier-3": "Level 3: Broad Connections"}


def bc_sirket(html):
    """Sayfanın Next.js verisindeki şirket kaydı (Boycat/kod/research_cek.py ile aynı okuma)."""
    t = "".join(json.loads('"' + p + '"') for p in re.findall(r'self.__next_f.push\(\[1,"(.*?)"\]\)</script>', html, flags=re.S))
    i = t.find('"company":{"slug"')
    if i < 0:
        return None
    return json.JSONDecoder().raw_decode(t[i + len('"company":'):])[0]


def normalle_bc(markalar):
    return {m["slug"]: kayit(m["ad"], m["seviye"], True, None, m.get("gerekce"), (), m["url"]) for m in markalar}


def cek_bc(onceki):
    eski = onceki.get("kayitlar") or {}
    if not eski:
        raise KaynakHatasi("Boycat: izlenecek marka listesi (önceki anlık görüntü) yok")
    yeni, okunamayan = {}, []
    for s, e in eski.items():
        url = f"https://research.boycat.io/company/{s}"
        try:
            r = al(url, deneme=3)
            if r.status_code == 404:
                continue                   # sayfa kalkmış
            c = bc_sirket(metin_coz(r))
        except (KaynakHatasi, ValueError) as x:
            if isinstance(x, EngelHatasi):
                raise
            c = None
        if not c:
            okunamayan.append(s)
            yeni[s] = e
        else:
            yeni[s] = kayit(e.get("ad"), BC_SEVIYE.get(c.get("verdict"), c.get("verdict")), True, None,
                            (c.get("blurb") or "").replace("​", "").strip(), (), url)
        time.sleep(0.5)
    if len(okunamayan) > 0.05 * len(eski):
        raise KaynakHatasi(f"Boycat: {len(okunamayan)}/{len(eski)} şirket sayfası okunamadı")
    return {"kayitlar": yeni, "parmak_izi": sha(json.dumps(yeni, sort_keys=True, ensure_ascii=False)), "meta": {"marka": len(yeni)},
            "uyarilar": [f"{len(okunamayan)} şirket sayfası okunamadı; önceki kayıtları korundu"] if okunamayan else []}


# ===================================================================== No Thanks
# Liste girişle korunan API'de ve Mac'teki uygulamanın klasöründeki nothanks.db'de; web'de marka sayfası yok, o klasöre buradan
# erişilmez. Yalnız App Store'daki sürüm izlenir. Bu zayıf bir işarettir: nothanks.db'nin sync_status tablosu ve kayıt tarihleri
# uygulamanın listeyi sunucudan eşitlediğini gösteriyor, yani liste yeni sürüm çıkmadan da değişebilir. Listeyi karşılaştırmak için
# kullanıcının uygulamadaki güncel nothanks.db'yi listeler/No Thanks/ altına yeniden kopyalaması gerekir.
NT_API = "https://itunes.apple.com/lookup?bundleId=com.bashsquare.nothanks"
NT_URL = "https://apps.apple.com/us/app/no-thanks-app/id6476206516"


def normalle_nt(surum, tarih=None):
    return {"uygulama": kayit("No Thanks uygulaması", None, True, None, None, (), NT_URL, tarih=(tarih or "")[:10], surum=surum)}


def cek_nt(onceki):
    r = al(NT_API).json().get("results") or []
    if not r:
        raise KaynakHatasi("No Thanks: App Store kaydı bulunamadı")
    return {"kayitlar": normalle_nt(r[0]["version"], r[0].get("currentVersionReleaseDate")), "parmak_izi": r[0]["version"], "meta": {}}


# ===================================================================== kayıt defteri
# siklik: "gunluk" kaynaklar her gün, "haftalik" olanlar yalnız tam taramada (pazartesi) kontrol edilir. "yerel" olanlar GitHub'dan
# okunamaz (bot koruması): GitHub'da çalışmaz, Mac'teki haftalık görevle (izleme/yerel_izle.sh) kontrol edilir.
# birim: raporda kayıtların adı.
KAYNAKLAR = {
    "bykt": dict(ad="bykt.org", site="https://bykt.org", cek=cek_bykt, siklik="gunluk", birim="marka",
                 kapsam="Kesin Boykot ve İnsafa Bağlı"),
    "bt": dict(ad="Bilinçli Tüketim", site="https://bilinclituketim.com", cek=cek_bt, siklik="gunluk", birim="marka",
               kapsam="çatısı 1–3 çarpılı ve sitede listelenen markalar"),
    "bd": dict(ad="Boykot Dedektifi", site="https://boykotdedektifi.com", cek=cek_bd, siklik="haftalik", birim="marka",
               kapsam="Boykot, İkincil Boykot ve Şüpheli"),
    "kb": dict(ad="Kolay Boykot (Filistin İçin)", site="https://www.kolayboykot.com/filistin-icin-c-843", cek=cek_kb,
               siklik="haftalik", birim="marka", kapsam="sayfası açılan ve rozeti “Boykot” olan markalar"),
    "bco": dict(ad="Boykot.co", site="https://www.boykot.co", cek=cek_bco, siklik="haftalik", birim="marka",
                kapsam="“Boykot” durumundaki markalar (“Boykot değil” markalar da izlenir)"),
    "eb": dict(ad="Eczanede Boykot", site="https://eczanedeboykot.com/tr", cek=cek_eb, siklik="gunluk", birim="ilaç",
               kapsam="boykot firmaları ve ürünleri"),
    "wp": dict(ad="Who Profits", site="https://www.whoprofits.org", cek=cek_wp, siklik="gunluk", birim="şirket",
               kapsam="şirket dizini (yalnız eklenen ve çıkan şirketler izlenir)"),
    "afsc": dict(ad="AFSC Gazze listesi", site=AFSC, cek=cek_afsc, siklik="gunluk", birim="şirket",
                 kapsam="listenin tamamı"),
    "dbio": dict(ad="DBIO", site=DBIO, cek=cek_dbio, siklik="gunluk", birim="veri dosyası",
                 kapsam="veri sayfasındaki CSV dosyaları"),
    "inv": dict(ad="AFSC Investigate", site="https://investigate.info", cek=cek_inv, siklik="gunluk",
                birim="veri dosyası", kapsam="indirme sayfasındaki veri seti"),
    "ak": dict(ad="Abbott & Keefer", site="https://directory.abbottandkeefer.com", cek=cek_ak, siklik="gunluk",
               birim="marka", kapsam="marka dizini (yalnız eklenen ve çıkan markalar izlenir)"),
    "bc": dict(ad="Boycat", site="https://research.boycat.io", cek=cek_bc, siklik="yerel", birim="marka",
               kapsam="veritabanındaki 199 marka (seviye ve gerekçe); listeye yeni giren marka görülmez"),
    "nt": dict(ad="No Thanks", site=NT_URL, cek=cek_nt, siklik="gunluk", birim="uygulama",
               kapsam="yalnız App Store sürümü; liste uygulamanın içinde, karşılaştırmak için güncel kopya gerekir"),
    "yr": dict(ad="Yerli Reçete", site=YR, cek=cek_yr, siklik="gunluk", birim="ilaç",
               kapsam="veritabanına ilaçları alınan 24 firma (Yerli Reçete boykot listesi değildir)"),
    "bmk": dict(ad="Boykot Market", site=BMK + "/tr/", cek=cek_bmk, siklik="haftalik", birim="marka", kapsam="listenin tamamı"),
    "bl": dict(ad="BoykotListe", site="https://boykotliste.com", cek=cek_bl, siklik="gunluk", birim="marka", kapsam="listenin tamamı"),
    "gm": dict(ad="Genç Müslümanlar", site=GM, cek=cek_gm, siklik="gunluk", birim="marka", kapsam="listenin tamamı"),
    "bi": dict(ad="Boycott Israel", site=BI, cek=cek_bi, siklik="gunluk", birim="şirket", kapsam="listenin tamamı"),
}
