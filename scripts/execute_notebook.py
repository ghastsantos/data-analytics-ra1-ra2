"""Executa todas as células num kernel novo e preserva evidências reais."""
import argparse
from pathlib import Path
import nbformat
from nbclient import NotebookClient

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--kernel", default="python3")
args = parser.parse_args()
path = root / "projeto_data_analytics.ipynb"
notebook = nbformat.read(path, as_version=4)
nbformat.validate(notebook)
client = NotebookClient(notebook, timeout=900, kernel_name=args.kernel,
                        resources={"metadata": {"path": str(root)}},
                        allow_errors=False)
try:
    client.execute()
finally:
    nbformat.write(notebook, path)
errors = [output for cell in notebook.cells if cell.cell_type == "code"
          for output in cell.outputs if output.output_type == "error"]
code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
assert not errors
assert all(cell.execution_count is not None for cell in code_cells)
print(f"PASS: {len(code_cells)} células de código executadas, sem erros.")
