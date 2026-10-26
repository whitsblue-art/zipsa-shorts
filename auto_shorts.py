import os
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# 각 씬별 대본, 자막, 그리고 어울리는 배경 분위기 설정
scenes = [
    {
        "text": "옷이나 소파에 박힌 반려동물 털, 매번 돌돌이로 밀어도 끝이 없죠?",
        "subtitle": "옷/소파에 박힌 털, 돌돌이로도 안 된다면?",
        "bg_color": (30, 35, 45)
    },
    {
        "text": "그럴 때 이 실리콘 털 제거 클리너 하나면 고민 끝입니다.",
        "subtitle": "실리콘 털 제거 클리너 하나로 끝!",
        "bg_color": (40, 30, 50)
    },
    {
        "text": "가볍게 슥슥 밀어주기만 해도 박혀 있던 털들이 마법처럼 싹 모아집니다.",
        "subtitle": "가볍게 슥슥 밀어주면 마법처럼 싹-",
        "bg_color": (25, 45, 40)
    },
    {
        "text": "세척도 물로 씻어내기만 하면 끝이라 반영구적으로 쓸 수 있어요.",
        "subtitle": "물로 씻어내기만 하면 반영구 사용!",
        "bg_color": (20, 40, 55)
    },
    {
        "text": "우리 아이 털 날림 스트레스에서 해방되는 가장 확실한 방법!",
        "subtitle": "털 날림 스트레스 완벽 해방",
        "bg_color": (50, 35, 30)
    },
    {
        "text": "지금 바로 프로필 링크 '집사연구소'에서 101번을 검색하세요!",
        "subtitle": "프로필 링크 [집사연구소] 101번 검색!",
        "bg_color": (55, 25, 35)
    }
]

async def generate_tts(text, output_filename):
    communicate = edge_tts.Communicate(text, "ko-KR-InJoonNeural", rate="-2%")
    await communicate.save(output_filename)

def create_scene_image(subtitle, bg_color, output_path):
    # 9:16 세로형 쇼츠 화면 생성 (1080x1920)
    img = Image.new('RGB', (1080, 1920), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # 시각적 포인트를 주는 다큐/쇼츠 스타일의 상단 라인
    draw.rectangle([100, 700, 980, 705], fill=(212, 175, 55))
    
    # 나눔고딕 폰트 적용
    font_path = "NanumGothicBold.ttf"
    try:
        font = ImageFont.truetype(font_path, 55)
    except:
        font = ImageFont.load_default()
        
    draw.text((100, 850), subtitle, fill=(255, 255, 255), font=font)
    img.save(output_path)

async def main():
    os.makedirs("output", exist_ok=True)
    
    font_path = "NanumGothicBold.ttf"
    if not os.path.exists(font_path):
        print("한글 폰트 다운로드 중...")
        subprocess.run([
            "curl", "-L", 
            "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf", 
            "-o", font_path
        ])

    print("집사연구소 고품질 쇼츠 렌더링 시작...")
    
    video_inputs = []
    
    for i, scene in enumerate(scenes):
        audio_file = f"output/scene_{i}.mp3"
        image_file = f"output/scene_{i}.png"
        scene_video = f"output/scene_{i}.mp4"
        
        await generate_tts(scene["text"], audio_file)
        create_scene_image(scene["subtitle"], scene["bg_color"], image_file)
        
        cmd_clip = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_file, "-i", audio_file,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", scene_video
        ]
        subprocess.run(cmd_clip, check=True)
        video_inputs.append(scene_video)

    concat_list_path = "output/concat_list.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for v in video_inputs:
            filename = os.path.basename(v)
            f.write(f"file '{filename}'\n")
            
    final_video = "output/zipsa_shorts_101.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
        "-c", "copy", "zipsa_shorts_101.mp4"
    ]
    subprocess.run(cmd_concat, cwd="output", check=True)
    print("최종 렌더링 완료:", final_video)

if __name__ == "__main__":
    asyncio.run(main())
