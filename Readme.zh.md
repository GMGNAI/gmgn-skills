# gmgn-cli

> English: [Readme.md](Readme.md)

GMGN 链上操作 AI 技能套件 — Token 研究、行情数据、钱包分析和交易。

---

## 技能

| 技能 | 说明 | 参考 |
|------|------|------|
| [`/gmgn-token`](skills/gmgn-token/SKILL.md) | Token 信息、安全、池子、持有者、交易者 | [SKILL.md](skills/gmgn-token/SKILL.md) |
| [`/gmgn-market`](skills/gmgn-market/SKILL.md) | K 线行情数据、热门代币 | [SKILL.md](skills/gmgn-market/SKILL.md) |
| [`/gmgn-portfolio`](skills/gmgn-portfolio/SKILL.md) | 钱包持仓、活动、统计 | [SKILL.md](skills/gmgn-portfolio/SKILL.md) |
| [`/gmgn-swap`](skills/gmgn-swap/SKILL.md) | 兑换提交 + 订单查询 | [SKILL.md](skills/gmgn-swap/SKILL.md) |

---

## 用法示例

安装技能后，向 AI 助手直接发送自然语言指令：

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

## 安装配置

### 0. 准备工作

申请 API Key 前，需要先准备两件事：

**生成 Ed25519 密钥对**

下载并运行 [Binance Asymmetric Key Generator](https://github.com/binance/asymmetric-key-generator/releases)。申请 API Key 时需要填入**公钥**，**私钥**稍后配置到 `.env`（swap / order 接口使用）。

**获取本机出口 IP**（用于填写 IP 白名单）

```bash
curl ip.me
```

或在浏览器访问 **https://ip.me**。

### 1. 获取 API Key

申请地址：**https://gmgn.ai/ai** — 填入上一步准备好的公钥和 IP 地址。

### 2. 配置

**方式 A — 全局配置（推荐）**

创建 `~/.config/gmgn/.env`，配置一次，所有目录均生效：

```bash
mkdir -p ~/.config/gmgn
cat > ~/.config/gmgn/.env << 'EOF'
GMGN_API_KEY=your_api_key_here

# swap / order 接口额外需要（第 0 步生成的私钥）：
GMGN_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n<base64>\n-----END PRIVATE KEY-----\n"
EOF
```

**方式 B — 项目 `.env`**

```bash
cp .env.example .env
# 编辑 .env，填入实际值
```

配置加载顺序：`~/.config/gmgn/.env` → 项目 `.env`（项目级优先）。

### 3. CLI 安装

安装固定版本，避免运行时拉取未经验证的更新：

```bash
npm install -g gmgn-cli@1.0.1
```

本地开发：

```bash
npm install
npm run build
node dist/index.js <command> [options]
```

### 4. 接入 AI 工具

#### Claude Code

安装包后通过插件机制自动发现技能。

#### Cursor

技能通过 `.cursor-plugin/` 配置自动发现。

1. 完成上方步骤 1–3
2. 配置凭证：`~/.config/gmgn/.env`
3. 重启 Cursor — Agent 模式下可通过 `/gmgn-*` 命令使用技能

#### Cline

1. 完成上方步骤 1–3
2. 在 Cline 设置 → **Skills directory**：填入已安装包的 `skills/` 目录路径：
   ```bash
   echo "$(npm root -g)/gmgn-skills/skills"
   ```
3. 配置凭证：`~/.config/gmgn/.env`
4. 重启 Cline — `/gmgn-token`、`/gmgn-market`、`/gmgn-portfolio`、`/gmgn-swap` 即可使用

#### Codex CLI

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.codex/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.codex/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

详细说明：[.codex/INSTALL.md](.codex/INSTALL.md)

#### OpenCode

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.opencode/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.opencode/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

详细说明：[.opencode/INSTALL.md](.opencode/INSTALL.md)

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
market trending（取 50 条）  →  AI 多维度分析选出 top 5  →  用户确认  →  token info / token security  →  swap
```

---

## CLI 参考

完整参数说明：[docs/cli-usage.md](docs/cli-usage.md)

### Token

```bash
npx gmgn-cli token info --chain sol --address <addr>
```

### Market

```bash
npx gmgn-cli market trending \
  --chain sol \
  --interval 1h \
  --order-by volume --limit 20 \
  --filter not_risk --filter not_honeypot
```

### Portfolio

```bash
npx gmgn-cli portfolio holdings --chain sol --wallet <addr>
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

# 查询订单
npx gmgn-cli order get --chain sol --order-id <order-id>
```

---

## 支持的链

| 接口类型 | 支持的链 | 链原生货币 |
|----------|----------|-----------|
| token / market / portfolio | `sol` / `bsc` / `base` | — |
| swap / order | `sol` / `bsc` / `base` | sol: SOL、USDC · bsc: BNB、USDC · base: ETH、USDC |

---

## 输出格式

默认输出格式化 JSON。使用 `--raw` 输出单行 JSON（方便 jq 等工具处理）：

```bash
npx gmgn-cli token info --chain sol --address <addr> --raw | jq '.price'
```

---

## 安全与免责

**关于 `GMGN_PRIVATE_KEY`**

`GMGN_PRIVATE_KEY` 是用于对 GMGN OpenAPI 请求进行签名认证的**签名密钥**，不是区块链钱包私钥，不直接控制链上资产。若泄露，攻击者可以伪造经过认证的 API 请求——请立即通过 GMGN 控制台轮换密钥。

**最佳实践**

- 限制配置文件权限：`chmod 600 ~/.config/gmgn/.env`
- 不要将 `.env` 文件提交到版本控制系统，请将其加入 `.gitignore`
- 不要在日志、截图或聊天中泄露 `GMGN_API_KEY` 或 `GMGN_PRIVATE_KEY`
- 使用固定版本安装（`npm install -g gmgn-cli@1.0.1`），而非 `npx gmgn-cli`，以避免在持有凭证的环境中执行未预期的包更新

**免责声明**

使用本工具及根据其输出做出的任何财务决策，风险由用户自行承担。GMGN 对因凭证管理不当导致的任何交易损失、错误或未授权访问不承担责任。
