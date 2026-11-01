"""해외 바이럴 동물/밈 큐레이션 쇼츠 자동 생성 파이프라인.

사용법
  python main.py --url "https://www.youtube.com/shorts/xxxx"   # 다운로드 → AI 기획 → 렌더링 전체 자동
  python main.py --script input/script.json                    # 기존 기획안으로 렌더링만
  python main.py                                               # 더미 테스트 모드 (오프라인 동작 확인)

공통 옵션
  --flip               좌우 반전 (재사용 콘텐츠 감지 회피)
  --speed 1.02         미세 배속 (기본 1.02)
  --bgm PATH           배경음악 파일 (기본 input/bgm.mp3, 없으면 원본 오디오만)
  --output PATH        결과 파일 (기본 output/final_shorts.mp4)
  --max-duration SEC   최대 길이 제한 (기본 0 = 제한 없음)
  --offline            Gemini 호출 없이 샘플 기획안 사용
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Windows 콘솔에서도 한글 로그가 깨지지 않도록
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.utils import INPUT_DIR, OUTPUT_DIR, ensure_dirs, media_duration, require_binary, resolve, run_ffmpeg

DUMMY_DURATION = 15


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent / ".env")
    except ImportError:
        pass


def create_dummy_assets(force: bool = False) -> None:
    """15초짜리 테스트용 원본 영상 / 배경 루프 / BGM / 샘플 script.json 생성."""
    from src.ai_scripter import SCRIPT_PATH, sample_script
    from src.background import ensure_background

    src = INPUT_DIR / "source.mp4"
    if force or not src.exists():
        print("[test] 더미 원본 영상 생성: input/source.mp4 (15초, 1280x720, 사인파 오디오)")
        run_ffmpeg([
            "-f", "lavfi", "-i", f"testsrc2=s=1280x720:r=30:d={DUMMY_DURATION}",
            "-f", "lavfi", "-i", f"sine=frequency=330:sample_rate=44100:duration={DUMMY_DURATION}",
            "-filter_complex", "[0:v]hue=h=t*12,format=yuv420p[v];[1:a]volume=0.25,aformat=channel_layouts=stereo[a]",
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-shortest", str(src),
        ], desc="dummy source")

    bgm = INPUT_DIR / "bgm.mp3"
    if force or not bgm.exists():
        print("[test] 더미 BGM 생성: input/bgm.mp3 (C-E-G 아르페지오)")
        # 0.25초마다 C5-E5-G5-E5 반복되는 부드러운 아르페지오 (+ 감쇠 엔벨로프)
        expr = ("0.25*sin(2*PI*t*(523.25*eq(mod(floor(t*4),4),0)+659.25*eq(mod(floor(t*4),4),1)"
                "+783.99*eq(mod(floor(t*4),4),2)+659.25*eq(mod(floor(t*4),4),3)))*exp(-3*mod(t,0.25))"
                "+0.08*sin(2*PI*130.81*t)")
        run_ffmpeg([
            "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={DUMMY_DURATION}",
            "-ac", "2", "-c:a", "libmp3lame", "-b:a", "128k", str(bgm),
        ], desc="dummy bgm")

    ensure_background(force=force)

    if force or not SCRIPT_PATH.exists():
        print("[test] 샘플 기획안 생성: input/script.json")
        SCRIPT_PATH.write_text(json.dumps(sample_script(DUMMY_DURATION), ensure_ascii=False, indent=2),
                               encoding="utf-8")


def load_script(path: str | Path) -> dict:
    p = resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"기획안 파일이 없습니다: {p}")
    return json.loads(p.read_text(encoding="utf-8-sig"))


def verify_output(path: Path) -> None:
    from src.utils import probe
    info = probe(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    print(f"[check] {path.name}: {v['width']}x{v['height']} {v.get('r_frame_rate')} "
          f"{v['codec_name']} / audio={a['codec_name'] if a else '없음'} / "
          f"{media_duration(path):.2f}s / {path.stat().st_size / 1e6:.1f}MB")
    if (v["width"], v["height"]) != (1080, 1920):
        raise RuntimeError("출력 해상도가 1080x1920이 아닙니다.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="해외 바이럴 동물/밈 쇼츠 자동 생성기")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--url", help="원본 영상 URL (유튜브/틱톡/레딧 등) → 전체 자동 실행")
    mode.add_argument("--script", help="기존 script.json으로 렌더링만 실행")
    ap.add_argument("--bgm", default=None, help="배경음악 경로 (기본: input/bgm.mp3)")
    ap.add_argument("--output", default=str(OUTPUT_DIR / "final_shorts.mp4"))
    ap.add_argument("--flip", action="store_true", help="좌우 반전")
    ap.add_argument("--speed", type=float, default=1.02, help="미세 배속 (기본 1.02)")
    ap.add_argument("--max-duration", type=float, default=0.0, help="최대 길이(초), 0=제한 없음")
    ap.add_argument("--offline", action="store_true", help="Gemini 호출 없이 샘플 기획안 사용")
    ap.add_argument("--force-dummy", action="store_true", help="테스트 모드에서 더미 에셋 강제 재생성")
    args = ap.parse_args(argv)

    _load_env()
    ensure_dirs()
    require_binary("ffmpeg")
    require_binary("ffprobe")

    from src.video_composer import RenderOptions, compose

    t0 = time.time()
    if args.url:
        from src.ai_scripter import generate_script
        from src.downloader import download
        download(args.url)
        script = generate_script("input/source.mp4", args.bgm or "input/bgm.mp3", offline=args.offline)
    elif args.script:
        script = load_script(args.script)
    else:
        print("=== 더미 테스트 모드 (인자 없음) ===")
        create_dummy_assets(force=args.force_dummy)
        script = load_script(INPUT_DIR / "script.json")

    if args.bgm:
        script["bgm_file"] = args.bgm

    out = compose(script, args.output, RenderOptions(
        speed=args.speed, flip=args.flip, max_duration=args.max_duration))
    verify_output(out)
    print(f"✅ 완료 ({time.time() - t0:.1f}s): {out}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"❌ 오류: {e}", file=sys.stderr)
        sys.exit(1)
