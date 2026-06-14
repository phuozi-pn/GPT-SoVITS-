# workers — 异步 Worker

| 目录 | 说明 | 运行时 |
|------|------|--------|
| `infer/` | TTS → api_v2 `/tts` 或 Mock | 本机 9880 |
| `train/` | 微调 Adapter（**默认 Mock**） | 云端 GPU 手工训练，见下方 |

**GPU 微调推荐路径**：[云端 GPU 训练指南](../docs/architecture/2026-06-10-云端GPU训练指南.md)（`infra/engine/cloud/train.sh`）。

平台 `Train Worker` 保留供后续 SaaS 化；本机 `.env` 保持 `TRAIN_MOCK=true` 即可。

## 运行

```powershell
# Infer（Mock）
$env:ENGINE_MOCK="true"
python -m workers.infer.runner

# Infer（真引擎 9880）
$env:ENGINE_MOCK="false"
python -m workers.infer.runner

# Train（Mock，默认）
python -m workers.train.runner
```

队列键：`jobs:infer` · `jobs:train`（Redis）

引擎合成：[infra/engine/README.md](../infra/engine/README.md)
