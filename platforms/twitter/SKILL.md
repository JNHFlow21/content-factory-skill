---
name: content-factory-twitter
description: 将公众号文章推送到 Twitter/X 草稿箱（X Articles 长文）。当用户说"发 Twitter"/"推 X"/"post to X"/"发推"时调用此 Skill。
version: 1.0.0
---

# Content Factory — Twitter/X 推送模块

> 本模块将 content-factory 生成的公众号文章（Markdown）转换为 X Article HTML，并推送到 Twitter/X 草稿箱。
> 触发词："发 Twitter" / "推 X" / "post to X" / "发推"
> 前提：Chrome 已登录 X 账号（手动登录一次后 session 持久化）

---

## 与 baoyu-post-to-x 的关系

本模块 fork 自 [JimLiu/baoyu-post-to-x](https://github.com/JimLiu/baoyu-skills)，针对 content-factory 的场景做了以下适配：
- 接收 article.md（公众号排版后的 Markdown）作为输入
- 自动提取标题、封面图、正文
- 默认草稿模式（submit=false），浏览器保持打开等用户审核后点发布

---

## 核心脚本

所有脚本位于 `scripts/` 子目录。

**脚本说明**：
| 脚本 | 用途 |
|------|------|
| `scripts/x-article.ts` | X Article 长文发布（核心） |
| `scripts/md-to-xhtml.ts` | Markdown → X Article HTML 转换 |
| `scripts/x-browser.ts` | 常规推文（text + image） |
| `scripts/x-quote.ts` | 引用推文 |
| `scripts/x-video.ts` | 视频推文 |
| `scripts/x-utils.ts` | 共享工具（Chrome CDP 连接） |
| `scripts/check-paste-permissions.ts` | 环境检查 |

---

## 完整推送流程（X Article 草稿）

**前置条件**：
- `bun` 已安装（运行 `brew install bun` 或 `npm install -g bun`）
- Chrome 已登录 X（手动登录一次，session 持久化）
- 依赖已安装：`cd scripts && bun install`

**Step 1：安装依赖**

```bash
cd "$HOME/.claude/skills/content-factory/platforms/twitter/scripts"
bun install 2>/dev/null || npm install 2>/dev/null || true
```

**Step 2：生成 X Article HTML**

```bash
ARTICLE_MD="${CONTENT_FACTORY_OUTPUT}/dagong-chuangye-siwei-chaoyue/article.md"
X_HTML="/tmp/x-article.html"

bun scripts/md-to-xhtml.ts \
  --input "$ARTICLE_MD" \
  --output "$X_HTML"
```

**Step 3：推送草稿箱**

```bash
ARTICLE_TITLE="打工人永远攒不下钱，创业者用钱买时间"
COVER_PNG="${CONTENT_FACTORY_OUTPUT}/dagong-chuangye-siwei-chaoyue/cover.png"

bun scripts/x-article.ts \
  --title "$ARTICLE_TITLE" \
  --html "$X_HTML" \
  --cover "$COVER_PNG" \
  --submit false
```

**Step 4：人工审核**

Chrome 浏览器自动打开，X Article 草稿已填写完毕。
→ 用户在浏览器中检查内容 → 点击 "Publish" 发布

---

## X Article HTML 转换说明（md-to-xhtml.ts）

`md-to-xhtml.ts` 是 `baoyu-post-to-x` 的 `md-to-html.ts`，做了以下处理：

- 解析 YAML frontmatter 中的 `title` 和 `cover_image`（如果有）
- 下载远程 HTTPS 图片到临时目录
- 解析本地图片路径
- 使用 `marked` 库转换 Markdown：
  - H1 标题单独提取（标题字段填入，不出现在正文）
  - H2/H3 保留为小标题
  - 段落、引用、代码块正常转换
  - 图片替换为 `XIMGPH_N` 占位符（供 x-article.ts 后续逐张插入）
  - 链接添加 `rel="noopener noreferrer nofollow"`
- 输出：`{ title, coverImage, contentImages[], html, totalBlocks }`

---

## 环境检查

首次使用前建议运行：

```bash
bun scripts/check-paste-permissions.ts
```

常见问题及修复：

| 检查项 | 修复方式 |
|--------|---------|
| Chrome 未安装 | 安装 Google Chrome |
| Bun 未安装 | `brew install oven-sh/bun/bun`（macOS）|
| Accessibility 权限（macOS）| 系统设置 → 隐私与安全性 → 辅助功能 → 允许终端 |
| Chrome debug 端口被占用 | `pkill -f "Chrome.*remote-debugging-port"` 后重试 |

---

## 草稿审核流程（重要）

- `--submit false`（默认）：浏览器保持打开，用户手动审核后点 Publish
- `--submit true`：自动点击 Publish（**不推荐**，AI 生成内容需人工审核）

---

## Twitter 配置

默认复用 baoyu 的 Chrome profile 目录：
`~/.config/baoyu-skills/chrome-profile/`（Linux/macOS）

如需指定自定义 Chrome profile：
```bash
bun scripts/x-article.ts ... --profile /path/to/custom-profile
```

---

## 与 content-factory 主流程的集成

在 content-factory SKILL.md 中，本模块通过以下方式被调用：

```
用户说"发 Twitter"/"推 X" → Step 8X 路由到本模块
→ 执行 md-to-xhtml.ts（生成 X Article HTML）
→ 执行 x-article.ts（推送草稿箱）
→ 人工审核 + Publish
→ Step 8.5X 记录到 history_twitter.yaml
```

---

## 注意事项

- X Article 需要 X Premium 订阅（普通账号只能发普通 tweet）
- 普通推文（280字）限制下，公众号长文不适合——请用 X Article 模式
- 图片上传后 X 会验证图片格式，建议使用 PNG/JPG
- Chrome 登录 session 持久化后，后续运行无需重复登录
