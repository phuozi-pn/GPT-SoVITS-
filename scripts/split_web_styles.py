"""Split apps/web/src/styles/tailwind.css — extract showcase block to showcase.css."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "apps/web/src/styles/tailwind.css"
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
start = next(i for i, line in enumerate(lines) if "展示站" in line)
end = next(i for i, line in enumerate(lines) if "/* Feed & community */" in line)
showcase = "".join(lines[start:end])
(ROOT / "apps/web/src/styles/showcase.css").write_text(
    "@layer components {\n" + showcase + "}\n",
    encoding="utf-8",
)
new = lines[:start] + ['@import "./showcase.css";\n', "\n"] + lines[end:]
p.write_text("".join(new), encoding="utf-8")
print(f"showcase extracted: lines {start}-{end}")
