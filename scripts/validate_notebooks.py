from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


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

STALE_ARTIFACTS = [
    "data/processed/process_wafer_summary_spc.csv",
    "data/processed/07_constant_engineered_features.csv",
    "reports/figures/10_residual_anomaly_by_lot.png",
    "reports/figures/10_residual_anomaly_in_06_pca.png",
    "reports/figures/10_residual_anomaly_vs_oof_error.png",
]

ROOT_REQUIRED_FRAGMENTS = [
    "def find_project_root(start=None):",
    '(candidate / "notebooks").exists()',
    '(candidate / "data").exists()',
    "CURRENT_DIR = Path.cwd().resolve()",
    "PROJECT_ROOT = find_project_root(CURRENT_DIR)",
]

ROOT_FORBIDDEN_FRAGMENTS = [
    "CURRENT_DIR.name",
    '(candidate / "data" / "processed").exists()',
]

EXPECTED_VM_METRICS = {
    "Training-Mean": {
        "rmse": 0.40437488375133024,
        "mae": 0.34767474017923183,
        "r2": -0.02394549656629308,
    },
    "Sequence-Only": {
        "rmse": 0.22092816113979696,
        "mae": 0.18333043870754773,
        "r2": 0.6943596773192635,
    },
    "Process-Only": {
        "rmse": 0.1296326058643884,
        "mae": 0.09723159843510487,
        "r2": 0.8947706236611082,
    },
    "Process + Sequence": {
        "rmse": 0.09540186778803818,
        "mae": 0.07499736755137963,
        "r2": 0.9430069040892808,
    },
}


def find_project_root(start: Path | None = None) -> Path:
    """Find the project root by walking upward from the current directory."""
    start = Path.cwd().resolve() if start is None else Path(start).resolve()

    for candidate in [start, *start.parents]:
        if (
            (candidate / "notebooks").exists()
            and (candidate / "data").exists()
        ):
            return candidate

    raise FileNotFoundError(
        "Project root not found. Expected a parent directory "
        "containing both notebooks/ and data/."
    )


def load_notebook(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def notebook_text(notebook: dict, cell_type: str | None = None) -> str:
    parts = []

    for cell in notebook.get("cells", []):
        if cell_type is not None and cell.get("cell_type") != cell_type:
            continue

        parts.append("".join(cell.get("source", [])))

    return "\n".join(parts)


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
                f"Cell {index}: code cell has not been executed "
                "(execution_count=None)"
            )
        else:
            execution_counts.append(execution_count)

        for error in get_output_errors(cell):
            problems.append(
                f"Cell {index}: stored output error -> {error}"
            )

        if index == 0 or cells[index - 1].get("cell_type") != "markdown":
            problems.append(
                f"Cell {index}: missing Markdown explanation before code"
            )

        if (
            index == len(cells) - 1
            or cells[index + 1].get("cell_type") != "markdown"
        ):
            problems.append(
                f"Cell {index}: missing Markdown interpretation after code"
            )

    if execution_counts:
        if execution_counts != sorted(execution_counts):
            problems.append(
                "Code-cell execution_count values are not increasing"
            )

        if len(execution_counts) != len(set(execution_counts)):
            problems.append(
                "Code-cell execution_count values contain duplicates"
            )

    code_text = notebook_text(notebook, cell_type="code")

    if code_text.count("def find_project_root(start=None):") != 1:
        problems.append(
            "Expected exactly one find_project_root() definition"
        )

    for fragment in ROOT_REQUIRED_FRAGMENTS:
        if fragment not in code_text:
            problems.append(
                f"Canonical project-root fragment missing: {fragment}"
            )

    for fragment in ROOT_FORBIDDEN_FRAGMENTS:
        if fragment in code_text:
            problems.append(
                f"Old project-root logic still present: {fragment}"
            )

    return {
        "name": path.name,
        "total_cells": len(cells),
        "markdown_cells": len(markdown_cells),
        "code_cells": len(code_cells),
        "problems": problems,
    }


