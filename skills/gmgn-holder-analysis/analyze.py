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
float_share = max(1.0 - burn_pct - dex_pct, 1e-9)

# 集中度只数钱包地址（addr_type==0），排除 DEX 池和销毁地址。
# holders 按 amount_percentage 降序返回，normal 保持该顺序。
top10    = sum(h['amount_percentage'] for h in normal[:10]) / float_share
top20    = sum(h['amount_percentage'] for h in normal[:20]) / float_share

airdrop  = [h for h in normal if h.get('buy_tx_count_cur', 0)==0 and h.get('balance', 0)>0]
bundlers = [h for h in normal if 'bundler'      in (h.get('maker_token_tags') or [])]
rats     = [h for h in normal if 'rat_trader'   in (h.get('maker_token_tags') or [])]
snipers  = [h for h in normal if 'sniper'       in (h.get('maker_token_tags') or [])]
fresh    = [h for h in normal if 'fresh_wallet' in (h.get('tags') or [])]
wash     = [h for h in normal if 'wash_trader'  in (h.get('tags') or [])]
risk_all = set(h['address'] for g in [bundlers, rats, snipers, fresh, wash] for h in g)
risk_pct = sum(h['amount_percentage'] for h in normal if h['address'] in risk_all) / float_share
# 分类明细各自求和会重复计算带多标签的钱包，总数是去重的 —— 输出时要说明差额来源
risk_tag_hits = sum(len(g) for g in [bundlers, rats, snipers, fresh, wash])
risk_overlap  = risk_tag_hits - len(risk_all)

airdrop_pct  = sum(h['amount_percentage'] for h in airdrop) / float_share
rats_pct     = sum(h['amount_percentage'] for h in rats)    / float_share

# normal_pct / bad_pct / healthy_pct 保持总供应基准：healthy_ratio 是"看得见的筹码里
# 有多少是干净的"这一质量比值，分母就该是观测到的钱包总量。Top100 之外的长尾干净与否
# 无从得知，换成流通盘做分母会让分散型代币凭空显示成健康度下降。
normal_pct    = sum(h['amount_percentage'] for h in normal)
all_bad       = set(h['address'] for h in airdrop) | risk_all
bad_pct       = sum(h['amount_percentage'] for h in normal if h['address'] in all_bad)
healthy_pct   = max(normal_pct - bad_pct, 0)
healthy_ratio = (healthy_pct / normal_pct) if normal_pct > 0 else 0
# Top100 覆盖了多少流通盘 —— 未覆盖的部分意味着所有流通盘占比都是下限
coverage      = min(normal_pct / float_share, 1.0)

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
same_src_wallets = sum(len(ws) for __, ws in same_src_groups)
weak_src_wallets = sum(len(ws) for __, ws in weak_src_groups)
same_src_pct     = sum(h['amount_percentage'] for __, ws in same_src_groups for h in ws) / float_share
weak_src_pct     = sum(h['amount_percentage'] for __, ws in weak_src_groups for h in ws) / float_share

# 同步注资改用滑动窗口。原先的固定分桶 (ts//WINDOW)*WINDOW 漏掉跨桶边界的相邻注资：
# 两笔相隔 60 秒但落在不同桶里就检测不到。
funded     = sorted([(_tr(h, 'timestamp', 0), h) for h in normal if _tr(h, 'timestamp', 0)])
win_groups = []
_cur       = []
for ts, h in funded:
    if _cur and ts - _cur[-1][0] > WINDOW:
        if len(_cur) >= 2: win_groups.append([x[1] for x in _cur])
        _cur = []
    _cur.append((ts, h))
if len(_cur) >= 2: win_groups.append([x[1] for x in _cur])
win_groups.sort(key=lambda v: -len(v))
win_pct = sum(h['amount_percentage'] for v in win_groups for h in v) / float_share

