# SPDX-License-Identifier: MIT
# Copyright (c) 2026 chenjunfeng
"""X（推特）数据层 —— 免 API Key。

三条公开通道，都是官方给第三方做嵌入用的端点，无需鉴权：
  1. syndication.twitter.com/srv/timeline-profile/screen-name/{handle}
     → 内嵌 __NEXT_DATA__ 的 HTML，含该账号最近 ~100 条推文与互动数。
     ⚠️ 按 IP 严格限流，密集并发直接 429 一片 → 走令牌桶 + 磁盘缓存 + 后台预热。
  2. cdn.syndication.twimg.com/tweet-result?id={id}
     → 单条推文详情。实测这个域名限流宽松得多（6 并发 0.8s 无 429），
       所以水化走独立的松闸门，可以并发。
  3. 见 x_search.py —— 用公开搜索引擎补"全网讨论"。

## KOL 名单怎么来的

不靠拍脑袋列名人。上游钱包榜 `rank/bsc/wallets/{period}?tag=kol|renowned|smart_degen`
带每个钱包绑定的 X 账号，这些是**链上实盘验证过的打狗 KOL**——按已实现盈利排序，
拉三个 tag × 三个周期能凑出约 200 个唯一句柄，实测 syndication 可读率 11/12。

最终监控名单 = 用户手工名单（kol_list.json，永远优先预热）+ 池子里盈利 Top N。
"""
from __future__ import annotations

import calendar
import gzip
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
HERE = os.path.dirname(os.path.abspath(__file__))
# 所有**会被写入**的路径都必须在用户缓存目录下，不能在 HERE 下。
# 缓存写在用户缓存目录，不写包自己的安装目录。上游是单机应用，缓存放在项目下
# 无所谓；这个包会被装到 ~/.claude/skills/ 里，往安装目录写文件既脏（升级时残留）
# 又可能因为只读挂载直接失败。XDG_CACHE_HOME 尊重系统约定。
_CACHE_ROOT = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
    "gmgn-x-narrative")
# 用户手工维护的 KOL 名单。这个也会被 save_kols() 写回，所以同样不能放在 HERE ——
# 二次筛查时发现它是唯一漏掉的写入点，装在只读位置会直接抛异常。
KOL_FILE = os.path.join(_CACHE_ROOT, "kol_list.json")
CACHE_DIR = os.path.join(_CACHE_ROOT, "x")
POOL_FILE = os.path.join(_CACHE_ROOT, "kol_pool.json")

TIMELINE_TTL = 30 * 60        # 时间线缓存多久算新鲜
STALE_OK = 12 * 3600          # 超过这个岁数就不再拿来用
MIN_INTERVAL = 4.0            # timeline 端点两次请求最小间隔（秒）
COOLDOWN_ON_429 = 180.0       # 撞限流后的静默期
POOL_TTL = 6 * 3600           # KOL 池刷新周期
WARM_LIMIT = int(os.environ.get("MEMEX_AGENT_KOL_WARM", "140"))   # 后台预热上限
# 热点提及的有效期。meme 盘节奏快，超过这个窗口的讨论只归档不计分。
MENTION_WINDOW = int(os.environ.get("MEMEX_AGENT_MENTION_WINDOW", str(24 * 3600)))
HOT_WINDOW = 6 * 3600          # 窗口内再分「热」和「温」
DISCOVERED_FILE = os.path.join(_CACHE_ROOT, "discovered.json")


