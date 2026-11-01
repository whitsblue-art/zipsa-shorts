"""yt-dlp로 유튜브/틱톡/레딧 등 URL에서 최고 화질 mp4를 input/source.mp4로 다운로드."""
from __future__ import annotations

from pathlib import Path

from .utils import INPUT_DIR, require_binary

SOURCE_PATH = INPUT_DIR / "source.mp4"


def download(url: str, out_path: Path = SOURCE_PATH) -> Path:
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
        ydl.download([url])

    cands = [p for p in out_path.parent.glob(stem.name + ".*") if not p.name.endswith((".part", ".ytdl"))]
    mp4 = [p for p in cands if p.suffix.lower() == ".mp4"]
    if not cands:
        raise RuntimeError("다운로드된 파일을 찾을 수 없습니다.")
    (mp4 or cands)[0].replace(out_path)
    for left in out_path.parent.glob(stem.name + ".*"):
        left.unlink(missing_ok=True)
    print(f"[download] 저장 완료: {out_path}")
    return out_path