def _span(v):
    ts = [t for t in (_tr(h, 'timestamp', 0) for h in v) if t]
    return (max(ts) - min(ts)) if ts else 0
tight_groups  = [v for v in win_groups if _span(v) <= TIGHT]
tight_wallets = sum(len(v) for v in tight_groups)

related = set()
for __, ws in same_src_groups:
    for h in ws: related.add(h['address'])
for v in win_groups:
    for h in v: related.add(h['address'])
related_pct = sum(h['amount_percentage'] for h in normal if h['address'] in related) / float_share
related_usd = sum(h.get('usd_value',0) for h in normal if h['address'] in related)

smart   = [h for h in normal if any(t in (h.get('tags') or []) for t in ['smart_degen','pump_smart'])]
kol     = [h for h in normal if 'kol' in (h.get('tags') or []) or 'renowned' in (h.get('tags') or [])]
whales  = [h for h in normal if 'whale' in (h.get('maker_token_tags') or [])]
diamond = [h for h in normal if h.get('sell_tx_count_cur',0)==0 and h.get('balance',0)>0]
partial = [h for h in normal if 0<(h.get('sell_amount_percentage') or 0)<0.5]
heavy_sell = [h for h in normal if (h.get('sell_amount_percentage') or 0)>=0.5]

smart_pct   = sum(h['amount_percentage'] for h in smart)   / float_share
kol_pct     = sum(h['amount_percentage'] for h in kol)     / float_share
whale_pct   = sum(h['amount_percentage'] for h in whales)  / float_share
diamond_pct = sum(h['amount_percentage'] for h in diamond) / float_share

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
profit_pct  = sum(h['amount_percentage'] for h in profit_w) / float_share
loss_pct    = sum(h['amount_percentage'] for h in loss_w)   / float_share
trapped     = [h for h in normal if (h.get('unrealized_pnl') or 0)<-0.2 and h.get('balance',0)>0]
trapped_pct = sum(h['amount_percentage'] for h in trapped)  / float_share

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
def _fs(ws): return sum(h['amount_percentage'] for h in ws) / float_share
zero_pct_val = _fs(zero_wallets)
low_pct_val  = _fs(low_wallets)
mid_pct_val  = _fs(mid_wallets)
high_pct_val = _fs(high_wallets)
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

def is_active(h):      return (h.get('buy_tx_count_cur') or 0)+(h.get('sell_tx_count_cur') or 0)>0
def is_selling(h):     return (h.get('sell_tx_count_cur') or 0)>0 and (h.get('balance') or 0)>=1
def is_buying_only(h): return (h.get('buy_tx_count_cur') or 0)>0 and (h.get('sell_tx_count_cur') or 0)==0

biggest     = max(normal, key=lambda h: h['amount_percentage']) if normal else None
biggest_pct = (biggest['amount_percentage'] / float_share) if biggest else 0
# 以下所有阈值都已按流通盘基准重新校准（旧值是总供应基准，直接沿用会让每条都亮红）
dangers = []
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
if dev_holding:
    hold_pct_val = sum(d.get('amount_percentage',0) for d in dev_holding) / float_share
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

if dangers:
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
    goods.append(_( f"KOL {len(kol)} 个在场（{pct(kol_pct):.2f}%）",
                    f"{len(kol)} KOL(s) holding ({pct(kol_pct):.2f}%)"))
if diamond_pct > 0.5:
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

sec1 = _("🚨 砸盘风险", "🚨 Dump Risk")
print(f"━━  {sec1}  {'━'*(54-len(sec1))}")
print()
c10f = "🔴" if top10>0.6 else ("🟡" if top10>0.4 else "🟢")
c20f = "🔴" if top20>0.75 else ("🟡" if top20>0.55 else "🟢")
print(f"  {_('集中度（占流通盘，已剔除 LP 与销毁）', 'Concentration (of tradeable float, LP + burn excluded)')}")
print(f"    Top10 {pct(top10):.1f}% {c10f}   Top20 {pct(top20):.1f}% {c20f}")
print()
if burn:
    print(f"  🔥 {_('销毁地址', 'Burn addr')}   {pct(burn_pct):.2f}%  ✅ {_('永久锁仓，无法流通', 'Permanently locked, non-circulating')}")
    print()
