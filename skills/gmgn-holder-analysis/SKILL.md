---
name: gmgn-holder-analysis
description: Token holder chip analysis — deep analysis of holder structure including chip distribution, entry cost, whale/dev/KOL behavior, risk wallets (rat traders, bundlers, snipers), related wallets, smart money signals, and an AI rating based purely on token structure. Use when user asks about holder analysis, 筹码分析, 持仓分析, chip structure, who is holding, or whether a token is safe to buy based on its holder composition.
argument-hint: "--chain <sol|bsc|base|eth|robinhood|arc|stable> --address <token_address>"
metadata:
  cliHelp: "gmgn-cli token holders --help && gmgn-cli portfolio created-tokens --help"
---

**BEFORE RUNNING ANY COMMAND: Run `gmgn-cli config --check`. If exit code is 0, proceed normally. If exit code is 1, run `gmgn-cli config` and show output, then apply the key with `gmgn-cli config --apply <KEY>`. If unknown option, tell user to run `npm install -g gmgn-cli`.**

**IMPORTANT: Always use `gmgn-cli` commands. Do NOT use curl, WebFetch, or visit gmgn.ai.**

When the user asks to analyze holders for a token, extract `--chain` and `--address` from their message, then run the analysis script below. Also detect the user's language: set `LANG` to `'zh'` if the user wrote in Chinese, `'en'` if in English (default `'zh'`).

## Analysis Script

Run the following command, replacing the placeholders with the actual values:

```bash
python3 ~/.claude/skills/gmgn-holder-analysis/analyze.py <FILL_IN_TOKEN_ADDRESS> <FILL_IN_CHAIN> <FILL_IN_LANG>
```

- FILL_IN_CHAIN: `sol` for Solana addresses; for EVM `0x...` addresses, use the chain the user specifies (`bsc`/`eth`/`base`/`robinhood`/`arc`/`stable`), otherwise use `auto`. Do NOT use `auto` when the user mentions arc, stable, or robinhood — pass the chain name directly.
- FILL_IN_LANG: `zh` if user wrote Chinese, `en` if English, default `zh`

## Output Rule

After the script finishes, paste the complete stdout verbatim into your reply — every line, every section, nothing omitted or summarized. Do NOT add any introduction, commentary, or summary before or after the output block.

