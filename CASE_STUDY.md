# 📝 Case Study: Automated Roster → Google Calendar Pipeline

## Background
The goal was to eliminate manual transcription of pilot rosters into Google Calendar. Early experiments with classic OCR (e.g., Tesseract) produced unreliable text: misread times, broken flight numbers, and inconsistent tables. To get usable data we needed two things: higher OCR accuracy and a deterministic intermediate representation that could be reused for any export format.

## Architecture
At the top level it’s a single CLI command, `ros2cal roster.jpg`, but the pipeline is split into tight steps:
- **Preprocess**: resize small images (~2×) and save as PNG to reduce compression artifacts.
- **OCR**: OpenAI Vision (`gpt-4.1`, `detail: high`) with a transcription-only prompt.
- **Parse**: separate call to `gpt-5.1` with a strict contract for the canonical JSON schema (`events` with `flights`, `activities`, `is_all_day`, etc.).
- **Export**: JSON → ICS with Z and local times in descriptions, and colors keyed by `duty_type`.
- **Config**: `OPENAI_API_KEY` from `.env` or env vars; dependencies declared in `pyproject.toml`.

## Pain Points & Lessons Learned
The main pain point was OCR quality. Standard tools failed on roster layouts, so Vision models were mandatory. Even then, simple tricks helped: upscaling and PNG conversion noticeably reduced misreads. Splitting the workflow into two dedicated model calls—one for OCR (4.1) and one for semantic parsing (5.1)—improved consistency because each step could be constrained separately. Determinism mattered: `temperature=0`, `top_p=1`, and prompts that ban “creativity” kept the JSON stable run to run. When data is ambiguous, the parser is instructed to omit the entry or mark it with an `error` field instead of guessing.

**What actually helped**
- Image preprocessing: upscale small images (~2×) and save as PNG to cut compression noise.
- Vision model choice: `gpt-4.1` with `detail: high`.
- Strict transcription prompt: “no interpretation, no guessing.”
- Deterministic params: `temperature=0`, `top_p=1`.
- Two-stage flow: OCR/AI vision first, then parsing as a separate call with its own guardrails.

## Cost Snapshot
Using standard pricing as of 14 Dec 2025, a typical run lands around ~$0.05:
- AI Vision (gpt-4.1, OCR): input 1,646 tokens ($0.003292) + output 1,137 tokens ($0.009096) → $0.012388.
- Text-to-JSON (gpt-5.1, parsing): input 3,228 tokens ($0.004035) + output 2,715 tokens ($0.027150) → $0.031185.
- Total per roster: $0.0436 (round to $0.05). Cached input was 0 in this sample; hitting cache would lower the input cost further.

## Status / Next Ideas
Today the CLI, prompts, JSON→ICS formatter, docs, and packaging are done. Next steps that consider a thin web front end for drag-and-drop uploads that calls the same pipeline. 
