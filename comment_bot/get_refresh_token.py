"""댓글 봇용 OAuth refresh token을 발급한다. 내 컴퓨터에서 한 번만 실행.

1. Google Cloud Console → API 및 서비스 → YouTube Data API v3 사용 설정
2. OAuth 동의 화면 구성 → 게시 상태를 '프로덕션'으로 (테스트 상태면 토큰이 7일 뒤 만료)
3. 사용자 인증 정보 → OAuth 클라이언트 ID → 유형 '데스크톱 앱' → JSON 다운로드 → client_secret.json
4. pip install google-auth-oauthlib
5. python comment_bot/get_refresh_token.py client_secret.json
6. 브라우저에서 채널 계정으로 로그인 → 출력된 세 값을 GitHub Secrets에 등록
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

if len(sys.argv) != 2:
    sys.exit("사용법: python comment_bot/get_refresh_token.py client_secret.json")

flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\nGitHub 저장소 → Settings → Secrets and variables → Actions 에 등록하세요:\n")
print(f"YT_CLIENT_ID={creds.client_id}")
print(f"YT_CLIENT_SECRET={creds.client_secret}")
print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