def validate_raw_readme(project_root: Path) -> list[str]:
    problems = []
    path = project_root / "data" / "raw" / "README.md"

    if not path.exists():
        return ["data/raw/README.md does not exist"]

    text = path.read_text(encoding="utf-8")

    escaped_patterns = {
        r"\#": r"escaped heading marker: \#",
        r"\*": r"escaped emphasis marker: \*",
        r"\_": r"escaped underscore: \_",
    }

    for pattern, description in escaped_patterns.items():
        if pattern in text:
            problems.append(
                f"data/raw/README.md still contains {description}"
            )

    required_text = [
        "# Raw Data",
        "## Dataset",
        "10.5281/zenodo.17122442",
        "Process_data.nc",
        "Dictionary_process.nc",
        "Lot_status.xlsx",
        "Si_Oxide_etch_89_points.csv",
        "Readme.pdf",
        "Wafer_layout.pdf",
        "notebooks/00_data_understanding.ipynb",
        "notebooks/01_data_quality.ipynb",
    ]

    for item in required_text:
        if item not in text:
            problems.append(
                f"data/raw/README.md missing expected text: {item}"
            )

    return problems


def validate_stale_artifacts(project_root: Path) -> list[str]:
    problems = []

    for relative_path in STALE_ARTIFACTS:
        path = project_root / relative_path

        if path.exists():
            problems.append(
                f"Stale artifact still exists: {relative_path}"
            )

    return problems


def require_columns(
    df: pd.DataFrame,
    required: set[str],
    name: str,
) -> list[str]:
    missing = sorted(required - set(df.columns))

    if not missing:
        return []

    return [
        f"{name} missing columns: {', '.join(missing)}"
    ]


def rmse(actual: pd.Series, predicted: pd.Series) -> float:
    diff = (
        predicted.to_numpy(dtype=float)
        - actual.to_numpy(dtype=float)
    )
    return float(np.sqrt(np.mean(diff ** 2)))


def mae(actual: pd.Series, predicted: pd.Series) -> float:
    diff = np.abs(
        predicted.to_numpy(dtype=float)
        - actual.to_numpy(dtype=float)
    )
    return float(np.mean(diff))


def r2(actual: pd.Series, predicted: pd.Series) -> float:
    y_true = actual.to_numpy(dtype=float)
    y_pred = predicted.to_numpy(dtype=float)

    denominator = float(
        np.sum(
            (y_true - y_true.mean()) ** 2
        )
    )

    if denominator == 0:
        return math.nan

    numerator = float(
        np.sum(
            (y_true - y_pred) ** 2
        )
    )

    return 1.0 - numerator / denominator


