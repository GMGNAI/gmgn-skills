# gmgn-cli

> English: [Readme.md](Readme.md)

GMGN OpenAPI 命令行工具 — 支持行情查询、Token 信息、钱包资产和交易接口。

---

## 快速开始

### 0. 获取 API Key

申请地址：**https://gmgn.ai/ai**

### 1. 配置

**方式 A — 全局配置（推荐，适合 AI skill / 全局安装）**

创建 `~/.config/gmgn/.env`，配置一次，所有目录均生效：

```bash
mkdir -p ~/.config/gmgn
cat > ~/.config/gmgn/.env << 'EOF'
GMGN_API_KEY=your_api_key_here

# swap / order 接口额外需要：
GMGN_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n<base64>\n-----END PRIVATE KEY-----\n"
EOF
```

**方式 B — 项目 `.env`**

```bash
cp .env.example .env
# 编辑 .env，填入实际值
```

配置加载顺序：`~/.config/gmgn/.env` → 项目 `.env`（项目级优先）。

### 2. 运行

无需安装，直接运行：

```bash
npx gmgn-cli <command> [options]
```

全局安装后直接使用：

```bash
npm install -g gmgn-cli
gmgn-cli <command> [options]
```

本地开发：

```bash
npm install
npm run build
node dist/index.js <command> [options]
```

---

## 命令

### Token

```bash
# 基础信息（含实时价格）
npx gmgn-cli token info --chain sol --address <addr>

# 安全信息
npx gmgn-cli token security --chain sol --address <addr>

# 池子信息
npx gmgn-cli token pool --chain sol --address <addr>

# Top 持有者
npx gmgn-cli token holders --chain sol --address <addr>

# Top 交易者
npx gmgn-cli token traders --chain sol --address <addr>
```

### Market

```bash
# K 线数据
npx gmgn-cli market kline \
  --chain sol \
  --address <addr> \
  --resolution 1m \
  --from 1700000000 \
  --to 1700003600

# Trending 热门代币（按交易量排序，最近 1h，仅安全代币）
npx gmgn-cli market trending \
  --chain sol \
  --interval 1h \
  --orderby volume --limit 20 \
  --filter not_risk --filter not_honeypot
```

粒度：`1m` / `5m` / `15m` / `1h` / `4h` / `1d`

### Portfolio

```bash
# 钱包持仓（默认：limit=20, order-by=usd_value, direction=desc）
npx gmgn-cli portfolio holdings --chain sol --wallet <addr>

# 覆盖默认值
npx gmgn-cli portfolio holdings --chain sol --wallet <addr> \
  --limit 50 --order-by unrealized_profit --direction asc

# 交易活动
npx gmgn-cli portfolio activity --chain sol --wallet <addr>

# 交易统计
npx gmgn-cli portfolio stats --chain sol --wallet <addr>

# Token 余额
npx gmgn-cli portfolio token-balance \
  --chain sol --wallet <addr> --token <token_addr>
```

### Swap（需要私钥）

```bash
# 提交兑换
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --slippage 0.01

# 按比例卖出 Token（input_token 不能是货币类型）
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <token-addr> \
  --output-token <sol-or-usdc-addr> \
  --percent 50

# 查询订单
npx gmgn-cli order get --chain sol --order-id <order-id>
```

---

## 典型使用场景

**研究 Token：**
```
token info  →  token security  →  token pool  →  token holders
```

**分析钱包：**
```
portfolio holdings  →  portfolio stats  →  portfolio activity
```

**执行交易：**
```
token info（确认 Token）  →  portfolio token-balance（检查余额）  →  swap  →  order get（轮询状态）
```

**通过 Trending 发现交易机会：**
```
market trending（取 50 条，按 score 排序）  →  AI 多维度分析选出 top 5  →  用户确认  →  token info / token security  →  swap
```

---

## 输出格式

默认输出格式化 JSON。使用 `--raw` 输出单行 JSON（方便 jq 等工具处理）：

```bash
npx gmgn-cli token info --chain sol --address <addr> --raw | jq '.price'
```

---

## 支持的链

| 接口类型 | 支持的链 | 链原生货币 |
|----------|----------|-----------|
| token / market / portfolio | `sol` / `bsc` / `base` | — |
| swap / order | `sol` / `bsc` / `base` | sol: SOL、USDC · bsc: BNB、USDC · base: ETH、USDC |

---

## AI 技能

本项目在包根目录 `skills/` 提供 AI 编程助手技能文件。

| 技能 | 说明 |
|------|------|
| `/gmgn-token` | Token 信息、安全、池子、持有者、交易者 |
| `/gmgn-market` | K 线行情数据 |
| `/gmgn-portfolio` | 钱包持仓、活动、统计 |
| `/gmgn-swap` | 兑换提交 + 订单查询 |

### Claude Code

安装包后通过插件机制自动发现技能。

### Cursor

安装包后通过 `.cursor-plugin/` 配置自动发现技能。

### Codex CLI

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.codex/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.codex/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

详细说明：[.codex/INSTALL.md](.codex/INSTALL.md)

### OpenCode

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.opencode/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.opencode/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

详细说明：[.opencode/INSTALL.md](.opencode/INSTALL.md)

### Cline

安装本包后，在 Cline 设置中将 `skills/` 配置为技能目录即可。

### 用户使用示例

以下是典型的 AI / MCP 接入方向本服务发起调用时的自然语言 prompt 示例：

```
buy 0.1 SOL of <token_address>
sell 50% of <token_address> on BSC
check order status <order_id>
is <token_address> safe to buy on solana?
show top holders of <token_address>
show my wallet holdings on SOL
query token details for 0x1234...
show trading stats for wallet <wallet_address> on BSC
```

---

## 安全与免责

- 不要将 `.env` 文件或私钥提交到版本控制系统，请将其加入 `.gitignore`
- 请妥善保管 `GMGN_API_KEY` 和私钥，不要在日志、截图或聊天中泄露
- swap/order 使用的私钥必须与绑定该 API Key 的钱包一致
- **使用本工具及根据其输出做出的任何财务决策，风险由用户自行承担。GMGN 对因凭证管理不当导致的任何交易损失、错误或未授权访问不承担责任。**

---

## 详细文档

完整参数说明：[docs/cli-usage.md](docs/cli-usage.md)
