"""Exporta o notebook executado para HTML pronto para impressão em PDF."""
import html
from pathlib import Path

import mistune
import nbformat


root = Path(__file__).resolve().parents[1]
notebook = nbformat.read(root / "projeto_data_analytics.ipynb", as_version=4)
assert all(cell.execution_count is not None for cell in notebook.cells
           if cell.cell_type == "code")
assert not any(output.output_type == "error"
               for cell in notebook.cells if cell.cell_type == "code"
               for output in cell.outputs)

markdown = mistune.create_markdown(plugins=["table"])
parts = []


def render_output(output):
    if output.output_type == "stream":
        return f'<pre class="stream">{html.escape(output.text)}</pre>'
    data = output.get("data", {})
    if "image/png" in data:
        return '<img class="plot" src="data:image/png;base64,' + data["image/png"] + '">'
    if "text/html" in data:
        return '<div class="table-output">' + "".join(data["text/html"]) + "</div>"
    if "text/plain" in data:
        return f'<pre class="result">{html.escape("".join(data["text/plain"]))}</pre>'
    return ""


for cell in notebook.cells:
    if cell.cell_type == "markdown":
        parts.append('<section class="markdown">' + markdown(cell.source) + "</section>")
        continue
    source = html.escape(cell.source)
    parts.append('<section class="code-cell"><pre><code>' + source + "</code></pre>")
    parts.extend(render_output(output) for output in cell.outputs)
    parts.append("</section>")

document = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Data Analytics — RA1, RA2 e RA3</title>
<style>
@page { size: A4; margin: 16mm 14mm; }
body { color: #18212b; background: white; font-family: Arial, sans-serif; }
body { max-width: 100%; }
.markdown { padding: 4px 0; line-height: 1.5; font-size: 10pt; }
.markdown h1 { font-size: 19pt; margin-top: 22px; color: #193c50; }
.markdown h2 { font-size: 14pt; margin-top: 18px; color: #193c50; }
.code-cell { margin: 6px 0 12px; }
.code-cell pre, .stream, .result { white-space: pre-wrap; overflow-wrap: anywhere; }
.code-cell > pre { border: 1px solid #d4dce2; background: #f5f7f9; padding: 7px; }
pre, code { font-family: Consolas, monospace; font-size: 8pt; line-height: 1.35; }
.stream, .result { margin: 5px 0; }
table { width: auto; max-width: 100%; border-collapse: collapse; font-size: 8.5pt; }
th, td { border: 1px solid #d5dce1; padding: 5px; text-align: left; }
th { background: #e8eff3; }
tr { break-inside: avoid; }
h1, h2, h3 { break-after: avoid; }
img.plot { display: block; width: 100%; height: auto; margin: 8px auto 12px; }
section { break-inside: auto; }
</style></head><body>""" + "\n".join(parts) + "</body></html>"

output_path = root / ".work/projeto_data_analytics.html"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(document, encoding="utf-8")
print(output_path)
