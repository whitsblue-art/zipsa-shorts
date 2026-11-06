# CLAUDE.md — zipsa-shorts

Loaded automatically at the start of every Claude Code session. This file **is** the project's
persistent memory: when a bug is fixed, a rule is agreed, or an architectural decision is made,
record it in the relevant section below in the same commit.

## 1. Project map

| Path | Role |
|---|---|
| `auto_shorts.py` | Whole pipeline: Coupang Partners API → product images → edge-tts voice → PIL frames → ffmpeg clips → concat into `output/zipsa_shorts_<id>.mp4` |
| `.github/workflows/daily_shorts.yml` | Runs the pipeline Mon/Wed/Fri 00:00 UTC (+ manual dispatch), uploads MP4s as artifact `all-zipsa-shorts` |

Pipeline per product (`build_shorts_for_product`):
1. `fetch_coupang_api_product(keyword)` — HMAC-signed search (`generate_hmac`), top 3 images + title.
2. For each scene: `generate_tts` (voice `ko-KR-InJoonNeural`) → `create_scene_frame` (1080×1920) → ffmpeg zoompan clip (AAC 44.1 kHz stereo).
3. Concat clips with re-encode (intentional — stream-copy concat caused audio crackle).

Content lives in the `products` list (id, keyword, scenes[text, subtitle]). The CTA scene must
reference the same id the viewer searches for under "집사연구소".

## 2. Environment & secrets

- Secrets: `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY` (GitHub Actions secrets; never commit, never log).
- Runtime deps: Python 3.10, `edge-tts pillow requests`, system `ffmpeg`. Font `NanumGothicBold.ttf` is downloaded at runtime.
- No local Coupang keys in Claude sessions → API-dependent paths cannot be run end-to-end here; verify
  frame/ffmpeg logic with a local placeholder image instead, and say so when reporting.

## 3. Working rules

- **Plan before code.** For any non-trivial change, state the plan, edge cases, and tech-debt
  warnings first. No blind edits.
- **DRY / small modules.** Extract repeated logic (ffmpeg arg lists, paths, colors, font loading)
  into named helpers/constants. Prefer short single-purpose functions — but never compress code
  at the cost of readability or behavior. Behavior-preserving refactors only, unless a fix is the goal.
- **Verify every phase.** After a change: `python -m py_compile auto_shorts.py`; if frame or ffmpeg
  logic changed, render one scene locally and inspect the PNG/MP4. Report what was and wasn't verified.
- **Don't regress known fixes** (see §5): 44.1 kHz audio, re-encode concat, unmodified TTS rate/pitch.
- **Diagnostics.** For CI failures, read the Actions job logs (GitHub MCP `get_job_logs`) before
  guessing. Browser DevTools MCP is only usable if connected in the session — don't assume it.
- Commit only to the assigned branch; never push secrets or `output/` media.

## 4. Known risks / tech debt (open)

- **Subtitle overflow:** `create_scene_frame` draws one line at 48px with no wrapping; long subtitles
  (e.g. the CTA) can exceed the 960px box and run off-canvas. Needs width-based wrapping/auto-shrink.
- **Empty image list:** if the API returns products without `productImage`, `i % len(downloaded_imgs)`
  raises `ZeroDivisionError`. Guard and fail with a clear message.
- **No HTTP status check:** `requests.get` result isn't `raise_for_status()`-checked; non-JSON error
  bodies will throw an opaque `JSONDecodeError`.
- **Image download:** `urllib.request.urlretrieve` sends no User-Agent and has no timeout/retry; CDN may 403.
- **Global TZ mutation:** `generate_hmac` sets `os.environ["TZ"]`; `time.strftime(..., time.gmtime())` is side-effect free.
- **Silent font fallback:** `ImageFont.load_default()` can't render Korean → boxes in video. Should fail loudly.
- **Unpinned deps / old actions:** no `requirements.txt`; `actions/checkout@v3`, `setup-python@v4` are outdated.
- **Unused param:** `scene_idx` in `create_scene_frame` is unused (comment mentions per-scene crop that isn't implemented).

## 5. Decision & fix log

Append newest first: `YYYY-MM-DD — what changed — why`.

- (pre-2026-11) — ffmpeg audio forced to AAC 44.1 kHz stereo, concat re-encodes — fixes audio crackle between scenes.
- (pre-2026-11) — TTS uses default rate/pitch — modified rate/pitch caused distorted voice.
- (pre-2026-11) — Product images from Coupang Partners API instead of scraping — scraping was blocked.