<!-- legacy inline script kept below for reference — DO NOT run this block -->
<!--
```python
python3 << 'PYEOF'
import json, subprocess, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

TOKEN_ADDR = "<FILL_IN_TOKEN_ADDRESS>"
CHAIN      = "<FILL_IN_CHAIN>"
LANG       = "<FILL_IN_LANG>"   # 'zh' or 'en'
WINDOW     = 1800
now_ts     = int(time.time())

ZH = (LANG == 'zh')
def _(zh, en): return zh if ZH else en

def run_cli(args, timeout=30):
    r = subprocess.run(['gmgn-cli'] + args + ['--raw'],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)

# Fetch holders and devs in parallel, then created-tokens after extracting creator
with ThreadPoolExecutor(max_workers=2) as ex:
    f_holders = ex.submit(run_cli, ['token', 'holders', '--chain', CHAIN, '--address', TOKEN_ADDR, '--limit', '100'])
    f_devs    = ex.submit(run_cli, ['token', 'holders', '--chain', CHAIN, '--address', TOKEN_ADDR, '--tag', 'dev', '--limit', '20'])

holders = f_holders.result()['list']
devs    = f_devs.result()['list']

_creator_tmp = next((d for d in devs if 'creator' in (d.get('maker_token_tags') or [])), None)
created_data = None
if _creator_tmp:
    try:
        created_data = run_cli(['portfolio', 'created-tokens', '--chain', CHAIN,
                                '--wallet', _creator_tmp['address'],
                                '--order-by', 'market_cap', '--direction', 'desc'])
    except: pass

# ── Wallet classification ────────────────────────────────
# addr_type: 0=normal, 1=burn, 2=DEX/pool
normal = [h for h in holders if h.get('addr_type', 0) == 0]
burn   = [h for h in holders if h.get('addr_type', 0) == 1]
dex    = [h for h in holders if h.get('addr_type', 0) == 2]

# ── Helpers ──────────────────────────────────────────────
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

# ── Price / MC ───────────────────────────────────────────
supply_list  = [h['balance']/h['amount_percentage'] for h in normal
                if h.get('amount_percentage',0)>0 and h.get('balance',0)>0]
total_supply = sorted(supply_list)[len(supply_list)//2] if supply_list else 1_000_000_000
price_list   = [h['usd_value']/h['balance'] for h in normal
                if h.get('balance',0)>0 and h.get('usd_value',0)>0]
cur_price    = sorted(price_list)[len(price_list)//2] if price_list else 0
cur_mc       = total_supply * cur_price

burn_pct = sum(h['amount_percentage'] for h in burn)
dex_pct  = sum(h['amount_percentage'] for h in dex)
top10    = sum(h['amount_percentage'] for h in holders[:10])
top20    = sum(h['amount_percentage'] for h in holders[:20])

# ── Risk wallets ─────────────────────────────────────────
# maker_token_tags: bundler, rat_trader, sniper, whale, top_holder, transfer_in, dev_team, creator
# tags: smart_degen, pump_smart, renowned, fresh_wallet, wash_trader, fomo, kol
airdrop  = [h for h in normal if h.get('buy_tx_count_cur', 0)==0 and h.get('balance', 0)>0]
bundlers = [h for h in normal if 'bundler'      in (h.get('maker_token_tags') or [])]
rats     = [h for h in normal if 'rat_trader'   in (h.get('maker_token_tags') or [])]
snipers  = [h for h in normal if 'sniper'       in (h.get('maker_token_tags') or [])]
fresh    = [h for h in normal if 'fresh_wallet' in (h.get('tags') or [])]
wash     = [h for h in normal if 'wash_trader'  in (h.get('tags') or [])]
risk_all = set(h['address'] for g in [bundlers, rats, snipers, fresh, wash] for h in g)
risk_pct = sum(h['amount_percentage'] for h in normal if h['address'] in risk_all)

airdrop_pct  = sum(h['amount_percentage'] for h in airdrop)
rats_pct     = sum(h['amount_percentage'] for h in rats)

# ── Healthy chip ratio ───────────────────────────────────
normal_pct    = sum(h['amount_percentage'] for h in normal)
all_bad       = set(h['address'] for h in airdrop) | risk_all
bad_pct       = sum(h['amount_percentage'] for h in normal if h['address'] in all_bad)
healthy_pct   = max(normal_pct - bad_pct, 0)
healthy_ratio = (healthy_pct / normal_pct) if normal_pct > 0 else 0

# ── Related wallets ──────────────────────────────────────
from_map = defaultdict(list)
for h in normal:
    fa = (h.get('native_transfer') or {}).get('from_address', '')
    if fa: from_map[fa].append(h)
same_src_groups  = sorted([(fa, ws) for fa, ws in from_map.items() if len(ws)>=2], key=lambda x: -len(x[1]))
same_src_wallets = sum(len(ws) for __,ws in same_src_groups)
same_src_pct     = sum(h['amount_percentage'] for __,ws in same_src_groups for h in ws)

funded = [((h.get('native_transfer') or {}).get('timestamp',0), h)
          for h in normal if (h.get('native_transfer') or {}).get('timestamp',0)]
bucket = defaultdict(list)
for ts, h in funded:
    bucket[(ts//WINDOW)*WINDOW].append(h)
win_groups = sorted([(k,v) for k,v in bucket.items() if len(v)>=2], key=lambda x: -len(x[1]))
win_pct    = sum(h['amount_percentage'] for __,v in win_groups for h in v)

related = set()
for __,ws in same_src_groups:
    for h in ws: related.add(h['address'])
for __,v in win_groups:
    for h in v: related.add(h['address'])
related_pct = sum(h['amount_percentage'] for h in normal if h['address'] in related)
related_usd = sum(h.get('usd_value',0) for h in normal if h['address'] in related)

# ── Quality signals ──────────────────────────────────────
smart   = [h for h in normal if any(t in (h.get('tags') or []) for t in ['smart_degen','pump_smart'])]
kol     = [h for h in normal if 'kol' in (h.get('tags') or []) or 'renowned' in (h.get('tags') or [])]
whales  = [h for h in normal if 'whale' in (h.get('maker_token_tags') or [])]
diamond = [h for h in normal if h.get('sell_tx_count_cur',0)==0 and h.get('balance',0)>0]
partial = [h for h in normal if 0<(h.get('sell_amount_percentage') or 0)<0.5]
heavy_sell = [h for h in normal if (h.get('sell_amount_percentage') or 0)>=0.5]

smart_pct   = sum(h['amount_percentage'] for h in smart)
kol_pct     = sum(h['amount_percentage'] for h in kol)
whale_pct   = sum(h['amount_percentage'] for h in whales)
diamond_pct = sum(h['amount_percentage'] for h in diamond)

# ── Dev data ─────────────────────────────────────────────
top100_map   = {h['address']: h for h in holders}
creator      = next((d for d in devs if 'creator' in (d.get('maker_token_tags') or [])), None)
sub_devs     = [d for d in devs if 'creator' not in (d.get('maker_token_tags') or [])]
dev_realized = sum(d.get('realized_profit') or 0 for d in devs)
dev_holding  = [d for d in devs if (d.get('balance') or 0)>=1]

# ── Holding metrics ──────────────────────────────────────
valid_starts  = [h['start_holding_at'] for h in holders if (h.get('start_holding_at') or 0)>0]
token_launch  = min(valid_starts) if valid_starts else now_ts
durations     = [now_ts-h['start_holding_at'] for h in normal
                 if (h.get('start_holding_at') or 0)>0 and now_ts>h['start_holding_at']]
avg_hold_days = (sum(durations)/len(durations)/86400) if durations else 0

profit_w = [h for h in normal if (h.get('profit') or 0)>0]
loss_w   = [h for h in normal if (h.get('profit') or 0)<0]
trapped  = [h for h in normal if (h.get('unrealized_pnl') or 0)<-0.2 and h.get('balance',0)>0]

# ── Buying power ─────────────────────────────────────────
# SOL: native_balance in lamports (1e9); EVM: in wei (1e18)
NATIVE_PRICE = 160 if CHAIN == 'sol' else (700 if CHAIN == 'bsc' else 2500)
NATIVE_DENOM = 1e9  if CHAIN == 'sol' else 1e18
def native_usd(h): return int(h.get('native_balance') or 0)/NATIVE_DENOM*NATIVE_PRICE
zero_wallets = [h for h in normal if native_usd(h)==0]
low_wallets  = [h for h in normal if 0 < native_usd(h) <= 200]
mid_wallets  = [h for h in normal if 200 < native_usd(h) <= 1200]
high_wallets = [h for h in normal if native_usd(h) > 1200]
zero_pct_val = sum(h['amount_percentage'] for h in zero_wallets)
low_pct_val  = sum(h['amount_percentage'] for h in low_wallets)
mid_pct_val  = sum(h['amount_percentage'] for h in mid_wallets)
high_pct_val = sum(h['amount_percentage'] for h in high_wallets)
high_total   = sum(native_usd(h) for h in high_wallets)
total_buying_power = sum(native_usd(h) for h in normal)

# ── Wallet roles / behaviors ─────────────────────────────
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
    buying  = [h for h in wlist if (h.get('buy_tx_count_cur') or 0)>0 and (h.get('sell_tx_count_cur') or 0)==0]
    selling = [h for h in wlist if (h.get('sell_tx_count_cur') or 0)>0 and (h.get('buy_tx_count_cur') or 0)==0]
    both    = [h for h in wlist if (h.get('buy_tx_count_cur') or 0)>0 and (h.get('sell_tx_count_cur') or 0)>0]
    holding = [h for h in wlist if (h.get('buy_tx_count_cur') or 0)==0 and (h.get('sell_tx_count_cur') or 0)==0]
    parts = []
    if buying:  parts.append(f"📈 {_('买入中', 'Buying')} {len(buying)}")
    if selling: parts.append(f"📉 {_('卖出中', 'Selling')} {len(selling)}")
    if both:    parts.append(f"🔄 {_('买卖都有', 'Both')} {len(both)}")
    if holding: parts.append(f"🤝 {_('未动', 'Holding')} {len(holding)}")
    return "  ".join(parts) if parts else "—"

def is_active(h):      return (h.get('buy_tx_count_cur') or 0)+(h.get('sell_tx_count_cur') or 0)>0
def is_selling(h):     return (h.get('sell_tx_count_cur') or 0)>0 and (h.get('balance') or 0)>=1
def is_buying_only(h): return (h.get('buy_tx_count_cur') or 0)>0 and (h.get('sell_tx_count_cur') or 0)==0

# ── Rating ───────────────────────────────────────────────
biggest = max(normal, key=lambda h: h['amount_percentage']) if normal else None
dangers = []
if rats and rats_pct > 0.1:
    dangers.append(_( f"老鼠仓持仓 {pct(rats_pct):.1f}%，出货即砸盘",
                      f"Rat traders hold {pct(rats_pct):.1f}% — instant dump risk"))
if biggest and biggest['amount_percentage'] > 0.15:
    dangers.append(_( f"最大单钱包持仓 {pct(biggest['amount_percentage']):.1f}%，筹码极度集中",
                      f"Largest wallet holds {pct(biggest['amount_percentage']):.1f}% — extreme concentration"))
if creator:
    to_out = creator.get('token_transfer_out') or {}
    if (to_out.get('address') or '') in top100_map:
        dangers.append(_("Dev 筹码转给内部马甲，换手控盘",
                         "Dev transferred chips to internal wallet — covert control"))

warns = []
if dev_holding:
    hold_pct_val = sum(d.get('amount_percentage',0) for d in dev_holding)
    if hold_pct_val > 0.01:
        warns.append(_( f"Dev 仍持仓 {pct(hold_pct_val):.2f}%",
                        f"Dev still holds {pct(hold_pct_val):.2f}%"))
if airdrop_pct > 0.15:
    warns.append(_( f"空降筹码 {pct(airdrop_pct):.1f}%，来源不透明",
                    f"Airdrop supply {pct(airdrop_pct):.1f}% — opaque origin"))
if risk_pct > 0.3:
    warns.append(_( f"风险钱包持仓 {pct(risk_pct):.1f}%，筹码质量差",
                    f"Risk wallets hold {pct(risk_pct):.1f}% — low chip quality"))
if related_pct > 0.1:
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
if diamond_pct > 0.4:
    goods.append(_( f"钻石手持仓 {pct(diamond_pct):.1f}%，筹码稳定",
                    f"Diamond hands hold {pct(diamond_pct):.1f}% — stable chips"))

exit_signals = []
if rats:
    exit_signals.append(_("老鼠仓钱包出现卖出操作", "Rat trader wallets start selling"))
if dev_holding:
    exit_signals.append(_("Dev 钱包开始出货", "Dev wallets start dumping"))
if airdrop_pct>0.15:
    exit_signals.append(_("空降大户出现集中卖出", "Airdrop whales start concentrated selling"))
if not exit_signals:
    exit_signals = [_("Top5 大户出现集中出货", "Top 5 holders start concentrated selling"),
                    _("价格跌破建仓均价支撑", "Price breaks below average entry cost")]
exit_signals = exit_signals[:3]

# ── Top5 pressure analysis ───────────────────────────────
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
    if buy0 or avg_cost==0:
        cost_str = _("零成本（转账获得）", "Zero cost (received via transfer)")
        pnl_str  = "—"
        lv       = "⚠️ " + _("高", "High")
        note     = _("零成本，随时可出货", "Zero cost — can dump anytime")
    elif up_pnl>1.0:
        mult     = up_pnl+1
        cost_str = f"{_('均价', 'avg')} ${avg_cost:.4f}"
        pnl_str  = f"+{up_pnl*100:.0f}% ({mult:.1f}x)  {usd(up_usd)}"
        lv       = "⚠️ " + _("高", "High")
        note     = _(f"建仓MC {usd(total_supply*avg_cost)} → 现 {usd(cur_mc)}，浮盈 {mult:.1f}x 压力强",
                     f"Entry MC {usd(total_supply*avg_cost)} → now {usd(cur_mc)}, {mult:.1f}x gain — strong pressure")
    elif up_pnl>0.1:
        cost_str = f"{_('均价', 'avg')} ${avg_cost:.4f}"
        pnl_str  = f"+{up_pnl*100:.0f}%  {usd(up_usd)}"
        lv       = "🟡 " + _("中", "Med")
        note     = _("小幅浮盈，出货意愿一般", "Moderate gain — mild sell pressure")
    elif up_pnl>=-0.1:
        cost_str = f"{_('均价', 'avg')} ${avg_cost:.4f}"
        pnl_str  = f"{up_pnl*100:+.0f}%  {usd(up_usd)}" if abs(up_usd)>=1 else _("接近成本", "Near cost")
        lv       = "🟢 " + _("低", "Low")
        note     = _("接近成本，短期抛压有限", "Near break-even — limited short-term pressure")
    else:
        cost_str = f"{_('均价', 'avg')} ${avg_cost:.4f}"
        pnl_str  = f"{up_pnl*100:.0f}%  {usd(up_usd)}"
        lv       = "🟢 " + _("低", "Low")
        note     = _("套牢中，短期不易割肉", "Underwater — unlikely to sell soon")
    beh     = wallet_behavior(h)
    beh_str = ("  " + _("行为", "behavior") + ": " + beh) if beh else ""
    return role_str, display_id, cost_str, pnl_str, lv, note, beh_str, holding_status(h)

# ══════════════════════════════════════════════════════════
# OUTPUT
# ══════════════════════════════════════════════════════════
title = _("Holder 筹码分析", "Holder Chip Analysis")
print(f"┌{'─'*56}┐")
print(f"│{('  '+title):^56}│")
print(f"│{('  '+TOKEN_ADDR[:10]+'...'+TOKEN_ADDR[-4:]+'  ·  Top100  ·  '+CHAIN.upper()):^56}│")
print(f"│{('  MC '+usd(cur_mc)):^56}│")
print(f"└{'─'*56}┘")
print()

# ── Dump Risk ──
sec1 = _("🚨 砸盘风险", "🚨 Dump Risk")
print(f"━━  {sec1}  {'━'*(54-len(sec1))}")
print()
c10f = "🔴" if top10>0.5 else ("🟡" if top10>0.3 else "🟢")
c20f = "🔴" if top20>0.6 else ("🟡" if top20>0.4 else "🟢")
print(f"  {_('集中度', 'Concentration')}   Top10 {pct(top10):.1f}% {c10f}   Top20 {pct(top20):.1f}% {c20f}")
print()
if burn:
    print(f"  🔥 {_('销毁地址', 'Burn addr')}   {pct(burn_pct):.2f}%  ✅ {_('永久锁仓，无法流通', 'Permanently locked, non-circulating')}")
    print()
airf = "🔴" if airdrop_pct>0.2 else ("🟡" if airdrop_pct>0.1 else "🟢")
print(f"  {_('空降筹码（从未买入、靠转账获得）', 'Airdrop (never bought, received via transfer)')}   {len(airdrop)} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(airdrop_pct):.2f}%  {airf}")
print()
riskf = "🔴" if risk_pct>0.3 else ("🟡" if risk_pct>0.1 else "🟢")
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
        gp = pct(sum(h['amount_percentage'] for h in group))
        print(f"    · {label:10s}  {len(group):2d} {_('个', '')}   {_('持仓', 'hold')} {gp:.2f}%  {flag}")
if not any([rats,bundlers,snipers,fresh,wash]):
    print(f"    · {_('未发现风险标签钱包', 'No risk-tagged wallets found')}  🟢")
print()
bundler_pct_val = sum(h['amount_percentage'] for h in bundlers)
sniper_pct_val  = sum(h['amount_percentage'] for h in snipers)
if dangers:
    sdp_summary = f"🔴 {dangers[0]}"
elif rats_pct > 0.05:
    sdp_summary = _( f"🔴 老鼠仓持仓 {pct(rats_pct):.1f}%，零成本拿的，随时可以无损砸盘",
                     f"🔴 Rat traders hold {pct(rats_pct):.1f}% at zero cost — can dump with no loss anytime")
elif top10 > 0.4:
    sdp_summary = _( f"🟡 Top10 持仓 {pct(top10):.1f}%，筹码过于集中，大户一旦出货冲击很大",
                     f"🟡 Top10 hold {pct(top10):.1f}% — highly concentrated, big impact if they sell")
elif bundler_pct_val > 0.2:
    sdp_summary = _( f"🟡 捆绑钱包持仓 {pct(bundler_pct_val):.1f}%，这批是开盘机器人扫货，出货时可能集中砸盘",
                     f"🟡 Bundlers hold {pct(bundler_pct_val):.1f}% — bot-swept at open, may dump together")
elif airdrop_pct > 0.15:
    sdp_summary = _( f"🟡 空降筹码 {pct(airdrop_pct):.1f}%，这些人零成本拿到币，随时可能出货",
                     f"🟡 Airdrop supply {pct(airdrop_pct):.1f}% at zero cost — may sell anytime")
elif sniper_pct_val > 0.1:
    sdp_summary = _( f"🟡 狙击者持仓 {pct(sniper_pct_val):.1f}%，开盘低价进的，浮盈高、随时可套现",
                     f"🟡 Snipers hold {pct(sniper_pct_val):.1f}% at launch price — high unrealized gain, may cash out")
elif risk_pct > 0.1:
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
    hp = pct(h['amount_percentage'])
    print(f"    {i}. {role_str}{display_id}")
    print(f"       {_('持仓', 'hold')} {hp:.2f}%  {cost_str}  {_('盈亏', 'pnl')} {pnl_str}")
    print(f"       {_('抛压', 'pressure')} {lv} — {note}")
    print(f"       {_('状态', 'status')} {st}{beh_str}")
    print()

# ── Dev Wallets ──
sec2 = _("👨‍💻 Dev 钱包", "👨‍💻 Dev Wallets")
print(f"━━  {sec2}  {'━'*(54-len(sec2))}")
print()
dev_status = (_("✅ 全部余额归零", "✅ All cleared") if not dev_holding
              else _(f"⚠️ 仍有 {len(dev_holding)} 个持仓中", f"⚠️ {len(dev_holding)} still holding"))
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
    hold_pct_c = creator.get('amount_percentage') or 0
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
        print(f"     {addr_short(to_addr)}  {_('持仓', 'hold')} {pct(target.get('amount_percentage',0)):.2f}%  {_('标签', 'tags')}: {' '.join(t_mtags) or _('无','none')}")
    elif (creator.get('balance') or 0)<1 and tf_out==0:
        print(f"  ✅ {_('已完全卖出，无异常转账记录', 'Fully sold, no abnormal transfers')}")
    print()
    if to_addr and to_addr in top100_map:
        dev_summary = _(  "🔴 Dev 换马甲持仓，这个很危险，随时可以砸盘",
                          "🔴 Dev using sock puppet — very dangerous, can dump anytime")
    elif dev_holding:
        dev_summary = _(  "🟡 Dev 还没出完，有出货风险，关注钱包动向",
                          "🟡 Dev hasn't fully exited — dump risk, watch wallet activity")
    elif dev_realized > 50000:
        dev_summary = _( f"🟡 Dev 已套现 {usd(dev_realized)}，虽然出完了但赚了不少",
                         f"🟡 Dev cashed out {usd(dev_realized)} — exited but made significant profit")
    else:
        dev_summary = _(  "🟢 Dev 已清仓，没有持仓压力",
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

# ── Related Funds ──
sec3 = _("🔗 关联资金", "🔗 Related Funds")
print(f"━━  {sec3}  {'━'*(54-len(sec3))}")
print()
print(f"  {_('多个钱包来自同一资金来源地址，或在极短时间内同步注资', 'Multiple wallets from same funding source or funded in tight time windows')}")
print()
if related:
    relf = "🔴" if related_pct>0.15 else ("🟡" if related_pct>0.05 else "🟢")
    print(f"  {_('涉及', 'Involves')} {len(related)} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(related_pct):.2f}%   {usd(related_usd)}  {relf}")
    print()
    print(f"  ├─ {_('同一资金来源地址', 'Same funding source')}   {len(same_src_groups)} {_('组', 'groups')} / {same_src_wallets} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(same_src_pct):.2f}%")
    if same_src_groups:
        fa, ws = same_src_groups[0]
        native_in = sum(float((w.get('native_transfer') or {}).get('amount',0) or 0) for w in ws)
        native_sym = 'SOL' if CHAIN=='sol' else ('BNB' if CHAIN=='bsc' else 'ETH')
        print(f"  │   {_('最大组', 'Largest group')}: {len(ws)} {_('个钱包', 'wallets')}   {_('同一地址先后转入启动资金', 'funded sequentially from same addr')}   {native_in:.4f} {native_sym}")
    print(f"  │")
    if win_groups:
        win_total = sum(len(v) for __,v in win_groups)
        if win_total>=3:
            k,v = win_groups[0]
            print(f"  └─ {_('同期注资（30min内集中入场）', 'Coordinated funding (within 30min)')}   {win_total} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(win_pct):.2f}%  ⚠️")
            print(f"      {_('最大批次', 'Largest batch')}: {len(v)} {_('个钱包', 'wallets')}   {_('合计持仓', 'total hold')} {pct(sum(h['amount_percentage'] for h in v)):.3f}%")
        else:
            print(f"  └─ {_('同期注资（30min内集中入场）', 'Coordinated funding (within 30min)')}   {win_total} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(win_pct):.2f}%")
    else:
        print(f"  └─ {_('未发现同期集中注资', 'No coordinated funding detected')}")
else:
    print(f"  {_('未发现明显关联资金', 'No significant linked funds detected')}  🟢")
print()

# ── Quality Signals ──
sec4 = _("🧠 优质信号", "🧠 Quality Signals")
print(f"━━  {sec4}  {'━'*(54-len(sec4))}")
print()
print(f"  {_('聪明钱', 'Smart Money')}   {len(smart):2d}   {_('持仓', 'hold')} {pct(smart_pct):.2f}%  {'✅' if smart else '—'}")
if smart: print(f"  {_('近期动向', 'Recent')}:  {trend_str(smart)}")
print(f"  KOL          {len(kol):2d}   {_('持仓', 'hold')} {pct(kol_pct):.2f}%  {'✅' if kol else '—'}")
if kol:
    for h in kol:
        name = h.get('twitter_name') or h.get('name') or addr_short(h['address'])
        print(f"    · {name}  {_('持仓', 'hold')} {pct(h['amount_percentage']):.2f}%  {holding_status(h)}  {_('买/卖', 'buy/sell')}: {h.get('buy_tx_count_cur',0)}/{h.get('sell_tx_count_cur',0)}")
print(f"  {_('鲸鱼', 'Whale')}        {len(whales):2d}   {_('持仓', 'hold')} {pct(whale_pct):.2f}%  {'✅' if whales else '—'}")
if whales: print(f"  {_('近期动向', 'Recent')}:  {trend_str(whales)}")
print()
df = "✅" if diamond_pct>0.5 else ("🟡" if diamond_pct>0.3 else "⚠️")
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

# ── Entry Cost Analysis ──
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
    total_hp    = sum(h['amount_percentage'] for h in ws)
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
    print(f"  {batch_label}{rank}{_('（', '(')}{label}{_('）', ')')}  {len(ws)} {_('个钱包', 'wallets')}  {_('持仓', 'hold')} {pct(total_hp):.2f}%  {risk_flag}")
    print(f"       {mc_str}")
    print(f"       ➤ {conclusion}")
    print()
    notable = sorted([h for h in ws if h.get('balance',0)>=1 and h['amount_percentage']>=0.002],
                     key=lambda h: -h['amount_percentage'])
    if not notable:
        notable = sorted([h for h in ws if h.get('balance',0)>=1], key=lambda h: -h['amount_percentage'])[:5]
    dumping      = [h for h in notable if is_selling(h)]
    holding_firm = [h for h in notable if is_buying_only(h)]
    silent_list  = [h for h in notable if not is_active(h)]
    if dumping:
        print(f"       🚨 {_('出货中的大户', 'Selling whales')}")
        for h in dumping[:3]:
            did    = (h.get('twitter_name') or '') or addr_short(h['address'])
            roles  = wallet_roles(h)
            role_s = "["+"·".join(roles)+"]  " if roles else ""
            print(f"         · {role_s}{did}  {pct(h['amount_percentage']):.2f}%  {_('浮盈','pnl')}{(h.get('unrealized_pnl') or 0)*100:+.0f}%  {_('已卖','sold')} {h.get('sell_tx_count_cur') or 0}x  {holding_status(h)}")
        print()
    if holding_firm:
        print(f"       📈 {_('持续加仓/未出货', 'Still accumulating / not sold')}")
        for h in holding_firm[:3]:
            did    = (h.get('twitter_name') or '') or addr_short(h['address'])
            roles  = wallet_roles(h)
            role_s = "["+"·".join(roles)+"]  " if roles else ""
            print(f"         · {role_s}{did}  {pct(h['amount_percentage']):.2f}%  {_('浮盈','pnl')}{(h.get('unrealized_pnl') or 0)*100:+.0f}%  {_('已买','bought')} {h.get('buy_tx_count_cur') or 0}x")
        print()
    if silent_list:
        silent_pct_val = sum(h['amount_percentage'] for h in silent_list)
        buy0_cnt       = sum(1 for h in silent_list if h.get('buy_tx_count_cur',0)==0)
        note_str       = (_("零成本空降为主", "mostly zero-cost airdrop") if buy0_cnt>len(silent_list)//2
                          else _("持仓未动", "holding without activity"))
        print(f"       💤 {_('静默持仓', 'Silent holders')}  {len(silent_list)}  {pct(silent_pct_val):.2f}%  → {_('抛压低，', 'low pressure, ')}{note_str}")
        print()
    print()

# ── Buying Power ──
sec6 = _("💰 持仓者购买力", "💰 Holder Buying Power")
print(f"━━  {sec6}  {'━'*(54-len(sec6))}")
print()
print(f"  {_('衡量现有持仓者还有多少子弹可以加仓', 'How much ammo holders have left to add')}   {_('合计可用余额', 'Total balance')} {usd(total_buying_power)}")
print()
if zero_wallets:
    print(f"  ⚫ {_('零余额', 'Zero balance')}     {len(zero_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(zero_pct_val):.2f}%   $0    → {_('无加仓能力，可能是分仓小号', 'No buying power, likely sub-wallets')}")
if low_wallets:
    low_total = sum(native_usd(h) for h in low_wallets)
    print(f"  🟡 {_('低（<$200）', 'Low (<$200)')}   {len(low_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(low_pct_val):.2f}%   {usd(low_total)}")
if mid_wallets:
    mid_total = sum(native_usd(h) for h in mid_wallets)
    print(f"  🟠 {_('中（$200~$1200）', 'Mid ($200~$1200)')}  {len(mid_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(mid_pct_val):.2f}%   {usd(mid_total)}")
if high_wallets:
    print(f"  🔴 {_('高（$1200+）', 'High ($1200+)')}  {len(high_wallets):3d} {_('个钱包', 'wallets')}   {_('持仓', 'hold')} {pct(high_pct_val):.2f}%   {usd(high_total)}   → {_('可随时加仓', 'can add anytime')}")
print()
if high_wallets:
    print(f"  ➤ {_('高余额钱包', 'High-balance wallets')} {len(high_wallets)} {_('个持仓', 'holding')} {pct(high_pct_val):.1f}%{_('，', ', ')}{_('合计', 'total')} {usd(high_total)} {_('可随时加仓', 'ready to add')}")
if zero_wallets and zero_pct_val > 0.05:
    print(f"  ➤ {len(zero_wallets)} {_('个钱包零余额（持仓 ', 'wallets with zero balance (hold ')}{pct(zero_pct_val):.1f}%{_('）', ')')}, {_('无加仓能力，可能是分仓小号', 'no buying power, likely sub-wallets')}")
print()

# ── Chip Structure ──
sec7 = _("📊 筹码结构", "📊 Chip Structure")
print(f"━━  {sec7}  {'━'*(54-len(sec7))}")
print()
total_n = len(normal)
if total_n > 0:
    print(f"  {_('盈利', 'Profit')} {len(profit_w)} ({len(profit_w)/total_n*100:.0f}%)   {_('亏损', 'Loss')} {len(loss_w)} ({len(loss_w)/total_n*100:.0f}%)   {_('持平', 'Break-even')} {total_n-len(profit_w)-len(loss_w)}")
tf_flag = "⚠️" if len(trapped)>30 else ""
print(f"  {_('套牢盘（浮亏>20%）', 'Underwater (>20% loss)')}   {len(trapped)}   {_('持仓', 'hold')} {pct(sum(h['amount_percentage'] for h in trapped)):.2f}%  {tf_flag}")
print(f"  {_('平均持仓时长', 'Avg hold duration')}   {avg_hold_days:.1f} {_('天', 'days')}")
print()

# ── AI Advice ──
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
print(f"\n  {_('健康筹码', 'Healthy chips')} {pct(healthy_ratio):.1f}% {hf}   DEX {pct(dex_pct):.1f}% {_('不纳入评估', 'excluded from eval')}")
print()
print(f"  {_('关注以下信号，出现则考虑离场：', 'Watch for these exit signals:')}")
for sig in exit_signals:
    print(f"    · {sig}")
PYEOF
```
-->

