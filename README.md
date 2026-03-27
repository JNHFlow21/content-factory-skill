# Content Factory v2.3

> 公众号内容生产流水线 — 从选题到推送全自动化

---

## 这个 Skill 能干什么？

**Content Factory** 是一个 AI 公众号内容生产助手，专为 AI 培训/商业类博主设计。

### 核心能力

| 环节 | 功能 |
|------|------|
| 热点抓取 | 自动抓取微博/头条/百度热搜，多维度评分选题 |
| 选题评估 | 热度×相关度×切入价值三维评分，历史去重 |
| 文章写作 | 对比型/痛点型/故事型等5种框架，素材库弹药（金句+概念）自动引用 |
| dbs五维诊断 | 封面/标题 ≥18 分硬阻断，文字洁癖/表达效率/认知落差/AI辅助逐维打磨 |
| AI绘图 | 3组差异化封面创意 + 3-6张内文配图，精确段落索引注入 |
| xiaohu排版 | 31套主题 AI 自动选择，纯净HTML输出含配图 |
| 推送草稿箱 | 自动上传封面+正文到微信草稿箱，捕获 media_id |
| 效果闭环 | 发布后自动拉取阅读/点赞/完读率数据，影响后续选题权重 |
| 风格学习 | 用户改稿 diff 自动积累，满5条自动更新 playbook |

### 内容风格

- **定位**：AI培训博主、商业思维、创业/职场认知
- **文风**：亲切大白话，像比用户先学了一步的朋友
- **禁忌**：术语不解释、居高临下、AI感套话、强行励志

### 支持的公众号配置

默认客户：**AI杰瑞斯（aijerrys）**。可在 `clients/` 目录下添加新的客户配置。

---

## Quick Start（AI 安装指南）

> 给 AI（Claude Code Agent）读取的安装指令。人类拿到仓库链接后，告诉 AI "帮我安装这个 Skill"，AI 自动完成安装。

### 安装命令

```bash
# 1. 将仓库克隆到 ~/.claude/skills/ 目录下
git clone https://github.com/JNHFlow21/content-factory-skill.git ~/.claude/skills/content-factory

# 2. 安装依赖（Python 3）
pip3 install pyyaml requests pillow 2>/dev/null || true

# 3. 告知用户 Skill 已安装，可以开始使用
```

### 安装后验证

```bash
# 验证安装成功
ls ~/.claude/skills/content-factory/SKILL.md
```

### 安装后告知用户（复制粘贴即可）

---

**✅ Content Factory Skill 安装完成！**

这个 Skill 可以帮你自动生产公众号文章，全流程从热点抓取到推送草稿箱一键完成。

**使用方法**：直接告诉我你想写什么主题，比如：
- "帮我写一篇关于 AI 创业的公众号文章"
- "写一篇打工心态和创业心态的文章"
- "写一篇关于 GEO 获客的内容"

我就会自动执行完整流程：热点抓取 → 选题评分 → 文章写作 → dbs五维诊断 → AI绘图 → xiaohu排版 → 推送草稿箱。

---

## 使用说明

### 触发方式

在 Claude Code 对话中，直接说出你的需求：

| 说法 | 触发流程 |
|------|---------|
| "写一篇关于 XXX 的公众号文章" | 完整流程（Step 0→9） |
| "帮我写公众号文章" | 完整流程 |
| 抖音/小红书链接 | Flow 0：素材输入 |
| "记录选题" | Flow 1：记录选题 |
| "深化选题" | Flow 2：深化选题 |
| "生成标题" | Flow 3：生成标题 |

### 主要流程示例

**写作场景**（最常用）：

```
你：写一篇关于职场 AI 提效的公众号文章

AI 自动执行：
  Step 0  → 读取客户配置和历史记录
  Step 1  → 自动抓取热点 + SEO评分
  Step 2  → 完整三维选题评估（自动选定最优选题）
  Step 3  → 框架选择
  Step 4  → 文章写作（素材库弹药 + writing-guide规则）
  Step 4.5 → dbs五维诊断（封面<18硬阻断，其他<18自动改稿，最多5轮）
  Step 5  → SEO优化 + 年份检查
  Step 6  → 3组封面创意 + 3-6张内文配图（精确段落索引）
  Step 7  → xiaohu AI自动选主题排版 + 配图注入
  Step 8  → 推送微信草稿箱（自动捕获 media_id）
  Step 8.5 → 幂等写入 history.yaml
  Step 9  → 效果闭环（24h后自动拉取数据）
```

