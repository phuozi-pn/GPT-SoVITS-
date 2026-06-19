# 剧本批量 CSV 样例

| 文件 | 用途 |
|------|------|
| `guzhenren_batch_20.csv` | 20 行龙宫台词，端到端试单（全成功） |
| `guzhenren_batch_mixed.csv` | 含 1 行敏感词，验证行级失败 + 其余成功 |

表头：`role,text` 或 `角色,台词`。角色名须与项目绑定一致。

运行端到端：

```powershell
cd C:\Users\panta\Desktop\GPT
# 真引擎（.env ENGINE_MOCK=false）须先：
#   .\scripts\engine_sync_env.ps1
#   .\scripts\engine_api_v2.ps1 -Action start
# 或占位：.env ENGINE_MOCK=true 后 platform_start.ps1
python scripts/engine_preflight.py
.\.venv\Scripts\python.exe scripts\smoke_e2e_guzhenren.py
python scripts/smoke_e2e_batch_mixed.py   # 敏感词行级失败
```

可选环境变量见 `smoke_e2e_guzhenren.py` 文件头。
