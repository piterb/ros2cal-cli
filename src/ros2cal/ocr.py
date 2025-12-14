"""Functions for turning roster JPGs into structured JSON via OpenAI."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from .prompts import SYSTEM_PROMPT_OCR, SYSTEM_PROMPT_PARSE


def _encode_image(path: Path) -> str:
    with path.open("rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def prepare_image_for_ocr(path: Path, scale: int = 2) -> Path:
    """Ensure the image is large enough and saved as PNG for better OCR."""
    img = Image.open(path)
    if img.width < 1500:
        img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    img = img.convert("RGB")
    out_path = path.with_suffix(path.suffix + "_processed.png")
    img.save(out_path, format="PNG")
    return out_path


class RosterParser:
    """End-to-end helper that OCRs and parses roster images into JSON."""

    def __init__(
        self,
        client: Optional[OpenAI] = None,
        ocr_model: str = "gpt-4.1",
        parse_model: str = "gpt-5.1",
    ) -> None:
        load_dotenv()
        self.client = client or OpenAI()
        self.ocr_model = ocr_model
        self.parse_model = parse_model

    def _ocr_image(self, image_path: Path) -> str:
        prepared_path = prepare_image_for_ocr(image_path)
        base64_image = _encode_image(prepared_path)

        response = self.client.responses.create(
            model=self.ocr_model,
            temperature=0,
            top_p=1,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT_OCR},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Transcribe the roster in this image exactly as text."},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{base64_image}", "detail": "high"},
                    ],
                },
            ],
        )
        return response.output_text

    def _parse_roster_text(self, roster_text: str) -> Dict[str, Any]:
        response = self.client.responses.create(
            model=self.parse_model,
            temperature=0,
            top_p=1,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT_PARSE},
                {"role": "user", "content": roster_text},
            ],
        )
        return json.loads(response.output_text)

    def parse_image(self, image_path: Path) -> Dict[str, Any]:
        """Return roster JSON for an image path."""
        ocr_text = self._ocr_image(image_path)
        return self._parse_roster_text(ocr_text)
