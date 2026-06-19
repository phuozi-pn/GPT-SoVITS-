# REQ-006 相似度测评与 AB 试听

> 状态：**MVP+1 第二切片（mock 评测 + 平台 AB 页）**

## 能力

| 能力 | API / 页面 | 说明 |
|------|------------|------|
| 自动评测 | 训练成功后 Train Worker 触发 | `QUALITY_MOCK=true` 时用确定性 mock 分数 |
| 手动评测 | `POST /voice-versions/{id}/quality/evaluate` | Owner 或重跑 |
| 相似度报告 | `GET /voice-versions/{id}/quality` | `similarity_score` / `quality_pass` |
| AB 盲听 | `GET .../ab-trial` + `POST .../ab-vote` | 随机排列 ref / synth |
| Web | `/quality/:voiceVersionId` | 工作台训练完成后可跳转 |

## Mock 公式（开发）

- `similarity_score = 0.88 + (uuid[:8] as int mod 12) / 100` → 约 0.88–0.99
- `quality_pass = score >= QUALITY_SIMILARITY_THRESHOLD`（默认 0.90）
- 合成样例：对 ref 音频做 `pitch_shift(1.08)` 生成 AB 对比轨

## 授权凭证 PDF（REQ-018）

- `GET /api/v1/authorizations/{id}/certificate.pdf`
- 依赖 `fpdf2`；Web 音色馆「导出 PDF」

## 本地验证

```powershell
# 训练 mock 完成后
# 浏览器打开 /quality/{voice_version_id}

pytest tests/test_quality_and_pdf.py -q
```

## 真实 embedding（第三切片）

设置 `QUALITY_MOCK=false`（需 `pip install voice-platform[quality]` 即 numpy）：

| 步骤 | 说明 |
|------|------|
| 合成 | 对测评句调用 GPT-SoVITS `EngineAdapter`（或 `ENGINE_MOCK=true` 时用 tone mock） |
| 特征 | 16kHz mono → log-mel 均值向量（40 维）→ L2 归一化 |
| 分数 | ref 与 synth 向量 cosine，多句取平均 |
| 测评集 | `voice_platform/quality/eval_sentences.py` 固定 20 句；`QUALITY_EVAL_SENTENCE_COUNT` 控制参与句数（默认 1） |
| method | `mel_speaker_embedding_v1` |

## 后续（更强 embedding）

- 替换为预训练 speaker encoder（如 ECAPA / resemblyzer）
- 20 人 AB 校准阈值
