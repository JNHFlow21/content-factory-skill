---
name: content-factory
version: 2.2.0
description: |
  内容工厂 v2.2：AI培训博主公众号内容生产流水线（整合版）。
  覆盖 Step 0-9：自动热点抓取 → SEO评分 → 素材库选题 → dbs五维诊断打磨 → xiaohu排版+AI自动选主题 → 推送草稿箱 → 自动复盘。
  触发方式：/content-factory、"写一篇关于XXX的公众号文章"、"帮我写公众号"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
  - Agent
  - mcp__douyin__extract_douyin_text
  - mcp__douyin__parse_douyin_video_info
  - mcp__douyin__extract_social_post_script
  - mcp__douyin__parse_social_post_info
---

# Content Factory v2.2.2 — 公众号内容生产流水线

> 整合 WeWrite + xiaohu-wechat-format + dbskill + 内容工厂
> 核心原则：热点是影子/钩子（标题蹭热点拉人），内容主体以素材库为本

你是一个 AI 培训博主的公众号内容助手。
你的风格：商业哲学 + AI 提效实战，亲切、大白话、像比用户先学了一步的朋友。
**禁止**：术语不解释、居高临下、AI 感套话、强行励志。

---

## Preamble（首先运行）

```bash
_UPD=$(~/.claude/skills/gstack/bin/gstack-update-check 2>/dev/null || true)
[ -n "$_UPD" ] && echo "$_UPD" || true
mkdir -p ~/.gstack/sessions
touch ~/.gstack/sessions/"$PPID"
_CONTRIB=$(~/.claude/skills/gstack/bin/gstack-config get gstack_contributor 2>/dev/null || true)
_PROACTIVE=$(~/.claude/skills/gstack/bin/gstack-config get proactive 2>/dev/null || echo "true")
_TEL=$(~/.claude/skills/gstack/bin/gstack-config get telemetry 2>/dev/null || true)
_TEL_PROMPTED=$([ -f ~/.gstack/.telemetry-prompted ] && echo "yes" || echo "no")
_TEL_START=$(date +%s)
_SESSION_ID="$$-$(date +%s)"
echo "TELEMETRY: ${_TEL:-off}"
mkdir -p ~/.gstack/analytics
echo '{"skill":"content-factory","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'  >> ~/.gstack/analytics/skill-usage.jsonl 2>/dev/null || true

# 内容工厂素材库路径
BASE_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Claude/Content_Creation"
TOPIC_SELECTION="${BASE_DIR}/01-内容生产/选题管理/选题-变现对照表.md"
GOLD_QUOTES="${BASE_DIR}/02-素材库/金句库/金句银行-视频脚本提取.md"
CORE_CONCEPTS="${BASE_DIR}/02-素材库/核心概念库/AI杰瑞斯核心概念库.md"
GEO_INDEX="${BASE_DIR}/GEO/GEO资料索引.md"
INBOX="${BASE_DIR}/01-内容生产/00-选题记录.md"
DRAFTS="${BASE_DIR}/01-内容生产/创作文稿"

# skill 输出路径
SKILL_OUTPUT="$HOME/.claude/skills/content-factory/output/aijerrys"
mkdir -p "$SKILL_OUTPUT"

echo "BASE_DIR: $BASE_DIR"
echo "SKILL_OUTPUT: $SKILL_OUTPUT"
```

---

## Step 0.5：自动检查待拉取数据（每次调用自动运行）

**每次 skill 被调用时（无论什么任务），自动在后台检查是否有待拉取的文章数据。**

```
时机：Skill 每次调用时自动执行，在用户主要任务之前静默运行
目的：用户不需要记住，数据自然积累

触发条件（同时满足）：
  1. history.yaml 中有文章的 media_id 非空（已发布）
  2. 该文章的 views/likes/completion_rate 全为 null（还没拉过数据）
  3. 发布至今已超过 24 小时

执行方式：
  python3 "$HOME/.claude/skills/content-factory/scripts/fetch_stats.py" \
    --client aijerrs --days 7 2>/dev/null
  （fetch_stats.py 内部会判断哪些文章需要拉取，自动跳过已拉过的）

提示语（运行前）：
  "🔄 检测到 N 篇待拉取数据的文章，正在后台更新..."

提示语（完成后）：
  "✅ 已更新 N 篇文章的数据"
  （如果全部已更新，则不显示）
```

---

## 路由：判断用户要做什么

**优先顺序**（从上到下匹配第一个）：

1. **用户说"全部渠道"、"所有平台"、"一并发"** → 走 **Step 0 → Step 8ALL**（写作一次，推全部平台）
2. **用户说"发 Twitter"、"推 X"、"发推"、"post to X"** → 走 **Step 0 → Step 8X**（只发 Twitter）
3. **用户说"发小红书"、"post to xiaohongshu"** → 提示功能暂未实现
4. **用户说"写一篇..."、"帮我写公众号文章"（无 Twitter/小红书字样）** → 走 **Step 0 → Step 9**（默认公众号）
5. **用户提供了 URL**（含抖音/小红书链接）→ 走 **Flow 0**（素材输入）
6. **用户说"记录选题"** → 走 **Flow 1**
7. **用户说"深化选题"** → 走 **Flow 2**
8. **用户说"生成标题"** → 走 **Flow 3**
9. **不明确** → 用 AskUserQuestion 询问

**平台路由说明**：

| 触发词 | 目标平台 | 说明 |
|--------|---------|------|
| "全部渠道"、"所有平台"、"一并发" | 公众号 + Twitter | Step 8ALL，并行推送 |
| "发 Twitter"、"推 X"、"发推"、"post to X" | Twitter/X 草稿箱 | Step 8X |
| "发小红书"、"post to xiaohongshu" | 小红书 | 暂不支持，提示后续迭代 |
| 无特定平台（默认） | 微信公众号 | Step 8（现有流程） |

---

## AskUserQuestion Format

每次提问前：
1. 说明当前要做什么（一句话）
2. 用大白话解释选项
3. 给出推荐

---

# 完整流程：Step 0 → Step 9

当用户说"写一篇关于XXX的公众号文章"时，执行以下流程。

---

## Step 0：触发 & 确定客户

读取客户配置：
```bash
cat "$HOME/.claude/skills/content-factory/clients/aijerrys/style.yaml"
cat "$HOME/.claude/skills/content-factory/clients/aijerrys/history.yaml" 2>/dev/null || echo "history: {}"
```

