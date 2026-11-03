"""Kaynak listelerdeki değişikliklerden olay kaydı (izleme/olaylar.json) üretir.

Her olay bir listenin bir kayıt hakkındaki tek bir adımıdır: ekleme, çıkarma (geri çekme), seviye yükseltme/düşürme,
metin düzeltme, kaynak güncelleme, çatı ya da ad değişikliği. Yalnız veritabanının kapsamına dokunan değişiklikler
olaydır (ör. bykt'de “Alınabilir” bir markanın metin düzeltmesi olay değildir; “Alınabilir”den “İnsafa Bağlı”ya
geçmesi olaydır). Olay kaydı sitenin “Güncellemeler” sekmesini besler ve veritabanı derlenirken geri çekilen kanıtlar
bu kayıttan işaretlenir.

Olay alanları: id, tespit (izlemenin fark ettiği gün), tarih (listenin kendi gösterdiği gün, biliniyorsa), liste,
kimlik (listedeki kayıt kimliği), marka, cati, tur, onceki, sonraki, kapsam ("girdi" | "cikti"), url, fark (metin),
baglanti (eklenen/çıkan kanıt bağlantıları), eski (geri çekilen kaydın son hâli: hukum, metin, url, kaynaklar, cati).
"""
import difflib
import json
import re
from pathlib import Path

TUR = {"ekleme": "Ekleme", "cikarma": "Çıkarma", "seviye_yukseltme": "Seviye yükseltme",
       "seviye_dusurme": "Seviye düşürme", "seviye": "Seviye değişikliği", "metin": "Metin düzeltme",
       "kaynak": "Kaynak güncelleme", "cati": "Çatı değişikliği", "ad": "Ad değişikliği", "bilgi": "Bilgi güncelleme",
       "veri": "Veri dosyası güncelleme"}
# hüküm sıraları (yüksek = daha ağır); listede olmayan hükümler sıralanamaz → "Seviye değişikliği"
DERECE = {
    "bykt": {"Alınabilir": 1, "İnsafa Bağlı": 2, "Kesin Boykot": 3},
    "bt": {"Listede değil (0)": 0, "Derecesiz": 0, "1 Çarpılı Şirket": 1, "2 Çarpılı Şirket": 2, "3 Çarpılı Şirket": 3},
    "bd": {"Uygun": 0, "Araştırılıyor": 0, "Ahlaken Boykot": 0, "Şüpheli": 1, "İkincil Boykot": 2, "Boykot": 3},
    "bco": {"Boykot değil": 0, "Boykot": 1},
    "bi": {"Düşük": 1, "Orta": 2, "Yüksek": 3, "Çok yüksek": 4},
    "bl": {"Düşük": 1, "Orta": 2, "Yüksek": 3},
    "bc": {"Level 3: Broad Connections": 1, "Level 2: Connected Companies": 2, "Official BDS Priority Campaign": 3},
}
DOSYA = {"dbio", "inv"}          # kayıtları veri dosyası olan kaynaklar


def duz(s):
    return re.sub(r"\s+", " ", s or "").strip()


def metin_farki(a, b, baglam=8, en=600, toplam=2500):
    """Kelime düzeyinde fark: {"p": [[işlem, metin], ...]}; işlem "=" (aynı, uzunsa kısaltılmış), "-" (silinen), "+" (eklenen)."""
    A, B = re.findall(r"\S+", duz(a)), re.findall(r"\S+", duz(b))
    ops = difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes()
    if all(o[0] == "equal" for o in ops):
        return None
    kirp = lambda s: s if len(s) <= en else s[: en - 1].rstrip() + "…"
    p, n = [], 0
    for k, (op, i1, i2, j1, j2) in enumerate(ops):
        if op == "equal":
            w = A[i1:i2]
            if k == 0 and len(w) > baglam:
                t = "… " + " ".join(w[-baglam:])
            elif k == len(ops) - 1 and len(w) > baglam:
                t = " ".join(w[:baglam]) + " …"
            elif len(w) > 2 * baglam:
                t = " ".join(w[:baglam]) + " … " + " ".join(w[-baglam:])
            else:
                t = " ".join(w)
            p.append(["=", t])
        else:
            if i2 > i1:
                p.append(["-", kirp(" ".join(A[i1:i2]))])
            if j2 > j1:
                p.append(["+", kirp(" ".join(B[j1:j2]))])
        n += len(p[-1][1])
        if n > toplam:
            p.append(["=", "…"])
            break
    return {"p": p}


def _eski(a):
    return {k: a[k] for k in ("hukum", "metin", "url", "kaynaklar", "cati") if a.get(k)}


