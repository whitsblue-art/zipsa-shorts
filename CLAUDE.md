# 집사연구소 쇼츠 — 클로드 유튜브 팀

이 저장소는 반려동물 용품 쇼츠 채널 **집사연구소**를 운영합니다.
대본 하나를 거대한 프롬프트 하나로 만들지 않고, 아래 5개 스킬이 순서대로 일을 넘겨받습니다.

| 순서 | 스킬 | 하는 일 | 산출물 (`content/<slug>/`) |
|---|---|---|---|
| 1 | `/yt-source-finder` | 최근 2주간 조회수가 급등한 영상 조사, 소재 선정 | `01_소재.md` |
| 2 | `/yt-scriptwriter` | 쇼츠 대본 초안 작성 | `02_대본.md` |
| 3 | `/yt-script-review` | 훅·심리·팩트·전환 4개 기준으로 검수 후 대본 확정 | `03_검수.md`, `02_대본.md` 갱신 |
| 4 | `/yt-publisher` | 제목 후보, 썸네일 문구와 레이아웃, 설명란, 태그 | `04_퍼블리시.md` |
| 5 | `/yt-editor` | Remotion 씬 데이터·컴포넌트 작성, TTS 생성, 렌더링 | `scenes.json`, `out/<slug>.mp4` |

전체를 한 번에 돌릴 때는 `/yt-pipeline <주제 또는 상품>`을 씁니다.

## 규칙

- **slug**: `s<두 자리 번호>_<영문-케밥>` (예: `s01_silicone-pet-hair-remover`). 번호는 `content/`에 있는 마지막 번호에 1을 더합니다.
- **상품 번호**: 프로필 링크 `[집사연구소]`에서 찾는 번호. 101부터 시작하며 `content/` 안의 기존 번호와 겹치면 안 됩니다.
- **단계 넘기기**: 각 스킬은 앞 단계 파일을 읽고 자기 파일만 씁니다. 앞 단계 파일이 없으면 멈추고 어떤 스킬을 먼저 돌려야 하는지 알려줍니다.
- **팩트**: 상품 효능, 수치, 리뷰 수, 가격은 출처가 확인된 것만 씁니다. 확인되지 않은 주장은 대본에 넣지 않거나 `[확인 필요]`로 표시합니다. "100% 제거", "완벽하게"처럼 증명할 수 없는 단정 표현은 검수에서 걸러냅니다.
- **광고 고지**: 쿠팡 파트너스 링크로 연결되는 콘텐츠이므로 설명란과 고정 댓글에 아래 문구를 반드시 넣습니다.
  > 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.

## 폴더 구조

```
.claude/skills/        5개 스킬 + yt-pipeline 총괄 스킬
content/<slug>/        영상 한 편의 기획 산출물
remotion/              Remotion 영상 템플릿 (React)
scripts/               보조 스크립트 (트렌드 조사, TTS)
comment_bot/           댓글 키워드 자동 답장
.github/workflows/     GitHub Actions (기존 쇼츠 생성, 댓글 봇, Remotion 렌더링)
auto_shorts.py         기존 쿠팡 API + FFmpeg 쇼츠 파이프라인 (그대로 유지)
```

## 자주 쓰는 명령

```bash
# 트렌드 조사 (YT_API_KEY 필요)
python scripts/find_trending.py --query "고양이 용품" --days 14

# 씬별 TTS 생성 후 scenes.json에 길이 기록
python scripts/tts.py content/<slug>/scenes.json

# 미리보기 / 렌더링
cd remotion && npm install
npx remotion studio
npx remotion render ShortsVideo out/<slug>.mp4 --props=../content/<slug>/scenes.json

# 댓글 봇 시험 실행 (답글을 실제로 달지 않음)
python comment_bot/auto_reply.py --dry-run
```
