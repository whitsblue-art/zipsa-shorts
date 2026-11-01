"""YouTube Data API v3 업로드 (선택 기능).

준비
 1) Google Cloud Console에서 'YouTube Data API v3' 사용 설정
 2) OAuth 클라이언트 ID(데스크톱 앱) 생성 → JSON을 data/client_secret.json 으로 저장
 3) 첫 업로드 때 브라우저 로그인 1회 → data/youtube_token.json 에 토큰 저장(이후 자동)

기본 공개 범위는 private(비공개)다. 확인 후 YouTube Studio에서 공개로 바꾸는 것을 권장.
"""
from __future__ import annotations

from pathlib import Path

from .crawler import DATA_DIR

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET = DATA_DIR / "client_secret.json"
TOKEN_FILE = DATA_DIR / "youtube_token.json"
CATEGORY_PETS_ANIMALS = "15"


def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not CLIENT_SECRET.exists():
            raise FileNotFoundError(
                f"{CLIENT_SECRET} 가 없습니다. Google Cloud에서 OAuth 클라이언트(데스크톱 앱) JSON을 받아 저장해주세요.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        creds = flow.run_local_server(port=0)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload(video: Path, title: str, description: str, tags: list[str],
           privacy: str = "private") -> str:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=_credentials())
    body = {
        "snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:15],
                    "categoryId": CATEGORY_PETS_ANIMALS, "defaultLanguage": "ko"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    print(f"[upload] YouTube 업로드 중 ({privacy})...")
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(f"[upload] 완료: https://youtube.com/shorts/{vid}")
    return vid