## Field Reference

### Holder object key fields

| Field | Type | Meaning |
|-------|------|---------|
| `address` | string | Wallet address |
| `balance` | float | Current token balance |
| `amount_percentage` | float | Fraction of total supply (0–1). Multiply by 100 for %. |
| `usd_value` | float | Current USD value of holdings |
| `avg_cost` | float | Average buy price per token |
| `unrealized_pnl` | float | Unrealized PnL ratio (0.5 = +50%) |
| `unrealized_profit` | float | Unrealized PnL in USD |
| `realized_profit` | float | Realized PnL in USD |
| `buy_tx_count_cur` | int | Buy transactions since token creation |
| `sell_tx_count_cur` | int | Sell transactions since token creation |
| `sell_amount_percentage` | float | Fraction of total buys that have been sold |
| `start_holding_at` | int | Unix timestamp of first buy |
| `addr_type` | int | 0=normal wallet, 1=burn/dead, 2=DEX/pool |
| `maker_token_tags` | list | `bundler`, `rat_trader`, `sniper`, `whale`, `top_holder`, `transfer_in`, `dev_team`, `creator` |
| `tags` | list | `smart_degen`, `pump_smart`, `renowned`, `fresh_wallet`, `wash_trader`, `fomo`, `kol` |
| `native_balance` | string | Raw native token balance (SOL: lamports /1e9; EVM: wei /1e18) |
| `native_transfer` | object | `{from_address, amount, timestamp}` — how wallet was funded |
| `twitter_name` | string | Twitter handle if known |
| `exchange` | string | DEX name for pool wallets |