# --------------------------------------------------------------------------
# 限速闸门
# --------------------------------------------------------------------------
class Gate:
    """令牌桶 + 撞墙冷却 + **优先级**。

    优先级是后加的，因为踩过坑：后台预热/慢队列用 `acquire(wait=True)` 死等，
    会把用户当下发起的请求饿死 —— 表现就是"多分析几个币就卡住"。
    现在前台传 priority=1，后台传 priority=-1；只要有前台在等，后台一律让路。

    另外撞 429 后会**自适应拉长间隔**（×1.6，封顶 8 倍），连续成功再慢慢收回来。
    """

    def __init__(self, min_interval, cooldown, name=""):
        self.base_interval = min_interval
        self.min_interval = min_interval
        self.cooldown = cooldown
        self.name = name
        self._lock = threading.Lock()
        self._last = 0.0
        self._hp_waiting = 0
        self._ok_streak = 0
        self.cooldown_until = 0.0
        self.blocked_count = 0

    def acquire(self, wait=True, priority=0):
        if priority > 0:
            with self._lock:
                self._hp_waiting += 1
        try:
            while True:
                with self._lock:
                    now = time.time()
                    if now < self.cooldown_until:
                        if not wait:
                            return False
                        sleep_for = min(3.0, self.cooldown_until - now)
                    elif priority <= 0 and self._hp_waiting > 0:
                        if not wait:
                            return False
                        sleep_for = 0.25          # 后台让路
                    elif now - self._last >= self.min_interval:
                        self._last = now
                        return True
                    else:
                        if not wait:
                            return False
                        sleep_for = self.min_interval - (now - self._last)
                time.sleep(max(0.05, sleep_for))
        finally:
            if priority > 0:
                with self._lock:
                    self._hp_waiting -= 1

    def penalise(self):
        with self._lock:
            self.cooldown_until = time.time() + self.cooldown
            self.blocked_count += 1
            self._ok_streak = 0
            self.min_interval = min(self.base_interval * 8, self.min_interval * 1.6)

    def succeed(self):
        with self._lock:
            self._ok_streak += 1
            if self._ok_streak >= 5 and self.min_interval > self.base_interval:
                self.min_interval = max(self.base_interval, self.min_interval / 1.3)
                self._ok_streak = 0

    def status(self):
        with self._lock:
            return {"name": self.name,
                    "cooling": time.time() < self.cooldown_until,
                    "cooldown_left": max(0, int(self.cooldown_until - time.time())),
                    "interval": round(self.min_interval, 1),
                    "waiting": self._hp_waiting,
                    "hit_429": self.blocked_count}


_gate = Gate(MIN_INTERVAL, COOLDOWN_ON_429, "timeline")
# 后台预热会一直占着 timeline 闸门，前台请求如果也 wait 就会被饿死。
# 所以前台一律非阻塞取闸门，取不到就把 handle 丢进优先队列让预热线程下一轮先抓。
_priority = []
_priority_lock = threading.Lock()


def request_warm(handle):
    h = resolve_handle(handle)
    if not h:
        return
    with _priority_lock:
        if h not in _priority:
            _priority.append(h)


def _take_priority():
    with _priority_lock:
        out = _priority[:]
        del _priority[:]
    return out
_tweet_gate = Gate(0.12, 60.0, "tweet")     # 松：只防雪崩，不防限流
_mem = {}
_mem_lock = threading.Lock()


# --------------------------------------------------------------------------
# 磁盘缓存
# --------------------------------------------------------------------------
def _cache_path(handle):
    return os.path.join(CACHE_DIR, re.sub(r"[^A-Za-z0-9_]", "_", handle.lower()) + ".json")


def _cache_read(handle):
    with _mem_lock:
        hit = _mem.get(handle.lower())
    if hit:
        return hit
    try:
        with open(_cache_path(handle), "r", encoding="utf-8") as fp:
            doc = json.load(fp)
        with _mem_lock:
            _mem[handle.lower()] = doc
        return doc
    except Exception:
        return None


def _cache_write(handle, tweets, ok=True):
    doc = {"handle": handle, "fetched_at": time.time(), "ok": ok, "tweets": tweets}
    with _mem_lock:
        _mem[handle.lower()] = doc
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = _cache_path(handle) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump(doc, fp, ensure_ascii=False)
        os.replace(tmp, _cache_path(handle))
    except Exception:
        pass
    return doc


def cache_age(handle):
    doc = _cache_read(handle)
    return None if not doc else time.time() - doc.get("fetched_at", 0)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "accept": "text/html,application/json,*/*",
        "accept-language": "en-US,en;q=0.9",
        "accept-encoding": "gzip, deflate",
        "referer": "https://platform.twitter.com/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        if enc == "gzip":
            raw = gzip.decompress(raw)
        elif enc == "deflate":
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        return raw.decode("utf-8", "replace")


# --------------------------------------------------------------------------
# 链接解析
# --------------------------------------------------------------------------
_HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")
_SKIP_PATHS = {"i", "search", "hashtag", "home", "explore", "intent", "share", "compose"}


def resolve_handle(url_or_handle):
    if not url_or_handle:
        return None
    s = str(url_or_handle).strip()
    if s.startswith("@"):
        s = s[1:]
    if "/" not in s and _HANDLE_RE.match(s):
        return s
    m = re.search(r"(?:twitter\.com|x\.com)/([^/?#]+)", s, re.I)
    if not m:
        return None
    handle = urllib.parse.unquote(m.group(1))
    if handle.lower() in _SKIP_PATHS or not _HANDLE_RE.match(handle):
        return None
    return handle


def resolve_status_id(url):
    if not url:
        return None
    m = re.search(r"/status(?:es)?/(\d+)", str(url))
    return m.group(1) if m else None


