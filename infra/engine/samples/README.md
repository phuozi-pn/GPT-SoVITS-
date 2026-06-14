# 零样本试听参考音频（Spike 测试用）

| 文件 | 时长 | 参考文本 |
|------|------|----------|
| `ref_zh_zero_shot.wav` | ~6.8 秒 | 大家好，我是测试用户，今天我们来测试一下语音合成功能。 |

## 用法

1. 打开 http://127.0.0.1:9872
2. 上传本目录下的 `ref_zh_zero_shot.wav`
3. **参考文本** 填上表中的句子（需与音频一致）
4. **目标文本** 可填任意中文，例如：`你好，这是一次零样本语音合成测试。`

> 本文件由 Windows 系统 TTS 生成，仅用于本地技术验证，不代表最终产品音质。

## 微调 Spike（W1）

1. 将本目录 `ref_zh_zero_shot.wav` 复制到上游引擎 `GPT-SoVITS/samples/`（容器内 `/workspace/GPT-SoVITS/samples/`）。
2. 可选：创建 `train.list`（与 WebUI 格式一致）：

   ```text
   /workspace/GPT-SoVITS/samples/ref_zh_zero_shot.wav|spk0|zh|大家好，我是测试用户，今天我们来测试一下语音合成功能。
   ```

3. 在容器内执行（**方式 B**：先 `scripts/engine_run_with_platform_mount.ps1` 挂载 `/workspace/GPT`）：

   ```powershell
   .\scripts\spike_train_in_container.ps1
   ```

   或容器内：`bash /workspace/GPT/infra/engine/docker-spike-train.sh`

4. 平台 Worker：`TRAIN_MOCK=false`，配置 `ENGINE_TRAIN_ROOT` / `ENGINE_TRAIN_DOCKER`，见 [infra/engine/README.md](../README.md) §11。
