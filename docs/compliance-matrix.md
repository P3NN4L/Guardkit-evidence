# 合规矩阵 · Guidelines 逐条对照（MAIB7050_Group_Project_Guidelines.pdf, Sem 1 2026–27）

> 用途：提交前对账。每条 = 原文要求 → 我们的对应物 → 状态。
> 状态：✅ 已满足 · 🟡 已有素材/待成稿 · 🔴 未开始（需人工输入或时间）
> 最后核对：2026-09-29，对照原 PDF 全文。

## Part 1 · Project Content

| § | 要求 | 我们的对应物 | 状态 |
|---|---|---|---|
| 1.1 | 业务问题 + 可溯证据 + 用户/行动/局限可见；非软件竞赛 | 提案 §1（双角色/行动/边界）；"永不自动拦截"= 局限可见性设计 | ✅ |
| 1.2 | 七要素全部连通 | use→sources→relational→JSON→retrieval→output→governance：`docs/design.md` 血缘图逐环对应 | ✅ |
| 1.3 | 选一个方向 | Direction E；示例句逐字吻合 | ✅ |
| 1.4 | 选题窄到可实施、需设计选择 | 可疑支付消息单场景；白名单取舍/检索选型/档位双条件皆为设计选择 | ✅ |
| 1.5 数据要求 | 五问（谁用/什么决策/为什么值得/要什么证据/数据为何合适） | 提案 §1–2 全答（统计数字占位符待填 🟡） | 🟡 |
| 1.5 来源表 | 公开数据：source、license、access date、limitations 全记录 | URL+accessed_at+license（25/27，余 2 seed 待补）+ DATA-HANDOFF 局限节 | ✅ |
| 1.5 核心门槛 | ≥3 关联实体；≥50 短文本或 ≥20 文档；Integration | 8 实体；108 短文本 + 27 文档；verdict_evidence 外键 | ✅ |
| 1.5 checklist | 业务问题/来源/集成计划+初步数据字典/局限与隐私 | 前三 ✅；**data-dictionary.md 成稿 ✅**；局限+PII ✅ | ✅ |
| 1.6 关系数据管理 | schema+键+关系+**数据字典**+代表性 SQL | `docs/data-dictionary.md` + `docs/queries.sql` 六组 | ✅ |
| 1.6 文档/文本管理 | 合理 JSON 结构+元数据+保留源证据+**成文的准备/转换决策** | JSONL+元数据+逐字段落；决策记录：DATA-HANDOFF + README 数据字典 + build_db 注释 | ✅ |
| 1.6 检索 | 能跑的关键词/元数据/混合检索 | FTS5+BM25+docagg；`retrieval_method` 字段落库 | ✅ |
| 1.6 有据输出 | 结果标明支撑记录/段落/元数据（compulsory） | 判决卡 + verdict_evidence 142 行 | ✅ |
| 1.6 集成与血缘 | 源→转换→存储→查询 路径 + **版本或运行说明可复现** | design.md 血缘图 + README 四条命令 + 确定性重建实测（逻辑逐行一致） | ✅ |
| 1.6 治理 | ownership/access/privacy/quality/human-review；禁泛泛伦理声明 | 字段级：PII 管线/审计链/永不拦截/复核字段 | ✅ |
| 1.6 评估 | 成文的代表性+困难用例集、期望判定、观测结果 | 108 标注池 + 交叉表；**60 例成稿（60cases.csv）未产出** | 🟡 |
| 1.6 演示路径 | 团队须能演示"用户问题→检索证据" | run_demo + notebook §4 判决卡现场渲染 | ✅ |

## Part 2 · Planning, Assessment and Submission

