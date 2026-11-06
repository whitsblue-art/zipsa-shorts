# CLAUDE.md — zipsa-shorts 작업 규칙과 프로젝트 기억

Claude Code가 세션을 시작할 때마다 자동으로 읽는 파일이다. 새로운 결정이나 버그 수정이 생기면 여기에 한 줄씩 추가한다.

## 사용자
- 한국어로 답한다. 과정 설명은 줄이고 **결과만** 짧게 보고한다(무엇을 했고, 무엇이 확인됐고, 무엇이 안 됐는지).
- 사용자 PC는 **Windows**다. 경로, 인코딩, 셸 차이를 항상 고려한다.

## 프로젝트 지도
- `main.py`: 단일 영상. `--url`, `--script`, 인자 없으면 더미 테스트
- `shorts_factory.py`: 발굴 → 다운로드 → AI → TTS → 렌더 → 업로드 일괄 처리
- `src/utils.py`: 경로 상수, `run_ffmpeg`(항상 cwd=ROOT), `probe`, `filter_path`
- `src/fonts.py`: 굵은 한글 폰트 탐색, 없으면 Pretendard 다운로드. `assets/fonts`에 복사
- `src/background.py`: 우주 배경 루프 생성 (Pillow 프레임 → ffmpeg stdin)
- `src/ai_scripter.py`: Gemini 2.5 Flash 호출. 영상 업로드 → 프레임 → 샘플 순으로 폴백. `normalize_script`로 검증
- `src/subtitle_generator.py`: `.ass` 생성 (타이틀 / 속마음 / 상황설명)
- `src/comment_generator.py`: 댓글 카드 PNG
- `src/video_composer.py`: filter_complex 합성과 오디오 믹싱 (원본, BGM, TTS 덕킹)
- `src/downloader.py`, `src/crawler.py`, `src/tts.py`, `src/uploader.py`: yt-dlp, Reddit/YouTube 발굴과 이력, Edge-TTS, YouTube API
- `auto_shorts.py`, `.github/workflows/daily_shorts.yml`: 별개의 기존 쿠팡 프로젝트. 건드리지 않는다.

## 아키텍처 결정과 이미 고친 버그 (되돌리지 말 것)
1. **libass 폰트 이름**: ASS 스타일에는 OpenType name 테이블의 nameID 1을 쓴다(예: `Pretendard ExtraBold`). Pillow가 돌려주는 `Pretendard`를 쓰면 다른 폰트로 대체된다. 관련 코드는 `fonts._name_table_family`
2. **필터 경로**: ffmpeg를 항상 프로젝트 루트에서 실행하고, `ass` 필터에는 상대경로를 넘긴다. 이렇게 해서 Windows의 `C:`와 `\` 이스케이프 문제를 피한다. 루트 밖 경로만 `filter_path`로 이스케이프한다.
3. **requirements.txt는 ASCII만**: 한글 주석이 있으면 Windows pip(cp949)에서 설치가 실패한다.
4. **다운로드**: 임시 이름(`source_download.*`)으로 받은 뒤 성공했을 때만 `source.mp4`를 교체한다.
5. **배경 생성**: ffmpeg `blend` 표현식은 1분 48초가 걸려 쓰지 않는다. Pillow로 프레임을 그려 파이프로 넘기면 약 5초다.
6. **시간 기준**: script.json의 시간은 원본 기준이다. 렌더러가 `/speed`로 환산한다. AI 프롬프트도 원본 기준으로 쓴다.
7. **폰트 다운로드 URL**: raw.githubusercontent.com을 먼저 시도한다. jsdelivr는 막히는 환경이 있다.
8. 댓글 카드 3장이 1400~1840 영역을 넘으면 카드를 균일하게 축소한다.

## 검증 (변경 후 반드시 실행)
```bash
python main.py                      # 더미 렌더. 1080x1920 출력과 [check] 줄 확인
python shorts_factory.py --test     # 공장 경로 확인
```
- 출력 프레임 3장(3초, 7초, 13초)을 이미지로 뽑아 눈으로 확인한다. 레이아웃과 폰트는 숫자만으로 검증되지 않는다.
- 폰트 대체 여부: `ffmpeg -v verbose ... -vf ass=...` 출력의 `fontselect` 줄을 확인한다.

## 환경 메모
- 클라우드 세션에서는 reddit, youtube, tiktok, Edge-TTS(speech.platform.bing.com) 접속이 차단돼 있다. 실제 다운로드 테스트는 로컬 HTTP 서버로 대신했다.
- 실제 영상 생성은 사용자의 Windows PC 로컬 세션에서 한다.

## 엔지니어링 원칙
- **계획 먼저**: 여러 파일을 바꾸거나 구조를 바꿀 때는 영향 범위, 엣지 케이스, 기술 부채를 먼저 짧게 정리한다. 한두 줄 수정은 바로 한다.
- **DRY**: 새 기능은 `src/` 모듈을 재사용한다. 다운로드, 렌더 같은 로직을 엔트리포인트에 복제하지 않는다.
- **간결하게, 단 가독성 우선**: 함수는 한 가지 일만 한다. 줄 수를 줄이려고 의미를 압축하거나 에러 처리를 빼지 않는다.
- **실패에 강하게**: 외부 의존(Gemini, TTS, 다운로드, 폰트)이 실패해도 폴백으로 영상은 나와야 한다. 실패는 로그로 알린다.
- **검증 없이 완료라고 하지 않는다**: 실행 결과(출력, 프레임)로 확인한 것만 완료로 보고한다. 확인 못 한 것은 그렇다고 쓴다.

## 하지 않는 것
- 워터마크 제거나 감지 회피를 강화하는 기능은 만들지 않는다. 기존 배속, eq, flip 옵션은 요청에 따라 넣었지만 효과를 보장하지 않는다.
- 업로드 기본값은 `private`이고, 자동 공개로 바꾸지 않는다. `data/`(OAuth 토큰, client_secret, 이력)는 커밋하지 않는다.
