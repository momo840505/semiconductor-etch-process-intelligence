from __future__ import annotations

import json
import sys
from pathlib import Path


EXPECTED_NOTEBOOKS = [
    "00_data_understanding.ipynb",
    "01_data_quality.ipynb",
    "02_wafer_quality_analysis.ipynb",
    "03_process_eda.ipynb",
    "04_process_quality_relationship.ipynb",
    "05_spc_monitoring.ipynb",
    "06_multivariate_analysis.ipynb",
    "07_feature_engineering.ipynb",
    "08_virtual_metrology.ipynb",
    "09_model_explainability.ipynb",
    "10_anomaly_detection.ipynb",
    "11_final_findings.ipynb",
]


def find_project_root(start: Path | None = None) -> Path:
    start = Path.cwd().resolve() if start is None else start.resolve()

    for candidate in [start, *start.parents]:
        if (candidate / "notebooks").exists():
            return candidate

    raise FileNotFoundError(
        "找不到專案根目錄：目前路徑往上都沒有 notebooks/ 資料夾。"
    )


def load_notebook(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_output_errors(cell: dict) -> list[str]:
    errors = []

    for output in cell.get("outputs", []):
        if output.get("output_type") == "error":
            error_name = output.get("ename", "UnknownError")
            error_value = output.get("evalue", "")
            errors.append(f"{error_name}: {error_value}")

    return errors


def validate_notebook(path: Path) -> dict:
    notebook = load_notebook(path)
    cells = notebook.get("cells", [])

    code_cells = [
        (index, cell)
        for index, cell in enumerate(cells)
        if cell.get("cell_type") == "code"
    ]

    markdown_cells = [
        cell
        for cell in cells
        if cell.get("cell_type") == "markdown"
    ]

    problems = []

    execution_counts = []

    for index, cell in code_cells:
        execution_count = cell.get("execution_count")

        if execution_count is None:
            problems.append(
                f"Cell {index}: code cell 尚未執行（execution_count=None）"
            )
        else:
            execution_counts.append(execution_count)

        output_errors = get_output_errors(cell)

        for error in output_errors:
            problems.append(
                f"Cell {index}: stored output error -> {error}"
            )

        if index == 0 or cells[index - 1].get("cell_type") != "markdown":
            problems.append(
                f"Cell {index}: Code Cell 前面沒有 Markdown 說明"
            )

        if (
            index == len(cells) - 1
            or cells[index + 1].get("cell_type") != "markdown"
        ):
            problems.append(
                f"Cell {index}: Code Cell 後面沒有 Markdown 解讀"
            )

    if execution_counts:
        if execution_counts != sorted(execution_counts):
            problems.append(
                "Code Cell execution_count 不是由前往後遞增"
            )

        if len(execution_counts) != len(set(execution_counts)):
            problems.append(
                "Code Cell execution_count 有重複"
            )

    return {
        "name": path.name,
        "total_cells": len(cells),
        "markdown_cells": len(markdown_cells),
        "code_cells": len(code_cells),
        "problems": problems,
    }


def main() -> int:
    project_root = find_project_root()
    notebooks_dir = project_root / "notebooks"

    print(f"Project root: {project_root}")
    print(f"Notebook directory: {notebooks_dir}")
    print()

    actual_notebooks = sorted(
        path.name
        for path in notebooks_dir.glob("*.ipynb")
        if ".ipynb_checkpoints" not in str(path)
    )

    missing_notebooks = [
        name
        for name in EXPECTED_NOTEBOOKS
        if name not in actual_notebooks
    ]

    unexpected_notebooks = [
        name
        for name in actual_notebooks
        if name not in EXPECTED_NOTEBOOKS
    ]

    global_problems = []

    if missing_notebooks:
        global_problems.append(
            "缺少 notebooks: "
            + ", ".join(missing_notebooks)
        )

    if unexpected_notebooks:
        global_problems.append(
            "發現額外 notebooks: "
            + ", ".join(unexpected_notebooks)
        )

    results = []

    for notebook_name in EXPECTED_NOTEBOOKS:
        path = notebooks_dir / notebook_name

        if not path.exists():
            continue

        results.append(
            validate_notebook(path)
        )

    print("Notebook Validation")
    print("=" * 88)

    total_notebook_problems = 0

    for result in results:
        status = "PASS" if not result["problems"] else "FAIL"

        print(
            f"{result['name']:<42} "
            f"{status:<5} | "
            f"cells={result['total_cells']:<3} "
            f"markdown={result['markdown_cells']:<3} "
            f"code={result['code_cells']:<3}"
        )

        for problem in result["problems"]:
            total_notebook_problems += 1
            print(f"    - {problem}")

    if global_problems:
        print()
        print("Repository-level problems")
        print("-" * 88)

        for problem in global_problems:
            print(f"- {problem}")

    print()
    print("=" * 88)

    total_problems = (
        total_notebook_problems
        + len(global_problems)
    )

    if total_problems == 0:
        print(
            "PASS: 00～11 全部 Notebook 通過結構與執行狀態檢查。"
        )
        return 0

    print(
        f"FAIL: 共發現 {total_problems} 個問題。"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
