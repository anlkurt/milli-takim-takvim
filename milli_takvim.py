#!/usr/bin/env python3
"""Türkiye A Milli Erkek Basketbol ve A Milli Kadın Voleybol takımlarının maçlarını
abone olunabilir .ics takvimlerine dönüştürür.

Kaynaklar:
  Basketbol : FIBA (fiba.basketball) etkinlik sayfaları. Dünya Kupası, Dünya Kupası
              Elemeleri, EuroBasket, EuroBasket Elemeleri, Olimpiyatlar.
  Voleybol  : Volleyball World (FIVB). Milletler Ligi (VNL), Dünya Şampiyonası,
              Olimpiyatlar.
              CEV (livescores.cev.eu). Avrupa Şampiyonası ve elemeleri, Avrupa Ligi.

Kullanım:
    python3 milli_takvim.py        # docs/basketbol.ics ve docs/voleybol.ics üretir

Bir takvimin kaynaklarından biri çalışmazsa o takvim dosyasına dokunulmaz (eski hali
korunur) ve betik hata koduyla biter. Sadece Python standart kütüphanesi kullanılır.
"""

import gzip
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MAC_SURESI = timedelta(hours=2)
HATIRLATMALAR = [("-PT1H", "1 saat"), ("-PT5M", "5 dakika")]  # maçtan önce
ISTANBUL = timezone(timedelta(hours=3))  # Türkiye 2016'dan beri sabit UTC+3
DOCS = Path(__file__).resolve().parent / "docs"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

FIBA_ETKINLIKLER = "https://www.fiba.basketball/en/events"
FIBA_MACLAR = "https://www.fiba.basketball/en/events/{}/games"
# Etkinlik listesinde görünmese de her zaman denenecek sayfalar (yoksa atlanır).
FIBA_SABIT = [
    "fiba-basketball-world-cup-2027-european-qualifiers",
    "fiba-basketball-world-cup-2027",
]
VW_API = "https://en.volleyballworld.com/api/v1/globalschedule/{}/{}"
CEV_API = "https://livescores.cev.eu/api/matches/period/{}/{}"

# Ülke kodu -> Türkçe ad. Listede olmayan ülke kaynağın verdiği adla yazılır.
ULKELER = {
    "TUR": "Türkiye", "ITA": "İtalya", "ISL": "İzlanda", "LTU": "Litvanya", "SRB": "Sırbistan",
    "BIH": "Bosna Hersek", "SUI": "İsviçre", "GRE": "Yunanistan", "ESP": "İspanya",
    "FRA": "Fransa", "GER": "Almanya", "SLO": "Slovenya", "CRO": "Hırvatistan",
    "MNE": "Karadağ", "LAT": "Letonya", "EST": "Estonya", "FIN": "Finlandiya",
    "SWE": "İsveç", "NOR": "Norveç", "DEN": "Danimarka", "POL": "Polonya", "CZE": "Çekya",
    "SVK": "Slovakya", "HUN": "Macaristan", "ROU": "Romanya", "BUL": "Bulgaristan",
    "MKD": "Kuzey Makedonya", "ALB": "Arnavutluk", "KOS": "Kosova", "GEO": "Gürcistan",
    "ARM": "Ermenistan", "AZE": "Azerbaycan", "UKR": "Ukrayna", "BLR": "Belarus",
    "RUS": "Rusya", "ISR": "İsrail", "CYP": "Kıbrıs", "POR": "Portekiz", "NED": "Hollanda",
    "BEL": "Belçika", "LUX": "Lüksemburg", "AUT": "Avusturya", "GBR": "Büyük Britanya",
    "ENG": "İngiltere", "IRL": "İrlanda", "MDA": "Moldova", "USA": "ABD", "CAN": "Kanada",
    "MEX": "Meksika", "PUR": "Porto Riko", "DOM": "Dominik Cumhuriyeti", "CUB": "Küba",
    "BRA": "Brezilya", "ARG": "Arjantin", "COL": "Kolombiya", "PER": "Peru", "CHI": "Şili",
    "VEN": "Venezuela", "URU": "Uruguay", "CHN": "Çin", "JPN": "Japonya", "KOR": "Güney Kore",
    "THA": "Tayland", "VIE": "Vietnam", "PHI": "Filipinler", "TPE": "Çin Taypesi",
    "KAZ": "Kazakistan", "IRI": "İran", "IRN": "İran", "QAT": "Katar", "JOR": "Ürdün",
    "LBN": "Lübnan", "IND": "Hindistan", "INA": "Endonezya", "AUS": "Avustralya",
    "NZL": "Yeni Zelanda", "EGY": "Mısır", "TUN": "Tunus", "MAR": "Fas", "ALG": "Cezayir",
    "KEN": "Kenya", "CMR": "Kamerun", "NGR": "Nijerya", "SEN": "Senegal", "ANG": "Angola",
    "CIV": "Fildişi Sahili", "SSD": "Güney Sudan", "CPV": "Yeşil Burun Adaları",
}


