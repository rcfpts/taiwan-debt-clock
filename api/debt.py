from http.server import BaseHTTPRequestHandler
import json
import re

import requests
import urllib3
from bs4 import BeautifulSoup


# 國庫署目前的 SSL 憑證會讓 requests 驗證失敗
urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

SOURCE_URL = (
    "https://www.nta.gov.tw/"
    "singlehtml/17?cntId=nta_7906_17"
)


class handler(BaseHTTPRequestHandler):

    def do_GET(self):

        try:
            # 取得國庫署網頁
            response = requests.get(
                SOURCE_URL,
                headers={
                    "User-Agent": "Mozilla/5.0"
                },
                timeout=20,
                verify=False
            )

            response.raise_for_status()

            # 解析 HTML
            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # 每一筆國債資料都位於 p 元素
            paragraphs = soup.find_all("p")

            debt_paragraphs = [
                p.get_text(" ", strip=True)
                for p in paragraphs
                if "中央政府債務未償餘額"
                in p.get_text()
            ]

            if not debt_paragraphs:
                raise Exception(
                    "找不到國債鐘資料"
                )

            # 官方網頁第一筆就是最新資料
            latest = debt_paragraphs[0]

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
                raise Exception(
                    "無法解析最新國債鐘資料"
                )

            # 整理成 JSON
            result = {
                "success": True,
                "date": match.group(1),
                "long_term": int(
                    match.group(2).replace(",", "")
                ),
                "short_term": int(
                    match.group(3).replace(",", "")
                ),
                "total": int(
                    match.group(4).replace(",", "")
                ),
                "per_capita": float(
                    match.group(5)
                ),
                "source": SOURCE_URL
            }

            body = json.dumps(
                result,
                ensure_ascii=False
            ).encode("utf-8")

            # 回傳 JSON
            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            # 讓 Google Sites 可以讀這個 API
            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            # 一小時內可使用快取
            self.send_header(
                "Cache-Control",
                "s-maxage=3600, stale-while-revalidate=86400"
            )

            self.end_headers()

            self.wfile.write(body)

        except Exception as error:

            body = json.dumps(
                {
                    "success": False,
                    "error": str(error)
                },
                ensure_ascii=False
            ).encode("utf-8")

            self.send_response(500)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.end_headers()

            self.wfile.write(body)
