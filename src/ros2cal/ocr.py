"""Functions for turning roster JPGs into structured JSON via OpenAI."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from .prompts import SYSTEM_PROMPT_OCR, SYSTEM_PROMPT_PARSE


@dataclass
class CallUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cached_output_tokens: int = 0
    total_tokens: Optional[int] = None

    @property
    def effective_total(self) -> int:
        """Return total tokens if provided, otherwise sum input+output."""
        if self.total_tokens is not None:
            return self.total_tokens
        return (self.input_tokens or 0) + (self.output_tokens or 0)


@dataclass
class RosterParseResult:
    data: Dict[str, Any]
    ocr_usage: CallUsage
    parse_usage: CallUsage


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

    def _extract_usage(self, response: Any) -> CallUsage:
        """Best-effort extraction of token usage, handling both attr and dict styles."""
        usage_obj = getattr(response, "usage", None)
        if usage_obj is None and isinstance(response, dict):
            usage_obj = response.get("usage")

        def get_value(obj: Any, key: str, default: Optional[int] = 0) -> Optional[int]:
            if obj is None:
                return default
            if isinstance(obj, dict):
                value = obj.get(key, default)
            else:
                value = getattr(obj, key, default)

            if value is None:
                return default
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        input_tokens = get_value(usage_obj, "input_tokens")
        output_tokens = get_value(usage_obj, "output_tokens")
        total_tokens = get_value(usage_obj, "total_tokens", None) if usage_obj is not None else None

        input_details = None
        output_details = None
        if isinstance(usage_obj, dict):
            input_details = usage_obj.get("input_token_details") or usage_obj.get("prompt_tokens_details")
            output_details = usage_obj.get("output_token_details") or usage_obj.get("completion_tokens_details")
        else:
            input_details = getattr(usage_obj, "input_token_details", None) or getattr(
                usage_obj, "prompt_tokens_details", None
            )
            output_details = getattr(usage_obj, "output_token_details", None) or getattr(
                usage_obj, "completion_tokens_details", None
            )

        cached_input_tokens = get_value(input_details, "cached_tokens")
        cached_output_tokens = get_value(output_details, "cached_tokens")

        return CallUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            cached_output_tokens=cached_output_tokens,
            total_tokens=total_tokens,
        )

    def _ocr_image(self, image_path: Path) -> tuple[str, CallUsage]:
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
        usage = self._extract_usage(response)
        return response.output_text, usage

    def _parse_roster_text(self, roster_text: str) -> tuple[Dict[str, Any], CallUsage]:
        response = self.client.responses.create(
            model=self.parse_model,
            temperature=0,
            top_p=1,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT_PARSE},
                {"role": "user", "content": roster_text},
            ],
        )
        usage = self._extract_usage(response)
        return json.loads(response.output_text), usage

    def parse_image(self, image_path: Path) -> RosterParseResult:
        """Return roster JSON for an image path, with token usage for both calls."""
        ocr_text, ocr_usage = self._ocr_image(image_path)
        parsed_json, parse_usage = self._parse_roster_text(ocr_text)
        return RosterParseResult(data=parsed_json, ocr_usage=ocr_usage, parse_usage=parse_usage)
