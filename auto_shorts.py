import os
import subprocess
import asyncio
import urllib.request
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# 각 씬별 대본, 자막, 그리고 각 장면에 어울리는 고화질 배경 이미지 (Unsplash 무료 소스 활용)
scenes = [
    {
        "text": "옷이나 소파에 박힌 반려동물 털, 매번 돌돌이로 밀어도 끝이 없죠?",
        "subtitle": "옷/소파에 박힌 털, 돌돌이로도 안 된다면?",
        "bg_url": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?q=80&w=1080&h=1920&fit=crop" # 강아지/털 관련 감성 컷
    },
    {
        "text": "그럴 때 이 실리콘 털 제거 클리너 하나면 고민 끝입니다.",
        "subtitle": "실리콘 털 제거 클리너 하나로 끝!",
        "bg_url": "https://images.unsplash.com/photo-1548767797-d8c844163c4c?q=80&w=1080&h=1920&fit=crop" # 반려동물 관련 컷
    },
    {
        "text": "가볍게 슥슥 밀어주기만 해도 박혀 있던 털들이 마법처럼 싹 모아집니다.",
        "subtitle": "가볍게 슥슥 밀어주면 마법처럼 싹-",
        "bg_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?q=80&w=1080&h=1920&fit=crop" # 고양이 컷
    },
    {
        "text": "세척도 물로 씻어내기만 하면 끝이라 반영구적으로 쓸 수 있어요.",
        "subtitle": "물로 씻어내기만 하면 반영구 사용!",
        "bg_url": "https://images.unsplash.com/photo-1537151608828-ea2b11777ee8?q=80&w=1080&h=1920&fit=crop" # 깔끔한 펫 이미지
    },
    {
        "text": "우리 아이 털 날림 스트레스에서 해방되는 가장 확실한 방법!",
        "subtitle": "털 날림 스트레스 완벽 해방",
        "bg_url": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?q=80&w=1080&h=1920&fit=crop" # 해맑은 강아지 컷
    },
    {
        "text": "지금 바로 프로필 링크 '집사연구소'에서 101번을 검색하세요!",
        "subtitle": "프로필 링크 [집사연구소] 101번 검색!",
        "bg_url": "https://images.unsplash.com/photo-1541599540903-216a46ca1dc0?q=80&w=1080&h=1920&fit=crop" # 쇼핑/추천 컷
    }
]

async def generate_tts(text, output_filename):
    # 진중하고 몰입감 있는 역사 쇼츠 스타일 나레이션 톤
    communicate = edge_tts.Communicate(text, "ko-KR-InJoonNeural", rate="-2%")
    await communicate.save(output_filename)

def create_scene_image(bg_image_path, subtitle, output_path):
    # 9:16 세로형 쇼츠 화면 로드 (1080x1920)
    try:
        img = Image.open(bg_image_path).convert("RGB")
        img = img.resize((1080, 1920))
    except:
        img = Image.new('RGB', (1080, 1920), color=(20, 20, 30))
        
    # 자막 가독성을 높이기 위해 배경 위에 어두운 반투명 레이어 덧씌우기
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 140))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    
    draw = ImageDraw.Draw(img)
    
    # 상단 골드 포인트 라인 (다큐 쇼츠 감성)
    draw.rectangle([100, 700, 980, 705], fill=(212, 175, 55))
    
    # 나눔고딕 폰트 적용
    font_path = "NanumGothicBold.ttf"
    try:
        font = ImageFont.truetype(font_path, 50)
    except:
        font = ImageFont.load_default()
        
    # 자막 배치
    draw.text((100, 850), subtitle, fill=(255, 255, 255), font=font)
    img.save(output_path)

async def main():
    os.makedirs("output", exist_ok=True)
    
    # 1. 한글 폰트 다운로드
    font_path = "NanumGothicBold.ttf"
    if not os.path.exists(font_path):
        print("한글 폰트 다운로드 중...")
        subprocess.run([
            "curl", "-L", 
            "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf", 
            "-o", font_path
        ])

    print("집사연구소 비주얼 쇼츠 렌더링 시작...")
    
    video_inputs = []
    
    for i, scene in enumerate(scenes):
        audio_file = f"output/scene_{i}.mp3"
        raw_bg_file = f"output/bg_{i}.jpg"
        image_file = f"output/scene_{i}.png"
        scene_video = f"output/scene_{i}.mp4"
        
        # 2. 각 씬별 배경 이미지 다운로드
        try:
            urllib.request.urlretrieve(scene["bg_url"], raw_bg_file)
        except:
            # 다운로드 실패 시 단색 이미지로 대체
            fallback = Image.new('RGB', (1080, 1920), color=(20, 20, 30))
            fallback.save(raw_bg_file)
            
        # 3. 오디오 생성
        await generate_tts(scene["text"], audio_file)
        
        # 4. 이미지 배경 + 자막 합성
        create_scene_image(raw_bg_file, scene["subtitle"], image_file)
        
        # 5. 영상 클립 생성
        cmd_clip = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_file, "-i", audio_file,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", scene_video
        ]
        subprocess.run(cmd_clip, check=True)
        video_inputs.append(scene_video)

    # 6. 병합 리스트 작성
    concat_list_path = "output/concat_list.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for v in video_inputs:
            filename = os.path.basename(v)
            f.write(f"file '{filename}'\n")
            
    # 7. 최종 영상 병합
    final_video = "output/zipsa_shorts_101.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
        "-c", "copy", "zipsa_shorts_101.mp4"
    ]
    subprocess.run(cmd_concat, cwd="output", check=True)
    print("비주얼 쇼츠 최종 렌더링 완료:", final_video)

if __name__ == "__main__":
    asyncio.run(main())
