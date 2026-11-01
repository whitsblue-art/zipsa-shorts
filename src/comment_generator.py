"""Pillow로 유튜브 베스트 댓글 모양 PNG 카드를 생성한다.

카드 디자인 (가로 960px, 세로 약 120~170px, 모서리 반경 20px)
 - 흰색 둥근 모서리 박스 + 은은한 그림자
 - 좌측 원형 파스텔 아바타
 - 상단: 모자이크/블러 처리된 회색 닉네임 캡슐 + 작성 시간(예: 2주 전)
 - 중앙: 검은색 굵은 본문 (글자 수에 따라 1~2줄 자동 줄바꿈, 넘치면 말줄임)
 - 하단: 👍 좋아요 수 / 💬 답글 수 (아이콘은 직접 그려 폰트 의존성 제거)
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .fonts import FontInfo, get_font
from .utils import TEMP_DIR

CARD_W = 960
RADIUS = 20
SHADOW = 10          # 그림자 여백(px). PNG 크기 = 카드 + 2*SHADOW
PAD_X = 26
AVATAR = 64
TEXT_X = PAD_X + AVATAR + 22
BODY_SIZE = 33
BODY_LINE = 42
META_SIZE = 23

PASTELS = [(255, 179, 186), (255, 223, 186), (255, 255, 186), (186, 255, 201),
           (186, 225, 255), (218, 192, 255), (255, 200, 230), (190, 240, 235)]
TIMES = ["1일 전", "3일 전", "5일 전", "1주 전", "2주 전", "3주 전", "1개월 전"]


@dataclass
class CardResult:
    path: Path
    width: int    # PNG 전체 크기 (그림자 포함)
    height: int


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int, max_lines: int = 2) -> list[str]:
    """글자 단위 측정 줄바꿈 (한글은 공백이 적어 단어 단위만으로는 부족)."""
    text = " ".join(text.replace("\\N", " ").split())
    lines: list[str] = []
    cur = ""
    words = text.split(" ")
    for wi, word in enumerate(words):
        cand = word if not cur else f"{cur} {word}"
        if draw.textlength(cand, font=font) <= max_w:
            cur = cand
            continue
        if cur:
            lines.append(cur)
            cur = ""
        # 단어 자체가 너무 길면 글자 단위로 자르기
        for ch in word:
            if draw.textlength(cur + ch, font=font) <= max_w:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        last = lines[max_lines - 1]
        while last and draw.textlength(last + "…", font=font) > max_w:
            last = last[:-1]
        lines = lines[: max_lines - 1] + [last.rstrip() + "…"]
    return lines or [""]


def _avatar(size: int, rnd: random.Random) -> Image.Image:
    s = size * 4  # 슈퍼샘플링으로 매끄러운 원
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = rnd.choice(PASTELS)
    d.ellipse([0, 0, s - 1, s - 1], fill=color + (255,))
    # 사람 실루엣 (흰색 반투명)
    w = (255, 255, 255, 210)
    d.ellipse([s * 0.34, s * 0.2, s * 0.66, s * 0.52], fill=w)
    d.ellipse([s * 0.18, s * 0.58, s * 0.82, s * 1.15], fill=w)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
    img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", (s, s), 0), mask))
    return img.resize((size, size), Image.LANCZOS)


def _nickname_capsule(w: int, h: int, rnd: random.Random) -> Image.Image:
    """모자이크 + 블러 느낌의 회색 닉네임 캡슐."""
    cell = 7
    small = Image.new("RGB", (w // cell + 1, h // cell + 1))
    for x in range(small.width):
        for y in range(small.height):
            g = rnd.randint(150, 205)
            small.putpixel((x, y), (g, g, g))
    mosaic = small.resize((small.width * cell, small.height * cell), Image.NEAREST).crop((0, 0, w, h))
    mosaic = mosaic.filter(ImageFilter.GaussianBlur(1.6)).convert("RGBA")
    mask = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=h * 2, fill=255)
    mosaic.putalpha(mask.resize((w, h), Image.LANCZOS))
    return mosaic


def _thumb_icon(d: ImageDraw.ImageDraw, x: int, y: int, s: int, color) -> None:
    """간단한 엄지척 아이콘 (s = 아이콘 크기)."""
    d.rounded_rectangle([x, y + s * 0.42, x + s * 0.22, y + s], radius=2, fill=color)            # 소매
    d.rounded_rectangle([x + s * 0.28, y + s * 0.40, x + s * 0.95, y + s], radius=s * 0.12, fill=color)  # 손바닥
    d.polygon([(x + s * 0.30, y + s * 0.45), (x + s * 0.48, y), (x + s * 0.62, y + s * 0.06),
               (x + s * 0.58, y + s * 0.45)], fill=color)                                        # 엄지


def _bubble_icon(d: ImageDraw.ImageDraw, x: int, y: int, s: int, color) -> None:
    d.rounded_rectangle([x, y + s * 0.05, x + s, y + s * 0.78], radius=s * 0.22, outline=color, width=3)
    d.polygon([(x + s * 0.22, y + s * 0.72), (x + s * 0.22, y + s), (x + s * 0.48, y + s * 0.74)], fill=color)


def create_comment_card(text: str, likes: str, out_path: Path, *, replies: str | None = None,
                        time_ago: str | None = None, seed: int | None = None,
                        font: FontInfo | None = None) -> CardResult:
    font = font or get_font()
    rnd = random.Random(seed if seed is not None else text)
    body_font = font.pil(BODY_SIZE)
    meta_font = font.pil(META_SIZE)

    scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = _wrap(scratch, text, body_font, CARD_W - TEXT_X - PAD_X)

    top = 16
    header_h = 28
    body_top = top + header_h + 8
    footer_top = body_top + BODY_LINE * len(lines) + 6
    card_h = footer_top + 28 + 12

    W, H = CARD_W + SHADOW * 2, card_h + SHADOW * 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # 그림자
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([SHADOW, SHADOW + 4, SHADOW + CARD_W, SHADOW + card_h + 2],
                                         radius=RADIUS, fill=(0, 0, 0, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))

    # 카드 본체 (슈퍼샘플링 둥근 모서리)
    k = 3
    box = Image.new("RGBA", (CARD_W * k, card_h * k), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle([0, 0, CARD_W * k - 1, card_h * k - 1], radius=RADIUS * k,
                                          fill=(255, 255, 255, 255))
    img.alpha_composite(box.resize((CARD_W, card_h), Image.LANCZOS), (SHADOW, SHADOW))

    ox, oy = SHADOW, SHADOW
    d = ImageDraw.Draw(img)

    # 아바타
    img.alpha_composite(_avatar(AVATAR, rnd), (ox + PAD_X, oy + top + 2))

    # 닉네임 캡슐 + 작성 시간
    cap_w = rnd.randint(110, 170)
    img.alpha_composite(_nickname_capsule(cap_w, 24, rnd), (ox + TEXT_X, oy + top + 2))
    d.text((ox + TEXT_X + cap_w + 12, oy + top + 14), time_ago or rnd.choice(TIMES),
           font=meta_font, fill=(130, 130, 130), anchor="lm")

    # 본문
    for i, line in enumerate(lines):
        d.text((ox + TEXT_X, oy + body_top + i * BODY_LINE), line, font=body_font, fill=(15, 15, 15))

    # 좋아요 / 답글
    gray = (96, 96, 96)
    fy = oy + footer_top
    x = ox + TEXT_X
    _thumb_icon(d, x, fy + 2, 22, gray)
    x += 32
    d.text((x, fy + 13), str(likes), font=meta_font, fill=gray, anchor="lm")
    x += int(d.textlength(str(likes), font=meta_font)) + 30
    _bubble_icon(d, x, fy + 3, 22, gray)
    x += 32
    replies = replies if replies is not None else str(rnd.randint(8, 120))
    d.text((x, fy + 13), replies, font=meta_font, fill=gray, anchor="lm")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return CardResult(out_path, W, H)


def generate_comment_cards(comments: list[dict], out_dir: Path = TEMP_DIR) -> list[CardResult]:
    font = get_font()
    results = []
    for i, c in enumerate(comments[:3]):
        results.append(create_comment_card(
            c.get("text", ""), c.get("likes", "0"), out_dir / f"comment_{i + 1}.png",
            replies=c.get("replies"), time_ago=c.get("time_ago"), seed=i * 7919 + len(c.get("text", "")),
            font=font,
        ))
    return results


if __name__ == "__main__":
    demo = [
        {"likes": "1.5천", "text": "자다가도 애기 소리에 바로 반응하는 거 봐... 모성애는 위대하다"},
        {"likes": "794", "text": "떨어질 뻔한 아기 코알라 꼭 안아주는 게 진짜 감동이네 ㅠㅠ"},
        {"likes": "342", "text": "귀여워"},
    ]
    for r in generate_comment_cards(demo):
        print(r)
