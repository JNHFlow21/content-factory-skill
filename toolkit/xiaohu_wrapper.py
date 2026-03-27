"""
xiaohu_wrapper.py — xiaohu-wechat-format subprocess 调用封装

通过 subprocess 调用 xiaohu-wechat-format 的 format.py，不直接 import。
用途：公众号文章 HTML 排版（31套主题）

⚠️ 前置依赖：xiaohu-wechat-format skill 必须已安装到 ~/.claude/skills/xiaohu-wechat-format/
如未安装，此模块不可用，请使用 WeWrite 自带的排版（Step 7 已配置）。

安装方式：
  git clone https://github.com/xxx/xiaohu-wechat-format.git ~/.claude/skills/xiaohu-wechat-format
"""

import subprocess
import os
import sys
from pathlib import Path


XIAOHU_SKILL_DIR = os.path.expanduser("~/.claude/skills/xiaohu-wechat-format")
FORMAT_SCRIPT = f"{XIAOHU_SKILL_DIR}/scripts/format.py"


def is_available() -> bool:
    """检查 xiaohu 是否已安装。"""
    return os.path.exists(FORMAT_SCRIPT)


def format_article(
    input_file: str,
    output_dir: str,
    theme: str = "terracotta",
    no_open: bool = True,
) -> str:
    """
    调用 xiaohu-wechat-format 的 format.py 对文章进行排版。

    Args:
        input_file: markdown 文件路径
        output_dir: 输出目录路径（会创建）
        theme: 主题名称（默认 terracotta）
        no_open: 不打开浏览器（默认 True）

    Returns:
        生成的 HTML 文件路径

    Raises:
        FileNotFoundError: xiaohu 未安装或 format.py 不存在
        subprocess.CalledProcessError: 排版失败
    """
    if not is_available():
        raise FileNotFoundError(
            f"xiaohu-wechat-format not installed at {XIAOHU_SKILL_DIR}.\n"
            "当前使用 WeWrite 内置主题（professional-clean）进行排版。\n"
            "如需 xiaohu 31 套主题，请安装 xiaohu-wechat-format skill。"
        )

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        sys.executable,
        FORMAT_SCRIPT,
        "--input", input_file,
        "--theme", theme,
        "--output", output_dir,
    ]
    if no_open:
        cmd.append("--no-open")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )

    article_slug = Path(input_file).stem
    html_file = os.path.join(output_dir, f"{article_slug}.html")

    if not os.path.exists(html_file):
        html_files = list(Path(output_dir).glob("*.html"))
        if html_files:
            html_file = str(html_files[0])

    # xiaohu 实际输出到 article/preview.html（预览壳），提取纯净内容
    preview_html = Path(output_dir) / "article" / "preview.html"
    if preview_html.exists():
        clean_html = _extract_wechat_clean_html(str(preview_html))
        if clean_html:
            # 保存纯净版到 article/wechat_clean.html
            clean_path = Path(output_dir) / "article" / "wechat_clean.html"
            clean_path.parent.mkdir(parents=True, exist_ok=True)
            clean_path.write_text(clean_html, encoding="utf-8")
            return str(clean_path)

    return html_file


def _extract_wechat_clean_html(preview_path: str) -> str:
    """从 xiaohu preview.html 中提取 #wechatHtml div 的纯净内容。"""
    import re
    try:
        content = Path(preview_path).read_text(encoding="utf-8")
        match = re.search(r'<div id="wechatHtml">(.*?)</div>\s*<script>', content, re.DOTALL)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return ""


def get_available_themes() -> list:
    """返回 xiaohu 支持的主题列表（30套，需 xiaohu 已安装）。"""
    if not is_available():
        return []
    return [
        # 企业/创业场景
        "terracotta",       # 陶土橙暖调，企业AI/创业首选
        "bytedance",        # 字节跳动蓝，企业科技感
        "minimal-gold",     # 极简金，高端商业
        "elegant-navy",     # 优雅深蓝，高端商务
        "elegant-green",    # 优雅绿，商务健康
        "elegant-blue",     # 优雅蓝，专业科技
        # 门店/实体/GEO场景
        "minimal-white",    # 极简白，门店/ GEO/实体店主（对应 minimal-blue）
        "minimal-gray",     # 极简灰
        "minimal-navy",    # 极简藏青
        "minimal-red",     # 极简红
        "coffee-house",    # 咖啡馆暖调，故事/情绪类
        # 深度内容
        "newspaper",       # 报纸风，深度分析/论证
        "sspai",           # 少数派，科技感干货
        "github",          # GitHub风格，技术/工具/教程
        "magazine",        # 杂志风，编辑感
        # 视觉冲击
        "bold-navy",       # 粗体藏青，强对比
        "bold-blue",       # 粗体蓝
        "bold-green",      # 粗体绿
        "focus-gold",     # 焦点金，高端聚焦
        "focus-blue",      # 焦点蓝
        "focus-red",      # 焦点红
        # 特殊风格
        "chinese",        # 中国风
        "lavender-dream", # 薰衣草紫梦，温柔梦幻
        "mint-fresh",     # 薄荷清新，年轻清新
        "sunset-amber",   # 日落琥珀，暖色夕阳
        "midnight",        # 午夜蓝，暗色系
        "ink",            # 墨水，书法质感
        "sports",         # 体育风
        "bauhaus",        # 包豪斯，几何现代
        "wechat-native",  # 微信原生风格
    ]