airf = "🔴" if airdrop_pct>0.25 else ("🟡" if airdrop_pct>0.1 else "🟢")
print(f"  {_('空降筹码（从未买入、靠转账获得）', 'Airdrop (never bought, received via transfer)')}   {len(airdrop)} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(airdrop_pct):.2f}%  {airf}")
print()
riskf = "🔴" if risk_pct>0.35 else ("🟡" if risk_pct>0.15 else "🟢")
print(f"  {_('风险钱包', 'Risk wallets')}   {_('合计', 'total')} {len(risk_all)} {_('个', '')}   {_('持仓', 'hold')} {pct(risk_pct):.2f}%  {riskf}")
risk_labels = [
    (_("老鼠仓",   "Rat Trader"),  rats,     "🚨"),
    (_("捆绑交易", "Bundler"),     bundlers, "⚠️"),
    (_("狙击者",   "Sniper"),      snipers,  "⚠️"),
    (_("新钱包",   "Fresh"),       fresh,    ""),
    (_("刷量",     "Wash"),        wash,     ""),
]
for label, group, flag in risk_labels:
    if group:
        gp = pct(sum(h['amount_percentage'] for h in group) / float_share)
        print(f"    · {label:10s}  {len(group):2d} {_('个', '')}   {_('持仓', 'hold')} {gp:.2f}%  {flag}")
if not any([rats,bundlers,snipers,fresh,wash]):
    print(f"    · {_('未发现风险标签钱包', 'No risk-tagged wallets found')}  🟢")
if risk_overlap > 0:
    # 分类明细相加会大于"合计" —— 说明差额来自多标签钱包，而不是算错了
    print(f"    · {_(f'合计已去重（{risk_overlap} 个钱包带多个风险标签）', f'Total is deduped ({risk_overlap} wallet(s) carry multiple risk tags)')}")
print()
bundler_pct_val = sum(h['amount_percentage'] for h in bundlers) / float_share
sniper_pct_val  = sum(h['amount_percentage'] for h in snipers)  / float_share
if dangers:
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
    hp = pct(h['amount_percentage'] / float_share)
    print(f"    {i}. {role_str}{display_id}")
    print(f"       {_('持仓', 'hold')} {hp:.2f}%  {cost_str}  {_('盈亏', 'pnl')} {pnl_str}")
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
    hold_pct_c = (creator.get('amount_percentage') or 0) / float_share
    c_status   = (_("余额归零", "Balance zero") if (creator.get('balance') or 0)<1
                  else _(f"⚠️ 持仓 {pct(hold_pct_c):.2f}%", f"⚠️ Holding {pct(hold_pct_c):.2f}%"))
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
        print(f"     {addr_short(to_addr)}  {_('持仓', 'hold')} {pct((target.get('amount_percentage') or 0)/float_share):.2f}%  {_('标签', 'tags')}: {' '.join(t_mtags) or _('无','none')}")
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
            is_curr = ath_info.get('ath_token','').lower()==TOKEN_ADDR.lower()
            curr_label = _('（本币）', ' (this token)') if is_curr else ''
            print(f"  {_('历史最高市值', 'All-time high MC')}: {ath_info.get('token_name','')}({ath_info.get('token_symbol','?')}){curr_label}  ATH {usd(float(ath_info.get('ath_mc') or 0))}")
        print()

