import requests
import urllib3
import re
import json
import os
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup


urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


SOURCE_URL = (
    "https://www.nta.gov.tw/"
    "singlehtml/17?cntId=nta_7906_17"
)


# ==============================
# 抓取國庫署網頁
# ==============================

response = requests.get(
    SOURCE_URL,
    headers={
        "User-Agent": "Mozilla/5.0"
    },
    timeout=30,
    verify=False
)

response.raise_for_status()


# ==============================
# 解析 HTML
# ==============================

soup = BeautifulSoup(
    response.text,
    "html.parser"
)

paragraphs = soup.find_all("p")


debt_paragraphs = [
    p.get_text(" ", strip=True)
    for p in paragraphs
    if "中央政府債務未償餘額"
    in p.get_text()
]


if not debt_paragraphs:
    raise RuntimeError(
        "找不到國債鐘資料"
    )


# 官方網站第一筆即最新資料
latest = debt_paragraphs[0]


# ==============================
# 解析最新一筆
# ==============================

pattern = re.compile(
    r"截至\s*"
    r"(\d{3}年\d{2}月\d{2}日)"
    r".*?"
    r"1年以上\s*([\d,]+)"
    r"\s*\(億元\)"
    r".*?"
    r"短期\s*([\d,]+)"
    r"\s*\(億元\)"
    r".*?"
    r"合計\s*([\d,]+)"
    r"\s*\(億元\)"
    r".*?"
    r"平均每人負擔債務"
    r"\s*[:：]\s*"
    r"([\d.]+)"
    r"\s*\(萬元\)"
)


match = pattern.search(latest)


if not match:
    raise RuntimeError(
        "無法解析國債鐘資料"
    )


# ==============================
# 建立 JSON
# ==============================

taiwan_tz = timezone(
    timedelta(hours=8)
)


data = {
    "success": True,

    "date":
        match.group(1),

    "long_term":
        int(
            match.group(2)
            .replace(",", "")
        ),

    "short_term":
        int(
            match.group(3)
            .replace(",", "")
        ),

    "total":
        int(
            match.group(4)
            .replace(",", "")
        ),

    "per_capita":
        float(
            match.group(5)
        ),

    "source":
        SOURCE_URL,

    "checked_at":
        datetime.now(
            taiwan_tz
        ).isoformat()
}


# ==============================
# 輸出到 docs/debt.json
# ==============================

os.makedirs(
    "docs",
    exist_ok=True
)


with open(
    "docs/debt.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        data,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )
)
