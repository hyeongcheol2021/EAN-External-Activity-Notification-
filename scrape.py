"""BISKIT 비교과 + 금오공대 공지(학사안내/행사안내/일반소식)를 확인해 docs/data.json을 갱신하고 새 글이면 알림을 보냅니다."""
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA = Path("docs/data.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (personal notifier)"}
KEEP_OLD = 500                                   # 목록에서 사라진 옛 글은 최근 500개까지만 보관

BISKIT_URL = "https://biskit.kumoh.ac.kr/"
MARKER = "신청기간"

BOARD = "https://www.kumoh.ac.kr/ko/"
# (id, 이름, 주소)
BOARDS = [
    ("haksa", "학사안내", BOARD + "sub06_01_01_01.do"),
    ("event", "행사안내", BOARD + "sub06_01_01_02.do"),
    ("news",  "일반소식", BOARD + "sub06_01_01_03.do"),
]
PAGES = (0, 10)                                  # 게시판마다 1~2페이지(최신 글 약 20개)를 확인

# 공지 3곳은 '제목'에 아래 키워드가 있는 글만 알림/표시합니다. (비스킷은 필터 없음)
#  - 대회 (단, '대회의실' 제외), 공모전, 해커톤·아이디어톤 같은 '~톤', 영문 hackathon 등
KEYWORD_RE = re.compile(r"대회(?!의실)|공모전|[가-힣A-Za-z]톤|hackathon|ideathon|datathon", re.I)


def wanted(title):
    return bool(KEYWORD_RE.search(title))


# ---------------------------------------------------------------- BISKIT
def clean(text):
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"모집인원\s*\d+\s*/\s*\d+\s*명", "", text).strip()