sec3 = _("🔗 关联资金", "🔗 Related Funds")
print(f"━━  {sec3}  {'━'*(54-len(sec3))}")
print()
print(f"  {_('多个钱包来自同一资金来源地址，或在极短时间内同步注资', 'Multiple wallets from same funding source or funded in tight time windows')}")
print()
if related:
    relf = "🔴" if related_pct>0.25 else ("🟡" if related_pct>0.1 else "🟢")
    # 秒级批量注资本身就是异常信号，不该因为占比小而在标题上显示为绿
    if tight_groups and relf == "🟢": relf = "🟡"
    print(f"  {_('涉及', 'Involves')} {len(related)} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(related_pct):.2f}%   {usd(related_usd)}  {relf}")
    print()
    print(f"  ├─ {_('强关联（同一来源 + 时间集中或金额一致）', 'Strong (same source + tight timing or uniform amounts)')}   {len(same_src_groups)} {_('组', 'groups')} / {same_src_wallets} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(same_src_pct):.2f}%")
    if same_src_groups:
        fa, ws = same_src_groups[0]
        native_in = sum(float(_tr(w, 'amount', 0) or 0) for w in ws)
        print(f"  │   {_('最大组', 'Largest group')}: {len(ws)} {_('个钱包', 'wallets')}   {_('来源', 'from')} {addr_short(fa)}   {_('合计注资', 'total funded')} {native_in:.4f} {NSYM}")
    if weak_src_groups:
        # 只共用转入地址、时间金额都不一致 —— 交易所热钱包和团伙长得一样，不能混进合计
        print(f"  ├─ {_('弱关联（仅共用转入地址，可能是交易所热钱包）', 'Weak (shared source only, may be a CEX hot wallet)')}   {len(weak_src_groups)} {_('组', 'groups')} / {weak_src_wallets} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(weak_src_pct):.2f}%   {_('不计入上方合计', 'excluded from total above')}")
    print(f"  │")
    if win_groups:
        win_total = sum(len(v) for v in win_groups)
        if tight_groups:
            print(f"  └─ {_(f'同步注资（{WINDOW//60}min 内集中入场）', f'Coordinated funding (within {WINDOW//60}min)')}   {win_total} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(win_pct):.2f}%  🔴")
            print(f"      🔴 {_(f'其中 {tight_wallets} 个钱包在 {TIGHT} 秒内被同步注资，基本可判定脚本批量打款', f'{tight_wallets} wallet(s) funded within {TIGHT}s — almost certainly scripted batch funding')}")
        elif win_total>=3:
            print(f"  └─ {_(f'同步注资（{WINDOW//60}min 内集中入场）', f'Coordinated funding (within {WINDOW//60}min)')}   {win_total} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(win_pct):.2f}%  ⚠️")
        else:
            print(f"  └─ {_(f'同步注资（{WINDOW//60}min 内集中入场）', f'Coordinated funding (within {WINDOW//60}min)')}   {win_total} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(win_pct):.2f}%")
        # 只有一个批次时，明细就是上面那行，不重复打印
        if len(win_groups) > 1:
            v = win_groups[0]
            print(f"      {_('最大批次', 'Largest batch')}: {len(v)} {_('个钱包', 'wallets')}   {_('合计持仓', 'total hold')} {pct(sum(h['amount_percentage'] for h in v)/float_share):.3f}%   {_('时间跨度', 'span')} {_span(v)}s")
        else:
            print(f"      {_('时间跨度', 'Span')} {_span(win_groups[0])}s")
    else:
        print(f"  └─ {_('未发现同步集中注资', 'No coordinated funding detected')}")
else:
    print(f"  {_('未发现明显关联资金', 'No significant linked funds detected')}  🟢")
    if weak_src_groups:
        print(f"  ({_(f'{weak_src_wallets} 个钱包共用转入地址，但时间和金额都不一致，判为交易所出金而非团伙', f'{weak_src_wallets} wallets share a funding address but differ in timing and amount — read as CEX withdrawals, not a gang')})")
print()

