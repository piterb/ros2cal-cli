import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, List

DEFAULT_LOCAL_TZ = "Europe/Berlin"

# Mapping of colors by duty_type
COLOR_MAP = {
    "FLIGHT": "#4285F4",
    "DH": "#DB4437",
    "HSBY": "#F4B400",
    "A/L": "#0F9D58",
    # default for others
}


def parse_iso_utc(s: str) -> datetime:
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def format_dt_for_ics(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def format_time_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%H:%M") + "z"


def format_time_lt(dt: datetime, local_tz: str) -> str:
    local = dt.astimezone(ZoneInfo(local_tz))
    return local.strftime("%H:%M") + " LT"


def escape_ics_text(text: str) -> str:
    if text is None:
        return ""
    text = text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")
    text = text.replace("\n", "\\n")
    return text


def build_description(event: Dict[str, Any], local_tz: str = DEFAULT_LOCAL_TZ) -> str:
    duty_type = event.get("duty_type", "")
    start_dt = parse_iso_utc(event["start_utc"])
    end_dt = parse_iso_utc(event["end_utc"])

    checkin_z = format_time_z(start_dt)
    checkout_z = format_time_z(end_dt)
    checkin_lt = format_time_lt(start_dt, local_tz)
    checkout_lt = format_time_lt(end_dt, local_tz)

    lines: List[str] = []

    if duty_type in ("FLIGHT", "DH"):
        lines.append(f"CHECK-IN {checkin_z} ({checkin_lt})")

        flights = event.get("flights") or []
        for f in flights:
            fn = f.get("flight_number") or "UNKNOWN"
            dep_ap = f.get("departure_airport") or "???"
            arr_ap = f.get("arrival_airport") or "???"

            dep_dt = parse_iso_utc(f["departure_time_utc"])
            arr_dt = parse_iso_utc(f["arrival_time_utc"])
            dep_t = format_time_z(dep_dt)
            arr_t = format_time_z(arr_dt)

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

        activities = event.get("activities") or []
        for a in activities:
            sp = a.get("start_place") or "???"
            ep = a.get("end_place") or "???"

            sdt = parse_iso_utc(a["start_time_utc"])
            edt = parse_iso_utc(a["end_time_utc"])
            st = format_time_z(sdt)
            et = format_time_z(edt)

            lines.append(f"{sp} {st} -> {ep} {et}")

        lines.append(f"CHECK-OUT {checkout_z} ({checkout_lt})")

    return "\n".join(lines)


def event_to_ics(event: Dict[str, Any], calendar_name: str, local_tz: str) -> str:
    """
    Conversion of one event into VEVENT.
    - A/L as all-day (VALUE=DATE, DTEND one day later)
    - UID: duty_type|start_utc|end_utc
    - COLOR by duty_type (if exists in COLOR_MAP)
    """
    duty_type = event.get("duty_type", "DUTY")
    summary = duty_type

    start_dt = parse_iso_utc(event["start_utc"])
    end_dt = parse_iso_utc(event["end_utc"])

    # UID: duty_type|start_utc|end_utc
    start_iso = event["start_utc"]
    end_iso = event["end_utc"]
    uid = f"{duty_type}|{start_iso}|{end_iso}"

    description = build_description(event, local_tz)
    description_esc = escape_ics_text(description)
    summary_esc = escape_ics_text(summary)

    now_utc = datetime.now(timezone.utc)
    dtstamp = format_dt_for_ics(now_utc)

    color = COLOR_MAP.get(duty_type)

    vevent_lines: List[str] = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{dtstamp}"]

    # A/L all-day event
    is_all_day = event.get("is_all_day", False) or duty_type == "A/L"
    if is_all_day:
        start_date = start_dt.date()
        end_date = start_date + timedelta(days=1)
        dtstart_date = start_date.strftime("%Y%m%d")
        dtend_date = end_date.strftime("%Y%m%d")

        vevent_lines.append(f"DTSTART;VALUE=DATE:{dtstart_date}")
        vevent_lines.append(f"DTEND;VALUE=DATE:{dtend_date}")
    else:
        dtstart = format_dt_for_ics(start_dt)
        dtend = format_dt_for_ics(end_dt)
        vevent_lines.append(f"DTSTART:{dtstart}")
        vevent_lines.append(f"DTEND:{dtend}")

    vevent_lines.append(f"SUMMARY:{summary_esc}")
    vevent_lines.append(f"DESCRIPTION:{description_esc}")

    if color:
        vevent_lines.append(f"COLOR:{color}")

    vevent_lines.append("END:VEVENT")

    return "\r\n".join(vevent_lines)


def json_to_ics(
    data: Dict[str, Any],
    calendar_name: str = "Roster",
    local_tz: str = DEFAULT_LOCAL_TZ,
) -> str:
    events = data.get("events", [])

    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{calendar_name}//RosterToICS//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    vevents: List[str] = [event_to_ics(ev, calendar_name, local_tz) for ev in events]

    footer = ["END:VCALENDAR"]

    ics_lines = header + vevents + footer
    return "\r\n".join(ics_lines)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python json_to_ics.py roster.json [output.ics]")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else json_path.with_suffix(".ics")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    ics_content = json_to_ics(data, calendar_name="Roster", local_tz=DEFAULT_LOCAL_TZ)

    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(ics_content)

    print(f"ICS saved to: {out_path}")
