# REQ-019 数字水印 MOS Spike 与算法选型

**日期**: 2026-06-22  
**状态**: Spike 完成，待听感 AB 与真实 TTS 样本复测

## 背景

合规导出需在音频中嵌入可追溯水印（`voice_platform/watermark/embedder.py` LSB）。上线前需验证**可听性影响**与**鲁棒性**是否满足 GB 45438-2025 配套实践。

## Spike 方法

运行：

```powershell
python scripts/watermark_mos_spike.py
```

指标：

| 指标 | 当前 LSB 典型值 | 说明 |
|------|-----------------|------|
| SNR | >40 dB | 全段信噪比，>30 dB 通常不可感知 |
| Max \|Δsample\| | 1 | 仅修改 LSB，幅度变化极小 |
| 往返提取 | ✓ | magic + JSON payload 可还原 |

## 算法候选

| 方案 | 可听性 | 鲁棒性（重编码/裁剪） | 实现成本 | 建议 |
|------|--------|----------------------|----------|------|
| **LSB（当前）** | 优 | 差 | 低 | MVP 合规元数据 + 节奏标识 |
| Spread-spectrum | 良 | 中 | 中 | Phase 2 默认 |
| Segment perceptual hash | 良 | 中 | 中 | 与指纹库联动 |
| Cepstrum / echo hiding | 中 | 高 | 高 | 仅高价值授权场景 |

## 决策（MVP+1）

1. **保留 LSB** 作为导出默认，配合节奏标识与 `manifest.json` 三重标识。
2. **不在 MVP+1 切换算法**；听感 AB 由运营抽检 10 条真实合成样本（MOS 目标 ≥4.0，ΔMOS ≤0.2）。
3. Phase 2 引入 spread-spectrum，并与 `audio_fingerprints` 表做交叉验证。

## 相关代码

- `voice_platform/watermark/embedder.py` — 嵌入/提取
- `domains/compliance/export.py` — 导出管线
- `infra/docker/migrations/024_audio_fingerprints.sql` — 指纹持久化

## 验收

- [x] Spike 脚本可运行并输出 SNR
- [ ] 10 条真实 TTS 样本听感 AB（运营）
- [ ] 重编码 MP3 后提取成功率（鲁棒性基线）
