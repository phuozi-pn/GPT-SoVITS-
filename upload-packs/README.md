# 云端上传包（本地专用，不入 Git）

大体积 zip 已被 `.gitignore` 排除，避免推送到 GitHub。

| 文件 | 用途 |
|------|------|
| `engine-min.zip` | 精简引擎目录，上传到 AutoDL 等 GPU 机 |
| `pretrained_models.zip` | 预训练模型（约 4GB），解压到引擎 `GPT_SoVITS/pretrained_models/` |

生成方式见 [云端 GPU 训练指南](../docs/architecture/2026-06-10-云端GPU训练指南.md)。
