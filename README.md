# ros2cal-cli

CLI tool to turn airline rosters (jpg/jpeg/png) into ICS calendar files using OpenAI.

- OCR + parsing via OpenAI Responses API (see prompts in `ros2cal/prompts.py`).
- Output is `.ics` ready for Google/Apple Calendar import.
- Optional intermediate JSON export.

## Installation

- Python 3.14+.
- API key in env var `OPENAI_API_KEY` (you can use a `.env` file).
- Install dependencies and CLI:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Simplest:

```bash
ros2cal path/to/roster.jpg
```

Save JSON too + custom calendar name:

```bash
ros2cal roster.jpg \
  --json-output out/roster.json \
  --ics-output out/roster.ics \
  --calendar-name "My Roster" \
```

The `.ics` file is saved next to the input image by default (`roster.ics`).
