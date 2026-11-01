"""공용 유틸리티: 프로젝트 경로, FFmpeg 실행, ffprobe, 필터 경로 이스케이프."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
BG_DIR = ASSETS_DIR / "bg"
INPUT_DIR = ROOT / "input"
TEMP_DIR = ROOT / "temp"
OUTPUT_DIR = ROOT / "output"

WIDTH, HEIGHT = 1080, 1920
FPS = 30


def ensure_dirs() -> None:
    for d in (FONTS_DIR, BG_DIR, INPUT_DIR, TEMP_DIR, OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)


def resolve(path: str | os.PathLike) -> Path:
    """상대 경로는 프로젝트 루트 기준으로 해석."""
    p = Path(path)
    return p if p.is_absolute() else (ROOT / p)


def require_binary(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise RuntimeError(
            f"'{name}' 실행 파일을 찾을 수 없습니다. FFmpeg를 설치하고 PATH에 추가해주세요.\n"
            "  - Windows: winget install Gyan.FFmpeg\n"
            "  - macOS  : brew install ffmpeg\n"
            "  - Linux  : sudo apt install ffmpeg"
        )
    return exe


def run_ffmpeg(args: list[str], desc: str = "ffmpeg") -> None:
    """항상 프로젝트 루트를 cwd로 FFmpeg 실행 (필터 내 상대경로 사용을 위해)."""
    cmd = [require_binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"[{desc}] FFmpeg 실패 (code {proc.returncode})\n{proc.stderr.strip()[-3000:]}")


def probe(path: str | os.PathLike) -> dict:
    cmd = [
        require_binary("ffprobe"), "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(resolve(path)),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe 실패: {path}\n{proc.stderr}")
    return json.loads(proc.stdout)


def media_duration(path: str | os.PathLike) -> float:
    info = probe(path)
    dur = info.get("format", {}).get("duration")
    if dur is None:
        for s in info.get("streams", []):
            if s.get("duration"):
                dur = s["duration"]
                break
    return float(dur or 0.0)


def has_audio(path: str | os.PathLike) -> bool:
    return any(s.get("codec_type") == "audio" for s in probe(path).get("streams", []))


def filter_path(path: str | os.PathLike) -> str:
    """FFmpeg 필터(subtitles/ass) 인자로 안전하게 넣을 수 있는 경로 문자열.

    1) 가능하면 프로젝트 루트 기준 상대경로(FFmpeg는 항상 cwd=ROOT로 실행)를 사용해
       Windows 드라이브 문자(C:)나 역슬래시 문제를 원천 차단한다.
    2) 상대경로가 불가능하면(다른 드라이브 등) 슬래시로 통일한 뒤
       필터 옵션 레벨의 특수문자(\\ : ')를 이스케이프하고, 필터그래프 레벨에서
       작은따옴표로 감싼다.
    """
    p = resolve(path)
    try:
        rel = os.path.relpath(p, ROOT)
        if not rel.startswith(".."):
            rel_posix = Path(rel).as_posix()
            if all(c.isalnum() or c in "/._-" for c in rel_posix):
                return rel_posix
    except ValueError:  # Windows: 다른 드라이브
        pass
    if "'" in str(p) and p.is_file():
        # 작은따옴표가 포함된 경로는 temp/ 안의 안전한 이름으로 복사해서 사용
        safe = TEMP_DIR / ("safe_" + "".join(c if c.isalnum() or c in "._-" else "_" for c in p.name))
        shutil.copyfile(p, safe)
        return filter_path(safe)
    s = p.as_posix()
    # 옵션 레벨 이스케이프: '\' 와 ':' (예: C:/ → C\:/)
    s = s.replace("\\", "\\\\").replace(":", "\\:")
    # 필터그래프 레벨: 작은따옴표로 감싸면 , ; [ ] 공백이 리터럴로 취급됨
    return f"'{s}'"
