# GP 数据包交接说明（DATA HANDOFF）

> 生成：2026-09-29，来源：guard-kit 数据池（versionV8-database 私有仓）导出子集
> 用途：MAIB7050 小组项目——两条硬门槛直接达标，SQLite 开箱即查

---

## 一、硬门槛对照（提交包验收项）

| 要求 | 门槛 | 本包 | 状态 |
|---|---|---|---|
| Structured Data | ≥3 个可 SQL 关联实体 | **3 张表**（institutions / evidence_documents / messages，含外键） | ✅ |
| Unstructured / Semi-structured | ≥20 份实质文档 **或** ≥50 条短文本 | **25 份证据文档 + 105 条标注消息**（= 本包 100 + 代码侧爬取 5，见文末附录；全部真实，满足代码侧规格 A/B/C 分类、B1≥12、困难案例 ≥10 与四语种 ≥15%） | ✅✅ |
| Integration | 结构化与非结构化有逻辑连接 | messages/verdicts 可关联 institutions（白名单否决证据链）；evidence_documents 落到 institution_id | ✅ |

## 二、文件清单

```
GP/data/
├── evidence_documents.jsonl   25 份证据文档（每行一份，含全文）
├── messages.jsonl             105 条标注消息（= 本包 100 条 37s/63n + 代码侧爬取 5 条 BEC；全部真实）
├── institutions.json          5 家机构注册表（白名单的种子表）
├── guardkit_course.db         SQLite：上述三张表 + 外键（本包自查用）
└── MESSAGES-SPEC.md           代码侧取数规格（本 messages.jsonl 的验收依据）
```

三表关系：`evidence_documents.institution_id → institutions.institution_id`；
`messages` 独立（筛查对象）；后续 verdicts 表再挂 messages × institutions。

## 三、数据来源与溯源字段（合规要点）

**证据文档**——全部为**公开网页**抓取，四类来源、六个域名：

| evidence_class | 来源域名 | 份数 | 说明 |
|---|---|---|---|
| hkma_bank_alert | shacombank / ocbc / publicbank 等 | 9 | 银行 fraud alert 通告（多数带 content_date） |
| bank_education | hsbc / chiyu 等 | 8 | 银行防骗教育页 |
| police_advisor | cyberdefender.hk | 4 | 港警方防骗资料库骗案条目 |
| gov_press | info.gov.hk | 5 | 政府新闻公报片段 |

每份都带：`source_domain / url / harvested_at（抓取时间戳）/ content_date（部分有）/
lang / category`。抓取方法：定向采集脚本（白名单域名 + DNS 校验），未绕过任何
访问限制；使用范围=课程内分析与展示。**content_date 缺失的文档在字段里是 null，
数据卡如实标注**（主要在 HSBC/ChiYu 教育页与 CyberDefender 条目）。

### 真实性核查（2026-09-29，全部通过）

**25 份证据文档全部为真实抓取，零编造、零合成**（evidence 类不含任何
`synthetic` 标记；LLM 生成的文本只出现在 messages 的 `synthetic_derived=1` 行，
已在字段层隔离）。核查方式：

1. **结构核查**：25/25 具备真实 URL（均为 http(s) 正规域名）+ 正文 ≥80 字；
   20/25 带抓取时间戳，gov_press 5 份按其源 schema 以 content_date 为主溯源
   （harvested_at 置 null，非缺失造假）。
2. **活体抽查**：随机抽两条 URL 线上回访，均返回真实页面且与记录相符——
   - `info.gov.hk/gia/general/202609/16/P2026091600208.htm` → 政府公报真实页
   - `shacombank.com.hk/.../press_20260728_fraudulentwebsites.htm` → 上海商业银行
     2026-07-28 诈骗网站警示通告（与 content_date 一致）
3. **可复查性**：判分人可点开任意 url 比对正文；content_date 与页面日期一致。

**消息**——v4 版按代码侧《MESSAGES-SPEC.md》取数并回应首轮验收意见（2026-09-29）：
**100 条全部真实、零 LLM 生成**（37 scam / 63 normal），时间口径：凡源库带日期的行
均已填 `received_at`（27/98，其余源库无日期、不造假补齐）。

| 类别 | 条数 | 构成 |
|---|---|---|
| A 主骗局（scam） | 38 | 冒充官方 16（邮政/海关/水务/税务/入境处/中旅社）、缴费/账单钓鱼 8、投资 5、兼职任务 4、中奖诱饵 3、杀猪盘/情感 2；含 2026 新骗术（.shop/.click、FPS 仿冒、演唱会代购） |
| B 正常（normal） | 63 | B1 机构通知 **26**（8 政府公报 + 8 真实银行警示 + **10 真实银行账单/按揭/月结单/存款到期 SMS**——首轮缺的账单体裁已补）/ B2 日常 29（真实 SMS 三语 + 网络聊天）/ B3 灰区 4 |
| C 困难案例 | 15（note 标注） | C1 对话体假借钱测警觉（W12-N16）/ C2 广告 / C3 高难负样本 / C4 2026 新骗术 |

**语言分布**：zh-HK 36（36%，为主）/ en 31 / mixed 18 / zh 15——四类均 ≥15%。
**纯粤语口语 scam 13 条**（首轮验收缺口已补，含对话体杀猪盘/投资群/任务派单）。

