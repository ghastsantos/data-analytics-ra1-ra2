"""Exporta HTML integral do notebook executado, adequado à impressão em PDF."""
from pathlib import Path
import nbformat
from nbconvert import HTMLExporter

root = Path(__file__).resolve().parents[1]
nb = nbformat.read(root / "projeto_data_analytics.ipynb", as_version=4)
assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
assert not any(o.output_type == "error" for c in nb.cells if c.cell_type == "code" for o in c.outputs)
exporter = HTMLExporter(template_name="classic")
exporter.exclude_input_prompt = True
exporter.exclude_output_prompt = True
body, _ = exporter.from_notebook_node(nb)
css = '''<style>
@page { size: A4; margin: 16mm 14mm; }
body { color: #18212b; background: white; font-family: Arial, sans-serif; }
div#notebook-container { width: 100%; padding: 0; box-shadow: none; }
.container { width: 100% !important; }
.prompt { display: none !important; }
.inner_cell { margin-left: 0 !important; width: 100%; }
.text_cell_render { padding: 5px 0; line-height: 1.5; font-size: 10pt; }
.text_cell_render h1 { font-size: 19pt; margin-top: 22px; color: #193c50; }
.text_cell_render h2 { font-size: 14pt; margin-top: 18px; color: #193c50; }
.input_area { border: 1px solid #d4dce2; border-radius: 0; background: #f5f7f9; }
pre, code { font-family: Consolas, monospace; font-size: 8pt !important; line-height: 1.35; }
pre { white-space: pre-wrap !important; overflow-wrap: anywhere; }
table { width: auto; max-width: 100%; border-collapse: collapse; font-size: 8.5pt !important; }
th, td { border: 1px solid #d5dce1 !important; padding: 5px !important; text-align: left !important; }
th { background: #e8eff3; }
tr { break-inside: avoid; }
h1, h2, h3 { break-after: avoid; }
.output_wrapper, .output, .output_area, .cell, .input { overflow: visible !important; }
.output_subarea { max-width: 100% !important; }
@media print {
  body { padding: 0 !important; }
  #notebook { padding: 0; }
  div.cell { display: block; padding: 3px 0; break-inside: auto; page-break-inside: auto; }
  div.output_wrapper, div.output { break-inside: auto; page-break-inside: auto; }
  div.output_area { display: block; }
  .input_area, .output_subarea { overflow: visible !important; }
  a[href]::after { content: none !important; }
}
</style>'''
body = body.replace("</head>", css + "</head>")
out = root / ".work/projeto_data_analytics.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(body, encoding="utf-8")
print(out)
