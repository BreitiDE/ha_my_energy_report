# My Energy Report

## Voraussetzungen

- Ein eingerichtetes **Energie-Dashboard** (Einstellungen → Dashboards → Energie). Die App liest
  daraus alle Quellen: Solar, Netzbezug/Einspeisung, Batterie und Wasser.
- Für Push: die **Companion-App** auf dem Handy (`notify.mobile_app_…`).
- Für E-Mail: die **SMTP-Integration** mit mindestens einem Empfänger.

## Bedienung

- **Übersicht:** Kennzahlen, letzte Berichte, Verlauf der letzten Wochen.
- **Berichte:** alle Berichte mit Vorschau, Download, erneutem Versand, Neu erstellen und Löschen.
  „Bericht erstellen …“ erzeugt den Bericht für eine beliebige abgeschlossene Woche.
- **Einstellungen:** Zeitplan (Wochentag, Uhrzeit), Anlagenname, Anlagenleistung, Aufbewahrung,
  Sprache sowie die Empfänger für Push und E-Mail mit Testfunktion.

Der Bericht umfasst immer die letzte abgeschlossene Woche (Mo–So). Die PDFs liegen unter
`/media/my_energy_report` und sind auch im Medienbrowser sichtbar.

---

## Requirements (English)

A configured energy dashboard; the Companion app for push; the SMTP integration for e-mail.
Reports are stored in `/media/my_energy_report`. Language: Settings → Language.
