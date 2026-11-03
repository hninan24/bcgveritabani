"""Kaynak listeleri kontrol eder, bir önceki anlık görüntüyle karşılaştırır ve Türkçe değişiklik raporu yazar.

Kullanım:
    python izleme/izle.py hizli          # günlük kaynaklar (bykt, BT, Eczanede Boykot, WP, AFSC, DBIO, Investigate, A&K)
    python izleme/izle.py tam            # hepsi (Boykot Dedektifi ve Kolay Boykot taraması dahil)
    python izleme/izle.py bykt,bd        # yalnız verilen kaynaklar

Dosyalar (izleme/ altında):
    veri/<kaynak>.json      kaynağın son anlık görüntüsü (normalleştirilmiş kayıtlar)
    durum.json              her kaynağın son kontrol zamanı, son değişikliği ve durumu
    raporlar/<tarih>.md     değişiklik bulunan her çalışmanın raporu
Ortam değişkenleri: BILDIRIM=<yol> verilirse kısa bildirim metni (GitHub Issue yorumu) oraya yazılır; GITHUB_OUTPUT
varsa degisiklik / ozet / rapor çıktıları eklenir. Bir kaynak kontrol edilemezse çıkış kodu 1 olur (diğerleri işlenir).
"""
import datetime as dt
import difflib
import json
import os
import re
import sys
import traceback
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kaynaklar import KAYNAKLAR, EngelHatasi  # noqa: E402
import olaylar  # noqa: E402

KOK = Path(__file__).resolve().parent
VERI, RAPOR, DURUM, OLAY = KOK / "veri", KOK / "raporlar", KOK / "durum.json", KOK / "olaylar.json"
SITE = KOK.parent / "index.html"
TSI = dt.timezone(dt.timedelta(hours=3))
ALANLAR = ("ad", "hukum", "kapsam", "cati", "metin", "kaynaklar", "url", "ek")
ETIKET = {"ad": "Ad", "hukum": "Hüküm", "cati": "Çatı", "metin": "Gerekçe metni", "kaynaklar": "Kaynak bağlantıları",
          "url": "Sayfa adresi", "ek": "Diğer alanlar"}
BILDIRIM_SINIR = 25          # bildirimde kaynak başına gösterilen en fazla madde
ENGEL_GUN = 7                # sitenin bot koruması bu kadar gün sürerse çalışma hatalı sayılır (daha kısası geçici sayılır)


def oku(p, vars=None):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except FileNotFoundError:
        return vars


def yaz(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True) + "\n", "utf-8")


# ------------------------------------------------------------------ veritabanıyla eşleştirme
def anahtar(s):
    s = unicodedata.normalize("NFKD", (s or "").replace("İ", "I").replace("ı", "i"))
    return re.sub(r"[^a-z0-9]+", "", s.encode("ascii", "ignore").decode().lower())


def veritabani():
    """Sitedeki (index.html) kuruluşlar: ad anahtarı → (görünen ad, çatı adı)."""
    try:
        t = SITE.read_text("utf-8")
        d = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', t, re.S).group(1))
    except Exception:  # noqa: BLE001
        return {}
    E = d["E"]
    cati = {}
    for i, e in enumerate(E):
        for j in e.get("ch") or []:
            cati[j] = e["n"]
    out = {}
    for i, e in enumerate(E):
        for n in [e["n"]] + list(e.get("a") or []):
            out.setdefault(anahtar(n), (e["n"], cati.get(i)))
    return out


# ------------------------------------------------------------------ fark
def fark(eski, yeni):
    out = []
    for i in sorted(yeni.keys() - eski.keys()):
        out.append(dict(tur="yeni", id=i, a=None, b=yeni[i], alanlar=[]))
    for i in sorted(eski.keys() - yeni.keys()):
        out.append(dict(tur="kalkan", id=i, a=eski[i], b=None, alanlar=[]))
    for i in sorted(eski.keys() & yeni.keys()):
        a, b = eski[i], yeni[i]
        al = [f for f in ALANLAR if a.get(f) != b.get(f)]
        if al:
            out.append(dict(tur="degisti", id=i, a=a, b=b, alanlar=al))
    return out


def etkili(d):
    return bool((d["a"] or {}).get("kapsam") or (d["b"] or {}).get("kapsam"))


