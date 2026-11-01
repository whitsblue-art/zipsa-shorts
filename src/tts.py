"""Edge-TTS로 상황 설명(narration) 자막을 한국어 음성으로 만든다. (선택 기능)

네트워크 오류 등으로 실패하면 빈 목록을 돌려주고 파이프라인은 음성 없이 계속 진행한다.
"""
from __future__ import annotations

import asyncio
import re

from .utils import TEMP_DIR, media_duration

DEFAULT_VOICE = "ko-KR-SunHiNeural"   # 여성. 남성: ko-KR-InJoonNeural
TAG_RE = re.compile(r"\{[^}]*\}")


def _clean(text: str) -> str:
    text = TAG_RE.sub("", text).replace("\\N", " ").replace("\n", " ")
    return " ".join(text.split())


async def _synth_all(jobs: list[tuple[str, str]], voice: str, rate: str) -> None:
    import edge_tts
    for text, path in jobs:
        await edge_tts.Communicate(text, voice=voice, rate=rate).save(path)


def make_voiceover(script: dict, voice: str = DEFAULT_VOICE, rate: str = "+10%") -> list[dict]:
    jobs, items = [], []
    for i, sub in enumerate(s for s in script.get("subtitles", []) if s.get("type") == "narration"):
        text = _clean(str(sub.get("text", "")))
        if not text:
            continue
        path = TEMP_DIR / f"tts_{i + 1}.mp3"
        jobs.append((text, str(path)))
        items.append({"file": f"temp/{path.name}", "start": float(sub.get("start", 0))})
    if not jobs:
        return []
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[tts] Edge-TTS 나레이션 {len(jobs)}개 생성 중 ({voice})...")
    try:
        asyncio.run(_synth_all(jobs, voice, rate))
        for it in items:
            media_duration(TEMP_DIR / it["file"].split("/")[-1])  # 유효성 확인
    except Exception as e:
        print(f"[tts] 실패 → 나레이션 없이 진행 ({e})")
        return []
    return items
