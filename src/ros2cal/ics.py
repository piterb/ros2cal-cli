"""JSON-to-ICS conversion utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List
from zoneinfo import ZoneInfo

DEFAULT_LOCAL_TZ = "Europe/Berlin"

COLOR_MAP = {
    "FLIGHT": "#4285F4",
    "DH": "#DB4437",
    "HSBY": "#F4B400",
    "A/L": "#0F9D58",
}


def _parse_iso_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _format_dt_for_ics(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _format_time_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%H:%M") + "z"


def _format_time_lt(dt: datetime, local_tz: str) -> str:
    local = dt.astimezone(ZoneInfo(local_tz))
    return local.strftime("%H:%M") + " LT"


def _escape_ics_text(text: str | None) -> str:
    if text is None:
        return ""
    text = text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")
    return text.replace("\n", "\\n")


def _build_description(event: Dict[str, Any], local_tz: str) -> str:
    duty_type = event.get("duty_type", "")
    start_dt = _parse_iso_utc(event["start_utc"])
    end_dt = _parse_iso_utc(event["end_utc"])

    checkin_z = _format_time_z(start_dt)
    checkout_z = _format_time_z(end_dt)
    checkin_lt = _format_time_lt(start_dt, local_tz)
    checkout_lt = _format_time_lt(end_dt, local_tz)

    lines: List[str] = []

    if duty_type in ("FLIGHT", "DH"):
        lines.append(f"CHECK-IN {checkin_z} ({checkin_lt})")

        for flight in event.get("flights") or []:
            fn = flight.get("flight_number") or "UNKNOWN"
            dep_ap = flight.get("departure_airport") or "???"
            arr_ap = flight.get("arrival_airport") or "???"

            dep_dt = _parse_iso_utc(flight["departure_time_utc"])
            arr_dt = _parse_iso_utc(flight["arrival_time_utc"])
            dep_t = _format_time_z(dep_dt)
            arr_t = _format_time_z(arr_dt)

            lines.append(f"{fn} {dep_ap} {dep_t} {arr_ap} {arr_t}")

        lines.append(f"CHECK-OUT {checkout_z} ({checkout_lt})")

    elif duty_type == "HSBY":
        lines.append("Standby (HSBY)")
        lines.append(f"{checkin_z} – {checkout_z} ({checkin_lt} – {checkout_lt})")
        loc = event.get("location")
        if loc:
            lines.append(f"Location: {loc}")

    elif duty_type == "A/L":
        lines.append("Annual leave")

    else:
        lines.append(f"Duty: {duty_type}")
        lines.append(f"CHECK-IN {checkin_z} ({checkin_lt})")

        for activity in event.get("activities") or []:
            start_place = activity.get("start_place") or "???"
            end_place = activity.get("end_place") or "???"

            start_dt_activity = _parse_iso_utc(activity["start_time_utc"])
            end_dt_activity = _parse_iso_utc(activity["end_time_utc"])
            start_t = _format_time_z(start_dt_activity)
            end_t = _format_time_z(end_dt_activity)

            lines.append(f"{start_place} {start_t} -> {end_place} {end_t}")

        lines.append(f"CHECK-OUT {checkout_z} ({checkout_lt})")

    return "\n".join(lines)


def _event_to_ics(event: Dict[str, Any], local_tz: str, calendar_name: str) -> str:
    duty_type = event.get("duty_type", "DUTY")
    summary = _escape_ics_text(duty_type)

    start_dt = _parse_iso_utc(event["start_utc"])
    end_dt = _parse_iso_utc(event["end_utc"])
    uid = f"{duty_type}|{event['start_utc']}|{event['end_utc']}"

    description_esc = _escape_ics_text(_build_description(event, local_tz))
    dtstamp = _format_dt_for_ics(datetime.now(timezone.utc))

    color = COLOR_MAP.get(duty_type)

    lines: List[str] = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{dtstamp}"]

    is_all_day = event.get("is_all_day", False) or duty_type == "A/L"
    if is_all_day:
        start_date = start_dt.date()
        end_date = start_date + timedelta(days=1)
        lines.append(f"DTSTART;VALUE=DATE:{start_date.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{end_date.strftime('%Y%m%d')}")
    else:
        lines.append(f"DTSTART:{_format_dt_for_ics(start_dt)}")
        lines.append(f"DTEND:{_format_dt_for_ics(end_dt)}")

    lines.append(f"SUMMARY:{summary}")
    lines.append(f"DESCRIPTION:{description_esc}")
    if color:
        lines.append(f"COLOR:{color}")
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def json_to_ics(
    roster: Dict[str, Any],
    *,
    calendar_name: str = "Roster",
    local_tz: str = DEFAULT_LOCAL_TZ,
) -> str:
    events: Iterable[Dict[str, Any]] = roster.get("events", [])
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{calendar_name}//RosterToICS//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    body = [_event_to_ics(event, local_tz, calendar_name) for event in events]
    footer = ["END:VCALENDAR"]
    return "\r\n".join(header + body + footer)
