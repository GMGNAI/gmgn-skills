#!/usr/bin/env python3
import json, subprocess, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

TOKEN_ADDR = sys.argv[1]
CHAIN      = sys.argv[2]
LANG       = sys.argv[3] if len(sys.argv) > 3 else 'zh'

# EVM 地址自动探测链（0x... 且 chain 传入 'auto' 或未明确指定时）
KNOWN_CHAINS = ('bsc', 'eth', 'base', 'sol', 'robinhood', 'arc', 'stable')
if CHAIN == 'auto' or (TOKEN_ADDR.startswith('0x') and CHAIN not in KNOWN_CHAINS):
    for _c in ('bsc', 'eth', 'base'):
        _r = subprocess.run(['gmgn-cli', 'token', 'holders', '--chain', _c,
                             '--address', TOKEN_ADDR, '--limit', '5', '--raw'],
                            capture_output=True, text=True, timeout=15)
        if _r.returncode == 0:
            _data = json.loads(_r.stdout)
            if _data.get('list'):
                CHAIN = _c
                break
    else:
        CHAIN = 'eth'  # fallback
WINDOW     = 300   # 同步注资滑窗（秒）—— 文档要求"极短时间"，取 5 分钟
TIGHT      = 60    # 秒级同步注资，基本可判定为脚本批量打款
now_ts     = int(time.time())

# 原生代币的包装地址，用于查询实时价格来估算持仓者购买力。
# 未列出的链（arc / stable / robinhood）拿不到价格，购买力改用原生单位展示。
WNATIVE = {
    'sol':  'So11111111111111111111111111111111111111112',
    'bsc':  '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
    'eth':  '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    'base': '0x4200000000000000000000000000000000000006',
}
NATIVE_SYM = {'sol': 'SOL', 'bsc': 'BNB', 'eth': 'ETH', 'base': 'ETH'}

ZH = (LANG == 'zh')
def _(zh, en): return zh if ZH else en

def run_cli(args, timeout=30):
    r = subprocess.run(['gmgn-cli'] + args + ['--raw'],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)

with ThreadPoolExecutor(max_workers=4) as ex:
    f_holders = ex.submit(run_cli, ['token', 'holders', '--chain', CHAIN, '--address', TOKEN_ADDR, '--limit', '100'])
    f_devs    = ex.submit(run_cli, ['token', 'holders', '--chain', CHAIN, '--address', TOKEN_ADDR, '--tag', 'dev', '--limit', '20'])
    # 原生代币价格与 holders 无依赖，和上面两个请求并发，不额外增加耗时
    f_price   = (ex.submit(run_cli, ['token', 'info', '--chain', CHAIN, '--address', WNATIVE[CHAIN]])
                 if CHAIN in WNATIVE else None)

    # dev 结果一到，立即发起 created-tokens，不等 holders
    devs = f_devs.result()['list']
    _creator_tmp = next((d for d in devs if 'creator' in (d.get('maker_token_tags') or [])), None)
    f_created = None
    if _creator_tmp:
        f_created = ex.submit(run_cli, ['portfolio', 'created-tokens', '--chain', CHAIN,
                                        '--wallet', _creator_tmp['address'],
                                        '--order-by', 'token_ath_mc', '--direction', 'desc'])

    holders      = f_holders.result()['list']
    created_data = f_created.result() if f_created else None

    # 价格取不到就降级为 None —— 宁可只显示原生数量，也不编造美元金额
    NATIVE_PRICE = None
    if f_price:
        try:
            NATIVE_PRICE = float(((f_price.result() or {}).get('price') or {}).get('price') or 0) or None
        except Exception:
            NATIVE_PRICE = None

normal = [h for h in holders if h.get('addr_type', 0) == 0]
burn   = [h for h in holders if h.get('addr_type', 0) == 1]
dex    = [h for h in holders if h.get('addr_type', 0) == 2]

def pct(v):  return v * 100
def pct_s(v):
    """退化流通盘只有 0.0035% 这种量级，固定两位小数会打成 "0.00%"，读起来就是真零 ——
    而"零"和"极小但非零"在这里是两个不同结论。低于 0.01% 时切成有效数字。"""
    p = pct(v)
    if p <= 0:   return "0%"
    if p < 0.01: return f"{p:.2g}%"
    return f"{p:.2f}%"
def usd(v):
    if v is None: return "$0"
    if abs(v) >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if abs(v) >= 1_000:     return f"${v/1_000:.1f}K"
    return f"${v:.0f}"
def fmt_amt(v):
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
    if v >= 1_000:     return f"{v/1_000:.0f}K"
    return f"{v:.0f}"
def age_label(entry_ts):
    secs  = now_ts - entry_ts
    days  = secs // 86400
    hours = secs // 3600
    if ZH: return f"{hours}小时前入场" if days == 0 else f"{days}天前入场"
    else:  return f"{hours}h ago" if days == 0 else f"{days}d ago"
def addr_short(addr):
    return f"{addr[:4]}...{addr[-4:]}"
def price_str(v):
    # meme 币均价常在 1e-8 量级，固定 4 位小数会全部显示成 $0.0000
    if not v or v <= 0: return "$0"
    if v >= 0.01:       return f"${v:.4f}"
    return "$" + f"{v:.12f}".rstrip('0')

supply_list  = [h['balance']/h['amount_percentage'] for h in normal
                if h.get('amount_percentage',0)>0 and h.get('balance',0)>0]