def auto_theme_selection(article_content: str, article_title: str = "") -> str:
    """
    根据文章内容自动选择最佳 xiaohu 主题。

    Args:
        article_content: 文章正文内容（用于分析场景）
        article_title: 文章标题（辅助判断）

    Returns:
        最佳匹配的 xiaohu 主题名称

    AI 选主题逻辑：
    1. 合并标题+正文进行场景分析
    2. 按关键词匹配场景类型
    3. 返回最佳主题

    场景 → 主题映射：
    - 企业AI/创业/转型/降本/增效 → terracotta（暖调，企业感）
    - GEO/门店/实体/线下/本地 → minimal-white（简洁，实体店主）
    - 深度分析/逻辑/论证/趋势 → newspaper（严肃，报纸风）
    - 工具/教学/教程/方法论 → github（技术文档感）
    - 情绪/共鸣/故事/人物 → coffee-house（温暖，故事感）
    - 科技/AI/字节/数字 → bytedance（科技蓝）
    - 高端/精致/商业精英 → minimal-gold（极简金）
    - 无特定场景 → terracotta（默认）
    """
    text = (article_title + " " + article_content).lower()

    # 场景匹配规则（按优先级）
    scene_rules = [
        # (关键词列表, 主题)
        (["geo", "门店", "实体店", "线下", "本地搜索", "地图优化", "商铺"], "minimal-white"),
        (["创业", "ceo", "商业模式", "变现", "商业", "企业", "公司", "降本", "增效", "转型", "战略"], "terracotta"),
        (["深度", "分析", "逻辑", "论证", "趋势", "洞察", "本质", "规律"], "newspaper"),
        (["工具", "教程", "教学", "方法", "步骤", "指南", "技巧", "提示词", "prompt"], "github"),
        (["情绪", "共鸣", "故事", "人物", "案例", "经历", "感受", "创业故事"], "coffee-house"),
        (["科技", "数字", "字节", "技术", "ai", "人工智能", "大模型", "算法"], "bytedance"),
        (["高端", "精英", "精致", "商业精英", "品牌"], "minimal-gold"),
    ]

    for keywords, theme in scene_rules:
        for kw in keywords:
            if kw in text:
                return theme

    return "terracotta"  # 默认主题


def insert_images_into_html(
    html_content: str,
    img_map: dict[int, str],
    img_dir: str = "",
    img_html_relpath: str = "",
) -> str:
    """
    将内文配图插入到纯净 HTML 的指定段落后。

    Args:
        html_content: 纯净 HTML 内容（#wechatHtml div 里的内容）
        img_map: {段落索引(0-based): 图片文件名}，段落索引指 <p> 标签的序号
                   ⚠️ 注意：img_map 的值必须是图片**文件名**（不含路径），
                   例如 "article_img_1.png"，不是 "/full/path/article_img_1.png"
        img_dir: 图片所在目录的完整路径，用于检查文件是否存在
                 例如 "/Users/.../output_dir/"
        img_html_relpath: 图片相对于 HTML 文件所在目录的路径
                          xiaohu 输出 HTML 在 output_dir/article/，
                          图片在 output_dir/，
                          所以 img_html_relpath = "../"
                          cli.py 推送时需要此路径来正确上传图片

    Returns:
        插入图片后的 HTML 字符串

    Raises:
        无（图片不存在时生成 <!-- IMAGE MISSING --> 注释，不阻断流程）

    示例：
        # xiaohu 场景：HTML 在 article/ 子目录，图片在上级目录
        html = insert_images_into_html(
            html_content,
            {0: "article_img_1.png", 8: "article_img_2.png"},
            img_dir="/Users/.../output_dir/",
            img_html_relpath="../"   # 相对于 HTML 目录的图片路径
        )

        # WeWrite 场景：HTML 和图片同在 output_dir/
        html = insert_images_into_html(
            html_content,
            {0: "article_img_1.png"},
            img_dir="/Users/.../output_dir/",
            img_html_relpath=""       # 同目录，不需要 ../
        )
    """
    import re
    if img_dir:
        os.makedirs(img_dir, exist_ok=True)

    def make_img_tag(filename: str) -> str:
        # HTML src 使用相对路径（相对于 HTML 文件所在目录）
        html_src = f"{img_html_relpath}{filename}" if img_html_relpath else filename
        # 文件存在性检查使用完整路径
        check_path = os.path.join(img_dir, filename) if img_dir else filename
        if img_dir and not os.path.exists(check_path):
            return f"<!-- IMAGE MISSING: {filename} -->"
        return (
            f'<p style="text-align:center;margin:24px 0">'
            f'<img src="{html_src}" style="width:100%;max-width:640px;border-radius:8px" />'
            f'</p>'
        )

    result_parts = []
    last_end = 0
    para_idx = 0

    for m in re.finditer(r'<p[^>]*>.*?</p>', html_content, re.DOTALL):
        result_parts.append(html_content[last_end:m.start()])
        result_parts.append(m.group())
        last_end = m.end()

        if para_idx in img_map:
            result_parts.append(make_img_tag(img_map[para_idx]))

        para_idx += 1

    result_parts.append(html_content[last_end:])
    return "".join(result_parts)