| § | 要求 | 我们的对应物 | 状态 |
|---|---|---|---|
| 2.1 | ≤5 人；角色/截止/存储/版本控制约定；**contribution record**；成员都要能讲全项目 | plan.md §五分工；贡献记录**无成文 artifact** | 🟡 |
| 2.2 提案 | 英文、≤1 页正文+≤2 页声明，经 Moodle 提交；字段齐全 | proposal v2 已成稿；**占位符待填：GroupID/成员/统计 [N][X]/[tool/model]** | 🟡 |
| 2.3 报告内容 | 英文、jointly authored、executive summary + 8 节（问题/来源/架构/实现路径/结果/评估/治理/结论） | 素材全齐（design/queries/walkthrough/primer/复现表）；**报告本体未写** | 🔴 |
| 2.4 README+索引 | 用途/结构/运行步骤/依赖/无凭据/已知局限/文件↔报告章节链接 | README ✅（文件↔报告章节链接待报告定稿后补） | 🟡 |
| 2.4 Data package | 数据 + **source register** + **data dictionary** + 生成内容明确标注 | **`data/source-register.csv` ✅（27 行）**；**`docs/data-dictionary.md` ✅**；标注 ✅ | ✅ |
| 2.4 Design artefacts | ERD/schema/JSON 结构/**架构与血缘视图**/访问与责任决策 | `docs/design.md` + assets 两张 PNG + 治理字段 | ✅ |
| 2.4 Implementation | 复现核心查询与检索路径所需的 SQL/notebook/code | queries.sql + src/*.py + **GuardKit_Evidence.ipynb** | ✅ |
| 2.4 Evaluation evidence | 测试用例/期望/结果/**失败例**/改进/选型对比 | fp-attribution + 交叉表 + 漏报归因；60 例成稿待做；选型对比=FTS5 vs embedding 论证（design.md §4） | 🟡 |
| 2.4 Demonstration | live demo + **录制兜底**（Class_GroupID_Demo.mp4） | demo 可现场跑；**视频未录** | 🔴 |
| 2.4 无凭据 | 不得含 API keys/密码/个人信息 | 已核：无凭据；PII 管线在库 | ✅ |
| 2.5 个人反思 | 每人英文 1 页，非报告缩写 | 各人自办 | 🔴（个人） |
| 2.6 页数 | 提案 1+2；报告 ≤10+2；反思 1+2 | 写作时执行 | 🔴（随写作） |
| 2.7 格式 | A4/2.54cm/TNR 12pt/1.2 倍距/标题 14·12 bold/图≥10pt/MLA/页码/**PDF** | 写作时执行 | 🔴（随写作） |
| 2.8 交付物命名 | Class_GroupID_Report.pdf + Project.zip + Slides + Demo.mp4 + AnalyticalReport + 可选 PeerEvaluation | **无一件已按名组装**（依赖上面各项完成） | 🔴 |
| 2.9 评分标准 | 85 组分 + 15 个人分；七准则 | match.md 逐项对分；Excellent 档特征全部命中中 | ✅（对标） |
| 2.10 答辩 | 15 分钟演示 + 5 分钟问答（2/3/5/3/2 时间表）；全员到 场能答 | walkthrough §0–§6 + 预设 Q&A；slides/排练待做 | 🟡 |
| 2.11 引用与 AI | 引用 MLA；**AI 申报**：工具/用途/影响部分/**如何核查修订**；不得把生成物当独立观察 | 提案声明模板在；**须补：三份外部 AI 复核文档 + 代码辅助的申报内容** | 🟡 |
| 2.12 final checks | scope 一致/证据标注/核心可查/页数格式/引用 AI 完整/链接可用/各人反思 | = 本矩阵；提交前逐项打勾 | 🟡 |

## 🔴→✅ 的最短路径（按依赖顺序）

1. **填提案占位符**（GroupID/成员/统计数字/AI 工具名）——需要团队输入，30 分钟
2. **60 例评估集成稿**（evaluation/60cases.csv + observed 结果表）——池子和骨架现成，1 天
3. **报告英文 10 页**（按 §2.3 八节，素材全齐）——3–4 天，最大件
4. **报告定稿后**：README 补"文件↔报告章节"链接 + 导出 Report.pdf
5. **Slides + demo 视频录制**——1 天
6. **各人反思 + 贡献记录成文 + zip 组装命名**——半天
7. **AI 申报终稿**（覆盖外部复核文档与本仓代码辅助）——10 分钟

> 结论：**§1 全部内容性要求（Part 1）已 ✅**；剩余全部集中在 Part 2 的"写作与包装"层，其中唯一需要团队新输入的是占位符信息和录屏。
