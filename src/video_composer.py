"""FFmpeg filter_complex 기반 1080x1920 3단 레이아웃 렌더러.

레이어 순서 (아래 → 위)
 1) 배경 루프 영상 (assets/bg/bg_loop.mp4, 무한 반복)
 2) 원본 영상: 가로 1080 맞춤 + 세로 최대 970px 크롭, Y 380~1350 중앙 배치
    재사용 콘텐츠 회피: 미세 배속(기본 1.02x) + eq 채도/대비 보정 + 선택적 좌우 반전
 3) 베스트 댓글 PNG 카드: appear_at 시점에 페이드+슬라이드 인, 끝까지 유지 (Y 1400~1840)
 4) ASS 자막: 상단 고정 타이틀 / 속마음 / 상황 설명
오디오: 원본(atempo 배속 보정) + BGM(무한 반복) 믹싱, 리미터, 마지막 1초 페이드아웃
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .background import ensure_background
from .comment_generator import generate_comment_cards
from .fonts import get_font
from .subtitle_generator import build_ass
from .utils import (FONTS_DIR, FPS, HEIGHT, OUTPUT_DIR, TEMP_DIR, WIDTH, filter_path,
                    has_audio, media_duration, resolve, run_ffmpeg)

VIDEO_TOP, VIDEO_BOTTOM = 380, 1350
VIDEO_H = VIDEO_BOTTOM - VIDEO_TOP           # 970
COMMENT_TOP, COMMENT_BOTTOM = 1400, 1840
COMMENT_GAP = 10
SLIDE_PX = 30
FADE_SEC = 0.35


@dataclass
class RenderOptions:
    speed: float = 1.02
    saturation: float = 1.05
    contrast: float = 1.02
    flip: bool = False
    max_duration: float = 0.0       # 0 = 원본 길이 그대로
    crf: int = 20
    preset: str = "veryfast"


def _layout_cards(cards) -> list[tuple[Path, int, int]]:
    """카드들을 위→아래로 쌓고, 영역(1400~1840)을 넘으면 균일하게 축소. (path, x, y) 반환."""
    if not cards:
        return []
    shadow = 10
    visual = [c.height - 2 * shadow for c in cards]
    avail = COMMENT_BOTTOM - COMMENT_TOP - COMMENT_GAP * (len(cards) - 1)
    scale = min(1.0, avail / sum(visual))
    placed = []
    y = COMMENT_TOP
    for c, vh in zip(cards, visual):
        path = c.path
        w, h = c.width, c.height
        if scale < 0.999:
            w, h = round(c.width * scale), round(c.height * scale)
            path = c.path.with_name(c.path.stem + "_fit.png")
            Image.open(c.path).resize((w, h), Image.LANCZOS).save(path)
        s = shadow * scale
        placed.append((path, round((WIDTH - w) / 2), round(y - s)))
        y += vh * scale + COMMENT_GAP
    return placed


def compose(script: dict, output: str | Path = OUTPUT_DIR / "final_shorts.mp4",
            opts: RenderOptions | None = None) -> Path:
    opts = opts or RenderOptions()
    speed = max(0.5, min(2.0, float(opts.speed or 1.0)))
    output = resolve(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    video = resolve(script.get("video_file", "input/source.mp4"))
    if not video.exists():
        raise FileNotFoundError(f"원본 영상이 없습니다: {video}")
    bgm_file = script.get("bgm_file")
    bgm = resolve(bgm_file) if bgm_file else None
    if bgm is not None and not bgm.exists():
        print(f"[render] BGM 파일 없음 → BGM 없이 진행: {bgm}")
        bgm = None

    duration = media_duration(video) / speed
    if opts.max_duration and duration > opts.max_duration:
        duration = opts.max_duration
    if duration <= 0:
        raise RuntimeError("원본 영상 길이를 확인할 수 없습니다.")
    D = f"{duration:.3f}"

    font = get_font()
    bg = ensure_background()
    ass_path = build_ass(script, duration, TEMP_DIR / "subtitles.ass", speed=speed, font=font)
    comments = script.get("comments", [])[:3]
    placed = _layout_cards(generate_comment_cards(comments))

    # ---------- 입력 ----------
    args: list[str] = ["-stream_loop", "-1", "-i", str(bg), "-i", str(video)]
    idx_bgm = None
    next_idx = 2
    if bgm is not None:
        args += ["-stream_loop", "-1", "-i", str(bgm)]
        idx_bgm = next_idx
        next_idx += 1
    card_inputs = []
    for path, _, _ in placed:
        args += ["-loop", "1", "-framerate", str(FPS), "-t", D, "-i", str(path)]
        card_inputs.append(next_idx)
        next_idx += 1

    # ---------- 비디오 필터 ----------
    f: list[str] = []
    f.append(f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
             f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},trim=duration={D},setpts=PTS-STARTPTS[bg]")
    main = [f"setpts=(PTS-STARTPTS)/{speed}", f"fps={FPS}",
            f"scale={WIDTH}:-2:flags=lanczos", f"crop={WIDTH}:'min(ih,{VIDEO_H})'"]
    if opts.flip:
        main.append("hflip")
    main.append(f"eq=saturation={opts.saturation}:contrast={opts.contrast}")
    main.append("setsar=1")
    f.append("[1:v]" + ",".join(main) + "[main]")
    f.append(f"[bg][main]overlay=x=0:y='{VIDEO_TOP}+({VIDEO_H}-h)/2':eof_action=repeat[v0]")

    last = "v0"
    for n, ((_, x, y), inp) in enumerate(zip(placed, card_inputs), start=1):
        at = float(comments[n - 1].get("appear_at", 0)) / speed
        at = max(0.0, min(at, duration - 0.5))
        f.append(f"[{inp}:v]format=rgba,fade=t=in:st={at:.3f}:d={FADE_SEC}:alpha=1[c{n}]")
        f.append(
            f"[{last}][c{n}]overlay=x={x}:"
            f"y='{y}-{SLIDE_PX}*max(0,1-(t-{at:.3f})/{FADE_SEC})':"
            f"enable='gte(t,{at:.3f})':eval=frame[v{n}]"
        )
        last = f"v{n}"
    f.append(f"[{last}]ass=filename={filter_path(ass_path)}:fontsdir={filter_path(FONTS_DIR)},"
             f"format=yuv420p[vout]")

    # ---------- 오디오 필터 ----------
    src_vol = float(script.get("source_volume", 1.0))
    bgm_vol = float(script.get("bgm_volume", 0.25))
    fade_st = max(0.0, duration - 1.0)
    a_parts = []
    if has_audio(video):
        f.append(f"[1:a]aresample=44100,atempo={speed},volume={src_vol}[asrc]")
        a_parts.append("[asrc]")
    if idx_bgm is not None:
        f.append(f"[{idx_bgm}:a]aresample=44100,volume={bgm_vol}[abgm]")
        a_parts.append("[abgm]")
    if len(a_parts) == 2:
        f.append("[asrc][abgm]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[amix]")
        a_in = "[amix]"
    elif len(a_parts) == 1:
        a_in = a_parts[0]
    else:
        f.append("anullsrc=r=44100:cl=stereo[asil]")
        a_in = "[asil]"
    f.append(f"{a_in}aformat=channel_layouts=stereo,apad,atrim=duration={D},"
             f"afade=t=out:st={fade_st:.3f}:d=1,alimiter=limit=0.95[aout]")

    filter_complex = ";\n".join(f)
    (TEMP_DIR / "filter_complex.txt").write_text(filter_complex, encoding="utf-8")  # 디버깅용

    args += [
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-t", D, "-r", str(FPS),
        "-c:v", "libx264", "-preset", opts.preset, "-crf", str(opts.crf),
        "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
        str(output),
    ]
    print(f"[render] 합성 시작 → {output} (길이 {duration:.2f}s, 배속 {speed}x"
          f"{', 좌우반전' if opts.flip else ''})")
    run_ffmpeg(args, desc="compose")
    print(f"[render] 완료: {output}")
    return output