sec4 = _("🧠 优质信号", "🧠 Quality Signals")
print(f"━━  {sec4}  {'━'*(54-len(sec4))}")
print()
print(f"  {_('聪明钱', 'Smart Money')}   {len(smart):2d}   {_('持仓', 'hold')} {pct(smart_pct):.2f}%  {'✅' if smart else '—'}")
if smart: print(f"  {_('近期动向', 'Recent')}:  {trend_str(smart)}")
print(f"  KOL          {len(kol):2d}   {_('持仓', 'hold')} {pct(kol_pct):.2f}%  {'✅' if kol else '—'}")
if kol:
    for h in kol:
        name = h.get('twitter_name') or h.get('name') or addr_short(h['address'])
        print(f"    · {name}  {_('持仓', 'hold')} {pct(h['amount_percentage']/float_share):.2f}%  {holding_status(h)}  {_('买/卖', 'buy/sell')}: {h.get('buy_tx_count_cur',0)}/{h.get('sell_tx_count_cur',0)}")
print(f"  {_('鲸鱼', 'Whale')}        {len(whales):2d}   {_('持仓', 'hold')} {pct(whale_pct):.2f}%  {'✅' if whales else '—'}")
if whales: print(f"  {_('近期动向', 'Recent')}:  {trend_str(whales)}")
print()
df = "✅" if diamond_pct>0.6 else ("🟡" if diamond_pct>0.35 else "⚠️")
print(f"  {_('钻石手（从未卖出）', 'Diamond hands (never sold)')}   {len(diamond):2d}   {_('持仓', 'hold')} {pct(diamond_pct):.1f}%  {df}")
print(f"  {_('部分卖出(<50%)', 'Partial sell (<50%)')}  {len(partial):2d}   {_('大量卖出(≥50%)', 'Heavy sell (≥50%)')}  {len(heavy_sell):2d}")
sig_count     = len(smart) + len(kol) + len(whales)
kol_selling   = [h for h in kol   if (h.get('sell_tx_count_cur') or 0) > 0]
kol_holding   = [h for h in kol   if (h.get('sell_tx_count_cur') or 0) == 0 and (h.get('balance') or 0) >= 1]
smart_selling = [h for h in smart if (h.get('sell_tx_count_cur') or 0) > 0]
smart_holding = [h for h in smart if (h.get('sell_tx_count_cur') or 0) == 0 and (h.get('balance') or 0) >= 1]
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
    total_hp    = sum(h['amount_percentage'] for h in ws) / float_share
    costed      = [h for h in ws if (h.get('avg_cost') or 0)>0]
    selling_out = [h for h in ws if holding_status(h) in (
                   _('🔴 大量出货','🔴 Heavy Selling'), _('🟡 出货中','🟡 Selling'))]
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
    print(f"  {batch_label}{rank}{_('（', '(')}{label}{_('）', ')')}  {len(ws)} {_('个钱包', 'wallets')}  {_('持仓', 'hold')} {pct(total_hp):.2f}%  {risk_flag}{sell_str}{hold_str}")
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
    print(f"  ⚫ {_('零余额', 'Zero balance')}     {len(zero_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(zero_pct_val):.2f}%   —    → {_('无加仓能力，可能是分仓小号', 'No buying power, likely sub-wallets')}")
if HAS_PRICE:
    if low_wallets:
        low_total = sum(native_usd(h) for h in low_wallets)
        print(f"  🟡 {_('低（<$200）', 'Low (<$200)')}   {len(low_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(low_pct_val):.2f}%   {usd(low_total)}")
    if mid_wallets:
        mid_total = sum(native_usd(h) for h in mid_wallets)
        print(f"  🟠 {_('中（$200~$1200）', 'Mid ($200~$1200)')}  {len(mid_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(mid_pct_val):.2f}%   {usd(mid_total)}")
    if high_wallets:
        print(f"  🔴 {_('高（$1200+）', 'High ($1200+)')}  {len(high_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(high_pct_val):.2f}%   {usd(high_total)}   → {_('可随时加仓', 'can add anytime')}")