### Created-tokens response fields

| Field | Meaning |
|-------|---------|
| `inner_count` | Unmigrated token count |
| `open_count` | Migrated token count |
| `tokens[].market_cap` | Current market cap in USD |
| `tokens[].is_open` | true = migrated |
| `creator_ath_info.ath_mc` | All-time high MC across all created tokens |
| `creator_ath_info.ath_token` | Token address of the ATH token |
| `creator_ath_info.token_symbol` | Symbol of the ATH token |

## Rating Standard

Entry timing pressure (批次浮盈/出货) does **NOT** affect the overall rating — it only affects section display.

| Rating (ZH) | Rating (EN) | Emoji | Condition |
|-------------|-------------|-------|-----------|
| 不建议买 | Not Recommended | 🔴 | Any: rat traders >10% / largest wallet >15% / dev sock puppet |
| 谨慎参与 | Caution | ⚠️ | ≥2 of: Dev still holding / airdrop >15% / risk wallets >30% / linked >10% |
| 可轻仓   | Light Position | 🟡 | Exactly 1 of above warns |
| 正常参与 | Normal | ✅ | None of the above |

## Supported Chains

`sol`, `bsc`, `base`, `eth`, `robinhood`, `arc`, `stable`

## Notes

- `balance >= 1` threshold avoids dust false positives when identifying dev holdings
- SOL `native_balance` is in lamports (÷1e9); EVM `native_balance` is in wei (÷1e18)
- `total_supply` is estimated as the median of `balance / amount_percentage` across normal wallets
- `cur_price` is estimated as the median of `usd_value / balance` across normal wallets
- Top5 displays Twitter name when available; else `first4...last4` format
