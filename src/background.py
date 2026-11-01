"""최하단 1080x1920 배경 루프 영상 준비.

assets/bg/bg_loop.mp4 가 없으면 어두운 우주 그라데이션 + 반짝이는 별(Pillow) 프레임을 FFmpeg로
인코딩하면서 노이즈/비네팅 필터를 입혀
끊김 없이 반복 가능한 10초 루프 영상을 자동 생성한다.
"""
from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .utils import BG_DIR, FPS, HEIGHT, ROOT, WIDTH, require_binary

BG_PATH = BG_DIR / "bg_loop.mp4"
LOOP_SEC = 10
BG_FPS = 15  # 별 반짝임 프레임 (출력은 30fps로 변환)


def _gradient() -> Image.Image:
    """세로 방향 우주 그라데이션 + 은은한 성운 얼룩 (정적)."""
    top, mid, bot = (4, 3, 14), (26, 16, 64), (6, 20, 40)
    col = Image.new("RGB", (1, HEIGHT))
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        a, b, k = (top, mid, t * 2) if t < 0.5 else (mid, bot, (t - 0.5) * 2)
        col.putpixel((0, y), tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)))
    base = col.resize((WIDTH, HEIGHT))
    neb = Image.new("RGB", (WIDTH // 4, HEIGHT // 4), (0, 0, 0))
    d = ImageDraw.Draw(neb)
    rnd = random.Random(7)
    for color in [(60, 30, 110), (20, 60, 120), (90, 30, 90)]:
        cx, cy = rnd.randrange(WIDTH // 4), rnd.randrange(HEIGHT // 4)
        r = rnd.randrange(60, 120)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    neb = neb.filter(ImageFilter.GaussianBlur(40)).resize((WIDTH, HEIGHT))
    return Image.blend(base, ImageChops.add(base, neb), 0.45)


def _stars(seed: int = 1, count: int = 420) -> list[tuple]:
    rnd = random.Random(seed)
    stars = []
    for _ in range(count):
        x, y = rnd.randrange(WIDTH), rnd.randrange(HEIGHT)
        r = rnd.choice([1, 1, 1, 1.5, 1.5, 2, 2.5, 3])
        tint = rnd.choice([(255, 255, 255), (200, 215, 255), (255, 235, 210)])
        k = rnd.choice([1, 2, 3])            # 주기 = LOOP_SEC / k → 루프 이음새 없음
        phase = rnd.random() * 2 * math.pi
        stars.append((x, y, r, tint, k, phase))
    return stars


def _frame(base: Image.Image, stars: list[tuple], t: float) -> Image.Image:
    img = base.copy()
    d = ImageDraw.Draw(img)
    for x, y, r, tint, k, phase in stars:
        b = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(2 * math.pi * k * t / LOOP_SEC + phase))
        if r >= 2:  # 큰 별은 은은한 광채
            g = r * 2.6
            d.ellipse([x - g, y - g, x + g, y + g], fill=tuple(int(c * b * 0.25) + 10 for c in tint))
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * b) for c in tint))
    return img


def ensure_background(force: bool = False) -> Path:
    if BG_PATH.exists() and BG_PATH.stat().st_size > 0 and not force:
        return BG_PATH
    BG_DIR.mkdir(parents=True, exist_ok=True)
    print("[bg] 배경 루프 영상 생성 중 (assets/bg/bg_loop.mp4)...")
    base, stars = _gradient(), _stars()
    cmd = [
        require_binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(BG_FPS), "-i", "-",
        # FFmpeg 필터: 필름 노이즈 + 비네팅
        "-vf", f"noise=alls=6:allf=t+u,vignette=PI/5,fps={FPS},format=yuv420p",
        "-t", str(LOOP_SEC), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-an", str(BG_PATH),
    ]
    proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(LOOP_SEC * BG_FPS):
            proc.stdin.write(_frame(base, stars, i / BG_FPS).tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    err = proc.stderr.read().decode("utf-8", "replace")
    if proc.wait() != 0:
        BG_PATH.unlink(missing_ok=True)
        raise RuntimeError(f"[background] FFmpeg 실패\n{err}")
    return BG_PATH


if __name__ == "__main__":
    print(ensure_background(force=True))