def baslik(d):
    a, b = d["a"] or {}, d["b"] or {}
    if d["tur"] == "yeni":
        return "Yeni kayıt"
    if d["tur"] == "kalkan":
        return "Listeden kalktı"
    if a.get("kapsam") != b.get("kapsam"):
        return "Kapsama girdi" if b.get("kapsam") else "Kapsamdan çıktı"
    for f in ("hukum", "cati", "ad", "metin", "kaynaklar", "url", "ek"):
        if f in d["alanlar"]:
            return ETIKET[f] + " değişti"
    return "Değişti"


SIRA = ["Yeni kayıt", "Kapsama girdi", "Kapsamdan çıktı", "Listeden kalktı", "Hüküm değişti", "Çatı değişti",
        "Ad değişti", "Gerekçe metni değişti", "Kaynak bağlantıları değişti", "Sayfa adresi değişti",
        "Diğer alanlar değişti", "Değişti"]


def kac(s):
    """Markdown işaretlerini kaçırır (metin parçaları biçimi bozmasın)."""
    return re.sub(r"([\\`*_~\[\]<>|#])", r"\\\1", s or "")


def kirp(s, n):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def metin_farki(a, b):
    """Değişen bölümler bağlamıyla: ~~silinen~~ **eklenen**."""
    f = olaylar.metin_farki(a, b)
    if not f:
        return "Yalnız boşluk/biçim farkı."
    return "> " + " ".join(kac(t) if op == "=" else f"~~{kac(t)}~~" if op == "-" else f"**{kac(t)}**" for op, t in f["p"])


def ayrinti(d, k, db):
    a, b = d["a"] or {}, d["b"] or {}
    r = b or a
    parcalar = []
    if d["tur"] == "yeni":
        parcalar.append(", ".join(x for x in (r.get("hukum"), f"çatı: {r['cati']}" if r.get("cati") else None) if x))
    elif d["tur"] == "kalkan":
        parcalar.append(", ".join(x for x in (a.get("hukum"), f"çatı: {a['cati']}" if a.get("cati") else None) if x))
    else:
        for f in ("hukum", "cati", "ad", "url"):
            if f in d["alanlar"]:
                parcalar.append(f"{ETIKET[f]}: {a.get(f) or '—'} → {b.get(f) or '—'}")
        if "kaynaklar" in d["alanlar"]:
            ea, eb = set(a.get("kaynaklar") or []), set(b.get("kaynaklar") or [])
            parcalar.append(f"bağlantı +{len(eb - ea)} / −{len(ea - eb)}")
        if "ek" in d["alanlar"]:
            ea, eb = a.get("ek") or {}, b.get("ek") or {}
            parcalar.append("; ".join(f"{x}: {kirp(str(ea.get(x) or '—'), 40)} → {kirp(str(eb.get(x) or '—'), 40)}"
                                      for x in sorted(set(ea) | set(eb)) if ea.get(x) != eb.get(x)))
    if not (k in olaylar.DOSYA or k in ("yr", "nt") or d["id"] == "_liste" or d["id"].startswith("/tr")):   # dosyalar, uygulama ve ilaç ürünleri hariç
        hit = db.get(anahtar(r.get("ad")))
        parcalar.append(f"veritabanında: {hit[0]}" + (f" (çatı: {hit[1]})" if hit and hit[1] else "") if hit
                        else "veritabanında yok")
    return " · ".join(p for p in parcalar if p)


def madde(d, k, db, metinli=True):
    r = d["b"] or d["a"]
    ad = kac(r.get("ad") or d["id"])
    ad = f"[{ad}]({r['url']})" if r.get("url") else ad
    s = f"- **{baslik(d)}:** {ad}"
    a = ayrinti(d, k, db)
    if a:
        s += f" — {a}"
    if metinli and "metin" in d["alanlar"]:
        s += "\n  <details><summary>Metin farkı</summary>\n\n" + "\n".join(
            "  " + x for x in metin_farki((d["a"] or {}).get("metin"), (d["b"] or {}).get("metin")).split("\n")) + \
             "\n\n  </details>"
    return s


