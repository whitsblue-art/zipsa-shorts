#!/usr/bin/env python3
"""올인원 쇼츠 공장: 발굴 → 다운로드 → AI 기획 → (TTS) → 렌더링 → (업로드).

  python shorts_factory.py                       # 바이럴 영상 1개 자동 발굴 → 쇼츠 1개 생성
  python shorts_factory.py --count 3             # 3개 연속 생성
  python shorts_factory.py --url "틱톡/유튜브/레딧 URL"   # 지정 영상으로 생성 (여러 번 사용 가능)
  python shorts_factory.py --urls urls.txt       # 파일의 URL들을 한 줄씩 처리
  python shorts_factory.py --test                # 네트워크 없이 더미 영상으로 동작 확인
  python shorts_factory.py --url URL --upload    # 생성 후 YouTube에 비공개 업로드

결과: output/<날짜_시간>_<영상ID>.mp4 + 같은 이름의 .json(업로드 제목/설명/태그/출처)
이력: data/history.json (이미 처리한 영상은 자동으로 건너뜀, --force 로 무시)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from main import _load_env, create_dummy_assets, load_script, verify_output
from src.utils import ASSETS_DIR, INPUT_DIR, OUTPUT_DIR, ensure_dirs, require_binary


def pick_bgm(explicit: str | None) -> str | None:
    """--bgm > assets/bgm/ 안의 랜덤 곡 > input/bgm.mp3 > 없음."""
    if explicit:
        return explicit
    lib = sorted(p for p in (ASSETS_DIR / "bgm").glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav"))
    if lib:
        return str(random.choice(lib))
    if (INPUT_DIR / "bgm.mp3").exists():
        return "input/bgm.mp3"
    return None


def credit_line(info: dict) -> str:
    who = info.get("uploader") or ""
    url = info.get("webpage_url") or info.get("url") or ""
    return f"📹 원본: {who} {url}".strip() if (who or url) else ""


def safe_name(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "_", text)[:40].strip("_") or "video"


def process(job: dict, args) -> Path:
    """job = {"id", "url", "title"}  (test 모드면 url 없음)"""
    from src.ai_scripter import generate_script
    from src.video_composer import RenderOptions, compose

    bgm = pick_bgm(args.bgm)
    info = dict(job)
    if args.test:
        create_dummy_assets(force=False)
        script = load_script(INPUT_DIR / "script.json")
        from src.ai_scripter import _norm_metadata
        script["metadata"] = _norm_metadata(script.get("metadata"))
    else:
        from src.downloader import download_with_info, trim_source
        _, dl = download_with_info(job["url"])
        info.update({k: v for k, v in dl.items() if v})
        if not job.get("id") or job["id"].startswith("url_"):
            info["id"] = f"{(dl.get('extractor_key') or 'web').lower()}_{dl.get('id') or job['id']}"
        trim_source(max_sec=args.max_sec)
        script = generate_script("input/source.mp4", bgm or "", offline=args.offline,
                                 source_title=info.get("title") or "")
    script["bgm_file"] = bgm

    if args.tts:
        from src.tts import make_voiceover
        script["voiceover"] = make_voiceover(script, voice=args.voice)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"{stamp}_{safe_name(info.get('id', 'test'))}.mp4"
    compose(script, out, RenderOptions(speed=args.speed, flip=args.flip))
    verify_output(out)
    shutil.copyfile(out, OUTPUT_DIR / "final_shorts.mp4")  # 최신 결과 바로가기

    meta = script.get("metadata", {})
    desc = meta.get("youtube_description", "")
    credit = credit_line(info) if not args.test else ""
    if credit:
        desc = f"{desc}\n\n{credit}"
    meta_out = {
        "title": meta.get("youtube_title", ""), "description": desc, "tags": meta.get("tags", []),
        "source": {k: info.get(k) for k in ("id", "url", "webpage_url", "title", "uploader")},
        "video": out.name,
    }
    out.with_suffix(".json").write_text(json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[meta] 제목: {meta_out['title']}")

    yt_id = ""
    if args.upload:
        from src.uploader import upload
        yt_id = upload(out, meta_out["title"], desc, meta_out["tags"], privacy=args.privacy)

    if not args.test:
        from src.crawler import add_history
        add_history(info["id"], job["url"], info.get("title", ""), out.name, yt_id)
    return out


def build_jobs(args) -> list[dict]:
    if args.test:
        return [{"id": "test", "title": "dummy"}]
    from src.crawler import find_viral_video, is_processed

    urls = list(args.url or [])
    if args.urls:
        lines = Path(args.urls).read_text(encoding="utf-8-sig").splitlines()
        urls += [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    if urls:
        jobs = []
        for u in urls:
            if not args.force and is_processed(u):
                print(f"[skip] 이미 처리한 영상: {u} (다시 만들려면 --force)")
                continue
            jobs.append({"id": f"url_{len(jobs) + 1}", "url": u, "title": ""})
        return jobs
    return [None] * args.count  # 자동 발굴은 처리 직전에 하나씩 (이력 반영)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="올인원 쇼츠 공장")
    ap.add_argument("--url", action="append", help="원본 URL (TikTok/YouTube/Reddit 등, 여러 번 지정 가능)")
    ap.add_argument("--urls", help="URL 목록 파일 (한 줄에 하나, #은 주석)")
    ap.add_argument("--count", type=int, default=1, help="자동 발굴 모드에서 만들 개수")
    ap.add_argument("--test", action="store_true", help="네트워크 없이 더미 영상으로 테스트")
    ap.add_argument("--max-sec", type=float, default=30, help="원본 최대 길이(초), 넘으면 앞부분만 사용")
    ap.add_argument("--bgm", help="배경음악 파일 (기본: assets/bgm/ 랜덤 → input/bgm.mp3)")
    ap.add_argument("--tts", action="store_true", help="상황 설명 자막을 Edge-TTS 나레이션으로 추가")
    ap.add_argument("--voice", default="ko-KR-SunHiNeural", help="TTS 목소리 (남성: ko-KR-InJoonNeural)")
    ap.add_argument("--flip", action="store_true", help="좌우 반전")
    ap.add_argument("--speed", type=float, default=1.02)
    ap.add_argument("--offline", action="store_true", help="Gemini 대신 샘플 대본")
    ap.add_argument("--upload", action="store_true", help="생성 후 YouTube 업로드")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--force", action="store_true", help="이미 처리한 URL도 다시 생성")
    args = ap.parse_args(argv)

    _load_env()
    ensure_dirs()
    require_binary("ffmpeg")
    require_binary("ffprobe")
    (ASSETS_DIR / "bgm").mkdir(parents=True, exist_ok=True)

    made, failed = [], 0
    for i, job in enumerate(build_jobs(args), start=1):
        t0 = time.time()
        print(f"\n===== [{i}] 쇼츠 생성 시작 =====")
        try:
            if job is None:
                from src.crawler import find_viral_video
                job = find_viral_video(max_sec=max(40, args.max_sec))
            out = process(job, args)
            made.append(out)
            print(f"✅ [{i}] 완료 ({time.time() - t0:.1f}s): {out}")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            failed += 1
            print(f"❌ [{i}] 실패: {e}", file=sys.stderr)
    print(f"\n총 {len(made)}개 생성, {failed}개 실패")
    for m in made:
        print(f"  - {m}")
    return 0 if made else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
