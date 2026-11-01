"""굵은 한글 고딕 폰트 탐색/다운로드 유틸리티.

우선순위
 1) assets/fonts/ 에 이미 연결된 폰트
 2) OS 시스템 폰트 (맑은 고딕 Bold, AppleSDGothicNeo, 나눔고딕 ExtraBold/Bold, Noto Sans CJK KR Bold ...)
 3) 오픈소스 폰트 자동 다운로드 (Pretendard ExtraBold → 나눔고딕 ExtraBold)
 4) fc-list 로 찾은 아무 한글 폰트 (최후의 수단)

선택된 폰트는 assets/fonts/ 로 복사되어 FFmpeg ass 필터의 fontsdir(상대경로)과
Pillow 렌더링에 동일하게 사용된다.
"""
from __future__ import annotations

import glob
import os
import shutil
import struct
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .utils import FONTS_DIR

FONT_EXTS = (".ttf", ".otf", ".ttc")
TEST_CHARS = "가나다한글뷁"

DOWNLOAD_URLS = [
    ("Pretendard-ExtraBold.otf",
     "https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/public/static/Pretendard-ExtraBold.otf"),
    ("Pretendard-ExtraBold.otf",
     "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/public/static/Pretendard-ExtraBold.otf"),
    ("NanumGothic-ExtraBold.ttf",
     "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-ExtraBold.ttf"),
]


@dataclass
class FontInfo:
    path: Path          # assets/fonts 내부 경로
    family: str         # ASS 스타일에 넣을 패밀리 이름
    index: int = 0      # TTC 컬렉션 내 인덱스 (Pillow용)

    def pil(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self.path), size, index=self.index)


def _system_candidates() -> list[str]:
    home = Path.home()
    if sys.platform.startswith("win"):
        windir = os.environ.get("WINDIR", r"C:\Windows")
        local = os.environ.get("LOCALAPPDATA", "")
        dirs = [os.path.join(windir, "Fonts"), os.path.join(local, "Microsoft", "Windows", "Fonts")]
        names = ["malgunbd.ttf", "NanumGothicExtraBold.ttf", "NanumGothicBold.ttf",
                 "NanumSquareEB.ttf", "Pretendard-ExtraBold.otf", "Pretendard-Bold.otf"]
        return [os.path.join(d, n) for d in dirs for n in names]
    if sys.platform == "darwin":
        dirs = ["/System/Library/Fonts", "/Library/Fonts", str(home / "Library/Fonts"),
                "/System/Library/Fonts/Supplemental"]
        names = ["AppleSDGothicNeo.ttc", "NanumGothicExtraBold.ttf", "NanumGothicBold.ttf",
                 "Pretendard-ExtraBold.otf", "AppleGothic.ttf"]
        return [os.path.join(d, n) for d in dirs for n in names]
    pats = [
        "/usr/share/fonts/**/Pretendard-ExtraBold.otf",
        "/usr/share/fonts/**/NanumGothicExtraBold.ttf",
        "/usr/share/fonts/**/NanumGothicBold.ttf",
        "/usr/share/fonts/**/NotoSansCJK*-Bold.ttc",
        "/usr/share/fonts/**/NotoSansKR-Bold*.ttf",
        str(home / ".local/share/fonts/**/*Bold*.[ot]t[fc]"),
        str(home / ".fonts/**/*Bold*.[ot]t[fc]"),
    ]
    out: list[str] = []
    for p in pats:
        out.extend(sorted(glob.glob(p, recursive=True)))
    return out


def _supports_korean(path: Path, index: int = 0) -> bool:
    try:
        font = ImageFont.truetype(str(path), 40, index=index)

        def render(ch: str) -> bytes:
            img = Image.new("L", (60, 60), 0)
            ImageDraw.Draw(img).text((5, 5), ch, font=font, fill=255)
            return img.tobytes()

        # .notdef(두부) 글리프와 같은 모양이면 미지원
        tofu = render("\uffff")
        return all(render(ch) != tofu and any(render(ch)) for ch in TEST_CHARS)
    except Exception:
        return False


def _best_index(path: Path) -> int:
    """TTC라면 Bold 계열 페이스 인덱스를 고른다."""
    if path.suffix.lower() != ".ttc":
        return 0
    best, best_score = 0, -1
    order = ["Heavy", "Black", "ExtraBold", "Bold", "SemiBold", "Medium", "Regular"]
    for i in range(32):
        try:
            _, style = ImageFont.truetype(str(path), 20, index=i).getname()
        except Exception:
            break
        score = next((len(order) - k for k, w in enumerate(order) if w.lower() in (style or "").lower()), 0)
        # 지나치게 굵은 Heavy/Black보다 ExtraBold/Bold 선호
        if style and style.lower() in ("bold", "extrabold"):
            score += 10
        if score > best_score:
            best, best_score = i, score
    return best


