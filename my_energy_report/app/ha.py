"""Zugriff auf Home Assistant über die Supervisor-Proxy-API (REST + WebSocket)."""

import os

import aiohttp

TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
CORE = "http://supervisor/core"
SUPERVISOR = "http://supervisor"


class HAError(Exception):
    pass


class HA:
    def __init__(self):
        self.session = None

    def _headers(self):
        return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    async def _s(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120))
        return self.session

    async def ws(self, *befehle):
        """Führt WebSocket-Befehle nacheinander aus und gibt die Ergebnisse zurück."""
        s = await self._s()
        try:
            async with s.ws_connect(f"{CORE}/websocket", max_msg_size=0) as w:
                msg = await w.receive_json()
                if msg.get("type") != "auth_required":
                    raise HAError(f"Unerwartete Antwort: {msg}")
                await w.send_json({"type": "auth", "access_token": TOKEN})
                msg = await w.receive_json()
                if msg.get("type") != "auth_ok":
                    raise HAError("Anmeldung an Home Assistant fehlgeschlagen")
                ergebnisse = []
                for i, b in enumerate(befehle, 1):
                    await w.send_json({"id": i, **b})
                    while True:
                        msg = await w.receive_json()
                        if msg.get("id") == i and msg.get("type") == "result":
                            break
                    if not msg.get("success"):
                        err = msg.get("error") or {}
                        raise HAError(f"{b['type']}: {err.get('message', 'Fehler')}")
                    ergebnisse.append(msg.get("result"))
                return ergebnisse
        except aiohttp.ClientError as e:
            raise HAError(f"Home Assistant nicht erreichbar: {e}") from e

    async def rest(self, methode, pfad, daten=None, basis=CORE):
        s = await self._s()
        try:
            async with s.request(methode, f"{basis}{pfad}", json=daten, headers=self._headers()) as r:
                text = await r.text()
                if r.status >= 400:
                    raise HAError(f"HTTP {r.status}: {text[:300]}")
                return await r.json(content_type=None) if text else None
        except aiohttp.ClientError as e:
            raise HAError(f"Home Assistant nicht erreichbar: {e}") from e

    # ---------------- Bausteine ----------------
    async def config(self):
        return (await self.ws({"type": "get_config"}))[0]

    async def energy_prefs(self):
        return (await self.ws({"type": "energy/get_prefs"}))[0]

    async def statistik(self, ids, start, ende, periode):
        if not ids:
            return {}
        return (await self.ws({
            "type": "recorder/statistics_during_period",
            "start_time": start.isoformat(), "end_time": ende.isoformat(),
            "statistic_ids": list(ids), "period": periode, "types": ["change"],
            "units": {"energy": "kWh", "volume": "L"},
        }))[0] or {}

    async def namen(self, ids):
        states = (await self.ws({"type": "get_states"}))[0]
        m = {s["entity_id"]: s.get("attributes", {}).get("friendly_name") for s in states}
        return {i: m.get(i) or i for i in ids}

    async def ziele(self):
        """Push-Ziele (notify.mobile_app_*) und E-Mail-Empfänger (SMTP-Entitäten)."""
        dienste, reg, states = await self._ziele_roh()
        push = []
        for d in dienste:
            if d.get("domain") == "notify":
                for name in sorted(d.get("services", {})):
                    if name.startswith("mobile_app_"):
                        push.append({"id": name, "name": name[len("mobile_app_"):].replace("_", " ")})
        namen = {s["entity_id"]: s.get("attributes", {}).get("friendly_name") for s in states}
        email = [{"id": e["entity_id"], "name": namen.get(e["entity_id"]) or e.get("name") or e["entity_id"]}
                 for e in reg if e.get("platform") == "smtp" and e["entity_id"].startswith("notify.")]
        return {"push": push, "email": sorted(email, key=lambda x: x["name"])}

    async def _ziele_roh(self):
        dienste = await self.rest("GET", "/api/services")
        reg, states = await self.ws({"type": "config/entity_registry/list"}, {"type": "get_states"})
        return dienste, reg, states

    async def push(self, dienst, titel, text, link):
        await self.rest("POST", f"/api/services/notify/{dienst}", {
            "title": titel, "message": text,
            "data": {"url": link, "clickAction": link, "group": "my-energy-report"},
        })

    async def email(self, entity_id, titel, text, html, anhang=None):
        daten = {"entity_id": entity_id, "title": titel, "message": text, "html": html}
        if anhang:
            daten["attachments"] = [anhang]
        await self.rest("POST", "/api/services/smtp/send_message", daten)

    async def addon_slug(self):
        try:
            info = await self.rest("GET", "/addons/self/info", basis=SUPERVISOR)
            return (info or {}).get("data", {}).get("slug")
        except HAError:
            return None
