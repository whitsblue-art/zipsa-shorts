"""채널 댓글에서 키워드를 찾아 안내 답글을 자동으로 단다.

GitHub Actions가 매시 20분에 실행한다 (.github/workflows/comment_bot.yml).
상태 파일 없이 동작한다: 채널 주인이 이미 답글을 단 댓글은 건너뛰므로 여러 번 돌아도 중복 답글이 생기지 않는다.

필요한 환경변수 (GitHub Secrets):
    YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
    → comment_bot/get_refresh_token.py로 한 번만 발급

사용법:
    python comment_bot/auto_reply.py --dry-run   # 답글 대상만 출력
    python comment_bot/auto_reply.py             # 실제로 답글 등록

API 할당량: commentThreads.list 1 unit, comments.insert 50 units (하루 기본 10,000 units).
"""
import argparse
import json
import os
import sys
import unicodedata
from datetime import datetime, timedelta, timezone

import requests

API = "https://www.googleapis.com/youtube/v3"
HERE = os.path.dirname(os.path.abspath(__file__))


def access_token():
    missing = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if missing:
        sys.exit(f"환경변수가 없습니다: {', '.join(missing)}")
    res = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=15)
    if res.status_code != 200:
        sys.exit(f"토큰 갱신 실패: {res.status_code} {res.text[:300]}\n"
                 "OAuth 앱이 '테스트' 상태면 refresh token이 7일 뒤 만료됩니다. get_refresh_token.py를 다시 실행하세요.")
    return res.json()["access_token"]


class YouTube:
    def __init__(self, token):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"

    def get(self, endpoint, **params):
        res = self.s.get(f"{API}/{endpoint}", params=params, timeout=15)
        res.raise_for_status()
        return res.json()

    def my_channel_id(self):
        items = self.get("channels", part="id", mine="true")["items"]
        if not items:
            sys.exit("이 계정에 연결된 채널이 없습니다.")
        return items[0]["id"]

    def recent_threads(self, channel_id, since):
        """채널 전체 영상의 댓글 스레드를 최신순으로, since 이후 것만 가져온다."""
        token = None
        while True:
            data = self.get(
                "commentThreads", part="snippet,replies", allThreadsRelatedToChannelId=channel_id,
                order="time", maxResults=100, textFormat="plainText",
                **({"pageToken": token} if token else {}),
            )
            for t in data.get("items", []):
                published = t["snippet"]["topLevelComment"]["snippet"]["publishedAt"]
                if datetime.fromisoformat(published.replace("Z", "+00:00")) < since:
                    return
                yield t
            token = data.get("nextPageToken")
            if not token:
                return

    def reply_authors(self, thread):
        """스레드에 달린 답글 작성자 채널 ID 목록. 답글이 5개를 넘으면 전부 다시 조회한다."""
        replies = thread.get("replies", {}).get("comments", [])
        if thread["snippet"].get("totalReplyCount", 0) > len(replies):
            replies, token = [], None
            while True:
                data = self.get("comments", part="snippet", parentId=thread["id"], maxResults=100,
                                **({"pageToken": token} if token else {}))
                replies += data.get("items", [])
                token = data.get("nextPageToken")
                if not token:
                    break
        return {r["snippet"].get("authorChannelId", {}).get("value") for r in replies}

    def reply(self, parent_id, text):
        res = self.s.post(f"{API}/comments", params={"part": "snippet"},
                          json={"snippet": {"parentId": parent_id, "textOriginal": text}}, timeout=15)
        res.raise_for_status()
        return res.json()["id"]


def normalize(text):
    return unicodedata.normalize("NFC", text).lower().replace(" ", "")


def load_config():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    for rule in cfg["rules"]:
        if "{link}" in rule["reply"] and not rule.get("link", "").strip():
            sys.exit(f"규칙 '{rule['name']}'의 link가 비어 있습니다. comment_bot/config.json에 안내 링크를 넣어 주세요.")
        rule["text"] = rule["reply"].replace("{link}", rule.get("link", "").strip())
        rule["norm_keywords"] = [normalize(k) for k in rule["keywords"]]
    return cfg


def match_rule(text, rules):
    norm = normalize(text)
    for rule in rules:
        if any(k in norm for k in rule["norm_keywords"]):
            return rule
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="답글을 달지 않고 대상만 출력")
    args = p.parse_args()

    cfg = load_config()
    yt = YouTube(access_token())
    me = yt.my_channel_id()
    since = datetime.now(timezone.utc) - timedelta(hours=cfg.get("lookback_hours", 48))
    ignore = set(cfg.get("ignore_authors", [])) | {me}

    checked = replied = failed = 0
    for thread in yt.recent_threads(me, since):
        checked += 1
        top = thread["snippet"]["topLevelComment"]["snippet"]
        author = top.get("authorChannelId", {}).get("value")
        if author in ignore:
            continue
        rule = match_rule(top.get("textOriginal") or top.get("textDisplay", ""), cfg["rules"])
        if not rule:
            continue
        if me in yt.reply_authors(thread):
            continue  # 이미 답글 단 댓글

        preview = (top.get("textOriginal") or "")[:40].replace("\n", " ")
        if args.dry_run:
            print(f"[dry-run] {rule['name']} ← {top.get('authorDisplayName')}: {preview}")
        else:
            try:
                yt.reply(thread["id"], rule["text"])
            except requests.HTTPError as e:
                failed += 1
                print(f"[실패] {preview}: {e.response.status_code} {e.response.text[:200]}")
                continue
            print(f"[답글] {rule['name']} ← {top.get('authorDisplayName')}: {preview}")
        replied += 1

    print(f"확인한 댓글 {checked}개, 답글 {'대상' if args.dry_run else '등록'} {replied}개, 실패 {failed}개")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
