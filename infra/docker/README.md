# 平台本地开发 Compose

MVP-0 自研平台依赖：**PostgreSQL + Redis**。API 与 Worker 在本机以 Python 进程运行（W1）。

## 启动

```powershell
cd infra/docker
copy .env.example .env
docker compose -f docker-compose.dev.yml up -d
```

## 停止

```powershell
docker compose -f docker-compose.dev.yml down
```

## 端口（默认）

| 服务 | 端口 |
|------|------|
| PostgreSQL | 5432 |
| Redis | 6379 |

## 数据库迁移

`apps/api/main.py` 启动时执行 `migrations/*.sql`：

- 使用表 `platform_sql_migrations` **每条 SQL 只执行一次**（新库按序全跑；已有数据的库首次升级会把 034 之前的文件标记为已执行）
- 脚本应尽量幂等；**种子/运营类迁移不得覆盖用户已设置的 `cover_image_url` 等字段**

| 文件 | 内容 |
|------|------|
| `001_init.sql` | `voice_versions`、`jobs` + dev 合成种子 |
| `002_train_entities.sql` | `voices`、`consents`、`voice_assets` + dev 训练种子 |
| `003_auth_users.sql` | `users` + dev 用户 |
| `004_quota.sql` | `usage_records` |
| `005_train_asset_engine_uri.sql` | dev 素材 URI 更新 |

## 下一步

启动 API 与 Worker： [apps/api/README.md](../../apps/api/README.md)

## W4 · 镜像发布（可选）

```powershell
cd C:\Users\panta\Desktop\GPT
.\scripts\platform_build_image.ps1 -Tag 20260610-120000
.\scripts\platform_release.ps1 -Tag 20260610-120000
.\scripts\platform_rollback.ps1 -StepsBack 1
```

见 [W4 Hardening 文档](../../docs/architecture/2026-06-10-w4-hardening-可观测与回滚.md)。

引擎 GPU 容器： [../engine/README.md](../engine/README.md)（独立 compose，在上游仓库执行）。
