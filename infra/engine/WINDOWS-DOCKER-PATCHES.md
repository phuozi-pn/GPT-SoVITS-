# Windows Docker 一次性修改清单

> 下列修改保存在 **本机磁盘**，`docker compose run` 重启容器**不会**丢失。  
> 仅当你 `git checkout` / 拉上游覆盖文件时才需重做「一次性」项。

## 一次性（改完就不用再改）

| 位置 | 修改 | 作用 |
|------|------|------|
| `GPT-SoVITS/docker-compose.yaml` | Lite 服务 **删除** `./tools/asr/models`、`uvr5_weights` 两行 volume；保留 `.:/workspace/GPT-SoVITS` | 避免 Windows 联接点挂载失败 |
| `GPT-SoVITS/docker-compose.yaml` | 删除所有 `/dev/null:` 挂载（若有） | Windows 不支持 |
| `GPT-SoVITS/docker-compose.yaml` | `shm_size: "16g"` | 防 OOM |
| `GPT-SoVITS/docker-compose.yaml` | 叠加 [docker-compose.platform-mount.yaml](./docker-compose.platform-mount.yaml) | 挂载本产品到 `/workspace/GPT`（微调 Spike 方式 B） |
| `GPT-SoVITS/GPT_SoVITS/inference_webui.py` | `_resolve_pretrained_path` + `safe_load_audio` | 英文模型名 + 读 wav |
| `GPT-SoVITS/GPT_SoVITS/inference_webui_fast.py` | 同上（若用并行推理） | 同上 |
| `GPT-SoVITS/tools/my_utils.py` | `safe_torchaudio_load` | api_v2 读参考音频 |
| `GPT-SoVITS/GPT_SoVITS/TTS_infer_pack/TTS.py` | 使用 `safe_torchaudio_load` | 同上 |
| `GPT-SoVITS/GPT_SoVITS/prepare_datasets/2-get-sv.py` | `safe_torchaudio_load` 替代 `torchaudio.load` | 微调 1B-sv；Spike 脚本会自动 patch（见 `patches/apply_train_torchaudio_patch.sh`） |
| `GPT-SoVITS/GPT_SoVITS/configs/tts_infer_v2pro.yaml` | v2Pro 权重 | api_v2 |
| `GPT-SoVITS/scripts/docker-api-v2-start.sh` | 启动 9880 | 平台 Worker 调用 |

## 每次新容器都要做（约 10 秒）

`docker compose run` 每次会起**新容器**，容器内 pip 包装的环境**不保留**，因此：

```bash
bash scripts/docker-webui-start.sh
```

脚本会自动 `pip install starlette<1.0` 并 `python webui.py`。  
**不需要**手改代码或改 compose。

## 每次启动固定习惯（不是改配置）

| 习惯 | 说明 |
|------|------|
| 浏览器用 `127.0.0.1` | 不要用日志里的 `0.0.0.0`（会 502） |
| 推理走 9872 | 9874 → 1C-推理 → 开启 TTS → 打开 9872 |
| 可选 `--remove-orphans` | 清理旧 run 容器警告 |

## 仅当再次报错时才做

| 现象 | 操作 |
|------|------|
| `CreateFile tools/asr/models` | 确认 compose 未恢复 asr 挂载；PowerShell：`rmdir` 联接点后 `mkdir` 真实目录 |
| 推理/FileNotFoundError 英文模型名 | 检查 `inference_webui.py` patch 是否被 git 覆盖 |
| 合成 libtorchcodec | 检查 `safe_load_audio` patch 是否还在 |
| 微调 1B-sv / `libtorchcodec` | 重跑 Spike（自动 patch `2-get-sv.py`）或手动执行 `infra/engine/patches/apply_train_torchaudio_patch.sh` |
| GPT 报缺 `6-name2semantic.tsv` | 上游 1C 产出 `6-name2semantic-0.tsv`；平台 Spike 脚本已合并为 WebUI 同款路径 |
| SoVITS 保存 `G_*.pth` FileNotFoundError | WebUI 会 `mkdir logs_s2_<version>`；Spike 已补齐；续跑：`.\scripts\spike_train_in_container.ps1 -FromStep sovits` |
| GPT resume / `weights_only` / `PosixPath` | 勿全量重跑；续跑 SoVITS：`-FromStep sovits`；若必须重跑 GPT，脚本会在训练前清空 `logs_s1_*/ckpt` |
| 9880 连接被意外关闭 | `api_v2` 未起 → `scripts/engine_api_v2.ps1 -Action start` |
| 9880 `address already in use` | 已有 api_v2 → `engine_api_v2.ps1 status`；勿重复 `python api_v2.py` |
| 重复 `docker compose run` / 9874 占用 | 只保留一个引擎容器；`engine_docker_cleanup.ps1`；复用 `docker exec` |