# --------------------------------------------------------------------------
# 归一化
# --------------------------------------------------------------------------
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def _parse_ts(s):
    if not s:
        return 0
    s = str(s)
    m = re.match(r"\w{3} (\w{3}) (\d{2}) (\d{2}):(\d{2}):(\d{2}) [+-]\d{4} (\d{4})", s)
    if m:
        mon, day, hh, mm, ss, yr = m.groups()
        return calendar.timegm((int(yr), _MONTHS.get(mon, 1), int(day),
                                int(hh), int(mm), int(ss), 0, 0, 0))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", s)
    if m:
        y, mo, d, hh, mm, ss = (int(x) for x in m.groups())
        return calendar.timegm((y, mo, d, hh, mm, ss, 0, 0, 0))
    return 0


def _outbound(entities):
    """抽外链。Web2 叙事源就是从这里挖出来的（小红书 / 微博 / 抖音 / 新闻…）。"""
    out = []
    for u in ((entities or {}).get("urls") or []):
        ex = u.get("expanded_url") or u.get("url")
        if ex and "twitter.com" not in ex and "x.com" not in ex:
            out.append(ex)
    return out


def _norm_tweet(t):
    user = t.get("user") or {}
    handle = user.get("screen_name")
    return {
        "id": t.get("id_str") or str(t.get("id") or ""),
        "text": t.get("full_text") or t.get("text") or "",
        "created_at": t.get("created_at"),
        "ts": _parse_ts(t.get("created_at")),
        "likes": int(t.get("favorite_count") or 0),
        "retweets": int(t.get("retweet_count") or 0),
        "replies": int(t.get("reply_count") or t.get("conversation_count") or 0),
        "quotes": int(t.get("quote_count") or 0),
        "lang": t.get("lang"),
        "handle": handle,
        "author": user.get("name"),
        "followers": int(user.get("followers_count") or 0),
        "verified": bool(user.get("is_blue_verified") or user.get("verified")),
        "avatar": user.get("profile_image_url_https") or "",
        "links": _outbound(t.get("entities")),
        "url": ("https://x.com/%s/status/%s" % (handle, t.get("id_str"))) if handle else None,
    }


# --------------------------------------------------------------------------
# 拉取
# --------------------------------------------------------------------------
def refresh_timeline(handle, force=False, wait=True, priority=0):
    handle = resolve_handle(handle)
    if not handle:
        return []
    doc = _cache_read(handle)
    if doc and not force and time.time() - doc.get("fetched_at", 0) < TIMELINE_TTL:
        return doc.get("tweets") or []
    if not _gate.acquire(wait=wait, priority=priority):
        request_warm(handle)          # 排到预热线程的插队位，下一轮优先抓
        return (doc or {}).get("tweets") or []

    url = "https://syndication.twitter.com/srv/timeline-profile/screen-name/%s" % handle
    try:
        html = _fetch(url)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            _gate.penalise()
        if doc:
            return doc.get("tweets") or []
        _cache_write(handle, [], ok=False)
        return []
    except Exception:
        if doc:
            return doc.get("tweets") or []
        _cache_write(handle, [], ok=False)
        return []

    _gate.succeed()
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    tweets = []
    if m:
        try:
            data = json.loads(m.group(1))
            entries = (((data.get("props") or {}).get("pageProps") or {})
                       .get("timeline") or {}).get("entries") or []
            for e in entries:
                if e.get("type") != "tweet":
                    continue
                tw = (e.get("content") or {}).get("tweet")
                if tw:
                    tweets.append(_norm_tweet(tw))
        except Exception:
            tweets = []
    _cache_write(handle, tweets, ok=bool(tweets))
    return tweets


def timeline(handle, allow_network=True, blocking=False):
    """读时间线。默认**非阻塞**：缓存过期且闸门被占就用旧缓存 + 排队，绝不干等。"""
    handle = resolve_handle(handle)
    if not handle:
        return []
    doc = _cache_read(handle)
    age = (time.time() - doc.get("fetched_at", 0)) if doc else None
    if doc and age is not None and age < TIMELINE_TTL:
        return doc.get("tweets") or []
    if allow_network:
        fresh = refresh_timeline(handle, wait=blocking)
        if fresh:
            return fresh
    if doc and age is not None and age < STALE_OK:
        return doc.get("tweets") or []
    return []


