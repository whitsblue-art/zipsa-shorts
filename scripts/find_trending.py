"""최근 N일 안에 올라온 영상 중 조회수가 급등한 영상을 찾는다 (/yt-source-finder 용).

사용법:
    YT_API_KEY=... python scripts/find_trending.py --query "고양이 털" --days 14
    python scripts/find_trending.py --query "강아지 산책" --shorts-only --json /tmp/out.json

API 할당량: search.list 1회 = 100 units, videos.list / channels.list = 1 unit (하루 기본 10,000 units).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

API = "https://www.googleapis.com/youtube/v3"


def get(endpoint, key, **params):
    params["key"] = key
    res = requests.get(f"{API}/{endpoint}", params=params, timeout=15)
    if res.status_code != 200:
        sys.exit(f"YouTube API 오류 ({endpoint}): {res.status_code} {res.text[:300]}")
    return res.json()


def parse_duration(iso):
    """PT1M5S 같은 ISO 8601 길이를 초로 바꾼다."""
    total, num = 0, ""
    for ch in iso.replace("PT", ""):
        if ch.isdigit():
            num += ch
        else:
            total += int(num or 0) * {"H": 3600, "M": 60, "S": 1}.get(ch, 0)
            num = ""
    return total


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--max", type=int, default=40, help="검색할 영상 수 (최대 50)")
    p.add_argument("--shorts-only", action="store_true", help="3분 이하 영상만")
    p.add_argument("--region", default="KR")
    p.add_argument("--json", help="결과를 저장할 JSON 경로")
    args = p.parse_args()

    key = os.environ.get("YT_API_KEY")
    if not key:
        sys.exit("YT_API_KEY 환경변수가 없습니다. Google Cloud Console에서 YouTube Data API v3 키를 만들어 주세요.")

    now = datetime.now(timezone.utc)
    after = (now - timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    search = get(
        "search", key,
        part="id", q=args.query, type="video", order="viewCount",
        publishedAfter=after, regionCode=args.region, relevanceLanguage="ko",
        maxResults=min(args.max, 50),
        **({"videoDuration": "short"} if args.shorts_only else {}),
    )
    ids = [it["id"]["videoId"] for it in search.get("items", [])]
    if not ids:
        sys.exit("검색 결과가 없습니다. 키워드를 넓혀 보세요.")

    videos = get("videos", key, part="snippet,statistics,contentDetails", id=",".join(ids))["items"]
    channel_ids = sorted({v["snippet"]["channelId"] for v in videos})
    channels = get("channels", key, part="statistics", id=",".join(channel_ids))["items"]
    subs = {c["id"]: int(c["statistics"].get("subscriberCount", 0) or 0) for c in channels}

    rows = []
    for v in videos:
        sec = parse_duration(v["contentDetails"]["duration"])
        if args.shorts_only and sec > 180:
            continue
        published = datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
        age_days = max((now - published).total_seconds() / 86400, 0.5)
        views = int(v["statistics"].get("viewCount", 0))
        sub = subs.get(v["snippet"]["channelId"], 0)
        rows.append({
            "title": v["snippet"]["title"],
            "channel": v["snippet"]["channelTitle"],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "published": published.strftime("%Y-%m-%d"),
            "duration_sec": sec,
            "views": views,
            "likes": int(v["statistics"].get("likeCount", 0) or 0),
            "comments": int(v["statistics"].get("commentCount", 0) or 0),
            "views_per_day": round(views / age_days),
            "subscribers": sub,
            "views_per_sub": round(views / sub, 2) if sub else None,
        })

    rows.sort(key=lambda r: r["views_per_day"], reverse=True)

    print(f"# '{args.query}' 최근 {args.days}일 급등 영상 ({now:%Y-%m-%d} 조회)\n")
    print("| 제목 | 채널 | 업로드 | 조회수 | 일평균 | 구독자 대비 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        ratio = f"{r['views_per_sub']}배" if r["views_per_sub"] is not None else "-"
        print(f"| [{r['title']}]({r['url']}) | {r['channel']} | {r['published']} | "
              f"{r['views']:,} | {r['views_per_day']:,} | {ratio} |")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"query": args.query, "fetched": now.isoformat(), "videos": rows}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