def _name_table_family(path: Path, index: int = 0) -> str | None:
    """OpenType 'name' 테이블에서 nameID 1(레거시 패밀리명)을 읽는다.

    libass는 nameID 1/4로 폰트를 매칭하므로, Pillow(FreeType)가 돌려주는
    타이포그래피 패밀리명(nameID 16, 예: 'Pretendard')을 쓰면 매칭에 실패해
    다른 폰트로 대체된다. (예: 'Pretendard ExtraBold' 이어야 함)
    """
    try:
        data = path.read_bytes()
        off = 0
        if data[:4] == b"ttcf":
            off = struct.unpack(">I", data[12 + 4 * index:16 + 4 * index])[0]
        num_tables = struct.unpack(">H", data[off + 4:off + 6])[0]
        for i in range(num_tables):
            rec = off + 12 + 16 * i
            tag, _cs, toff, _len = struct.unpack(">4sIII", data[rec:rec + 16])
            if tag != b"name":
                continue
            _fmt, count, str_off = struct.unpack(">HHH", data[toff:toff + 6])
            found: dict[tuple, str] = {}
            for j in range(count):
                pid, eid, lid, nid, ln, no = struct.unpack(">HHHHHH", data[toff + 6 + 12 * j:toff + 18 + 12 * j])
                if nid != 1:
                    continue
                raw = data[toff + str_off + no:toff + str_off + no + ln]
                text = raw.decode("utf-16-be", "replace") if pid in (0, 3) else raw.decode("latin-1", "replace")
                found[(pid, lid)] = text.strip("\x00 ")
            for key in [(3, 0x409)] + list(found):
                if found.get(key):
                    return found[key]
    except Exception:
        pass
    return None


def _make_info(path: Path) -> FontInfo:
    idx = _best_index(path)
    family = _name_table_family(path, idx)
    if not family:
        family, _style = ImageFont.truetype(str(path), 20, index=idx).getname()
    return FontInfo(path=path, family=family or path.stem, index=idx)


def _link_into_assets(src: Path) -> Path:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    dst = FONTS_DIR / src.name
    if not dst.exists() or dst.stat().st_size != src.stat().st_size:
        shutil.copyfile(src, dst)
    return dst


def _download() -> Path | None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in DOWNLOAD_URLS:
        dst = FONTS_DIR / name
        if dst.exists() and dst.stat().st_size > 10_000:
            return dst
        try:
            print(f"[font] 다운로드 시도: {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) < 10_000:
                continue
            dst.write_bytes(data)
            if _supports_korean(dst):
                return dst
            dst.unlink(missing_ok=True)
        except Exception as e:  # 네트워크 차단 등
            print(f"[font]   실패: {e}")
    return None


def _fc_list_korean() -> list[str]:
    if not shutil.which("fc-list"):
        return []
    try:
        out = subprocess.run(["fc-list", ":lang=ko", "file", "style"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace").stdout
    except Exception:
        return []
    rows = [l.split(":")[0].strip() for l in out.splitlines() if l.strip()]
    bold = [r for r, l in zip(rows, out.splitlines()) if "bold" in l.lower()]
    return bold + [r for r in rows if r not in bold]


@lru_cache(maxsize=1)
def get_font() -> FontInfo:
    # 1) 이미 연결된 폰트
    if FONTS_DIR.exists():
        for p in sorted(FONTS_DIR.iterdir()):
            if p.suffix.lower() in FONT_EXTS and _supports_korean(p, _best_index(p)):
                info = _make_info(p)
                print(f"[font] 사용: {p.name} ({info.family})")
                return info
    # 2) 시스템 폰트
    for c in _system_candidates():
        p = Path(c)
        if p.is_file() and _supports_korean(p, _best_index(p)):
            info = _make_info(_link_into_assets(p))
            print(f"[font] 시스템 폰트 연결: {p} ({info.family})")
            return info
    # 3) 다운로드
    dl = _download()
    if dl:
        info = _make_info(dl)
        print(f"[font] 다운로드 폰트 사용: {dl.name} ({info.family})")
        return info
    # 4) 아무 한글 폰트
    for c in _fc_list_korean():
        p = Path(c)
        if p.is_file() and p.suffix.lower() in FONT_EXTS and _supports_korean(p, _best_index(p)):
            info = _make_info(_link_into_assets(p))
            print(f"[font] (대체) 한글 폰트 연결: {p} ({info.family})")
            return info
    raise RuntimeError(
        "한글 폰트를 찾을 수 없습니다. 굵은 한글 폰트(.ttf/.otf)를 assets/fonts/ 에 넣어주세요."
    )


if __name__ == "__main__":
    f = get_font()
    print(f)