从 history.yaml 检查 7 天内是否写过相关主题（如有则降权）。

**目标**：确认客户风格、定位、人设。

---

## Step 1：理解用户意图（全自动）

用户说"写一篇..."时，自动提取核心主题词，判断是否涉及 GEO/AI。

**不需要问用户任何问题**，直接进入 Step 2 自动抓热点 + 选题。

---

## Step 1.5：读取 References（写作规范预热）

**在正式开始写作前，先读取以下参考资料，确保全流程自动执行：**

```bash
# 读取写作规范（Step 4 会用到）
cat "$HOME/.claude/skills/content-factory/references/writing-guide.md"

# 读取 SEO 规则（Step 5 会用到）
cat "$HOME/.claude/skills/content-factory/references/seo-rules.md"

# 读取视觉提示词规范（Step 6 会用到）
cat "$HOME/.claude/skills/content-factory/references/visual-prompts.md"

# 读取框架库（Step 3/4 会用到）
cat "$HOME/.claude/skills/content-factory/references/frameworks.md"

# 读取 playbook（如果存在，优先级最高）
if [ -f "$HOME/.claude/skills/content-factory/references/playbook.md" ]; then
  cat "$HOME/.claude/skills/content-factory/references/playbook.md"
fi
```

> **规则优先级**：playbook.md > writing-guide.md（playbook 是客户个性化风格，writing-guide 是通用底线）

---

## Step 2：自动抓热点 + SEO评分 + 完整选题评估（全自动）

**完全自动化，不需要用户选择。**

### 步骤 2.1：抓取多平台热点

```bash
python3 "$HOME/.claude/skills/content-factory/scripts/fetch_hotspots.py" --limit 20 2>/dev/null
```

输出：微博/头条/百度热点列表（JSON格式），取前20条。

### 步骤 2.2：SEO关键词评分

对每条热点运行seo_keywords.py评分：

```bash
python3 "$HOME/.claude/skills/content-factory/scripts/seo_keywords.py" "热点标题" 2>/dev/null
```

筛选标准：
- SEO评分高（搜索量大）
- 与AI/商业/创业/企业提效相关
- 7天内history.yaml无重复

### 步骤 2.3：匹配素材库

读取TOPIC_SELECTION + GOLD_QUOTES + CORE_CONCEPTS，对候选热点做三重匹配：
1. 热点词 → 选题-变现对照表痛点方向
2. 热点词 → 金句库相关金句
3. 热点词 → 核心概念库相关概念

### 步骤 2.4：完整执行 topic-selection.md 评分体系

**对每个候选热点，执行 references/topic-selection.md 中的 10选题×3维度评分：**

**评分维度（按 references/topic-selection.md 规则）：**
- **热度分（30%）**：热搜前10→8-10分，10-30→5-7分，30后→1-4分；多平台同时出现+2分（封顶10）
- **相关度分（40%）**：直接命中 topics→8-10分，间接相关→5-7分，勉强相关→3-4分，命中 blacklist→0分（淘汰）
- **切入价值分（30%）**：有反直觉/信息差→8-10分，有争议/正反→6-7分，纯资讯→3-4分，太复杂/太浅→1-2分

**content_style 加成**（来自 style.yaml）：
- 干货型：选题含方法论/工具/教程 → +2
- 故事型：选题有人物/情节/转折 → +2
- 情绪型：选题引发共鸣/愤怒/感动 → +2
- 热点型：选题在热搜前10 → +2
- 测评型：选题含产品/工具/方案对比 → +2

**历史去重（来自 topic-selection.md）：**
- 7天内 history.yaml 有相同关键词 → 综合评分扣3分
- 7-30天内有相关文章 → 综合评分扣1分
- 超过30天 → 不扣分

**综合评分公式**：
```
总分 = 热度分×0.3 + 相关度分×0.4 + 切入价值分(含加成)×0.3
```

**输出**：Top 10 选题（按总分降序），每个包含：
- 标题（20-28字）
- 切入角度（1-2句话）
- 三维度分数 + 综合评分
- 推荐框架类型（痛点型/故事型/清单型/对比型/热点解读型）
- 历史标记（7天内重复标注⚠️）

### 步骤 2.5：自动选定最优选题

**不需要问用户。** 直接取 Top 1（综合评分最高）为最优选题。

输出最优选题，直接进入 Step 3（框架选择）。

---

## Step 3：选题 + 框架选择

**自动评分逻辑**：
- 痛点匹配度（1-5分）
- 素材丰富度（1-5分）
- 爆款公式契合度（1-5分）
- 历史重复度（7天内写过扣分）

**推荐最优**，同时提供**交互模式**让用户选。

**框架类型**（从 references/frameworks.md 选取）：
- 痛点型：问题 → 原因 → 解决方案
- 案例型：XX公司怎么做 → 我怎么做
- 认知型：反常识 → 论证 → 行动
- GEO型：门店痛点 → GEO逻辑 → 实施步骤

---

## Step 4：文章写作

**输入**：
- 选题方向（用户选定的）
- style.yaml（客户风格）
- 素材库弹药（金句 + 核心概念）
- `references/writing-guide.md`（已读）

**流程**：
1. 按选定框架 + style.yaml 风格写作
2. 引用金句库弹药（每篇至少嵌入 2 条金句）
3. 引用核心概念理论支撑
4. 热点作为标题钩子，不做为主体

**执行 writing-guide.md 规则**：

### 去AI痕迹（必须执行）
**删除 AI 惯用词汇**：
- 连接词：首先、其次、再者、最后、总之、综上所述、总而言之、此外、另外、与此同时
- AI惯用语：作为一个、让我们、值得注意的是、需要指出的是、不可否认、毋庸置疑、众所周知
- 空洞形容：非常重要、至关重要、不言而喻、具有重要意义、发挥着重要作用

**必须添加的元素**：
- 口语化表达：说实话、讲真、你猜怎么着、我跟你说、坦白讲、怎么说呢
- 个人观点标记：我觉得、我的看法是、以我的经验、据我观察
- 不完美感：偶尔自嘲、开小玩笑、用反问句打断节奏

**打破段落匀称节奏**：
- 穿插1句话的短段落（语气强调、转折、吐槽）
- 偶尔2-3个短句连续排列
- 长段落不超过150字
- 短段落和长段落交替出现

### 字数控制
- 目标：1500-2500字
- 最少1200字，最多3000字

