# -*- coding: utf-8 -*-
"""GuardKit v7 评分组件——课程仓内置快照（pinned snapshot）。

来源：guard-kit v7 现役评分器（P3NN4L/guard-kit-code，training/evolve.py，
白名单 v4 定版，2026-09-27），逐字快照；权重为公开包 @p3nn4l/guard-kit@7.0.0
的 models/radar.json。课程项目按提案以「pinned dependency」方式消费引擎：
本文件与 radar.json 一起构成只读依赖，不在此仓中修改。
与 npm 包 TS 推理的一致性由 v7 仓守门（training/verify/verify-ml.ts，≤1e-6），
本仓 tests/test_parity.py 另验证本快照与 v7 训练侧逐位一致。

仅需 Python 3 标准库（无 sklearn 依赖）。
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

# 官方提示白名单：反诈主题词 × 官方建议词
NOTICE_TOPIC = re.compile(
    r"反詐|反诈|防騙|防骗|防範|防范|anti-?deception|anti-?fraud"
    r"|騙案.{0,4}(宗|多|增|上升|數據|警示)|诈骗.{0,4}(宗|多|增|上升)|被騙.{0,4}個案|被骗.{0,4}个案"
    r"|防騙講座|防骗讲座|反詐騙宣傳|反诈骗宣传|scamalert|fraudwarning|fraudalert"
    r"|詐騙高發|诈骗高发|高發期|高发期|詐騙警示|诈骗警示|如非本人|非本人交易|非本人操作")
NOTICE_ADVICE = re.compile(
    r"(撥打|拨打|致电|致電|打)\s*(18222|110|999|96110)"
    r"|(熱線|热线|舉報|举报|掛線|挂断|掛斷|切勿|毋須|无须|核實|核实|never\s*ask|hang\s*up|hotline|report\s*it|do\s*not\s*transfer)"
    r"|小心|提防|警惕|唔好亂|唔好(匯|汇|轉|转|信|理)|不要輕信|不要轻信|beware"
    r"|不會以電話|不会以电话|唔會以電話|唔会以电话|不會要求|不会要求|唔會要求|唔会要求")
# 官方域名白名单 × 无可疑 URL 记号
OFFICIAL_DOMAIN = re.compile(
    r"gov\.hk|hongkongpost\.hk|edu\.hk|hsbc\.com\.hk|hangseng\.com|bochk\.com"
    r"|icbc\.com\.hk|dahsing\.com|citibank\.com\.hk")
BAD_URL_TOKEN = re.compile(r"(?:\.|/)(?:top|xyz|click|icu|vip|club|shop|live|rest|monster|buzz)(?:$|[^a-z])")
# 机构通知白名单 v4：机构通知主题 × 官方渠道指引 × 无可疑 URL（三重条件）
INSTITUTIONAL_TOPIC = re.compile(
    r"月結單|月结单|賬單|账单|學費|学费|選課|选课|網上註冊|网上注册|消費券|消费券"
    r"|里數|里数|里程|保險|保险|續保|续保|財務處|财务处|政府公告"
    r"|註冊組|注册组|管理處|管理处|客務中心|客务中心"
    r"|勞工處|劳工处|運輸署|运输署|社會福利署|社会福利署|警務處|警务处|警署"
    r"|醫管局|医管局|醫院管理局|法律援助|職業退休金|职业退休金|強積金|强积金|公積金|公积金"
    r"|入境事務|稅務局|税务局|學生會|学生会|教務處|教务处|學費分期|学费分期"
    r"|定期存款|按揭|信用咭|信用卡|簽賬|签账|簽帳|签帐|自動轉賬|自动转账|轉數快|转数快"
    r"|雙重認證|双重认证|匯率|汇率|餘額|余额|結餘|结余"
    r"|實習|实习|課程註冊|课程注册|course\s*registration|失物認領|失物认领|失物招領|失物招领"
    r"|數據用量|数据用量|水費|水费|電費|电费|醫療報告|医疗报告")
SAFE_CHANNEL = re.compile(
    r"無需任何|无需任何|毋須回[覆复]|无须回[覆复]|不含任何連結|不含任何链接"
    r"|不會以訊息|不会以讯息|不會以電話|不会以电话|唔會以電話|唔会以电话"
    r"|於App內|于App内|App內|App内|myPortal|MyPortal"
    r"|致電\s*183|致电\s*183|致電\s*2233|致电\s*2233"
    r"|聯絡.{0,8}註冊組|联络.{0,8}注册组|客戶經理|客户经理"
    r"|(如需查詢|如需协助|如需協助|如有查詢|如有查询|如有疑問|如有疑问).{0,6}(致電|致电|聯絡|联络|親臨|亲临)"
    r"|請致電\s*\d{4}\s*\d{4}|请致电\s*\d{4}\s*\d{4}"
    r"|歡迎親臨|欢迎亲临"
    r"|網上理財|网上理财|網上銀行|网上银行|mobile\s*app|app內|app内|app或網站|app或网站|myportal"
    r"|(不會|唔會|不会)(致電|致电)?要求"
    r"|已寄出|郵寄|邮寄"
    r"|(證明書|证明书|通知書|通知书|報表|报表|賬單|账单|月結單|月结单).{0,16}(寄出|寄到|送達|送达|發出|发出)"
    r"|學生入口|学生入口|student\s*portal|官方帳號|官方账号|辦公時間|办公时间|學生證核對|学生证核对"
    r"|noimmediateaction|willbe(emailed|issued|sent)|aninvoice"
    r"|交易已成功|已成功入賬|已成功入账|已成功處理|已成功处理|已成功繳付|已成功缴付|已成功續期|已成功续期|已存入")

RAW_MID = 0.455
RAW_HIGH = 0.505


def norm_text(t: str) -> str:
    t = unicodedata_normalize(t)
    return "".join(t.split())


def unicodedata_normalize(t: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKC", t).lower()


def load_model(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def make_scorer(model: dict):
    """与 v7 训练侧同公式：n-gram → sublinear tf×idf → L2 → softmax → Platt 校准，
    白名单压档 → 双条件判档。返回 score(text) = (pred, probs, p_cal, p_raw)。"""
    vocab, idf, coef, intercept = model["vocab"], model["idf"], model["coef"], model["intercept"]
    labels, platt, bands = model["labels"], model["platt"], model["bands"]
    eps = 1e-9

    def score(text: str):
        t = norm_text(text)
        n = len(t)
        cnt = defaultdict(int)
        for i in range(n):
            for l in (1, 2, 3):
                if i + l > n:
                    break
                j = vocab.get(t[i:i + l])
                if j is not None:
                    cnt[j] += 1
        if not cnt:
            return "normal", {}, 0.0, 0.0
        v = [0.0] * len(idf)
        for j, c in cnt.items():
            v[j] = (1.0 + math.log(c)) * idf[j]
        nv = math.sqrt(sum(x * x for x in v))
        if nv > 0:
            v = [x / nv for x in v]
        margins = [intercept[k] + sum(w * x for w, x in zip(row, v) if x != 0)
                   for k, row in enumerate(coef)]
        mx = max(margins)
        exps = [math.exp(m - mx) for m in margins]
        ssum = sum(exps)
        probs = {labels[k]: exps[k] / ssum for k in range(len(labels))}
        p_scam = 1 - probs["normal"]
        logit = math.log((p_scam + eps) / (1 - p_scam + eps))
        p_cal = 1 / (1 + math.exp(-(platt["a"] * logit + platt["b"])))
        if NOTICE_TOPIC.search(t) and NOTICE_ADVICE.search(t):
            p_scam = min(p_scam, bands["mid"] - 0.01)
            p_cal = min(p_cal, bands["mid"] - 0.01)
        if OFFICIAL_DOMAIN.search(t) and not BAD_URL_TOKEN.search(t):
            p_scam = min(p_scam, bands["mid"] - 0.01)
            p_cal = min(p_cal, bands["mid"] - 0.01)
        if INSTITUTIONAL_TOPIC.search(t) and SAFE_CHANNEL.search(t) and not BAD_URL_TOKEN.search(t):
            p_scam = min(p_scam, bands["mid"] - 0.01)
            p_cal = min(p_cal, bands["mid"] - 0.01)
        mid = p_cal >= bands["mid"] and p_scam >= RAW_MID
        pred = "scam" if mid else "normal"
        return pred, probs, p_cal, p_scam

    return score