def single_tweet(status_id):
    """单条推文水化。走松闸门，可以并发调用。"""
    if not status_id:
        return None
    key = "tweet:" + str(status_id)
    with _mem_lock:
        hit = _mem.get(key)
    if hit and time.time() - hit["fetched_at"] < 1800:
        return hit["tweet"]
    if not _tweet_gate.acquire(wait=True, priority=1):
        return None
    url = "https://cdn.syndication.twimg.com/tweet-result?id=%s&lang=en&token=a" % status_id
    try:
        doc = json.loads(_fetch(url))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            _tweet_gate.penalise()
        return None
    except Exception:
        return None
    user = doc.get("user") or {}
    ents = doc.get("entities") or {}
    out = {
        "id": doc.get("id_str") or str(status_id),
        "text": doc.get("text") or "",
        "created_at": doc.get("created_at"),
        "ts": _parse_ts(doc.get("created_at")),
        "likes": int(doc.get("favorite_count") or 0),
        "retweets": int(doc.get("conversation_count") or 0),
        "replies": int(doc.get("conversation_count") or 0),
        "quotes": 0,
        "lang": doc.get("lang"),
        "handle": user.get("screen_name"),
        "author": user.get("name"),
        "followers": int(user.get("followers_count") or 0),
        "verified": bool(user.get("is_blue_verified") or user.get("verified")),
        "avatar": user.get("profile_image_url_https") or "",
        "links": _outbound(ents),
        "media": [m.get("expanded_url") for m in (ents.get("media") or []) if m.get("expanded_url")],
        "url": "https://x.com/%s/status/%s" % (user.get("screen_name") or "i", status_id),
    }
    with _mem_lock:
        _mem[key] = {"fetched_at": time.time(), "tweet": out}
    return out


def profile(handle, allow_network=True, blocking=False):
    tl = timeline(handle, allow_network=allow_network, blocking=blocking)
    if not tl:
        return None
    now = time.time()
    recent = [t for t in tl if t["ts"] and now - t["ts"] < 7 * 86400]
    eng = [t["likes"] + t["retweets"] + t["replies"] + t["quotes"] for t in tl[:30]]
    return {
        "handle": tl[0]["handle"], "name": tl[0]["author"], "avatar": tl[0]["avatar"],
        "followers": tl[0]["followers"], "verified": tl[0]["verified"],
        "posts_7d": len(recent),
        "avg_engagement": int(sum(eng) / len(eng)) if eng else 0,
        "cache_age": cache_age(handle), "latest": tl[:5], "partial": False,
    }


def profile_from_tweet(tweet):
    if not tweet or not tweet.get("handle"):
        return None
    return {
        "handle": tweet["handle"], "name": tweet.get("author"),
        "avatar": tweet.get("avatar", ""), "followers": tweet.get("followers", 0),
        "verified": tweet.get("verified", False), "posts_7d": 0,
        "avg_engagement": tweet.get("likes", 0) + tweet.get("retweets", 0),
        "latest": [tweet], "partial": True, "cache_age": 0,
    }


# --------------------------------------------------------------------------
# KOL 池：从 链上盈利榜反推真实打狗 KOL
# --------------------------------------------------------------------------
DEFAULT_KOLS = [
    "cz_binance", "heyibinance", "binance", "BNBCHAIN", "PancakeSwap",
    "gmgnai", "lookonchain",
]

_pool_lock = threading.Lock()


