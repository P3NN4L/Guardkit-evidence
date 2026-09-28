# GuardKit Evidence — MAIB7050 Group Project

> MAIB7050 · Business Data Management for AI · Direction E (Risk Compliance and Escalation)
> **GuardKit Evidence** — an evidence-grounded screening data product for suspicious payment messages in Hong Kong.

一个可查验（working & checkable）的数据产品原型：**一条可疑支付消息 → 打分 → 判决卡（分数/命中规则/官方依据原文）→ 升级人工复核**。

## 30 秒跑通

```bash
python3 src/build_db.py      # 建 SQLite 库（6 张关系表）+ 种子数据
python3 src/run_demo.py      # 打分 3 条消息 → CLI 判决卡 + demo/verdict_cards.html
python3 tests/test_parity.py # 一致性守门（本机有 public-v7 仓时强校验，否则跳过）
open demo/verdict_cards.html # 浏览器看产品形态
```

仅需 Python 3 标准库（sqlite3），无第三方依赖。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `src/build_db.py` | 建库：institutions / rules / messages / verdicts / evidence_documents / evidence_passages |
| `src/run_demo.py` | 核心路径：打分 → 白名单压档 → 证据检索 → 判决卡（CLI + HTML）→ 升级案件 |
| `src/seed_evidence.json` | 证据种子：真实官方页面逐字引用（警务处《商業電郵騙案》2026-01-16、HKMA《Beware of Fraudsters!》），带原文链接+抓取日期+内容 hash |
| `engine/scorer.py` | guard-kit v7 评分组件的 **pinned 快照**（只读依赖，本仓不修改） |
| `models/radar.json` | v7 现役权重（= 公开 npm 包 `@p3nn4l/guard-kit@7.0.0` 的模型文件） |
| `tests/test_parity.py` | 快照 ↔ v7 训练侧评分器逐位一致守门 |
| `docs/proposal.md` | 提交用提案（Moodle 1 页正文版） |
| `docs/match.md` | 作业要求 ↔ 资产逐条对照表 |
| `docs/plan.md` | 执行计划（里程碑/工作包/分工/风险/提交前 checklist） |
| `demo/verdict_cards.html` | 三张判决卡（高危→升级人工 / 机构白名单→放行 / 已知困难案例→人工兜底） |

## 三张判决卡演示的三个设计点

1. **MSG-001 冒充供应商换账户 → 高危 → 升级人工**：证据精确命中警务处原文「供應商聲稱更換付款賬戶，必須先聯絡對方已知舊有聯絡方式確認」——输出可溯源（Element 6）。
2. **MSG-002 银行账单通知（真实盲测卷样本）→ 命中机构通知白名单 → 放行**：三重条件（主题×官方渠道×无可疑链接）压档——明确的数据治理取舍（Element 7）。
3. **MSG-003 假借钱对话（已知困难案例，引擎误报）→ 高危 → 人工复核**：引擎有已知盲区，但工作流把结论交给人而非自动拦截——「triage → human review」的安全垫，评估将如实报告。

## 边界（诚实声明）

- 打分引擎是确定性 n-gram 模型（无生成式组件）：老骗术近乎满分，2025 新骗术存在召回缺口（v7 全卷基线 `recall 84.2%`），将作为已知局限写入评估。
- 检索层当前为演示级（关键词+bigram），正式版做 FTS/embedding 对比评估（见 `docs/plan.md` WP3）。
- 本仓不存储任何真实用户消息；消息样本为演示撰写或团队盲测卷内容（来源标注于 `messages.source`）。
- 先期工作申报：评分引擎、语料与评测基线由组员 Zhanjian Li 在课程开始前开发（公开仓 P3NN4L/guard-kit-code），本仓以 pinned 依赖消费，不属于本课程被评估的贡献。
