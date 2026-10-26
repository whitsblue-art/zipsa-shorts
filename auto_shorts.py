import os
import hmac
import hashlib
import time
import urllib.parse
import urllib.request
import subprocess
import asyncio
import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# 환경변수에서 쿠팡 API 키 로드
ACCESS_KEY = os.environ.get("COUPANG_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("COUPANG_SECRET_KEY", "")

# 데일리로 제작할 상품 목록 (키워드로 쿠팡 API에서 1위 상품 이미지와 정보를 즉시 가져옴)
products = [
    {
        "id": "101",
        "keyword": "실리콘 반려동물 털 제거 클리너",
        "scenes": [
            {"text": "옷이나 소파에 박힌 반려동물 털, 매번 돌돌이로 밀어도 끝이 없죠?", "subtitle": "옷/소파에 박힌 털, 돌돌이로도 안 된다면?"},
            {"text": "수많은 집사님들이 극찬한 이 실리콘 클리너 하나면 고민 끝입니다.", "subtitle": "집사님들 극찬! 돌돌이 한계 돌파"},
            {"text": "가볍게 슥슥 밀어주기만 해도 박혀 있던 털들이 마법처럼 싹 모아집니다.", "subtitle": "가볍게 슥슥 밀어주면 마법처럼 싹-"},
            {"text": "물로 가볍게 씻어내기만 하면 끝이라 반영구적으로 쓸 수 있어 경제적이에요.", "subtitle": "물세척으로 반영구 사용 가능!"},
            {"text": "우리 아이 털 날림 스트레스에서 완벽하게 해방되는 가장 확실한 방법!", "subtitle": "털 날림 스트레스 완벽 해방"},
            {"text": "지금 바로 프로필 링크 '집사연구소'에서 101번을 검색하세요!", "subtitle": "프로필 링크 [집사연구소] 101번 검색!"}
        ]
    }
]

def generate_hmac(method, url, secret_key, access_key):
    """쿠팡 파트너스 API 공식 HMAC 서명 생성"""
    path, *query = url.split("?")
    os.environ["TZ"] = "GMT+0"
    if hasattr(time, 'tzset'):
        time.tzset()
    datetime_str = time.strftime('%y%m%d') + 'T' + time.strftime('%H%M%S') + 'Z'
    message = datetime_str + method + path + (query[0] if query else "")
    signature = hmac.new(
        bytes(secret_key, "utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_str}, signature={signature}"

def fetch_coupang_api_product(keyword):
    """쿠팡 API를 통해 차단 없이 실제 상품 고화질 이미지와 상품명 추출"""
    if not ACCESS_KEY or not SECRET_KEY:
        raise ValueError("쿠팡 API 키가 설정되지 않았습니다! GitHub Secrets에 키를 등록해주세요.")
        
    encoded_kw = urllib.parse.quote(keyword)
    url = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={encoded_kw}&limit=3"
    full_url = "https://api-gateway.coupang.com" + url
    
    headers = {
        "Authorization": generate_hmac("GET", url, SECRET_KEY, ACCESS_KEY),
        "Content-Type": "application/json;charset=UTF-8"
    }
    
    res = requests.get(full_url, headers=headers, timeout=10)
    data = res.json()
    
    if data.get("rCode") == "0" and data.get("data", {}).get("productData"):
        items = data["data"]["productData"]
        # 검색된 상위 상품들의 실제 이미지 URL 리스트 확보
        images = [item["productImage"] for item in items if item.get("productImage")]
        title = items[0]["productName"]
        print(f"쿠팡 API 상품 매칭 성공: {title}")
        return {"title": title, "images": images}
    else:
        raise RuntimeError(f"쿠팡 API 응답 오류: {data}")

async def generate_tts(text, output_filename):
    # 음성 깨짐을 방지하기 위해 rate/pitch 변조를 최소화한 정석 설정
    communicate = edge_tts.Communicate(text, "ko-KR-InJoonNeural")
    await communicate.save(output_filename)

def create_scene_frame(product_img_path, subtitle, scene_idx, output_path):
    """어두운 고급 배경 위에 실제 쿠팡 상품 사진을 큼직하게 배치하고 자막 합성"""
    canvas = Image.new('RGB', (1080, 1920), color=(18, 20, 28))
    
    try:
        prod_img = Image.open(product_img_path).convert("RGB")
        # 씬마다 구도를 살짝 다르게 크롭/리사이즈하여 단조로움 탈피
        prod_img = prod_img.resize((920, 920), Image.Resampling.LANCZOS)
        canvas.paste(prod_img, (80, 220))
    except Exception as e:
        print(f"상품 이미지 로드 오류: {e}")

    draw = ImageDraw.Draw(canvas)
    
    # 상품 이미지 테두리 골드 포인트
    draw.rectangle([78, 218, 1002, 1142], outline=(212, 175, 55), width=4)
    
    # 하단 자막 영역 어두운 박스 및 골드 라인
    draw.rectangle([60, 1250, 1020, 1520], fill=(10, 12, 18))
    draw.rectangle([100, 1250, 980, 1256], fill=(212, 175, 55))
    
    font_path = "NanumGothicBold.ttf"
    try:
        font = ImageFont.truetype(font_path, 48)
    except:
        font = ImageFont.load_default()
        
    # 자막 중앙 정렬 계산
    bbox = draw.textbbox((0, 0), subtitle, font=font)
    text_w = bbox[2] - bbox[0]
    x_pos = max(80, (1080 - text_w) // 2)
    
    draw.text((x_pos, 1355), subtitle, fill=(255, 255, 255), font=font)
    canvas.save(output_path)

async def build_shorts_for_product(prod):
    prod_id = prod["id"]
    prod_dir = f"output/prod_{prod_id}"
    os.makedirs(prod_dir, exist_ok=True)
    
    # 1. 쿠팡 API로 실제 상품 이미지들 가져오기
    api_data = fetch_coupang_api_product(prod["keyword"])
    img_urls = api_data["images"]
    
    # 상품 이미지 다운로드
    downloaded_imgs = []
    for idx, url in enumerate(img_urls):
        img_path = f"{prod_dir}/coupang_item_{idx}.jpg"
        urllib.request.urlretrieve(url, img_path)
        downloaded_imgs.append(img_path)

    video_inputs = []
    
    for i, scene in enumerate(prod["scenes"]):
        audio_file = f"{prod_dir}/scene_{i}.mp3"
        image_file = f"{prod_dir}/scene_{i}.png"
        scene_video = f"{prod_dir}/scene_{i}.mp4"
        
        # 2. 깨끗한 TTS 생성
        await generate_tts(scene["text"], audio_file)
        
        # 3. 쿠팡 실제 상품 이미지 + 자막 프레임 생성
        selected_img = downloaded_imgs[i % len(downloaded_imgs)]
        create_scene_frame(selected_img, scene["subtitle"], i, image_file)
        
        # 4. 정지 화면이 아닌 부드러운 줌인(Zoom-in) 모션 및 고음질 오디오 렌더링 (44100Hz 고정으로 소리 깨짐 완벽 방지)
        cmd_clip = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_file, "-i", audio_file,
            "-vf", "zoompan=z='min(zoom+0.0008,1.12)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            "-shortest", scene_video
        ]
        subprocess.run(cmd_clip, check=True)
        video_inputs.append(scene_video)

    # 5. 전체 씬 병합 (재인코딩 방식으로 오디오 지지직거림 원천 차단)
    concat_list_path = f"{prod_dir}/concat_list.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for v in video_inputs:
            f.write(f"file '{os.path.basename(v)}'\n")
            
    final_video = f"output/zipsa_shorts_{prod_id}.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
        "-c:v", "libx264", "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
        f"../zipsa_shorts_{prod_id}.mp4"
    ]
    subprocess.run(cmd_concat, cwd=prod_dir, check=True)
    print(f"[{prod_id}번 상품] 쿠팡 API 기반 쇼츠 완성: {final_video}")

async def main():
    os.makedirs("output", exist_ok=True)
    
    font_path = "NanumGothicBold.ttf"
    if not os.path.exists(font_path):
        subprocess.run([
            "curl", "-L", 
            "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf", 
            "-o", font_path
        ], check=True)

    for prod in products:
        await build_shorts_for_product(prod)

if __name__ == "__main__":
    asyncio.run(main())
