# 剧本批量 CSV 样例

| 文件 | 用途 |
|------|------|
| `guzhenren_batch_20.csv` | 20 行龙宫台词，端到端试单（全成功） |
| `guzhenren_batch_mixed.csv` | 含 1 行敏感词，验证行级失败 + 其余成功 |

表头：`role,text` 或 `角色,台词`。角色名须与项目绑定一致。

运行端到端：

```powershell
cd C:\Users\panta\Desktop\GPT
.\.venv\Scripts\python.exe scripts\smoke_e2e_guzhenren.py
```

可选环境变量见 `smoke_e2e_guzhenren.py` 文件头。
