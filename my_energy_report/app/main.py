"""My Energy Report – Home-Assistant-App: Zeitpläne, Berichtsliste, Versand."""

import asyncio
import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiohttp import web

import report
from ha import HA, HAError

VERSION = "1.0.2"
DATA = Path(os.environ.get("MER_DATA", "/data"))
MEDIA = Path(os.environ.get("MER_MEDIA", "/media/my_energy_report"))
MEDIA_ID = "media-source://media_source/local/my_energy_report"
STATIC = Path(__file__).parent / "static"
PORT = int(os.environ.get("MER_PORT", "8099"))
ARTEN = ("week", "month", "year")

log = logging.getLogger("my_energy_report")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

STANDARD = {
    # Wochenbericht
    "enabled": True, "weekday": 0, "time": "06:30",
    # Monatsbericht
    "m_enabled": False, "m_day": 1, "m_time": "07:00", "m_prev_year": True,
    # Jahresbericht
    "y_enabled": False, "y_day": 1, "y_month": 1, "y_time": "07:30",
    "plant_name": "Zuhause", "kwp": None, "keep_weeks": 52, "language": "auto",
    "push": [], "email": [],
}


def _hm(text, standard="06:30"):
    try:
        h, m = (int(x) for x in str(text).split(":")[:2])
        return h, m
    except ValueError:
        h, m = standard.split(":")
        return int(h), int(m)


