# zipsa-shorts

반려동물 용품 쇼츠 채널 **집사연구소** 자동 운영 저장소.

## 구성

| 구성 요소 | 위치 | 실행 |
|---|---|---|
| 클로드 유튜브 팀 (5개 스킬 + 총괄) | `.claude/skills/` | Claude Code에서 `/yt-pipeline <주제>` 또는 단계별 `/yt-source-finder` … `/yt-editor` |
| Remotion 영상 템플릿 | `remotion/` | `npx remotion studio` / Actions `Render Remotion Short` |
| 댓글 키워드 자동 답장 | `comment_bot/` | Actions `Comment Auto Reply` (매시 20분) |
| 기존 쿠팡 + FFmpeg 쇼츠 | `auto_shorts.py` | Actions `Zipsa Shorts Auto Pipeline` (월·수·금) |

스킬 사이의 규칙과 폴더 구조는 [`CLAUDE.md`](CLAUDE.md)에 있습니다.

## 처음 설정

### GitHub Secrets
| 이름 | 용도 | 발급 |
|---|---|---|
| `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY` | 상품 이미지 (기존) | 쿠팡 파트너스 |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | 댓글 봇 | `python comment_bot/get_refresh_token.py client_secret.json` (파일 상단 안내 참고) |
| `YT_API_KEY` (선택, 로컬 환경변수) | 트렌드 조사 `scripts/find_trending.py` | Google Cloud Console → YouTube Data API v3 → API 키 |

### 댓글 봇
1. `comment_bot/config.json`의 `link`에 안내 링크를 넣는다. **비어 있으면 봇은 답글을 달지 않고 실패로 끝난다.**
2. Actions → `Comment Auto Reply` → Run workflow (dry_run 체크) 로 대상 댓글을 먼저 확인한다.
3. 이후에는 매시 20분에 자동 실행된다. 채널이 이미 답글을 단 댓글은 건너뛰므로 중복 답글이 생기지 않는다.

### 영상 렌더링
```bash
python scripts/tts.py content/<slug>/scenes.json     # 씬별 음성 + 길이
cd remotion && npm install
npx remotion studio                                   # 미리보기
npx remotion render ShortsVideo out/<slug>.mp4 --props=../content/<slug>/scenes.json
```
또는 Actions → `Render Remotion Short` 에 slug를 넣어 실행하면 mp4가 아티팩트로 올라온다.
