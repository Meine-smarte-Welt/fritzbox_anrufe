# SHA256 (Inhalt ab Zeile 2, d.h. dieser Datei ohne diese erste Zeile): 1f22199430beba85d4856f64da1c092ebe3b27b800d1b5bc47e9d0ac6a41476b
"""Anrufstatistik für den Anrufbeantworter (neu in v1.6.0).

Reine Auswertung, ohne Home-Assistant-Import (testbar). Eingabe sind die
bereits geladenen Nachrichten aller Anrufbeantworter; es gibt keine zusätzliche
Abfrage an die FRITZ!Box. Gezählt wird, was die Box aktuell speichert - wer
Nachrichten löscht, verringert die Statistik entsprechend.

Zeitangaben der Box sind ohne Zeitzone; sie gelten als Ortszeit der FRITZ!Box
(= in der Regel die von Home Assistant).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

MAX_LISTED_CALLS = 50
DAYS_SHOWN = 14


def build_stats(calls: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    """Statistik aus Nachrichten berechnen.

    ``calls``: je Nachricht ``{"slot", "date" (datetime|None), "number",
    "name", "duration", "new"}``. ``now``: aktuelle Ortszeit (ohne Zeitzone).
    Nachrichten ohne Datum zählen zur Gesamtzahl, nicht zu den Zeiträumen.
    """
    dated = sorted(
        (call for call in calls if isinstance(call.get("date"), datetime)),
        key=lambda call: call["date"],
        reverse=True,
    )
    today = now.date()
    by_day = {today - timedelta(days=offset): 0 for offset in range(DAYS_SHOWN - 1, -1, -1)}
    last_7 = last_30 = today_count = 0
    by_hour = [0] * 24
    for call in dated:
        day = call["date"].date()
        age = (today - day).days
        if age == 0:
            today_count += 1
        if 0 <= age < 7:
            last_7 += 1
        if 0 <= age < 30:
            last_30 += 1
        if day in by_day:
            by_day[day] += 1
        by_hour[call["date"].hour] += 1

    listed = [
        {
            "timestamp": call["date"].isoformat(),
            "date": call["date"].strftime("%d.%m.%Y"),
            "time": call["date"].strftime("%H:%M"),
            "number": call.get("number"),
            "name": call.get("name"),
            "duration": call.get("duration"),
            "new": bool(call.get("new")),
            "slot": call.get("slot"),
        }
        for call in dated[:MAX_LISTED_CALLS]
    ]
    last = dated[0] if dated else None
    return {
        "total": len(calls),
        "new": sum(1 for call in calls if call.get("new")),
        "today": today_count,
        "last_7_days": last_7,
        "last_30_days": last_30,
        "last_call": last["date"].isoformat() if last else None,
        "last_call_date": last["date"].strftime("%d.%m.%Y") if last else None,
        "last_call_time": last["date"].strftime("%H:%M") if last else None,
        "last_call_number": last.get("number") if last else None,
        "last_call_name": last.get("name") if last else None,
        "by_day": [{"date": day.isoformat(), "count": count} for day, count in by_day.items()],
        "by_hour": by_hour,
        "calls": listed,
    }