def validate_vm_ablation(project_root: Path) -> list[str]:
    problems = []
    processed = project_root / "data" / "processed"

    paths = {
        "outer":
            processed
            / "08_nested_outer_fold_results.csv",
        "sequence_outer":
            processed
            / "08_process_plus_sequence_outer_fold_results.csv",
        "metrics":
            processed
            / "08_ablation_metrics.csv",
        "nested_oof":
            processed
            / "08_nested_oof_predictions.csv",
        "ablation_oof":
            processed
            / "08_ablation_oof_predictions.csv",
        "config":
            processed
            / "08_final_model_config.json",
    }

    missing = [
        str(path.relative_to(project_root))
        for path in paths.values()
        if not path.exists()
    ]

    if missing:
        return [
            "Missing required VM artifact(s): "
            + ", ".join(missing)
        ]

    outer = pd.read_csv(paths["outer"])
    sequence_outer = pd.read_csv(
        paths["sequence_outer"]
    )
    metrics = pd.read_csv(paths["metrics"])
    nested_oof = pd.read_csv(
        paths["nested_oof"]
    )
    ablation_oof = pd.read_csv(
        paths["ablation_oof"]
    )

    with paths["config"].open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    for issue in require_columns(
        outer,
        {"test_lot", "outer_rmse"},
        "08_nested_outer_fold_results.csv",
    ):
        problems.append(issue)

    for issue in require_columns(
        sequence_outer,
        {"test_lot", "outer_rmse"},
        "08_process_plus_sequence_outer_fold_results.csv",
    ):
        problems.append(issue)

    for issue in require_columns(
        metrics,
        {"model", "rmse", "mae", "r2"},
        "08_ablation_metrics.csv",
    ):
        problems.append(issue)

    for issue in require_columns(
        nested_oof,
        {
            "experiment_key",
            "lot_number",
            "actual_mean_si_etch",
            "nested_process_pred",
            "nested_error",
            "abs_nested_error",
        },
        "08_nested_oof_predictions.csv",
    ):
        problems.append(issue)

    for issue in require_columns(
        ablation_oof,
        {
            "experiment_key",
            "lot_number",
            "actual_mean_si_etch",
            "mean_baseline_pred",
            "sequence_only_pred",
            "process_only_pred",
            "process_plus_sequence_pred",
            "process_only_error",
            "process_plus_sequence_error",
            "process_only_abs_error",
            "process_plus_sequence_abs_error",
        },
        "08_ablation_oof_predictions.csv",
    ):
        problems.append(issue)

    if problems:
        return problems

    # ----- Outer-fold lot-level comparison -----
    comparison = (
        outer[["test_lot", "outer_rmse"]]
        .rename(
            columns={
                "outer_rmse":
                    "process_only_rmse",
            }
        )
        .merge(
            sequence_outer[
                ["test_lot", "outer_rmse"]
            ].rename(
                columns={
                    "outer_rmse":
                        "process_plus_sequence_rmse",
                }
            ),
            on="test_lot",
            how="inner",
            validate="one_to_one",
        )
        .sort_values("test_lot")
        .reset_index(drop=True)
    )

    expected_lots = list(range(1, 11))
    actual_lots = (
        comparison["test_lot"]
        .astype(int)
        .tolist()
    )

    if actual_lots != expected_lots:
        problems.append(
            "08 outer-fold lots should be exactly "
            f"{expected_lots}, found {actual_lots}"
        )
    else:
        comparison["improved"] = (
            comparison[
                "process_plus_sequence_rmse"
            ]
            <
            comparison[
                "process_only_rmse"
            ]
        )

        improved_count = int(
            comparison["improved"].sum()
        )

        non_improved_lots = (
            comparison.loc[
                ~comparison["improved"],
                "test_lot",
            ]
            .astype(int)
            .tolist()
        )

        if improved_count != 8:
            problems.append(
                "Process + Sequence should improve "
                f"8/10 lots; found {improved_count}/10"
            )

        if non_improved_lots != [7, 10]:
            problems.append(
                "Non-improved lots should be "
                f"[7, 10]; found {non_improved_lots}"
            )

    # ----- OOF identity and lineage -----
    if len(nested_oof) != 88:
        problems.append(
            "08_nested_oof_predictions.csv should contain "
            f"88 rows; found {len(nested_oof)}"
        )

    if len(ablation_oof) != 88:
        problems.append(
            "08_ablation_oof_predictions.csv should contain "
            f"88 rows; found {len(ablation_oof)}"
        )

    if nested_oof["experiment_key"].duplicated().any():
        problems.append(
            "08_nested_oof_predictions.csv contains duplicate experiment_key"
        )

    if ablation_oof["experiment_key"].duplicated().any():
        problems.append(
            "08_ablation_oof_predictions.csv contains duplicate experiment_key"
        )

    nested_sorted = nested_oof.sort_values(
        "experiment_key"
    ).reset_index(drop=True)

    ablation_sorted = ablation_oof.sort_values(
        "experiment_key"
    ).reset_index(drop=True)

    if (
        nested_sorted["experiment_key"].tolist()
        != ablation_sorted["experiment_key"].tolist()
    ):
        problems.append(
            "Nested OOF and ablation OOF experiment_key sets do not match"
        )
    else:
        if not np.allclose(
            nested_sorted[
                "actual_mean_si_etch"
            ].to_numpy(dtype=float),
            ablation_sorted[
                "actual_mean_si_etch"
            ].to_numpy(dtype=float),
            rtol=0.0,
            atol=1e-12,
        ):
            problems.append(
                "Nested OOF and ablation OOF target values do not match"
            )

        if not np.allclose(
            nested_sorted[
                "nested_process_pred"
            ].to_numpy(dtype=float),
            ablation_sorted[
                "process_only_pred"
            ].to_numpy(dtype=float),
            rtol=0.0,
            atol=1e-12,
        ):
            problems.append(
                "Process-only predictions in nested OOF and ablation OOF "
                "do not match"
            )

    nested_error_expected = (
        nested_oof["nested_process_pred"]
        - nested_oof["actual_mean_si_etch"]
    )

    if not np.allclose(
        nested_oof["nested_error"],
        nested_error_expected,
        rtol=0.0,
        atol=1e-12,
    ):
        problems.append(
            "nested_error is inconsistent with prediction - actual"
        )

    if not np.allclose(
        nested_oof["abs_nested_error"],
        np.abs(nested_oof["nested_error"]),
        rtol=0.0,
        atol=1e-12,
    ):
        problems.append(
            "abs_nested_error is inconsistent with abs(nested_error)"
        )

    process_error_expected = (
        ablation_oof["process_only_pred"]
        - ablation_oof["actual_mean_si_etch"]
    )

    process_sequence_error_expected = (
        ablation_oof[
            "process_plus_sequence_pred"
        ]
        - ablation_oof[
            "actual_mean_si_etch"
        ]
    )

    if not np.allclose(
        ablation_oof["process_only_error"],
        process_error_expected,
        rtol=0.0,
        atol=1e-12,
    ):
        problems.append(
            "process_only_error is inconsistent with prediction - actual"
        )

    if not np.allclose(
        ablation_oof[
            "process_plus_sequence_error"
        ],
        process_sequence_error_expected,
        rtol=0.0,
        atol=1e-12,
    ):
        problems.append(
            "process_plus_sequence_error is inconsistent with "
            "prediction - actual"
        )

    if not np.allclose(
        ablation_oof[
            "process_only_abs_error"
        ],
        np.abs(
            ablation_oof[
                "process_only_error"
            ]
        ),
        rtol=0.0,
        atol=1e-12,
    ):
        problems.append(
            "process_only_abs_error is inconsistent"
        )

    if not np.allclose(
        ablation_oof[
            "process_plus_sequence_abs_error"
        ],
        np.abs(
            ablation_oof[
                "process_plus_sequence_error"
            ]
        ),
        rtol=0.0,
        atol=1e-12,
    ):
        problems.append(
            "process_plus_sequence_abs_error is inconsistent"
        )

    # ----- Recompute pooled metrics from OOF predictions -----
    predictions = {
        "Training-Mean":
            "mean_baseline_pred",
        "Sequence-Only":
            "sequence_only_pred",
        "Process-Only":
            "process_only_pred",
        "Process + Sequence":
            "process_plus_sequence_pred",
    }

    metric_rows = (
        metrics.set_index("model")
    )

    for model_name, pred_col in predictions.items():
        if model_name not in metric_rows.index:
            problems.append(
                f"08_ablation_metrics.csv missing model: {model_name}"
            )
            continue

        actual = ablation_oof[
            "actual_mean_si_etch"
        ]
        predicted = ablation_oof[
            pred_col
        ]

        calculated = {
            "rmse": rmse(actual, predicted),
            "mae": mae(actual, predicted),
            "r2": r2(actual, predicted),
        }

        for metric_name, value in calculated.items():
            stored = float(
                metric_rows.loc[
                    model_name,
                    metric_name,
                ]
            )

            if not np.isclose(
                stored,
                value,
                rtol=1e-10,
                atol=1e-12,
            ):
                problems.append(
                    f"{model_name} {metric_name} does not match "
                    f"OOF recomputation: stored={stored:.12f}, "
                    f"recomputed={value:.12f}"
                )

            expected = (
                EXPECTED_VM_METRICS[
                    model_name
                ][metric_name]
            )

            if not np.isclose(
                stored,
                expected,
                rtol=1e-10,
                atol=1e-12,
            ):
                problems.append(
                    f"{model_name} {metric_name} changed from the "
                    f"audited result: expected={expected:.12f}, "
                    f"found={stored:.12f}"
                )

    # ----- Final prototype configuration regression checks -----
    expected_config = {
        "target":
            "mean_si_etch",
        "feature_set":
            "Extended",
        "model":
            "ElasticNet",
        "n_training_wafers":
            88,
        "n_input_predictors":
            109,
        "n_predictors_after_variance_filter":
            98,
        "n_nonzero_coefficients":
            54,
    }

    for key, expected in expected_config.items():
        actual = config.get(key)

        if actual != expected:
            problems.append(
                f"08_final_model_config.json: {key} "
                f"expected {expected!r}, found {actual!r}"
            )

    params = config.get("params", {})

    if not np.isclose(
        float(params.get("alpha", np.nan)),
        0.01,
        rtol=0.0,
        atol=1e-12,
    ):
        problems.append(
            "08_final_model_config.json alpha should be 0.01"
        )

    if not np.isclose(
        float(params.get("l1_ratio", np.nan)),
        0.1,
        rtol=0.0,
        atol=1e-12,
    ):
        problems.append(
            "08_final_model_config.json l1_ratio should be 0.1"
        )

    # ----- Notebook text regression check -----
    notebook_path = (
        project_root
        / "notebooks"
        / "08_virtual_metrology.ipynb"
    )

    notebook = load_notebook(
        notebook_path
    )

    markdown = notebook_text(
        notebook,
        cell_type="markdown",
    )

    # Only flag stale wording that specifically describes the
    # Process + Sequence ablation. A generic "9/10 Lots" statement is
    # valid elsewhere in this notebook (Process-Only vs Mean Baseline),
    # so it must not be treated as an error.
    stale_phrases = [
        "Process + Sequence 在 **9/10 個 Lots**",
        "Process + Sequence 在 **9 / 10 個 Lots**",
        "10 個 Lots 裡有 **9 個** RMSE 下降",
        "唯一例外是 **Lot 7**",
    ]

    for phrase in stale_phrases:
        if phrase in markdown:
            problems.append(
                "08 notebook still contains stale interpretation: "
                + phrase
            )

    if re.search(
        r"\b8\s*/\s*10\b",
        markdown,
    ) is None:
        problems.append(
            "08 notebook should explicitly state the 8/10 lot result"
        )

    if "Lot 7" not in markdown:
        problems.append(
            "08 notebook should mention Lot 7 as a non-improved lot"
        )

    if "Lot 10" not in markdown:
        problems.append(
            "08 notebook should mention Lot 10 as a non-improved lot"
        )

    return problems


