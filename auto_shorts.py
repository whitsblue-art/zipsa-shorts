import os
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# 1. 101번 반려동물 꿀템(실리콘 털 제거 클리너) 6개 장면 구성
scenes = [
    {
        "text": "옷이나 소파에 박힌 반려동물 털, 매번 돌돌이로 밀어도 끝이 없죠?",
        "visual": "Pet hair stubbornly stuck on a fabric sofa, close up view"
    },
    {
        "text": "그럴 때 이 실리콘 털 제거 클리너 하나면 고민 끝입니다.",
        "visual": "A practical silicone pet hair remover tool, clean minimalist product shot"
    },
    {
        "text": "가볍게 슥슥 밀어주기만 해도 박혀 있던 털들이 마법처럼 싹 모아집니다.",
        "visual": "Silicone pet hair remover tool easily scraping pet hair off a sofa, satisfying motion"
    },
    {
        "text": "세척도 물로 씻어내기만 하면 끝이라 반영구적으로 쓸 수 있어요.",
        "visual": "Rinsing the silicone pet hair remover tool clean under running water"
    },
    {
        "text": "우리 아이 털 날림 스트레스에서 해방되는 가장 확실한 방법!",
        "visual": "A cute cat and dog resting happily in a clean, hair-free living room"
    },
    {
        "text": "지금 바로 프로필 링크 '집사연구소'에서 101번을 검색하세요!",
        "visual": "Text overlay and visual prompt directing to profile link 101"
    }
]

async def generate_tts(text, output_filename):
    communicate = edge_tts.Communicate(text, "ko-KR-InJoonNeural", rate="+22%", pitch="-8Hz", volume="+15%")
    await communicate.save(output_filename)

# 오디오 무음 제거 및 중저음 보강 후처리 함수
def process_audio(input_path, output_path):
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-50dB:detection=peak,bass=g=5:f=110:w=0.6",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("집사연구소 쇼핑 쇼츠 파이프라인 세팅 완료!")
