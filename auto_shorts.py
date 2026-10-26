import os
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# 1. 101번 반려동물 꿀템(실리콘 털 제거 클리너) 6개 장면 대본 및 비주얼 구성
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
    communicate = edge_tts.Communicate(text, "ko-KR-InJoonNeural", rate="+15%", pitch="-5Hz")
    await communicate.save(output_filename)

def create_scene_image(subtitle, output_path):
    # 9:16 세로형 쇼츠 화면 생성 (1080x1920)
    img = Image.new('RGB', (1080, 1920), color=(20, 20, 30))
    draw = ImageDraw.Draw(img)
    
    # 텍스트 랜더링 설정 (기본 폰트 활용)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 60)
    except:
        font = ImageFont.load_default()
        
    # 화면 중앙에 자막 배치
    draw.text((100, 900), subtitle, fill=(255, 255, 255), font=font)
    img.save(output_path)

async def main():
    os.makedirs("output", exist_ok=True)
    print("집사연구소 101번 상품 진짜 쇼츠 영상 렌더링 시작...")
    
    video_inputs = []
    
    for i, scene in enumerate(scenes):
        audio_file = f"output/scene_{i}.mp3"
        image_file = f"output/scene_{i}.png"
        scene_video = f"output/scene_{i}.mp4"
        
        # 1. 오디오 생성
        await generate_tts(scene["text"], audio_file)
        
        # 2. 자막 이미지 생성
        create_scene_image(scene["subtitle"], image_file)
        
        # 3. 이미지와 오디오를 합쳐서 각 장면별 영상 클립 생성
        cmd_clip = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_file, "-i", audio_file,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-shortest", scene_video
        ]
        subprocess.run(cmd_clip, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        video_inputs.append(scene_video)

    # 4. 모든 장면 클립을 하나로 병합하는 텍스트 파일 생성
    concat_list_path = "output/concat_list.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for v in video_inputs:
            f.write(f"file '{v}'\n")
            
    # 5. 최종 완성 쇼츠 영상 병합
    final_video = "output/zipsa_shorts_101.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-c", "copy", final_video
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("진짜 쇼츠 영상 렌더링 완료:", final_video)

if __name__ == "__main__":
    asyncio.run(main())