def bolum(k, farklar, db, sinir=None, metinli=True):
    K = KAYNAKLAR[k]
    et = [d for d in farklar if etkili(d)]
    dis = [d for d in farklar if not etkili(d)]
    et.sort(key=lambda d: (SIRA.index(baslik(d)), ((d["b"] or d["a"]).get("ad") or "").casefold()))
    satir = [f"## {K['ad']}: {len(farklar)} değişiklik" + (f" ({len(et)} tanesi veritabanının kapsamında)" if dis else ""),
             f"Kapsam: {K['kapsam']}. Kaynak: {K['site']}", ""]
    gos = et if sinir is None else et[:sinir]
    satir += [madde(d, k, db, metinli) for d in gos]
    if sinir is not None and len(et) > sinir:
        satir.append(f"- … ve {len(et) - sinir} değişiklik daha (tam rapora bakın)")
    if dis:
        ozet = {}
        for d in dis:
            ozet[baslik(d)] = ozet.get(baslik(d), 0) + 1
        satir += ["", f"<details><summary>Kapsam dışı {len(dis)} değişiklik: "
                  + ", ".join(f"{v} {x.lower()}" for x, v in sorted(ozet.items(), key=lambda kv: SIRA.index(kv[0])))
                  + "</summary>", ""]
        satir += [madde(d, k, db, False) for d in (dis if sinir is None else dis[:sinir])]
        satir += ["", "</details>"]
    return "\n".join(satir)


# ------------------------------------------------------------------ çalıştırma
def secim(arg):
    if arg in ("tam", "hepsi"):
        return [k for k, v in KAYNAKLAR.items() if v["siklik"] != "yerel"]
    if arg in ("hizli", "gunluk", ""):
        return [k for k, v in KAYNAKLAR.items() if v["siklik"] == "gunluk"]
    ks = [x.strip() for x in arg.split(",") if x.strip()]
    bilinmeyen = [x for x in ks if x not in KAYNAKLAR]
    if bilinmeyen:
        sys.exit(f"bilinmeyen kaynak: {bilinmeyen} (seçenekler: {', '.join(KAYNAKLAR)})")
    return ks


