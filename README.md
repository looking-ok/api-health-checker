# api-health-checker

API 连通性检测小工具：定时检测一组 API / 网站，自动记录**超时、状态码、耗时和返回体片段**，并把结果提交回仓库。

## 项目结构

```
api-health-checker/
├── checker.py                    # 检测脚本（仅用 Python 标准库，无需装依赖）
├── config.json                   # 检测目标列表（要测什么改这里）
├── reports/
│   ├── latest.json               # 最新一次检测结果
│   └── history.csv               # 历史记录（每次检测追加）
└── .github/workflows/check.yml   # GitHub Actions：每小时自动检测
```

## 本地运行

```
python checker.py
```

输出示例：

```
[OK  ] GitHub API -> status=200 312ms
[FAIL] 百度 -> status=None 连接超时
```

## 添加检测目标

编辑 `config.json`，往 `targets` 里加一项即可：

```json
{
  "name": "我的服务",
  "url": "https://example.com/api/ping",
  "timeout": 10,
  "expect_status": 200,
  "expect_keyword": "pong"
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `name` | 否 | 显示名称，默认用 url |
| `url` | ✅ | 检测地址 |
| `timeout` | 否 | 超时秒数，默认 10 |
| `expect_status` | 否 | 预期状态码，默认 200 |
| `expect_keyword` | 否 | 要求返回体中包含的关键词 |

## 自动运行

仓库已配置 GitHub Actions（`.github/workflows/check.yml`）：

- **每小时自动运行**一次，结果自动提交到 `reports/`
- 也可以在仓库 **Actions → API 健康检查 → Run workflow** 手动触发

## 注意事项

- 检测需要密钥的 API 时，不要把 key 写进 `config.json`，应使用仓库的 **Settings → Secrets and variables → Actions**，脚本里再从环境变量读取
- `reports/history.csv` 会持续增长，过大时可以清空重来
