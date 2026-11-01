# zipsa-shorts

## 해외 바이럴 동물/밈 큐레이션 쇼츠 자동 생성기

원본 영상 URL 하나로 **다운로드 → AI 기획안(자막/속마음/베스트댓글) → 댓글 카드 렌더링 → 1080x1920 3단 레이아웃 합성**까지 원클릭으로 처리합니다.

```
┌──────────────────────┐  Y 160~340  상단 고정 훅 타이틀 (노란 키워드 하이라이트)
│  자는 줄 알았는데?    │
│   역시 엄마다...      │
├──────────────────────┤  Y 380~1350 원본 영상 (가로 1080 맞춤, 세로 크롭)
│   * 엄마는 자고 *     │  ← 속마음 (Y≈480, 기울임, 초록/분홍)
│      [ 원본 영상 ]    │
│  유칼립투스 나무 위    │  ← 상황 설명 (Y≈1220)
├──────────────────────┤  Y 1400~1840 베스트 댓글 카드 (시간차 등장)
│ (●) ▒▒▒ 2주 전        │
│     댓글 본문...      │
│     👍 1.5천  💬 42   │
└──────────────────────┘  배경: 어두운 우주/별빛 루프 영상
```

### 설치

```bash
pip install -r requirements.txt
cp .env.example .env        # GEMINI_API_KEY 입력 (없으면 샘플 기획안으로 동작)
```

FFmpeg(libass 포함 빌드)가 PATH에 있어야 합니다.
- Windows: `winget install Gyan.FFmpeg` · macOS: `brew install ffmpeg` · Linux: `sudo apt install ffmpeg`

### 사용법

```bash
python main.py --url "https://www.youtube.com/shorts/xxxx"   # 전체 자동 실행
python main.py --script input/script.json                    # 기존 기획안으로 렌더링만
python main.py                                               # 더미 테스트 모드
```

| 옵션 | 설명 |
|---|---|
| `--flip` | 좌우 반전 (재사용 콘텐츠 감지 회피) |
| `--speed 1.02` | 미세 배속 (기본 1.02x, 오디오는 atempo로 피치 유지) |
| `--bgm PATH` | 배경음악 (기본 `input/bgm.mp3`, 없으면 원본 오디오만) |
| `--output PATH` | 결과 경로 (기본 `output/final_shorts.mp4`) |
| `--max-duration SEC` | 최대 길이 제한 |
| `--offline` | Gemini 호출 없이 샘플 기획안 사용 |
| `--force-dummy` | 테스트 모드에서 더미 에셋 재생성 |

`--url` 모드에서 BGM을 쓰려면 `input/bgm.mp3`를 미리 넣어두거나 `--bgm`으로 지정하세요.

### 올인원 공장 모드 (`shorts_factory.py`)

발굴 → 다운로드 → AI 기획 → (TTS) → 렌더링 → (업로드)를 한 번에 처리하고, 처리 이력을 남겨 같은 영상을 두 번 만들지 않습니다.

```bash
python shorts_factory.py                         # Reddit 동물 서브레딧 → (실패 시) YouTube 검색으로 1개 자동 발굴
python shorts_factory.py --count 3               # 3개 연속
python shorts_factory.py --url "https://www.tiktok.com/@user/video/123"   # 틱톡/유튜브/레딧 URL 지정
python shorts_factory.py --urls urls.txt         # 한 줄에 URL 하나 (#은 주석)
python shorts_factory.py --test                  # 네트워크 없이 더미로 동작 확인
python shorts_factory.py --url URL --tts         # 상황 설명 자막을 Edge-TTS 나레이션으로
python shorts_factory.py --url URL --upload      # 생성 후 YouTube에 비공개(private) 업로드
```

