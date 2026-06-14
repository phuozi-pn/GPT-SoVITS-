# GPT-SoVITS · Docker 运行指南（Windows / Linux）

> **微调训练**：请用 [云端 GPU 训练指南](../../docs/architecture/2026-06-10-云端GPU训练指南.md)（`infra/engine/cloud/train.sh`），**不要**在本机 Windows Docker 里跑微调。  
> **本指南用途**：在本机 Docker 跑 WebUI / **9880 合成**。

> 代码与 compose 在**上游仓库**（非本产品 `GPT` 仓库）。  
> MVP pinned：`git checkout 20250606v2pro`  
> **平台对接**：零样本推理 ✅ · api_v2 `:9880` ✅

---

## 0. 前置条件

| 项 | 要求 |
|----|------|
| Docker | [Docker Desktop](https://www.docker.com/products/docker-desktop/)（Windows 建议开 **WSL2 后端**） |
| GPU | NVIDIA + 驱动正常（`nvidia-smi` 有输出） |
| Docker GPU | Desktop → Settings → Resources → 启用 GPU（或 WSL2 内已装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)） |
| 磁盘 | ≥30GB（镜像 + 权重 + 缓存） |

```powershell
docker --version
docker compose version
nvidia-smi
```

---

## 1. 克隆上游并切换版本

**必须在项目根目录操作**（Compose 会挂载当前目录全部文件）。

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
git checkout 20250606v2pro
git pull   # 可选：与 compose 里镜像 tag 对齐
```

---

## 2. 镜像怎么选

### 2.1 先看 Docker Hub 标签

代码更新比镜像快，启动前到 Docker Hub 看**当前可用 tags**（仓库名见上游 README，一般为项目维护者发布的 `gpt-sovits` 系列镜像）。

Compose 会按 CPU 架构自动拉 **amd64 / arm64**。

### 2.2 四个 Compose 服务

| 服务名 | 说明 |
|--------|------|
| `GPT-SoVITS-CU126-Lite` | CUDA 12.6 轻量版（Hub 上 `latest` 常指向此类） |
| `GPT-SoVITS-CU128-Lite` | CUDA 12.8 轻量版 — **RTX 5080 等新卡优先试** |
| `GPT-SoVITS-CU126` | CUDA 12.6 **完整版**（含更多 bundled 模型） |
| `GPT-SoVITS-CU128` | CUDA 12.8 完整版 |

| 对比 | Lite | 完整版 |
|------|------|--------|
| 体积 / 依赖 | 更小 | 更大 |
| ASR 模型 | **不含**；需要时程序**自动下载** | 已包含 |
| UVR5 模型 | **不含**；需**自行下载** | 已包含 |
| Spike（训练+合成） | 通常够用 | Lite 报错再换 |

### 2.3 环境变量 `is_half`

| 值 | 含义 |
|----|------|
| `true` | 半精度 fp16，**显存更省**（GPU 支持时推荐，16GB 卡建议开） |
| `false` | 全精度 |

在上游 `docker-compose.yaml` 对应服务的 `environment` 里设置，例如 `is_half=true`（具体键名以仓库内 yaml 为准）。

---

## 3. 放置 v2Pro 预训练权重

Lite/完整版都**需要**你本地的 v2Pro 权重（不会随 Lite 自带）：

```text
GPT-SoVITS/GPT_SoVITS/pretrained_models/
├── v2Pro/s2Gv2Pro.pth
├── v2Pro/s2Dv2Pro.pth
├── sv/pretrained_eres2netv2w24s4ep4.ckpt
└── s1bert25hz-5k/   （整个文件夹）
```

Compose 挂载**当前目录**，所以权重放在 clone 根目录下即可，容器内路径与本地一致。

---

## 4. Windows 必做：增大共享内存 `shm_size`

Docker Desktop 默认 `/dev/shm` 很小，容易导致 WebUI/训练异常。

在上游 **`docker-compose.yaml`** 里，给要用的服务（如 `GPT-SoVITS-CU128-Lite`）增加：

```yaml
services:
  GPT-SoVITS-CU128-Lite:
    shm_size: "16g"    # 内存够可 16g，至少 8g
    # ... 其余保持上游默认
