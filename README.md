# ros2cal-cli

CLI na preklad leteckých rozpisov (jpg/jpeg/png) do ICS kalendára cez OpenAI.

- OCR a parsovanie zabezpečuje OpenAI Responses API (pozri prompty v `ros2cal/prompts.py`).
- Výstup je priamo `.ics` pripravené na import do Google/Apple kalendára.
- Voliteľne uloží aj medzikrok JSON.

## Inštalácia

- Python 3.14+.
- API kľúč v premennej prostredia `OPENAI_API_KEY` (môžeš použiť `.env`).
- Nainštaluj závislosti a CLI:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Použitie

Najjednoduchšie:

```bash
ros2cal path/to/roster.jpg
```

Uloženie aj JSON + vlastný názov kalendára a timezone pre popisy:

```bash
ros2cal roster.jpg \
  --json-output out/roster.json \
  --ics-output out/roster.ics \
  --calendar-name "My Roster" \
  --local-tz Europe/Prague
```

Výstupný súbor `.ics` sa predvolene uloží vedľa vstupného obrázka (`roster.ics`).
