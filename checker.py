#!/usr/bin/env python3
"""API 连通性检测小工具。

读取 config.json 中的目标列表，逐个发送请求，记录：
- 是否超时、耗时（毫秒）
- HTTP 状态码是否符合预期
- 返回体片段（以及可选的关键词校验）

结果写入 reports/latest.json（最新报告）和 reports/history.csv（历史记录）。
仅使用 Python 标准库，无需安装任何依赖。
"""

import csv
import json
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
REPORT_DIR = ROOT / "reports"
DEFAULT_TIMEOUT = 10
BODY_SNIPPET_LEN = 200
CSV_COLUMNS = [
    "checked_at", "name", "url", "ok", "status_code",
    "elapsed_ms", "timeout", "error", "body_snippet",
]


def load_targets():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    return config.get("targets", [])


def check_target(target):
    url = target["url"]
    timeout = target.get("timeout", DEFAULT_TIMEOUT)
    expect_status = target.get("expect_status", 200)
    keyword = target.get("expect_keyword")

    result = {
        "name": target.get("name", url),
        "url": url,
        "ok": False,
        "status_code": None,
        "elapsed_ms": None,
        "timeout": False,
        "error": "",
        "body_snippet": "",
    }

    start = time.monotonic()
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "api-health-checker/1.0"}
        )
        with urllib.request.urlopen(
            request, timeout=timeout, context=ssl.create_default_context()
        ) as resp:
            body = resp.read(8192).decode("utf-8", "replace")
            result["status_code"] = resp.status
            result["elapsed_ms"] = round((time.monotonic() - start) * 1000)
            result["body_snippet"] = " ".join(body.split())[:BODY_SNIPPET_LEN]
            if resp.status != expect_status:
                result["error"] = f"状态码 {resp.status}，预期 {expect_status}"
            elif keyword and keyword not in body:
                result["error"] = f"响应体中未找到关键词: {keyword}"
            else:
                result["ok"] = True
    except urllib.error.HTTPError as exc:
        result["status_code"] = exc.code
        result["elapsed_ms"] = round((time.monotonic() - start) * 1000)
        result["error"] = f"HTTP {exc.code}（预期 {expect_status}）"
    except Exception as exc:  # noqa: BLE001 - 记录一切网络异常
        result["elapsed_ms"] = round((time.monotonic() - start) * 1000)
        message = f"{type(exc).__name__}: {exc}"
        result["timeout"] = "timed out" in message.lower() or "timeout" in message.lower()
        result["error"] = "连接超时" if result["timeout"] else message
    return result


def write_reports(results):
    REPORT_DIR.mkdir(exist_ok=True)
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = {
        "checked_at": checked_at,
        "all_ok": all(item["ok"] for item in results),
        "results": results,
    }
    (REPORT_DIR / "latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    csv_path = REPORT_DIR / "history.csv"
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(CSV_COLUMNS)
        for item in results:
            writer.writerow([checked_at, item["name"], item["url"], item["ok"],
                             item["status_code"], item["elapsed_ms"], item["timeout"],
                             item["error"], item["body_snippet"][:100]])
    return report


def main():
    targets = load_targets()
    if not targets:
        print("config.json 中没有配置任何检测目标。")
        return
    results = [check_target(target) for target in targets]
    report = write_reports(results)

    for item in results:
        mark = "OK  " if item["ok"] else "FAIL"
        extra = item["error"] if item["error"] else f"{item['elapsed_ms']}ms"
        print(f"[{mark}] {item['name']} -> status={item['status_code']} {extra}")
    overall = "全部正常" if report["all_ok"] else "存在异常，详见 reports/latest.json"
    print(f"\n检测完成：{overall}")


if __name__ == "__main__":
    main()