```

改完后保存，再执行下面的 `docker compose run`。

---

## 5. 启动（复制即用）

在 **`GPT-SoVITS` 仓库根目录**：

```powershell
cd $env:USERPROFILE\Desktop\GPT-SoVITS

# RTX 5080 / 新驱动 — 推荐
docker compose run --service-ports GPT-SoVITS-CU128-Lite

# 若 CU128 拉取或运行失败，再试 CU126
# docker compose run --service-ports GPT-SoVITS-CU126-Lite

# Lite 缺功能 / 报错 — 换完整版
# docker compose run --service-ports GPT-SoVITS-CU128
```

首次运行会 **拉镜像**，耗时较长。终端出现类似：

```text
Running on local URL:  http://0.0.0.0:9874
```

浏览器打开：**http://127.0.0.1:9874**（不要用 `0.0.0.0`，Windows 浏览器会 502）

### 5.1 每次重启容器：只需一条启动脚本

`docker compose run` 每次会创建**新容器**，容器里 `pip install starlette` **不会保留**，但**不用改代码、不用改 compose**。

进容器后执行（推荐）：

```bash
bash scripts/docker-webui-start.sh
```

等价于手动：

```bash
pip install 'starlette<1.0.0'
python webui.py
```

**一次性修改**（compose、inference patch）见 [WINDOWS-DOCKER-PATCHES.md](./WINDOWS-DOCKER-PATCHES.md)。

### 5.2 WebUI 内检查

1. 模型版本选 **v2Pro**（勿选 v3/v4）。
2. 确认预训练路径指向 `GPT_SoVITS/pretrained_models/`。
3. 零样本：3–10s 参考音频 + 文本试合成。

### 5.3 进入容器调试

另开终端：

```powershell
docker ps
docker exec -it <容器名或ID> bash
```

---

## 6. 本地构建镜像（可选）

Hub 镜像 lag 于代码，或需最新 commit 时：

```bash
# 在 GPT-SoVITS 根目录，Git Bash / WSL 内
bash docker_build.sh --cuda 12.8 --lite
# 或完整版：bash docker_build.sh --cuda 12.8
```

再用 compose 指向本地 build 的 image（见上游 README）。

---

## 7. 常见问题

| 现象 | 处理 |
|------|------|
| GPU 不可用 | Docker Desktop 开 GPU；WSL2 装 nvidia-container-toolkit |
| 启动后很快 OOM / 奇怪崩溃 | 设 `shm_size: 16g`；设 `is_half=true` |
| 找不到 v2Pro 权重 | 检查 `pretrained_models` 目录名与 WebUI 配置 |
| Lite 缺 UVR5 | 自行下载 UVR5 模型到上游文档指定路径，或换 **完整版** 服务 |
| ASR 相关 | Lite 会在需要时**自动下载** ASR，需联网 |
| CU128 失败 | 改 `GPT-SoVITS-CU126-Lite` 或完整版 |
| Windows `undefined volume tools/asr/models` | 曾改为 `./tools/asr/models`；**现建议删除该挂载**（见下行） |
| Windows `CreateFile tools/asr/models: cannot be accessed` | 容器 CMD 在挂载目录里创建了**符号链接/联接点**，Docker 无法再把它当 volume 源。处理：① compose **只保留** `.:/workspace/GPT-SoVITS`，去掉 `asr/models`、`uvr5_weights` 两行挂载；② 删除主机上坏掉的联接点，改回**真实文件夹**（`rmdir tools\asr\models` 后 `mkdir`） |
| Windows `/dev/null` mount 失败 | **删除** compose 里所有 `/dev/null:` 行（仅 Linux 可用）；策略 A 仍靠镜像 CMD 链到 `/workspace/models/` |
| WebUI `unhashable type: dict` | 容器内：`pip install 'starlette<1.0.0'` 后再 `python webui.py`（Starlette 1.0 与 Gradio 不兼容） |
| WebUI `localhost is not accessible` | 同上修复后重试；仍失败则 `export is_share=True` 后用 gradio 公网链接，或 `pip install -U 'gradio>=4.44,<5'` |
| 9872 空响应 / 推理进程秒退 | 英文 UI 模型名未解析为路径；见 [Spike §8](../../docs/architecture/2026-06-03-w1-spike-v2pro-快速验证.md#8-spike-环境-workaround本机实测) |
| 合成报「错误」/ `libtorchcodec` | 推理 WebUI：`safe_load_audio`；api_v2 / **微调 1B-sv**：`safe_torchaudio_load`（见 PATCHES 文档） |
| 微调 GPT 缺 semantic / SoVITS 保存失败 | 见 [Spike §8.2](../../docs/architecture/2026-06-03-w1-spike-v2pro-快速验证.md#82-微调-spikespike_train_v2propy) |
| 微调 GPT resume / `weights_only` | 用 `-FromStep sovits` 续跑；全量重跑 GPT 前脚本会清空 `logs_s1_*/ckpt` |
| 平台 API 合成 | 先起 `api_v2`（9880），Worker `ENGINE_MOCK=false`；见 `apps/api/README.md` |
| 9880 连接被意外关闭 | **`api_v2` 未启动**（仅端口映射）→ `scripts/engine_api_v2.ps1 -Action start` |
| 9880 address already in use | 容器内 **已有** api_v2 → `engine_api_v2.ps1 status`；勿重复 `python api_v2.py` |
| 重复 `docker compose run` | 每次 **新容器**；9874 冲突 → 复用现有容器或 `engine_docker_cleanup.ps1` |
| 端口占用 | 改 compose 端口映射或 `docker stop` 旧引擎容器 |

---

## 8. 故障排查与原因说明

### 8.1 要不要每次重启都改一遍？

| 类型 | 要不要每次重做 | 说明 |
|------|----------------|------|
| `docker-compose.yaml`（去掉 asr 挂载、shm_size） | **否** | 文件在硬盘上，改一次永久生效 |
| `inference_webui.py` patch（模型名、读音频） | **否** | 同上；除非 `git pull` 覆盖 |
| `pip install starlette<1.0` | **是** | 新容器没有上次 pip 状态 → 用 `scripts/docker-webui-start.sh` 一条命令 |
| 浏览器地址用 `127.0.0.1` | **习惯** | 不是改配置，只是别点 `0.0.0.0` 链接 |
| 删联接点 `tools/asr/models` | **通常否** | 仅当 compose 又挂了这个路径且再报错时 |

**结论：不用每次「修错误码/改文件」**；每次新容器只需跑 **启动脚本** + 用正确 URL。

### 8.2 四类典型问题（原因简述）

**① `CreateFile tools/asr/models`**

- 容器 CMD 在挂载目录里创建了**符号链接/联接点**。
- compose 若再单独挂载该路径，Windows Docker 无法挂载 → 启动失败。
- 零样本不需要 ASR/UVR5，去掉挂载即可。

**② 浏览器 502（地址是 `0.0.0.0`）**

- `0.0.0.0` = 服务监听所有网卡，**不是**给用户访问的 URL。
- 请用 **http://127.0.0.1:9874** / **:9872**。

**③ 9872 空页 / `Use v3 base model...` FileNotFound**

- 下拉框是**英文显示名**，未映射成 `.ckpt` 路径，推理进程秒退。
- 需 `inference_webui.py` 一次性 patch（见 PATCHES 文档）。

**④ 合成报「错误」/ `libtorchcodec`**

- `torchaudio.load` 在容器内缺 FFmpeg 组件。
- 需 `safe_load_audio()` 回退 `soundfile`（一次性 patch）。

更完整的 Spike 记录：[w1-spike §8](../../docs/architecture/2026-06-03-w1-spike-v2pro-快速验证.md#8-spike-环境-workaround本机实测)。

### 8.3 Docker 重复容器与端口

**为什么老报错？** 上游用 `docker compose run`，**每执行一次会起一个新容器**（名如 `gpt-sovits-…-run-<hash>`）。旧容器若仍占 **9874/9880**，再 run 会 **端口冲突**；容器内若已后台起了 **api_v2**，再手动 `python api_v2.py` 会 **`address already in use`**。这两种都不是「Docker 坏了」，而是 **重复启动**。

**正确习惯：同一时刻只保留一个引擎容器**

```powershell
docker ps --filter "publish=9874"    # 找当前 ACTIVE 容器
cd C:\Users\panta\Desktop\GPT
.\scripts\engine_docker_cleanup.ps1  # 列出所有引擎容器
.\scripts\engine_docker_cleanup.ps1 -StopStale   # 停掉其它仍 Up 的旧 run 容器
```

| 你想做的事 | 做法 |
|------------|------|
| 进已有容器 | `docker exec -it <ACTIVE名> bash` |
| 再起一个 compose run | 先 `docker stop <旧名>`，或 cleanup；**不要**两个同时占 9874 |
| 平台 Spike / 微调 | 复用已挂载 `/workspace/GPT` 的容器；`engine_run_with_platform_mount.ps1` 检测到已有容器会 **拒绝重复 run** |
| 启动 9880 合成 | `.\scripts\engine_api_v2.ps1 -Action start`（已起则跳过） |
| 微调后试听 | `.\scripts\engine_api_v2.ps1 -Action synthesize` → `finetuned_spike.wav` |
| 强制再起容器 | `.\scripts\engine_run_with_platform_mount.ps1 -Force`（需先 stop 占端口的旧容器） |

**容器内进程 vs 容器本身**

```text
docker ps          → 容器在跑（9874/9880 端口映射）
api_v2 / webui.py  → 容器 *内部* 的 Python 服务（新容器需重新 pip + 启动）
```

`pip install starlette` 的 WARNING 可忽略；**新容器**才需要重做，**同一容器**内重复 pip 无害。

---

## 9. 与本产品仓库的关系

| 路径 | 说明 |
|------|------|
| `Desktop/GPT-SoVITS` | 上游引擎（本指南操作目录） |
| `Desktop/GPT` | 产品文档 + 平台代码 |
| `GPT/infra/docker/` | 仅 **PostgreSQL + Redis**（平台用，与引擎 compose 分开） |

架构说明：[ADR-004](../../docs/architecture/sections/05-技术决策与质量.md#adr-004-引擎-docker-hub-官方镜像)

---

## 11. 微调 Spike（平台 Train Worker）

W1 通过 `workers/train/engine_adapter.py` 调用 `infra/engine/scripts/spike_train_v2pro.py`，流程与 WebUI **1A→1B→1C→GPT→SoVITS** 一致；默认超参见 `train-v2pro-spike.json`（4+4 epoch）。

**2026-06-03 容器实测**：`manual-spike-001` 产出 `platform_manualspike001-e4.ckpt` + `platform_manualspike001_e4_s100.pth`；详见 [Spike §4.5](../../docs/architecture/2026-06-03-w1-spike-v2pro-快速验证.md#45-微调实测结果manual-spike-001)。

### 11.1 容器内手动 Spike（方式 B — 推荐）

**一次性**：在上游 `docker-compose.yaml` 已配置 `shm_size: 16g` 的前提下，用 **叠加 compose** 挂载本产品仓库：

```powershell
# 仓库根目录 GPT/
.\scripts\engine_run_with_platform_mount.ps1
```

等价于在上游目录执行：

```powershell
cd $env:USERPROFILE\Desktop\GPT-SOVITS\GPT-SoVITS
$env:PLATFORM_MOUNT = "C:/Users/panta/Desktop/GPT"
docker compose -f docker-compose.yaml `
  -f C:/Users/panta/Desktop/GPT/infra/engine/docker-compose.platform-mount.yaml `
  run --service-ports --remove-orphans GPT-SoVITS-CU128-Lite
