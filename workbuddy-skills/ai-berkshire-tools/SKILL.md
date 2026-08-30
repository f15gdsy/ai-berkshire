---
name: ai-berkshire-tools
description: "AI Berkshire 共享验证工具包（伪 skill，供其他 skill 引用，无需单独触发）。包含 financial_rigor.py（市值/估值/交叉验证/三情景精确算术）、report_audit.py（报告数据抽检）、twstock_data.py（台股行情/月营收）、terminal_value.py（永续价值计算）、xueqiu_scraper.py（雪球数据，需登录态缓存，独立环境可能不可用）。其他 AI Berkshire skill 按三步链解析工具：仓库 tools/ → 本包 scripts/ → Python 内联精确运算降级。"
---

# AI Berkshire 共享验证工具包

本包不承载独立工作流，而是为其他 AI Berkshire skill 提供可独立安装的验证工具。安装其他 AI Berkshire skill 时，请一并安装本包。

包含脚本：`scripts/financial_rigor.py`, `scripts/report_audit.py`, `scripts/twstock_data.py`, `scripts/terminal_value.py`, `scripts/xueqiu_scraper.py`。

## 使用方式

其他 skill 会自动按三步解析链定位工具（仓库 tools/ → 本包 scripts/ → 内联降级），无需手动指定路径。手工调用示例：

```bash
python3 scripts/financial_rigor.py verify-market-cap \
  --price 380 --shares 29.3亿 --reported 1.11万亿港元 --currency HKD
```

## 脚本依赖说明

- `xueqiu_scraper.py` 依赖登录态缓存（`/tmp/xueqiu_state.json`），独立环境中可能不可用，届时改用其他数据源并标注。
- 所有脚本仅依赖 Python 标准库（部分可能使用 `urllib` 联网取数）。
