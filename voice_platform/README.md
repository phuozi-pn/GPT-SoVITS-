# voice_platform — 横切平台能力

Python 包名 **`voice_platform`**（避免与标准库 `platform` 冲突）。架构文档中的「Platform 层」指本包。

| 目录 | 说明 | W1 |
|------|------|-----|
| `job/` | Job 模型、Redis 队列、Repository、Pydantic 契约 | ✅ |
| `auth/` | JWT、Redis OTP、User 模型 | ✅ |
| `quota/` | 用量记录、月配额预检/实扣 | ✅ |
| `storage/` | 本地文件存储、公开 URL | ✅ |
| `config.py` | 环境配置、DB Session | ✅ |

Worker 消费 `voice_platform/job` 队列契约；配额在 Job `succeeded` 后实扣。

历史占位目录 `platform/` 仅作说明，请以本包为准。