class App:
    def __init__(self, ha):
        self.ha = ha
        self.settings = dict(STANDARD)
        self.reports = []
        self.running = None          # Bericht-ID, die gerade erstellt wird
        self.tz = ZoneInfo(os.environ.get("TZ") or "Europe/Berlin")
        self.ha_lang = "de"
        self.connected = False
        self.ha_error = None
        self.quellen = {k: [] for k in report.KATEGORIEN}
        self.ziele = {"push": [], "email": []}
        self.slug = None
        self.lock = asyncio.Lock()

    # ---------------- Speicher ----------------
    def laden(self):
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / "pages").mkdir(exist_ok=True)
        MEDIA.mkdir(parents=True, exist_ok=True)
        try:
            self.settings.update(json.loads((DATA / "settings.json").read_text()))
        except (OSError, ValueError):
            pass
        try:
            self.reports = json.loads((DATA / "reports.json").read_text())
        except (OSError, ValueError):
            self.reports = []
        for r in self.reports:           # Berichte aus 1.0.0/1.0.1 sind Wochenberichte
            r.setdefault("type", "week")
        self.sortieren()

    def speichern(self):
        (DATA / "settings.json").write_text(json.dumps(self.settings, indent=1))
        (DATA / "reports.json").write_text(json.dumps(self.reports, indent=1))

    def sortieren(self):
        rang = {"year": 0, "month": 1, "week": 2}
        self.reports.sort(key=lambda r: (r["bis"], -rang.get(r.get("type", "week"), 2)), reverse=True)

    def lang(self):
        s = self.settings.get("language", "auto")
        if s in ("de", "en"):
            return s
        return "de" if self.ha_lang.startswith("de") else "en"

    # ---------------- Home Assistant ----------------
    async def ha_abgleich(self):
        try:
            cfg = await self.ha.config()
            if cfg.get("time_zone"):
                self.tz = ZoneInfo(cfg["time_zone"])
            self.ha_lang = cfg.get("language") or "de"
            self.quellen = report.quellen_aus_prefs(await self.ha.energy_prefs())
            self.ziele = await self.ha.ziele()
            if self.slug is None:
                self.slug = await self.ha.addon_slug()
            self.connected, self.ha_error = True, None
        except Exception as e:  # noqa: BLE001
            self.connected, self.ha_error = False, str(e)
            log.warning("Abgleich mit Home Assistant fehlgeschlagen: %s", e)

    # ---------------- Zeitpläne ----------------
    def plan_schluessel(self, typ):
        s = self.settings
        if typ == "week":
            return (s.get("enabled"), s.get("weekday"), s.get("time"))
        if typ == "month":
            return (s.get("m_enabled"), s.get("m_day"), s.get("m_time"))
        return (s.get("y_enabled"), s.get("y_day"), s.get("y_month"), s.get("y_time"))

    def naechster_lauf(self, typ, ab=None):
        s = self.settings
        jetzt = ab or datetime.now(self.tz)
        mk = lambda d, hm: datetime(d.year, d.month, d.day, hm[0], hm[1], tzinfo=self.tz)
        if typ == "week":
            if not s.get("enabled"):
                return None
            tag = jetzt.date() + timedelta(days=(int(s.get("weekday", 0)) - jetzt.weekday()) % 7)
            lauf = mk(tag, _hm(s.get("time"), "06:30"))
            return lauf if lauf > jetzt else lauf + timedelta(days=7)
        if typ == "month":
            if not s.get("m_enabled"):
                return None
            tag = int(s.get("m_day", 1))
            lauf = mk(date(jetzt.year, jetzt.month, tag), _hm(s.get("m_time"), "07:00"))
            if lauf <= jetzt:
                nm = report._monat_plus(date(jetzt.year, jetzt.month, 1), 1)
                lauf = mk(date(nm.year, nm.month, tag), _hm(s.get("m_time"), "07:00"))
            return lauf
        if not s.get("y_enabled"):
            return None
        tag, monat = int(s.get("y_day", 1)), int(s.get("y_month", 1))
        lauf = mk(date(jetzt.year, monat, tag), _hm(s.get("y_time"), "07:30"))
        return lauf if lauf > jetzt else mk(date(jetzt.year + 1, monat, tag), _hm(s.get("y_time"), "07:30"))

    async def zeitplan(self):
        schluessel = {a: None for a in ARTEN}
        ziel = {a: None for a in ARTEN}
        while True:
            await asyncio.sleep(20)
            jetzt = datetime.now(self.tz)
            faellig = []
            for typ in ARTEN:
                neu = self.plan_schluessel(typ) + (str(self.tz),)
                if neu != schluessel[typ]:
                    schluessel[typ], ziel[typ] = neu, self.naechster_lauf(typ, jetzt)
                if ziel[typ] and jetzt >= ziel[typ]:
                    ziel[typ] = self.naechster_lauf(typ, jetzt + timedelta(minutes=1))
                    faellig.append(typ)
            for typ in faellig:
                ref = report.letzte_periode(typ, jetzt.date())
                log.info("Geplanter %s-Bericht für den Zeitraum ab %s", typ, ref)
                await self.erstellen(typ, ref, vorjahr=bool(self.settings.get("m_prev_year")) if typ == "month" else False,
                                     versenden=True, ausloeser="schedule")

    # ---------------- Bericht erstellen ----------------
    def dateiname(self, per, lang):
        if per["typ"] == "week":
            return (f"Energie-Bericht_KW{per['kw']:02d}_{per['jahr']}.pdf" if lang == "de"
                    else f"Energy-Report_W{per['kw']:02d}_{per['jahr']}.pdf")
        basis = "Energie-Bericht" if lang == "de" else "Energy-Report"
        if per["typ"] == "month":
            return f"{basis}_{per['jahr']}-{per['monat']:02d}.pdf"
        return f"{basis}_{per['jahr']}.pdf"

    async def erstellen(self, typ, ref, vorjahr=False, versenden=False, ausloeser="manual"):
        async with self.lock:
            per = report.periode(typ, ref, vorjahr)
            rid = per["id"]
            self.running = rid
            lang = self.lang()
            eintrag = {"id": rid, "type": typ, "kw": per.get("kw"), "jahr": per["jahr"], "monat": per.get("monat"),
                       "von": per["start"].isoformat(), "bis": (per["ende"] - timedelta(days=1)).isoformat(),
                       "prev_year": bool(per.get("vj")),
                       "created": datetime.now(self.tz).isoformat(timespec="seconds"),
                       "trigger": ausloeser, "status": "ok", "error": None, "kpi": {},
                       "file": None, "size": 0, "pages": 0, "sent": {}}
            try:
                await self.ha_abgleich()
                if not self.connected:
                    raise HAError(self.ha_error or "Home Assistant nicht erreichbar")
                alle = [sid for kat in report.KATEGORIEN for sid in self.quellen[kat]]
                if not alle:
                    raise HAError("Im Energie-Dashboard sind keine Quellen eingerichtet")
                dt = lambda d: datetime(d.year, d.month, d.day, tzinfo=self.tz)
                stats = {"cur": await self.ha.statistik(alle, dt(per["start"]), dt(per["ende"]), "hour"),
                         "vor": await self.ha.statistik(alle, dt(per["vor"][0]), dt(per["vor"][1]), "hour")}
                if per.get("vj"):
                    stats["vj"] = await self.ha.statistik(alle, dt(per["vj"][0]), dt(per["vj"][1]), "hour")
                monate = None
                if typ != "year":
                    monate = await self.ha.statistik(alle, dt(per["jahr_start"]), dt(per["ende"]), "month")
                namen = await self.ha.namen(alle)
                d = report.auswerten(per, stats, monate, self.quellen, self.tz, namen)
                name = self.dateiname(per, lang)
                alt = next((r for r in self.reports if r["id"] == rid), None)
                if alt and alt.get("file") and alt["file"] != name:
                    (MEDIA / alt["file"]).unlink(missing_ok=True)
                erstellt = datetime.now(self.tz).strftime("%d.%m.%Y %H:%M" if lang == "de" else "%d/%m/%Y %H:%M")
                await asyncio.get_running_loop().run_in_executor(
                    None, report.baue_pdf, d, str(MEDIA / name), self.settings.get("plant_name") or "",
                    self.settings.get("kwp"), erstellt, lang)
                eintrag.update(file=name, size=(MEDIA / name).stat().st_size, kpi=report.kennzahlen(d))
                eintrag["pages"] = await self.seiten_bilder(rid, MEDIA / name)
            except Exception as e:  # noqa: BLE001
                log.exception("Bericht %s fehlgeschlagen", rid)
                eintrag.update(status="error", error=str(e))
            self.reports = [r for r in self.reports if r["id"] != rid] + [eintrag]
            self.sortieren()
            self.aufraeumen()
            self.speichern()
            self.running = None
        if versenden and eintrag["status"] == "ok":
            await self.versenden(eintrag)
        return eintrag

    async def seiten_bilder(self, rid, pdf):
        ziel = DATA / "pages"
        for alt in ziel.glob(f"{rid}-*.png"):
            alt.unlink()
        proc = await asyncio.create_subprocess_exec(
            "pdftoppm", "-png", "-r", "70", str(pdf), str(ziel / rid),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, err = await proc.communicate()
        if proc.returncode:
            log.warning("Vorschau für %s fehlgeschlagen: %s", rid, err.decode(errors="replace"))
            return 0
        bilder = sorted(ziel.glob(f"{rid}-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
        for i, b in enumerate(bilder, 1):     # pdftoppm nummeriert je nach Seitenzahl mit 1 oder 01
            b.rename(ziel / f"{rid}-{i}.png")
        return len(bilder)

    def aufraeumen(self):
        """Nur Wochenberichte werden nach der eingestellten Dauer gelöscht."""
        wochen = int(self.settings.get("keep_weeks") or 0)
        if wochen <= 0:
            return
        grenze = (date.today() - timedelta(weeks=wochen)).isoformat()
        for r in [r for r in self.reports if r.get("type", "week") == "week" and r["von"] < grenze]:
            self.loeschen(r["id"], speichern=False)

    def loeschen(self, rid, speichern=True):
        r = next((x for x in self.reports if x["id"] == rid), None)
        if not r:
            return False
        if r.get("file"):
            (MEDIA / r["file"]).unlink(missing_ok=True)
        for b in (DATA / "pages").glob(f"{rid}-*.png"):
            b.unlink()
        self.reports = [x for x in self.reports if x["id"] != rid]
        if speichern:
            self.speichern()
        return True

    # ---------------- Versand ----------------
    def texte(self, r):
        de = self.lang() == "de"
        k = r.get("kpi") or {}
        f = lambda v, n=1: (f"{v:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".") if de
                            else f"{v:,.{n}f}")
        zeilen = []
        if k.get("pv") is not None:
            zeilen.append(("PV" if de else "Solar") + f" {f(k['pv'])} kWh")
        if k.get("verbrauch") is not None:
            zeile = ("Verbrauch" if de else "Consumption") + f" {f(k['verbrauch'])} kWh"
            if k.get("autarkie") is not None:
                zeile += (" · Autarkie " if de else " · self-sufficiency ") + f"{f(k['autarkie'], 0)} %"
            zeilen.append(zeile)
        if k.get("bezug") is not None:
            zeilen.append(("Netzbezug" if de else "Grid import") + f" {f(k['bezug'])} kWh")
        if k.get("wasser") is not None:
            zeilen.append(("Wasser" if de else "Water") + f" {f(k['wasser'], 0)} L")
        von, bis = date.fromisoformat(r["von"]), date.fromisoformat(r["bis"])
        typ = r.get("type", "week")
        if typ == "week":
            titel = (f"Energiebericht KW {r['kw']} ({von:%d.%m.}–{bis:%d.%m.%Y})" if de
                     else f"Energy report week {r['kw']} ({von:%d/%m}–{bis:%d/%m/%Y})")
        elif typ == "month":
            m = report.MONATE_LANG["de" if de else "en"][von.month - 1]
            titel = f"Energiebericht {m} {von.year}" if de else f"Energy report {m} {von.year}"
        else:
            titel = f"Energiebericht {von.year}" if de else f"Energy report {von.year}"
        return titel, zeilen

    async def versenden(self, r, nur=None):
        titel, zeilen = self.texte(r)
        text = "\n".join(zeilen)
        link = f"/hassio/ingress/{self.slug}" if self.slug else "/hassio/dashboard"
        ergebnis = {}
        if nur in (None, "push") and self.settings.get("push"):
            fehler = []
            for ziel in self.settings["push"]:
                try:
                    await self.ha.push(ziel, titel, text, link)
                except Exception as e:  # noqa: BLE001
                    fehler.append(f"{ziel}: {e}")
            ergebnis["push"] = "ok" if not fehler else "; ".join(fehler)
        if nur in (None, "email") and self.settings.get("email"):
            de = self.lang() == "de"
            html = ("<p style=\"font-family:sans-serif\">" + "<br>".join(zeilen) + "</p>"
                    "<p style=\"font-family:sans-serif;color:#6b6a65\">"
                    + ("Der vollständige Bericht hängt als PDF an." if de else "The full report is attached as a PDF.")
                    + "</p>")
            anhang = {"media_source": {"media_content_id": f"{MEDIA_ID}/{r['file']}",
                                       "media_content_type": "application/pdf"},
                      "filename": r["file"]}
            fehler = []
            for ziel in self.settings["email"]:
                try:
                    await self.ha.email(ziel, titel, text, html, anhang)
                except Exception as e:  # noqa: BLE001
                    fehler.append(f"{ziel}: {e}")
            ergebnis["email"] = "ok" if not fehler else "; ".join(fehler)
        if ergebnis:
            r.setdefault("sent", {}).update(ergebnis)
            r["sent_at"] = datetime.now(self.tz).isoformat(timespec="seconds")
            self.speichern()
        return ergebnis

    # ---------------- Zustand für die Oberfläche ----------------
    def zustand(self):
        laeufe = {a: self.naechster_lauf(a) for a in ARTEN}
        naechster = min(((v, a) for a, v in laeufe.items() if v), default=(None, None))
        return {
            "version": VERSION, "connected": self.connected, "ha_error": self.ha_error,
            "settings": self.settings,
            "next_runs": {a: v.isoformat() if v else None for a, v in laeufe.items()},
            "next_run": naechster[0].isoformat() if naechster[0] else None, "next_type": naechster[1],
            "running": self.running, "lang": self.lang(), "ha_lang": self.ha_lang,
            "sources": {k: len(v) for k, v in self.quellen.items()},
            "targets": self.ziele, "storage": sum(r.get("size", 0) for r in self.reports),
            "folder": str(MEDIA), "now": datetime.now(self.tz).isoformat(timespec="seconds"),
        }


# ---------------------------------------------------------------------------
# Web
# ---------------------------------------------------------------------------
def fehler(text, status=400):
    return web.json_response({"error": text}, status=status)


@web.middleware
async def schutz(request, handler):
    if request.method not in ("GET", "HEAD") and request.headers.get("X-App") != "1":
        return fehler("Fehlender Header X-App", 403)
    try:
        return await handler(request)
    except HAError as e:
        return fehler(str(e), 502)


def routen(app: App):
    r = web.RouteTableDef()

    @r.get("/")
    async def index(_):
        return web.FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})

    @r.get("/lang-en.js")
    async def lang_en(_):
        return web.FileResponse(STATIC / "lang-en.js", headers={"Cache-Control": "no-cache"})

    @r.get("/favicon.svg")
    async def favicon(_):
        return web.FileResponse(STATIC / "favicon.svg")

    @r.get("/favicon.ico")
    async def favicon_ico(_):
        return web.Response(status=204)

    @r.get("/api/state")
    async def state(_):
        return web.json_response(app.zustand())

    @r.post("/api/refresh")
    async def refresh(_):
        await app.ha_abgleich()
        return web.json_response(app.zustand())

    @r.get("/api/reports")
    async def liste(_):
        return web.json_response(app.reports)

    @r.post("/api/reports")
    async def neu(request):
        body = await request.json()
        typ = body.get("type", "week")
        if typ not in ARTEN:
            return fehler("Unbekannte Berichtsart")
        try:
            ref = date.fromisoformat(body.get("period") or body.get("week") or "")
        except ValueError:
            return fehler("Ungültiger Zeitraum")
        per = report.periode(typ, ref)
        if per["ende"] > datetime.now(app.tz).date():
            return fehler("Der Zeitraum ist noch nicht abgeschlossen")
        if app.running:
            return fehler("Es wird gerade schon ein Bericht erstellt", 409)
        eintrag = await app.erstellen(typ, ref, vorjahr=typ == "month" and bool(body.get("prev_year")),
                                      versenden=bool(body.get("send")))
        return web.json_response(eintrag)

    @r.delete("/api/reports/{rid}")
    async def weg(request):
        if not app.loeschen(request.match_info["rid"]):
            return fehler("Bericht nicht gefunden", 404)
        return web.json_response({"ok": True})

    @r.post("/api/reports/{rid}/send")
    async def senden(request):
        rep = next((x for x in app.reports if x["id"] == request.match_info["rid"]), None)
        if not rep or rep["status"] != "ok":
            return fehler("Bericht nicht gefunden", 404)
        if not (app.settings.get("push") or app.settings.get("email")):
            return fehler("Kein Empfänger eingerichtet")
        return web.json_response(await app.versenden(rep))

    @r.get("/api/reports/{rid}/pdf")
    async def pdf(request):
        rep = next((x for x in app.reports if x["id"] == request.match_info["rid"]), None)
        if not rep or not rep.get("file") or not (MEDIA / rep["file"]).exists():
            return fehler("Datei nicht gefunden", 404)
        art = "attachment" if request.query.get("download") else "inline"
        return web.FileResponse(MEDIA / rep["file"], headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": f'{art}; filename="{rep["file"]}"'})

    @r.get("/api/reports/{rid}/page/{n}")
    async def seite(request):
        rid = request.match_info["rid"]
        if "/" in rid or ".." in rid:
            return fehler("Ungültige ID", 400)
        p = DATA / "pages" / f"{rid}-{int(request.match_info['n'])}.png"
        if not p.exists():
            return fehler("Vorschau nicht vorhanden", 404)
        return web.FileResponse(p, headers={"Cache-Control": "no-cache"})

    @r.put("/api/settings")
    async def einstellungen(request):
        body = await request.json()
        s = dict(app.settings)

        def zeit(wert):
            h, m = (int(x) for x in str(wert).split(":")[:2])
            if not (0 <= h < 24 and 0 <= m < 60):
                raise ValueError
            return f"{h:02d}:{m:02d}"

        try:
            for feld in ("enabled", "m_enabled", "y_enabled", "m_prev_year"):
                if feld in body:
                    s[feld] = bool(body[feld])
            if "weekday" in body:
                s["weekday"] = int(body["weekday"]) % 7
            for feld in ("time", "m_time", "y_time"):
                if feld in body:
                    s[feld] = zeit(body[feld])
            for feld in ("m_day", "y_day"):
                if feld in body:
                    s[feld] = min(max(int(body[feld]), 1), 28)
            if "y_month" in body:
                s["y_month"] = min(max(int(body["y_month"]), 1), 12)
            if "plant_name" in body:
                s["plant_name"] = str(body["plant_name"]).strip()[:60]
            if "kwp" in body:
                s["kwp"] = float(body["kwp"]) if body["kwp"] not in (None, "") else None
                if s["kwp"] is not None and not 0 < s["kwp"] < 10000:
                    return fehler("Die Anlagenleistung muss zwischen 0 und 10.000 kWp liegen")
            if "keep_weeks" in body:
                s["keep_weeks"] = max(0, min(int(body["keep_weeks"]), 520))
            if "language" in body:
                s["language"] = body["language"] if body["language"] in ("auto", "de", "en") else "auto"
            for feld in ("push", "email"):
                if feld in body:
                    s[feld] = [str(x) for x in body[feld]]
        except (TypeError, ValueError):
            return fehler("Ungültige Eingabe")
        app.settings = s
        app.aufraeumen()
        app.speichern()
        return web.json_response(app.zustand())

    @r.post("/api/test/{art}")
    async def test(request):
        art = request.match_info["art"]
        de = app.lang() == "de"
        if art == "push":
            if not app.settings.get("push"):
                return fehler("Kein Push-Empfänger ausgewählt")
            for ziel in app.settings["push"]:
                await app.ha.push(ziel, "My Energy Report",
                                  "Testnachricht – Push funktioniert." if de else "Test message – push works.",
                                  f"/hassio/ingress/{app.slug}" if app.slug else "/hassio/dashboard")
        elif art == "email":
            if not app.settings.get("email"):
                return fehler("Kein E-Mail-Empfänger ausgewählt")
            for ziel in app.settings["email"]:
                text = "Testnachricht – E-Mail funktioniert." if de else "Test message – e-mail works."
                await app.ha.email(ziel, "My Energy Report", text, f"<p>{text}</p>")
        else:
            return fehler("Unbekannter Test", 404)
        return web.json_response({"ok": True})

    return r


async def starten(app: App):
    import ha as ha_modul
    app.laden()
    await app.ha_abgleich()
    web_app = web.Application(middlewares=[schutz])
    web_app.add_routes(routen(app))
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("My Energy Report %s läuft auf Port %s (Token %s)", VERSION, PORT,
             "vorhanden" if ha_modul.TOKEN else "FEHLT")

    async def abgleich_schleife():
        while True:
            await asyncio.sleep(300)
            await app.ha_abgleich()

    await asyncio.gather(app.zeitplan(), abgleich_schleife())


if __name__ == "__main__":
    asyncio.run(starten(App(HA())))
