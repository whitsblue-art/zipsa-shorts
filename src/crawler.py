"""해외 바이럴 동물 영상 후보 발굴 + 처리 이력 관리.

1순위: Reddit 동물 서브레딧 주간 인기 영상 (top.json, 로그인 불필요)
2순위: yt-dlp YouTube 검색 (해외 동물 쇼츠)
TikTok은 공개 검색 API가 없어 자동 발굴 대신 --url / --urls 로 직접 넣는 방식을 지원한다.
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

from .utils import ROOT

DATA_DIR = ROOT / "data"
HISTORY_FILE = DATA_DIR / "history.json"

SUBREDDITS = ["AnimalsBeingMoms", "AnimalsBeingBros", "aww", "AnimalsBeingDerps",
              "AnimalsBeingFunny", "Eyebleach", "rarepuppers", "cats"]
YT_QUERIES = ["baby animal rescue shorts", "mother animal protecting baby shorts",
              "cute animal plot twist shorts", "funny cat reaction shorts", "dog unexpected moment shorts"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) zipsa-shorts/1.0"


# ---------------- 이력 ----------------
def _load() -> dict:
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data.get("processed"), list):
                return data
        except Exception:
            pass
    return {"processed": []}


def processed_keys() -> set[str]:
    keys = set()
    for item in _load()["processed"]:
        if isinstance(item, str):
            keys.add(item)
        else:
            keys.update(k for k in (item.get("id"), item.get("url")) if k)
    return keys


def is_processed(*keys: str | None) -> bool:
    done = processed_keys()
    return any(k and k in done for k in keys)


def add_history(vid: str, url: str, title: str = "", output: str = "", youtube_id: str = "") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = _load()
    data["processed"].append({
        "id": vid, "url": url, "title": title, "output": output,
        "youtube_id": youtube_id, "date": datetime.now().isoformat(timespec="seconds"),
    })
    HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------- 발굴 ----------------
def _from_reddit(min_sec: float, max_sec: float, min_ups: int) -> dict | None:
    import requests

    subs = SUBREDDITS[:]
    random.shuffle(subs)
    done = processed_keys()
    for sub in subs:
        try:
            res = requests.get(f"https://www.reddit.com/r/{sub}/top.json",
                               params={"t": "week", "limit": 50}, headers={"User-Agent": UA}, timeout=10)
            if res.status_code != 200:
                print(f"  - r/{sub}: HTTP {res.status_code}")
                continue
            for child in res.json().get("data", {}).get("children", []):
                p = child.get("data", {})
                vid = f"reddit_{p.get('id')}"
                if vid in done or not p.get("is_video") or p.get("over_18"):
                    continue
                rv = (p.get("media") or {}).get("reddit_video") or {}
                dur = rv.get("duration") or 0
                if min_sec <= dur <= max_sec and p.get("ups", 0) >= min_ups:
                    url = f"https://www.reddit.com{p.get('permalink')}"
                    print(f"  -> Reddit r/{sub}: {p.get('title')} ({dur}초, 👍{p.get('ups')})")
                    return {"id": vid, "url": url, "title": p.get("title", "")}
        except Exception as e:
            print(f"  - r/{sub}: {e}")
    return None


def _from_youtube(max_sec: float) -> dict | None:
    import yt_dlp

    done = processed_keys()
    queries = YT_QUERIES[:]
    random.shuffle(queries)
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
    for q in queries[:3]:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                res = ydl.extract_info(f"ytsearch15:{q}", download=False) or {}
        except Exception as e:
            print(f"  - YouTube 검색 실패 ({q}): {e}")
            continue
        for e in res.get("entries") or []:
            if not e or not e.get("id"):
                continue
            vid = f"youtube_{e['id']}"
            dur = e.get("duration") or 0
            if vid in done or (dur and dur > max(60, max_sec * 2)):
                continue
            url = f"https://www.youtube.com/watch?v={e['id']}"
            print(f"  -> YouTube: {e.get('title')} ({dur or '?'}초)")
            return {"id": vid, "url": url, "title": e.get("title", "")}
    return None


def find_viral_video(min_sec: float = 8, max_sec: float = 40, min_ups: int = 500) -> dict:
    print("[crawl] 해외 바이럴 동물 영상 탐색 중...")
    found = _from_reddit(min_sec, max_sec, min_ups)
    if not found:
        print("[crawl] Reddit에서 못 찾음 → YouTube 검색으로 전환")
        found = _from_youtube(max_sec)
    if not found:
        raise RuntimeError("새로운 바이럴 영상을 찾지 못했습니다. (네트워크/차단 여부 확인, 또는 --url 로 직접 지정)")
    return found