def fetch_biskit():
    r = requests.get(BISKIT_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = {}
    for a in soup.find_all("a"):
        raw = a.get_text(" ", strip=True)
        if MARKER in raw:
            key = clean(raw)
            m = re.search(r"신청기간\s*([\d.]+\s*~\s*[\d.]+)", key)
            out[key] = dict(key=key, source="biskit", label="비교과 프로그램",
                            title=key.split("외부인")[0].strip().lstrip("- ").strip(),
                            period=m.group(1).replace(" ", "") if m else "", url=BISKIT_URL)
    return out


# ---------------------------------------------------------------- 공지 게시판
def clean_title(a):
    t = (a.get("title") or "").strip()
    if t:
        return t
    t = a.get_text(" ", strip=True)                              # title 속성이 없을 때: '공지 제목 작성자 날짜 조회' 형태 정리
    t = re.sub(r"^공지\s+", "", t)
    return re.sub(r"\s+\S+\s+\d{4}-\d{2}-\d{2}\s+\d+$", "", t).strip()


def make_board_fetcher(sid, label, url):
    def fetch():
        out, total = {}, 0
        for off in PAGES:
            params = {"mode": "list", "articleLimit": 10, "article.offset": off}
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                m = re.search(r"articleNo=(\d+)", a["href"])
                if not m or "mode=view" not in a["href"]:
                    continue
                total += 1
                title = clean_title(a)
                if not wanted(title):
                    continue
                no = m.group(1)
                tr = a.find_parent("tr")
                text = tr.get_text(" ", strip=True) if tr else ""
                d = re.search(r"\d{4}-\d{2}-\d{2}", text)
                cat = ""
                for td in (tr.find_all("td") if tr else []):
                    t = td.get_text(strip=True)
                    if re.fullmatch(r"\[[^\]]{1,10}\]", t):
                        cat = t.strip("[]"); break
                key = f"{sid}:{no}"
                out[key] = dict(key=key, source=sid, label=label, no=int(no), title=title,
                                date=d.group(0) if d else "", cat=cat, url=f"{url}?mode=view&articleNo={no}")
        if total == 0:                                 # 글 링크가 하나도 없으면 구조 변경/접속 차단으로 판단
            raise ValueError("게시글 목록을 찾지 못했습니다 (구조 변경 또는 접속 차단 가능성)")
        return out
    return fetch


# ---------------------------------------------------------------- 알림
def short_period(p):
    m = re.match(r"\d{4}\.(\d{2})\.(\d{2})\s*~\s*\d{4}\.(\d{2})\.(\d{2})", p)
    return f"{m[1]}/{m[2]} ~ {m[3]}/{m[4]}" if m else p


def build_messages(it):
    """(디스코드용 마크다운, 텔레그램용 HTML)"""
    if it["source"] == "biskit":
        per = short_period(it.get("period", ""))
        return (f"🔔 **새로운 비교과 프로그램**\n\n**[{it['title']}]**\n신청기간: {per}",
                f"🔔 <b>새로운 비교과 프로그램</b>\n\n<b>[{html.escape(it['title'])}]</b>\n신청기간: {per}")
    tag = it["label"] + (f" · {it['cat']}" if it.get("cat") else "")
    meta = f"{it['date']}\n" if it.get("date") else ""
    return (f"🔔 **새 공지 · {tag}**\n\n**{it['title']}**\n{meta}{it['url']}",
            f"🔔 <b>새 공지 · {html.escape(tag)}</b>\n\n<b>{html.escape(it['title'])}</b>\n{meta}{it['url']}")


def notify(it):
    discord, telegram = build_messages(it)
    hook = os.getenv("DISCORD_WEBHOOK")
    if hook:
        requests.post(hook, json={"content": discord}, timeout=15)
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": telegram, "parse_mode": "HTML"}, timeout=15)


# ---------------------------------------------------------------- 메인
def main():
    sources = [("biskit", fetch_biskit)] + [(sid, make_board_fetcher(sid, lb, u)) for sid, lb, u in BOARDS]

    old = json.loads(DATA.read_text("utf-8")) if DATA.exists() else None
    known = {}
    if old:
        for i in old["items"]:
            i.setdefault("source", "biskit"); i.setdefault("label", "비교과 프로그램"); i.setdefault("url", BISKIT_URL)
            if i["source"] != "biskit" and not wanted(i["title"]):
                continue                                   # 이전 버전에서 저장된 키워드 없는 공지는 정리
            known[i["key"]] = i
    baselined = set(old.get("sources", ["biskit"])) if old else set()   # 처음 보는 출처는 알림 없이 기록만
    now = int(time.time())
    failed = []

    for sid, fetch in sources:
        try:
            cur = fetch()
        except Exception as e:
            print(f"[{sid}] 실패: {e}"); failed.append(sid); continue
        if not cur and sid == "biskit":
            print("[biskit] 항목을 찾지 못했습니다 (구조 변경 또는 접속 차단 가능성)"); failed.append(sid); continue
        first = sid not in baselined
        for k in list(cur)[::-1]:                      # 오래된 것부터
            if k not in known:
                cur[k]["first_seen"] = now
                known[k] = cur[k]
                if not first:
                    try: notify(cur[k])
                    except Exception as e: print(f"  알림 전송 실패({k}): {e}")
                    print(f"[{sid}] 새 글: {cur[k]['title']}")
        for k, it in known.items():
            if it["source"] == sid:
                it["active"] = k in cur
        baselined.add(sid)
        print(f"[{sid}] 확인 완료" + (" (첫 기록)" if first else ""))

    items = sorted(known.values(), key=lambda i: -i.get("first_seen", 0))
    keep = [i for i in items if i.get("active")]
    keep += [i for i in items if not i.get("active")][:KEEP_OLD]
    keep.sort(key=lambda i: -i.get("first_seen", 0))
    new_data = {"items": keep, "sources": sorted(baselined)}
    if old is None or old.get("items") != keep or old.get("sources") != new_data["sources"]:
        new_data["updated"] = now
        DATA.parent.mkdir(exist_ok=True)
        DATA.write_text(json.dumps(new_data, ensure_ascii=False, indent=1), "utf-8")
        print("변경 사항 저장")
    else:
        print("변경 없음")
    if failed:
        sys.exit(f"실패한 출처: {', '.join(failed)}")


if __name__ == "__main__":
    main()
