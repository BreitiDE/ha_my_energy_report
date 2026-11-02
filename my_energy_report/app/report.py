"""Auswertung der Energie-Statistik und PDF-Bericht für Woche, Monat und Jahr (Deutsch/Englisch)."""

import calendar
import math
import os
from datetime import date, datetime, timedelta, timezone

KATEGORIEN = ["pv", "bezug", "einspeisung", "laden", "entladen", "wasser"]

TAGE = {"de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
MONATE = {"de": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
          "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]}
MONATE_LANG = {"de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
                      "Oktober", "November", "Dezember"],
               "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                      "October", "November", "December"]}

EN = {
    "Energie-Wochenbericht": "Weekly Energy Report",
    "Energie-Monatsbericht": "Monthly Energy Report",
    "Energie-Jahresbericht": "Annual Energy Report",
    "PV-Erzeugung": "Solar production",
    "Hausverbrauch": "Home consumption",
    "Autarkie": "Self-sufficiency",
    "Eigenverbrauch": "Self-consumption",
    "Netzbezug": "Grid import",
    "Einspeisung": "Grid export",
    "Batterie": "Battery",
    "Batterie entladen": "Battery discharged",
    "Wasser": "Water",
    "Netz": "Grid",
    "Solar direkt": "Solar direct",
    "Woher kam der Strom?": "Where did the power come from?",
    "Hausverbrauch je Tag": "Home consumption per day",
    "Hausverbrauch je Monat": "Home consumption per month",
    "Erzeugung und Verbrauch im Tagesverlauf": "Production and consumption by hour",
    "Ø kWh je Stunde": "avg. kWh per hour",
    "Ø Liter je Stunde": "avg. litres per hour",
    "Verbrauch": "Consumption",
    "Energieflüsse": "Energy flows",
    "Herkunft des Verbrauchs": "Source of consumption",
    "Verwendung des PV-Stroms": "Use of solar power",
    "Direkt verbraucht": "Used directly",
    "In die Batterie": "Into battery",
    "Eingespeist": "Exported",
    "Erzeugung": "Production",
    "Vorwoche": "Previous week",
    "Vormonat": "Previous month",
    "Vorjahr": "Previous year",
    "Vorjahresmonat": "Same month last year",
    "Diese Woche": "This week",
    "Dieser Monat": "This month",
    "Dieses Jahr": "This year",
    "Bester Tag": "Best day",
    "Bester Monat": "Best month",
    "Spez. Ertrag": "Specific yield",
    "Spitzenstunde": "Peak hour",
    "Tagesertrag": "Daily yield",
    "Monatsertrag": "Monthly yield",
    "Durchschnittliches Tagesprofil": "Average daily profile",
    "Jahresverlauf {jahr}": "Year {jahr}",
    "PV bisher {v} kWh": "solar so far {v} kWh",
    " · Verbrauch {v} kWh": " · consumption {v} kWh",
    "Bezug {v} kWh": "import {v} kWh",
    "Einspeisung {v} kWh": "export {v} kWh",
    "Saldo {v} kWh": "balance {v} kWh",
    "geladen {a} kWh · entladen {b} kWh": "charged {a} kWh · discharged {b} kWh",
    " · Verhältnis entladen/geladen {v} %": " · discharged/charged ratio {v} %",
    "Geladen": "Charged",
    "Entladen": "Discharged",
    "Wasser im Tagesverlauf": "Water by hour",
    "Liter": "Litres",
    "Details": "Details",
    "Tageswerte": "Daily values",
    "Monatswerte": "Monthly values",
    "Tag": "Day",
    "Monat": "Month",
    "Summe": "Total",
    "Einspeis.": "Export",
    "Bat. +": "Bat. +",
    "Bat. -": "Bat. -",
    "Wasser L": "Water L",
    "Energiewerte in kWh. Bat. + = in die Batterie geladen, Bat. - = aus der Batterie entnommen.":
        "Energy values in kWh. Bat. + = charged into the battery, Bat. - = taken from the battery.",
    "Vergleich": "Comparison",
    "Kennzahl": "Figure",
    "Änderung": "Change",
    "keine Daten": "no data",
    "PV-Erzeugung nach Quelle": "Solar production by source",
    "Ertragsstärkste PV-Stunden": "Strongest solar hours",
    "Ertragsstärkste PV-Tage": "Strongest solar days",
    "Kurzfazit": "Summary",
    "Ø {v} kWh pro Tag": "avg. {v} kWh per day",
    "Ø {v} kWh/Tag · {p}": "avg. {v} kWh/day · {p}",
    "Ø {v} L/Tag · {p}": "avg. {v} L/day · {p}",
    "{v} kWh aus dem Netz": "{v} kWh from the grid",
    "des PV-Stroms selbst genutzt": "of solar power used on site",
    "entladen · {v} kWh geladen": "discharged · {v} kWh charged",
    "{name}: {v} kWh": "{name}: {v} kWh",
    " ggü. VW": " vs. prev. week",
    " ggü. VM": " vs. prev. month",
    " ggü. VJ": " vs. prev. year",
    "keine Vergleichsdaten": "no comparison data",
    "{tag} {von}-{bis} Uhr": "{tag} {von}-{bis}",
    "{tag}, {datum}  {von}:00 - {bis}:00 Uhr": "{tag}, {datum}  {von}:00 - {bis}:00",
    "24 Uhr": "24 h",
    "Erstellt {t} · Quelle: Home Assistant Energie-Statistik": "Created {t} · Source: Home Assistant energy statistics",
    "Seite {n}/{{nb}}": "Page {n}/{{nb}}",
    "KW {kw}": "Week {kw}",
    "Jahr {j}": "Year {j}",
    "in KW {kw}": "in week {kw}",
    "im {m}": "in {m}",
    "im Jahr {j}": "in {j}",
    "Die PV-Anlage hat {wann} {v} kWh erzeugt": "The solar system produced {v} kWh {wann}",
    " ({p} gegenüber {vor}).": " ({p} compared to {vor}).",
    "der Vorwoche": "the previous week",
    "dem Vormonat": "the previous month",
    "dem Vorjahr": "the previous year",
    "Stärkster {e} war {a} ({av} kWh), schwächster {b} ({bv} kWh).":
        "The best {e} was {a} ({av} kWh), the weakest {b} ({bv} kWh).",
    "Tag": "Day",
    "Im Haus wurden {v} kWh verbraucht, davon kamen {n} kWh aus dem Netz":
        "The home used {v} kWh, of which {n} kWh came from the grid",
    ", die Autarkie lag bei {a} %.": ", self-sufficiency was {a} %.",
    "{e} % des PV-Stroms wurden selbst genutzt, {x} kWh gingen ins Netz.":
        "{e} % of the solar power was used on site, {x} kWh went to the grid.",
    "Die Batterie hat {a} kWh aufgenommen und {b} kWh abgegeben.":
        "The battery took in {a} kWh and delivered {b} kWh.",
    "Der Wasserverbrauch lag bei {v} Litern": "Water consumption was {v} litres",
    "Im Vergleich zum Vorjahresmonat lag die PV-Erzeugung bei {p}.":
        "Compared to the same month last year, solar production was {p}.",
    "Kubikmeter": "cubic metres",
    "Fortsetzung": "continued",
    "%-Pkt.": "pp",
}


class Sprache:
    def __init__(self, lang):
        self.lang = "en" if lang == "en" else "de"

    def t(self, text, **kw):
        s = EN.get(text, text) if self.lang == "en" else text
        return s.format(**kw) if kw else s

    def n(self, wert, stellen=1):
        s = f"{wert:,.{stellen}f}"
        if self.lang == "en":
            return s
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def tag(self, i):
        return TAGE[self.lang][i]

    def monat(self, i):
        return MONATE[self.lang][i]

    def monat_lang(self, i):
        return MONATE_LANG[self.lang][i]

    def datum(self, d, jahr=False):
        if self.lang == "en":
            return d.strftime("%d/%m/%Y" if jahr else "%d/%m")
        return d.strftime("%d.%m.%Y" if jahr else "%d.%m.")

    def pct(self, p, suffix=""):
        if p is None:
            return self.t("keine Vergleichsdaten")
        return f"{'+' if p >= 0 else ''}{self.n(p, 0)} %{self.t(suffix) if suffix else ''}"


# ----------------------------------------------------------------------
# Quellen und Zeiträume
# ----------------------------------------------------------------------
def quellen_aus_prefs(prefs):
    q = {k: [] for k in KATEGORIEN}

    def add(kat, sid):
        if sid and sid not in q[kat]:
            q[kat].append(sid)

    for s in (prefs or {}).get("energy_sources", []) or []:
        typ = s.get("type")
        if typ == "solar":
            add("pv", s.get("stat_energy_from"))
        elif typ == "grid":
            for f in s.get("flow_from", []) or []:
                add("bezug", f.get("stat_energy_from"))
            for f in s.get("flow_to", []) or []:
                add("einspeisung", f.get("stat_energy_to"))
            add("bezug", s.get("stat_energy_from"))
            add("einspeisung", s.get("stat_energy_to"))
        elif typ == "battery":
            add("entladen", s.get("stat_energy_from"))
            add("laden", s.get("stat_energy_to"))
        elif typ == "water":
            add("wasser", s.get("stat_energy_from"))
    return q


def _monat_plus(d, n):
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def periode(typ, ref, vorjahr=False):
    """Zeitraum eines Berichts. ref: ein Datum innerhalb des Zeitraums."""
    if typ == "week":
        start = ref - timedelta(days=ref.weekday())
        ende = start + timedelta(days=7)
        vor = (start - timedelta(days=7), start)
        kw = start.isocalendar()
        rid = f"{kw[0]}-W{kw[1]:02d}"
        extra = {"kw": kw[1], "jahr": kw[0]}
    elif typ == "month":
        start = date(ref.year, ref.month, 1)
        ende = _monat_plus(start, 1)
        vor = (_monat_plus(start, -1), start)
        rid = f"{start.year}-M{start.month:02d}"
        extra = {"jahr": start.year, "monat": start.month}
    elif typ == "year":
        start = date(ref.year, 1, 1)
        ende = date(ref.year + 1, 1, 1)
        vor = (date(ref.year - 1, 1, 1), start)
        rid = f"{start.year}-Y"
        extra = {"jahr": start.year}
    else:
        raise ValueError(typ)
    p = {"typ": typ, "id": rid, "start": start, "ende": ende, "vor": vor, "vj": None,
         "jahr_start": date(start.year, 1, 1), **extra}
    if typ == "month" and vorjahr:
        p["vj"] = (date(start.year - 1, start.month, 1), _monat_plus(date(start.year - 1, start.month, 1), 1))
    return p


def letzte_periode(typ, heute):
    """Der letzte abgeschlossene Zeitraum vor 'heute'."""
    if typ == "week":
        return heute - timedelta(days=heute.weekday() + 7)
    if typ == "month":
        return _monat_plus(date(heute.year, heute.month, 1), -1)
    return date(heute.year - 1, 1, 1)


def _lokal(wert, tz):
    if isinstance(wert, (int, float)):
        if wert > 1e11:          # Millisekunden (WebSocket-API)
            wert = wert / 1000
        return datetime.fromtimestamp(wert, tz=tz)
    if isinstance(wert, str):
        wert = datetime.fromisoformat(wert)
    if wert.tzinfo is None:
        wert = wert.replace(tzinfo=timezone.utc)
    return wert.astimezone(tz)


# ----------------------------------------------------------------------
# Auswertung
# ----------------------------------------------------------------------
def _analyse(stat, quellen, von, bis, tz, n, bucket):
    """Stundenwerte eines Zeitraums auswerten. bucket(t) -> Index 0..n-1."""
    stunden = {k: {} for k in KATEGORIEN}
    pro_id = {}
    for kat in KATEGORIEN:
        for sid in quellen.get(kat, []):
            pro_id[sid] = 0.0
            for row in stat.get(sid, []) or []:
                ch = row.get("change")
                if ch is None:
                    continue
                t = _lokal(row["start"], tz)
                if not (von <= t.date() < bis):
                    continue
                ch = max(float(ch), 0.0)
                stunden[kat][t] = stunden[kat].get(t, 0.0) + ch
                pro_id[sid] += ch
    tage = max((bis - von).days, 1)
    a = {k: {"b": [0.0] * n, "profil": [0.0] * 24, "summe": 0.0, "vorhanden": bool(quellen.get(k))}
         for k in KATEGORIEN}
    bil = {k: [0.0] * n for k in ("verbrauch", "direkt", "batterie", "netz", "pv_batt")}
    profil_v = [0.0] * 24
    pv_stunden, pv_tage = {}, {}
    alle = set()
    for k in KATEGORIEN:
        alle.update(stunden[k])
    for t in alle:
        g = {k: stunden[k].get(t, 0.0) for k in KATEGORIEN}
        b = bucket(t)
        if not 0 <= b < n:
            continue
        for k in KATEGORIEN:
            a[k]["b"][b] += g[k]
            a[k]["profil"][t.hour] += g[k] / tage
        pv, bz, es, la, en = g["pv"], g["bezug"], g["einspeisung"], g["laden"], g["entladen"]
        verbrauch = max(pv + bz + en - es - la, 0.0)
        pv_batt = min(la, max(pv - es, 0.0))
        direkt = min(max(pv - es - pv_batt, 0.0), verbrauch)
        batt = min(en, verbrauch - direkt)
        netz = max(verbrauch - direkt - batt, 0.0)
        for k, v in (("verbrauch", verbrauch), ("direkt", direkt), ("batterie", batt), ("netz", netz), ("pv_batt", pv_batt)):
            bil[k][b] += v
        profil_v[t.hour] += verbrauch / tage
        if pv > 0:
            pv_stunden[t] = pv
            pv_tage[t.date()] = pv_tage.get(t.date(), 0.0) + pv
    for k in KATEGORIEN:
        a[k]["summe"] = sum(a[k]["b"])
    v_sum = sum(bil["verbrauch"])
    pv_sum = a["pv"]["summe"]
    return {
        "k": a, "bil": bil, "tage": tage, "daten_vorhanden": bool(alle),
        "verbrauch": v_sum, "netz": sum(bil["netz"]), "direkt": sum(bil["direkt"]),
        "batterie": sum(bil["batterie"]), "pv_batt": sum(bil["pv_batt"]),
        "profil_verbrauch": profil_v,
        "autarkie": (100 * (1 - sum(bil["netz"]) / v_sum)) if v_sum > 0 else None,
        "autarkie_b": [(100 * (1 - bil["netz"][i] / bil["verbrauch"][i])) if bil["verbrauch"][i] > 0 else None
                       for i in range(n)],
        "eigen": (100 * max(pv_sum - a["einspeisung"]["summe"], 0.0) / pv_sum)
                 if pv_sum > 0 and a["einspeisung"]["vorhanden"] else None,
        "top_stunden": sorted(pv_stunden.items(), key=lambda kv: kv[1], reverse=True)[:5],
        "top_tage": sorted(pv_tage.items(), key=lambda kv: kv[1], reverse=True)[:5],
        "pro_id": pro_id,
    }


def _bucket(typ, start):
    if typ == "year":
        return 12, lambda t: t.month - 1
    n = 7 if typ == "week" else calendar.monthrange(start.year, start.month)[1]
    return n, lambda t: (t.date() - start).days


def auswerten(per, stats, monat_stat, quellen, tz, namen):
    """stats: {"cur": …, "vor": …, "vj": …} Stundenstatistik je Zeitraum."""
    typ = per["typ"]
    n, bf = _bucket(typ, per["start"])
    cur = _analyse(stats["cur"], quellen, per["start"], per["ende"], tz, n, bf)
    vs, ve = per["vor"]
    n_v, bf_v = _bucket(typ, vs)
    vor = _analyse(stats.get("vor") or {}, quellen, vs, ve, tz, n_v, bf_v)
    vj = None
    if per.get("vj"):
        js, je = per["vj"]
        n_j, bf_j = _bucket(typ, js)
        vj = _analyse(stats.get("vj") or {}, quellen, js, je, tz, n_j, bf_j)
    monate = None
    if monat_stat is not None:
        monate = {k: [0.0] * 12 for k in KATEGORIEN}
        for kat in KATEGORIEN:
            for sid in quellen.get(kat, []):
                for row in monat_stat.get(sid, []) or []:
                    if row.get("change") is None:
                        continue
                    t = _lokal(row["start"], tz)
                    if t.year == per["start"].year:
                        monate[kat][t.month - 1] += max(float(row["change"]), 0.0)
        monate["verbrauch"] = [max(monate["pv"][m] + monate["bezug"][m] + monate["entladen"][m]
                                   - monate["einspeisung"][m] - monate["laden"][m], 0.0) for m in range(12)]
    pv = cur["k"]["pv"]["b"]
    return {
        "per": per, "typ": typ, "n": n, "cur": cur, "vor": vor, "vj": vj, "monate": monate,
        "bester": max(range(n), key=lambda i: pv[i]), "schwaechster": min(range(n), key=lambda i: pv[i]),
        "quellen": [(namen.get(s, s), cur["pro_id"].get(s, 0.0)) for s in quellen.get("pv", [])],
        "verbrauch_da": bool(quellen.get("bezug")),
    }


def pct(neu, alt):
    if not alt:
        return None
    return (neu / alt - 1) * 100


def kennzahlen(d):
    """Kompakte Werte für die Berichtsliste."""
    c, v = d["cur"], d["vor"]
    k = c["k"]
    r = lambda x, n=1: round(x, n)
    da = lambda kat: k[kat]["vorhanden"]
    return {
        "pv": r(k["pv"]["summe"]) if da("pv") else None,
        "pv_vw": r(v["k"]["pv"]["summe"]) if da("pv") and v["daten_vorhanden"] else None,
        "verbrauch": r(c["verbrauch"]) if d["verbrauch_da"] else None,
        "autarkie": r(c["autarkie"], 0) if c["autarkie"] is not None else None,
        "bezug": r(k["bezug"]["summe"]) if da("bezug") else None,
        "einspeisung": r(k["einspeisung"]["summe"]) if da("einspeisung") else None,
        "batterie": r(k["entladen"]["summe"]) if da("entladen") else None,
        "wasser": r(k["wasser"]["summe"], 0) if da("wasser") else None,
    }


# ----------------------------------------------------------------------
# PDF
# ----------------------------------------------------------------------
def _latin(s):
    ersatz = {"–": "-", "—": "-", "→": "->", "€": "EUR", "≈": "~", "•": "·", "„": '"', "“": '"', "³": "3"}
    for a, b in ersatz.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def _nice_max(v):
    if v <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= v:
            return m * e
    return 10 * e


def titel_zeitraum(per, S):
    """Kurzbezeichnung des Zeitraums, z. B. 'KW 44 · 26.10. - 01.11.2026', 'Oktober 2026', 'Jahr 2025'."""
    if per["typ"] == "week":
        bis = per["ende"] - timedelta(days=1)
        return f"{S.t('KW {kw}', kw=per['kw'])} · {S.datum(per['start'])} - {S.datum(bis, True)}"
    if per["typ"] == "month":
        return f"{S.monat_lang(per['start'].month - 1)} {per['start'].year}"
    return S.t("Jahr {j}", j=per["start"].year)


def baue_pdf(d, pfad, anlagenname, kwp, erstellt, lang="de"):
    from fpdf import FPDF

    S = Sprache(lang)
    t, n = S.t, S.n
    typ, per, cur, vor, vj = d["typ"], d["per"], d["cur"], d["vor"], d["vj"]
    k, kv = cur["k"], vor["k"]
    N = d["n"]

    SOLAR = (206, 108, 0)
    SOLAR_DUNKEL = (164, 85, 2)
    SOLAR_ZART = (247, 219, 201)
    NETZ = (42, 120, 214)
    EINSP = (98, 80, 214)
    BATT = (232, 123, 164)
    BATT_HELL = (245, 196, 214)
    WASSER = (27, 175, 122)
    WASSER_HELL = (175, 227, 207)
    DUNKEL = (11, 11, 11)
    GRAU = (107, 106, 101)
    GRAU_HELL = (195, 194, 183)
    GRAU_ZART = (240, 239, 236)
    GRUEN = (8, 107, 8)
    ROT = (166, 42, 42)
    WEISS = (255, 255, 255)
    KOPF = (26, 26, 25)

    hat = {kat: k[kat]["vorhanden"] for kat in k}
    vor_name = {"week": "Vorwoche", "month": "Vormonat", "year": "Vorjahr"}[typ]
    vor_kurz = {"week": " ggü. VW", "month": " ggü. VM", "year": " ggü. VJ"}[typ]
    jetzt_name = {"week": "Diese Woche", "month": "Dieser Monat", "year": "Dieses Jahr"}[typ]
    berichtstitel = {"week": "Energie-Wochenbericht", "month": "Energie-Monatsbericht", "year": "Energie-Jahresbericht"}[typ]
    zeitraum_txt = titel_zeitraum(per, S)
    vor_da = vor["daten_vorhanden"]

    def label(i):
        if typ == "week":
            dd = per["start"] + timedelta(days=i)
            return f"{S.tag(i)} {S.datum(dd)}"
        if typ == "month":
            return str(i + 1)
        return S.monat(i)

    def label_lang(i):
        if typ == "week":
            return label(i)
        if typ == "month":
            dd = per["start"] + timedelta(days=i)
            return f"{S.tag(dd.weekday())} {S.datum(dd)}"
        return S.monat_lang(i)

    labels = [label(i) for i in range(N)]
    viele = N > 12

    class Bericht(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(*GRAU)
            self.cell(0, 5, _latin(t("Erstellt {t} · Quelle: Home Assistant Energie-Statistik", t=erstellt)), align="L")
            self.set_x(15)
            self.cell(0, 5, t("Seite {n}/{{nb}}", n=self.page_no()), align="R")

    pdf = Bericht(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.set_margins(15, 15, 15)
    pdf.alias_nb_pages()

    def logo(x, y, s):
        pdf.set_fill_color(*SOLAR)
        pdf.rect(x, y, s, s, style="F", round_corners=True, corner_radius=s * 7 / 32)
        f = s / 32
        pdf.set_fill_color(*WEISS)
        pdf.polygon([(x + 18 * f, y + 5 * f), (x + 9 * f, y + 18 * f), (x + 15 * f, y + 18 * f),
                     (x + 13 * f, y + 27 * f), (x + 23 * f, y + 13 * f), (x + 17 * f, y + 13 * f)], style="F")

    def kopf(titel, gross):
        h = 34 if gross else 22
        pdf.set_fill_color(*KOPF)
        pdf.rect(0, 0, 210, h, style="F")
        pdf.set_fill_color(*SOLAR)
        pdf.rect(0, h, 210, 1.2, style="F")
        s = 14 if gross else 10
        logo(195 - s, (h - s) / 2, s)
        pdf.set_text_color(*WEISS)
        if gross:
            pdf.set_font("Helvetica", "B", 21)
            pdf.text(15, 17, _latin(titel))
            pdf.set_font("Helvetica", "", 10.5)
            pdf.set_text_color(*GRAU_HELL)
            pdf.text(15, 25.5, _latin(f"{zeitraum_txt}  ·  {anlagenname}" if anlagenname else zeitraum_txt))
            return 44
        pdf.set_font("Helvetica", "B", 14)
        pdf.text(15, 12.5, _latin(titel))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GRAU_HELL)
        pdf.text(15, 18, _latin(zeitraum_txt))
        return 32

    erste = [True]
    akt_titel = [""]

    def neue_seite(titel):
        pdf.add_page()
        akt_titel[0] = titel
        y = kopf(titel, erste[0])
        erste[0] = False
        return y

    def platz(y, hoehe):
        if y + hoehe > 278:
            return neue_seite(f"{akt_titel[0]} ({t('Fortsetzung')})") + 4
        return y

    def abschnitt(y, titel, zusatz=None):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*DUNKEL)
        pdf.text(15, y, _latin(titel))
        breite = pdf.get_string_width(_latin(titel))
        if zusatz:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*GRAU)
            pdf.text(15 + breite + 4, y, _latin(zusatz))
        pdf.set_draw_color(*GRAU_ZART)
        pdf.set_line_width(0.3)
        pdf.line(15, y + 2, 195, y + 2)

    def kachel(x, y, w, h, lab, wert, sub, akzent, sub_farbe=GRAU):
        pdf.set_fill_color(252, 252, 251)
        pdf.set_draw_color(225, 224, 217)
        pdf.set_line_width(0.25)
        pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2.5)
        pdf.set_fill_color(*akzent)
        pdf.rect(x, y + 3, 1.2, h - 6, style="F")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(82, 81, 78)
        pdf.text(x + 4.5, y + 6.5, _latin(lab))
        pdf.set_font("Helvetica", "B", 14.5)
        pdf.set_text_color(*DUNKEL)
        pdf.text(x + 4.5, y + 15.3, _latin(wert))
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*sub_farbe)
        sub = _latin(sub)
        while pdf.get_string_width(sub) > w - 7 and len(sub) > 4:
            sub = sub[:-2]
        pdf.text(x + 4.5, y + 21.3, sub)

    def kachelreihen(y, kacheln):
        w, h, gap = 42, 25, 4
        for i, kd in enumerate(kacheln):
            reihe, spalte = divmod(i, 4)
            kachel(15 + spalte * (w + gap), y + reihe * (h + gap), w, h, *kd)
        return y + ((len(kacheln) + 3) // 4) * (h + gap) - gap

    def y_achse(x0, y0, w, h, vmax, schritte, einheit):
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_line_width(0.2)
        schritt = vmax / schritte
        if abs(schritt - round(schritt)) < 1e-9:
            dez = 0
        elif abs(schritt * 10 - round(schritt * 10)) < 1e-9:
            dez = 1
        else:
            dez = 2
        for i in range(schritte + 1):
            yy = y0 + h - h * i / schritte
            pdf.set_draw_color(*(GRAU_HELL if i == 0 else GRAU_ZART))
            pdf.line(x0, yy, x0 + w, yy)
            pdf.set_text_color(*GRAU)
            lab = n(schritt * i, dez)
            pdf.text(x0 - 1.5 - pdf.get_string_width(lab), yy + 1, lab)
        pdf.text(x0 - 10, y0 - 2.5, _latin(einheit))

    def legende(y, eintraege, x_rechts=195):
        pdf.set_font("Helvetica", "", 7.5)
        breite = sum(9 + pdf.get_string_width(_latin(tx)) for _, tx, _ in eintraege)
        x = x_rechts - breite + 2.5
        for farbe, text, linie in eintraege:
            if linie:
                pdf.set_draw_color(*farbe)
                pdf.set_line_width(0.6)
                pdf.line(x, y - 1, x + 5, y - 1)
            else:
                pdf.set_fill_color(*farbe)
                pdf.rect(x, y - 2.6, 3.2, 3.2, style="F")
            pdf.set_text_color(*GRAU)
            pdf.text(x + 6.5, y, _latin(text))
            x += 9 + pdf.get_string_width(_latin(text))

    def balken(x0, y0, w, h, serien, gestapelt=False, einheit="kWh", dez=1,
               beschriften=None, hervorheben=None, schritte=4, label_fett=None, labs=None):
        labs = labs or labels
        anz = len(labs)
        if gestapelt:
            werte_max = max(sum(s[2][i] for s in serien) for i in range(anz))
        else:
            werte_max = max(max(s[2][:anz] + [0]) for s in serien)
        vmax = _nice_max(werte_max * 1.14)
        y_achse(x0, y0, w, h, vmax, schritte, einheit)
        gw = w / anz
        werte_zeigen = anz <= 12
        for i in range(anz):
            gx = x0 + i * gw
            if gestapelt:
                bw = gw * (0.55 if anz <= 12 else 0.7)
                bx = gx + (gw - bw) / 2
                yy = y0 + h
                for _, farbe, werte in serien:
                    hh = h * werte[i] / vmax
                    if hh > 0.05:
                        pdf.set_fill_color(*farbe)
                        pdf.rect(bx, yy - hh, bw, hh, style="F")
                        yy -= hh
                if werte_zeigen:
                    total = sum(s[2][i] for s in serien)
                    pdf.set_font("Helvetica", "B", 6.8)
                    pdf.set_text_color(*DUNKEL)
                    lab = n(total, dez)
                    pdf.text(bx + bw / 2 - pdf.get_string_width(lab) / 2, yy - 1.4, lab)
            else:
                m = len(serien)
                innen = gw * (0.78 if m > 1 else (0.55 if anz <= 12 else 0.7))
                bw = innen / m
                for j, (_, farbe, werte) in enumerate(serien):
                    wert = werte[i] if i < len(werte) else 0.0
                    bx = gx + (gw - innen) / 2 + j * bw
                    hh = h * wert / vmax
                    f = farbe
                    if hervorheben and hervorheben[0] == j and hervorheben[1] == i:
                        f = hervorheben[2]
                    pdf.set_fill_color(*f)
                    pdf.rect(bx + bw * 0.06, y0 + h - hh, bw * 0.88, hh, style="F")
                    if werte_zeigen and (beschriften is None or j in beschriften) and round(wert, dez) > 0:
                        pdf.set_font("Helvetica", "B" if m == 1 or j == m - 1 else "", 6.5)
                        pdf.set_text_color(*(DUNKEL if m == 1 or j == m - 1 else GRAU))
                        lab = n(wert, dez)
                        pdf.text(bx + bw / 2 - pdf.get_string_width(lab) / 2, y0 + h - hh - 1.3, lab)
            fett = label_fett is not None and label_fett == i
            pdf.set_font("Helvetica", "B" if fett else "", 7.2 if anz <= 12 else 6.2)
            pdf.set_text_color(*(DUNKEL if fett else GRAU))
            lab = _latin(labs[i])
            pdf.text(gx + gw / 2 - pdf.get_string_width(lab) / 2, y0 + h + 4.8, lab)

    def profil(x0, y0, w, h, flaechen, linien, einheit="kWh"):
        alle = [x for _, _, werte in flaechen for x in werte] + [x for _, werte, _ in linien for x in werte]
        vmax = _nice_max(max(alle + [0]) * 1.1)
        y_achse(x0, y0, w, h, vmax, 4, einheit)
        sx = w / 24
        punkte = lambda werte: [(x0 + (s + 0.5) * sx, y0 + h - h * werte[s] / vmax) for s in range(24)]
        for fuell, linie, werte in flaechen:
            p = punkte(werte)
            pdf.set_fill_color(*fuell)
            pdf.polygon([(x0, y0 + h)] + p + [(x0 + w, y0 + h)], style="F")
            pdf.set_draw_color(*linie)
            pdf.set_line_width(0.5)
            pdf.polyline(p)
        for farbe, werte, gestrichelt in linien:
            pdf.set_draw_color(*farbe)
            pdf.set_line_width(0.5)
            if gestrichelt:
                pdf.set_dash_pattern(dash=1.2, gap=0.8)
            pdf.polyline(punkte(werte))
            pdf.set_dash_pattern()
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*GRAU)
        for s in range(0, 22, 3):
            lab = f"{s:02d}"
            pdf.text(x0 + s * sx - pdf.get_string_width(lab) / 2, y0 + h + 4.5, lab)
        lab = _latin(t("24 Uhr"))
        pdf.text(x0 + w - pdf.get_string_width(lab) / 2, y0 + h + 4.5, lab)

    def flussbalken(y, titel, teile):
        gesamt = sum(x[2] for x in teile) or 1
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*DUNKEL)
        pdf.text(15, y, _latin(titel))
        x = 15
        for _, farbe, wert in teile:
            ww = 180 * wert / gesamt
            if ww > 0:
                pdf.set_fill_color(*farbe)
                pdf.rect(x, y + 2, ww, 6, style="F")
                if ww > 14:
                    pdf.set_font("Helvetica", "B", 7)
                    pdf.set_text_color(*DUNKEL)
                    lab = f"{n(wert / gesamt * 100, 0)} %"
                    pdf.text(x + ww / 2 - pdf.get_string_width(lab) / 2, y + 6.1, lab)
            x += ww
        x = 15
        pdf.set_font("Helvetica", "", 7.5)
        for name, farbe, wert in teile:
            pdf.set_fill_color(*farbe)
            pdf.rect(x, y + 10.2, 3, 3, style="F")
            pdf.set_text_color(*GRAU)
            lab = _latin(f"{name} {n(wert)} kWh")
            pdf.text(x + 4.5, y + 12.7, lab)
            x += 10 + pdf.get_string_width(lab)

    def vgl(neu, alt_a):
        return S.pct(pct(neu, alt_a) if vor_da else None, vor_kurz)

    # ====================== Übersicht ======================
    v_da = d["verbrauch_da"]
    if v_da:
        y = neue_seite(t(berichtstitel))
        kacheln = []
        if hat["pv"]:
            kacheln.append((t("PV-Erzeugung"), f"{n(k['pv']['summe'])} kWh", vgl(k["pv"]["summe"], kv["pv"]["summe"]), SOLAR))
        kacheln.append((t("Hausverbrauch"), f"{n(cur['verbrauch'])} kWh",
                        t("Ø {v} kWh/Tag · {p}", v=n(cur["verbrauch"] / cur["tage"]),
                          p=S.pct(pct(cur["verbrauch"], vor["verbrauch"]) if vor_da else None)), GRAU))
        if cur["autarkie"] is not None:
            kacheln.append((t("Autarkie"), f"{n(cur['autarkie'], 0)} %", t("{v} kWh aus dem Netz", v=n(cur["netz"])), GRUEN))
        if cur["eigen"] is not None:
            kacheln.append((t("Eigenverbrauch"), f"{n(cur['eigen'], 0)} %", t("des PV-Stroms selbst genutzt"), SOLAR_DUNKEL))
        kacheln.append((t("Netzbezug"), f"{n(k['bezug']['summe'])} kWh", vgl(k["bezug"]["summe"], kv["bezug"]["summe"]), NETZ))
        if hat["einspeisung"]:
            kacheln.append((t("Einspeisung"), f"{n(k['einspeisung']['summe'])} kWh",
                            vgl(k["einspeisung"]["summe"], kv["einspeisung"]["summe"]), EINSP))
        if hat["laden"] or hat["entladen"]:
            kacheln.append((t("Batterie"), f"{n(k['entladen']['summe'])} kWh",
                            t("entladen · {v} kWh geladen", v=n(k["laden"]["summe"])), BATT))
        if hat["wasser"]:
            w_ = k["wasser"]
            kacheln.append((t("Wasser"), f"{n(w_['summe'], 0)} L",
                            t("Ø {v} L/Tag · {p}", v=n(w_["summe"] / cur["tage"], 0),
                              p=S.pct(pct(w_["summe"], kv["wasser"]["summe"]) if vor_da else None)), WASSER))
        y = kachelreihen(y, kacheln[:8]) + 12

        abschnitt(y, t("Woher kam der Strom?"), t("Hausverbrauch je Monat" if typ == "year" else "Hausverbrauch je Tag"))
        serien = []
        if hat["pv"]:
            serien.append((t("Solar direkt"), SOLAR, cur["bil"]["direkt"]))
        if hat["entladen"]:
            serien.append((t("Batterie"), BATT, cur["bil"]["batterie"]))
        serien.append((t("Netz"), NETZ, cur["bil"]["netz"]))
        legende(y, [(f, nm, False) for nm, f, _ in serien])
        balken(27, y + 10, 168, 44, serien, gestapelt=True, dez=0 if typ == "year" else 1)
        y += 70

        abschnitt(y, t("Erzeugung und Verbrauch im Tagesverlauf"), t("Ø kWh je Stunde"))
        leg = [(DUNKEL, t("Verbrauch"), True)]
        if hat["pv"]:
            leg.insert(0, (SOLAR, t("PV-Erzeugung"), False))
        legende(y, leg)
        profil(27, y + 10, 168, 32, [(SOLAR_ZART, SOLAR, k["pv"]["profil"])] if hat["pv"] else [],
               [(DUNKEL, cur["profil_verbrauch"], False)])
        y += 56

        if y < 245:
            abschnitt(y, t("Energieflüsse"))
            y += 9
            herkunft = [(t("Solar direkt"), SOLAR, cur["direkt"])]
            if hat["entladen"]:
                herkunft.append((t("Batterie"), BATT, cur["batterie"]))
            herkunft.append((t("Netz"), NETZ, cur["netz"]))
            flussbalken(y, t("Herkunft des Verbrauchs"), herkunft)
            if hat["pv"] and k["pv"]["summe"] > 0:
                y += 19
                verw = [(t("Direkt verbraucht"), SOLAR, cur["direkt"])]
                if hat["laden"]:
                    verw.append((t("In die Batterie"), BATT_HELL, cur["pv_batt"]))
                if hat["einspeisung"]:
                    verw.append((t("Eingespeist"), EINSP, k["einspeisung"]["summe"]))
                flussbalken(y, t("Verwendung des PV-Stroms"), verw)

    # ====================== PV ======================
    pv = k["pv"]
    if hat["pv"]:
        y = neue_seite(t("PV-Erzeugung"))
        b = d["bester"]
        p = pct(pv["summe"], kv["pv"]["summe"]) if vor_da else None
        kacheln = [
            (t("Erzeugung"), f"{n(pv['summe'])} kWh", t("Ø {v} kWh pro Tag", v=n(pv["summe"] / cur["tage"])), SOLAR),
            (t(vor_name), S.pct(p) if p is not None else "-", f"{t(vor_name)}: {n(kv['pv']['summe'])} kWh", SOLAR,
             GRAU if p is None else (GRUEN if p >= 0 else ROT)),
            (t("Bester Monat" if typ == "year" else "Bester Tag"), f"{n(pv['b'][b])} kWh", label_lang(b), SOLAR),
        ]
        if vj is not None:
            pj = pct(pv["summe"], vj["k"]["pv"]["summe"]) if vj["daten_vorhanden"] else None
            kacheln.append((t("Vorjahresmonat"), S.pct(pj) if pj is not None else "-",
                            f"{t('Vorjahresmonat')}: {n(vj['k']['pv']['summe'])} kWh" if vj["daten_vorhanden"] else t("keine Daten"),
                            SOLAR, GRAU if pj is None else (GRUEN if pj >= 0 else ROT)))
        elif kwp:
            kacheln.append((t("Spez. Ertrag"), n(pv["summe"] / kwp, 2 if typ == "week" else 1), f"kWh/kWp · {n(kwp, 1)} kWp", SOLAR))
        elif cur["top_stunden"]:
            ts, tv = cur["top_stunden"][0]
            kacheln.append((t("Spitzenstunde"), f"{n(tv, 2)} kWh",
                            t("{tag} {von}-{bis} Uhr", tag=f"{S.tag(ts.weekday())} {S.datum(ts.date())}",
                              von=f"{ts.hour:02d}", bis=f"{ts.hour + 1:02d}"), SOLAR))
        y = kachelreihen(y, kacheln) + 13

        abschnitt(y, t("Monatsertrag" if typ == "year" else "Tagesertrag"))
        if typ == "month" and vj is not None:
            serien = [(t("Vorjahresmonat"), GRAU_HELL, vj["k"]["pv"]["b"]), (t(jetzt_name), SOLAR, pv["b"])]
        elif typ == "month":
            serien = [(t(jetzt_name), SOLAR, pv["b"])]
        else:
            serien = [(t(vor_name), GRAU_HELL, kv["pv"]["b"]), (t(jetzt_name), SOLAR, pv["b"])]
        legende(y, [(f, nm, False) for nm, f, _ in serien])
        balken(27, y + 10, 168, 44, serien, beschriften={len(serien) - 1},
               hervorheben=(len(serien) - 1, b, SOLAR_DUNKEL), dez=0 if typ == "year" else 1)
        y += 70

        abschnitt(y, t("Durchschnittliches Tagesprofil"), t("Ø kWh je Stunde"))
        legende(y, [(SOLAR, t(jetzt_name), False), (GRAU, t(vor_name), True)])
        profil(27, y + 10, 168, 32, [(SOLAR_ZART, SOLAR, pv["profil"])],
               [(GRAU, kv["pv"]["profil"], True)] if vor_da else [])
        y += 56

        if d["monate"] is not None:
            mo = d["monate"]
            zusatz = t("PV bisher {v} kWh", v=n(sum(mo["pv"]), 0))
            serien = [(t("PV-Erzeugung"), SOLAR, mo["pv"])]
            if v_da:
                zusatz += t(" · Verbrauch {v} kWh", v=n(sum(mo["verbrauch"]), 0))
                serien.append((t("Verbrauch"), GRAU_HELL, mo["verbrauch"]))
            abschnitt(y, t("Jahresverlauf {jahr}", jahr=per["start"].year), zusatz)
            legende(y, [(f, nm, False) for nm, f, _ in serien])
            balken(27, y + 10, 168, 36, serien, dez=0, schritte=2, beschriften={0},
                   label_fett=per["start"].month - 1, labs=[S.monat(m) for m in range(12)])
        elif typ == "year" and v_da:
            abschnitt(y, t("Autarkie"), t("Monatswerte"))
            werte = [a or 0.0 for a in cur["autarkie_b"]]
            balken(27, y + 10, 168, 36, [(t("Autarkie"), SOLAR_DUNKEL, werte)], einheit="%", dez=0, schritte=2)

    # ====================== Netz / Batterie / Wasser ======================
    bereiche = []
    if hat["bezug"] or hat["einspeisung"]:
        bereiche.append("netz")
    if hat["laden"] or hat["entladen"]:
        bereiche.append("batterie")
    if hat["wasser"]:
        bereiche.append("wasser")
    dez_b = 0 if typ == "year" else 1
    if bereiche:
        namen_b = {"netz": t("Netz"), "batterie": t("Batterie"), "wasser": t("Wasser")}
        y = neue_seite(" · ".join(namen_b[x] for x in bereiche)) + 4
        for bereich in bereiche:
            if bereich == "netz":
                serien, zus = [], []
                if hat["bezug"]:
                    serien.append((t("Netzbezug"), NETZ, k["bezug"]["b"]))
                    zus.append(t("Bezug {v} kWh", v=n(k["bezug"]["summe"])))
                if hat["einspeisung"]:
                    serien.append((t("Einspeisung"), EINSP, k["einspeisung"]["b"]))
                    zus.append(t("Einspeisung {v} kWh", v=n(k["einspeisung"]["summe"])))
                if hat["bezug"] and hat["einspeisung"]:
                    saldo = k["einspeisung"]["summe"] - k["bezug"]["summe"]
                    zus.append(t("Saldo {v} kWh", v=f"{'+' if saldo >= 0 else ''}{n(saldo)}"))
                abschnitt(y, t("Netz"), " · ".join(zus))
                legende(y + 7, [(f, nm, False) for nm, f, _ in serien])
                balken(27, y + 15, 168, 40, serien, dez=dez_b)
            elif bereich == "batterie":
                serien = []
                if hat["laden"]:
                    serien.append((t("Geladen"), BATT_HELL, k["laden"]["b"]))
                if hat["entladen"]:
                    serien.append((t("Entladen"), BATT, k["entladen"]["b"]))
                zus = t("geladen {a} kWh · entladen {b} kWh", a=n(k["laden"]["summe"]), b=n(k["entladen"]["summe"]))
                if k["laden"]["summe"] > 0 and hat["entladen"]:
                    zus += t(" · Verhältnis entladen/geladen {v} %", v=n(k["entladen"]["summe"] / k["laden"]["summe"] * 100, 0))
                abschnitt(y, t("Batterie"), zus)
                legende(y + 7, [(f, nm, False) for nm, f, _ in serien])
                balken(27, y + 15, 168, 40, serien, dez=dez_b)
            else:
                w_ = k["wasser"]
                abschnitt(y, t("Wasser"), f"{n(w_['summe'], 0)} L · {n(w_['summe'] / 1000, 2)} {t('Kubikmeter')} · "
                                          f"{S.pct(pct(w_['summe'], kv['wasser']['summe']) if vor_da else None, vor_kurz)}")
                if typ == "month":
                    serien = [(t(jetzt_name), WASSER, w_["b"])]
                else:
                    serien = [(t(vor_name), GRAU_HELL, kv["wasser"]["b"]), (t(jetzt_name), WASSER, w_["b"])]
                legende(y + 7, [(f, nm, False) for nm, f, _ in serien])
                balken(27, y + 15, 168, 40, serien, einheit=t("Liter"), dez=0, beschriften={len(serien) - 1})
            y += 76
        if hat["wasser"] and y < 230:
            w_ = k["wasser"]
            abschnitt(y, t("Wasser im Tagesverlauf"), t("Ø Liter je Stunde"))
            legende(y, [(WASSER, t(jetzt_name), False), (GRAU, t(vor_name), True)])
            profil(27, y + 10, 168, 28, [(WASSER_HELL, WASSER, w_["profil"])],
                   [(GRAU, kv["wasser"]["profil"], True)] if vor_da else [], einheit=t("Liter"))

    # ====================== Details ======================
    y = neue_seite(t("Details")) + 4
    abschnitt(y, t("Monatswerte" if typ == "year" else "Tageswerte"))
    spalten = [("Tag" if typ != "year" else "Monat", None)]
    if hat["pv"]:
        spalten.append(("PV", lambda i: n(pv["b"][i])))
    if v_da:
        spalten.append(("Verbrauch", lambda i: n(cur["bil"]["verbrauch"][i])))
    if hat["bezug"]:
        spalten.append(("Netzbezug", lambda i: n(k["bezug"]["b"][i])))
    if hat["einspeisung"]:
        spalten.append(("Einspeis.", lambda i: n(k["einspeisung"]["b"][i])))
    if hat["laden"]:
        spalten.append(("Bat. +", lambda i: n(k["laden"]["b"][i])))
    if hat["entladen"]:
        spalten.append(("Bat. -", lambda i: n(k["entladen"]["b"][i])))
    if v_da:
        spalten.append(("Autarkie", lambda i: "-" if cur["autarkie_b"][i] is None else f"{n(cur['autarkie_b'][i], 0)} %"))
    if hat["wasser"]:
        spalten.append(("Wasser L", lambda i: n(k["wasser"]["b"][i], 0)))
    erste_breite = 30
    rest = (180 - erste_breite) / max(len(spalten) - 1, 1)
    breiten = [erste_breite] + [rest] * (len(spalten) - 1)
    zh = 6.5 if N <= 12 else 6.0

    def tabellenkopf(y, kopfzeilen, br):
        pdf.set_fill_color(*KOPF)
        pdf.rect(15, y, 180, 7, style="F")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*WEISS)
        x = 15
        for i, (name, sw) in enumerate(zip(kopfzeilen, br)):
            pdf.set_xy(x + 1.5, y)
            pdf.cell(sw - 3, 7, _latin(name), align="L" if i == 0 else "R")
            x += sw
        return y + 7

    def zeile(y, texte, br, fett=False, hintergrund=None, farben=None, h=6.5):
        if hintergrund:
            pdf.set_fill_color(*hintergrund)
            pdf.rect(15, y, 180, h, style="F")
        x = 15
        for i, (sw, text) in enumerate(zip(br, texte)):
            pdf.set_font("Helvetica", "B" if fett else "", 8.5 if h >= 6.5 else 8)
            pdf.set_text_color(*((farben or {}).get(i, DUNKEL)))
            pdf.set_xy(x + 1.5, y)
            pdf.cell(sw - 3, h, _latin(text), align="L" if i == 0 else "R")
            x += sw
        return y + h

    y = tabellenkopf(y + 6, [t(s[0]) for s in spalten], breiten)
    for i in range(N):
        y = zeile(y, [label_lang(i)] + [s[1](i) for s in spalten[1:]], breiten,
                  hintergrund=GRAU_ZART if i % 2 else None, h=zh)
    summen = {"PV": n(pv["summe"]), "Verbrauch": n(cur["verbrauch"]),
              "Netzbezug": n(k["bezug"]["summe"]), "Einspeis.": n(k["einspeisung"]["summe"]),
              "Bat. +": n(k["laden"]["summe"]), "Bat. -": n(k["entladen"]["summe"]),
              "Autarkie": "-" if cur["autarkie"] is None else f"{n(cur['autarkie'], 0)} %",
              "Wasser L": n(k["wasser"]["summe"], 0)}
    pdf.set_draw_color(*SOLAR)
    pdf.set_line_width(0.5)
    pdf.line(15, y, 195, y)
    y = zeile(y, [t("Summe")] + [summen[s[0]] for s in spalten[1:]], breiten, fett=True, hintergrund=SOLAR_ZART)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*GRAU)
    pdf.text(15, y + 4, _latin(t("Energiewerte in kWh. Bat. + = in die Batterie geladen, Bat. - = aus der Batterie entnommen.")))
    y += 14

    # --- Vergleich ---
    vgl_spalten = [(t(vor_name), vor)]
    if vj is not None:
        vgl_spalten.append((t("Vorjahresmonat"), vj))
    zeilen = []

    def zeilenwert(name, f, dez=1, einheit="kWh", prozent=False):
        werte = [f(cur)] + [f(x) if x["daten_vorhanden"] else None for _, x in vgl_spalten]
        zeilen.append((name, werte, dez, einheit, prozent))

    if hat["pv"]:
        zeilenwert(t("PV-Erzeugung"), lambda x: x["k"]["pv"]["summe"])
    if v_da:
        zeilenwert(t("Hausverbrauch"), lambda x: x["verbrauch"])
        zeilenwert(t("Netzbezug"), lambda x: x["k"]["bezug"]["summe"])
    if hat["einspeisung"]:
        zeilenwert(t("Einspeisung"), lambda x: x["k"]["einspeisung"]["summe"])
    if hat["entladen"]:
        zeilenwert(t("Batterie entladen"), lambda x: x["k"]["entladen"]["summe"])
    if v_da:
        zeilenwert(t("Autarkie"), lambda x: x["autarkie"], dez=0, einheit="%", prozent=True)
    if hat["wasser"]:
        zeilenwert(t("Wasser"), lambda x: x["k"]["wasser"]["summe"], dez=0, einheit="L")

    hoehe = 14 + 7 + 6.5 * len(zeilen)
    y = platz(y, hoehe)
    abschnitt(y, t("Vergleich"))
    kz = [t("Kennzahl"), titel_zeitraum(per, S) if typ != "week" else t("KW {kw}", kw=per["kw"])]
    for name, _ in vgl_spalten:
        kz += [name, t("Änderung")]
    br = [46] + [(180 - 46) / (len(kz) - 1)] * (len(kz) - 1)
    y = tabellenkopf(y + 6, kz, br)
    for i, (name, werte, dez, einheit, prozent) in enumerate(zeilen):
        fmt = lambda v: "-" if v is None else f"{n(v, dez)} {einheit}"
        texte, farben = [name, fmt(werte[0])], {}
        for j in range(1, len(werte)):
            texte.append(fmt(werte[j]) if werte[j] is not None else t("keine Daten"))
            if werte[j] is None or werte[0] is None:
                texte.append("-")
            elif prozent:
                dv = werte[0] - werte[j]
                texte.append(f"{'+' if dv >= 0 else ''}{n(dv, 0)} {t('%-Pkt.')}")
            else:
                pc = pct(werte[0], werte[j])
                texte.append("-" if pc is None else f"{'+' if pc >= 0 else ''}{n(pc, 0)} %")
        y = zeile(y, texte, br, hintergrund=GRAU_ZART if i % 2 else None, farben=farben)
    y += 10

    if hat["pv"] and d["quellen"]:
        y = platz(y, 14 + 7.5 * len(d["quellen"]))
        abschnitt(y, t("PV-Erzeugung nach Quelle"))
        y += 7
        gesamt = pv["summe"] or 1
        for name, wert in d["quellen"]:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*DUNKEL)
            nm = _latin(name)
            kurz = nm
            while pdf.get_string_width(kurz) > 62 and len(kurz) > 4:
                kurz = kurz[:-2]
            pdf.text(15, y + 4, kurz if kurz == nm else kurz + "...")
            pdf.set_fill_color(*GRAU_ZART)
            pdf.rect(80, y + 1, 80, 4, style="F")
            pdf.set_fill_color(*SOLAR)
            pdf.rect(80, y + 1, 80 * wert / gesamt, 4, style="F")
            pdf.set_font("Helvetica", "B", 9)
            lab = f"{n(wert)} kWh"
            pdf.text(195 - pdf.get_string_width(lab), y + 4, lab)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*GRAU)
            pdf.text(163, y + 4, f"{n(wert / gesamt * 100, 0)} %")
            y += 7.5
        y += 7

        top = cur["top_stunden"] if typ == "week" else cur["top_tage"]
        if top:
            y = platz(y, 14 + 7.5 * len(top))
            abschnitt(y, t("Ertragsstärkste PV-Stunden" if typ == "week" else "Ertragsstärkste PV-Tage"))
            y += 7
            for rang, (wann, wert) in enumerate(top, 1):
                pdf.set_fill_color(*(SOLAR if rang == 1 else SOLAR_ZART))
                pdf.ellipse(15, y, 5.5, 5.5, style="F")
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(*DUNKEL)
                pdf.text(15 + 2.75 - pdf.get_string_width(str(rang)) / 2, y + 3.9, str(rang))
                pdf.set_font("Helvetica", "", 9)
                if typ == "week":
                    txt = t("{tag}, {datum}  {von}:00 - {bis}:00 Uhr", tag=S.tag(wann.weekday()),
                            datum=S.datum(wann.date()), von=f"{wann.hour:02d}", bis=f"{wann.hour + 1:02d}")
                else:
                    txt = f"{S.tag(wann.weekday())}, {S.datum(wann, True)}"
                pdf.text(24, y + 4, _latin(txt))
                pdf.set_font("Helvetica", "B", 9)
                lab = f"{n(wert, 2 if typ == 'week' else 1)} kWh"
                pdf.text(120 - pdf.get_string_width(lab), y + 4, lab)
                y += 7.5
            y += 7

    # --- Kurzfazit ---
    saetze = []
    wann = {"week": t("in KW {kw}", kw=per.get("kw")), "month": t("im {m}", m=titel_zeitraum(per, S)),
            "year": t("im Jahr {j}", j=per["start"].year)}[typ]
    vor_dat = {"week": "der Vorwoche", "month": "dem Vormonat", "year": "dem Vorjahr"}[typ]
    if hat["pv"]:
        b, s = d["bester"], d["schwaechster"]
        p = pct(pv["summe"], kv["pv"]["summe"]) if vor_da else None
        saetze.append(t("Die PV-Anlage hat {wann} {v} kWh erzeugt", wann=wann, v=n(pv["summe"]))
                      + (t(" ({p} gegenüber {vor}).", p=S.pct(p), vor=t(vor_dat)) if p is not None else "."))
        saetze.append(t("Stärkster {e} war {a} ({av} kWh), schwächster {b} ({bv} kWh).",
                        e=t("Monat" if typ == "year" else "Tag"), a=label_lang(b), av=n(pv["b"][b]),
                        b=label_lang(s), bv=n(pv["b"][s])))
        if vj is not None and vj["daten_vorhanden"]:
            saetze.append(t("Im Vergleich zum Vorjahresmonat lag die PV-Erzeugung bei {p}.",
                            p=S.pct(pct(pv["summe"], vj["k"]["pv"]["summe"]))))
    if v_da:
        saetze.append(t("Im Haus wurden {v} kWh verbraucht, davon kamen {n} kWh aus dem Netz",
                        v=n(cur["verbrauch"]), n=n(cur["netz"]))
                      + (t(", die Autarkie lag bei {a} %.", a=n(cur["autarkie"], 0)) if cur["autarkie"] is not None else "."))
    if cur["eigen"] is not None:
        saetze.append(t("{e} % des PV-Stroms wurden selbst genutzt, {x} kWh gingen ins Netz.",
                        e=n(cur["eigen"], 0), x=n(k["einspeisung"]["summe"])))
    if hat["laden"] or hat["entladen"]:
        saetze.append(t("Die Batterie hat {a} kWh aufgenommen und {b} kWh abgegeben.",
                        a=n(k["laden"]["summe"]), b=n(k["entladen"]["summe"])))
    if hat["wasser"]:
        p = pct(k["wasser"]["summe"], kv["wasser"]["summe"]) if vor_da else None
        saetze.append(t("Der Wasserverbrauch lag bei {v} Litern", v=n(k["wasser"]["summe"], 0))
                      + (t(" ({p} gegenüber {vor}).", p=S.pct(p), vor=t(vor_dat)) if p is not None else "."))
    y = platz(y, 40)
    abschnitt(y, t("Kurzfazit"))
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*DUNKEL)
    pdf.set_xy(15, y + 5)
    pdf.multi_cell(180, 5.2, _latin(" ".join(saetze)), align="L")

    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    pdf.output(pfad)
    return pfad