def main() -> int:
    project_root = find_project_root()
    notebooks_dir = (
        project_root
        / "notebooks"
    )

    print(
        f"Project root: {project_root}"
    )
    print(
        f"Notebook directory: {notebooks_dir}"
    )
    print()

    actual_notebooks = sorted(
        path.name
        for path in notebooks_dir.glob(
            "*.ipynb"
        )
        if ".ipynb_checkpoints"
        not in str(path)
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
            "Missing notebooks: "
            + ", ".join(
                missing_notebooks
            )
        )

    if unexpected_notebooks:
        global_problems.append(
            "Unexpected notebooks: "
            + ", ".join(
                unexpected_notebooks
            )
        )

    results = []

    for notebook_name in (
        EXPECTED_NOTEBOOKS
    ):
        path = (
            notebooks_dir
            / notebook_name
        )

        if not path.exists():
            continue

        results.append(
            validate_notebook(path)
        )

    print("Notebook Validation")
    print("=" * 96)

    total_notebook_problems = 0

    for result in results:
        status = (
            "PASS"
            if not result[
                "problems"
            ]
            else "FAIL"
        )

        print(
            f"{result['name']:<42} "
            f"{status:<5} | "
            f"cells={result['total_cells']:<3} "
            f"markdown={result['markdown_cells']:<3} "
            f"code={result['code_cells']:<3}"
        )

        for problem in (
            result["problems"]
        ):
            total_notebook_problems += 1
            print(
                f"    - {problem}"
            )

    repository_checks = {
        "Raw README":
            validate_raw_readme(
                project_root
            ),
        "Stale Artifacts":
            validate_stale_artifacts(
                project_root
            ),
        "08 VM Consistency":
            validate_vm_ablation(
                project_root
            ),
    }

    print()
    print("Repository Validation")
    print("=" * 96)

    repository_problem_count = 0

    for name, problems in (
        repository_checks.items()
    ):
        status = (
            "PASS"
            if not problems
            else "FAIL"
        )

        print(
            f"{name:<30} {status}"
        )

        for problem in problems:
            repository_problem_count += 1
            print(
                f"    - {problem}"
            )

    if global_problems:
        print()
        print("Repository-level Problems")
        print("-" * 96)

        for problem in global_problems:
            print(
                f"- {problem}"
            )

    total_problems = (
        total_notebook_problems
        + repository_problem_count
        + len(global_problems)
    )

    print()
    print("=" * 96)

    if total_problems == 0:
        print(
            "PASS: notebook structure, project-root logic, README, "
            "artifact cleanup, and 08 VM consistency all passed."
        )
        return 0

    print(
        f"FAIL: found {total_problems} problem(s)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
