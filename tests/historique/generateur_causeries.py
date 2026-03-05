
# fichier tests/generateur_causeries.py produit le fichier ICS pour nextcloud
#Le script : génère les dates aléatoires ; génère les UUID ; construit un fichier ICS strictement conforme RFC 5545 ; écrit le fichier causeries_bord_du_lac.ics sur ton ordinateur

import uuid
import random
from datetime import datetime, timedelta

# -----------------------------
# PARAMÈTRES GÉNÉRAUX
# -----------------------------

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 9, 1)

themes = [
    "IA",
    "Lacs de données",
    "RAG",
    "Prompts systèmes",
    "Logiciels libres",
    "Éthique et morale"
]

visio_link = "https://bbb.fdn.fr/rooms/ysp-xu9-cgf-vrh/join"
public_calendar = "https://hae.frama.space/apps/calendar/p/dZNWNCErJNPoQdcy"

# -----------------------------
# RFC 5545 : FOLDING DES LIGNES
# -----------------------------

def fold_line(line, limit=75):
    """Plie une ligne ICS selon RFC 5545 (75 caractères max)."""
    if len(line) <= limit:
        return line
    folded = []
    while len(line) > limit:
        folded.append(line[:limit])
        line = " " + line[limit:]
    folded.append(line)
    return "\n".join(folded)

def fold_lines(lines):
    """Applique fold_line à une liste de lignes."""
    return "\n".join(fold_line(line) for line in lines)

# -----------------------------
# GÉNÉRATION DES DATES
# -----------------------------

def generate_event_dates():
    events = []
    current = start_date

    while current < end_date:
        week_days = list(range(7))
        chosen_days = random.sample(week_days, 2)

        for d in chosen_days:
            event_day = current + timedelta(days=d)

            if event_day >= end_date:
                continue

            hour = random.randint(9, 18)
            minute = random.choice([0, 15, 30, 45])

            start_dt = event_day.replace(hour=hour, minute=minute, second=0)
            end_dt = start_dt + timedelta(minutes=90)

            events.append((start_dt, end_dt))

        current += timedelta(days=7)

    return sorted(events)

# -----------------------------
# FORMATAGE ICS
# -----------------------------

def format_dt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")

def generate_ics():
    events = generate_event_dates()

    ics = []
    ics.append("BEGIN:VCALENDAR")
    ics.append("VERSION:2.0")
    ics.append("CALSCALE:GREGORIAN")
    ics.append("PRODID:-//Causeries au bord du lac//FR")
    ics.append("X-WR-CALNAME:Causeries au bord du lac")

    # Bloc VTIMEZONE Europe/Paris
    ics.append("BEGIN:VTIMEZONE")
    ics.append("TZID:Europe/Paris")
    ics.append("BEGIN:STANDARD")
    ics.append("TZOFFSETFROM:+0200")
    ics.append("TZOFFSETTO:+0100")
    ics.append("TZNAME:CET")
    ics.append("DTSTART:19701025T030000")
    ics.append("RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU")
    ics.append("END:STANDARD")
    ics.append("BEGIN:DAYLIGHT")
    ics.append("TZOFFSETFROM:+0100")
    ics.append("TZOFFSETTO:+0200")
    ics.append("TZNAME:CEST")
    ics.append("DTSTART:19700329T020000")
    ics.append("RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU")
    ics.append("END:DAYLIGHT")
    ics.append("END:VTIMEZONE")

    theme_index = 0

    for start_dt, end_dt in events:
        theme = themes[theme_index % len(themes)]
        theme_index += 1

        uid = str(uuid.uuid4())
        now = datetime.utcnow()

        ics.append("BEGIN:VEVENT")
        ics.append(f"UID:{uid}")
        ics.append(f"DTSTAMP:{format_dt(now)}Z")
        ics.append(f"CREATED:{format_dt(now)}Z")
        ics.append(f"LAST-MODIFIED:{format_dt(now)}Z")
        ics.append("SEQUENCE:0")
        ics.append("STATUS:CONFIRMED")

        ics.append(f"SUMMARY:Causeries au bord du lac : {theme}")
        ics.append(f"DTSTART;TZID=Europe/Paris:{format_dt(start_dt)}")
        ics.append(f"DTEND;TZID=Europe/Paris:{format_dt(end_dt)}")

        description = (
            "Session de réflexion collective autour des enjeux liés aux IA, aux lacs "
            "de données, aux RAG, aux prompts systèmes, aux logiciels libres, et aux "
            "questions d'éthique et de morale."
        )
        ics.append(f"DESCRIPTION:{description}")

        ics.append(f"LOCATION:{visio_link}")
        ics.append(f"URL:{public_calendar}")
        ics.append("END:VEVENT")

    ics.append("END:VCALENDAR")

    return fold_lines(ics)

# -----------------------------
# ÉCRITURE DU FICHIER
# -----------------------------

with open("causeries_bord_du_lac.ics", "w", encoding="utf-8") as f:
    f.write(generate_ics())

print("Fichier 'causeries_bord_du_lac.ics' généré avec succès (RFC 5545 OK).")