def uret(k, farklar, tespit):
    """izle.fark() çıktısından olaylar. farklar: [{tur: yeni|kalkan|degisti, id, a, b, alanlar}]."""
    out = []

    def olay(d, tur, **x):
        r = d["b"] or d["a"]
        o = {"id": f"{tespit}|{k}|{d['id']}|{tur}", "tespit": tespit, "liste": k, "kimlik": d["id"],
             "marka": r.get("ad") or d["id"], "cati": r.get("cati"), "tur": tur, "url": r.get("url")}
        o.update({a: v for a, v in x.items() if v not in (None, "", [], {})})
        out.append(o)

    for d in farklar:
        a, b = d["a"] or {}, d["b"] or {}
        if k in DOSYA:
            if d["tur"] == "yeni":
                olay(d, "veri", sonraki="yeni veri dosyası", tarih=b.get("tarih"))
            elif d["tur"] == "kalkan":
                olay(d, "veri", onceki="veri dosyası kaldırıldı")
            else:
                olay(d, "veri", onceki="önceki sürüm", sonraki="dosya içeriği değişti", tarih=b.get("tarih"))
            continue
        if d["tur"] == "yeni":
            if b.get("kapsam"):
                olay(d, "ekleme", sonraki=b.get("hukum"), tarih=b.get("eklenme") or b.get("tarih"))
            continue
        if d["tur"] == "kalkan":
            if a.get("kapsam"):
                olay(d, "cikarma", onceki=a.get("hukum"), kapsam="cikti", eski=_eski(a))
            continue
        al = d["alanlar"]
        if a.get("kapsam") != b.get("kapsam") and "hukum" not in al:
            # hüküm aynı, kapsam değişti (ör. BT'de çatının gizlenmesi): listeye giriş / çıkış
            if b.get("kapsam"):
                olay(d, "ekleme", sonraki=b.get("hukum"), kapsam="girdi", tarih=b.get("tarih"))
            else:
                olay(d, "cikarma", onceki=a.get("hukum"), kapsam="cikti", eski=_eski(a), tarih=b.get("tarih"))
            continue
        if not (a.get("kapsam") or b.get("kapsam")):
            continue
        if "hukum" in al:
            ra, rb = DERECE.get(k, {}).get(a.get("hukum")), DERECE.get(k, {}).get(b.get("hukum"))
            tur = "seviye" if ra is None or rb is None or ra == rb else ("seviye_yukseltme" if rb > ra else "seviye_dusurme")
            kp = "girdi" if b.get("kapsam") and not a.get("kapsam") else "cikti" if a.get("kapsam") and not b.get("kapsam") else None
            olay(d, tur, onceki=a.get("hukum"), sonraki=b.get("hukum"), kapsam=kp, tarih=b.get("tarih"),
                 eski=_eski(a) if kp == "cikti" else None)
        if not (a.get("kapsam") and b.get("kapsam")):
            continue                                   # kapsama yeni giren ya da çıkan kaydın diğer alanları ayrı olay değil
        if "cati" in al:
            olay(d, "cati", onceki=a.get("cati"), sonraki=b.get("cati"), tarih=b.get("tarih"))
        if "ad" in al:
            olay(d, "ad", onceki=a.get("ad"), sonraki=b.get("ad"), tarih=b.get("tarih"))
        if "metin" in al:
            olay(d, "metin", fark=metin_farki(a.get("metin"), b.get("metin")), tarih=b.get("tarih"))
        if "kaynaklar" in al:
            ea, eb = a.get("kaynaklar") or [], b.get("kaynaklar") or []
            olay(d, "kaynak", baglanti={"eklenen": [u for u in eb if u not in ea], "cikan": [u for u in ea if u not in eb]},
                 tarih=b.get("tarih"))
        if "url" in al or "ek" in al:
            ea, eb = dict(a.get("ek") or {}), dict(b.get("ek") or {})
            if "url" in al:
                ea["sayfa"], eb["sayfa"] = a.get("url"), b.get("url")
            ks = [x for x in sorted(set(ea) | set(eb)) if ea.get(x) != eb.get(x)]
            olay(d, "bilgi", onceki="; ".join(f"{x}: {ea.get(x) or '—'}" for x in ks),
                 sonraki="; ".join(f"{x}: {eb.get(x) or '—'}" for x in ks), tarih=b.get("tarih"))
    return out


def oku(yol):
    try:
        return json.loads(Path(yol).read_text("utf-8"))
    except FileNotFoundError:
        return []


def ekle(yol, yeni):
    """Olayları dosyaya ekler (aynı kimlikli olay yenisiyle değişir); yeniden eskiye sıralı yazar."""
    if not yeni:
        return 0
    eski = {o["id"]: o for o in oku(yol)}
    for o in yeni:
        eski[o["id"]] = o
    hepsi = sorted(eski.values(), key=lambda o: (o["tespit"], o["liste"], o["marka"].casefold(), o["tur"]), reverse=True)
    Path(yol).write_text(json.dumps(hepsi, ensure_ascii=False, indent=1) + "\n", "utf-8")
    return len(yeni)
