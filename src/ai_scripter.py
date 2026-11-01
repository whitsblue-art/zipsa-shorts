"""Gemini(gemini-2.5-flash)로 쇼츠 기획안(script.json)을 자동 생성한다.

1순위: 원본 영상 파일을 Files API로 업로드해 영상 자체를 분석
2순위: 업로드 실패 시 1초 단위 추출 프레임(JPEG)을 이미지로 전달
폴백 : API 키가 없거나 네트워크/응답 오류 시 기본 샘플 JSON(영상 길이에 맞춰 시간 보정) 반환
"""
from __future__ import annotations

import copy
import json
import os
import re
import time
from pathlib import Path

from .utils import INPUT_DIR, TEMP_DIR, media_duration, resolve, run_ffmpeg

MODEL = "gemini-2.5-flash"
SCRIPT_PATH = INPUT_DIR / "script.json"
MAX_FRAMES = 40

SAMPLE_SCRIPT: dict = {
    "video_file": "input/source.mp4",
    "bgm_file": "input/bgm.mp3",
    "bgm_volume": 0.25,
    "source_volume": 1.0,
    "top_title": {
        "line1": "{\\c&H00D7FF&}자는 줄{\\c&HFFFFFF&} 알았는데?",
        "line2": "역시 {\\c&H00D7FF&}엄마다...",
    },
    "subtitles": [
        {"start": 0.0, "end": 3.5, "type": "narration", "text": "유칼립투스 나무 위\\N코알라 가족"},
        {"start": 2.0, "end": 4.5, "type": "thought", "color": "green", "text": "* 엄마는 자고 *"},
        {"start": 4.5, "end": 8.0, "type": "narration",
         "text": "분명히 눈감고 있던 어미가\\N빛의 속도로 새끼를 잡아내고"},
        {"start": 8.0, "end": 12.0, "type": "thought", "color": "pink", "text": "* 힝... 무서웠다구 *"},
        {"start": 12.0, "end": 15.0, "type": "narration", "text": "오늘도 무사히\\N육아 성공"},
    ],
    "comments": [
        {"appear_at": 4.0, "likes": "1.5천", "text": "자다가도 애기 소리에 바로 반응하는 거 봐... 모성애는 위대하다"},
        {"appear_at": 8.0, "likes": "794", "text": "떨어질 뻔한 아기 코알라 꼭 안아주는 게 진짜 감동이네 ㅠㅠ"},
        {"appear_at": 11.5, "likes": "342", "text": "아기 코알라 놀라서 엄마 품 파고드는 거 너무 귀엽다"},
    ],
}
SAMPLE_DURATION = 15.0

PROMPT = """너는 구독자 100만 유튜브 쇼츠 채널 '해외 바이럴 동물/밈 큐레이션'의 메인 작가야.
첨부된 해외 바이럴 영상(길이 {duration:.1f}초)을 보고 한국 시청자용 쇼츠 기획안을 JSON으로만 출력해.

[작성 규칙]
1. top_title: 영상 내내 상단에 고정되는 2줄 훅 타이틀. 각 줄 12자 이내.
   핵심 키워드는 ASS 태그로 노란색 강조: {{\\\\c&H00D7FF&}}키워드{{\\\\c&HFFFFFF&}} (JSON 문자열 안이므로 역슬래시 2개)
2. subtitles: 3막 구조(도입-전개-반전/결말)로 시간순 배치. 모든 시간은 원본 영상 기준 초 단위(0 ~ {duration:.1f}).
   - type "narration": 상황 설명 자막, 1~2줄(줄바꿈은 \\\\N), 한 줄 15자 이내, 4~6개.
   - type "thought": 동물/인물의 속마음 대사. "* 대사 *" 형태로 양옆 별표. 짧고 귀엽고 웃기게. 2~4개.
     color는 "green" 또는 "pink".
   - narration끼리는 시간이 겹치지 않게. thought는 narration과 겹쳐도 됨.
3. comments: 한국 네티즌 말투(ㅋㅋ, ㅠㅠ, ~네, 반말 섞인 공감)의 베스트 댓글 정확히 3개, 각 40자 이내.
   appear_at은 영상 중반부부터 시간차를 두고 오름차순 (예: 길이의 30%, 55%, 80% 지점).
   likes는 "2.3천", "1.1만", "794" 같은 한국 유튜브 표기.
4. 영상에 실제로 나오는 장면과 타이밍에 정확히 맞출 것. 과장된 거짓 정보 금지.

[출력 JSON 스키마]
{{
  "top_title": {{"line1": "...", "line2": "..."}},
  "subtitles": [{{"start": 0.0, "end": 3.0, "type": "narration", "text": "..."}},
                {{"start": 1.5, "end": 4.0, "type": "thought", "color": "green", "text": "* ... *"}}],
  "comments": [{{"appear_at": 4.0, "likes": "1.5천", "text": "..."}}]
}}
"""


def sample_script(duration: float | None = None) -> dict:
    """오프라인/폴백용 샘플. duration이 주어지면 타임스탬프를 비례 보정."""
    data = copy.deepcopy(SAMPLE_SCRIPT)
    if duration and duration > 0:
        k = duration / SAMPLE_DURATION
        for s in data["subtitles"]:
            s["start"], s["end"] = round(s["start"] * k, 2), round(s["end"] * k, 2)
        for c in data["comments"]:
            c["appear_at"] = round(c["appear_at"] * k, 2)
    return data


