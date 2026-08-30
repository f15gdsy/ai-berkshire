#!/usr/bin/env python3
"""Generate WorkBuddy skills from AI Berkshire Claude command files.

Produces two kinds of packages under workbuddy-skills/:

1. One SKILL.md per canonical skill in skills/*.md, prefixed with a
   harness-neutral adapter note (tool vocabulary mapping, $ARGUMENTS
   handling, quality rules, and the 3-step tool resolution chain).
2. A shared `ai-berkshire-tools` pseudo skill package containing the
   tool scripts referenced by skills, so that skills installed outside
   the repository can still run their validation commands.

Other harness targets (codex-skills/, codex-prompts/) are handled by
their own sync scripts and are intentionally untouched here.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS = ROOT / "skills"
WORKBUDDY_SKILLS = ROOT / "workbuddy-skills"
TOOLS = ROOT / "tools"

# Tool scripts referenced by skills (verified via grep across skills/*.md).
# Keep in sync: --check verifies every tools/<script> referenced in any
# skill body exists in the generated ai-berkshire-tools package.
BUNDLED_TOOLS = [
    "financial_rigor.py",
    "report_audit.py",
    "twstock_data.py",
    "terminal_value.py",
    "xueqiu_scraper.py",
]

TOOLS_SKILL_NAME = "ai-berkshire-tools"

TOOLS_SKILL_DESCRIPTION = (
    "AI Berkshire 共享验证工具包（伪 skill，供其他 skill 引用，无需单独触发）。"
    "包含 financial_rigor.py（市值/估值/交叉验证/三情景精确算术）、report_audit.py"
    "（报告数据抽检）、twstock_data.py（台股行情/月营收）、terminal_value.py"
    "（永续价值计算）、xueqiu_scraper.py（雪球数据，需登录态缓存，独立环境可能不可用）。"
    "其他 AI Berkshire skill 按三步链解析工具：仓库 tools/ → 本包 scripts/ → Python 内联精确运算降级。"
)

ADAPTER_NOTE = """## Harness adapter note

本 skill 由 `skills/{source_name}` 生成，可在 WorkBuddy 及任何支持 Agent Skills 规范的 harness 中独立运行。

- **参数**：正文中的 `$ARGUMENTS` 指当前会话中用户提出的请求（触发 skill 时附带的内容）。
- **工具词汇映射**：正文中提到的 Claude 专属工具（Agent/Task、WebSearch、Bash、Read、Write 等），使用当前 harness 中最接近的能力执行：可用的子代理/后台任务、联网搜索、命令行执行、文件读写。某个能力不可用时，明确告知用户并降级执行（例如无法联网时标注"仅凭既有知识，未经联网验证"）。
- **工具解析链（按顺序尝试）**：
  1. 当前工作目录位于 ai-berkshire 仓库内 → 直接使用仓库 `tools/` 下的脚本；
  2. 否则查找 `ai-berkshire-tools` skill 的 `scripts/` 目录（依次尝试 `~/.workbuddy/skills/ai-berkshire-tools/scripts/` 与 `<workspace>/.workbuddy/skills/ai-berkshire-tools/scripts/`）；
  3. 都找不到 → 用 Python（`decimal` 等精确算术）内联实现相同的验算逻辑，并在输出中标注"验算由内联脚本完成，未经 tools/ 标准工具校验"。
- **其他 AI Berkshire skill 引用**：正文中提到的其他 skill 名（如 `investment-team`、`earnings-review`）未安装时，按正文描述独立降级执行相应部分，不中断主流程。
- **研究质量规则**（无论在哪个 harness 中运行都必须遵守）：
  - 开始研究前先运行 `date` 命令确认今天日期，以此作为"最新"数据的基线，并在报告头部注明数据截止日。禁止假设训练数据中的日期是当前日期。
  - 关键财务数据至少两个独立来源交叉验证，误差 >1% 必须标记。
  - 市值、估值、情景分析等数学计算使用精确算术工具（见工具解析链）验算，不心算。
  - 明确标注低置信度结论、不完整数据与来源缺口。本项目用于学习与研究，不构成投资建议。

