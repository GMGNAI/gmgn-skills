# SPDX-License-Identifier: MIT
# Copyright (c) 2026 chenjunfeng
"""全网 X 讨论搜索 —— 免 API Key。

X 的公开嵌入端点**没有搜索接口**（`timeline-search` 是 404），所以"搜 CA 看大家在说什么"
只能绕道公开搜索引擎：

    搜索引擎 → 抽 x.com/{handle}/status/{id} → 用 cdn.syndication.twimg.com 水化

水化那一步是官方端点，拿到的是真实原文 + 真实点赞/转发数，不是搜索引擎摘要。

## 关键词怎么框

CA 是唯一无歧义的凭据，但**只搜 CA 会漏掉整条叙事** —— 像「牛来」这种
Web2 叙事盘，大家聊的是名字，根本不会贴合约。所以问法覆盖三类：

    "0xbeea…"            合约地址（两种写法）
    "$牛来"              cashtag
    "牛来"               币名本身
    "牛来" (BNB OR BSC)  币名 + 链上语境

外加一条：行情源的 `twitter_username` 有时直接给的是一个 X 搜索链接
（`x.com/search?q=%24%E7%89%9B%E6%9D%A5`）—— 那等于官方告诉你该搜什么，直接拿来用。

结果**按讨论度（点赞 + 转发×2 + 回复）排序，取最高的几条**，而不是按匹配强度排。

## 引擎分工

  Brave      对中文 X 内容索引最好 —— 搜「牛来」能挖出那部同名国产动画电影扑街的
             全套讨论（互动 4000+），而这些推文一条合约都没贴。是主力。
             缺点：连发两三条就 429，所以走慢闸门，只把最有价值的问法给它。
  Bing RSS   `format=rss`，URL 不加壳、无挑战页、几乎不限流 → 兜底跑全部问法。
             缺点：对中文 X 内容索引很薄，基本只在 CA 这种英数串上有用。
  DuckDuckGo 覆盖不错但对脚本极敏感，密集请求直接返 202 挑战页。
             → 只在**后台慢队列**里跑，默认 90s 一个问法，结果攒进缓存，
               下次问同一个 CA 就能用上。

每个问法单独按 6 小时缓存，永不重复发同一条查询。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

import xsocial as X

HERE = os.path.dirname(os.path.abspath(__file__))
# 缓存写在用户缓存目录，不写包自己的安装目录。上游是单机应用，缓存放在项目下
# 无所谓；这个包会被装到 ~/.claude/skills/ 里，往安装目录写文件既脏（升级时残留）
# 又可能因为只读挂载直接失败。XDG_CACHE_HOME 尊重系统约定。
_CACHE_ROOT = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
    "gmgn-x-narrative")
CACHE_DIR = os.path.join(_CACHE_ROOT, "search")
QUERY_DIR = os.path.join(CACHE_DIR, "q")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SEARCH_TTL = 20 * 60          # 某个 CA 的聚合结果多久算新鲜
QUERY_TTL = 6 * 3600          # 单条查询语句「有结果」时的缓存时长
EMPTY_TTL = 20 * 60           # 「零结果」只缓存这么久 —— 否则一次落空锁死 6 小时
MAX_HYDRATE = 40              # 一次最多水化多少条（用来挑 Top）
BRAVE_QUERIES = 1             # 内联只给 Brave 一个问法，其余丢慢队列
TOP_N = int(os.environ.get("MEMEX_AGENT_TOP_DISCUSSION", "8"))   # 展示讨论度最高的几条
ENGAGEMENT_FLOOR = 20         # 仅靠币名命中时，互动量到这个数才认
DDG_MAX_QUERIES = 3           # 慢队列里每个币最多排几个问法

_brave_gate = X.Gate(float(os.environ.get("MEMEX_AGENT_BRAVE_INTERVAL", "6")), 300.0,
                     "brave")
_bing_gate = X.Gate(float(os.environ.get("MEMEX_AGENT_BING_INTERVAL", "0.6")), 120.0, "bing")
_ddg_gate = X.Gate(float(os.environ.get("MEMEX_AGENT_DDG_INTERVAL", "90")), 900.0, "ddg")

STATUS_RE = re.compile(r"(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/status/(\d+)")

_inflight = set()
_inflight_lock = threading.Lock()
_ddg_queue = queue.Queue()
_ddg_worker = None


# --------------------------------------------------------------------------
# 缓存
# --------------------------------------------------------------------------
def _key(ca, symbol):
    return re.sub(r"[^A-Za-z0-9_]", "_", (ca or symbol or "").lower())[:64]


def _path(ca, symbol):
    return os.path.join(CACHE_DIR, _key(ca, symbol) + ".json")


def _read(ca, symbol):
    try:
        with open(_path(ca, symbol), "r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return None


def _write(ca, symbol, doc):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = _path(ca, symbol) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump(doc, fp, ensure_ascii=False)
        os.replace(tmp, _path(ca, symbol))
    except Exception:
        pass


def _q_path(engine, query):
    h = hashlib.sha1(("%s|%s" % (engine, query)).encode("utf-8")).hexdigest()[:20]
    return os.path.join(QUERY_DIR, h + ".json")


def _q_read(engine, query):
    try:
        with open(_q_path(engine, query), "r", encoding="utf-8") as fp:
            doc = json.load(fp)
        ttl = QUERY_TTL if doc.get("ids") else EMPTY_TTL
        if time.time() - doc.get("at", 0) < ttl:
            return doc
    except Exception:
        pass
    return None


def _q_write(engine, query, ids):
    try:
        os.makedirs(QUERY_DIR, exist_ok=True)
        tmp = _q_path(engine, query) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump({"at": time.time(), "engine": engine, "query": query,
                       "ids": ids}, fp, ensure_ascii=False)
        os.replace(tmp, _q_path(engine, query))
    except Exception:
        pass


# --------------------------------------------------------------------------
# 引擎
# --------------------------------------------------------------------------
def _fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "accept": "text/html,application/xhtml+xml,application/rss+xml,*/*",
        "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "accept-encoding": "gzip, deflate",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        if enc == "gzip":
            raw = gzip.decompress(raw)
        elif enc == "deflate":
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        return resp.status, raw.decode("utf-8", "replace")


def _brave(query):
    code, html = _fetch("https://search.brave.com/search?q=" + urllib.parse.quote(query))
    if code != 200:
        raise RuntimeError("brave %s" % code)
    return list(dict.fromkeys(STATUS_RE.findall(html)))


def _bing(query):
    code, body = _fetch("https://www.bing.com/search?format=rss&count=50&q="
                        + urllib.parse.quote(query))
    if code != 200 or "<rss" not in body[:300]:
        raise RuntimeError("bing bad response")
    return list(dict.fromkeys(STATUS_RE.findall(body)))


def _ddg(query):
    code, html = _fetch("https://duckduckgo.com/html/?q=" + urllib.parse.quote(query))
    ids = list(dict.fromkeys(STATUS_RE.findall(html)))
    if not ids and (code == 202 or "anomaly" in html or len(html) < 20000):
        raise RuntimeError("challenged")
    return ids


# --------------------------------------------------------------------------
# 问法
# --------------------------------------------------------------------------
def extract_search_hint(twitter_field):
    """行情源的 twitter 字段有时是 x.com/search?q=xxx —— 等于官方给的搜索词。"""
    if not twitter_field:
        return None
    m = re.search(r"(?:x|twitter)\.com/search\?(?:[^\s]*&)?q=([^&\s]+)",
                  str(twitter_field))
    if not m:
        return None
    try:
        hint = urllib.parse.unquote(m.group(1)).strip()
    except Exception:
        return None
    return hint if 1 < len(hint) <= 40 else None


def build_queries(ca, symbol, name=None, hint=None, alpha=False):
    """返回 [(用途, 查询语句)]。CA 排前面（最准），名字紧随（覆盖 Web2 叙事盘）。"""
    qs = []
    sym = (symbol or "").lstrip("$").strip()
    nm = (name or "").strip()

    if ca:
        qs.append(("ca", 'site:x.com "%s"' % ca))
        qs.append(("ca", '"%s"' % ca))
    if sym:
        qs.append(("sym", 'site:x.com "$%s"' % sym))
        qs.append(("name", 'site:x.com "%s"' % sym))
    if nm and nm.lower() != sym.lower():
        qs.append(("name", 'site:x.com "%s"' % nm))
    if sym:
        qs.append(("name", 'site:x.com "%s" (BNB OR BSC OR CA)' % sym))
    if hint:
        qs.append(("hint", 'site:x.com %s' % hint))
    # 上了 Binance Alpha 的盘，「上所」本身就是最热的讨论点，单独问一次
    if alpha and (sym or nm):
        key = sym or nm
        qs.append(("listing", 'site:x.com "%s" (Alpha OR 币安 OR Binance)' % key))
    return qs


# --------------------------------------------------------------------------
# 校验：搜索来的结果用什么标准收
# --------------------------------------------------------------------------
def make_verifier(ca, symbol, name):
    """搜索结果的校验比时间线扫描宽松 —— 因为查询语句本身已经把关键词框死了。

    时间线扫描里"名称命中"是**撞上的**（噪声大，只当疑似）；
    搜索结果里"名称命中"是**我们主动搜的**（这条推确实包含这个词），
    再叠加「有链上语境词 / 互动量够高 / 作者在 KOL 名单里」任一条即认。
    """
    ca_low = (ca or "").lower()
    sym = (symbol or "").lstrip("$").strip().lower()
    nm = (name or "").strip().lower()

    def verify(t):
        low = (t.get("text") or "").lower()
        if ca_low and ca_low in low:
            return ("ca", ca_low[:10] + "…" + ca_low[-6:])
        if [a for a in X.ADDR_RE.findall(low) if a != ca_low]:
            return None                       # 在贴别的合约
        if sym and ("$" + sym) in low:
            return ("cashtag", "$" + sym)

        # 用带词边界的命中，别让「乳牛来说」这种子串混进来
        hit = next((c for c in (sym, nm)
                    if c and len(c) >= 2 and X.bounded_hit(t.get("text") or "", c) is not None),
                   None)
        if not hit:
            return None
        eng = t.get("likes", 0) + t.get("retweets", 0) * 2 + t.get("replies", 0)
        ctx = next((w.strip() for w in X.CONTEXT_WORDS if w in low), None)
        if ctx:
            return ("name", "%s + %s" % (hit, ctx))
        if eng >= ENGAGEMENT_FLOOR:
            return ("name", "%s · 互动 %d" % (hit, eng))
        if X.pool_meta(t.get("handle")):
            return ("name", "%s · 作者在 KOL 名单" % hit)
        return None

    return verify


# --------------------------------------------------------------------------
# DDG 后台慢队列
# --------------------------------------------------------------------------
def _ensure_ddg_worker():
    global _ddg_worker
    if _ddg_worker and _ddg_worker.is_alive():
        return

    def loop():
        while True:
            ca, symbol, name, hint = _ddg_queue.get()
            try:
                got = False
                queries = build_queries(ca, symbol, name, hint)
                # 先用 Brave 把剩下的问法补完（它中文覆盖最好，值得多花时间）
                for _, q in queries:
                    if _q_read("brave", q) or _brave_gate.status()["cooling"]:
                        continue
                    if not _brave_gate.acquire(wait=True, priority=-1):
                        break
                    try:
                        ids = _brave(q)
                        _q_write("brave", q, ids)
                        got = got or bool(ids)
                    except Exception:
                        _brave_gate.penalise()
                        break
                # DDG 一条 90s，别把一个币的问法排太满
                for _, q in queries[:DDG_MAX_QUERIES]:
                    if _q_read("ddg", q):
                        continue
                    if not _ddg_gate.acquire(wait=True, priority=-1):
                        break
                    try:
                        ids = _ddg(q)
                        _q_write("ddg", q, ids)
                        got = got or bool(ids)
                    except Exception:
                        _ddg_gate.penalise()
                        break
                if got:
                    _do_search(ca, symbol, name, hint, use_ddg_cache_only=True,
                               persist=True)
            except Exception:
                pass
            finally:
                with _inflight_lock:
                    _inflight.discard(_key(ca, symbol))
                _ddg_queue.task_done()

    _ddg_worker = threading.Thread(target=loop, name="ddg-slow", daemon=True)
    _ddg_worker.start()


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def _collect_ids(ca, symbol, name, hint, alpha=False, inline=True,
                 use_ddg_cache_only=False):
    queries = build_queries(ca, symbol, name, hint, alpha)
    found, engines, errors = [], [], []

    for eng in ("brave", "bing", "ddg"):
        for _, q in queries:
            hit = _q_read(eng, q)
            if hit:
                found.extend(tuple(x) for x in hit["ids"])
                if hit["ids"]:
                    engines.append(eng)

    if not inline or use_ddg_cache_only:
        return found, engines, errors

    # Brave 只跑最值钱的问法：币名/cashtag 优先（中文叙事全靠它），其次 CA
    brave_order = ([q for k, q in queries if k in ("name", "sym", "hint")]
                   + [q for k, q in queries if k == "ca"])
    # Brave 是**非阻塞**取闸门：抢不到就跳过，让后台慢队列去补。
    # 之前这里 wait=True，多开几个分析就全堵在 6s 的 Brave 闸门上 —— 就是"卡进程"的来源。
    brave_todo = [q for q in brave_order if not _q_read("brave", q)][:BRAVE_QUERIES]
    for q in brave_todo:
        if not _brave_gate.acquire(wait=False, priority=1):
            break
        try:
            ids = _brave(q)
            _q_write("brave", q, ids)
            _brave_gate.succeed()
            if ids:
                engines.append("brave")
            found.extend(ids)
        except Exception as exc:
            errors.append("brave: %s" % exc)
            _brave_gate.penalise()
            break

    # DDG 原来只在后台慢队列跑（90s 一条），首次分析根本用不上。
    # 但实测它是**唯一**对新盘 CA 有命中的引擎（Bing 对 X 已基本无索引，
    # Brave 中文好但一碰就 429）。所以给它一个内联机会：只问 CA 这一条，
    # 非阻塞取闸门 —— 抢不到就跳过，绝不让分析卡在这里。
    ddg_ca = next((q for k, q in queries if k == "ca"), None)
    if ddg_ca and not _q_read("ddg", ddg_ca) and _ddg_gate.acquire(wait=False, priority=1):
        try:
            ids = _ddg(ddg_ca)
            _q_write("ddg", ddg_ca, ids)
            _ddg_gate.succeed()
            if ids:
                engines.append("ddg")
            found.extend(ids)
        except Exception as exc:
            errors.append("ddg: %s" % exc)
            _ddg_gate.penalise()

    bing_todo = [q for _, q in queries if not _q_read("bing", q)]
    if bing_todo:
        def ask(q):
            if not _bing_gate.acquire(wait=True, priority=1):
                return [], None
            try:
                ids = _bing(q)
                _q_write("bing", q, ids)
                _bing_gate.succeed()
                return ids, None
            except Exception as exc:
                return [], "bing: %s" % exc
        with ThreadPoolExecutor(max_workers=min(6, len(bing_todo))) as pool:
            for ids, err in pool.map(ask, bing_todo):
                if err:
                    errors.append(err)
                elif ids:
                    engines.append("bing")
                found.extend(ids)
    return found, engines, errors


def _do_search(ca, symbol, name, hint=None, alpha=False, use_ddg_cache_only=False,
                persist=True):
    found, engines, errors = _collect_ids(ca, symbol, name, hint, alpha,
                                          use_ddg_cache_only=use_ddg_cache_only)

    seen, pairs = set(), []
    for handle, sid in found:
        if sid not in seen:
            seen.add(sid)
            pairs.append((handle, sid))
    pairs = pairs[:MAX_HYDRATE]

    verify = make_verifier(ca, symbol, name)
    now = time.time()
    fresh, historical, rejected = [], [], 0
    if pairs:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for t in pool.map(lambda p: X.single_tweet(p[1]), pairs):
                if not t or not t.get("text"):
                    continue
                got = verify(t)
                if not got:
                    rejected += 1
                    continue
                row = X._decorate(t, got[0], got[1], "search", X.pool_meta(t.get("handle")))
                row["engagement"] = (t["likes"] + t["retweets"] * 2 + t["replies"]
                                     + t.get("quotes", 0))
                ts = t.get("ts") or 0
                if ts and now - ts <= X.MENTION_WINDOW:
                    fresh.append(row)
                    X.note_discovery(t, ca, got[0])
                else:
                    historical.append(row)

    # 按讨论度排序 —— 用户要的是"讨论度最高的几个"，不是匹配最强的几个
    by_eng = lambda t: -t["engagement"]
    fresh.sort(key=by_eng)
    historical.sort(key=by_eng)

    doc = {"fetched_at": time.time(), "tweets": fresh[:TOP_N],
           "all_count": len(fresh), "historical": historical[:TOP_N],
           "historical_count": len(historical),
           "engine": "+".join(sorted(set(engines))) or None,
           "found_ids": len(pairs), "rejected": rejected,
           "queries": [q for _, q in build_queries(ca, symbol, name, hint)],
           "window": X.MENTION_WINDOW, "errors": errors[:3]}
    if persist and (fresh or historical or not errors):
        _write(ca, symbol, doc)
    return doc


QUEUE_MAX = int(os.environ.get("MEMEX_AGENT_SEARCH_QUEUE", "8"))


def _queue_ddg(ca, symbol, name, hint):
    """丢进后台慢队列。队列封顶，满了就丢弃 —— 积压几十个只会让每个都更晚拿到。"""
    k = _key(ca, symbol)
    with _inflight_lock:
        if k in _inflight or len(_inflight) >= QUEUE_MAX:
            return
        _inflight.add(k)
    _ensure_ddg_worker()
    _ddg_queue.put((ca, symbol, name, hint))


def search(ca, symbol=None, name=None, hint=None, alpha=False, allow_inline=True):
    """给分析链用的入口。Bing 内联出即时结果，DDG 丢慢队列补深度。

    state: fresh(缓存新鲜) / live(刚查的) / stale(旧缓存) / queued / cooling
    """
    doc = _read(ca, symbol)
    age = (time.time() - doc["fetched_at"]) if doc else None
    _queue_ddg(ca, symbol, name, hint)        # 无论如何都让慢队列去补

    if doc and age is not None and age < SEARCH_TTL:
        out = dict(doc)
        out["state"] = "fresh"
        out["age"] = int(age)
        return out

    if allow_inline and not (_bing_gate.status()["cooling"]
                             and _brave_gate.status()["cooling"]):
        fresh = _do_search(ca, symbol, name, hint, alpha)
        fresh["state"] = "live"
        fresh["age"] = 0
        return fresh

    if doc:
        out = dict(doc)
        out["state"] = "stale"
        out["age"] = int(age or 0)
        return out
    return {"tweets": [], "historical": [], "all_count": 0, "historical_count": 0,
            "engine": None, "found_ids": 0, "rejected": 0, "errors": [],
            "queries": [q for _, q in build_queries(ca, symbol, name, hint, alpha)],
            "state": "cooling", "age": None,
            "cooldown_left": _bing_gate.status()["cooldown_left"]}


def status():
    return {"brave": _brave_gate.status(), "bing": _bing_gate.status(),
            "ddg": _ddg_gate.status(), "ddg_queue": _ddg_queue.qsize()}