### 目录结构

```
content-factory/
├── SKILL.md              # 主 Skill 文件（AI 读取的工作流定义）
├── config.yaml           # 全局配置
├── clients/              # 客户配置
│   └── aijerrys/        # 默认客户（AI杰瑞斯）
│       ├── style.yaml   # 风格配置
│       ├── history.yaml  # 发布历史（自动更新）
│       └── lessons/     # 改稿学习积累（自动生成）
├── scripts/              # Python 工具脚本
│   ├── fetch_hotspots.py    # 热点抓取
│   ├── seo_keywords.py       # SEO评分
│   ├── fetch_stats.py        # 微信数据拉取
│   ├── learn_edits.py        # 改稿学习
│   └── build_playbook.py     # 生成 playbook
├── toolkit/              # 工具封装
│   ├── xiaohu_wrapper.py    # xiaohu排版封装（含配图注入）
│   ├── image_gen.py          # AI绘图调用
│   └── cli.py               # WeWrite CLI（推送草稿箱）
└── references/          # 参考文档
    ├── writing-guide.md   # 写作规范（去AI痕迹）
    ├── seo-rules.md        # SEO规则
    ├── visual-prompts.md   # 视觉提示词规范
    ├── frameworks.md       # 写作框架库
    └── topic-selection.md  # 选题评分体系
```

### DBS 五维诊断标准

| 维度 | 满分 | 及格线 | 说明 |
|------|------|--------|------|
| 封面/标题 | 20 | ≥18 | 反直觉/数字/痛点/好奇钩子 |
| 文字洁癖 | 20 | ≥18 | 无AI套话，大白话有温度 |
| 表达效率 | 20 | ≥18 | 一句话说清核心，段落清晰 |
| 认知落差 | 20 | ≥18 | 反常识/颠覆认知，有独特见解 |
| AI辅助 | 20 | ≥18 | 具体工具名、有操作步骤 |

> **注意**：封面/标题 <18 是硬性阻断，不允许跳过。其他任何维度 <18 都会自动进入改稿循环，最多 5 轮。

### 效果数据闭环

- 发布后 24h，AI 自动拉取微信草稿箱数据（阅读量/点赞/完读率）
- 高效果选题标签 → 后续同类选题加权
- 低效果选题标签 → 后续降低权重

---

## 自定义配置

### 添加新客户

在 `clients/` 下新建目录，添加 `style.yaml`（风格配置）和空的 `history.yaml`：

```yaml
# clients/demo/style.yaml
name: "demo"
industry: "行业"
target_audience: "目标受众"
content_style: "干货型"  # 干货型 | 故事型 | 情绪型 | 热点型 | 测评型
tone: "实战、直接"
topics:
  - 主题1
  - 主题2
blacklist:
  words: ["敏感词1", "敏感词2"]
  topics: ["政治", "宗教"]
author: "作者名"
theme: "professional-clean"
```

### xiaohu 排版主题

支持 31 套 xiaohu-wechat-format 主题，AI 根据文章内容自动选择：

| 场景 | 推荐主题 |
|------|---------|
| 企业/AI/创业 | terracotta（默认） |
| 深度分析/论证 | newspaper |
| 工具/教程 | github |
| 情绪/故事 | coffee-house |
| 科技/AI | bytedance |
| 高端/商业 | minimal-gold |

如需安装 xiaohu-wechat-format：
```bash
git clone https://github.com/xxx/xiaohu-wechat-format.git ~/.claude/skills/xiaohu-wechat-format
```

---

## 依赖说明

- **Python 3.8+**
- **依赖包**：pyyaml, requests, pillow
- **可选**：xiaohu-wechat-format（未安装时自动降级到 WeWrite professional-clean 主题）
- **外部服务**：WeWrite CLI（推送草稿箱）、AI绘图工具（image_gen.py）

---

## 版本历史

- **v2.2.2**：DBS五维诊断全面提升至 ≥18 分门槛；修复 Step 8 media_id 提取逻辑；修复 Step 8.5 bash heredoc 变量传递问题
- **v2.2.1**：配图段落索引改为 img_map.json 精确映射；Step 0.5 自动拉取数据；history.yaml 幂等写入
- **v2.2**：完整 Step 0-9 全流程整合；xiaohu 31套主题 AI 自动选择；dbs 五维诊断打磨循环
