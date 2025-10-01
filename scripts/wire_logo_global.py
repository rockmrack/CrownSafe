import os, base64, re, sys
from pathlib import Path

# Find the file that defines ReportBuilderAgentLogic
root = Path(".")
candidates = list(root.rglob("**/*report_builder_agent*/*.py")) + list(root.rglob("**/report_builder_agent*.py"))
target = None
for p in candidates:
    t = p.read_text(encoding="utf-8", errors="ignore")
    if "class ReportBuilderAgentLogic" in t and "Environment(" in t:
        target = p; break
if not target:
    print("Could not find ReportBuilderAgentLogic file"); sys.exit(1)

s = target.read_text(encoding="utf-8")

# Ensure imports
if "import base64" not in s:
    s = s.replace("import os", "import os, base64") if "import os" in s else "import os, base64\n" + s

# Helper method
helper = r"""
    def _resolve_logo_src(self):
        path = os.getenv("BRAND_LOGO_PATH", "").strip()
        if not path:
            return None
        if path.startswith(("http://", "https://", "data:")):
            return path
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
            mime = {"png":"image/png","jpg":"image/jpeg","jpeg":"image/jpeg","svg":"image/svg+xml"}.get(ext,"application/octet-stream")
            return f"data:{mime};base64,{b64}"
        except Exception as e:
            try:
                self.logger.warning("Logo not found at %s: %s", path, e)
            except Exception:
                pass
            return None
"""

# Insert helper into the class if missing
import re
if "_resolve_logo_src(" not in s:
    s = re.sub(r"(class\s+ReportBuilderAgentLogic\s*\([^)]*\)\s*:\s*\n)", r"\1" + helper + "\n", s, count=1)

# Inject Jinja global after Environment(...) is created
if "self.jinja_env.globals.setdefault(\"logo_src\"" not in s:
    s = re.sub(r"(self\.jinja_env\s*=\s*Environment\([^\)]*\)\s*\n)",
               r"\1        self.jinja_env.globals.setdefault(\"logo_src\", self._resolve_logo_src())\n",
               s, count=1)

target.write_text(s, encoding="utf-8")
print("Patched:", target)