def main():
    ks = secim(sys.argv[1] if len(sys.argv) > 1 else "hizli")
    simdi = dt.datetime.now(TSI)
    zaman = simdi.isoformat(timespec="seconds")
    durum = oku(DURUM, {})
    sonuc, hatalar, uyarilar, engeller, yeni_olay = {}, {}, {}, {}, []
    for k in ks:
        K = KAYNAKLAR[k]
        onceki = oku(VERI / f"{k}.json", {})
        dk = durum.setdefault(k, {})
        print(f"[{k}] {K['ad']} kontrol ediliyor…", flush=True)
        try:
            r = K["cek"](onceki)
        except Exception as e:  # noqa: BLE001
            msg = str(e) or type(e).__name__
            if isinstance(e, EngelHatasi):
                # site bot korumasıyla geri çevirdi: son başarılı kontrolden bu yana ENGEL_GUN geçmediyse geçici sayılır
                sb = dk.get("son_basari")
                gun = (simdi - dt.datetime.fromisoformat(sb)).days if sb else None
                if gun is not None and gun < ENGEL_GUN:
                    engeller[k] = f"{msg}; son başarılı kontrol {sb[:10]}"
                    dk.update(son_kontrol=zaman, durum="engel: " + msg)
                    print(f"[{k}] geçici olarak okunamadı: {engeller[k]}", flush=True)
                    continue
                msg += f"; {gun} gündür okunamıyor" if gun is not None else "; hiç okunamadı"
            traceback.print_exc()
            hatalar[k] = msg
            dk.update(son_kontrol=zaman, durum="hata: " + msg)
            continue
        dk.update(son_kontrol=zaman, son_basari=zaman, durum="ok", parmak_izi=r["parmak_izi"])
        if r.get("degismedi"):
            print(f"[{k}] değişmedi", flush=True)
            continue
        if r.get("uyarilar"):
            uyarilar[k] = r["uyarilar"]
        f = fark(onceki.get("kayitlar") or {}, r["kayitlar"]) if onceki else []
        if onceki and not f:                      # kayıtlar aynı: anlık görüntü yeniden yazılmaz
            print(f"[{k}] değişmedi", flush=True)
            continue
        n0 = len(onceki.get("kayitlar") or {})
        if n0 >= 20 and len(f) > 0.5 * n0 and not os.environ.get("IZLEME_ZORLA"):
            # kayıtların yarısından fazlası birden: büyük olasılıkla site yapısı değişti ve ayrıştırıcı bozuldu
            hatalar[k] = (f"{n0} kaydın {len(f)} tanesi birden değişti; site yapısı değişmiş olabilir. Anlık görüntü "
                          f"güncellenmedi (değişiklik gerçekse iş akışını 'zorla' seçeneğiyle yeniden çalıştırın)")
            dk.update(durum="hata: toplu değişiklik")
            print(f"[{k}] {hatalar[k]}", flush=True)
            continue
        yaz(VERI / f"{k}.json", {"kaynak": k, "ad": K["ad"], "tarih": zaman, "parmak_izi": r["parmak_izi"],
                                  "meta": r.get("meta") or {}, "kayitlar": r["kayitlar"]})
        if not onceki:
            print(f"[{k}] ilk anlık görüntü kaydedildi ({len(r['kayitlar'])} kayıt)", flush=True)
            continue
        if f:
            dk["son_degisiklik"] = zaman
            sonuc[k] = f
            yeni_olay += olaylar.uret(k, f, simdi.date().isoformat())
        print(f"[{k}] {len(f)} değişiklik ({sum(map(etkili, f))} kapsamda)", flush=True)
    yaz(DURUM, durum)
    n_olay = olaylar.ekle(OLAY, yeni_olay)

    db = veritabani()
    tarih = simdi.strftime("%Y-%m-%d %H:%M")
    kisa = ", ".join(f"{KAYNAKLAR[k]['ad']} {len(v)}" for k, v in sonuc.items())
    ust = [f"Kontrol edilen kaynaklar: {', '.join(KAYNAKLAR[k]['ad'] for k in ks)}."]
    if sonuc:
        ust.append(f"Değişiklik bulunan: {kisa}. Olay kaydına (sitenin Güncellemeler sekmesi) {n_olay} olay eklendi.")
    else:
        ust.append("Değişiklik yok.")
    if hatalar:
        ust.append("Kontrol edilemeyen: " + "; ".join(f"{KAYNAKLAR[k]['ad']} ({v})" for k, v in hatalar.items()) + ".")
    if engeller:
        ust.append("Geçici olarak okunamayan (sitenin bot koruması, önceki anlık görüntü korundu): "
                   + "; ".join(f"{KAYNAKLAR[k]['ad']} ({v})" for k, v in engeller.items()) + ".")
    for k, v in uyarilar.items():
        ust.append(f"{KAYNAKLAR[k]['ad']}: " + "; ".join(v) + ".")
    aciklama = ("“Veritabanında” notu, kaydın adının sitedeki (index.html) bir kuruluşun adıyla ya da diğer adlarından "
                "biriyle eşleşip eşleşmediğini gösterir; eşleşme yalnız yazıma bakar. Değişiklikler veritabanına "
                "kendiliğinden işlenmez.")
    rapor_yolu = None
    if sonuc or hatalar:
        RAPOR.mkdir(parents=True, exist_ok=True)
        rapor_yolu = RAPOR / f"{simdi.strftime('%Y-%m-%d-%H%M')}.md"
        govde = [f"# Kaynak izleme raporu: {tarih} (TSİ)", "", *ust, "", aciklama, ""]
        govde += [bolum(k, v, db) + "\n" for k, v in sonuc.items()]
        rapor_yolu.write_text("\n".join(govde), "utf-8")
        print("rapor:", rapor_yolu.relative_to(KOK.parent), flush=True)

    # kısa bildirim (Issue yorumu) ve GitHub çıktıları
    if os.environ.get("BILDIRIM") and rapor_yolu:
        depo = os.environ.get("GITHUB_REPOSITORY")
        link = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{depo}/blob/main/"
                f"{rapor_yolu.relative_to(KOK.parent).as_posix()}") if depo else rapor_yolu.name
        b = [f"### Kaynak izleme: {tarih} (TSİ)", "", *ust, "", f"Tam rapor: {link}", ""]
        b += [bolum(k, v, db, sinir=BILDIRIM_SINIR) + "\n" for k, v in sonuc.items()]
        if os.environ.get("BILDIRIM_KISI"):
            b.append(f"cc {os.environ['BILDIRIM_KISI']}")
        metin = "\n".join(b)
        if len(metin) > 60000:                       # Issue yorum sınırı 65536 karakter
            b = [f"### Kaynak izleme: {tarih} (TSİ)", "", *ust, "", f"Değişiklikler çok olduğu için yalnız tam rapor: {link}"]
            metin = "\n".join(b)
        Path(os.environ["BILDIRIM"]).write_text(metin, "utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"degisiklik={1 if sonuc else 0}\n")
            fh.write(f"hata={1 if hatalar else 0}\n")
            fh.write(f"ozet={kirp(kisa or 'değişiklik yok', 120)}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write("\n".join([f"## Kaynak izleme: {tarih} (TSİ)", "", *ust, ""])
                     + "\n".join(bolum(k, v, db, sinir=BILDIRIM_SINIR, metinli=False) for k, v in sonuc.items()))
    print("\n".join(ust))
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