- 결과: `output/<날짜_시간>_<영상ID>.mp4`와 같은 이름의 `.json`(업로드 제목·설명·태그·원본 출처). 최신 결과는 `output/final_shorts.mp4`에도 복사됩니다.
- 원본이 `--max-sec`(기본 30초)보다 길면 앞부분만 사용합니다.
- BGM: `--bgm` → `assets/bgm/` 폴더의 곡 중 랜덤 → `input/bgm.mp3` 순서로 고릅니다.
- 이력: `data/history.json`. 이미 처리한 URL은 건너뜁니다(`--force`로 무시).
- 업로드 준비: Google Cloud에서 YouTube Data API v3를 켜고 OAuth 클라이언트(데스크톱 앱) JSON을
  `data/client_secret.json`으로 저장합니다. 첫 업로드 때 브라우저에서 한 번 로그인하면 됩니다.
  기본 공개 범위는 `private`이며 `--privacy unlisted|public`으로 바꿀 수 있습니다.
- 업로드 설명란에는 원본 출처(업로더·URL)가 자동으로 들어갑니다.

### 구조

```
main.py                    CLI 엔트리포인트
src/downloader.py          yt-dlp → input/source.mp4 (실패 시 기존 파일 보존)
src/ai_scripter.py         Gemini 2.5 Flash 기획안 생성 (영상 업로드 → 프레임 → 샘플 폴백)
src/comment_generator.py   Pillow 유튜브 댓글 카드 PNG
src/subtitle_generator.py  타이틀/속마음/상황설명 → 단일 .ass
src/video_composer.py      FFmpeg filter_complex 합성
src/fonts.py               굵은 한글 폰트 탐색 → assets/fonts 연결 (없으면 Pretendard 자동 다운로드)
src/background.py          assets/bg/bg_loop.mp4 자동 생성 (우주 그라데이션 + 반짝이는 별 + 노이즈)
src/utils.py               경로/FFmpeg/ffprobe/필터 경로 이스케이프
src/crawler.py             Reddit/YouTube 바이럴 영상 발굴 + data/history.json
src/tts.py                 Edge-TTS 나레이션 (선택)
src/uploader.py            YouTube Data API 업로드 (선택)
shorts_factory.py          올인원 공장 엔트리포인트
```

### 크로스 플랫폼 경로 처리

FFmpeg는 항상 프로젝트 루트를 작업 디렉터리로 실행하고, `ass` 필터의 `filename`/`fontsdir`에는
`temp/subtitles.ass`, `assets/fonts` 같은 **상대경로**를 넘깁니다. 그래서 Windows의 `C:`나 `\` 이스케이프
문제가 생기지 않습니다. 루트 밖 경로라면 `/`로 통일하고 `:`·`\`를 이스케이프한 뒤 작은따옴표로 감쌉니다.

### script.json 스키마

```json
{
  "video_file": "input/source.mp4",
  "bgm_file": "input/bgm.mp3",
  "bgm_volume": 0.25,
  "source_volume": 1.0,
  "top_title": {"line1": "{\\c&H00D7FF&}자는 줄{\\c&HFFFFFF&} 알았는데?", "line2": "역시 {\\c&H00D7FF&}엄마다..."},
  "subtitles": [
    {"start": 0.0, "end": 3.5, "type": "narration", "text": "유칼립투스 나무 위\\N코알라 가족"},
    {"start": 2.0, "end": 4.5, "type": "thought", "color": "green", "text": "* 엄마는 자고 *"}
  ],
  "comments": [{"appear_at": 4.0, "likes": "1.5천", "text": "자다가도 애기 소리에 바로 반응하는 거 봐..."}]
}
```

- 시간은 **원본 영상 기준**입니다. 배속을 적용하면 렌더러가 자동으로 출력 타임라인에 맞춰 환산합니다.
- `color`: `green`, `pink`, `yellow`, `white`, `skyblue` 또는 ASS 색상 코드(`&HBBGGRR&`)
- 선택 필드: 댓글별 `replies`(답글 수), `time_ago`(예: `"2주 전"`)

---
기존 쿠팡 상품 쇼츠 스크립트(`auto_shorts.py`)와 워크플로는 그대로 유지됩니다.