total_supply = sorted(supply_list)[len(supply_list)//2] if supply_list else 1_000_000_000
price_list   = [h['usd_value']/h['balance'] for h in normal
                if h.get('balance',0)>0 and h.get('usd_value',0)>0]
cur_price    = sorted(price_list)[len(price_list)//2] if price_list else 0
cur_mc       = total_supply * cur_price

burn_pct = sum(h['amount_percentage'] for h in burn)
dex_pct  = sum(h['amount_percentage'] for h in dex)

# ── 流通盘基准 ──────────────────────────────────────────────────────────
# 下方所有"持仓占比"都除以 float_share，即以可流通盘为分母而非总供应。
# 理由：报告要回答的是"能砸盘的筹码占多少"，锁在 DEX 池和销毁地址里的份额
# 砸不动，把它们算进分母会把真实抛压系统性稀释（LP 占 56% 时会低估 2.3 倍）。
# burn_pct / dex_pct 本身保持总供应基准 —— 它们定义了流通盘，再用流通盘做分母会循环。
float_raw   = 1.0 - burn_pct - dex_pct
float_share = max(float_raw, 1e-9)

# ── 流通盘退化保护 ──────────────────────────────────────────────────────
# DEX 池（或销毁地址）吃掉几乎全部供应时 float_share 趋零，于是每个 `/ float_share`
# 都把尘埃钱包放大成两位数甚至 100%：实测过一个未迁移的盘，LP 占 99.9%，一个只握着
# 约 $2 代币的钱包被判成"最大单钱包持仓 100%，筹码极度集中"，评级直接给到 🔴 不建议买。
# 那个 100% 是除零噪声，不是集中度。这类币的正确结论是"此刻无法评估筹码结构"。
# 阈值取 2%：低于这个比例，Top100 里任何一个尘埃钱包都能占到"流通盘"的两位数百分比。
FLOAT_MIN        = 0.02
float_degenerate = float_raw < FLOAT_MIN

# ── 空持仓表保护 ────────────────────────────────────────────────────────
# 上游 token holders 会返回 {"list":[]}（币彻底凉了、或索引里已经没有这个盘）。
# 此时每个占比都是 0，dangers/warns 一条都不触发，级联会一路落到"🟢 集中度正常，
# 没发现明显砸盘风险"和"✅ 正常参与"—— 对一份零数据的报告给出正面结论，
# 比不给结论危险得多。"没有数据"必须显式说出来。
no_holders   = len(normal) == 0
unassessable = float_degenerate or no_holders

# 无法评估时百分比一律不上色 —— "0.00% 🔴" 或 "0.0% 🟢" 读起来像结论，其实只是除零/空集
def pf(f): return "⚪" if unassessable else f

# 无法评估时干脆不打印这个占比数字。分母趋零时同一份报告里会同时出现 "hold 100.00%"
# 和 "hold 0.00%"，两个都是除零产物而不是持仓事实。顶部横幅只解释了一次，读者扫到
# "KOL 1 hold 0.00%" 仍然会读成"KOL 没拿货"。钱包个数不经过 float_share，照常打印。
def fpct(v, dec=2): return _("无法评估", "n/a") if unassessable else f"{pct(v):.{dec}f}%"

# ── 流通盘换算只走这两个函数 ─────────────────────────────────────────────
# 不要再手写 `/ float_share`。漏掉一次除法就退回总供应基准，数字看上去仍然合理、
# 也不会报错 —— 正是本次迁移要修掉的那类 bug。集中成两个函数后，漏除法就是漏调用，
# 一眼能看出来。
# fs 故意用下标 h['amount_percentage'] 取字段：字段缺失时直接 KeyError 而不是静默算 0。
def fs(ws): return sum(h['amount_percentage'] for h in ws) / float_share  # 一组钱包的合计占比
def f1(v):  return v / float_share                                        # 单个已取出的占比值

# 集中度只数钱包地址（addr_type==0），排除 DEX 池和销毁地址。
# holders 按 amount_percentage 降序返回，normal 保持该顺序。
top10    = fs(normal[:10])
top20    = fs(normal[:20])

airdrop  = [h for h in normal if h.get('buy_tx_count_cur', 0)==0 and h.get('balance', 0)>0]
bundlers = [h for h in normal if 'bundler'      in (h.get('maker_token_tags') or [])]
rats     = [h for h in normal if 'rat_trader'   in (h.get('maker_token_tags') or [])]
snipers  = [h for h in normal if 'sniper'       in (h.get('maker_token_tags') or [])]
fresh    = [h for h in normal if 'fresh_wallet' in (h.get('tags') or [])]
wash     = [h for h in normal if 'wash_trader'  in (h.get('tags') or [])]

# ── 风险标签的唯一定义处 ────────────────────────────────────────────────
# 去重合计（risk_all）、重叠计数（risk_tag_hits）、§1 的分类明细渲染，三处都从这里派生。
# 之前这五类各自写成三份字面量列表：加第六类标签要改三个地方，漏掉 risk_all 会让
# "合计"少算而明细照常打印，输出自相矛盾且不报错。列表顺序即输出顺序。
RISK_GROUPS = [
    (_("老鼠仓",   "Rat Trader"), rats,     "🚨"),
    (_("捆绑交易", "Bundler"),    bundlers, "⚠️"),
    (_("狙击者",   "Sniper"),     snipers,  "⚠️"),
    (_("新钱包",   "Fresh"),      fresh,    ""),
    (_("刷量",     "Wash"),       wash,     ""),
]
risk_all = set(h['address'] for _lb, g, _fl in RISK_GROUPS for h in g)
risk_pct = fs(h for h in normal if h['address'] in risk_all)
# 分类明细各自求和会重复计算带多标签的钱包，总数是去重的 —— 输出时要说明差额来源
risk_tag_hits = sum(len(g) for _lb, g, _fl in RISK_GROUPS)
risk_overlap  = risk_tag_hits - len(risk_all)
# 这两个只在 §1 小结的级联里用到，但属于计算而非渲染，放在同类指标旁边
bundler_pct_val = fs(bundlers)
sniper_pct_val  = fs(snipers)

airdrop_pct  = fs(airdrop)
rats_pct     = fs(rats)

# ── 筹码质量分解 ────────────────────────────────────────────────────────
# 三个桶都保持总供应基准，分母是观测到的钱包筹码（normal_pct）：这是"看得见的筹码里
# 有多少是干净的"这一质量比值，分母就该是观测到的钱包总量。Top100 之外的长尾干净与否
# 无从得知，换成流通盘做分母会让分散型代币凭空显示成健康度下降。
#
# 旧版把"空降"和"风险标签"并成一个 all_bad 再取补集，压成单个 healthy_ratio。后果是
# 任何空投分发的币都塌成"健康筹码 0.0% 🔴"—— 和同一段里"钻石手持仓 80% ✅、Top10 12%"
# 直接打架，而且抹掉了结构：读者看不出这 0% 是因为有老鼠仓，还是仅仅因为筹码是转账来的。
# 拆开的依据是两者性质不同：风险标签是"这个地址有前科"（已证实的坏），零成本空降是
# "不知道这批筹码怎么来的"（来源未知）。未知不该和已证实的坏共用一个 🔴。
risk_chip_pct    = sum(h['amount_percentage'] for h in normal if h['address'] in risk_all)
airdrop_only     = [h for h in airdrop if h['address'] not in risk_all]   # 与风险标签去重，避免重复计
airdrop_only_pct = sum(h['amount_percentage'] for h in airdrop_only)
normal_pct       = sum(h['amount_percentage'] for h in normal)
clean_pct        = max(normal_pct - risk_chip_pct - airdrop_only_pct, 0)
clean_ratio      = (clean_pct        / normal_pct) if normal_pct > 0 else 0
risk_ratio       = (risk_chip_pct    / normal_pct) if normal_pct > 0 else 0
airdrop_ratio    = (airdrop_only_pct / normal_pct) if normal_pct > 0 else 0
# 🔴 只留给"有前科的地址占了大头"这种确定的坏。缺口主要来自零成本空降时给 🟡：
# 那是来源不透明的风险提示，不是"筹码已证实劣质"的结论。
if   risk_ratio  > 0.30:      qf = "🔴"
elif clean_ratio >= 0.50:     qf = "🟢"
elif clean_ratio >= 0.30:     qf = "🟡"
elif airdrop_ratio >= (1 - clean_ratio) * 0.8: qf = "🟡"   # 缺口几乎全是空降
else:                         qf = "🔴"
# Top100 覆盖了多少流通盘 —— 未覆盖的部分意味着所有流通盘占比都是下限
coverage      = min(f1(normal_pct), 1.0)

# ── 关联资金 ────────────────────────────────────────────────────────────
# 文档要的是"团伙作案"。只看"共用同一个转入地址"会把交易所热钱包判成团伙 ——
# 一个 CEX 热钱包给 30 个互不相关的散户打款，特征和 30 个小号一模一样。
# 硬编码 CEX 地址名单在 skill 里无法维护，改用 payload 里已有的一致性信号：
# 同一批小号通常在很短时间内、以几乎相同的金额被打款。
nonwallet_addrs = set(h['address'] for h in burn) | set(h['address'] for h in dex)

def _tr(h, k, d=0): return (h.get('native_transfer') or {}).get(k, d)

def coherent(ws):
    """时间集中 或 金额高度一致 —— 任一成立即判为强关联"""
    ts    = [t for t in (_tr(w, 'timestamp', 0) for w in ws) if t]
    am    = [float(_tr(w, 'amount', 0) or 0) for w in ws]
    tight = bool(ts) and (max(ts) - min(ts)) <= 6 * 3600
    mean  = (sum(am) / len(am)) if am else 0
    uniform = mean > 0 and (max(am) - min(am)) / mean <= 0.15
    return tight or uniform

from_map = defaultdict(list)
for h in normal:
    fa = _tr(h, 'from_address', '')
    if fa and fa not in nonwallet_addrs:
        from_map[fa].append(h)
# ≥3 个钱包才成组：2 个钱包共用转入地址的证据太弱，噪声远大于信号
_cand = [(fa, ws) for fa, ws in from_map.items() if len(ws) >= 3]
same_src_groups  = sorted([(fa, ws) for fa, ws in _cand if coherent(ws)],     key=lambda x: -len(x[1]))
weak_src_groups  = sorted([(fa, ws) for fa, ws in _cand if not coherent(ws)], key=lambda x: -len(x[1]))
# 丢弃项命名为 _src（来源地址）而不是 __ —— 单下划线 `_` 是本文件的 i18n 函数，
# `__` 看起来像与它相关的东西，容易误读
same_src_wallets = sum(len(ws) for _src, ws in same_src_groups)
weak_src_wallets = sum(len(ws) for _src, ws in weak_src_groups)
same_src_pct     = fs(h for _src, ws in same_src_groups for h in ws)
weak_src_pct     = fs(h for _src, ws in weak_src_groups for h in ws)

# 同步注资改用滑动窗口。原先的固定分桶 (ts//WINDOW)*WINDOW 漏掉跨桶边界的相邻注资：
# 两笔相隔 60 秒但落在不同桶里就检测不到。
# key 必须显式取 p[0]：默认的元组比较在 timestamp 相同时会继续比较第二项，
# 也就是拿两个 dict 相比 → TypeError，整个脚本崩掉、一行输出都没有。
# 而"同一秒被批量注资"正是本段要找的信号，时间戳撞车是常态而非边缘情况。
funded     = sorted(((_tr(h, 'timestamp', 0), h) for h in normal if _tr(h, 'timestamp', 0)),
                    key=lambda p: p[0])
win_groups = []
_cur       = []
for ts, h in funded:
    if _cur and ts - _cur[-1][0] > WINDOW:
        if len(_cur) >= 2: win_groups.append([x[1] for x in _cur])
        _cur = []
    _cur.append((ts, h))
if len(_cur) >= 2: win_groups.append([x[1] for x in _cur])
win_groups.sort(key=lambda v: -len(v))
win_pct = fs(h for v in win_groups for h in v)

def _span(v):
    ts = [t for t in (_tr(h, 'timestamp', 0) for h in v) if t]
    return (max(ts) - min(ts)) if ts else 0
tight_groups  = [v for v in win_groups if _span(v) <= TIGHT]
tight_wallets = sum(len(v) for v in tight_groups)

related = set()
for _src, ws in same_src_groups:
    for h in ws: related.add(h['address'])
for v in win_groups:
    for h in v: related.add(h['address'])
related_pct = fs(h for h in normal if h['address'] in related)
related_usd = sum(h.get('usd_value',0) for h in normal if h['address'] in related)

smart   = [h for h in normal if any(t in (h.get('tags') or []) for t in ['smart_degen','pump_smart'])]
kol     = [h for h in normal if 'kol' in (h.get('tags') or []) or 'renowned' in (h.get('tags') or [])]
whales  = [h for h in normal if 'whale' in (h.get('maker_token_tags') or [])]
partial = [h for h in normal if 0<(h.get('sell_amount_percentage') or 0)<0.5]
heavy_sell = [h for h in normal if (h.get('sell_amount_percentage') or 0)>=0.5]

# ── 钻石手必须自己买过 ──────────────────────────────────────────────────
# 旧定义只要 sell_tx==0 且 balance>0，于是零成本空降钱包全被算进钻石手：空投分发的币
# 会同时打印"空降筹码 79% 🔴"和"钻石手持仓 80% ✅ 筹码稳定"，同一批钱包被数了两次、
# 结论还相反。"钻石手"的含义是扛住了浮亏没卖 —— 没花钱买入的地址无所谓扛，
# 它不卖可能只是私钥在分发方手里。所以要求 buy_tx>0。
# 空降且未动的那批不丢弃，单独列成 idle_airdrop：它们仍是随时可能出货的零成本筹码。
diamond      = [h for h in normal if (h.get('buy_tx_count_cur') or 0)>0
                                 and (h.get('sell_tx_count_cur') or 0)==0
                                 and (h.get('balance') or 0)>0]
idle_airdrop = [h for h in normal if (h.get('buy_tx_count_cur') or 0)==0
                                 and (h.get('sell_tx_count_cur') or 0)==0
                                 and (h.get('balance') or 0)>0]

smart_pct        = fs(smart)
kol_pct          = fs(kol)
whale_pct        = fs(whales)
diamond_pct      = fs(diamond)
idle_airdrop_pct = fs(idle_airdrop)

# §4 小结的判据。原先夹在 §4 的两条 print 之间 —— 本文件的约定是"计算全在渲染之前"，
# 放回这里让那条边界重新成立
sig_count     = len(smart) + len(kol) + len(whales)
kol_selling   = [h for h in kol   if (h.get('sell_tx_count_cur') or 0) > 0]
kol_holding   = [h for h in kol   if (h.get('sell_tx_count_cur') or 0) == 0 and (h.get('balance') or 0) >= 1]
smart_selling = [h for h in smart if (h.get('sell_tx_count_cur') or 0) > 0]
smart_holding = [h for h in smart if (h.get('sell_tx_count_cur') or 0) == 0 and (h.get('balance') or 0) >= 1]

top100_map   = {h['address']: h for h in holders}
creator      = next((d for d in devs if 'creator' in (d.get('maker_token_tags') or [])), None)
sub_devs     = [d for d in devs if 'creator' not in (d.get('maker_token_tags') or [])]
dev_realized = sum(d.get('realized_profit') or 0 for d in devs)
dev_holding  = [d for d in devs if (d.get('balance') or 0)>=1]

valid_starts  = [h['start_holding_at'] for h in holders if (h.get('start_holding_at') or 0)>0]
token_launch  = min(valid_starts) if valid_starts else now_ts
durations     = [now_ts-h['start_holding_at'] for h in normal
                 if (h.get('start_holding_at') or 0)>0 and now_ts>h['start_holding_at']]
avg_hold_days = (sum(durations)/len(durations)/86400) if durations else 0

profit_w = [h for h in normal if (h.get('profit') or 0)>0]
loss_w   = [h for h in normal if (h.get('profit') or 0)<0]
# 文档问"持有者大部分盈利还是亏损"，钱包个数是字面答案；但抛压看的是筹码权重 ——
# 3 个握着 40% 流通盘的盈利钱包，威胁远大于 60 个尘埃钱包。两者都给出。
profit_pct  = fs(profit_w)
loss_pct    = fs(loss_w)
trapped     = [h for h in normal if (h.get('unrealized_pnl') or 0)<-0.2 and h.get('balance',0)>0]
trapped_pct = fs(trapped)

# 只列已确认精度的链。arc / stable / robinhood 的原生精度未确认，套 1e18 会把余额
# 算成 0.000，读起来像"这些钱包没有 gas"—— 错的数字比没有数字更危险。
NATIVE_DENOM = {'sol': 1e9, 'bsc': 1e18, 'eth': 1e18, 'base': 1e18}.get(CHAIN)
NSYM         = NATIVE_SYM.get(CHAIN, 'NATIVE')
HAS_NATIVE   = NATIVE_DENOM is not None
HAS_PRICE    = HAS_NATIVE and NATIVE_PRICE is not None
def native_amt(h):
    if not HAS_NATIVE: return 0.0
    try:    return float(h.get('native_balance') or 0) / NATIVE_DENOM
    except (TypeError, ValueError): return 0.0
def native_usd(h): return native_amt(h) * NATIVE_PRICE if HAS_PRICE else 0.0
def fmt_native(v): return f"{v:.3f} {NSYM}"

if not HAS_NATIVE:
    # 精度未知，native_balance 无法换算 —— 一个钱包都不归档，整节改为"无法评估"
    zero_wallets, low_wallets, mid_wallets, high_wallets = [], [], [], []
elif HAS_PRICE:
    zero_wallets = [h for h in normal if native_amt(h) <= 0]
    low_wallets  = [h for h in normal if 0 < native_usd(h) <= 200]
    mid_wallets  = [h for h in normal if 200 < native_usd(h) <= 1200]
    high_wallets = [h for h in normal if native_usd(h) > 1200]
else:
    # 拿不到原生代币价格就不虚构美元档位，只分"零余额 / 有余额"
    zero_wallets = [h for h in normal if native_amt(h) <= 0]
    low_wallets, mid_wallets = [], []
    high_wallets = [h for h in normal if native_amt(h) > 0]
zero_pct_val = fs(zero_wallets)
low_pct_val  = fs(low_wallets)
mid_pct_val  = fs(mid_wallets)
high_pct_val = fs(high_wallets)
high_total   = sum(native_usd(h) for h in high_wallets)
high_native  = sum(native_amt(h) for h in high_wallets)
total_buying_power        = sum(native_usd(h) for h in normal)
total_buying_power_native = sum(native_amt(h) for h in normal)

ROLE_MAP = {
    'rat_trader':   _('老鼠仓', 'Rat Trader'),
    'sniper':       _('狙击',   'Sniper'),
    'bundler':      _('捆绑',   'Bundler'),
    'whale':        _('鲸鱼',   'Whale'),
    'smart_degen':  _('聪明钱', 'Smart'),
    'pump_smart':   _('聪明钱', 'Smart'),
    'renowned':     'KOL',
    'kol':          'KOL',
    'fresh_wallet': _('新钱包', 'Fresh'),
    'wash_trader':  _('刷量',   'Wash'),
    'creator':      'Dev',
    'dev_team':     'Dev',
}
def wallet_roles(h):
    roles = []
    for t in (h.get('maker_token_tags') or [])+(h.get('tags') or []):
        if t in ROLE_MAP: roles.append(ROLE_MAP[t])
    return list(dict.fromkeys(roles))

def holding_status(h):
    sp  = h.get('sell_amount_percentage', 0) or 0
    bal = h.get('balance', 0) or 0
    if bal <= 0:   return _("已清仓",     "Cleared")
    if sp >= 0.8:  return _("🔴 大量出货", "🔴 Heavy Selling")
    if sp >= 0.3:  return _("🟡 出货中",   "🟡 Selling")
    if sp > 0:     return _("少量出货",    "Light Selling")
    return             _("持仓未动",       "Holding")

# §5 要数"这批钱包里有几个在出货"。原先的写法是把 holding_status(h) 的返回值
# 和两条本地化文案做字符串比对 —— 那是给人看的显示文本：改一个 emoji 或改一个词，
# 这里就会静默返回空列表，sell_ratio 变 0，每个批次都被降级成 🟢，而且不报任何错。
# 改成直接复用 holding_status 的同一组阈值：余额>0 且已卖出量≥30%，
# 等价于原来的 {🔴 大量出货, 🟡 出货中} 两个分支。
def is_distributing(h):
    return (h.get('balance', 0) or 0) > 0 and (h.get('sell_amount_percentage', 0) or 0) >= 0.3

def wallet_behavior(h):
    buy_tx  = h.get('buy_tx_count_cur', 0) or 0
    sell_tx = h.get('sell_tx_count_cur', 0) or 0
    if buy_tx==0 and sell_tx==0: return _("几乎无链上活动",     "Almost no on-chain activity")
    if buy_tx>0 and sell_tx==0:  return _("持续买入，尚未卖出", "Buying only, not sold yet")
    if sell_tx>0 and buy_tx==0:  return _("只卖不买",           "Selling only")
    return ""

def trend_str(wlist):
    """文档问的是"持续加仓中还是出货中"。按累计买卖笔数分桶会把绝大多数活跃钱包
    归进"买卖都有"，两个分支都答不上。改用 sell_amount_percentage（已卖出量占已买入量
    的比例）判净方向 —— 和 holding_status 用的是同一个字段。"""
    cleared, dumping, trimming, adding, holding, idle = [], [], [], [], [], []
    for h in wlist:
        sp  = h.get('sell_amount_percentage') or 0
        buy = h.get('buy_tx_count_cur') or 0
        sell = h.get('sell_tx_count_cur') or 0
        if buy == 0 and sell == 0: idle.append(h)      # 转账获得，链上无交易
        elif sp >= 0.8:  cleared.append(h)
        elif sp >= 0.3:  dumping.append(h)
        elif sp > 0:     trimming.append(h)
        elif buy >= 2:   adding.append(h)              # 多次买入且未卖出
        else:            holding.append(h)
    parts = []
    if adding:   parts.append(f"📈 {_('加仓中', 'Accumulating')} {len(adding)}")
    if holding:  parts.append(f"🤝 {_('持仓未动', 'Holding')} {len(holding)}")
    if trimming: parts.append(f"🟡 {_('少量减持', 'Trimming')} {len(trimming)}")
    if dumping:  parts.append(f"📉 {_('出货中', 'Distributing')} {len(dumping)}")
    if cleared:  parts.append(f"🔴 {_('清仓中', 'Exiting')} {len(cleared)}")
    if idle:     parts.append(f"⚪ {_('无交易', 'Idle')} {len(idle)}")
    return "  ".join(parts) if parts else "—"

def is_selling(h):     return (h.get('sell_tx_count_cur') or 0)>0 and (h.get('balance') or 0)>=1
def is_buying_only(h): return (h.get('buy_tx_count_cur') or 0)>0 and (h.get('sell_tx_count_cur') or 0)==0

biggest     = max(normal, key=lambda h: h['amount_percentage']) if normal else None
biggest_pct = f1(biggest['amount_percentage']) if biggest else 0
# 以下所有阈值都已按流通盘基准重新校准（旧值是总供应基准，直接沿用会让每条都亮红）
# 流通盘退化时这些阈值判的全是除零噪声（详见 float_degenerate），一条都不能计入评级 ——
# 不依赖百分比的判据（Dev 马甲）不受影响，照常检查。
dangers = []
if not float_degenerate:
    if rats and rats_pct > 0.05:
        dangers.append(_( f"老鼠仓持仓 {pct(rats_pct):.1f}%，出货即砸盘",
                          f"Rat traders hold {pct(rats_pct):.1f}% — instant dump risk"))
    if biggest_pct > 0.10:
        dangers.append(_( f"最大单钱包持仓 {pct(biggest_pct):.1f}%，筹码极度集中",
                          f"Largest wallet holds {pct(biggest_pct):.1f}% — extreme concentration"))
if creator:
    to_out = creator.get('token_transfer_out') or {}
    if (to_out.get('address') or '') in top100_map:
        dangers.append(_("Dev 筹码转给内部马甲，换手控盘",
                         "Dev transferred chips to internal wallet — covert control"))

warns = []
if no_holders:
    warns.append(_( "上游未返回任何持仓地址，筹码结构无法评估（本报告所有占比均为空集，不是 0%）",
                    "Upstream returned no holder addresses — chip structure not assessable (every percentage here is an empty set, not a real 0%)"))
elif float_degenerate:
    # 唯一还成立的结论就是"这盘子还没放开，没法评"。给出的是绝对值而不是百分比。
    warns.append(_( f"流通盘仅占总供应 {pct_s(float_raw)}（DEX {pct(dex_pct):.1f}% + 销毁 {pct(burn_pct):.1f}%），筹码结构无法评估",
                    f"Float is only {pct_s(float_raw)} of supply (DEX {pct(dex_pct):.1f}% + burn {pct(burn_pct):.1f}%) — chip structure not assessable"))
else:
    if dev_holding:
        # dev 来自另一个 endpoint，字段可能缺失，所以先用 .get 求和再交给 f1 换算，
        # 不走 fs（fs 用下标取字段）
        hold_pct_val = f1(sum(d.get('amount_percentage',0) for d in dev_holding))
        if hold_pct_val > 0.01:
            warns.append(_( f"Dev 仍持仓 {pct(hold_pct_val):.2f}%",
                            f"Dev still holds {pct(hold_pct_val):.2f}%"))
    if airdrop_pct > 0.2:
        warns.append(_( f"空降筹码 {pct(airdrop_pct):.1f}%，来源不透明",
                        f"Airdrop supply {pct(airdrop_pct):.1f}% — opaque origin"))
    if risk_pct > 0.35:
        warns.append(_( f"风险钱包持仓 {pct(risk_pct):.1f}%，筹码质量差",
                        f"Risk wallets hold {pct(risk_pct):.1f}% — low chip quality"))
    if related_pct > 0.15:
        warns.append(_( f"关联钱包 {len(related)} 个持仓 {pct(related_pct):.1f}%",
                        f"Linked wallets ({len(related)}) hold {pct(related_pct):.1f}%"))

if unassessable and not dangers:
    # Dev 马甲那条（唯一不依赖百分比的 danger）若成立就照常给 🔴；否则不下结论。
    # 退化 / 空数据时"没发现问题"和"评级正常"是两件事，不能让它落到 ✅ 正常参与。
    rating_em, rating_text = "⚪", _("无法评估", "Cannot Assess")
elif dangers:
    rating_em, rating_text = "🔴", _("不建议买", "Not Recommended")
elif len(warns) >= 2:
    rating_em, rating_text = "⚠️", _("谨慎参与", "Caution")
elif len(warns) == 1:
    rating_em, rating_text = "🟡", _("可轻仓",   "Light Position")
else:
    rating_em, rating_text = "✅", _("正常参与", "Normal")

goods = []
if burn_pct > 0.05:
    goods.append(_( f"销毁 {pct(burn_pct):.1f}% 永久锁仓，流通减少",
                    f"Burned {pct(burn_pct):.1f}% permanently — reduced supply"))
if whales:
    buying_w = [h for h in whales if is_buying_only(h)]
    if buying_w:
        goods.append(_( f"鲸鱼 {len(buying_w)} 个持续买入，尚未出货",
                        f"{len(buying_w)} whale(s) still accumulating, not sold"))
if kol:
    # 钱包个数是实打实的；退化时占比是噪声，就只报个数
    goods.append(_( f"KOL {len(kol)} 个在场" + ("" if float_degenerate else f"（{pct(kol_pct):.2f}%）"),
                    f"{len(kol)} KOL(s) holding" + ("" if float_degenerate else f" ({pct(kol_pct):.2f}%)")))
if diamond_pct > 0.5 and not float_degenerate:
    goods.append(_( f"钻石手持仓 {pct(diamond_pct):.1f}%，筹码稳定",
                    f"Diamond hands hold {pct(diamond_pct):.1f}% — stable chips"))

exit_signals = []
if rats:
    exit_signals.append(_("老鼠仓钱包出现卖出操作", "Rat trader wallets start selling"))
if dev_holding:
    exit_signals.append(_("Dev 钱包开始出货", "Dev wallets start dumping"))
if airdrop_pct>0.2:
    exit_signals.append(_("空降大户出现集中卖出", "Airdrop whales start concentrated selling"))
if not exit_signals:
    exit_signals = [_("Top5 大户出现集中出货", "Top 5 holders start concentrated selling"),
                    _("价格跌破建仓均价支撑", "Price breaks below average entry cost")]
exit_signals = exit_signals[:3]

top5_holders = sorted(normal, key=lambda h: -h['amount_percentage'])[:5]

def top5_pressure(h):
    avg_cost = h.get('avg_cost') or 0
    up_pnl   = h.get('unrealized_pnl') or 0
    up_usd   = h.get('unrealized_profit') or 0
    buy0     = h.get('buy_tx_count_cur',0)==0
    roles    = wallet_roles(h)
    if buy0 and not roles: roles.append(_('空降', 'Airdrop'))
    role_str   = "["+"·".join(roles)+"]  " if roles else ""
    display_id = (h.get('twitter_name') or '') or addr_short(h['address'])
    # 建仓MC = 总供应 × 建仓均价。文档把它和浮盈并列为抛压信号，所以四个有成本的分支
    # 都要给 —— 只报"均价 $0.0000"读不出这是多大的盘子进的。
    entry_mc = total_supply * avg_cost
    cost_str = (f"{_('建仓MC', 'Entry MC')} {usd(entry_mc)}"
                f"（{_('均价', 'avg')} {price_str(avg_cost)}）" if ZH else
                f"Entry MC {usd(entry_mc)} (avg {price_str(avg_cost)})")
    if buy0 or avg_cost==0:
        cost_str = _("零成本（转账获得）", "Zero cost (received via transfer)")
        pnl_str  = "—"
        lv       = "⚠️ " + _("高", "High")
        note     = _("零成本，随时可出货", "Zero cost — can dump anytime")
    elif up_pnl>1.0:
        mult     = up_pnl+1
        pnl_str  = f"+{up_pnl*100:.0f}% ({mult:.1f}x)  {usd(up_usd)}"
        lv       = "⚠️ " + _("高", "High")
        note     = _(f"现 MC {usd(cur_mc)}，浮盈 {mult:.1f}x，获利了结压力强",
                     f"Now MC {usd(cur_mc)}, {mult:.1f}x gain — strong take-profit pressure")
    elif up_pnl>0.1:
        pnl_str  = f"+{up_pnl*100:.0f}%  {usd(up_usd)}"
        lv       = "🟡 " + _("中", "Med")
        note     = _("小幅浮盈，出货意愿一般", "Moderate gain — mild sell pressure")
    elif up_pnl>=-0.1:
        pnl_str  = f"{up_pnl*100:+.0f}%  {usd(up_usd)}" if abs(up_usd)>=1 else _("接近成本", "Near cost")
        lv       = "🟢 " + _("低", "Low")
        note     = _("接近成本，短期抛压有限", "Near break-even — limited short-term pressure")
    else:
        pnl_str  = f"{up_pnl*100:.0f}%  {usd(up_usd)}"
        lv       = "🟢 " + _("低", "Low")
        note     = _("套牢中，短期不易割肉", "Underwater — unlikely to sell soon")
    beh     = wallet_behavior(h)
    beh_str = ("  " + _("行为", "behavior") + ": " + beh) if beh else ""
    return role_str, display_id, cost_str, pnl_str, lv, note, beh_str, holding_status(h)

title = _("Holder 筹码分析", "Holder Chip Analysis")
print(f"┌{'─'*56}┐")
print(f"│{('  '+title):^56}│")
print(f"│{('  '+TOKEN_ADDR[:10]+'...'+TOKEN_ADDR[-4:]+'  ·  Top100  ·  '+CHAIN.upper()):^56}│")
print(f"│{('  MC '+usd(cur_mc)):^56}│")
print(f"└{'─'*56}┘")
print()

if no_holders:
    # 空数据也必须在所有 0.00% 之前说清楚，否则整份报告读起来像"干净得没有任何风险"
    print(f"  ⚠️  {_('上游未返回任何持仓地址 —— 筹码结构无法评估', 'Upstream returned no holder addresses — chip structure not assessable')}")
    print(_( "      下方所有占比与计数都是空集的渲染结果，不是“该项为 0”；评级已置为“无法评估”。",
             "      Every percentage and count below renders an empty set, not a measured zero. Rating is set to “Cannot Assess”."))
    print(_( "      常见原因：代币已无活跃持仓、或上游索引里已不再收录该盘。可稍后重试确认。",
             "      Usual causes: the token has no active holders left, or upstream no longer indexes it. Retry later to confirm."))
    print()

if float_degenerate:
    # 退化时这行必须在所有百分比之前出现，否则读者会先把 100% 当成集中度结论。
    # 同时给出绝对值（代币数 + 美元），这是此刻唯一有意义的量级。
    _fl_tok = total_supply * max(float_raw, 0)
    _fl_usd = _fl_tok * cur_price
    _fl_usd_s = "<$1" if 0 < _fl_usd < 1 else usd(_fl_usd)
    print(f"  ⚠️  {_('流通盘退化 —— 筹码结构此刻无法评估', 'Degenerate float — chip structure not assessable right now')}")
    print(_( f"      DEX 池 {pct(dex_pct):.1f}% + 销毁 {pct(burn_pct):.1f}% 占掉几乎全部供应，可流通部分只剩 {pct_s(float_raw)}",
             f"      DEX {pct(dex_pct):.1f}% + burn {pct(burn_pct):.1f}% hold nearly all supply; only {pct_s(float_raw)} is tradeable"))
    print(_( f"      （通常是还没迁移的 launchpad 盘）实际可流通约 {fmt_amt(_fl_tok)} 个代币 ≈ {_fl_usd_s}",
             f"      (typically a launchpad token pre-migration) tradeable ≈ {fmt_amt(_fl_tok)} tokens ≈ {_fl_usd_s}"))
    print(_( "      下方“占流通盘”的百分比分母趋零，会把尘埃钱包放大成两位数甚至 100%，",
             "      Float percentages below divide by a near-zero denominator, inflating dust wallets to double digits or 100%,"))
    print(_( "      不能当作集中度结论；评级已置为“无法评估”，颜色标记一律显示 ⚪。",
             "      so they are not concentration findings. Rating is set to “Cannot Assess” and flags show ⚪."))
    print()

sec1 = _("🚨 砸盘风险", "🚨 Dump Risk")
print(f"━━  {sec1}  {'━'*(54-len(sec1))}")
print()
c10f = pf("🔴" if top10>0.6 else ("🟡" if top10>0.4 else "🟢"))
c20f = pf("🔴" if top20>0.75 else ("🟡" if top20>0.55 else "🟢"))
print(f"  {_('集中度（占流通盘，已剔除 LP 与销毁）', 'Concentration (of tradeable float, LP + burn excluded)')}")
print(f"    Top10 {fpct(top10, 1)} {c10f}   Top20 {fpct(top20, 1)} {c20f}")
print()
if burn:
    print(f"  🔥 {_('销毁地址', 'Burn addr')}   {pct(burn_pct):.2f}%  ✅ {_('永久锁仓，无法流通', 'Permanently locked, non-circulating')}")
    print()
airf = pf("🔴" if airdrop_pct>0.25 else ("🟡" if airdrop_pct>0.1 else "🟢"))
print(f"  {_('空降筹码（从未买入、靠转账获得）', 'Airdrop (never bought, received via transfer)')}   {len(airdrop)} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(airdrop_pct)}  {airf}")
print()
riskf = pf("🔴" if risk_pct>0.35 else ("🟡" if risk_pct>0.15 else "🟢"))
print(f"  {_('风险钱包', 'Risk wallets')}   {_('合计', 'total')} {len(risk_all)} {_('个', '')}   {_('持仓', 'hold')} {fpct(risk_pct)}  {riskf}")
for label, group, flag in RISK_GROUPS:
    if group:
        gp = fpct(fs(group))
        print(f"    · {label:10s}  {len(group):2d} {_('个', '')}   {_('持仓', 'hold')} {gp}  {flag}")
if not any(g for _lb, g, _fl in RISK_GROUPS):
    # 空持仓表时"未发现"只是没数据可查，不能打成 🟢
    if no_holders:
        print(f"    · {_('没有钱包可供检查', 'No wallets available to check')}  ⚪")
    else:
        print(f"    · {_('未发现风险标签钱包', 'No risk-tagged wallets found')}  🟢")
if risk_overlap > 0:
    # 分类明细相加会大于"合计" —— 说明差额来自多标签钱包，而不是算错了
    print(f"    · {_(f'合计已去重（{risk_overlap} 个钱包带多个风险标签）', f'Total is deduped ({risk_overlap} wallet(s) carry multiple risk tags)')}")
print()
if no_holders:
    # 级联最后一档是"🟢 没发现明显砸盘风险"。空持仓表会一路落到那里，
    # 把"没有数据"渲染成"没有风险" —— 必须在入口就拦掉。
    sdp_summary = _( "⚪ 没有任何持仓数据，砸盘风险无法判断（不是“无风险”）",
                     "⚪ No holder data at all — dump risk cannot be judged (this is not \"no risk\")")
elif float_degenerate:
    # 这段级联里每一条判据都是流通盘占比，退化时全是噪声 —— 只能重复"没法评"
    sdp_summary = _( f"⚪ 流通盘只剩 {pct_s(float_raw)}，上面的占比都是除零放大的结果，砸盘风险无法判断",
                     f"⚪ Only {pct_s(float_raw)} of supply is tradeable — the percentages above are divide-by-zero artifacts; dump risk cannot be judged")
elif dangers:
    sdp_summary = f"🔴 {dangers[0]}"
elif rats_pct > 0.03:
    sdp_summary = _( f"🔴 老鼠仓持仓 {pct(rats_pct):.1f}%，零成本拿的，随时可以无损砸盘",
                     f"🔴 Rat traders hold {pct(rats_pct):.1f}% at zero cost — can dump with no loss anytime")
elif top10 > 0.5:
    sdp_summary = _( f"🟡 Top10 持仓 {pct(top10):.1f}%，筹码过于集中，大户一旦出货冲击很大",
                     f"🟡 Top10 hold {pct(top10):.1f}% — highly concentrated, big impact if they sell")
elif bundler_pct_val > 0.3:
    sdp_summary = _( f"🟡 捆绑钱包持仓 {pct(bundler_pct_val):.1f}%，这批是开盘机器人扫货，出货时可能集中砸盘",
                     f"🟡 Bundlers hold {pct(bundler_pct_val):.1f}% — bot-swept at open, may dump together")
elif airdrop_pct > 0.2:
    sdp_summary = _( f"🟡 空降筹码 {pct(airdrop_pct):.1f}%，这些人零成本拿到币，随时可能出货",
                     f"🟡 Airdrop supply {pct(airdrop_pct):.1f}% at zero cost — may sell anytime")
elif sniper_pct_val > 0.15:
    sdp_summary = _( f"🟡 狙击者持仓 {pct(sniper_pct_val):.1f}%，开盘低价进的，浮盈高、随时可套现",
                     f"🟡 Snipers hold {pct(sniper_pct_val):.1f}% at launch price — high unrealized gain, may cash out")
elif risk_pct > 0.15:
    sdp_summary = _( f"🟡 风险钱包合计持仓 {pct(risk_pct):.1f}%，需要留意动向",
                     f"🟡 Risk wallets total {pct(risk_pct):.1f}% — watch their moves")
elif burn_pct > 0.1:
    sdp_summary = _( f"🟢 销毁了 {pct(burn_pct):.1f}%，流通筹码少，LP 也锁住了，相对干净",
                     f"🟢 {pct(burn_pct):.1f}% burned — reduced supply, LP locked, relatively clean")
else:
    sdp_summary = _("🟢 集中度正常，没发现明显的砸盘风险",
                    "🟢 Normal concentration, no obvious dump risk detected")
print(f"  → {_('小结', 'Summary')}{_('：', ': ')}{sdp_summary}")
print()
print(f"  {_('Top5 持仓钱包抛压分析', 'Top 5 Holder Sell Pressure')}")
print(f"  {_('浮盈越高 / 建仓MC越低 → 获利了结压力越强', 'Higher unrealized gain / lower entry MC → stronger sell pressure')}")
print()
for i, h in enumerate(top5_holders, 1):
    role_str, display_id, cost_str, pnl_str, lv, note, beh_str, st = top5_pressure(h)
    hp = fpct(f1(h['amount_percentage']))
    print(f"    {i}. {role_str}{display_id}")
    print(f"       {_('持仓', 'hold')} {hp}  {cost_str}  {_('盈亏', 'pnl')} {pnl_str}")
    print(f"       {_('抛压', 'pressure')} {lv} — {note}")
    print(f"       {_('状态', 'status')} {st}{beh_str}")
    print()

sec2 = _("👨‍💻 Dev 钱包", "👨‍💻 Dev Wallets")
print(f"━━  {sec2}  {'━'*(54-len(sec2))}")
print()
# 一个 dev 都没查到 ≠ dev 已清仓 —— 前者是查不到，后者是查到了且为零
if not devs:
    dev_status = _("— 未查到 dev 钱包", "— no dev wallets found")
elif not dev_holding:
    dev_status = _("✅ 全部余额归零", "✅ All cleared")
else:
    dev_status = _(f"⚠️ 仍有 {len(dev_holding)} 个持仓中", f"⚠️ {len(dev_holding)} still holding")
if sub_devs:
    print(f"  {_('共', 'Total')} {len(devs)} {_('个钱包（1 主号 + ', 'wallets (1 main + ')}{len(sub_devs)}{_(' 小号）', ' sub)')}   {dev_status}")
else:
    print(f"  {_('共', 'Total')} {len(devs)} {_('个钱包', 'wallets')}   {dev_status}")
print(f"  {_('Dev 合计已实现利润', 'Dev total realized profit')}  {usd(dev_realized)}")
print()
if creator:
    c_sell_v   = creator.get('sell_volume_cur') or 0
    tf_out     = creator.get('history_transfer_out_amount') or 0
    tf_val     = creator.get('history_transfer_out_income') or 0
    sell_amt   = creator.get('sell_amount_cur') or 0
    hold_pct_c = f1(creator.get('amount_percentage') or 0)
    c_status   = (_("余额归零", "Balance zero") if (creator.get('balance') or 0)<1
                  else _(f"⚠️ 持仓 {fpct(hold_pct_c)}", f"⚠️ Holding {fpct(hold_pct_c)}"))
    print(f"  {_('主号 (Creator)', 'Main (Creator)')}   {addr_short(creator['address'])}")
    parts = [c_status]
    if sell_amt>0:
        parts.append(_(f"卖出 {fmt_amt(sell_amt)} 个（{usd(c_sell_v)}）",
                       f"Sold {fmt_amt(sell_amt)} ({usd(c_sell_v)})"))
    if tf_out>0:
        to_out  = creator.get('token_transfer_out') or {}
        to_addr = to_out.get('address') or ''
        if to_addr and to_addr in top100_map:
            parts.append(_(f"转出 {fmt_amt(tf_out)} 个至 Top100 内部钱包（估值 {usd(tf_val)}）",
                           f"Transferred {fmt_amt(tf_out)} to Top100 internal wallet (est. {usd(tf_val)})"))
        else:
            parts.append(_(f"转出 {fmt_amt(tf_out)} 个至外部地址（估值 {usd(tf_val)}）",
                           f"Transferred {fmt_amt(tf_out)} to external addr (est. {usd(tf_val)})"))
    print(f"  {'   '.join(parts)}")
    to_out  = creator.get('token_transfer_out') or {}
    to_addr = to_out.get('address') or ''
    if to_addr and to_addr in top100_map:
        target  = top100_map[to_addr]
        t_mtags = [t for t in (target.get('maker_token_tags') or []) if t not in ('top_holder','transfer_in')]
        print(f"\n  ⚠️ {_('转出筹码仍在 Top100（换马甲继续持有）：', 'Transferred chips still in Top100 (sock puppet):')}")
        print(f"     {addr_short(to_addr)}  {_('持仓', 'hold')} {fpct(f1(target.get('amount_percentage') or 0))}  {_('标签', 'tags')}: {' '.join(t_mtags) or _('无','none')}")
    elif (creator.get('balance') or 0)<1 and tf_out==0:
        print(f"  ✅ {_('已完全卖出，无异常转账记录', 'Fully sold, no abnormal transfers')}")
    print()
    if to_addr and to_addr in top100_map:
        dev_summary = _("🔴 Dev 换马甲持仓，这个很危险，随时可以砸盘",
                        "🔴 Dev using sock puppet — very dangerous, can dump anytime")
    elif dev_holding:
        dev_summary = _("🟡 Dev 还没出完，有出货风险，关注钱包动向",
                        "🟡 Dev hasn't fully exited — dump risk, watch wallet activity")
    elif dev_realized > 50000:
        dev_summary = _(f"🟡 Dev 已套现 {usd(dev_realized)}，虽然出完了但赚了不少",
                        f"🟡 Dev cashed out {usd(dev_realized)} — exited but made significant profit")
    else:
        dev_summary = _("🟢 Dev 已清仓，没有持仓压力",
                        "🟢 Dev fully exited — no holding pressure")
    print(f"  → {_('小结', 'Summary')}{_('：', ': ')}{dev_summary}")
    print()
    if created_data:
        all_tokens = created_data.get('tokens') or []
        total_cnt  = (created_data.get('inner_count') or 0)+(created_data.get('open_count') or 0)
        mig_cnt    = created_data.get('open_count') or 0
        nonmig_cnt = created_data.get('inner_count') or 0
        print(f"  {_('历史发币', 'Token history')}   {_('共', 'total')} {total_cnt}   {_('已迁移', 'migrated')} {mig_cnt}   {_('未迁移', 'unmigrated')} {nonmig_cnt}")
        top3_mc = sorted(all_tokens, key=lambda t: float(t.get('market_cap') or 0), reverse=True)[:3]
        if top3_mc:
            print(f"  {_('当前市值 Top3', 'Current MC Top3')}:")
            for i, t in enumerate(top3_mc, 1):
                mig_label = _('已迁移', 'migrated') if t.get('is_open') else _('未迁移', 'unmigrated')
                print(f"    {i}. {t.get('symbol','?')}  {usd(float(t.get('market_cap') or 0))}  [{mig_label}]")
        ath_info = created_data.get('creator_ath_info') or {}
        if ath_info and ath_info.get('ath_mc'):
            ath_mc     = float(ath_info.get('ath_mc') or 0)
            is_curr    = ath_info.get('ath_token','').lower()==TOKEN_ADDR.lower()
            curr_label = _('（本币）', ' (this token)') if is_curr else ''
            # 历史最高市值低于当前市值在数学上不可能（本币此刻的市值本身就是它的历史候选），
            # 说明上游 ath 字段还没跟上这轮拉升 —— 实测 token info 的 ath_price 等于
            # price_24h，一个 24 小时涨了上百倍的币，ATH 就会停在一天前的价位。
            # 照原样打印会被当成真实峰值，进而拿去算"距离 ATH 还有多少空间"。留 5% 容差，
            # 因为 cur_mc 自己是 median(usd_value/balance) × median(supply) 的估算值。
            stale_ath = ath_mc > 0 and cur_mc > 0 and ath_mc < cur_mc * 0.95
            ath_note  = "" if not stale_ath else _(
                f"  ⚠️ 低于当前市值 {usd(cur_mc)}，上游 ATH 数据滞后，不可作为峰值参考",
                f"  ⚠️ below current MC {usd(cur_mc)} — upstream ATH is stale, not a usable peak")
            print(f"  {_('历史最高市值', 'All-time high MC')}: {ath_info.get('token_name','')}({ath_info.get('token_symbol','?')}){curr_label}  ATH {usd(ath_mc)}{ath_note}")
        print()

sec3 = _("🔗 关联资金", "🔗 Related Funds")
print(f"━━  {sec3}  {'━'*(54-len(sec3))}")
print()
print(f"  {_('多个钱包来自同一资金来源地址，或在极短时间内同步注资', 'Multiple wallets from same funding source or funded in tight time windows')}")
print()
if related:
    relf = pf("🔴" if related_pct>0.25 else ("🟡" if related_pct>0.1 else "🟢"))
    # 秒级批量注资本身就是异常信号，不该因为占比小而在标题上显示为绿。判据是钱包数与
    # 时间跨度，不含流通盘占比，所以流通盘退化时（relf 为 ⚪）这条升级依然有效。
    if tight_groups and relf in ("🟢", "⚪"): relf = "🟡"
    print(f"  {_('涉及', 'Involves')} {len(related)} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(related_pct)}   {usd(related_usd)}  {relf}")
    print()
    print(f"  ├─ {_('强关联（同一来源 + 时间集中或金额一致）', 'Strong (same source + tight timing or uniform amounts)')}   {len(same_src_groups)} {_('组', 'groups')} / {same_src_wallets} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(same_src_pct)}")
    if same_src_groups:
        fa, ws = same_src_groups[0]
        native_in = sum(float(_tr(w, 'amount', 0) or 0) for w in ws)
        print(f"  │   {_('最大组', 'Largest group')}: {len(ws)} {_('个钱包', 'wallets')}   {_('来源', 'from')} {addr_short(fa)}   {_('合计注资', 'total funded')} {native_in:.4f} {NSYM}")
    if weak_src_groups:
        # 只共用转入地址、时间金额都不一致 —— 交易所热钱包和团伙长得一样，不能混进合计
        print(f"  ├─ {_('弱关联（仅共用转入地址，可能是交易所热钱包）', 'Weak (shared source only, may be a CEX hot wallet)')}   {len(weak_src_groups)} {_('组', 'groups')} / {weak_src_wallets} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(weak_src_pct)}   {_('不计入上方合计', 'excluded from total above')}")
    print(f"  │")
    if win_groups:
        win_total = sum(len(v) for v in win_groups)
        if tight_groups:
            print(f"  └─ {_(f'同步注资（{WINDOW//60}min 内集中入场）', f'Coordinated funding (within {WINDOW//60}min)')}   {win_total} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(win_pct)}  🔴")
            print(f"      🔴 {_(f'其中 {tight_wallets} 个钱包在 {TIGHT} 秒内被同步注资，基本可判定脚本批量打款', f'{tight_wallets} wallet(s) funded within {TIGHT}s — almost certainly scripted batch funding')}")
        elif win_total>=3:
            print(f"  └─ {_(f'同步注资（{WINDOW//60}min 内集中入场）', f'Coordinated funding (within {WINDOW//60}min)')}   {win_total} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(win_pct)}  ⚠️")
        else:
            print(f"  └─ {_(f'同步注资（{WINDOW//60}min 内集中入场）', f'Coordinated funding (within {WINDOW//60}min)')}   {win_total} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(win_pct)}")
        # 只有一个批次时，明细就是上面那行，不重复打印
        if len(win_groups) > 1:
            v = win_groups[0]
            print(f"      {_('最大批次', 'Largest batch')}: {len(v)} {_('个钱包', 'wallets')}   {_('合计持仓', 'total hold')} {fpct(fs(v), 3)}   {_('时间跨度', 'span')} {_span(v)}s")
        else:
            print(f"      {_('时间跨度', 'Span')} {_span(win_groups[0])}s")
    else:
        print(f"  └─ {_('未发现同步集中注资', 'No coordinated funding detected')}")
else:
    if no_holders:
        print(f"  {_('没有钱包可供检查资金来源', 'No wallets available to trace funding')}  ⚪")
    else:
        print(f"  {_('未发现明显关联资金', 'No significant linked funds detected')}  🟢")
    if weak_src_groups:
        print(f"  ({_(f'{weak_src_wallets} 个钱包共用转入地址，但时间和金额都不一致，判为交易所出金而非团伙', f'{weak_src_wallets} wallets share a funding address but differ in timing and amount — read as CEX withdrawals, not a gang')})")
print()

sec4 = _("🧠 优质信号", "🧠 Quality Signals")
print(f"━━  {sec4}  {'━'*(54-len(sec4))}")
print()
# ✅/— 只表示"这类钱包在不在场"，是个数派生的、不经过 float_share，退化时依然成立，
# 所以不走 pf()；被中和掉的只是占比数字本身。
print(f"  {_('聪明钱', 'Smart Money')}   {len(smart):2d}   {_('持仓', 'hold')} {fpct(smart_pct)}  {'✅' if smart else '—'}")
if smart: print(f"  {_('近期动向', 'Recent')}:  {trend_str(smart)}")
print(f"  KOL          {len(kol):2d}   {_('持仓', 'hold')} {fpct(kol_pct)}  {'✅' if kol else '—'}")
if kol:
    for h in kol:
        name = h.get('twitter_name') or h.get('name') or addr_short(h['address'])
        print(f"    · {name}  {_('持仓', 'hold')} {fpct(f1(h['amount_percentage']))}  {holding_status(h)}  {_('买/卖', 'buy/sell')}: {h.get('buy_tx_count_cur',0)}/{h.get('sell_tx_count_cur',0)}")
print(f"  {_('鲸鱼', 'Whale')}        {len(whales):2d}   {_('持仓', 'hold')} {fpct(whale_pct)}  {'✅' if whales else '—'}")
if whales: print(f"  {_('近期动向', 'Recent')}:  {trend_str(whales)}")
print()
df = pf("✅" if diamond_pct>0.6 else ("🟡" if diamond_pct>0.35 else "⚠️"))
print(f"  {_('钻石手（买入过且从未卖出）', 'Diamond hands (bought & never sold)')}   {len(diamond):2d}   {_('持仓', 'hold')} {fpct(diamond_pct, 1)}  {df}")
if idle_airdrop:
    # 单独一行，避免读者把这批零成本筹码当成"扛住了没卖"的钻石手
    print(f"  {_('空降未动（从未买入也未卖出）', 'Idle airdrop (never bought, never sold)')}   {len(idle_airdrop):2d}   {_('持仓', 'hold')} {fpct(idle_airdrop_pct, 1)}   {_('零成本，不计入钻石手', 'zero cost — not counted as diamond hands')}")
print(f"  {_('部分卖出(<50%)', 'Partial sell (<50%)')}  {len(partial):2d}   {_('大量卖出(≥50%)', 'Heavy sell (≥50%)')}  {len(heavy_sell):2d}")
if sig_count == 0:
    sig_summary = _("🟡 没有聪明钱和KOL，这个币没什么外部背书",
                    "🟡 No smart money or KOL — no external endorsement")
elif kol_selling and len(kol_selling) >= max(1, len(kol)//2+1):
    sig_summary = _(f"🟡 {len(kol)}个KOL里有{len(kol_selling)}个已开始卖——跟进要小心",
                    f"🟡 {len(kol_selling)}/{len(kol)} KOL(s) already selling — be careful following")
elif smart_selling and len(smart_selling) >= max(1, len(smart)//2+1):
    sig_summary = _(f"🟡 聪明钱里有{len(smart_selling)}个已经在出货，信号在减弱",
                    f"🟡 {len(smart_selling)} smart money wallet(s) selling — signal weakening")
elif smart_holding:
    sig_summary = _(f"🟢 {len(smart_holding)}个聪明钱一直持仓没卖，这类人通常提前判断，信号较强",
                    f"🟢 {len(smart_holding)} smart money wallet(s) holding firm — usually early movers, strong signal")
elif kol_holding:
    sig_summary = _(f"🟢 {len(kol_holding)}个KOL全程持仓未卖，参考价值保留",
                    f"🟢 {len(kol_holding)} KOL(s) fully holding — signal still valid")
else:
    sig_summary = _("🟢 鲸鱼在场，有大资金背书",
                    "🟢 Whales present — backed by large capital")
print(f"  → {_('小结', 'Summary')}{_('：', ': ')}{sig_summary}")
print()

sec5 = _("📈 入场成本分析", "📈 Entry Cost Analysis")
print(f"━━  {sec5}  {'━'*(54-len(sec5))}")
print()
print(f"  {_('当前 MC', 'Current MC')} {usd(cur_mc)}")
print()
time_clusters = defaultdict(list)
for h in normal:
    sh = h.get('start_holding_at') or 0
    if sh<=0: continue
    time_clusters[(sh-token_launch)//86400].append(h)
sig_clusters = sorted([(age,ws) for age,ws in time_clusters.items() if len(ws)>=2],
                      key=lambda x: -sum(h['amount_percentage'] for h in x[1]))[:4]

for rank, (age, ws) in enumerate(sig_clusters, 1):
    entry_ts    = token_launch + age*86400
    label       = age_label(entry_ts)
    total_hp    = fs(ws)
    costed      = [h for h in ws if (h.get('avg_cost') or 0)>0]
    selling_out = [h for h in ws if is_distributing(h)]
    still_hold  = [h for h in ws if (h.get('balance') or 0)>=1]
    if costed:
        avg_entry = sum(total_supply*h['avg_cost'] for h in costed)/len(costed)
        roi       = (cur_mc-avg_entry)/avg_entry*100 if avg_entry>0 else 0
        mc_str    = _(f"建仓MC {usd(avg_entry)} → 现 {usd(cur_mc)} ({roi:+.0f}%)",
                      f"Entry MC {usd(avg_entry)} → now {usd(cur_mc)} ({roi:+.0f}%)")
    else:
        avg_entry=0; roi=0
        mc_str    = _("建仓MC 未知（转账获得）", "Entry MC unknown (received via transfer)")
    sell_ratio = len(selling_out)/len(still_hold) if still_hold else 0
    if roi>500 and sell_ratio>0.15:
        risk_flag = "🔴"
        conclusion = _(f"这批人建仓时才 {usd(avg_entry)}，涨了 {roi:.0f}%，现在有 {len(selling_out)} 个在卖出套现——追入容易接到他们的盘",
                       f"Entry at {usd(avg_entry)}, up {roi:.0f}%, {len(selling_out)} already selling — buying now means catching their exits")
    elif roi>200 and sell_ratio>0.1:
        risk_flag = "🟡"
        conclusion = _(f"涨了 {roi:.0f}%，有 {len(selling_out)} 个开始出货，但多数还没动——注意大户下一步动向",
                       f"Up {roi:.0f}%, {len(selling_out)} starting to sell but most still holding — watch whale next moves")
    elif roi>0:
        risk_flag = "🟢"
        conclusion = _(f"涨了 {roi:.0f}%，出货的人不多，短期卖压不大",
                       f"Up {roi:.0f}%, few selling — limited short-term pressure")
    else:
        risk_flag = "🟢"
        conclusion = _(f"这批人目前亏着呢（{roi:.0f}%），不到割肉的程度，短期不太会卖",
                       f"Currently down {roi:.0f}% — unlikely to sell at a loss short-term")
    batch_label = _('批次', 'Batch')
    selling_cnt  = len([h for h in ws if is_selling(h)])
    holding_cnt  = len([h for h in ws if is_buying_only(h)])
    sell_str     = f"  🚨 {_('出货中','selling')} {selling_cnt}" if selling_cnt else ""
    hold_str     = f"  📈 {_('加仓中','accumulating')} {holding_cnt}" if holding_cnt else ""
    # 批次占比同样以流通盘为分母 —— 退化时会把一个尘埃批次打成 "hold 100.00% 🟢"，
    # 一行之内同时给出"全部筹码"和"没风险"两个错误结论。数字和旗标都要中和。
    print(f"  {batch_label}{rank}{_('（', '(')}{label}{_('）', ')')}  {len(ws)} {_('个钱包', 'wallets')}  {_('持仓', 'hold')} {fpct(total_hp)}  {pf(risk_flag)}{sell_str}{hold_str}")
    print(f"       {mc_str}")
    print(f"       ➤ {conclusion}")
    print()

sec6 = _("💰 持仓者购买力", "💰 Holder Buying Power")
print(f"━━  {sec6}  {'━'*(54-len(sec6))}")
print()
if not HAS_NATIVE:
    print(f"  {_('衡量现有持仓者还有多少子弹可以加仓', 'How much ammo holders have left to add')}")
    print()
    print(f"  ⚠️  {_(f'{CHAIN} 链的原生代币精度未确认，native_balance 无法换算 —— 本节不做评估', f'Native decimals unconfirmed for {CHAIN}; native_balance cannot be converted — section not assessed')}")
    print()
else:
    if HAS_PRICE:
        bp_str = _(f"{usd(total_buying_power)}（{fmt_native(total_buying_power_native)} @ {price_str(NATIVE_PRICE)}）",
                   f"{usd(total_buying_power)} ({fmt_native(total_buying_power_native)} @ {price_str(NATIVE_PRICE)})")
    else:
        bp_str = fmt_native(total_buying_power_native)
    print(f"  {_('衡量现有持仓者还有多少子弹可以加仓', 'How much ammo holders have left to add')}   {_('合计可用余额', 'Total balance')} {bp_str}")
    print()
if zero_wallets:
    print(f"  ⚫ {_('零余额', 'Zero balance')}     {len(zero_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(zero_pct_val)}   —    → {_('无加仓能力，可能是分仓小号', 'No buying power, likely sub-wallets')}")
if HAS_PRICE:
    if low_wallets:
        low_total = sum(native_usd(h) for h in low_wallets)
        print(f"  🟡 {_('低（<$200）', 'Low (<$200)')}   {len(low_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(low_pct_val)}   {usd(low_total)}")
    if mid_wallets:
        mid_total = sum(native_usd(h) for h in mid_wallets)
        print(f"  🟠 {_('中（$200~$1200）', 'Mid ($200~$1200)')}  {len(mid_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(mid_pct_val)}   {usd(mid_total)}")
    if high_wallets:
        print(f"  🔴 {_('高（$1200+）', 'High ($1200+)')}  {len(high_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(high_pct_val)}   {usd(high_total)}   → {_('可随时加仓', 'can add anytime')}")
elif high_wallets:
    # 拿不到原生代币价格，只按原生数量分档，不编造美元金额
    print(f"  🟢 {_('有余额', 'Has balance')}     {len(high_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {fpct(high_pct_val)}   {fmt_native(high_native)}")
    print(f"     ({_(f'{CHAIN} 链拿不到 {NSYM} 价格，仅显示原生数量', f'No {NSYM} price for {CHAIN}, native amount only')})")
print()
if high_wallets and HAS_PRICE:
    print(f"  ➤ {_('高余额钱包', 'High-balance wallets')} {len(high_wallets)} {_('个持仓', 'holding')} {fpct(high_pct_val, 1)}{_('，', ', ')}{_('合计', 'total')} {usd(high_total)} {_('可随时加仓', 'ready to add')}")
if zero_wallets and zero_pct_val > 0.1:
    print(f"  ➤ {len(zero_wallets)} {_('个钱包零余额（持仓 ', 'wallets with zero balance (hold ')}{fpct(zero_pct_val, 1)}{_('）', ')')}, {_('无加仓能力，可能是分仓小号', 'no buying power, likely sub-wallets')}")
print()

sec7 = _("📊 筹码结构", "📊 Chip Structure")
print(f"━━  {sec7}  {'━'*(54-len(sec7))}")
print()
total_n = len(normal)
if total_n > 0:
    # 钱包个数答"多数人赚没赚"，流通盘占比答"赚钱的筹码有多重" —— 抛压看后者
    print(f"  {_('盈利', 'Profit')} {len(profit_w)}   ({len(profit_w)/total_n*100:.0f}% {_('钱包', 'wallets')} / {fpct(profit_pct, 1)} {_('流通盘', 'float')})")
    print(f"  {_('亏损', 'Loss')} {len(loss_w)}   ({len(loss_w)/total_n*100:.0f}% {_('钱包', 'wallets')} / {fpct(loss_pct, 1)} {_('流通盘', 'float')})   {_('持平', 'Break-even')} {total_n-len(profit_w)-len(loss_w)}")
tf_flag = "⚠️" if len(trapped)>30 else ""
print(f"  {_('套牢盘（浮亏>20%）', 'Underwater (>20% loss)')}   {len(trapped)}   {_('持仓', 'hold')} {fpct(trapped_pct)}  {tf_flag}")
print(f"  {_('平均持仓时长', 'Avg hold duration')}   {avg_hold_days:.1f} {_('天', 'days')}")
print()

sec8 = _("🤖 AI 建议", "🤖 AI Advice")
print(f"━━  {sec8}  {'━'*(54-len(sec8))}")
print()
print(f"  {rating_em} {rating_text}")
print()
if dangers:
    print(f"  {_('核心风险', 'Core Risks')}:")
    for d in dangers: print(f"    · {d}")
if warns:
    print(f"  {_('注意信号', 'Warnings')}:")
    for w in warns:   print(f"    · {w}")
if goods:
    print(f"  {_('积极因素', 'Positives')}:")
    for g in goods:   print(f"    · {g}")
# 三个桶互斥、相加为 100%，读者能看出缺口是"有前科"还是"来源未知"造成的
if no_holders:
    # 三个桶全是 0.0% 时打印它们，等于宣称"筹码里既没有风险标签也没有空降"
    print(f"\n  {_('筹码质量', 'Chip quality')} ⚪   "
          f"{_('没有观测到任何钱包，无法计算', 'no wallets observed — cannot compute')}")
else:
    # 三个桶的分母是 normal_pct（总供应基准），不受流通盘退化影响，所以构成照常打印；
    # 但退化盘里被观测到的筹码本身只有尘埃级，对着尘埃下 🔴/🟢 的结论没有意义 ——
    # 评级已经是"无法评估"，这里再亮一个红灯只会自相矛盾。故只中和旗标，并注明筹码体量。
    _qf_disp = pf(qf)
    _qf_note = "" if not float_degenerate else _(
        f"，仅占总供应 {pct_s(normal_pct)}", f", only {pct_s(normal_pct)} of supply")
    print(f"\n  {_('筹码质量', 'Chip quality')} {_qf_disp}   "
          f"({_('占观测到的钱包筹码', 'share of observed wallet chips')}{_qf_note})")
    print(f"    {_('自己买入且无风险标签', 'Bought in, no risk tag')} {pct(clean_ratio):.1f}%"
          f"   {_('零成本空降', 'Zero-cost airdrop')} {pct(airdrop_ratio):.1f}%"
          f"   {_('风险标签', 'Risk-tagged')} {pct(risk_ratio):.1f}%")
    if clean_ratio < 0.5 and airdrop_ratio > risk_ratio:
        print(_( "    （缺口主要来自零成本空降：来源未知，不等于已证实的坏筹码）",
                 "    (Shortfall is mostly zero-cost airdrop — unknown provenance, not proven-bad chips)"))
# 退化时 .1f 会把 0.0035% 打成 0.0%，和"未发现 LP"的 0 混成一个数
_fs_disp = pct_s(float_raw) if float_degenerate else f"{pct(float_share):.1f}%"
# coverage = normal_pct / float_share，退化时它同样是除零结果（恒等于 100%），不能报
_cov_disp = "" if unassessable else _(f"   Top100 覆盖流通盘 {pct(coverage):.0f}%",
                                      f"   Top100 covers {pct(coverage):.0f}% of float")
if burn_pct + dex_pct > 0.001:
    print(_( f"  流通盘 {_fs_disp}（销毁 {pct(burn_pct):.1f}% + DEX {pct(dex_pct):.1f}% 已剔除，不纳入评估）{_cov_disp}",
             f"  Float {_fs_disp} (burn {pct(burn_pct):.1f}% + DEX {pct(dex_pct):.1f}% excluded){_cov_disp}"))
else:
    # 没有销毁也没有 LP 行，就别写"已剔除 0.0%"
    print(_( f"  流通盘 100%（未发现销毁地址与 DEX 池）{_cov_disp}",
             f"  Float 100% (no burn address or DEX pool found){_cov_disp}"))
# 这条脚注必须跟着实际覆盖率走。原先无条件打印，于是在 Top100 覆盖 100% 流通盘的币上，
# 它和上一行的"Top100 覆盖流通盘 100%"当场自相矛盾 —— 一行说覆盖满了，下一行说没覆盖满。
if no_holders:
    # coverage = 0 会让下面那条打成"Top100 覆盖 0%，所以是下限"—— 下限的说法预设了有数据
    print(_( "  以上占比没有任何持仓数据支撑，既不是下限也不是完整值，请勿据此比较",
             "  The percentages above rest on no holder data at all — they are neither floors nor complete values; do not compare on them"))
elif float_degenerate:
    # 退化时 coverage 本身也是 f1() 的产物，同样是噪声，两种说法都不能给
    print(_( "  以上持仓占比的分母（流通盘）趋零，数值不可用于横向比较，请以本节顶部的绝对值为准",
             "  The float denominator above is near zero, so these percentages are not comparable — use the absolute figures at the top of this section"))
elif coverage < 0.995:
    print(_( f"  以上持仓占比均以流通盘为分母；Top100 只覆盖其中 {pct(coverage):.0f}%，未覆盖的部分意味着这些占比是下限",
             f"  Percentages above are share of tradeable float; Top100 covers {pct(coverage):.0f}% of it, so they are floors"))
else:
    print(_( "  以上持仓占比均以流通盘为分母；Top100 已覆盖全部流通盘，占比即完整值而非下限",
             "  Percentages above are share of tradeable float; Top100 covers all of it, so they are complete values, not floors"))
if coverage < 0.5 and not unassessable:
    # 覆盖率低时，"占比小"只说明 Top100 之外还有很多筹码，不能读成利好
    print(_( f"  ⚠️ Top100 只覆盖了流通盘的 {pct(coverage):.0f}%，占比偏低的指标属于未知而非利好",
             f"  ⚠️ Top100 covers only {pct(coverage):.0f}% of float — low percentages mean unknown, not good"))
print()
print(f"  {_('关注以下信号，出现则考虑离场：', 'Watch for these exit signals:')}")
for sig in exit_signals:
    print(f"    · {sig}")
print()
print("=" * 58)
print("  [OUTPUT COMPLETE — COPY ABOVE VERBATIM, DO NOT SUMMARIZE]")
print("=" * 58)