def _extract_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def normalize_script(data: dict, duration: float, video_file: str, bgm_file: str) -> dict:
    """AI 응답을 렌더러가 안전하게 쓸 수 있도록 검증/보정."""
    out = {
        "video_file": video_file,
        "bgm_file": bgm_file,
        "bgm_volume": float(data.get("bgm_volume", 0.25)),
        "source_volume": float(data.get("source_volume", 1.0)),
        "top_title": {
            "line1": str((data.get("top_title") or {}).get("line1", "")).strip(),
            "line2": str((data.get("top_title") or {}).get("line2", "")).strip(),
        },
        "subtitles": [],
        "comments": [],
    }
    if not out["top_title"]["line1"] and not out["top_title"]["line2"]:
        out["top_title"] = copy.deepcopy(SAMPLE_SCRIPT["top_title"])
    for s in data.get("subtitles", []) or []:
        try:
            st, en = float(s["start"]), float(s["end"])
        except (KeyError, TypeError, ValueError):
            continue
        st, en = max(0.0, min(st, duration)), max(0.0, min(en, duration))
        if en - st < 0.3 or not str(s.get("text", "")).strip():
            continue
        item = {"start": round(st, 2), "end": round(en, 2),
                "type": "thought" if s.get("type") == "thought" else "narration",
                "text": str(s["text"]).strip()}
        if item["type"] == "thought":
            item["color"] = s.get("color", "green")
        out["subtitles"].append(item)
    out["subtitles"].sort(key=lambda x: x["start"])
    comments = [c for c in (data.get("comments") or []) if str(c.get("text", "")).strip()][:3]
    for i, c in enumerate(comments):
        try:
            at = float(c.get("appear_at"))
        except (TypeError, ValueError):
            at = duration * (0.3 + 0.25 * i)
        out["comments"].append({
            "appear_at": round(max(0.0, min(at, max(0.0, duration - 1.0))), 2),
            "likes": str(c.get("likes", "1천")),
            "text": str(c["text"]).strip(),
        })
    out["comments"].sort(key=lambda x: x["appear_at"])
    if not out["subtitles"] or not out["comments"]:
        fb = sample_script(duration)
        out["subtitles"] = out["subtitles"] or fb["subtitles"]
        out["comments"] = out["comments"] or fb["comments"]
    return out


def _extract_frames(video: Path, duration: float) -> list[Path]:
    fdir = TEMP_DIR / "frames"
    fdir.mkdir(parents=True, exist_ok=True)
    for old in fdir.glob("*.jpg"):
        old.unlink()
    fps = 1.0 if duration <= MAX_FRAMES else MAX_FRAMES / duration
    run_ffmpeg(["-i", str(video), "-vf", f"fps={fps:.4f},scale=512:-2",
                "-q:v", "4", str(fdir / "frame_%03d.jpg")], desc="extract frames")
    return sorted(fdir.glob("frame_*.jpg"))


def _call_gemini(video: Path, duration: float, api_key: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = PROMPT.format(duration=duration)
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.9)

    contents: list
    try:
        print("[ai] 원본 영상 업로드 중 (Gemini Files API)...")
        f = client.files.upload(file=str(video))
        t0 = time.time()
        while getattr(f.state, "name", str(f.state)) == "PROCESSING":
            if time.time() - t0 > 180:
                raise TimeoutError("영상 처리 대기 시간 초과")
            time.sleep(3)
            f = client.files.get(name=f.name)
        if getattr(f.state, "name", str(f.state)) != "ACTIVE":
            raise RuntimeError(f"업로드 상태 이상: {f.state}")
        contents = [f, prompt]
    except Exception as e:
        print(f"[ai] 영상 업로드 실패 → 1초 단위 프레임으로 대체 ({e})")
        frames = _extract_frames(video, duration)
        step = duration / max(1, len(frames))
        contents = []
        for i, fp in enumerate(frames):
            contents.append(f"[{i * step:.1f}초 프레임]")
            contents.append(types.Part.from_bytes(data=fp.read_bytes(), mime_type="image/jpeg"))
        contents.append(prompt)

    print(f"[ai] {MODEL} 기획안 생성 요청...")
    resp = client.models.generate_content(model=MODEL, contents=contents, config=config)
    return _extract_json(resp.text or "")


def generate_script(video_file: str = "input/source.mp4", bgm_file: str = "input/bgm.mp3",
                    out_path: Path = SCRIPT_PATH, offline: bool = False) -> dict:
    video = resolve(video_file)
    duration = media_duration(video)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    data: dict | None = None
    if offline or not api_key or api_key == "your_api_key_here":
        print("[ai] GEMINI_API_KEY 없음/오프라인 모드 → 샘플 기획안 사용")
    else:
        for attempt in range(2):
            try:
                data = _call_gemini(video, duration, api_key)
                break
            except Exception as e:
                print(f"[ai] Gemini 호출 실패 ({attempt + 1}/2): {e}")
        if data is None:
            print("[ai] 샘플 기획안으로 폴백")
    script = normalize_script(data or sample_script(duration), duration, video_file, bgm_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ai] 기획안 저장: {out_path}")
    return script