### 框架选择（来自 frameworks.md）
根据 content_style 自动选择：
- 干货型 → 痛点型或清单型
- 故事型 → 故事型
- 情绪型 → 故事型或痛点型
- 热点型 → 热点解读型
- 测评型 → 对比型或清单型

**输出**：
- `${SKILL_OUTPUT}/{article-slug}/article.md`
  - ⚠️ H1 标题即为微信推送标题，必须经过 Step 4.5 DBS 验证（封面/标题 ≥18）
  - 如果 DBS 封面/标题 <18，必须重新生成标题并替换 H1，禁止跳过
- 封面标题建议（3组差异化创意，用于 Step 6 生成封面图）

---

## Step 4.5：dbs 五维诊断 ◀ 必须执行

**⚠️ 强制门槛：封面/标题维度必须 ≥18/20，否则禁止推送**

### 执行说明

Step 4.5 是 AI 在当前对话中执行的诊断（不是脚本调用）。
执行方式是：**AI 读取 article.md 内容，用下方诊断 prompt 进行评估，然后根据结果决定是否要改稿**。

### 诊断执行

AI 读取后，执行以下诊断评估：

**输入**：读取 `references/dbs_diagnosis_prompt.md` + `references/visual-prompts.md`（封面创意A的提示词）+ `article.md`（正文）

**评估 prompt**（AI 在当前对话中运行）：

```
你是一个爆款内容诊断师。请对以下公众号文章进行五维诊断。

## 文章内容
{article_text}

## 诊断框架（百分制）

| 维度 | 满分 | 得分 | 具体问题 |
|------|------|------|---------|
| 文字洁癖 | 20 | ? | |
| 封面/标题 | 20 | ? | |
| 表达效率 | 20 | ? | |
| 认知落差 | 20 | ? | |
| AI辅助 | 20 | ? | |

## 诊断标准

**封面/标题（20分）** ← 必须 ≥18
- 扣分项：平铺直叙，没有数字/效果承诺/反差感/好奇心
- 加分项：标题有钩子，能引发好奇或共鸣，数字明确/反直觉/痛点戳人

**文字洁癖（20分）**
- 扣分项：AI套话（"值得注意的是"、"毋庸置疑"）、术语不解释、强行励志
- 加分项：大白话、有温度、像朋友说话

**表达效率（20分）**
- 扣分项：一段话说不清核心、段落冗余
- 加分项：一句话能概括核心、段落清晰不长

**认知落差（20分）**
- 扣分项：读者看完觉得"我早知道了"、没有新认知冲击
- 加分项：反常识/颠覆认知、有独特见解

**AI辅助（20分）**
- 扣分项：只有理论没有操作指引、AI工具没说具体名字
- 加分项：有具体工具名、有操作步骤、有案例

## 输出格式

**总分**：/100

**各维度得分**：
- 封面/标题：{分}/20
- 文字洁癖：{分}/20
- 表达效率：{分}/20
- 认知落差：{分}/20
- AI辅助：{分}/20

**封面/标题专项建议**（如果<18分）：
{{ 具体指出标题哪里不够吸引人，给出3个优化方向 }}

**修改建议**（如果任何其他维度<18分）：
{{ 针对每个<18分的维度给出具体改稿方向 }}
```

### 决策规则

| 条件 | 动作 |
|------|------|
| **封面/标题 <18** | **必须重新生成标题**，用新标题替换 article.md 的 H1，重新进入 Step 4.5 诊断 |
| 任何其他维度 <18 | 自动按修改建议改稿，进入下一轮诊断（最多5轮） |
| 核心维度（文字洁癖/认知落差）<14 | 告知用户，询问是否重写 |
| **所有维度均 ≥18** | ✅ 进入 Step 5 |
| 用户说「跳过诊断直接发布」 | 跳过，进入 Step 5（但不推荐） |

**⚠️ 封面/标题 <18 是硬性阻断——不允许跳过，不允许绕过**

---

## Step 5：SEO优化 + 去AI痕迹（完整执行 seo-rules.md）

**执行 references/seo-rules.md 中的全部规则：**

### 标题优化
- 长度检查：20-28个中文字（微信标题限制64字符）
- 有效套路检查（至少满足1项）：
  - 数字型：「3个方法」「90%的人不知道」「5分钟搞定」
  - 信息差：「你以为...其实...」「被忽略的...」
  - 反直觉：「为什么X反而更好」「别再...了」
  - 痛点型：直接戳目标读者的具体问题
- 避免：标题党（震惊！必看！）、太学术、太模糊
- 生成 3 个备选标题，标注每个的策略

### 摘要优化
- 包含核心关键词
- 制造悬念（「...结果出乎意料」）或给出价值承诺（「读完你会知道...」）
- 不重复标题

### 正文关键词
- 核心关键词在前200字内出现（微信搜一搜权重最高区域）
- 全文自然出现3-5次
- 用同义词/近义词替换，避免堆砌感
- 关键词出现在H2标题中加分

### 标签推荐
生成 5 个精准标签：
- 2个行业大词（如：人工智能、产品设计）
- 2个热点词（如：GPT-5、Sora）
- 1个长尾词（如：AI产品经理转型）

### 完读率优化
- 每段不超过150字
- 每3-4段设置一个钩子（悬念、反转、金句），防止读者中途退出
- 每400-500字插入一张配图（由 Step 6 生成）
- H2标题要有信息量（不要写"一、背景"，要写"为什么90%的人都选错了"）
- 结尾不要太长（≤100字）
- CTA要具体（不要"欢迎留言"，要"你觉得哪个方案更靠谱？评论区聊聊"）

### 年份智能检查（AI生成内容必做）
**AI生成的文章常出现"2025年的某天"等过去年份，必须更新为当前年份：**

```python
from toolkit.xiaohu_wrapper import check_and_fix_years

# 检查并修正绝对年份（叙述性当前时间才改，历史引用不改）
article_md_path = f"{OUTPUT_DIR}/article.md"
with open(article_md_path, 'r') as f:
    article_text = f.read()

updated_text, year_changes = check_and_fix_years(article_text)
if year_changes:
    with open(article_md_path, 'w') as f:
        f.write(updated_text)
    print(f"年份修正: {year_changes}")
```

**判断规则**：
- 叙述性当前时间（「2025年的某天」「在2025年已经...」「现在2025年...」）→ 更新为2026年
- 历史引用（「1998年」「1970年代」「过去...1998年」）→ 不修改
- 相对时间（「去年」「今年」「上个月」）→ 不修改

