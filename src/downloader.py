"""yt-dlp로 유튜브/틱톡/레딧 등 URL에서 최고 화질 mp4를 input/source.mp4로 다운로드."""
from __future__ import annotations

from pathlib import Path

from .utils import INPUT_DIR, media_duration, require_binary, run_ffmpeg

SOURCE_PATH = INPUT_DIR / "source.mp4"


def download(url: str, out_path: Path = SOURCE_PATH) -> Path:
    return download_with_info(url, out_path)[0]


def download_with_info(url: str, out_path: Path = SOURCE_PATH) -> tuple[Path, dict]:
    """다운로드 후 (경로, 원본 정보{id,title,uploader,webpage_url,extractor}) 반환."""
    import yt_dlp

    require_binary("ffmpeg")  # 영상+오디오 병합에 필요
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # 임시 이름으로 받은 뒤 성공 시에만 교체 → 실패해도 기존 source.mp4 보존
    stem = out_path.with_name(out_path.stem + "_download")
    for old in out_path.parent.glob(stem.name + ".*"):
        old.unlink()

    opts = {
        # mp4(h264)+m4a 우선, 없으면 최고 화질 아무 포맷 → mp4로 병합/리먹스
        "format": "bv*[ext=mp4][vcodec^=avc]+ba[ext=m4a]/bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        "outtmpl": str(stem) + ".%(ext)s",
        "merge_output_format": "mp4",
        "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
        "noplaylist": True,
        "quiet": False,
        "no_warnings": True,
        "retries": 3,
        "http_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    }
    print(f"[download] {url}")
    with yt_dlp.YoutubeDL(opts) as ydl:
        raw = ydl.extract_info(url, download=True) or {}
    if raw.get("_type") == "playlist" and raw.get("entries"):
        raw = next((e for e in raw["entries"] if e), raw)
    info = {k: raw.get(k) for k in ("id", "title", "uploader", "webpage_url", "extractor_key")}
    info["webpage_url"] = info.get("webpage_url") or url

    cands = [p for p in out_path.parent.glob(stem.name + ".*") if not p.name.endswith((".part", ".ytdl"))]
    mp4 = [p for p in cands if p.suffix.lower() == ".mp4"]
    if not cands:
        raise RuntimeError("다운로드된 파일을 찾을 수 없습니다.")
    (mp4 or cands)[0].replace(out_path)
    for left in out_path.parent.glob(stem.name + ".*"):
        left.unlink(missing_ok=True)
    print(f"[download] 저장 완료: {out_path}")
    return out_path, info


def trim_source(path: Path = SOURCE_PATH, max_sec: float = 30.0) -> float:
    """max_sec보다 길면 앞부분만 잘라 H.264/AAC로 정규화. 최종 길이(초) 반환."""
    dur = media_duration(path)
    if max_sec and dur > max_sec + 0.1:
        tmp = path.with_name(path.stem + "_trim.mp4")
        print(f"[download] {dur:.1f}초 → {max_sec:.0f}초로 컷")
        run_ffmpeg(["-i", str(path), "-t", f"{max_sec}", "-map", "0:v:0", "-map", "0:a:0?",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "44100", str(tmp)], desc="trim")
        tmp.replace(path)
        dur = media_duration(path)
    return dur
