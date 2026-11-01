---
name: yt-editor
description: 확정 대본과 퍼블리시 패키지로 Remotion(React) 씬 데이터 content/<slug>/scenes.json을 만들고, 필요하면 새 씬 컴포넌트를 remotion/src/scenes/에 추가한 뒤 TTS 생성과 렌더링까지 한다. "편집해줘", "영상 만들어줘", "렌더링" 요청 시 사용.
argument-hint: "<slug>"
---

# /yt-editor — 화면·편집 (Remotion)

입력: `$ARGUMENTS` = slug. `02_대본.md`(확정본)와 `04_퍼블리시.md`가 모두 있어야 한다. 없으면 어떤 스킬을 먼저 돌려야 하는지 안내하고 멈춘다.

## 템플릿 구조 (`remotion/`)

```
src/index.ts                 registerRoot
src/Root.tsx                 <Composition id="ShortsVideo"> — props로 scenes.json을 받는다
src/ShortsVideo.tsx          씬 목록을 <Series>로 이어 붙이고, 씬마다 <Audio>를 붙인다
src/types.ts                 scenes.json의 타입 (Zod 스키마)
src/components/Stage.tsx     1080×1920 배경, 안전 영역, 진행 바
src/components/Subtitle.tsx  하단 자막 (**굵게** 부분은 골드)
src/scenes/*.tsx             씬 종류별 컴포넌트 (아래 표)
```

| `type` | 컴포넌트 | 쓰는 곳 |
|---|---|---|
| `cover` | `CoverScene` | 첫 씬(훅). 04_퍼블리시.md의 headline/subline/highlight |
| `problem` | `ProblemScene` | 문제 상황. 큰 이모지/아이콘 + 흔들림 + 빨간 X |
| `product` | `ProductScene` | 상품 이미지가 `spring({ frame })`으로 튀어나오며 등장 |
| `point` | `PointScene` | 이점 하나를 큰 글자 + 체크 아이콘으로 |
| `cta` | `CtaScene` | 상품 번호 배지, "프로필 링크 [집사연구소]" |

## 작업 순서

1. 대본의 씬마다 위 `type` 중 하나를 고른다. 맞는 게 없으면 `remotion/src/scenes/`에 새 컴포넌트를 만들고 `ShortsVideo.tsx`의 `SCENES` 맵과 `types.ts` 스키마에 추가한다.
   - 애니메이션은 `useCurrentFrame()` + `spring({ frame, fps, config: { damping: 200 } })` / `interpolate()`만 쓴다. CSS transition·`setTimeout`은 렌더링에서 안 먹으므로 쓰지 않는다.
   - 텍스트·핵심 요소는 위아래 250px 안전 영역 밖에 두지 않는다 (`Stage`가 안전 영역을 잡아준다).
2. `content/<slug>/scenes.json`을 쓴다. 형식은 `content/s01_*/scenes.json` 예시와 `remotion/src/types.ts`를 따른다.
   - `image`는 `remotion/public/` 기준 경로. 상품 이미지는 `auto_shorts.py`의 쿠팡 API로 받아 `remotion/public/<slug>/`에 둔다. 아직 없으면 비워 두면 상품 대신 자리표시 카드가 나온다.
3. TTS를 만들고 씬 길이를 채운다.
   ```bash
   pip install edge-tts mutagen
   python scripts/tts.py content/<slug>/scenes.json
   ```
   씬마다 `remotion/public/<slug>/scene_<n>.mp3`가 생기고 `durationInFrames`가 음성 길이 + 여유 12프레임으로 기록된다.
4. 미리보기 후 렌더링.
   ```bash
   cd remotion && npm install
   npx remotion studio          # 브라우저에서 확인
   npx remotion render ShortsVideo out/<slug>.mp4 --props=../content/<slug>/scenes.json
   ```
   클라우드·CI에서는 GitHub Actions `Render Remotion Short` 워크플로를 slug 입력으로 실행하면 mp4가 아티팩트로 올라온다.
5. 확인할 것: 첫 프레임이 썸네일 역할을 하는지, 자막이 화면 밖으로 넘치지 않는지, 음성과 씬 전환이 맞는지. 문제가 있으면 `npx remotion still ShortsVideo out/check.png --frame=<n> --props=...`로 특정 프레임을 뽑아 본다.

## 출력

- `content/<slug>/scenes.json`
- (필요 시) 새 씬 컴포넌트
- `remotion/out/<slug>.mp4` — 렌더링한 영상 (저장소에는 커밋하지 않는다)
- 마지막에 업로드 체크리스트: 04_퍼블리시.md의 1순위 제목, 설명란(광고 고지 포함), 고정 댓글.