**标注政策（重要）**：
- **全部真实**（`synthetic_derived=false` 全表）：来源为规格白名单——团队盲测卷
  （blind-v10/v12/n200/n400/n1000v2，其中 real_* 990 条为可证真实 SMS 语料）、
  2026 年 HKMA/银行警示抓取（URL+content_date 溯源）、政府公报、网络语言采集。
- **文本逐字**：未清洗/改写/补标点；可疑裸域名按原样保留（非可点击链接）。
- **无真实个人信息**：PII 扫描（邮箱/电话/证件号）0 命中。
- **license**：25 份证据文档已补 `license_note`（诚实口径：© 机构保留版权，
  逐字引用 + URL + 日期用于课程研究）。
- 局限声明：v10–v12/n200/n400 为团队早期采集卷，卷内原始出处粒度有限
  （n1000v2 real_* 与 2026 抓取部分溯源最完整）。

### ⚠️ 两个无法以「真实」满足的缺口（需代码侧决策，数据侧不造假补齐）

1. **A1 BEC 真实文本 = 0（全库扫描确认）**：应用户要求已对两仓全部 111 个数据文件、
   279,495 行做 BEC 模式全扫——命中 448 条中，可证真实的仅有银行/警方** advisory 描述文**
   （非消息体），其余为 LLM 改写（禁用）与 v7 时代写作增广（corpus impersonation 类，
   含复写文本与占位号码，不可当真实）。真实 BEC 催付邮件原文从不被官方逐字公开
   （警务处 BEC 专页只描述手法）。建议：判决卡①保留 demo-written 原型并在评估节
   如实标注；或授权数据侧定向采集警务处 BEC 案例页找逐字引文（产出无法保证）。
2. **B1 真实「账单/月结单」= 0**：真实个人账单 SMS 含个人数据，公开渠道不可得
   （隐私红线，课程 §1.5 自身也禁止）。已以**真实银行/HKMA 客户通告**替代
   （16 条机构通知均为真实官方客户文本）；如需账单体演示，建议沿用 MSG-002 式
   demo-written 并如实标注。

**给代码侧的声明措辞（Generated data，按现包如实改写）**：
> All data in this package are real: evidence documents are verbatim excerpts from
> public HKMA/bank/police/government pages (URL and access date recorded); messages
> are drawn from the team's real-labelled corpora and 2026 official fraud alerts.
> No AI-generated text is included in the data package. AI tools were used for
> pipeline engineering and drafting only; all outputs were human-checked.

## 四、开箱即查（示例 SQL，已验证可跑）

```sql
-- 每家机构的证据文档数
SELECT i.name, COUNT(*) AS docs
FROM evidence_documents e JOIN institutions i ON e.institution_id = i.institution_id
GROUP BY 1 ORDER BY docs DESC;

-- 消息类别 × genre 交叉表（volume=来源卷，note=困难案例标注）
SELECT volume, label, COUNT(*) FROM messages GROUP BY 1, 2 ORDER BY 1, 2;

-- 困难案例清单（评估节素材）
SELECT msg_id, label, note FROM messages WHERE note IS NOT NULL;

-- 白名单机构（authority）的证据都说了什么类别的骗术
SELECT e.category, COUNT(*) FROM evidence_documents e
JOIN institutions i ON e.institution_id = i.institution_id
WHERE i.whitelist_flag = 1 GROUP BY 1;
```

## 五、与项目七要素的对位提示

| 要素 | 用哪个文件 |
|---|---|
| 2 Data sources | evidence_documents.jsonl（公开页来源+时间戳） |
| 3 Relational core | guardkit_course.db 三表（建议再加 verdicts 表挂 messages） |
| 4 Flexible evidence layer | evidence_documents 的 url/date/category 元数据 + JSON 原文 |
| 5 Retrieval | messages.jsonl 做检索对象；evidence 做语义检索库 |
| 6 Traceable output | verdict → 引用 evidence_documents.url + content_date |
| 7 Governance | 见「标注政策」与「局限」；另注意：消息文本不含任何真实个人信息 |

## 六、明确不在本包里的

- guard-kit 全量语料（1.3 万+ 条）与训练管线——超出课程需要，未导出
- 模型权重、打分引擎——课程里作为「打分组件」调用即可，不需要随包提交
- v3.0 历史版本与审计文档——科研线私有仓内容

---

## 附：代码侧追加记录（2026-09-29，接上节之后）

- `messages.jsonl` 现为 **105 条** = 本包 100 条（全部真实，37 scam / 63 normal）+ **代码侧爬取追加 5 条真实 BEC 邮件**（`volume=public-nazario`，msg_id `pub-nz-*`，来源 Nazario honeypot 公开语料 phishing-2024/2025，正文逐字、溯源写入 `note` 字段）。
- 两版 B1 缺口（机构通知类）与 C 类困难案例已由本包补齐；A1（冒充供应商换账户 BEC）真实样本中的英文部分由上述 5 条补足，**粤语 BEC 仍缺**，后续按 MESSAGES-SPEC A1 从盲测卷补充。
- 建库口径以 `python3 src/build_db.py` 输出为准（当前：messages=108 含 3 条演示，硬门槛双达标）。
