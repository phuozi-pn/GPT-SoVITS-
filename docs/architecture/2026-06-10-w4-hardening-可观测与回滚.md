# W4 · 可观测、告警与镜像回滚

| 项 | 内容 |
|----|------|
| **日期** | 2026-06-10 |
| **状态** | MVP-0 W4 已落地（轻量版） |
| **上级** | [路线图 §7.1](./sections/07-路线图与追溯.md) |

---

## 1. Trace（全链路）

| 能力 | 实现 |
|------|------|
| API 入站 | `TraceMiddleware` 读取/生成 `X-Trace-Id`，响应头回传 |
| Job 落库 | `jobs.trace_id`（已有 migration 001） |
| Worker 日志 | `job_id` + `trace_id` 结构化字段 |
| 前端 | `sessionStorage` + 请求头 `X-Trace-Id` |
| Job 查询 | `GET /api/v1/jobs/{id}` 返回 `trace_id` |

日志格式（默认文本）：

```text
2026-06-10 12:00:00 INFO [abc-trace] apps.api.middleware.trace: GET /api/v1/synthesis -> 202 45.2ms
```

JSON 模式：`.env` 设 `LOG_JSON=true`。

---

## 2. 失败告警（飞书 Webhook）

`.env`：

```env
ALERT_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxx
ALERT_ON_JOB_FAILURE=true
ALERT_WEBHOOK_FORMAT=feishu   # 或 generic
```

触发点：`JobRepository.mark_failed()`（合成/训练/批量全失败）。

消息示例：

```text
[Voice Platform] Job failed
job_id: ...
job_type: synthesize
trace_id: ...
error: Engine set_gpt_weights failed (502)
```

---

## 3. 镜像发布与回滚

```powershell
cd C:\Users\panta\Desktop\GPT

# 构建并记录版本
.\scripts\platform_build_image.ps1 -Tag 20260610-120000

# 发布（写 .runtime/releases.json + compose 拉起 api/workers）
.\scripts\platform_release.ps1 -Tag 20260610-120000

# 回滚到上一版
.\scripts\platform_rollback.ps1 -StepsBack 1
```

清单：`.runtime/releases.json`（最近 10 个 tag）。

Compose：`infra/docker/docker-compose.platform.yml`（叠加 `docker-compose.dev.yml` 的 PG/Redis）。

健康检查：`GET /health` → `{ "status": "ok", "release": "<tag>" }`。

---

## 4. 运维检查清单

| 检查 | 命令 |
|------|------|
| 当前 release | `curl http://127.0.0.1:8001/health` |
| 发布历史 | `Get-Content .runtime\releases.json` |
| 追踪某次失败 | API 响应头 `X-Trace-Id` → 搜 worker 日志 / DB `jobs.trace_id` |
| 告警测试 | 故意让合成失败（停 9880）→ 飞书收到消息 |

---

## 5. 测试

```powershell
pytest tests/test_observability.py -q
```

---

## 6. 后续（MVP+1）

- OpenTelemetry 导出 / Grafana
- 批量「部分失败」阈值告警
- K8s Helm + 多副本 infer 池
