"""Save camera frames and sidecar metadata when a warning fires."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .rules import Finding

WARSAW = ZoneInfo("Europe/Warsaw")
SAFE_NAME = re.compile(r"[^a-zA-Z0-9_.-]+")


def _stamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=WARSAW).strftime("%Y%m%dT%H%M%S")


def _safe(value: str) -> str:
    cleaned = SAFE_NAME.sub("-", value).strip("-")
    return cleaned or "event"


def save_evidence(
    directory: Path,
    ts: float,
    frames: dict[str, bytes],
    findings: list[Finding],
) -> list[str]:
    if not frames or not findings:
        return []
    directory.mkdir(parents=True, exist_ok=True)
    stamp = _stamp(ts)
    rule = _safe(findings[0].rule)
    level = _safe(findings[0].level)
    saved: list[str] = []
    summary = {
        "ts": datetime.fromtimestamp(ts, tz=WARSAW).isoformat(),
        "findings": [
            {
                "level": item.level,
                "rule": item.rule,
                "message": item.message,
                "details": item.details,
                "should_stop": item.should_stop,
            }
            for item in findings
        ],
    }
    for role, jpeg in frames.items():
        if not jpeg:
            continue
        stem = directory / f"{stamp}_{_safe(role)}_{level}_{rule}"
        image_path = stem.with_suffix(".jpg")
        meta_path = stem.with_suffix(".json")
        image_bytes = annotate_jpeg(jpeg, findings, role)
        image_path.write_bytes(image_bytes)
        meta_path.write_text(json.dumps(summary | {"camera": role}, indent=2) + "\n", encoding="utf-8")
        saved.append(str(image_path))
        saved.append(str(meta_path))
    return saved


def annotate_jpeg(jpeg: bytes, findings: list[Finding], role: str) -> bytes:
    """Stamp a banner onto the frame when Pillow is installed; otherwise return the original."""
    try:
        from io import BytesIO

        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return jpeg
    try:
        image = Image.open(BytesIO(jpeg)).convert("RGB")
    except Exception:
        return jpeg
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    lines = [f"Papaj Watcher  {role}"] + [f"{item.level}: {item.message}" for item in findings[:4]]
    padding = 6
    line_h = 14
    height = padding * 2 + line_h * len(lines)
    draw.rectangle((0, 0, image.width, height), fill=(140, 20, 20) if any(item.level == "critical" for item in findings) else (140, 110, 20))
    y = padding
    for line in lines:
        draw.text((padding, y), line[:140], fill=(255, 255, 255), font=font)
        y += line_h
    out = BytesIO()
    image.save(out, format="JPEG", quality=85)
    return out.getvalue()