def _pool_read():
    try:
        with open(POOL_FILE, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return None


def refresh_kol_pool(force=False):
    """拉 链上盈利钱包榜里绑定了 X 的地址，按已实现盈利排序存成 KOL 池。"""
    doc = _pool_read()
    if doc and not force and time.time() - doc.get("fetched_at", 0) < POOL_TTL:
        return doc

    # 上游项目这里打的是内部端点 smart_money_rank。这个包只用官方 OpenAPI，
    # 所以改走 /v1/user/kol 与 /v1/user/smartmoney（各权重 1）—— 实测两者的
    # maker_info 里都带 twitter_username，20/20 行全有，够建池子。
    import openapi as API   # 延迟导入，避免模块级循环依赖

    pool = {}
    for tag, fn in (("kol", API.kol), ("smart_degen", API.smart_money)):
        try:
            rows = fn(limit=100)
        except Exception:
            continue
        for r in rows:
            mi = (r or {}).get("maker_info") or {}
            h = resolve_handle((mi.get("twitter_username") or "").strip())
            if not h:
                continue
            e = pool.setdefault(h.lower(), {
                "handle": h, "name": mi.get("twitter_name") or h,
                "avatar": mi.get("avatar") or "", "tags": [],
                "profit": 0.0, "pnl": 0.0, "wallet": r.get("maker"),
            })
            for t in ([tag] + list(mi.get("tags") or [])):
                if t and t not in e["tags"]:
                    e["tags"].append(t)
            try:
                e["profit"] = max(e["profit"], abs(float(r.get("amount_usd") or 0)))
            except (TypeError, ValueError):
                pass

    rows = sorted(pool.values(), key=lambda x: -x["profit"])
    doc = {"fetched_at": time.time(), "kols": rows}
    if rows:
        with _pool_lock:
            try:
                os.makedirs(os.path.dirname(POOL_FILE), exist_ok=True)
                tmp = POOL_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fp:
                    json.dump(doc, fp, ensure_ascii=False)
                os.replace(tmp, POOL_FILE)
            except Exception:
                pass
    return doc


def kol_pool():
    doc = _pool_read() or {"fetched_at": 0, "kols": []}
    return doc.get("kols") or []


def pool_meta(handle):
    if not handle:
        return None
    low = handle.lower()
    for k in kol_pool():
        if k["handle"].lower() == low:
            return k
    return None


def load_kols():
    """用户手工名单。"""
    try:
        with open(KOL_FILE, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        handles = [h for h in (resolve_handle(x) for x in (data.get("handles") or [])) if h]
        return handles or list(DEFAULT_KOLS)
    except Exception:
        return list(DEFAULT_KOLS)


def save_kols(handles):
    clean = []
    for h in handles:
        r = resolve_handle(h)
        if r and r not in clean:
            clean.append(r)
    with open(KOL_FILE, "w", encoding="utf-8") as fp:
        json.dump({"handles": clean}, fp, ensure_ascii=False, indent=2)
    return clean


DISCOVERED_SLOTS = int(os.environ.get("MEMEX_AGENT_DISCOVERED_SLOTS", "20"))


def active_kols(limit=None):
    """最终监控名单 = 手工名单 + 自动发现 + 链上盈利钱包榜池，按这个优先级。

    自动发现排在池子前面：那些人是**实际在聊具体盘**被抓到的，
    比「历史上赚过钱」更贴近当下热点。
    """
    limit = WARM_LIMIT if limit is None else limit
    out, seen = [], set()

    def push(h):
        if not h or h.lower() in seen or len(out) >= limit:
            return
        seen.add(h.lower())
        out.append(h)

    for h in load_kols():
        push(h)
    for e in discovered_kols(DISCOVERED_SLOTS):
        push(e["handle"])
    for k in kol_pool():
        push(k["handle"])
    return out


def source_of(handle):
    low = (handle or "").lower()
    if low in {h.lower() for h in load_kols()}:
        return "manual"
    if low in {e["handle"].lower() for e in discovered_kols(DISCOVERED_SLOTS)}:
        return "discovered"
    return "pool"


def kol_status():
    manual = {h.lower() for h in load_kols()}
    out = []
    for h in active_kols():
        doc = _cache_read(h) or {}
        tl = doc.get("tweets") or []
        meta = pool_meta(h) or {}
        out.append({
            "handle": h, "manual": h.lower() in manual, "source": source_of(h),
            "cached": bool(doc), "ok": bool(doc.get("ok")), "count": len(tl),
            "age": int(time.time() - doc["fetched_at"]) if doc.get("fetched_at") else None,
            "followers": tl[0]["followers"] if tl else 0,
            "avatar": tl[0]["avatar"] if tl else meta.get("avatar", ""),
            "name": (tl[0]["author"] if tl else meta.get("name")) or h,
            "profit": meta.get("profit", 0), "tags": meta.get("tags", []),
        })
    ready = sum(1 for r in out if r["ok"])
    return {"kols": out, "ready": ready, "total": len(out),
            "pool_size": len(kol_pool()),
            "discovered_size": len(_disc_read()),
            "pool_age": int(time.time() - (_pool_read() or {}).get("fetched_at", 0)),
            "gate": _gate.status(), "tweet_gate": _tweet_gate.status()}


def kol_feed(limit=40):
    rows = []
    for h in active_kols():
        doc = _cache_read(h)
        if not doc:
            continue
        meta = pool_meta(h)
        for t in (doc.get("tweets") or [])[:12]:
            r = dict(t)
            if meta:
                r["kol"] = {"profit": meta["profit"], "tags": meta["tags"]}
            rows.append(r)
    rows.sort(key=lambda t: -(t.get("ts") or 0))
    return rows[:limit]


# --------------------------------------------------------------------------
# 提及扫描（只读缓存，不阻塞）
# --------------------------------------------------------------------------
ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")

# 裸符号必须配上这些上下文词才算数，否则「牛来」「utility」这种会把无关推文全捞进来
CONTEXT_WORDS = (
    "bsc", "bnb", "binance", "币安", "ca:", "合约", "contract",
    "pancake", "four.meme", "fourmeme", "flap", "gmgn", "dexscreener", "dextools",
    "meme", "土狗", "金狗", "打狗", "内盘", "外盘", "埋伏", "上车",
    "市值", "mcap", "market cap", "presale", "貔貅", "gem", "ape", "degen",
)
# 太泛的符号，即使带语境词也不认裸匹配
GENERIC_SYMBOLS = {
    "bnb", "bsc", "eth", "btc", "sol", "ca", "dev", "gm", "ai", "meme", "dog", "cat",
    "pepe", "moon", "pump", "up", "new", "usd", "usdt", "the", "and", "for", "you",
    "coin", "token", "test", "buy", "sell", "hold", "king", "queen", "cash", "gold",
    "utility", "value", "power", "money", "life", "love", "time", "world", "future",
    "trump", "elon", "musk", "baby", "safe", "star", "fire", "gold", "green", "red",
    "人生", "老子", "世界", "未来", "时间", "中国", "美国", "自由", "梦想", "生活",
    "牛市", "熊市", "行情", "价格", "交易", "赚钱", "财富",
}
PROXIMITY = 40      # 裸符号与语境词的最大字符距离

TIER_LABEL = {"ca": "合约地址", "cashtag": "$符号", "context": "名称+语境（弱）"}
TIER_WEIGHT = {"ca": 1.0, "cashtag": 0.9, "context": 0.35}
HARD_TIERS = ("ca", "cashtag")     # 只有这两档参与打分


_WORDISH = re.compile(r"[^\W_]", re.UNICODE)


def bounded_hit(text, cand):
    """找裸符号出现的位置，并要求它是一个**独立的词**。

    ascii 符号**要求原文里是全大写**（$MARS / MARS），小写的 `utility`、`value`
    绝大多数是在说那个英文单词本身，不是在说这个币；正则的两个 lookaround
    同时把词边界也管了。

    中文没有空格分词，光用 `in` 会把「乳牛来说」「bonk牛来了」「公牛来了」
    全当成「牛来」的提及 —— 这是实测抓到的误报。规则改成：
    命中处**至少有一侧**是非字母数字（标点、空格、$、#、或字符串边界）。
      乳牛来说 → 两侧都是汉字，拒
      $牛来 / #牛来 /「牛来上阿尔法了」→ 有一侧是符号或开头，收
    """
    if not cand:
        return None
    if cand.isascii():
        m = re.search(r"(?<![A-Za-z0-9])" + re.escape(cand.upper()) + r"(?![A-Za-z0-9])",
                      text)
        return m.start() if m else None
    low, c = (text or "").lower(), cand.lower()
    i = low.find(c)
    while i >= 0:
        prev = low[i - 1] if i > 0 else ""
        nxt = low[i + len(c)] if i + len(c) < len(low) else ""
        if not (prev and _WORDISH.match(prev)) or not (nxt and _WORDISH.match(nxt)):
            return i
        i = low.find(c, i + 1)
    return None


def build_matcher(ca, symbol, name=None):
    """强框定匹配器。宁可漏，不可错 —— 三档证据：

      ca       正文里出现完整合约地址          → 硬凭据，计分
      cashtag  出现 `$SYMBOL`（带美元号）      → 硬凭据，计分
      context  裸符号 + 语境词                → 弱匹配，**只展示不计分**

    排他规则：正文里只提了**别的** CA 而没提我们这个，整条丢掉 ——
    这一条砍掉的误报最多。

    context 档还额外要求：符号不在通用词表里、ascii 符号原文必须全大写、
    正文至少出现两个不同语境词、且符号与某个语境词相距不超过 40 字符。
    即便如此它也只是「疑似」，不进分数。

    返回 (tier, evidence) 或 None。
    """
    ca_low = (ca or "").lower()
    sym = (symbol or "").lstrip("$").strip().lower()
    nm = (name or "").strip().lower()

    def match(text):
        text = text or ""
        low = text.lower()

        if ca_low and ca_low in low:
            return ("ca", ca_low[:10] + "…" + ca_low[-6:])

        if [a for a in ADDR_RE.findall(low) if a != ca_low]:
            return None                      # 在贴别的合约，不是在聊这个盘

        if sym and ("$" + sym) in low:
            return ("cashtag", "$" + sym)

        ctx_hits = [(w.strip(), low.find(w)) for w in CONTEXT_WORDS if w in low]
        if len(ctx_hits) < 2:
            return None                      # 语境不足，裸匹配一律不认

        for cand in (sym, nm):
            if not cand or cand in GENERIC_SYMBOLS or len(cand) < 2:
                continue
            if cand.isascii() and len(cand) < 4:
                continue
            pos = bounded_hit(text, cand)
            if pos is None:
                continue
            near = [w for w, i in ctx_hits if abs(i - pos) <= PROXIMITY]
            if not near:
                continue
            return ("context", "%s + %s" % (cand, near[0]))
        return None

    return match


def _decorate(t, tier, evidence, source, meta=None):
    """给命中的推文打上证据、时效、来源标记，供打分和 UI 直接用。"""
    row = dict(t)
    row["match"] = tier
    row["match_label"] = TIER_LABEL.get(tier, tier)
    row["evidence"] = evidence
    row["hard"] = tier in HARD_TIERS
    row["weight"] = TIER_WEIGHT.get(tier, 0.35)
    row["source"] = source
    age = (time.time() - t["ts"]) if t.get("ts") else None
    row["age_sec"] = age
    row["heat"] = ("hot" if age is not None and age <= HOT_WINDOW
                   else "warm" if age is not None and age <= MENTION_WINDOW
                   else "old")
    if meta:
        row["kol"] = {"profit": meta["profit"], "tags": meta["tags"],
                      "wallet": meta.get("wallet")}
    return row


def handles_from_holders(holders):
    """从持有人列表里白捡 X 账号。

    `token_holders` 的每一行自带 `twitter_username` —— 我们每次分析本来就拉
    100 条，所以这一步**零额外请求**。实测「金融便利店」100 个持有人里有 16 个
    带账号，其中 10 个不在全局 KOL 池里。

    这批人的优先级应该高于全局池：持有这个币的人比「历史上赚过钱的人」
    更可能正在聊这个币。按持仓占比排序。
    """
    rows = []
    for h in holders or []:
        handle = resolve_handle(h.get("twitter_username") or "")
        if not handle:
            continue
        rows.append((handle, float(h.get("amount_percentage") or 0),
                     h.get("twitter_name") or handle))
    rows.sort(key=lambda r: -r[1])
    out, seen = [], set()
    for handle, pct, nm in rows:
        if handle.lower() in seen:
            continue
        seen.add(handle.lower())
        out.append({"handle": handle, "name": nm, "percent": pct})
    return out


def scan_mentions(ca, symbol, name=None, handles=None, extra_timelines=None,
                  window=None):
    """扫 KOL 池缓存里的提及。窗口内的算热点，窗口外的只归档不计分。"""
    window = MENTION_WINDOW if window is None else window
    handles = handles if handles is not None else active_kols()
    match = build_matcher(ca, symbol, name)
    now = time.time()

    fresh, old, seen, covered = [], [], set(), 0

    def take(t, source, meta=None):
        got = match(t.get("text"))
        if not got or t.get("id") in seen:
            return
        seen.add(t.get("id"))
        row = _decorate(t, got[0], got[1], source, meta)
        ts = t.get("ts") or 0
        if ts and now - ts <= window:
            fresh.append(row)
        else:
            old.append(row)

    for h in handles:
        doc = _cache_read(h)
        if not doc or not doc.get("tweets"):
            continue
        covered += 1
        meta = pool_meta(h)
        for t in doc["tweets"]:
            take(t, "kol", meta)
    for tl in (extra_timelines or []):
        for t in (tl or []):
            take(t, "project")

    key = lambda t: -(t["weight"] * (t["likes"] + t["retweets"] * 2 + t["replies"] + 1))
    fresh.sort(key=key)
    old.sort(key=key)
    return {"hits": fresh, "historical": old[:10], "covered": covered,
            "total": len(handles), "pool_size": len(kol_pool()), "window": window}


# --------------------------------------------------------------------------
# 自动发现：从实际讨论里沉淀新账号，让名单自己长
# --------------------------------------------------------------------------
_disc_lock = threading.Lock()


def _disc_read():
    try:
        with open(DISCOVERED_FILE, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def _disc_write(doc):
    try:
        os.makedirs(os.path.dirname(DISCOVERED_FILE), exist_ok=True)
        tmp = DISCOVERED_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump(doc, fp, ensure_ascii=False)
        os.replace(tmp, DISCOVERED_FILE)
    except Exception:
        pass


def note_discovery(tweet, ca, tier):
    """某个账号用硬证据（CA 或 $符号）聊了某个盘 → 记一笔，够格就进监控名单。

    上游钱包榜只是种子；真正在聊盘的人得从实际讨论里捞。
    """
    h = tweet.get("handle")
    if not h or tier not in ("ca", "cashtag"):
        return
    with _disc_lock:
        doc = _disc_read()
        e = doc.get(h.lower()) or {
            "handle": h, "name": tweet.get("author") or h,
            "avatar": tweet.get("avatar") or "", "followers": 0,
            "tokens": [], "hits": 0, "first_seen": time.time(),
        }
        e["name"] = tweet.get("author") or e["name"]
        e["avatar"] = tweet.get("avatar") or e["avatar"]
        e["followers"] = max(e.get("followers", 0), int(tweet.get("followers") or 0))
        if ca and ca.lower() not in e["tokens"]:
            e["tokens"].append(ca.lower())
        e["hits"] = e.get("hits", 0) + 1
        e["last_seen"] = time.time()
        doc[h.lower()] = e
        _disc_write(doc)


def discovered_kols(limit=40):
    """按「聊过几个不同的盘」排序 —— 聊得多的更像真·打狗号，而不是一次性喊单。"""
    rows = list(_disc_read().values())
    rows.sort(key=lambda e: (-len(e.get("tokens") or []), -e.get("hits", 0),
                             -e.get("followers", 0)))
    return rows[:limit]


# --------------------------------------------------------------------------
# 后台预热
# --------------------------------------------------------------------------
_warmer = None


def start_warmer():
    global _warmer
    if _warmer and _warmer.is_alive():
        return _warmer

    def drain_priority():
        for h in _take_priority():
            refresh_timeline(h, priority=-1)

    def loop():
        while True:
            try:
                refresh_kol_pool()
                drain_priority()
                for h in active_kols():
                    drain_priority()      # 前台插队的永远先抓
                    doc = _cache_read(h)
                    age = (time.time() - doc["fetched_at"]) if doc and doc.get("fetched_at") \
                        else None
                    if age is None or age > TIMELINE_TTL:
                        refresh_timeline(h, priority=-1)   # 后台，随时给前台让路
                    time.sleep(0.4)
            except Exception:
                pass
            for _ in range(15):
                drain_priority()
                time.sleep(2)

    _warmer = threading.Thread(target=loop, name="x-warmer", daemon=True)
    _warmer.start()
    return _warmer


# --------------------------------------------------------------------------
# 叙事识别
# --------------------------------------------------------------------------
# 分类靠关键词命中，所以**币名本身**也要进词表 —— 「金融便利店」是 CZ 的梗，
# 但推文正文里经常一个「币安」都不出现，只靠正文关键词会漏掉整个类别。
NARRATIVE_MAP = [
    ("币安概念", ["币安概念", "bnb概念", "金融便利店", "便利店", "cz_binance", "赵长鹏",
                  "长铁", "cz的", "cz 说", "cz发", "heyibinance", "何一", "bnbchain",
                  "bnb 生态", "bnb生态", "binance alpha", "币安alpha", "币安 alpha",
                  "上币安", "打新", "余额宝", "四哥", "四姐"]),
    ("交易所 / CEX", ["binance", "币安", "cz_", " cz ", "heyi", "upbit", "coinbase",
                      "okx", "上所", "listing", "alpha"]),
    ("政治 / 时事", ["trump", "特朗普", "election", "president", "政策", "关税", "tariff",
                     "war", "musk", "马斯克", "政府", "fed", "降息", "两会"]),
    ("动物 / 经典 meme", ["dog", "狗", "cat", "猫", "pepe", "frog", "蛙", "inu", "shib",
                          "bonk", "monkey", "猴", "capybara", "熊猫", "鸭"]),
    ("AI / 科技", ["ai", "agent", "gpt", "robot", "机器人", "deepseek", "算力", "llm",
                   "claude", "openai", "英伟达"]),
    ("明星 / 网红", ["kol", "网红", "明星", "主播", "celeb", "idol", "singer", "顶流",
                     "小红书", "抖音", "快手", "b站"]),
    ("节日 / 赛事", ["春节", "christmas", "halloween", "世界杯", "olympic", "奥运",
                     "节日", "赛事", "中秋", "国庆", "双十一"]),
    ("链上文化 / 打土狗", ["degen", "ape", "wagmi", " gm ", "打狗", "土狗", "冲", "meta",
                           "pvp", "内盘", "外盘", "叙事", "分红", "貔貅", "金狗"]),
]


def classify_narrative(texts):
    blob = " ".join(t for t in texts if t).lower()
    scored = []
    for label, keys in NARRATIVE_MAP:
        hit = [k.strip() for k in keys if k in blob]
        if hit:
            scored.append({"label": label, "weight": len(hit), "keywords": hit[:6]})
    scored.sort(key=lambda x: -x["weight"])
    return scored[:3]