```

容器内将出现：

| 路径 | 内容 |
|------|------|
| `/workspace/GPT-SoVITS` | 上游引擎 |
| `/workspace/GPT` | 本产品 monorepo |

**另开 PowerShell** 跑 Spike（自动准备 `train.list` + 调用脚本）：

```powershell
cd C:\Users\panta\Desktop\GPT
# 全量（1A → SoVITS）
.\scripts\spike_train_in_container.ps1

# GPT 已完成，仅补 SoVITS（约 1 分钟）
.\scripts\spike_train_in_container.ps1 -FromStep sovits

# 强制清空 logs/<exp> 后全量重跑
# $env:SPIKE_CLEAN=1; .\scripts\spike_train_in_container.ps1
```

| 参数 / 环境变量 | 说明 |
|-----------------|------|
| `-FromStep sovits` | 跳过 1A–GPT，校验预处理后只跑 SoVITS |
| `-FromStep gpt` | 跳过 1A–1C，从 GPT 开训 |
| `SPIKE_FROM_STEP` | 容器内等价于 `-FromStep` |
| `SPIKE_CLEAN=1` | 删除 `logs/<exp_name>` 后再预处理 |

成功输出：`/tmp/spike_train_<job_id>.json`（含 `gpt_checkpoint`、`sovits_checkpoint`、`elapsed_sec`）。

或容器内手动：

```bash
mkdir -p /workspace/GPT-SoVITS/samples
cp /workspace/GPT/infra/engine/samples/ref_zh_zero_shot.wav /workspace/GPT-SoVITS/samples/
cat > /workspace/GPT-SoVITS/samples/train.list << 'EOF'
/workspace/GPT-SoVITS/samples/ref_zh_zero_shot.wav|spk0|zh|大家好，我是测试用户，今天我们来测试一下语音合成功能。
EOF
bash /workspace/GPT/infra/engine/docker-spike-train.sh
```

> **注意**：当前已在跑、但未挂载 `/workspace/GPT` 的旧容器**不能**直接 Spike，需先 `Ctrl+C` 停掉后用 `engine_run_with_platform_mount.ps1` 重启。  
> **GPT 已训完时勿再全量重跑**（会触发 Lightning resume / `weights_only` 问题）；用 `-FromStep sovits`。

配置文件：`infra/engine/docker-compose.platform-mount.yaml` · 路径示例：`.env.platform-mount.example` · patch 清单：[WINDOWS-DOCKER-PATCHES.md](./WINDOWS-DOCKER-PATCHES.md)

记录 **VRAM 峰值**：Spike 实测 **6596 MiB**（16GB 卡，40%），见 [Spike §4.2 / §4.6](../../docs/architecture/2026-06-03-w1-spike-v2pro-快速验证.md#46-vram-采样说明)。

### 11.2 平台 Worker（Docker exec 模式）

`.env` 示例：

```env
TRAIN_MOCK=false
ENGINE_TRAIN_ROOT=C:/Users/panta/Desktop/GPT-SOVITS/GPT-SoVITS
ENGINE_TRAIN_DOCKER=<容器名>
ENGINE_TRAIN_ROOT_IN_DOCKER=/workspace/GPT-SoVITS
ENGINE_TRAIN_PLATFORM_MOUNT=/workspace/GPT
```

Worker 会 staging 到 `{ENGINE_TRAIN_ROOT}/logs/platform_staging/{job_id}/`，在容器内跑 spike 脚本，成功后写入 `VoiceVersion.metadata.engine_*_path`。

### 11.3 微调后推理

**① 启动 api_v2（必做）**

```powershell
cd C:\Users\panta\Desktop\GPT
.\scripts\engine_api_v2.ps1 -Action status
.\scripts\engine_api_v2.ps1 -Action start      # 约 1-2 min
.\scripts\engine_api_v2.ps1 -Action synthesize # → finetuned_spike.wav
```

**② 手动 HTTP**（需 `-TimeoutSec 300`）

`api_v2` 启动后须 **同时** 切换 GPT + SoVITS（yaml 默认 SoVITS 可能是底模）：

```text
GET http://127.0.0.1:9880/set_gpt_weights?weights_path=GPT_weights_v2Pro/platform_manualspike001-e4.ckpt
GET http://127.0.0.1:9880/set_sovits_weights?weights_path=SoVITS_weights_v2Pro/platform_manualspike001_e4_s100.pth
GET http://127.0.0.1:9880/tts?...   # 见 Spike §4.7
```

2026-06-03 实测：`finetuned_spike.wav` 合成成功（9880 链路 ✅）。

Infer Worker 已读取 `VoiceVersion.metadata` 自动 `set_gpt_weights` / `set_sovits_weights`（W2）。

---

## 10. 最小命令清单（Windows + 5080）

```powershell
cd $env:USERPROFILE\Desktop\GPT-SOVITS\GPT-SoVITS
git checkout 20250606v2pro
docker compose run --service-ports --remove-orphans GPT-SoVITS-CU128-Lite
# 容器内（每次新容器执行一次）:
#   bash scripts/docker-webui-start.sh
# 浏览器: http://127.0.0.1:9874
```
