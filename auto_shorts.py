import os
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# 역사 다큐/쇼츠 스타일의 대본 및 자막 구성
scenes = [
    {
        "text": "옷이나 소파에 박힌 반려동물 털, 매번 돌돌이로 밀어도 끝이 없죠?",
        "subtitle": "옷/소파에 박힌 털, 돌돌이로도 안 된다면?"
    },
    {
        "text": "그럴 때 이 실리콘 털 제거 클리너 하나면 고민 끝입니다.",
        "subtitle": "실리콘 털 제거 클리너 하나로 끝!"
    },
    {
        "text": "가볍게 슥슥 밀어주기만 해도 박혀 있던 털들이 마법처럼 싹 모아집니다.",
        "subtitle": "가볍게 슥슥 밀어주면 마법처럼 싹-"
    },
    {
        "text": "세척도 물로 씻어내기만 하면 끝이라 반영구적으로 쓸 수 있어요.",
        "subtitle": "물로 씻어내기만 하면 반영구 사용!"
    },
    {
        "text": "우리 아이 털 날림 스트레스에서 해방되는 가장 확실한 방법!",
        "subtitle": "털 날림 스트레스 완벽 해방"
    },
    {
        "text": "지금 바로 프로필 링크 '집사연구소'에서 101번을 검색하세요!",
        "subtitle": "프로필 링크 [집사연구소] 101번 검색!"
    }
]

async def generate_tts(text, output_filename):
    # 역사 쇼츠처럼 진중하고 무게감 있는 나레이션 톤 적용 (봉진 목소리, 약간 차분한 속도)
    communicate = edge_tts.Communicate(text, "ko-KR-BongJinNeural", rate="-2%", pitch="-2Hz")
    await communicate.save(output_filename)

def create_scene_image(subtitle, output_path):
    # 9:16 세로형 쇼츠 화면 생성 (1080x1920) - 감성적인 다큐 톤의 어두운 배경
    img = Image.new('RGB', (1080, 1920), color=(18, 22, 32))
    draw = ImageDraw.Draw(img)
    
    # 상단 장식 라인 추가 (역사 쇼츠 느낌의 시각적 디테일)
    draw.rectangle([100, 750, 980, 755], fill=(212, 175, 55)) # 골드 포인트 라인
    
    # 나눔고딕 폰트 적용
    font_path = "NanumGothicBold.ttf"
    try:
        font = ImageFont.truetype(font_path, 55)
    except:
        font = ImageFont.load_default()
        
    # 자막 위치 중앙 배치
    draw.text((100, 900), subtitle, fill=(255, 255, 255), font=font)
    img.save(output_path)

async def main():
    os.makedirs("output", exist_ok=True)
    
    # 한글 폰트 자동 다운로드
    font_path = "NanumGothicBold.ttf"
    if not os.path.exists(font_path):
        print("한글 폰트 다운로드 중...")
        subprocess.run([
            "curl", "-L", 
            "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf", 
            "-o", font_path
        ])

    print("집사연구소 역사 쇼츠 스타일 렌더링 시작...")
    
    video_inputs = []
    
    for i, scene in enumerate(scenes):
        audio_file = f"output/scene_{i}.mp3"
        image_file = f"output/scene_{i}.png"
        scene_video = f"output/scene_{i}.mp4"
        
        # 1. 웅장한 역사 톤 오디오 생성
        await generate_tts(scene["text"], audio_file)
        
        # 2. 다큐 스타일 자막 이미지 생성
        create_scene_image(scene["subtitle"], image_file)
        
        # 3. 이미지 + 오디오 결합 클립 생성
        cmd_clip = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_file, "-i", audio_file,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", scene_video
        ]
        subprocess.run(cmd_clip, check=True)
        video_inputs.append(scene_video)

    # 4. 병합 리스트 작성
    concat_list_path = "output/concat_list.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for v in video_inputs:
            filename = os.path.basename(v)
            f.write(f"file '{filename}'\n")
            
    # 5. 최종 영상 병합
    final_video = "output/zipsa_shorts_101.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
        "-c", "copy", "zipsa_shorts_101.mp4"
    ]
    subprocess.run(cmd_concat, cwd="output", check=True)
    print("역사 쇼츠 스타일 최종 렌더링 완료:", final_video)

if __name__ == "__main__":
    asyncio.run(main())
