# 云端 GPU 训练（AutoDL / 租服务器）

**推荐路径**：在 Linux GPU 服务器上完成「数据集准备 → 微调 → 下载权重」；本机 Windows 只做 **9880 合成试听**。

| 步骤 | 在哪里做 |
|------|----------|
| 静音切分 + FunASR 标注 | 云端 |
| `spike_train_v2pro.py` 微调 | 云端 |
| 下载 `.ckpt` / `.pth` | scp → 本机 |
| api_v2 合成试听 | 本机引擎容器 |

完整说明：[docs/architecture/2026-06-10-云端GPU训练指南.md](../../../docs/architecture/2026-06-10-云端GPU训练指南.md)

## 一键脚本（在云端 bash 执行）

```bash
export ENGINE_ROOT=$HOME/GPT-SoVITS      # 上游 clone，tag 20250606v2pro
export PLATFORM_ROOT=$HOME/GPT           # 本仓库（或只 scp infra/engine 目录）

bash infra/engine/cloud/train.sh \
  /path/to/train_10min.wav \
  /root/train_out \
  my-job-001
```

输出：`train_out/dataset/`、`train_out/result.json`，权重在 `ENGINE_ROOT/GPT_weights_v2Pro/` 与 `SoVITS_weights_v2Pro/`。
