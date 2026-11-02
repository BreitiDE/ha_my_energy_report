# Changelog

## 1.0.2

- Neu: Monats- und Jahresberichte mit eigenem Zeitplan (Monat: Tag 1.–28. + Uhrzeit, Jahr: Tag, Monat + Uhrzeit)
- Monatsbericht optional mit Vergleich zum Vorjahresmonat (im Zeitplan und beim Erstellen wählbar)
- „Bericht erstellen“ mit Umschalter Woche | Monat | Jahr, auch für vergangene Monate und Jahre
- PDF: Vergleichstabelle zur Vorperiode, Monats-/Jahreswerte, ertragsstärkste Tage
- Berichtsliste mit Art und Filter Woche/Monat/Jahr, Verlauf umschaltbar Wochen/Monate/Jahre
- Aufbewahrung gilt nur für Wochenberichte; Monats- und Jahresberichte bleiben erhalten

## 1.0.1

- Behoben: Keine Verbindung zu Home Assistant („Anmeldung fehlgeschlagen“), weil das SUPERVISOR_TOKEN beim Start über s6-overlay nicht ankam
- Genauere Fehlermeldung bei fehlgeschlagener Anmeldung

## 1.0.0

- Erste Version: Wochenbericht als PDF (PV, Verbrauch, Netz, Batterie, Wasser) aus dem Energie-Dashboard
- Zeitplan, Berichtsliste mit Vorschau und Download
- Versand per Push (Companion-App) und E-Mail (SMTP-Integration)
- Oberfläche auf Deutsch und Englisch
- Button „Unterstützen“ (PayPal)