def check_and_fix_years(
    html_or_md: str,
    current_year: int | None = None,
) -> tuple[str, list[dict]]:
    """
    检查文本中的绝对年份引用，判断是否需要更新为当前年份。

    判断规则：
    - 叙述性当前时间（如"2025年的某天"、"在2025年已经..."）→ 更新为当前年份
    - 历史性过去时间（如"1998年"、"在1970年代"）→ 不修改
    - 相对时间（"去年"、"今年"、"上个月"）→ 不修改

    Args:
        html_or_md: HTML 或 Markdown 原文
        current_year: 当前年份，默认为本年

    Returns:
        (修正后的文本, 修改记录列表)
    """
    import re
    from datetime import datetime

    if current_year is None:
        current_year = datetime.now().year

    # 匹配绝对年份：20XX年 或 19XX年
    year_pattern = re.compile(r'(19\d{2}|20\d{2})年')
    matches = list(year_pattern.finditer(html_or_md))

    changes = []

    for m in matches:
        year = int(m.group(1))
        start = max(0, m.start() - 40)
        end = min(len(html_or_md), m.end() + 20)
        ctx = html_or_md[start:end]

        # 判断：历史性引用 → 不改
        # 关键词：前、过去、当时、曾经、历史、年代（70/80/90/00年代）、世纪
        historical_kw = ["前", "过去", "当时", "曾经", "历史", "年代", "世纪"]
        is_historical = any(kw in ctx for kw in historical_kw)

        if is_historical:
            continue

        # 判断：叙述性当前时间 → 更新为今年
        # 特征：紧跟在"某天"、"已经"、"现在"、"当今"、"眼下"等词后面
        # 或出现在"越来越"、"正在"等进行时语境中
        current_context_kw = ["某天", "已经", "现在", "当今", "眼下", "越来越", "正在"]
        is_current_context = any(kw in ctx for kw in current_context_kw)

        if is_current_context and year < current_year:
            old = m.group()
            new = f"{current_year}年"
            # 只替换这一个位置（保护其他年份不变）
            new_text = html_or_md[:m.start()] + new + html_or_md[m.end():]
            changes.append({
                "year": year,
                "new_year": current_year,
                "context": ctx,
                "action": "updated",
            })
            # 重新查找（文本已改变，重新匹配后续）
            html_or_md = new_text
            # 重新构建匹配列表（只处理剩余的）
            remaining = list(re.finditer(year_pattern, html_or_md))
            # 简化处理：只替换找到的第一个，其余由人工判断
            break

    return html_or_md, changes


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="xiaohu 排版封装")
    parser.add_argument("--input", required=True, help="输入 markdown 文件")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--theme", default=None, help="主题名称（不填则自动选择）")
    parser.add_argument("--auto-theme", action="store_true", help="根据文章内容自动选择主题")
    args = parser.parse_args()

    if not is_available():
        print(f"ERROR: xiaohu-wechat-format not installed at {XIAOHU_SKILL_DIR}")
        sys.exit(1)

    # 自动选主题
    theme = args.theme
    if args.auto_theme or theme is None:
        article_content = Path(args.input).read_text(encoding="utf-8")
        theme = auto_theme_selection(article_content, "")
        print(f"AI 自动选择主题: {theme}")
    else:
        print(f"使用指定主题: {theme}")

    html_file = format_article(args.input, args.output, theme)
    print(f"HTML 生成完成: {html_file}")
