---
name: yt-pipeline
description: 집사연구소 쇼츠 한 편을 소재 찾기부터 렌더링까지 5개 스킬(yt-source-finder → yt-scriptwriter → yt-script-review → yt-publisher → yt-editor) 순서로 처음부터 끝까지 돌린다. "쇼츠 하나 만들어줘", "파이프라인 돌려줘" 요청 시 사용.
argument-hint: "[주제 또는 상품 키워드]"
---

# /yt-pipeline — 총괄

입력: `$ARGUMENTS` (주제 또는 상품). 비어 있으면 "반려동물 용품".

아래 스킬을 **순서대로** 실행한다. 각 스킬의 SKILL.md 지시를 그대로 따르고, 단계마다 산출물 파일이 생겼는지 확인한 뒤 다음으로 넘어간다.

1. `/yt-source-finder $ARGUMENTS` → `content/<slug>/01_소재.md` (여기서 slug가 정해진다)
2. `/yt-scriptwriter <slug>` → `02_대본.md`
3. `/yt-script-review <slug>` → `03_검수.md`, 확정본 `02_대본.md` — **통과하지 못하면 4단계로 넘어가지 않는다**
4. `/yt-publisher <slug>` → `04_퍼블리시.md`
5. `/yt-editor <slug>` → `scenes.json`, TTS, 렌더링

## 단계 사이 보고

단계마다 한두 줄로 보고한다: 무엇을 만들었고, 다음 단계에 넘기는 핵심이 무엇인지.
사람이 판단해야 하는 지점에서는 멈추고 묻는다:
- 1단계 후: 선정 소재가 마음에 드는지 (후보 3개 제시)
- 4단계 후: 제목 1순위 확정

## 끝나면

- 만든 파일 목록
- 업로드 체크리스트 (제목, 설명란과 광고 고지, 해시태그, 고정 댓글)
- `auto_shorts.py`의 `products`에 넣을 항목 (FFmpeg 파이프라인도 같이 쓰는 경우)