class Bulunamadi(Exception):
    pass


def getir(url, deneme=3):
    for i in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                veri = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    veri = gzip.decompress(veri)
                return veri
        except Exception as e:  # ağ hatasında kısa bekleyip tekrar dene
            if i == deneme - 1:
                raise RuntimeError("{} alınamadı: {}".format(url, e))
            time.sleep(3 * (i + 1))


def utc(metin):
    """'2026-11-29T16:00:00' veya '...Z' biçimindeki UTC zamanını datetime'a çevirir."""
    return datetime.strptime(metin[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def ulke(kod, ad):
    if kod in ULKELER:
        return ULKELER[kod]
    ad = (ad or "").strip()
    return ad.title() if ad.isupper() else (ad or "Belli değil")


def mac(uid, bas, gun, ev, dep, skor, yer, satirlar, kaynak):
    return {"uid": uid, "baslangic": bas, "gun": gun, "ev": ev, "deplasman": dep,
            "skor": skor, "yer": yer, "aciklama": [s for s in satirlar if s], "kaynak": kaynak}


# ---------------------------------------------------------------- FIBA (basketbol)

def fiba_sayfa_verisi(sayfa):
    """Sayfaya gömülü (Next.js) veri parçalarını birleştirip düz metin olarak döndürür."""
    parcalar = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', sayfa)
    return "".join(json.loads(p) for p in parcalar)


def fiba_slug_uygun(slug):
    """A erkek milli takımın oynayabileceği etkinlik mi?"""
    if "women" in slug or re.search(r"u\d\d", slug) or "3x3" in slug:
        return False
    if "olympic" in slug or "eurobasket" in slug:
        return True
    return bool(re.fullmatch(r"fiba-basketball-world-cup-\d{4}(-european-qualifiers)?", slug))


def fiba_yarisma_adi(ad):
    ad = ad or ""
    m = re.search(r"\d{4}", ad)
    yil = m.group(0) if m else ""
    if "World Cup" in ad:
        return "FIBA {} Dünya Kupası{}".format(yil, " Avrupa Elemeleri" if "Qualifiers" in ad else "")
    if "EuroBasket" in ad:
        ek = " Ön Elemeleri" if "Pre-Qualifiers" in ad else " Elemeleri" if "Qualifiers" in ad else ""
        return "FIBA EuroBasket {}{}".format(yil, ek)
    return ad


def fiba_maclari():
    liste = getir(FIBA_ETKINLIKLER).decode("utf-8", "replace")
    sluglar = list(FIBA_SABIT)
    for s in sorted(set(re.findall(r"/en/events/([a-z0-9-]+)", liste))):
        if fiba_slug_uygun(s) and s not in sluglar:
            sluglar.append(s)

    oyunlar = {}
    coz = json.JSONDecoder()
    for slug in sluglar:
        sayfa = getir(FIBA_MACLAR.format(slug)).decode("utf-8", "replace")
        if "<title>Page Not Found" in sayfa:
            continue
        veri = fiba_sayfa_verisi(sayfa)
        for m in re.finditer(r'\{"gameId":', veri):
            try:
                o, _ = coz.raw_decode(veri, m.start())
            except ValueError:
                continue
            if "teamA" in o and "competition" in o:
                oyunlar[o["gameId"]] = o
        print("  FIBA {}: sayfa okundu".format(slug))
    if not oyunlar:
        raise RuntimeError("FIBA sayfalarında hiç maç bulunamadı (sayfa yapısı değişmiş olabilir)")

    maclar = []
    for o in oyunlar.values():
        a, b, y = o.get("teamA") or {}, o.get("teamB") or {}, o.get("competition") or {}
        if "TUR" not in (a.get("code"), b.get("code")):
            continue
        if y.get("gender") != "Men" or y.get("ageCategory") != "Senior":
            continue
        if o.get("isPostponed") or not o.get("gameDateTimeUTC"):
            continue
        saat_belli = o.get("hasTimeGameDateTime", True)
        bas = utc(o["gameDateTimeUTC"]) if saat_belli else None
        gun = bas.astimezone(ISTANBUL).date() if bas else utc(o["gameDateTime"]).date()
        skor = None
        if o.get("statusCode") == "VALID" and (o.get("teamAScore") or o.get("teamBScore")):
            skor = "{}-{}".format(o["teamAScore"], o["teamBScore"])
        tur = o.get("round") or {}
        tur_adi = tur.get("roundName") or ""
        if tur.get("roundType") == "G" and tur.get("roundNumber"):
            tur_adi = "{}. tur".format(tur["roundNumber"])
        if o.get("groupPairingCode") and tur.get("roundType") == "G":
            tur_adi += ", {} Grubu".format(o["groupPairingCode"])
        yer = ", ".join(x for x in (o.get("venueName"), o.get("hostCity")) if x)
        maclar.append(mac(
            "fiba-{}".format(o["gameId"]), bas, gun,
            ulke(a.get("code"), a.get("shortName")), ulke(b.get("code"), b.get("shortName")),
            skor, yer, [fiba_yarisma_adi(y.get("officialName")), tur_adi], "FIBA"))
    return maclar


# ---------------------------------------------------------------- Volleyball World

def vw_yarisma_adi(ad):
    ad = ad or ""
    if re.search(r"\bVNL\b|Nations League", ad):
        m = re.search(r"\d{4}", ad)
        return "Milletler Ligi (VNL) {}".format(m.group(0) if m else "").strip()
    if "World Championship" in ad:
        m = re.search(r"\d{4}", ad)
        return "FIVB Dünya Şampiyonası {}".format(m.group(0) if m else "").strip()
    return ad


def vw_maclari(bas_gun, bit_gun):
    maclar = []
    g = bas_gun
    while g <= bit_gun:
        son = min(g + timedelta(days=180), bit_gun)
        veri = json.loads(getir(VW_API.format(g.isoformat(), son.isoformat())))
        takimlar = {}
        for t in veri.get("allTeams", []):
            if t.get("discipline") == "volley":
                takimlar.setdefault(t.get("no"), t)
        for m in veri.get("matches", []):
            if m.get("discipline") != "volley" or m.get("gender") != "Women":
                continue
            ad = m.get("competitionFullName") or ""
            if re.search(r"\bU\d\d\b|Youth|Junior|Club", ad):
                continue
            a, b = takimlar.get(m.get("teamANo")) or {}, takimlar.get(m.get("teamBNo")) or {}
            if not any(t.get("code") == "TUR" and not t.get("isClub") for t in (a, b)):
                continue
            zaman = utc(m["matchDateUtc"])
            bas = None if m.get("isMatchTBD") else zaman
            skor = None
            if m.get("matchStatus") == 2 and (m.get("teamAScore") or m.get("teamBScore")):
                skor = "{}-{}".format(m["teamAScore"], m["teamBScore"])
            havuz = (m.get("pool") or {}).get("name") or ""
            yer = ", ".join(x.strip() for x in (m.get("city"), m.get("country")) if x and x.strip())
            maclar.append(mac(
                "vw-{}".format(m["matchNo"]), bas, zaman.astimezone(ISTANBUL).date(),
                ulke(a.get("code"), a.get("name")), ulke(b.get("code"), b.get("name")),
                skor, yer, [vw_yarisma_adi(ad), " · ".join(x for x in (m.get("roundName"), havuz) if x)],
                "Volleyball World"))
        print("  Volleyball World {} – {}: {} kayıt tarandı".format(g, son, len(veri.get("matches", []))))
        g = son + timedelta(days=1)
    return maclar


# ---------------------------------------------------------------- CEV

def cev_yarisma_adi(ad):
    ad = re.sub(r"\s*\|\s*Women\s*$", "", ad or "")
    m = re.search(r"\d{4}", ad)
    yil = m.group(0) if m else ""
    if "EuroVolley" in ad:
        return "CEV Avrupa Şampiyonası (EuroVolley) {}".format(yil).strip()
    if "European League" in ad or "Golden League" in ad:
        return "CEV Avrupa Ligi {}".format(yil).strip()
    return ad


def cev_maclari(bas_gun, bit_gun):
    maclar = []
    for yil in range(bas_gun.year, bit_gun.year + 1):
        veri = json.loads(getir(CEV_API.format("{}0101".format(yil), "{}1231".format(yil))))
        kayitlar = veri["data"]
        for m in kayitlar:
            if m.get("IsBeach") or m.get("IsSnow") or m.get("MaleNotFemale"):
                continue
            ad = m.get("CompetitionName") or ""
            if re.search(r"\bU\d\d\b", ad):
                continue
            # Kulüplerin de ülke kodu TUR olduğu için takım adına da bakılır.
            adlar = [(m.get(k) or "").upper().replace("İ", "I").replace("Ü", "U")
                     for k in ("HomeTeamName", "GuestTeamName")]
            kodlar = [m.get("HomeTeamNationID"), m.get("GuestTeamNationID")]
            if not any(k == "TUR" and a in ("TURKIYE", "TURKEY") for k, a in zip(kodlar, adlar)):
                continue
            if m.get("MatchStatusDescription") == "Bye" or not m.get("MatchDateTime_UTC"):
                continue
            zaman = utc(m["MatchDateTime_UTC"])
            yerel = m.get("MatchDateTime") or ""
            saat_yok = m.get("MatchStatusDescription") == "Draft" or yerel.endswith("T00:00:00")
            skor = None
            if m.get("MatchStatus") == 4 and (m.get("WonSetHome") or m.get("WonSetGuest")):
                skor = "{}-{}".format(m["WonSetHome"], m["WonSetGuest"])
            yer = ", ".join(x.strip() for x in (m.get("StadiumName"), m.get("StadiumCity")) if x and x.strip())
            asama = " · ".join(x for x in (m.get("PhaseName"), m.get("ChampionshipName")) if x)
            maclar.append(mac(
                "cev-{}".format(m["MatchID"]), None if saat_yok else zaman,
                utc(yerel).date() if saat_yok and yerel else zaman.astimezone(ISTANBUL).date(),
                ulke(kodlar[0], m.get("HomeTeamName")), ulke(kodlar[1], m.get("GuestTeamName")),
                skor, yer, [cev_yarisma_adi(ad), asama], "CEV"))
        print("  CEV {}: {} kayıt tarandı".format(yil, len(kayitlar)))
    return maclar


# ---------------------------------------------------------------- ICS

def kacis(metin):
    return metin.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def katla(satir):
    """RFC 5545: satırları 75 oktette katlar, UTF-8 karakterlerini bölmeden."""
    b = satir.encode("utf-8")
    parcalar = []
    while len(b) > 75:
        kes = 75 if not parcalar else 74
        while (b[kes] & 0xC0) == 0x80:
            kes -= 1
        parcalar.append(b[:kes].decode("utf-8"))
        b = b[kes:]
    parcalar.append(b.decode("utf-8"))
    return "\r\n ".join(parcalar)


def ics_olustur(maclar, takvim_adi, simge):
    simdi = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//milli-takim-takvim//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + kacis(takvim_adi),
        "X-WR-TIMEZONE:Europe/Istanbul",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    for m in maclar:
        if m["skor"]:
            baslik = "{} {} {} {}".format(simge, m["ev"], m["skor"], m["deplasman"])
        else:
            baslik = "{} {} - {}".format(simge, m["ev"], m["deplasman"])
        aciklama = list(m["aciklama"])
        if m["baslangic"] is None:
            baslik += " (saat belli değil)"
            aciklama.append("Maç saati henüz açıklanmadı; açıklanınca otomatik güncellenir.")
        aciklama.append("Kaynak: " + m["kaynak"])

        s += ["BEGIN:VEVENT", "UID:{}@milli-takim-takvim".format(m["uid"]), "DTSTAMP:" + simdi]
        if m["baslangic"]:
            s += [
                "DTSTART:" + m["baslangic"].strftime("%Y%m%dT%H%M%SZ"),
                "DTEND:" + (m["baslangic"] + MAC_SURESI).strftime("%Y%m%dT%H%M%SZ"),
            ]
        else:
            s += [
                "DTSTART;VALUE=DATE:" + m["gun"].strftime("%Y%m%d"),
                "DTEND;VALUE=DATE:" + (m["gun"] + timedelta(days=1)).strftime("%Y%m%d"),
                "TRANSP:TRANSPARENT",
            ]
        s += ["SUMMARY:" + kacis(baslik), "DESCRIPTION:" + kacis("\n".join(aciklama))]
        if m["yer"]:
            s.append("LOCATION:" + kacis(m["yer"]))
        if m["baslangic"] and not m["skor"]:
            for tetik, sure in HATIRLATMALAR:
                s += [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    "DESCRIPTION:" + kacis("{} {} sonra başlıyor".format(baslik, sure)),
                    "TRIGGER:" + tetik,
                    "END:VALARM",
                ]
        s.append("END:VEVENT")
    s.append("END:VCALENDAR")
    return "\r\n".join(katla(x) for x in s) + "\r\n"


def sirala(maclar):
    tekil = {}
    for m in maclar:  # aynı maç iki kaynakta da varsa (gün + eşleşme) ilkini tut
        tekil.setdefault((m["gun"], m["ev"], m["deplasman"]), m)
    return sorted(tekil.values(),
                  key=lambda m: (m["gun"], m["baslangic"] or datetime.max.replace(tzinfo=timezone.utc)))


def takvim_yaz(dosya, takvim_adi, simge, kaynaklar):
    """Kaynakların hepsi çalışırsa dosyayı yazar; biri bile çalışmazsa eski dosya kalır."""
    maclar = []
    try:
        for kaynak in kaynaklar:
            maclar += kaynak()
    except Exception as e:
        print("HATA: {} güncellenmedi, eski hali korunuyor: {}".format(dosya.name, e), file=sys.stderr)
        return False
    maclar = sirala(maclar)
    if not maclar:
        print("HATA: {} için hiç maç bulunamadı, eski hali korunuyor.".format(dosya.name), file=sys.stderr)
        return False
    dosya.parent.mkdir(parents=True, exist_ok=True)
    with open(dosya, "w", encoding="utf-8", newline="") as f:
        f.write(ics_olustur(maclar, takvim_adi, simge))
    gelecek = sum(1 for m in maclar if not m["skor"])
    print("{}: {} maç ({} oynanmamış)".format(dosya.name, len(maclar), gelecek))
    return True


def main():
    bugun = date.today()
    bas_gun, bit_gun = date(bugun.year, 1, 1), date(bugun.year + 1, 12, 31)
    tamam = [
        takvim_yaz(DOCS / "basketbol.ics", "Türkiye Basketbol (A Erkek)", "🏀", [fiba_maclari]),
        takvim_yaz(DOCS / "voleybol.ics", "Türkiye Voleybol (A Kadın)", "🏐",
                   [lambda: vw_maclari(bas_gun, bit_gun), lambda: cev_maclari(bas_gun, bit_gun)]),
    ]
    if not all(tamam):
        sys.exit(1)


if __name__ == "__main__":
    main()
