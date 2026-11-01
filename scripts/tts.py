"""scenes.json의 씬마다 edge-tts 음성을 만들고 durationInFrames를 음성 길이에 맞춘다 (/yt-editor 용).

사용법:
    pip install edge-tts mutagen
    python scripts/tts.py content/<slug>/scenes.json

결과:
    remotion/public/<slug>/scene_<n>.mp3 생성
    scenes.json의 각 씬에 audio, durationInFrames 기록
"""
import asyncio
import json
import math
import os
import sys

import edge_tts
from mutagen.mp3 import MP3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "remotion", "public")
PADDING_FRAMES = 12  # 문장 사이 숨 고르기


async def main(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    slug = data["slug"]
    fps = data.get("fps", 30)
    voice = data.get("voice", "ko-KR-InJoonNeural")
    out_dir = os.path.join(PUBLIC, slug)
    os.makedirs(out_dir, exist_ok=True)

    for i, scene in enumerate(data["scenes"]):
        text = scene.get("narration", "").strip()
        if not text:
            continue
        rel = f"{slug}/scene_{i}.mp3"
        dest = os.path.join(PUBLIC, rel)
        await edge_tts.Communicate(
            text, voice, rate=data.get("rate", "+5%"), proxy=os.environ.get("TTS_PROXY")
        ).save(dest)
        seconds = MP3(dest).info.length
        scene["audio"] = rel
        scene["durationInFrames"] = math.ceil(seconds * fps) + PADDING_FRAMES
        print(f"씬 {i}: {seconds:.2f}초 → {scene['durationInFrames']}프레임")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    total = sum(s["durationInFrames"] for s in data["scenes"]) / fps
    print(f"총 길이: {total:.1f}초")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: python scripts/tts.py content/<slug>/scenes.json")
    asyncio.run(main(sys.argv[1]))
