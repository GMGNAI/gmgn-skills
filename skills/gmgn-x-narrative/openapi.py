# gmgn-cli 适配层 —— 本包所有 GMGN 数据的唯一入口。
#
# 本仓库的硬性规则（CLAUDE.md 第一条）：所有 GMGN 数据必须经由 gmgn-cli，
# 禁止 WebFetch / curl 直连任何 gmgn 域名。所以这个模块**不发 HTTP，也完全不接触
# API Key** —— 鉴权、限流、输出消毒全部由 CLI 负责。写法沿用
# skills/gmgn-holder-analysis/analyze.py 的 run_cli()。
#
# 只用四条 read-only 命令，一条交易命令都不碰：
#     token info        代币符号、名称、项目方 X 账号
#     token holders     持有人绑定的 X 账号（每行自带 twitter_username）
#     track kol         KOL 池
#     track smartmoney  聪明钱池
#
# 注意：CLI 的输出经过 sanitize.ts 消毒（中和提示词注入框架、去掉隐藏字符）。
# 这对本包是好事 —— 我们读的正是代币元数据和社交字段，那是完全由攻击者控制的
# 输入。实测普通的 twitter_username 不受影响，能原样通过。
import json
import subprocess


class ApiError(Exception):
    pass


def run_cli(args, timeout=30, optional=False):
    try:
        r = subprocess.run(["gmgn-cli"] + args + ["--raw"],
                           capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise ApiError("gmgn-cli not found. Install it once with: "
                       "npm install -g gmgn-cli")
    except subprocess.TimeoutExpired:
        if optional:
            return None
        raise ApiError("gmgn-cli timed out after %ds" % timeout)
    if r.returncode != 0:
        if optional:
            return None
        raise ApiError((r.stderr or "").strip() or "gmgn-cli exited %d" % r.returncode)
    try:
        return json.loads(r.stdout)
    except ValueError:
        if optional:
            return None
        raise ApiError("gmgn-cli returned output that is not JSON")


def available():
    """gmgn-cli 是否可用。主流程用它给出一句人话错误，而不是抛栈。"""
    try:
        subprocess.run(["gmgn-cli", "--version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


def _rows(d):
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for k in ("list", "rank", "holders"):
            if isinstance(d.get(k), list):
                return d[k]
    return []


def token_info(ca, chain):
    return run_cli(["token", "info", "--chain", chain, "--address", ca]) or {}


def token_top_holders(ca, chain, limit=100):
    return _rows(run_cli(["token", "holders", "--chain", chain, "--address", ca,
                          "--limit", str(limit)], optional=True))


def kol(chain="bsc", limit=100):
    return _rows(run_cli(["track", "kol", "--chain", chain, "--limit", str(limit)],
                         optional=True))


def smart_money(chain="bsc", limit=100):
    return _rows(run_cli(["track", "smartmoney", "--chain", chain,
                          "--limit", str(limit)], optional=True))
