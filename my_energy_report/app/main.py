"""My Energy Report – Home-Assistant-App: Zeitplan, Berichtsliste, Versand."""

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

VERSION = "1.0.0"
DATA = Path(os.environ.get("MER_DATA", "/data"))
MEDIA = Path(os.environ.get("MER_MEDIA", "/media/my_energy_report"))
MEDIA_ID = "media-source://media_source/local/my_energy_report"
STATIC = Path(__file__).parent / "static"
PORT = int(os.environ.get("MER_PORT", "8099"))

log = logging.getLogger("my_energy_report")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

STANDARD = {
    "enabled": True, "weekday": 0, "time": "06:30",
    "plant_name": "Zuhause", "kwp": None, "keep_weeks": 52, "language": "auto",
    "push": [], "email": [],
}


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

    def speichern(self):
        (DATA / "settings.json").write_text(json.dumps(self.settings, indent=1))
        (DATA / "reports.json").write_text(json.dumps(self.reports, indent=1))

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

    # ---------------- Zeitplan ----------------
    def naechster_lauf(self, ab=None):
        s = self.settings
        if not s.get("enabled"):
            return None
        jetzt = ab or datetime.now(self.tz)
        h, m = (int(x) for x in s.get("time", "06:30").split(":"))
        tag = jetzt.date() + timedelta(days=(int(s.get("weekday", 0)) - jetzt.weekday()) % 7)
        lauf = datetime(tag.year, tag.month, tag.day, h, m, tzinfo=self.tz)
        if lauf <= jetzt:
            lauf += timedelta(days=7)
        return lauf

    async def zeitplan(self):
        schluessel, ziel = None, None
        while True:
            await asyncio.sleep(20)
            s = self.settings
            jetzt = datetime.now(self.tz)
            neu = (s.get("enabled"), s.get("weekday"), s.get("time"), str(self.tz))
            if neu != schluessel:
                schluessel, ziel = neu, self.naechster_lauf(jetzt)
            if ziel and jetzt >= ziel:
                ziel = self.naechster_lauf(jetzt + timedelta(minutes=1))
                heute = jetzt.date()
                montag = heute - timedelta(days=heute.weekday() + 7)
                log.info("Geplanter Bericht für die Woche ab %s", montag)
                await self.erstellen(montag, versenden=True, ausloeser="schedule")

    # ---------------- Bericht erstellen ----------------
    async def erstellen(self, montag, versenden, ausloeser="manual"):
        async with self.lock:
            kw = montag.isocalendar()
            rid = f"{kw[0]}-W{kw[1]:02d}"
            self.running = rid
            lang = self.lang()
            eintrag = {"id": rid, "kw": kw[1], "jahr": kw[0], "von": montag.isoformat(),
                       "bis": (montag + timedelta(days=6)).isoformat(),
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
                zr = report.zeitraum(montag, self.tz)
                stat = await self.ha.statistik(alle, zr["vorwoche_start"], zr["ende"], "hour")
                jahr = await self.ha.statistik(alle, zr["jahr_start"], zr["ende"], "month")
                namen = await self.ha.namen(alle)
                d = report.auswerten(stat, jahr, self.quellen, zr, self.tz, namen)
                name = (f"Energie-Bericht_KW{kw[1]:02d}_{kw[0]}.pdf" if lang == "de"
                        else f"Energy-Report_W{kw[1]:02d}_{kw[0]}.pdf")
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
            self.reports.sort(key=lambda r: r["von"], reverse=True)
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
        bilder = sorted(ziel.glob(f"{rid}-*.png"))
        for i, b in enumerate(bilder, 1):     # pdftoppm nummeriert je nach Seitenzahl mit 1 oder 01
            b.rename(ziel / f"{rid}-{i}.png")
        return len(bilder)

    def aufraeumen(self):
        wochen = int(self.settings.get("keep_weeks") or 0)
        if wochen <= 0:
            return
        grenze = (date.today() - timedelta(weeks=wochen)).isoformat()
        for r in [r for r in self.reports if r["von"] < grenze]:
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
            zeilen.append(("Verbrauch" if de else "Consumption") + f" {f(k['verbrauch'])} kWh"
                          + (f" · Autarkie {f(k['autarkie'], 0)} %" if de and k.get("autarkie") is not None else "")
                          + (f" · self-sufficiency {f(k['autarkie'], 0)} %" if not de and k.get("autarkie") is not None else ""))
        if k.get("bezug") is not None:
            zeilen.append(("Netzbezug" if de else "Grid import") + f" {f(k['bezug'])} kWh")
        if k.get("wasser") is not None:
            zeilen.append(("Wasser" if de else "Water") + f" {f(k['wasser'], 0)} L")
        von = date.fromisoformat(r["von"])
        bis = date.fromisoformat(r["bis"])
        titel = (f"Energiebericht KW {r['kw']} ({von:%d.%m.}–{bis:%d.%m.%Y})" if de
                 else f"Energy report week {r['kw']} ({von:%d/%m}–{bis:%d/%m/%Y})")
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
        nl = self.naechster_lauf()
        belegt = sum(r.get("size", 0) for r in self.reports)
        return {
            "version": VERSION, "connected": self.connected, "ha_error": self.ha_error,
            "settings": self.settings, "next_run": nl.isoformat() if nl else None,
            "running": self.running, "lang": self.lang(), "ha_lang": self.ha_lang,
            "sources": {k: len(v) for k, v in self.quellen.items()},
            "targets": self.ziele, "storage": belegt, "folder": str(MEDIA),
            "now": datetime.now(self.tz).isoformat(timespec="seconds"),
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
        try:
            montag = date.fromisoformat(body.get("week", ""))
        except ValueError:
            return fehler("Ungültige Woche")
        montag -= timedelta(days=montag.weekday())
        if montag + timedelta(days=7) > datetime.now(app.tz).date():
            return fehler("Die Woche ist noch nicht abgeschlossen")
        if app.running:
            return fehler("Es wird gerade schon ein Bericht erstellt", 409)
        eintrag = await app.erstellen(montag, bool(body.get("send")))
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
        p = DATA / "pages" / f"{request.match_info['rid']}-{int(request.match_info['n'])}.png"
        if not p.exists():
            return fehler("Vorschau nicht vorhanden", 404)
        return web.FileResponse(p, headers={"Cache-Control": "no-cache"})

    @r.put("/api/settings")
    async def einstellungen(request):
        body = await request.json()
        s = dict(app.settings)
        try:
            if "enabled" in body:
                s["enabled"] = bool(body["enabled"])
            if "weekday" in body:
                s["weekday"] = int(body["weekday"]) % 7
            if "time" in body:
                h, m = (int(x) for x in str(body["time"]).split(":")[:2])
                if not (0 <= h < 24 and 0 <= m < 60):
                    raise ValueError
                s["time"] = f"{h:02d}:{m:02d}"
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
    app.laden()
    await app.ha_abgleich()
    web_app = web.Application(middlewares=[schutz])
    web_app.add_routes(routen(app))
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("My Energy Report %s läuft auf Port %s", VERSION, PORT)

    async def abgleich_schleife():
        while True:
            await asyncio.sleep(300)
            await app.ha_abgleich()

    await asyncio.gather(app.zeitplan(), abgleich_schleife())


if __name__ == "__main__":
    asyncio.run(starten(App(HA())))