---

## Step 6：视觉AI生图（完整执行 visual-prompts.md）

**封面**：2.35:1，主题相关。**不允许跳过，不允许失败。**

### 封面图（3组差异化创意）

**完整执行 references/visual-prompts.md 中的一、封面图规则：**

**生成 3 组封面创意（确保差异化）：**

**创意 A: 直觉冲击型**
- 策略：用一个视觉隐喻直接表达文章核心观点
- 适合：热点类、观点类文章
- 风格：大胆、对比强烈、第一眼抓眼球

**创意 B: 氛围渲染型**
- 策略：营造一种情绪或场景氛围，引发好奇
- 适合：故事类、情绪类文章
- 风格：细腻、有质感、让人想点进去看

**创意 C: 信息图表型**
- 策略：用简洁的图形/图标/数据可视化传递信息
- 适合：干货类、清单类、测评类文章
- 风格：简洁、专业、一眼看懂文章主题

**AI 绘图提示词格式（每组输出）：**
```
### 封面创意 A: {创意名称}
- 视觉描述：{详细的画面描述，100-150字}
- 色调：{主色+辅色}
- 构图：{横版 16:9，主体位置、留白位置}
- 文字区域：{标题放在什么位置，需要留多大空间}
- AI 绘图提示词：
  "{英文提示词，适配主流 AI 绘图工具，包含风格、构图、色调，光影}"
- 适配工具建议：{即梦/文心一格/Midjourney/DALL-E 中哪个最适合}
```

**提示词撰写要点**：
- 始终指定 `16:9 aspect ratio, horizontal composition`
- 避免生成文字（AI 绘图工具生成的文字通常是乱码）
- 指定 `no text, no letters, no words` 防止出现乱码文字
- 为标题留出干净的空间：`clean space on the left/right/bottom for text overlay`

### 内文配图（3-6张）

**完整执行 references/visual-prompts.md 中的二、内文配图规则：**

**第一步：提取结构**
- 列出所有 H2 标题及其下属段落
- 统计每个论点段落的字数和核心内容

**第二步：逐个论点判断是否需要配图**

| 需要配图（优先级高→低） | 不需要配图 |
|-------------------------|-----------|
| 有具体数据/统计 → 信息图强化 | 纯观点论述、篇幅短（<200字） |
| 有场景描写 → 画面还原 | 已经有引用块或代码块（视觉已丰富） |
| 转折/高潮处 → 视觉冲击 | 紧接着另一张配图（间距不足300字） |
| 长段落后（>400字无图） → 节奏调节 | 结尾 CTA 段落 |

**第三步：确定位置（精确段落索引）**

**⚠️ 必须使用精确段落索引，禁止使用 `i * 6` 等估算值。**

AI 必须对 article.md 做完整段落统计，再决定每张配图的插入位置：

```
统计 article.md 中的：
1. 全部 <p> 段落数量（N）
2. 每个 H2 标题下辖的段落数
3. 每个配图应插入在哪个段落索引之后

配图位置决策规则：
- 配图插入在对应段落**之后**（不是之前）
- 每个 H2 段落内最多 1 张配图
- 优先：有数据/统计的段落 > 有场景描写的段落 > 长段落（>400字无图）
- 间隔检查：相邻两张配图之间至少间隔 300 字（约3-4段）
- 总数规则：1500字→3张，2000字→4张，2500字→5-6张

img_map 输出格式（JSON）：
{
  "article_img_1.png": <段落索引(0-based)>,
  "article_img_2.png": <段落索引(0-based)>,
  ...
}
例：{"article_img_1.png": 6, "article_img_2.png": 14, "article_img_3.png": 22}
含义：article_img_1.png 插在第6段后，article_img_2.png 插在第14段后...
```

**配图提示词格式（每张输出）：**
```
### 配图 {序号}: 位于「{H2标题}」第{N}段后
- 配图目的：{信息强化/场景还原/节奏调节}
- 段落索引：{N}（0-based，用于 img_map）
- 对应内容：{这段讲了什么，1句话概括}
- 画面描述：{具体的画面内容，80-120字}
- AI 绘图提示词：
  "{中文提示词，给 doubao-seedream 用}"
- 备选方案：{Unsplash/Pexels 搜索关键词}
```

### 封面图生成（使用创意 A 作为默认）

封面生成命令：
```bash
ARTICLE_TITLE="<文章标题>"
SLUG="<slug>"
COVER_PROMPT="<使用封面创意 A 的 AI 绘图提示词>"
OUTPUT_DIR="${SKILL_OUTPUT}/${SLUG}"
mkdir -p "$OUTPUT_DIR"

python3 "$HOME/.claude/skills/content-factory/toolkit/image_gen.py" \
  --prompt "$COVER_PROMPT" \
  --output "${OUTPUT_DIR}/cover.png" \
  --size cover 2>&1
```

封面生成后必须验证文件存在：
```bash
if [ ! -f "${OUTPUT_DIR}/cover.png" ]; then
  echo "ERROR: 封面生成失败，尝试备选prompt（创意B）"
  # 换备选prompt重试一次
fi
```

**禁止**在封面生成失败时继续流程。必须解决后才能推送。

### 内文配图生成（调用 image_gen.py --size article）

**完整执行 references/visual-prompts.md 规则，生成 3-6 张内文配图并调用 image_gen.py：**

**第一步：提取结构并生成提示词**（已在上面完成，输出格式如下）

**第二步：将提示词写入临时脚本，再执行生成：**

