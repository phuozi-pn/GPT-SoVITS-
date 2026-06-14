# 已弃用：本机 Windows Docker 训练脚本

**训练请用云端 GPU**：[docs/architecture/2026-06-10-云端GPU训练指南.md](../../docs/architecture/2026-06-10-云端GPU训练指南.md)

| 脚本 | 原用途 | 替代 |
|------|--------|------|
| `train_local_wav.py` | 本机 API 触发 Train Worker | 云端 `infra/engine/cloud/train.sh` |
| `prepare_train_dataset.ps1` | Windows Docker 内 ASR 切分 | 云端 `prepare_train_dataset.py` |
| `spike_train_in_container.ps1` | 容器内 Spike | 云端 `train.sh` |
| `engine_run_with_platform_mount.ps1` | 挂载平台目录跑训练 | 仅合成需要引擎容器时，在上游目录 `docker compose run` |

保留文件仅供历史参考，**新流程勿再使用**。
