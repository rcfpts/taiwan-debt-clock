import requests
import urllib3
import re
import json
import os

from datetime import datetime, timezone, timedelta

from bs4 import BeautifulSoup

import gspread
from google.oauth2.service_account import Credentials


urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ==============================
# 基本設定
# ==============================

SOURCE_URL = (
    "https://www.nta.gov.tw/"
    "singlehtml/17?cntId=nta_7906_17"
)

SHEET_NAME = "國債資料"


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


# 官方第一筆就是最新資料
latest = debt_paragraphs[0]


# ==============================
# 解析最新資料
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
# 整理資料
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


print(
    "抓到最新資料：",
    json.dumps(
        data,
        ensure_ascii=False
    )
)


# ==============================
# 讀取 GitHub Secrets
# ==============================

service_account_json = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_JSON"
)

spreadsheet_id = os.environ.get(
    "GOOGLE_SHEET_ID"
)


if not service_account_json:
    raise RuntimeError(
        "找不到 GOOGLE_SERVICE_ACCOUNT_JSON"
    )


if not spreadsheet_id:
    raise RuntimeError(
        "找不到 GOOGLE_SHEET_ID"
    )


# ==============================
# 登入 Google Sheets
# ==============================

credentials_info = json.loads(
    service_account_json
)


scopes = [
    "https://www.googleapis.com/auth/spreadsheets"
]


credentials = (
    Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )
)


client = gspread.authorize(
    credentials
)


spreadsheet = client.open_by_key(
    spreadsheet_id
)


worksheet = spreadsheet.worksheet(
    SHEET_NAME
)


# ==============================
# 讀取目前 Sheet
# ==============================

rows = worksheet.get_all_records()


# 建立 key → 列號 對照
# 第 1 列是表頭，所以資料從第 2 列開始

key_to_row = {}

for index, row in enumerate(
    rows,
    start=2
):

    key = str(
        row.get("key", "")
    ).strip()

    if key:
        key_to_row[key] = index


# ==============================
# 要自動更新的資料
# ==============================

updates = {
    "central_total": {
        "value": data["total"],
        "unit": "億元"
    },

    "long_term": {
        "value": data["long_term"],
        "unit": "億元"
    },

    "short_term": {
        "value": data["short_term"],
        "unit": "億元"
    },

    "per_capita": {
        "value": data["per_capita"],
        "unit": "萬元"
    }
}


# ==============================
# 更新 Sheet
# ==============================

for key, item in updates.items():

    if key not in key_to_row:
        print(
            f"找不到 key：{key}，跳過"
        )
        continue

    row_number = key_to_row[key]

    # C欄：數值
    worksheet.update_cell(
        row_number,
        3,
        item["value"]
    )

    # D欄：單位
    worksheet.update_cell(
        row_number,
        4,
        item["unit"]
    )

    # E欄：資料日期
    worksheet.update_cell(
        row_number,
        5,
        data["date"]
    )

    # F欄：更新方式
    worksheet.update_cell(
        row_number,
        6,
        "自動"
    )

    # G欄：資料來源
    worksheet.update_cell(
        row_number,
        7,
        "財政部國庫署"
    )

    # H欄：來源網址
    worksheet.update_cell(
        row_number,
        8,
        SOURCE_URL
    )

    print(
        f"已更新：{key}"
    )


# ==============================
# 額外輸出 debt.json
# 保留原本 GitHub Pages 用途
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


print("Google Sheet 更新完成")
print("docs/debt.json 更新完成")