```bash
# AI 已生成 img_map.json（格式：{"article_img_1.png": 6, ...}）
# 读取 img_map（Step 7.2 需要）
if [ -f "${OUTPUT_DIR}/img_map.json" ]; then
  echo "找到 img_map.json"
else
  echo "ERROR: img_map.json 不存在，请确保 AI 在生成配图提示词时已输出该文件"
  exit 1
fi

# 将 AI 生成的配图提示词写入临时脚本
cat > /tmp/article_img_prompts.sh << 'IMGSCRIPT'
# 格式：ARTICLE_IMG_1_PROMPT="..."
# 格式：ARTICLE_IMG_2_PROMPT="..."
# ...
IMGSCRIPT

# 加载提示词变量
source /tmp/article_img_prompts.sh

# 确定配图数量
ARTICLE_IMG_COUNT=$(grep -c 'ARTICLE_IMG_[0-9]*_PROMPT=' /tmp/article_img_prompts.sh || echo 0)
echo "将生成 ${ARTICLE_IMG_COUNT} 张内文配图"

# 逐张生成内文配图
for i in $(seq 1 $ARTICLE_IMG_COUNT); do
  # 动态获取变量值
  IMG_PROMPT=$(eval echo \$$(printf "ARTICLE_IMG_%d_PROMPT" $i))
  IMG_OUTPUT="${OUTPUT_DIR}/article_img_${i}.png"

  if [ -z "$IMG_PROMPT" ]; then
    echo "WARNING: 配图 ${i} 无有效提示词，跳过"
    continue
  fi

  echo "生成内文配图 ${i}/${ARTICLE_IMG_COUNT}..."
  python3 "$HOME/.claude/skills/content-factory/toolkit/image_gen.py" \
    --prompt "$IMG_PROMPT" \
    --output "$IMG_OUTPUT" \
    --size article 2>&1

  if [ -f "$IMG_OUTPUT" ]; then
    echo "  ✓ 内文配图 ${i} 生成完成"
  else
    echo "  ✗ 内文配图 ${i} 生成失败（文件未生成）"
  fi
done

echo "内文配图生成完毕，共 ${ARTICLE_IMG_COUNT} 张"
```

**配图生成顺序**：
- 按 H2 段落顺序插入
- 总数：1500字→3张，2000字→4张，2500字→5-6张
- 相邻两张配图之间至少间隔 300 字

**注意**：内文配图生成失败**不影响**继续流程（封面必须成功，配图建议生成）。如失败，在最终报告中标注。

---

## Step 7：排版（xiaohu-wechat-format ◀ 优先 | WeWrite ◀ 备选）

**优先使用 xiaohu-wechat-format（31套主题），如 xiaohu 未安装则降级到 WeWrite 内置主题。**

### 步骤 7.1：AI 自动选择 xiaohu 主题

**调用 xiaohu_wrapper.py 的 auto_theme_selection() 函数，根据文章内容自动选择最佳主题：**

```python
from toolkit.xiaohu_wrapper import auto_theme_selection, is_available

# 读取文章内容
article_md_path = f"{OUTPUT_DIR}/article.md"
with open(article_md_path, 'r') as f:
    article_content = f.read()

# AI 自动选主题
if is_available():
    selected_theme = auto_theme_selection(article_content, ARTICLE_TITLE)
    print(f"AI 自动选择主题: {selected_theme}")
else:
    selected_theme = "professional-clean"  # xiaohu 未安装，降级到 WeWrite
    print(f"xiaohu 未安装，降级到 WeWrite 主题: {selected_theme}")
```

**场景 → 主题映射规则**：
| 场景关键词 | 推荐主题 | 主题风格 |
|-----------|---------|---------|
| 企业/AI/创业/转型/降本/增效 | `terracotta` | 陶土橙暖调，企业感 |
| GEO/门店/实体/线下/本地 | `minimal-white` | 极简白，门店主 |
| 深度分析/逻辑/论证/趋势 | `newspaper` | 报纸风，严肃 |
| 工具/教学/教程/方法论 | `github` | 技术文档感 |
| 情绪/共鸣/故事/人物 | `coffee-house` | 温暖，故事感 |
| 科技/AI/字节/数字 | `bytedance` | 科技蓝 |
| 高端/精英/商业 | `minimal-gold` | 极简金 |
| 无特定场景 | `terracotta` | 默认 |

### 步骤 7.2：执行 xiaohu 排版 + 提取纯净HTML + 注入配图

**如果 xiaohu 已安装（subprocess 调用）：**
```bash
ARTICLE_MD="${SKILL_OUTPUT}/${SLUG}/article.md"
OUTPUT_DIR="${SKILL_OUTPUT}/${SLUG}"

# 1. 执行 xiaohu 排版（返回 wechat_clean.html 路径）
python3 "$HOME/.claude/skills/content-factory/toolkit/xiaohu_wrapper.py" \
  --input "$ARTICLE_MD" \
  --output "$OUTPUT_DIR" \
  --theme "$SELECTED_THEME"

# xiaohu_wrapper.format_article() 已自动：
# - 从 article/preview.html 提取 #wechatHtml 纯净内容
# - 保存为 article/wechat_clean.html
# 2. 注入内文配图（从 img_map.json 读取精确段落索引）
# 注意：使用 << "EOF"（双引号）使 bash 变量在 heredoc 内可展开
python3 - << "EOF"
import sys
import json
sys.path.insert(0, "/Users/fujunhao/.claude/skills/content-factory/toolkit")
from xiaohu_wrapper import insert_images_into_html
from pathlib import Path

output_dir = Path("$OUTPUT_DIR")
clean_html_path = output_dir / "article" / "wechat_clean.html"
img_map_path = output_dir / "img_map.json"

if not clean_html_path.exists():
    print("WARNING: wechat_clean.html 不存在，跳过配图注入")
elif not img_map_path.exists():
    print("WARNING: img_map.json 不存在，跳过配图注入")
else:
    # 从 img_map.json 读取 AI 计算的精确段落索引
    # 格式：{"article_img_1.png": 6, "article_img_2.png": 14, ...}
    with open(img_map_path, 'r', encoding='utf-8') as f:
        img_map = json.load(f)

    # img_map 的键是文件名，值是段落索引（0-based）
    # 需要翻转：{段落索引: 文件名}
    img_map_flipped = {v: k for k, v in img_map.items()}

    html_content = clean_html_path.read_text(encoding="utf-8")

    # 检查图片文件是否都存在
    missing_imgs = [fname for fname in img_map.keys() if not (output_dir / fname).exists()]
    if missing_imgs:
        print(f"WARNING: 以下图片文件缺失: {missing_imgs}")
        print("跳过配图注入")
    else:
        html_with_imgs = insert_images_into_html(
            html_content,
            img_map_flipped,                    # {段落索引: 文件名}
            img_dir=str(output_dir),             # 完整路径，用于存在性检查
            img_html_relpath="../"              # xiaohu HTML 在 article/ 子目录
        )

        clean_html_path.write_text(html_with_imgs, encoding="utf-8")
        print(f"已注入 {len(img_map)} 张配图到 wechat_clean.html")
        for fname, para_idx in img_map.items():
            print(f"  {fname} → 段落 {para_idx}")
EOF
```

