# -*- coding: utf-8 -*-
"""共享文本处理：规范化、字符 bigram、FTS 索引串、PII 扫描。

run_demo.py（查询侧）与 build_db.py（索引侧）共用同一实现，
保证 FTS 索引串与查询串的构造方式一致。
"""

import re


def norm(t: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", t.lower())


def bigrams(t: str) -> set:
    t = norm(t)
    return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else {t}


def fts_tokens(t: str) -> str:
    """FTS5 索引串：CJK 无空格分词，按字符 bigram 切开（unicode61 兼容）。"""
    return " ".join(sorted(bigrams(t)))


def fts_query(t: str) -> str:
    """FTS5 查询串：bigram 以 OR 连接（裸空格是隐式 AND，几乎必然零命中），
    相关度排序交给 bm25。"""
    return " OR ".join(sorted(bigrams(t)))


# PII 扫描：邮箱 / 电话 / 香港身份证号。
# 电话三形态（降低误报）：852 前缀、4+4 分隔写法、或「電話/熱線/fax」等上下文词后的 8 位连写——
# 裸 8 位连写不单独命中（HKMA 恶意网站清单等文档里的编号/路径数字会误报）。
# 脱敏边界（治理口径）：个人邮箱/身份证必脱敏；公司客服热线与公共角色邮箱（info@/cs@…）
# 是公开通告的正式内容（建议动作就是拨打），保留原文以维持逐字引用。
PII_PATTERNS = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone", re.compile(r"(?:(?:\(\s?852\s?\)|\+?852[\s\-]?)\d{7,8}\b|\b\d{4}[\s\-]\d{4}\b|(?:電話|电话|tel(?:\:)?|hotline|熱線|热线|傳真|传真|fax)[^\d]{0,6}\d{8}\b)", re.IGNORECASE)),
    ("hkid", re.compile(r"\b[A-Z]{1,2}\d{6}\(?[0-9A]\)?")),
]
PHONE_CORPORATE_CONTEXT = re.compile(
    r"(?:customer\s+service\s+hotline|service\s+hotline|hotline|熱線|热线|客戶服務|客户服务|辦事處|办事处)[^.\n]{0,30}$",
    re.IGNORECASE)
EMAIL_ROLE_LOCAL_PARTS = {"info", "cs", "enquiry", "enquiries", "service", "support", "admin", "contact", "help"}


def _pii_findings(t: str):
    """与 pii_redact 同口径的命中枚举（公司热线/角色邮箱不算）。
    返回 [(kind, matched_text)]。"""
    out = []
    for kind, pat in PII_PATTERNS:
        for m in pat.finditer(t):
            if kind == "email" and m.group(0).split("@")[0].lower() in EMAIL_ROLE_LOCAL_PARTS:
                continue
            if kind == "phone" and PHONE_CORPORATE_CONTEXT.search(t[max(0, m.start() - 40):m.start()]):
                continue
            out.append((kind, m.group(0)))
    return out


def pii_scan_count(t: str) -> int:
    """疑似个人联系信息命中数（与 pii_redact 同口径，公司联系方式不计）。"""
    return len(_pii_findings(t))


def pii_redact(t: str):
    """证据段落脱敏：个人邮箱 / 身份证 / 非公司语境电话；公司热线与角色邮箱保留。
    返回 (脱敏文本, 实际脱敏数)。"""
    n = 0

    def mask(s: str) -> str:
        return s[:2] + "***" if len(s) > 4 else "***"

    def sub_email(m):
        nonlocal n
        local = m.group(0).split("@")[0].lower()
        if local in EMAIL_ROLE_LOCAL_PARTS:
            return m.group(0)  # 公共角色邮箱=机构联系方式，保留
        n += 1
        return mask(m.group(0))

    def sub_phone(m):
        nonlocal n
        head = t[max(0, m.start() - 40):m.start()]
        if PHONE_CORPORATE_CONTEXT.search(head):
            return m.group(0)  # 公司客服热线=通告正式内容，保留
        n += 1
        return mask(m.group(0))

    def sub_hkid(m):
        nonlocal n
        n += 1
        return mask(m.group(0))

    t = PII_PATTERNS[0][1].sub(sub_email, t)
    t = PII_PATTERNS[1][1].sub(sub_phone, t)
    t = PII_PATTERNS[2][1].sub(sub_hkid, t)
    return t, n
