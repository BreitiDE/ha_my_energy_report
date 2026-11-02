"""Auswertung der Energie-Statistik und Erzeugung des PDF-Berichts (Deutsch/Englisch)."""

import math
import os
from datetime import datetime, timedelta, timezone

KATEGORIEN = ["pv", "bezug", "einspeisung", "laden", "entladen", "wasser"]

TAGE = {"de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
MONATE = {"de": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
          "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]}

EN = {
    "Energie-Wochenbericht": "Weekly Energy Report",
    "PV-Erzeugung": "Solar production",
    "Hausverbrauch": "Home consumption",
    "Autarkie": "Self-sufficiency",
    "Eigenverbrauch": "Self-consumption",
    "Netzbezug": "Grid import",
    "Einspeisung": "Grid export",
    "Batterie": "Battery",
    "Wasser": "Water",
    "Netz": "Grid",
    "Solar direkt": "Solar direct",
    "Woher kam der Strom?": "Where did the power come from?",
    "Hausverbrauch je Tag": "Home consumption per day",
    "Erzeugung und Verbrauch im Tagesverlauf": "Production and consumption by hour",
    "Ø kWh je Stunde": "avg. kWh per hour",
    "Ø Liter je Stunde": "avg. litres per hour",
    "Verbrauch": "Consumption",
    "Energieflüsse der Woche": "Energy flows this week",
    "Herkunft des Verbrauchs": "Source of consumption",
    "Verwendung des PV-Stroms": "Use of solar power",
    "Direkt verbraucht": "Used directly",
    "In die Batterie": "Into battery",
    "Eingespeist": "Exported",
    "Erzeugung": "Production",
    "Vorwoche": "Previous week",
    "Diese Woche": "This week",
    "Bester Tag": "Best day",
    "Spez. Ertrag": "Specific yield",
    "Spitzenstunde": "Peak hour",
    "Tagesertrag": "Daily yield",
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
    "Tag": "Day",
    "Summe": "Total",
    "Einspeis.": "Export",
    "Bat. +": "Bat. +",
    "Bat. -": "Bat. -",
    "Wasser L": "Water L",
    "Energiewerte in kWh. Bat. + = in die Batterie geladen, Bat. - = aus der Batterie entnommen.":
        "Energy values in kWh. Bat. + = charged into the battery, Bat. - = taken from the battery.",
    "PV-Erzeugung nach Quelle": "Solar production by source",
    "Ertragsstärkste PV-Stunden": "Strongest solar hours",
    "Kurzfazit": "Summary",
    "Netz · Batterie · Wasser": "Grid · Battery · Water",
    "Ø {v} kWh pro Tag": "avg. {v} kWh per day",
    "Ø {v} kWh/Tag · {p}": "avg. {v} kWh/day · {p}",
    "Ø {v} L/Tag · {p}": "avg. {v} L/day · {p}",
    "{v} kWh aus dem Netz": "{v} kWh from the grid",
    "des PV-Stroms selbst genutzt": "of solar power used on site",
    "entladen · {v} kWh geladen": "discharged · {v} kWh charged",
    "Vorwoche: {v} kWh": "Previous week: {v} kWh",
    " ggü. VW": " vs. prev. week",
    " ggü. Vorwoche": " vs. previous week",
    " zur Vorwoche": " vs. previous week",
    "keine Vergleichsdaten": "no comparison data",
    "{tag} {von}-{bis} Uhr": "{tag} {von}-{bis}",
    "{tag}, {datum}  {von}:00 - {bis}:00 Uhr": "{tag}, {datum}  {von}:00 - {bis}:00",
    "24 Uhr": "24 h",
    "Erstellt {t} · Quelle: Home Assistant Energie-Statistik": "Created {t} · Source: Home Assistant energy statistics",
    "Seite {n}/{{nb}}": "Page {n}/{{nb}}",
    "KW {kw}": "Week {kw}",
    "Die PV-Anlage hat in KW {kw} {v} kWh erzeugt": "The solar system produced {v} kWh in week {kw}",
    " ({p} gegenüber der Vorwoche).": " ({p} compared to the previous week).",
    "Stärkster Tag war {a} ({av} kWh), schwächster {b} ({bv} kWh).":
        "The best day was {a} ({av} kWh), the weakest {b} ({bv} kWh).",
    "Im Haus wurden {v} kWh verbraucht, davon kamen {n} kWh aus dem Netz":
        "The home used {v} kWh, of which {n} kWh came from the grid",
    ", die Autarkie lag bei {a} %.": ", self-sufficiency was {a} %.",
    "{e} % des PV-Stroms wurden selbst genutzt, {x} kWh gingen ins Netz.":
        "{e} % of the solar power was used on site, {x} kWh went to the grid.",
    "Die Batterie hat {a} kWh aufgenommen und {b} kWh abgegeben.":
        "The battery took in {a} kWh and delivered {b} kWh.",
    "Der Wasserverbrauch lag bei {v} Litern": "Water consumption was {v} litres",
    "Kubikmeter": "cubic metres",
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

    def datum(self, d, jahr=False):
        if self.lang == "en":
            return d.strftime("%d/%m/%Y" if jahr else "%d/%m")
        return d.strftime("%d.%m.%Y" if jahr else "%d.%m.")

    def pct(self, p, suffix=""):
        if p is None:
            return self.t("keine Vergleichsdaten")
        return f"{'+' if p >= 0 else ''}{self.n(p, 0)} %{self.t(suffix) if suffix else ''}"


# ----------------------------------------------------------------------
# Quellen und Zeitraum
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


def zeitraum(montag, tz):
    """montag: date des ersten Tags der Berichtswoche."""
    mk = lambda d: datetime(d.year, d.month, d.day, tzinfo=tz)
    return {
        "start": mk(montag), "ende": mk(montag + timedelta(days=7)),
        "vorwoche_start": mk(montag - timedelta(days=7)),
        "jahr_start": datetime(montag.year, 1, 1, tzinfo=tz),
        "jahr": montag.year, "kw": montag.isocalendar()[1],
    }


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
def _bilanz(k, schluessel):
    tage = {n: [0.0] * 7 for n in ("verbrauch", "direkt", "batterie", "netz", "pv_batt")}
    profil = [0.0] * 24
    for i in range(7):
        for h in range(24):
            g = lambda kat: k[kat][schluessel].get((i, h), 0.0)
            pv, bz, es, la, en = g("pv"), g("bezug"), g("einspeisung"), g("laden"), g("entladen")
            verbrauch = max(pv + bz + en - es - la, 0.0)
            pv_batt = min(la, max(pv - es, 0.0))
            direkt = min(max(pv - es - pv_batt, 0.0), verbrauch)
            batt = min(en, verbrauch - direkt)
            netz = max(verbrauch - direkt - batt, 0.0)
            tage["verbrauch"][i] += verbrauch
            tage["direkt"][i] += direkt
            tage["batterie"][i] += batt
            tage["netz"][i] += netz
            tage["pv_batt"][i] += pv_batt
            profil[h] += verbrauch / 7
    return tage, profil


def auswerten(stat, jahr_stat, quellen, zr, tz, namen):
    start_d = zr["start"].date()
    vw_d = zr["vorwoche_start"].date()
    k = {}
    for kat in KATEGORIEN:
        a = {"tage": [0.0] * 7, "tage_vw": [0.0] * 7, "std": {}, "std_vw": {},
             "monate": [0.0] * 12, "pro_id": {}}
        for sid in quellen.get(kat, []):
            a["pro_id"][sid] = 0.0
            for row in stat.get(sid, []) or []:
                ch = row.get("change")
                if ch is None:
                    continue
                ch = max(float(ch), 0.0)
                t = _lokal(row["start"], tz)
                if t >= zr["start"]:
                    i = (t.date() - start_d).days
                    if 0 <= i < 7:
                        a["tage"][i] += ch
                        a["std"][(i, t.hour)] = a["std"].get((i, t.hour), 0.0) + ch
                        a["pro_id"][sid] += ch
                elif t >= zr["vorwoche_start"]:
                    i = (t.date() - vw_d).days
                    if 0 <= i < 7:
                        a["tage_vw"][i] += ch
                        a["std_vw"][(i, t.hour)] = a["std_vw"].get((i, t.hour), 0.0) + ch
            for row in jahr_stat.get(sid, []) or []:
                ch = row.get("change")
                if ch is None:
                    continue
                t = _lokal(row["start"], tz)
                if t.year == zr["jahr"]:
                    a["monate"][t.month - 1] += max(float(ch), 0.0)
        a["summe"] = sum(a["tage"])
        a["summe_vw"] = sum(a["tage_vw"])
        a["vorhanden"] = bool(quellen.get(kat))
        a["profil"] = [sum(a["std"].get((i, h), 0.0) for i in range(7)) / 7 for h in range(24)]
        a["profil_vw"] = [sum(a["std_vw"].get((i, h), 0.0) for i in range(7)) / 7 for h in range(24)]
        a["quellen"] = [(namen.get(s, s), v) for s, v in sorted(a["pro_id"].items(), key=lambda kv: -kv[1])]
        k[kat] = a

    pv = k["pv"]
    pv["bester"] = max(range(7), key=lambda i: pv["tage"][i])
    pv["schwaechster"] = min(range(7), key=lambda i: pv["tage"][i])
    pv["top"] = sorted(pv["std"].items(), key=lambda kv: kv[1], reverse=True)[:5]

    bil, profil_v = _bilanz(k, "std")
    bil_vw, _ = _bilanz(k, "std_vw")
    monate_v = [max(k["pv"]["monate"][m] + k["bezug"]["monate"][m] + k["entladen"]["monate"][m]
                    - k["einspeisung"]["monate"][m] - k["laden"]["monate"][m], 0.0) for m in range(12)]
    v_sum = sum(bil["verbrauch"])
    verbrauch = {
        "vorhanden": k["bezug"]["vorhanden"],
        "tage": bil["verbrauch"], "tage_vw": bil_vw["verbrauch"],
        "summe": v_sum, "summe_vw": sum(bil_vw["verbrauch"]),
        "direkt": bil["direkt"], "batterie": bil["batterie"], "netz": bil["netz"],
        "summe_direkt": sum(bil["direkt"]), "summe_batterie": sum(bil["batterie"]),
        "summe_netz": sum(bil["netz"]),
        "profil": profil_v, "monate": monate_v,
        "autarkie": (100 * (1 - sum(bil["netz"]) / v_sum)) if v_sum > 0 else None,
        "autarkie_tage": [(100 * (1 - bil["netz"][i] / bil["verbrauch"][i])) if bil["verbrauch"][i] > 0 else None
                          for i in range(7)],
        "pv_batt": sum(bil["pv_batt"]),
    }
    eig = None
    if pv["summe"] > 0 and k["einspeisung"]["vorhanden"]:
        eig = 100 * max(pv["summe"] - k["einspeisung"]["summe"], 0.0) / pv["summe"]

    daten = [start_d + timedelta(days=i) for i in range(7)]
    return {
        "kw": zr["kw"], "jahr": zr["jahr"], "monat_aktuell": zr["start"].month,
        "von": daten[0], "bis": daten[6], "daten": daten,
        "k": k, "verbrauch": verbrauch, "eigenverbrauch": eig,
    }


def pct(neu, alt):
    if not alt:
        return None
    return (neu / alt - 1) * 100


def kennzahlen(d):
    """Kompakte Werte fuer die Berichtsliste."""
    k, v = d["k"], d["verbrauch"]
    r = lambda x, n=1: round(x, n)
    return {
        "pv": r(k["pv"]["summe"]) if k["pv"]["vorhanden"] else None,
        "pv_vw": r(k["pv"]["summe_vw"]) if k["pv"]["vorhanden"] else None,
        "verbrauch": r(v["summe"]) if v["vorhanden"] else None,
        "autarkie": r(v["autarkie"], 0) if v["autarkie"] is not None else None,
        "bezug": r(k["bezug"]["summe"]) if k["bezug"]["vorhanden"] else None,
        "einspeisung": r(k["einspeisung"]["summe"]) if k["einspeisung"]["vorhanden"] else None,
        "batterie": r(k["entladen"]["summe"]) if k["entladen"]["vorhanden"] else None,
        "wasser": r(k["wasser"]["summe"], 0) if k["wasser"]["vorhanden"] else None,
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


def baue_pdf(d, pfad, anlagenname, kwp, erstellt, lang="de"):
    from fpdf import FPDF

    S = Sprache(lang)
    t, n = S.t, S.n

    # Farben: Akzent laut Styleguide, Serien angelehnt an das Energie-Dashboard
    SOLAR = (206, 108, 0)
    SOLAR_DUNKEL = (164, 85, 2)
    SOLAR_HELL = (237, 183, 146)
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

    k = d["k"]
    v = d["verbrauch"]
    pv = k["pv"]
    hat = {kat: k[kat]["vorhanden"] for kat in k}

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
    zeitraum_txt = f"{t('KW {kw}', kw=d['kw'])} · {S.datum(d['von'])} - {S.datum(d['bis'], True)}"
    tageslabels = [f"{S.tag(i)} {S.datum(d['daten'][i])}" for i in range(7)]

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
            pdf.text(15, 25.5, _latin(f"{zeitraum_txt}  ·  {anlagenname}"))
            return 44
        pdf.set_font("Helvetica", "B", 14)
        pdf.text(15, 12.5, _latin(titel))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GRAU_HELL)
        pdf.text(15, 18, _latin(zeitraum_txt))
        return 32

    erste = [True]

    def neue_seite(titel):
        pdf.add_page()
        y = kopf(titel, erste[0])
        erste[0] = False
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

    def kachel(x, y, w, h, label, wert, sub, akzent, sub_farbe=GRAU):
        pdf.set_fill_color(252, 252, 251)
        pdf.set_draw_color(225, 224, 217)
        pdf.set_line_width(0.25)
        pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2.5)
        pdf.set_fill_color(*akzent)
        pdf.rect(x, y + 3, 1.2, h - 6, style="F")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(82, 81, 78)
        pdf.text(x + 4.5, y + 6.5, _latin(label))
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

    def balken(x0, y0, w, h, labels, serien, gestapelt=False, einheit="kWh", dez=1,
               beschriften=None, hervorheben=None, schritte=4, label_fett=None):
        anz = len(labels)
        if gestapelt:
            werte_max = max(sum(s[2][i] for s in serien) for i in range(anz))
        else:
            werte_max = max(max(s[2]) for s in serien)
        vmax = _nice_max(werte_max * 1.14)
        y_achse(x0, y0, w, h, vmax, schritte, einheit)
        gw = w / anz
        for i in range(anz):
            gx = x0 + i * gw
            if gestapelt:
                bw = gw * 0.55
                bx = gx + (gw - bw) / 2
                yy = y0 + h
                for _, farbe, werte in serien:
                    hh = h * werte[i] / vmax
                    if hh > 0.05:
                        pdf.set_fill_color(*farbe)
                        pdf.rect(bx, yy - hh, bw, hh, style="F")
                        yy -= hh
                total = sum(s[2][i] for s in serien)
                pdf.set_font("Helvetica", "B", 6.8)
                pdf.set_text_color(*DUNKEL)
                lab = n(total, dez)
                pdf.text(bx + bw / 2 - pdf.get_string_width(lab) / 2, yy - 1.4, lab)
            else:
                m = len(serien)
                innen = gw * (0.78 if m > 1 else 0.55)
                bw = innen / m
                for j, (_, farbe, werte) in enumerate(serien):
                    bx = gx + (gw - innen) / 2 + j * bw
                    hh = h * werte[i] / vmax
                    f = farbe
                    if hervorheben and hervorheben[0] == j and hervorheben[1] == i:
                        f = hervorheben[2]
                    pdf.set_fill_color(*f)
                    pdf.rect(bx + bw * 0.06, y0 + h - hh, bw * 0.88, hh, style="F")
                    if (beschriften is None or j in beschriften) and round(werte[i], dez) > 0:
                        pdf.set_font("Helvetica", "B" if m == 1 or j == m - 1 else "", 6.5)
                        pdf.set_text_color(*(DUNKEL if m == 1 or j == m - 1 else GRAU))
                        lab = n(werte[i], dez)
                        pdf.text(bx + bw / 2 - pdf.get_string_width(lab) / 2, y0 + h - hh - 1.3, lab)
            fett = label_fett is not None and label_fett == i
            pdf.set_font("Helvetica", "B" if fett else "", 7.2)
            pdf.set_text_color(*(DUNKEL if fett else GRAU))
            lab = _latin(labels[i])
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

    # ====================== Uebersicht ======================
    if v["vorhanden"]:
        y = neue_seite(t("Energie-Wochenbericht"))
        kacheln = []
        if hat["pv"]:
            kacheln.append((t("PV-Erzeugung"), f"{n(pv['summe'])} kWh",
                            S.pct(pct(pv["summe"], pv["summe_vw"]), " ggü. VW"), SOLAR))
        kacheln.append((t("Hausverbrauch"), f"{n(v['summe'])} kWh",
                        t("Ø {v} kWh/Tag · {p}", v=n(v["summe"] / 7), p=S.pct(pct(v["summe"], v["summe_vw"]))), GRAU))
        if v["autarkie"] is not None:
            kacheln.append((t("Autarkie"), f"{n(v['autarkie'], 0)} %",
                            t("{v} kWh aus dem Netz", v=n(v["summe_netz"])), GRUEN))
        if d["eigenverbrauch"] is not None:
            kacheln.append((t("Eigenverbrauch"), f"{n(d['eigenverbrauch'], 0)} %",
                            t("des PV-Stroms selbst genutzt"), SOLAR_DUNKEL))
        kacheln.append((t("Netzbezug"), f"{n(k['bezug']['summe'])} kWh",
                        S.pct(pct(k["bezug"]["summe"], k["bezug"]["summe_vw"]), " ggü. VW"), NETZ))
        if hat["einspeisung"]:
            kacheln.append((t("Einspeisung"), f"{n(k['einspeisung']['summe'])} kWh",
                            S.pct(pct(k["einspeisung"]["summe"], k["einspeisung"]["summe_vw"]), " ggü. VW"), EINSP))
        if hat["laden"] or hat["entladen"]:
            kacheln.append((t("Batterie"), f"{n(k['entladen']['summe'])} kWh",
                            t("entladen · {v} kWh geladen", v=n(k["laden"]["summe"])), BATT))
        if hat["wasser"]:
            w_ = k["wasser"]
            kacheln.append((t("Wasser"), f"{n(w_['summe'], 0)} L",
                            t("Ø {v} L/Tag · {p}", v=n(w_["summe"] / 7, 0), p=S.pct(pct(w_["summe"], w_["summe_vw"]))), WASSER))
        y = kachelreihen(y, kacheln[:8]) + 12

        abschnitt(y, t("Woher kam der Strom?"), t("Hausverbrauch je Tag"))
        serien = []
        if hat["pv"]:
            serien.append((t("Solar direkt"), SOLAR, v["direkt"]))
        if hat["entladen"]:
            serien.append((t("Batterie"), BATT, v["batterie"]))
        serien.append((t("Netz"), NETZ, v["netz"]))
        legende(y, [(f, nm, False) for nm, f, _ in serien])
        balken(27, y + 10, 168, 44, tageslabels, serien, gestapelt=True)
        y += 70

        abschnitt(y, t("Erzeugung und Verbrauch im Tagesverlauf"), t("Ø kWh je Stunde"))
        leg = [(DUNKEL, t("Verbrauch"), True)]
        if hat["pv"]:
            leg.insert(0, (SOLAR, t("PV-Erzeugung"), False))
        legende(y, leg)
        profil(27, y + 10, 168, 32,
               [(SOLAR_ZART, SOLAR, pv["profil"])] if hat["pv"] else [],
               [(DUNKEL, v["profil"], False)])
        y += 56

        if y < 245:
            abschnitt(y, t("Energieflüsse der Woche"))
            y += 9
            herkunft = [(t("Solar direkt"), SOLAR, v["summe_direkt"])]
            if hat["entladen"]:
                herkunft.append((t("Batterie"), BATT, v["summe_batterie"]))
            herkunft.append((t("Netz"), NETZ, v["summe_netz"]))
            flussbalken(y, t("Herkunft des Verbrauchs"), herkunft)
            if hat["pv"] and pv["summe"] > 0:
                y += 19
                verw = [(t("Direkt verbraucht"), SOLAR, v["summe_direkt"])]
                if hat["laden"]:
                    verw.append((t("In die Batterie"), BATT_HELL, v["pv_batt"]))
                if hat["einspeisung"]:
                    verw.append((t("Eingespeist"), EINSP, k["einspeisung"]["summe"]))
                flussbalken(y, t("Verwendung des PV-Stroms"), verw)

    # ====================== PV ======================
    if hat["pv"]:
        y = neue_seite(t("PV-Erzeugung"))
        b = pv["bester"]
        p = pct(pv["summe"], pv["summe_vw"])
        kacheln = [
            (t("Erzeugung"), f"{n(pv['summe'])} kWh", t("Ø {v} kWh pro Tag", v=n(pv["summe"] / 7)), SOLAR),
            (t("Vorwoche"), S.pct(p) if p is not None else "-", t("Vorwoche: {v} kWh", v=n(pv["summe_vw"])), SOLAR,
             GRAU if p is None else (GRUEN if p >= 0 else ROT)),
            (t("Bester Tag"), f"{n(pv['tage'][b])} kWh", f"{S.tag(b)}, {S.datum(d['daten'][b])}", SOLAR),
        ]
        if kwp:
            kacheln.append((t("Spez. Ertrag"), n(pv["summe"] / kwp, 2), f"kWh/kWp · {n(kwp, 1)} kWp", SOLAR))
        elif pv["top"]:
            (ti, th), tv = pv["top"][0]
            kacheln.append((t("Spitzenstunde"), f"{n(tv, 2)} kWh",
                            t("{tag} {von}-{bis} Uhr", tag=S.tag(ti), von=f"{th:02d}", bis=f"{th + 1:02d}"), SOLAR))
        y = kachelreihen(y, kacheln) + 13

        abschnitt(y, t("Tagesertrag"))
        legende(y, [(GRAU_HELL, t("Vorwoche"), False), (SOLAR, t("Diese Woche"), False)])
        balken(27, y + 10, 168, 44, tageslabels,
               [(t("Vorwoche"), GRAU_HELL, pv["tage_vw"]), (t("Diese Woche"), SOLAR, pv["tage"])],
               beschriften={1}, hervorheben=(1, b, SOLAR_DUNKEL))
        y += 70

        abschnitt(y, t("Durchschnittliches Tagesprofil"), t("Ø kWh je Stunde"))
        legende(y, [(SOLAR, t("Diese Woche"), False), (GRAU, t("Vorwoche"), True)])
        profil(27, y + 10, 168, 32, [(SOLAR_ZART, SOLAR, pv["profil"])], [(GRAU, pv["profil_vw"], True)])
        y += 56

        zusatz = t("PV bisher {v} kWh", v=n(sum(pv["monate"]), 0))
        serien = [(t("PV-Erzeugung"), SOLAR, pv["monate"])]
        if v["vorhanden"]:
            zusatz += t(" · Verbrauch {v} kWh", v=n(sum(v["monate"]), 0))
            serien.append((t("Verbrauch"), GRAU_HELL, v["monate"]))
        abschnitt(y, t("Jahresverlauf {jahr}", jahr=d["jahr"]), zusatz)
        legende(y, [(f, nm, False) for nm, f, _ in serien])
        balken(27, y + 10, 168, 36, [S.monat(m) for m in range(12)], serien, dez=0, schritte=2,
               beschriften={0}, label_fett=d["monat_aktuell"] - 1)

    # ====================== Netz / Batterie / Wasser ======================
    bereiche = []
    if hat["bezug"] or hat["einspeisung"]:
        bereiche.append("netz")
    if hat["laden"] or hat["entladen"]:
        bereiche.append("batterie")
    if hat["wasser"]:
        bereiche.append("wasser")
    if bereiche:
        namen_b = {"netz": t("Netz"), "batterie": t("Batterie"), "wasser": t("Wasser")}
        y = neue_seite(" · ".join(namen_b[x] for x in bereiche)) + 4
        for bereich in bereiche:
            if bereich == "netz":
                serien, zus = [], []
                if hat["bezug"]:
                    serien.append((t("Netzbezug"), NETZ, k["bezug"]["tage"]))
                    zus.append(t("Bezug {v} kWh", v=n(k["bezug"]["summe"])))
                if hat["einspeisung"]:
                    serien.append((t("Einspeisung"), EINSP, k["einspeisung"]["tage"]))
                    zus.append(t("Einspeisung {v} kWh", v=n(k["einspeisung"]["summe"])))
                if hat["bezug"] and hat["einspeisung"]:
                    saldo = k["einspeisung"]["summe"] - k["bezug"]["summe"]
                    zus.append(t("Saldo {v} kWh", v=f"{'+' if saldo >= 0 else ''}{n(saldo)}"))
                abschnitt(y, t("Netz"), " · ".join(zus))
                legende(y + 7, [(f, nm, False) for nm, f, _ in serien])
                balken(27, y + 15, 168, 40, tageslabels, serien)
            elif bereich == "batterie":
                serien = []
                if hat["laden"]:
                    serien.append((t("Geladen"), BATT_HELL, k["laden"]["tage"]))
                if hat["entladen"]:
                    serien.append((t("Entladen"), BATT, k["entladen"]["tage"]))
                zus = t("geladen {a} kWh · entladen {b} kWh", a=n(k["laden"]["summe"]), b=n(k["entladen"]["summe"]))
                if k["laden"]["summe"] > 0 and hat["entladen"]:
                    zus += t(" · Verhältnis entladen/geladen {v} %",
                             v=n(k["entladen"]["summe"] / k["laden"]["summe"] * 100, 0))
                abschnitt(y, t("Batterie"), zus)
                legende(y + 7, [(f, nm, False) for nm, f, _ in serien])
                balken(27, y + 15, 168, 40, tageslabels, serien)
            else:
                w_ = k["wasser"]
                abschnitt(y, t("Wasser"), f"{n(w_['summe'], 0)} L · {n(w_['summe'] / 1000, 2)} {t('Kubikmeter')} · "
                                          f"{S.pct(pct(w_['summe'], w_['summe_vw']), ' ggü. Vorwoche')}")
                legende(y + 7, [(GRAU_HELL, t("Vorwoche"), False), (WASSER, t("Diese Woche"), False)])
                balken(27, y + 15, 168, 40, tageslabels,
                       [(t("Vorwoche"), GRAU_HELL, w_["tage_vw"]), (t("Diese Woche"), WASSER, w_["tage"])],
                       einheit=t("Liter"), dez=0, beschriften={1})
            y += 76
        if hat["wasser"] and y < 230:
            w_ = k["wasser"]
            abschnitt(y, t("Wasser im Tagesverlauf"), t("Ø Liter je Stunde"))
            legende(y, [(WASSER, t("Diese Woche"), False), (GRAU, t("Vorwoche"), True)])
            profil(27, y + 10, 168, 28, [(WASSER_HELL, WASSER, w_["profil"])], [(GRAU, w_["profil_vw"], True)],
                   einheit=t("Liter"))

    # ====================== Details ======================
    y = neue_seite(t("Details")) + 4
    abschnitt(y, t("Tageswerte"))
    spalten = [("Tag", None)]
    if hat["pv"]:
        spalten.append(("PV", lambda i: n(pv["tage"][i])))
    if v["vorhanden"]:
        spalten.append(("Verbrauch", lambda i: n(v["tage"][i])))
    if hat["bezug"]:
        spalten.append(("Netzbezug", lambda i: n(k["bezug"]["tage"][i])))
    if hat["einspeisung"]:
        spalten.append(("Einspeis.", lambda i: n(k["einspeisung"]["tage"][i])))
    if hat["laden"]:
        spalten.append(("Bat. +", lambda i: n(k["laden"]["tage"][i])))
    if hat["entladen"]:
        spalten.append(("Bat. -", lambda i: n(k["entladen"]["tage"][i])))
    if v["vorhanden"]:
        spalten.append(("Autarkie", lambda i: "-" if v["autarkie_tage"][i] is None
                        else f"{n(v['autarkie_tage'][i], 0)} %"))
    if hat["wasser"]:
        spalten.append(("Wasser L", lambda i: n(k["wasser"]["tage"][i], 0)))
    erste_breite = 26
    rest = (180 - erste_breite) / max(len(spalten) - 1, 1)
    breiten = [erste_breite] + [rest] * (len(spalten) - 1)

    y += 6
    pdf.set_fill_color(*KOPF)
    pdf.rect(15, y, 180, 7, style="F")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*WEISS)
    x = 15
    for (name, _), sw in zip(spalten, breiten):
        pdf.set_xy(x + 1.5, y)
        pdf.cell(sw - 3, 7, _latin(t(name)), align="L" if name == "Tag" else "R")
        x += sw
    y += 7

    def zeile(texte, fett=False, hintergrund=None):
        nonlocal y
        if hintergrund:
            pdf.set_fill_color(*hintergrund)
            pdf.rect(15, y, 180, 6.5, style="F")
        x = 15
        for (name, _), sw, text in zip(spalten, breiten, texte):
            pdf.set_font("Helvetica", "B" if fett else "", 8.5)
            pdf.set_text_color(*DUNKEL)
            pdf.set_xy(x + 1.5, y)
            pdf.cell(sw - 3, 6.5, _latin(text), align="L" if name == "Tag" else "R")
            x += sw
        y += 6.5

    for i in range(7):
        zeile([tageslabels[i]] + [s[1](i) for s in spalten[1:]], hintergrund=GRAU_ZART if i % 2 else None)
    summen = {"PV": n(pv["summe"]), "Verbrauch": n(v["summe"]),
              "Netzbezug": n(k["bezug"]["summe"]), "Einspeis.": n(k["einspeisung"]["summe"]),
              "Bat. +": n(k["laden"]["summe"]), "Bat. -": n(k["entladen"]["summe"]),
              "Autarkie": "-" if v["autarkie"] is None else f"{n(v['autarkie'], 0)} %",
              "Wasser L": n(k["wasser"]["summe"], 0)}
    pdf.set_draw_color(*SOLAR)
    pdf.set_line_width(0.5)
    pdf.line(15, y, 195, y)
    zeile([t("Summe")] + [summen[s[0]] for s in spalten[1:]], fett=True, hintergrund=SOLAR_ZART)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*GRAU)
    pdf.text(15, y + 4, _latin(t("Energiewerte in kWh. Bat. + = in die Batterie geladen, Bat. - = aus der Batterie entnommen.")))
    y += 14

    if hat["pv"] and pv["quellen"]:
        abschnitt(y, t("PV-Erzeugung nach Quelle"))
        y += 7
        gesamt = pv["summe"] or 1
        for name, wert in pv["quellen"]:
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

        abschnitt(y, t("Ertragsstärkste PV-Stunden"))
        y += 7
        for rang, ((ti, th), wert) in enumerate(pv["top"], 1):
            pdf.set_fill_color(*(SOLAR if rang == 1 else SOLAR_ZART))
            pdf.ellipse(15, y, 5.5, 5.5, style="F")
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*DUNKEL)
            pdf.text(15 + 2.75 - pdf.get_string_width(str(rang)) / 2, y + 3.9, str(rang))
            pdf.set_font("Helvetica", "", 9)
            pdf.text(24, y + 4, _latin(t("{tag}, {datum}  {von}:00 - {bis}:00 Uhr", tag=S.tag(ti),
                                         datum=S.datum(d["daten"][ti]), von=f"{th:02d}", bis=f"{th + 1:02d}")))
            pdf.set_font("Helvetica", "B", 9)
            lab = f"{n(wert, 2)} kWh"
            pdf.text(120 - pdf.get_string_width(lab), y + 4, lab)
            y += 7.5
        y += 7

    abschnitt(y, t("Kurzfazit"))
    y += 5
    saetze = []
    if hat["pv"]:
        b, s = pv["bester"], pv["schwaechster"]
        p = pct(pv["summe"], pv["summe_vw"])
        saetze.append(t("Die PV-Anlage hat in KW {kw} {v} kWh erzeugt", kw=d["kw"], v=n(pv["summe"]))
                      + (t(" ({p} gegenüber der Vorwoche).", p=S.pct(p)) if p is not None else "."))
        saetze.append(t("Stärkster Tag war {a} ({av} kWh), schwächster {b} ({bv} kWh).",
                        a=S.tag(b), av=n(pv["tage"][b]), b=S.tag(s), bv=n(pv["tage"][s])))
    if v["vorhanden"]:
        saetze.append(t("Im Haus wurden {v} kWh verbraucht, davon kamen {n} kWh aus dem Netz",
                        v=n(v["summe"]), n=n(v["summe_netz"]))
                      + (t(", die Autarkie lag bei {a} %.", a=n(v["autarkie"], 0)) if v["autarkie"] is not None else "."))
    if d["eigenverbrauch"] is not None:
        saetze.append(t("{e} % des PV-Stroms wurden selbst genutzt, {x} kWh gingen ins Netz.",
                        e=n(d["eigenverbrauch"], 0), x=n(k["einspeisung"]["summe"])))
    if hat["laden"] or hat["entladen"]:
        saetze.append(t("Die Batterie hat {a} kWh aufgenommen und {b} kWh abgegeben.",
                        a=n(k["laden"]["summe"]), b=n(k["entladen"]["summe"])))
    if hat["wasser"]:
        w_ = k["wasser"]
        p = pct(w_["summe"], w_["summe_vw"])
        saetze.append(t("Der Wasserverbrauch lag bei {v} Litern", v=n(w_["summe"], 0))
                      + (t(" ({p} gegenüber der Vorwoche).", p=S.pct(p)) if p is not None else "."))
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*DUNKEL)
    pdf.set_xy(15, y)
    pdf.multi_cell(180, 5.2, _latin(" ".join(saetze)), align="L")

    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    pdf.output(pfad)
    return pfad