**路径机制说明**（重要，防止再犯）：
- xiaohu 输出结构：`output_dir/article/wechat_clean.html`
- 内文配图位置：`output_dir/article_img_1.png`（与 `article/` 同级）
- HTML → 图片的正确相对路径：`../article_img_1.png`
- `img_dir`：传 output_dir 的完整路径（用于 existence 检查）
- `img_html_relpath`：传 `"../"`（生成正确的 `<img src="../...">` 供 cli.py 上传）
- **禁止**把完整路径传进 `img_map`，`img_map` 的值必须是文件名

**如果 xiaohu 未安装（降级到 WeWrite）：**
```bash
python3 "$HOME/.claude/skills/content-factory/toolkit/cli.py" publish \
  --theme professional-clean \
  --cover "${OUTPUT_DIR}/cover.png" \
  --title "$ARTICLE_TITLE" \
  --author "AI杰瑞斯" \
  "$ARTICLE_MD"
```

### 步骤 7.3：用户可随时换主题

- 如果用户说「换一个主题」→ 重新执行步骤 7.1，用新主题重新排版
- 如果用户说具体主题名（如「用 bytedance 主题」）→ 直接使用指定主题

---

## Step 8：推送草稿箱

直接调用 content-factory 自有 cli.py（底层就是 WeWrite，排版+上传封面+创建草稿一体）：

```bash
ARTICLE_TITLE="<文章标题>"
SLUG="<slug>"
OUTPUT_DIR="${SKILL_OUTPUT}/${SLUG}"
COVER_FILE="${OUTPUT_DIR}/cover.png"

# 推送纯净HTML（含配图）到微信草稿箱
# ⚠️ 重要：使用 article/wechat_clean.html，不是 article.md 或 preview.html
# wechat_clean.html 是 xiaohu 提取的纯净内容，已注入内文配图
PUBLISH_OUTPUT=$(python3 "$HOME/.claude/skills/content-factory/toolkit/cli.py" publish \
  --theme professional-clean \
  --cover "$COVER_FILE" \
  --title "$ARTICLE_TITLE" \
  --author "AI杰瑞斯" \
  "${OUTPUT_DIR}/article/wechat_clean.html" 2>&1)

echo "$PUBLISH_OUTPUT"

# 从输出中提取 media_id（取 Draft created! 行的，草稿箱的，不是封面图的）
MEDIA_ID=$(echo "$PUBLISH_OUTPUT" | grep 'Draft created!' | sed 's/.*media_id: //' | tr -d ' ')
if [ -z "$MEDIA_ID" ]; then
  echo "ERROR: 未能从推送输出中提取 media_id"
  exit 1
fi
echo "MEDIA_ID=$MEDIA_ID"

# 写入临时文件（Step 8.5 独立 block 无法访问 Step 8 的变量，用文件传递）
echo "$MEDIA_ID" > /tmp/aijerrys_last_media_id.txt
echo "$SLUG" > /tmp/aijerrys_last_slug.txt
echo "$ARTICLE_TITLE" > /tmp/aijerrys_last_title.txt
echo "$SELECTED_THEME" > /tmp/aijerrys_last_theme.txt
```

**重要**：
- 传 `${OUTPUT_DIR}/article/wechat_clean.html` 路径，**不是** `article.md` 或 `preview.html`
- `preview.html` 是 xiaohu 的预览壳（含工具栏、手机框架），推送到微信会导致内容重复
- `article.md` 是原始 markdown，缺少排版和配图
- `wechat_clean.html` 是纯净文章HTML，已含内文配图，是正确的推送文件
- 封面必须先生成（Step 6），否则推送会失败（微信草稿箱要求封面图）

**如果封面生成失败**，推送也失败，BLOCKED，不能继续。

---

## Step 8.5：写入 history.yaml

记录本次发布，供后续去重 + 自动复盘。

**幂等机制**：
- `slug + media_id` 作为唯一键
- 同 slug + 同 media_id → 已写过，跳过
- 同 slug + 不同 media_id → 重新推送，更新 media_id
- 写入后验证，不成功则报告

```bash
HISTORY_FILE="$HOME/.claude/skills/content-factory/clients/aijerrys/history.yaml"

# 从 Step 8 的临时文件读取传递过来的值
MEDIA_ID=$(cat /tmp/aijerrys_last_media_id.txt)
SLUG=$(cat /tmp/aijerrys_last_slug.txt)
ARTICLE_TITLE=$(cat /tmp/aijerrys_last_title.txt)
SELECTED_THEME=$(cat /tmp/aijerrys_last_theme.txt)

python3 - << "EOF"
import yaml
from pathlib import Path
from datetime import datetime

history_file = Path("$HISTORY_FILE")
MEDIA_ID = "$MEDIA_ID"
SLUG = "$SLUG"
TITLE = "$ARTICLE_TITLE"
THEME = "$SELECTED_THEME"
TODAY = datetime.now().strftime("%Y-%m-%d")

with open(history_file, 'r', encoding='utf-8') as f:
    history = yaml.safe_load(f)

# 幂等检查：同 slug 是否已存在
existing = [i for i, a in enumerate(history.get("articles", []) if a.get("slug") == SLUG]

if existing:
    idx = existing[0]
    existing_media = history["articles"][idx].get("media_id")
    if existing_media == MEDIA_ID:
        print(f"history.yaml: slug={SLUG} 已存在且 media_id 相同，跳过写入")
    else:
        # 同 slug 不同 media_id：重新推送，更新
        history["articles"][idx].update({
            "date": TODAY,
            "title": TITLE,
            "theme": THEME,
            "media_id": MEDIA_ID,
            "views": None,
            "likes": None,
            "completion_rate": None,
        })
        print(f"history.yaml: slug={SLUG} 已更新 media_id: {existing_media} → {MEDIA_ID}")
else:
    new_entry = {
        "date": TODAY,
        "title": TITLE,
        "slug": SLUG,
        "theme": THEME,
        "media_id": MEDIA_ID,
        "views": None,
        "likes": None,
        "completion_rate": None,
    }
    history.setdefault("articles", []).append(new_entry)
    print(f"history.yaml: 新增 slug={SLUG}, media_id={MEDIA_ID}")

# 写入 + 验证
with open(history_file, 'w', encoding='utf-8') as f:
    yaml.dump(history, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

# 验证写入
with open(history_file, 'r', encoding='utf-8') as f:
    verify = yaml.safe_load(f)
entries = [a for a in verify.get("articles", []) if a.get("slug") == SLUG]
if entries and entries[0].get("media_id") == MEDIA_ID:
    print(f"✓ history.yaml 写入验证成功: slug={SLUG}")
else:
    print(f"⚠️ history.yaml 写入验证失败，请手动检查: slug={SLUG}, media_id={MEDIA_ID}")
EOF
```

