import os
import subprocess
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont

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
    img = Image.new('RGB', (1080, 1920), color=(15, 15, 25))
    draw = ImageDraw.Draw(img)
    
    # 우분투 환경에서도 기본 지원되는 폰트 또는 기본 폰트 대체 적용
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 55)
    except:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 55)
        except:
            font = ImageFont.load_default()
        
    # 텍스트 줄바꿈 및 중앙 배치 시뮬레이션
    draw.text((80, 900), subtitle, fill=(255, 255, 255), font=font)
    img.save(output_path)

async def main():
    os.makedirs("output", exist_ok=True)
    print("집사연구소 101번 상품 쇼츠 안정적 렌더링 시작...")
    
    video_inputs = []
    
    for i, scene in enumerate(scenes):
        audio_file = f"output/scene_{i}.mp3"
        image_file = f"output/scene_{i}.png"
        scene_video = f"output/scene_{i}.mp4"
        
        # 1. 오디오 생성
        await generate_tts(scene["text"], audio_file)
        
        # 2. 이미지 생성
        create_scene_image(scene["subtitle"], image_file)
        
        # 3. 이미지와 오디오 결합 클립 생성 (오디오 길이에 맞춤)
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
            # 절대 경로 또는 파일명 기재
            filename = os.path.basename(v)
            f.write(f"file '{filename}'\n")
            
    # 5. 최종 쇼츠 영상 병합 (output 폴더 안에서 실행)
    final_video = "output/zipsa_shorts_101.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
        "-c", "copy", "zipsa_shorts_101.mp4"
    ]
    subprocess.run(cmd_concat, cwd="output", check=True)
    print("최종 쇼츠 영상 렌더링 및 아티팩트 준비 완료:", final_video)

if __name__ == "__main__":
    asyncio.run(main())