elif high_wallets:
    # 拿不到原生代币价格，只按原生数量分档，不编造美元金额
    print(f"  🟢 {_('有余额', 'Has balance')}     {len(high_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(high_pct_val):.2f}%   {fmt_native(high_native)}")
    print(f"     ({_(f'{CHAIN} 链拿不到 {NSYM} 价格，仅显示原生数量', f'No {NSYM} price for {CHAIN}, native amount only')})")
print()
if high_wallets and HAS_PRICE:
    print(f"  ➤ {_('高余额钱包', 'High-balance wallets')} {len(high_wallets)} {_('个持仓', 'holding')} {pct(high_pct_val):.1f}%{_('，', ', ')}{_('合计', 'total')} {usd(high_total)} {_('可随时加仓', 'ready to add')}")
if zero_wallets and zero_pct_val > 0.1:
    print(f"  ➤ {len(zero_wallets)} {_('个钱包零余额（持仓 ', 'wallets with zero balance (hold ')}{pct(zero_pct_val):.1f}%{_('）', ')')}, {_('无加仓能力，可能是分仓小号', 'no buying power, likely sub-wallets')}")
print()

sec7 = _("📊 筹码结构", "📊 Chip Structure")
print(f"━━  {sec7}  {'━'*(54-len(sec7))}")
print()
total_n = len(normal)
if total_n > 0:
    # 钱包个数答"多数人赚没赚"，流通盘占比答"赚钱的筹码有多重" —— 抛压看后者
    print(f"  {_('盈利', 'Profit')} {len(profit_w)}   ({len(profit_w)/total_n*100:.0f}% {_('钱包', 'wallets')} / {pct(profit_pct):.1f}% {_('流通盘', 'float')})")
    print(f"  {_('亏损', 'Loss')} {len(loss_w)}   ({len(loss_w)/total_n*100:.0f}% {_('钱包', 'wallets')} / {pct(loss_pct):.1f}% {_('流通盘', 'float')})   {_('持平', 'Break-even')} {total_n-len(profit_w)-len(loss_w)}")
tf_flag = "⚠️" if len(trapped)>30 else ""
print(f"  {_('套牢盘（浮亏>20%）', 'Underwater (>20% loss)')}   {len(trapped)}   {_('持仓', 'hold')} {pct(trapped_pct):.2f}%  {tf_flag}")
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
hf = "🔴" if healthy_ratio<0.3 else ("🟡" if healthy_ratio<0.5 else "🟢")
print(f"\n  {_('健康筹码', 'Healthy chips')} {pct(healthy_ratio):.1f}% {hf}   ({_('占观测到的钱包筹码', 'share of observed wallet chips')})")
if burn_pct + dex_pct > 0.001:
    print(_( f"  流通盘 {pct(float_share):.1f}%（销毁 {pct(burn_pct):.1f}% + DEX {pct(dex_pct):.1f}% 已剔除，不纳入评估）   Top100 覆盖流通盘 {pct(coverage):.0f}%",
             f"  Float {pct(float_share):.1f}% (burn {pct(burn_pct):.1f}% + DEX {pct(dex_pct):.1f}% excluded)   Top100 covers {pct(coverage):.0f}% of float"))
else:
    # 没有销毁也没有 LP 行，就别写"已剔除 0.0%"
    print(_( f"  流通盘 100%（未发现销毁地址与 DEX 池）   Top100 覆盖流通盘 {pct(coverage):.0f}%",
             f"  Float 100% (no burn address or DEX pool found)   Top100 covers {pct(coverage):.0f}% of float"))
print(_( "  以上持仓占比均以流通盘为分母；Top100 未覆盖的部分意味着这些占比是下限",
         "  Percentages above are share of tradeable float; they are floors — Top100 does not cover the entire float"))
if coverage < 0.5:
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