"""


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :].lstrip("\n")


def frontmatter_field(existing: str, field: str) -> str | None:
    match = re.search(rf"(?m)^{field}:\s*(.+)$", existing)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        value = value[1:-1].replace('\\"', '"')
    return value


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def skill_md(name: str, source_name: str, source_text: str) -> str:
    existing, body = split_frontmatter(source_text)
    if existing:
        skill_name = frontmatter_field(existing, "name") or name
        description = frontmatter_field(existing, "description") or first_heading(
            body, name
        )
    else:
        skill_name = name
        description = first_heading(source_text, name)
    return (
        "---\n"
        f"name: {skill_name}\n"
        f"description: \"{description.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"')}\"\n"
        "---\n\n"
        + ADAPTER_NOTE.format(source_name=source_name)
        + body.rstrip()
        + "\n"
    )


def tools_skill_md() -> str:
    scripts = ", ".join(f"`scripts/{t}`" for t in BUNDLED_TOOLS)
    body = (
        "# AI Berkshire 共享验证工具包\n\n"
        "本包不承载独立工作流，而是为其他 AI Berkshire skill 提供可独立安装的验证工具。"
        "安装其他 AI Berkshire skill 时，请一并安装本包。\n\n"
        f"包含脚本：{scripts}。\n\n"
        "## 使用方式\n\n"
        "其他 skill 会自动按三步解析链定位工具（仓库 tools/ → 本包 scripts/ → 内联降级），"
        "无需手动指定路径。手工调用示例：\n\n"
        "```bash\n"
        "python3 scripts/financial_rigor.py verify-market-cap \\\n"
        "  --price 380 --shares 29.3亿 --reported 1.11万亿港元 --currency HKD\n"
        "```\n\n"
        "## 脚本依赖说明\n\n"
        "- `xueqiu_scraper.py` 依赖登录态缓存（`/tmp/xueqiu_state.json`），"
        "独立环境中可能不可用，届时改用其他数据源并标注。\n"
        "- 所有脚本仅依赖 Python 标准库（部分可能使用 `urllib` 联网取数）。\n"
    )
    return (
        "---\n"
        f"name: {TOOLS_SKILL_NAME}\n"
        f"description: \"{TOOLS_SKILL_DESCRIPTION.replace('\"', '\\\\\"')}\"\n"
        "---\n\n"
        + body
    )


def referenced_tools_missing() -> list[str]:
    """Tool scripts referenced in any skill body but missing from tools/."""
    missing: list[str] = []
    for source in sorted(CLAUDE_SKILLS.glob("*.md")):
        text = source.read_text(encoding="utf-8")
        for match in re.findall(r"tools/([a-z_]+\.py)", text):
            if match not in BUNDLED_TOOLS:
                missing.append(f"{source.stem}: tools/{match}")
    return missing


def main() -> None:
    check = "--check" in sys.argv[1:]
    unknown_args = [arg for arg in sys.argv[1:] if arg != "--check"]
    if unknown_args:
        joined = ", ".join(unknown_args)
        raise SystemExit(f"Unknown argument(s): {joined}")

    missing = referenced_tools_missing()
    if missing:
        print("Tools referenced by skills but not bundled:")
        for item in missing:
            print(f"  {item}  (add to BUNDLED_TOOLS in sync-workbuddy-skills.py)")
        raise SystemExit(1)

    stale: list[str] = []
    count = 0

    for source in sorted(CLAUDE_SKILLS.glob("*.md")):
        name = source.stem
        source_text = source.read_text(encoding="utf-8")
        target_dir = WORKBUDDY_SKILLS / name
        target = target_dir / "SKILL.md"
        content = skill_md(name, source.name, source_text)
        if check:
            if not target.exists() or target.read_text(encoding="utf-8") != content:
                stale.append(str(target.relative_to(ROOT)))
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        count += 1

    # Shared tools pseudo skill package
    tools_target_dir = WORKBUDDY_SKILLS / TOOLS_SKILL_NAME
    tools_md = tools_target_dir / "SKILL.md"
    tools_content = tools_skill_md()
    if check:
        if not tools_md.exists() or tools_md.read_text(encoding="utf-8") != tools_content:
            stale.append(str(tools_md.relative_to(ROOT)))
        for tool in BUNDLED_TOOLS:
            src = TOOLS / tool
            dst = tools_target_dir / "scripts" / tool
            if not src.exists():
                print(f"Bundled tool missing from tools/: {tool}")
                raise SystemExit(1)
            if not dst.exists() or dst.read_text(encoding="utf-8") != src.read_text(
                encoding="utf-8"
            ):
                stale.append(str(dst.relative_to(ROOT)))
    else:
        scripts_dir = tools_target_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        tools_md.write_text(tools_content, encoding="utf-8")
        for tool in BUNDLED_TOOLS:
            shutil.copy2(TOOLS / tool, scripts_dir / tool)

    count += 1

    if check:
        if stale:
            print("WorkBuddy skills are out of date:")
            for path in stale:
                print(f"  {path}")
            raise SystemExit(1)
        print(f"Checked {count} WorkBuddy skill packages in {WORKBUDDY_SKILLS.relative_to(ROOT)}")
        return

    print(f"Generated {count} WorkBuddy skill packages in {WORKBUDDY_SKILLS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