写入字段：
- `date`：发布日期
- `title`：文章标题
- `slug`：文章slug
- `theme`：使用的主题
- `media_id`：微信返回的media_id（用于后续自动拉取数据）
- `views/likes/completion_rate`：null（Step 9 自动填充）

---

## Step 8X：推送 Twitter/X 草稿箱

**触发条件**：用户说"发 Twitter"/"推 X"/"post to X"/"发推"

**前提条件**：
- `bun` 已安装（运行 `brew install bun` 或 `npm install -g bun`）
- Chrome 已登录 X 账号（session 持久化）
- `platforms/twitter/scripts` 依赖已安装：`cd platforms/twitter/scripts && bun install`

**流程**：

### 步骤 8X.1：生成 X Article HTML

```bash
PLATFORM_TWITTER="$HOME/.claude/skills/content-factory/platforms/twitter"
OUTPUT_DIR="${SKILL_OUTPUT}/${SLUG}"
ARTICLE_MD="${OUTPUT_DIR}/article.md"
X_HTML="/tmp/x-article-${SLUG}.html"

# 安装依赖（如需要）
cd "$PLATFORM_TWITTER/scripts" && bun install 2>/dev/null || npm install 2>/dev/null || true

# Markdown → X Article HTML
bun "$PLATFORM_TWITTER/scripts/md-to-xhtml.ts" \
  --input "$ARTICLE_MD" \
  --output "$X_HTML"
```

### 步骤 8X.2：推送草稿箱

```bash
ARTICLE_TITLE="<文章标题（截断到70字）>"
COVER_PNG="${OUTPUT_DIR}/cover.png"

bun "$PLATFORM_TWITTER/scripts/x-article.ts" \
  --title "$ARTICLE_TITLE" \
  --html "$X_HTML" \
  --cover "$COVER_PNG" \
  --submit false
```

**重要**：
- `--submit false`（默认）：Chrome 保持打开，用户人工审核后点 Publish
- 不使用 `--submit true`（禁止 AI 自动发布）
- X Article 需要 X Premium 订阅（普通账号只能发普通 tweet）
- 公众号长文（2000字）→ X Article 长文模式 ✅

### 步骤 8X.3：人工审核

Chrome 自动打开，X Article 草稿已填写完毕。
→ 用户检查：标题是否正确、封面图是否合适、正文是否完整
→ 点击 **Publish** 发布

---

## Step 8.5X：写入 Twitter 发布记录

记录本次 Twitter 发布（幂等机制，同 slug 跳过）：

```bash
TWITTER_HISTORY="$HOME/.claude/skills/content-factory/clients/aijerrys/history_twitter.yaml"
mkdir -p "$(dirname "$TWITTER_HISTORY")"

# 如 history_twitter.yaml 不存在则创建
if [ ! -f "$TWITTER_HISTORY" ]; then
  echo "articles: []" > "$TWITTER_HISTORY"
fi

python3 - "$TWITTER_HISTORY" "$SLUG" "$ARTICLE_TITLE" "$SELECTED_THEME" << 'PYEOF'
import yaml
from pathlib import Path
from datetime import datetime

history_file = Path(__import__('sys').argv[1])
SLUG = __import__('sys').argv[2]
TITLE = __import__('sys').argv[3]
THEME = __import__('sys').argv[4]
TODAY = datetime.now().strftime("%Y-%m-%d")

with open(history_file, 'r', encoding='utf-8') as f:
    history = yaml.safe_load(f)

existing = [i for i, a in enumerate(history.get("articles", [])) if a.get("slug") == SLUG]
if existing:
    print(f"Twitter: slug={SLUG} 已存在，跳过写入")
else:
    entry = {"date": TODAY, "title": TITLE, "slug": SLUG, "theme": THEME}
    history.setdefault("articles", []).append(entry)
    with open(history_file, 'w', encoding='utf-8') as f:
        yaml.dump(history, f, allow_unicode=True, default_flow_style=False)
    print(f"Twitter: 已写入 slug={SLUG}")
PYEOF
```

---

## Step 8ALL：推送全部可用平台（并行）

**触发条件**：用户说"全部渠道"、"所有平台"、"一并发"

**核心逻辑**：写作只做一次，各平台并行推送各自的草稿箱。

### 执行方式

```bash
# Step 8 和 Step 8X 并行执行
# （两个推送任务互相独立，同时运行）

# 1. 微信公众号推送（Step 8）
# 已有的推送逻辑不变...

# 2. Twitter/X 推送（Step 8X）
# 已有的 Step 8X 逻辑不变...

# 3. 完成后汇总报告
echo "=== 全部渠道推送完成 ==="
echo "✅ 微信公众号：草稿箱已推送，人工审核后发布"
echo "✅ Twitter/X：Chrome 已打开，X Article 草稿已填入，人工审核后发布"
```

**并行执行示例（后台）**：

```bash
# 并行运行两个推送
(
  # 公众号推送（Step 8）
  echo "推送微信公众号..."
  # ... Step 8 推送代码 ...
) &

(
  # Twitter 推送（Step 8X）
  echo "推送 Twitter/X..."
  # ... Step 8X 推送代码 ...
) &

wait  # 等待两个都完成

echo "全部平台推送完成"
```

**结果汇总**：
- 微信公众号：Chrome WeWrite 草稿箱 → 人工发布
- Twitter/X：Chrome X 草稿箱 → 人工审核后点 Publish

**注意**：
- 小红书暂不支持，报告中注明"小红书推送暂未实现"
- 任一平台推送失败不影响另一平台
- 失败时报告具体哪个平台失败及其错误信息

---

## Step 9：效果闭环 + 风格学习（全自动）

### 效果闭环（fetch_stats.py → 影响后续选题）

**推送成功后自动运行，不需要用户触发。**

发布后 24h 内自动尝试抓取数据（最多等 24h，微信数据有延迟）：
```bash
python3 "$HOME/.claude/skills/content-factory/scripts/fetch_stats.py" \
  --client aijerrs --days 7 2>/dev/null
```

**效果数据自动影响选题（Step 2）**：
- 读取 history.yaml 中所有文章的完读率/点赞/阅读量
- 高效果Topic标签 → 后续同类选题加权（如"GEO获客"类文章完读率高 → GEO选题多分配）
- 低效果Topic标签 → 后续降低权重（如纯AI工具测评点赞低 → 减少同类）
- 自动更新 `选题-变现对照表` 中的爆款公式系数

### 风格学习（learn_edits.py → 自动积累 → 自动更新 Playbook）

**全程自动化，用户只需要做一件事：发布文章后在草稿箱修改，然后告诉 AI「这是我发布的最终版本」或直接粘贴最终正文。**

**触发时机**：用户粘贴最终正文（与AI草稿有diff）→ 自动执行以下流程：

```bash
# 1. 自动检测草稿 vs 最终版的 diff
python3 "$HOME/.claude/skills/content-factory/scripts/learn_edits.py" \
  --client aijerrs \
  --draft "${SKILL_OUTPUT}/${SLUG}/article.md" \
  --final "<用户粘贴的最终正文路径或直接读取剪贴板>"

# 2. 脚本输出 diff 分析和 lessons 数量
# 3. 如果 lessons 数量 >= 5，自动触发 playbook 更新：
LESSONS_COUNT=$(ls "$HOME/.claude/skills/content-factory/clients/aijerrys/lessons/" 2>/dev/null | wc -l | tr -d ' ')
if [ "$LESSONS_COUNT" -ge 5 ]; then
  echo "已积累 ${LESSONS_COUNT} 条 lesson，自动更新 Playbook..."
  python3 "$HOME/.claude/skills/content-factory/scripts/build_playbook.py" \
    --client aijerrs
  echo "Playbook 已更新，下次写作自动应用新风格"
fi
```

**learn_edits.py 自动做的事**：
1. 对比 AI 草稿 vs 用户最终版本
2. 提取修改 pattern（用词替换/段落删除/结构调整/语气调整等）
3. 存入 `clients/aijerrys/lessons/` 目录
4. 积累满 5 条时，**自动调用 build_playbook.py**（不需要用户说任何命令）

**build_playbook.py 的自动化**：
- 读取 corpus 目录所有历史文章（如果有）
- 读取所有 lessons（learn_edits.py 积累的）
- 分析写作风格、模式、偏好
- 输出 `references/playbook.md`
- **playbook.md 优先级最高**，覆盖 writing-guide.md 通用规则

**效果数据自动影响写作（fetch_stats.py → 自动更新偏好）**：
- 完读率高 → 同类框架/选题多写
- 点赞高 → 同类金句多引用
- 阅读量低 → 同类Topic降低权重

---

# Flow 0：素材输入（独立于完整流程）

---

# Flow 0：素材输入（独立于完整流程）

**目标**：把外部链接变成结构化素材笔记，并提议选题。

### 步骤 0.1：检测 URL 类型

```bash
INPUT_URL="<用户提供的URL>"
if echo "$INPUT_URL" | grep -qiE "douyin"; then
  URL_TYPE="douyin"
elif echo "$INPUT_URL" | grep -qiE "xiaohongshu|xhslink"; then
  URL_TYPE="xiaohongshu"
else
  URL_TYPE="web"
fi
echo "URL_TYPE: $URL_TYPE"
```

### 步骤 0.2：提取内容

**抖音** → 使用 MCP 工具：
```bash
# 提取逐字稿
mcp__douyin__extract_douyin_text --share_link "$INPUT_URL"

# 提取元数据
mcp__douyin__parse_douyin_video_info --share_link "$INPUT_URL"
```

**小红书** → 使用 MCP 工具：
```bash
mcp__douyin__parse_social_post_info --share_link "$INPUT_URL"
mcp__douyin__extract_social_post_script --share_link "$INPUT_URL"
```

**多条链接批量处理**：
1. 启动 sub-agent 执行所有链接
2. 逐个处理：读取 → 获取逐字稿 → 写入文件
3. 每个链接都是完整逐字稿，不遗漏

### 步骤 0.3：整理素材

从提取内容中整理：
- **核心信息**（3-5条要点，用大白话）
- **标签**（工具教学/认知觉醒/对比测评/趋势解读）
- **作者/来源**

### 步骤 0.4：保存素材笔记

```bash
DATE=$(date +%Y%m%d)
NOTE_FILE="${BASE_DIR}/02-素材库/视频脚本素材库/${DATE}-<来源>.md"
```

### 步骤 0.5：提议选题

> 基于这个素材，我建议这 1-2 个选题：
>
> 1. [选题标题] | 痛点 | 爆款公式
>
> 要加到选题记录吗？

---

# Flow 1：记录选题

**目标**：把用户脑子里的想法存进选题记录。

```bash
echo "- [ ] [$(date +%Y-%m-%d)] {选题标题} | {类型} | {来源}" >> "${INBOX}"
```

---

# Flow 2：深化选题

**目标**：把选题发展成完整脚本草稿。

### 步骤 2.1：搜索相关素材

```bash
grep -r "{关键词}" "${BASE_DIR}/02-素材库" --include="*.md" -l 2>/dev/null | head -10
```

### 步骤 2.2：读取金句库和核心概念库

```bash
cat "$GOLD_QUOTES"
cat "$CORE_CONCEPTS"
```

### 步骤 2.3：生成脚本草稿

按框架 + 风格生成完整脚本（Hook → 核心内容 → CTA）。

---

# Flow 3：生成标题与 Hook

**目标**：为现有草稿生成 3 组标题 + Hook 组合。

读取 `references/frameworks.md` 中的爆款公式，生成多样化方案。

---

## Completion Status Protocol

完成时汇报：
- **DONE** — 任务完成，文件已保存
- **DONE_WITH_CONCERNS** — 完成但有问题
- **BLOCKED** — 无法继续，说明原因
- **NEEDS_CONTEXT** — 缺少信息，说明需要什么

---

## Telemetry（最后运行）

```bash
_TEL_END=$(date +%s)
_TEL_DUR=$(( _TEL_END - _TEL_START ))
rm -f ~/.gstack/analytics/.pending-"$_SESSION_ID" 2>/dev/null || true
~/.claude/skills/gstack/bin/gstack-telemetry-log \
  --skill "content-factory" --duration "$_TEL_DUR" --outcome "OUTCOME" \
  --used-browse "false" --session-id "$_SESSION_ID" 2>/dev/null &
```
