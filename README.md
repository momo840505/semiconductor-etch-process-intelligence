# Semiconductor Etch Process Intelligence
## 半導體蝕刻製程智慧分析與虛擬量測

這個專案使用公開的 BOSCH Plasma-Etching 製程資料，從 wafer 品質、製程訊號、SPC、多變量分析、Virtual Metrology 到異常偵測，整理成一條完整的半導體製程資料分析流程。

專案重點不是只追求單一模型分數，而是先處理 Lot / wafer sequence 結構，再分開看 Process–Quality association、預測、SPC、OOD 和 model error。

---

## 1. 專案問題

這個專案主要想回答幾個問題：

1. Wafer 的 Si Etch quality 是否存在空間結構？
2. 同一個 Lot 裡，Quality 和 Process Signals 是否會隨 wafer order 改變？
3. 扣掉 Lot 內 linear sequence trend 後，哪些 Process Signals 仍和 Quality 有 association？
4. 能不能用 wafer-level process features 建立 Virtual Metrology，預測 `mean_si_etch`？
5. `wafer_number` 加進模型後，held-out-Lot prediction 是否還會改善？
6. 哪些 wafers 在 SPC、Residual Anomaly、Cross-Lot OOD 或 VM error 中值得回查？

---

## 2. Dataset

資料來源：

**A Multi-Model Dataset for BOSCH Plasma-Etching: Optical Emission Spectra, Process Parameters, and Wafer Measurements for Data-Driven Plasma Modeling**

Zenodo DOI:

https://doi.org/10.5281/zenodo.17122442

這個專案主要使用：

- `Process_data.nc`
- `Dictionary_process.nc`
- `Lot_status.xlsx`
- `Si_Oxide_etch_89_points.csv`
- `Readme.pdf`
- `Wafer_layout.pdf`

原始資料不放進 GitHub repository。

本專案沒有使用大型 daily OES `.nc` 檔案。

### 專案實際使用的資料規模

- Process wafers：96
- Quality-labeled wafers：88
- Lots：10
- 每片有 Quality label 的 wafer：89 個 spatial measurement points
- QC 後主要 Process Signals：27

---

## 3. Analysis Pipeline

| Notebook | 內容 |
|---|---|
| `00_data_understanding.ipynb` | Raw data 結構、wafer identity、Process / Quality coverage |
| `01_data_quality.ipynb` | Missing、duplicate、time-axis、feature QC |
| `02_wafer_quality_analysis.ipynb` | Wafer quality、Lot sequence、spatial pattern |
| `03_process_eda.ipynb` | Process signal EDA、Main Active Window、sequence pattern |
| `04_process_quality_relationship.ipynb` | Sequence-adjusted Process–Quality correlation + Lot-level Bootstrap |
| `05_spc_monitoring.ipynb` | Retrospective Phase-I I-MR SPC |
| `06_multivariate_analysis.ipynb` | Correlation、Raw PCA、Sequence-adjusted Residual PCA |
| `07_feature_engineering.ipynb` | Wafer-level process feature engineering |
| `08_virtual_metrology.ipynb` | Nested Leave-One-Lot-Out VM + Process + Sequence Ablation |
| `09_model_explainability.ipynb` | Coefficients + grouped permutation sensitivity |
| `10_anomaly_detection.ipynb` | Residual anomaly、Pure Cross-Lot OOD、VM error comparison |
| `11_final_findings.ipynb` | Cross-artifact validation 與 Final Findings |

---

## 4. 主要分析結果

### 4.1 Wafer quality 有明顯 spatial difference

88 片 labeled wafers 的：

- Mean Si Etch 平均：**43.66812 µm**
- Mean CV：**8.21143%**
- Outer - inner pooled mean：**+5.03895 µm**

外圈與內部量測區的平均 Si Etch level 並不相同。

---

### 4.2 Quality 和 Process 都有 wafer-sequence structure

Quality：

- Mean Si Etch slope < 0：**10 / 10 Lots**
- CV slope < 0：**9 / 10 Lots**

Process：

- Median `|within-Lot Spearman|`：**0.38788 → 0.08485**
- **24 / 24** comparable process features 在 detrending 後都下降

所以後續 correlation、SPC 與 modeling 都保留 Lot / wafer sequence 的資料結構。

---

### 4.3 Process–Quality Association

在每個 Lot 內先扣掉 linear wafer-sequence trend 後：

Mean Si Etch：

- Exploratory candidates：**5**
- Bootstrap interval 沒跨 0：**4 / 5**
- `PlatenRFLoadPower` adjusted Pearson：**-0.6090**

CV Si Etch：

- Exploratory candidates：**7**
- Bootstrap interval 沒跨 0：**4 / 7**
- `Heater4Temp` adjusted Pearson：**+0.5513**

這些結果只當作 exploratory association，不當成 causal effect。

---

## 5. Virtual Metrology

Target：

`mean_si_etch`

Validation：

**Nested Leave-One-Lot-Out**

四種設定的結果：

| Model | RMSE (µm) | MAE (µm) | R² |
|---|---:|---:|---:|
| Training-Mean | 0.40437 | 0.3477 | -0.0239 |
| Sequence-Only | 0.22093 | 0.1833 | 0.6944 |
| Process-Only | 0.12963 | 0.09723 | 0.89477 |
| Process + Sequence | **0.09540** | **0.07500** | **0.94301** |

Process + Sequence 相比 Process-Only：

- RMSE 約低 **26.4%**
- **8 / 10 Lots** 的 RMSE 更低

Primary Process-only outer folds：

- ElasticNet：10 / 10
- Extended：6 folds
- Base：4 folds

Process + Sequence outer folds：

- ElasticNet：10 / 10
- Base：10 / 10

---

## 6. Explainability

Nested grouped permutation sensitivity 第一名：

`PlatenRFTuningCapacitor`

- Mean ΔRMSE：**+0.24996 µm**

Final ElasticNet sensor coefficient aggregation 第一名也是：

`PlatenRFTuningCapacitor`

這裡解讀的是 predictive dependence，不是製程因果。

---

## 7. SPC、Anomaly 與 Cross-Lot OOD

Phase-I SPC：

- I-chart feature-wafer flags：46
- Unique wafers with I-chart flag：19
- MR feature-wafer flags：47
- Unique wafers with MR flag：23

Residual Anomaly：

- Review candidates：3 / 96

Pure Cross-Lot OOD：

- Candidates：5 / 96

兩者 overlap：

- 2 wafers

Process score 和 `|OOF error|` 中最高的 Spearman：

- `ood_pca_recon_rmse`
- rho = **0.30948**
- 95% Lot-bootstrap interval = **[0.00848, 0.60309]**

---

## 8. Lot 8

Primary Process-only VM：

- RMSE：**0.22384 µm**
- Max absolute OOF error：**0.57555 µm**

Process + Sequence：

- RMSE：**0.10707 µm**

其他 review signals：

- Residual candidates：2
- Cross-Lot OOD candidates：3
- SPC I-chart flagged wafers：6

這些結果代表不同 review channels 在 Lot 8 同時出現較多訊號，但不能直接解讀成 defect probability。

---

## 9. Final Prototype

Final full-data prototype：

- Feature Set：Extended
- Model：ElasticNet
- `alpha = 0.01`
- `l1_ratio = 0.1`
- Input predictors：109
- Near-Constant Filter 後：98
- Non-zero coefficients：54

正式 performance evidence 仍以 Nested Leave-One-Lot-Out OOF 為主，不使用 full-data fit 的 training performance 當泛化成績。

---

## 10. 專案結構

```text
semiconductor-etch-process-intelligence/
│
├─ data/
│  ├─ raw/
│  │  └─ README.md
│  ├─ interim/
│  └─ processed/
│
├─ models/
│
├─ notebooks/
│  ├─ 00_data_understanding.ipynb
│  ├─ 01_data_quality.ipynb
│  ├─ 02_wafer_quality_analysis.ipynb
│  ├─ 03_process_eda.ipynb
│  ├─ 04_process_quality_relationship.ipynb
│  ├─ 05_spc_monitoring.ipynb
│  ├─ 06_multivariate_analysis.ipynb
│  ├─ 07_feature_engineering.ipynb
│  ├─ 08_virtual_metrology.ipynb
│  ├─ 09_model_explainability.ipynb
│  ├─ 10_anomaly_detection.ipynb
│  └─ 11_final_findings.ipynb
│
├─ reports/
│  └─ figures/
│
├─ scripts/
│  └─ validate_notebooks.py
│
├─ requirements.txt
├─ .gitignore
└─ README.md
```

---

## 11. 執行方式

### 建立環境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 準備 Raw Data

依照：

`data/raw/README.md`

下載資料並放到：

```text
data/raw/
```

### 執行 Notebook

請依照：

```text
00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11
```

順序執行。

### Notebook Validation

```powershell
python scripts\validate_notebooks.py
```

全部成功時應顯示：

```text
PASS: 00～11 全部 Notebook 通過結構與執行狀態檢查。
```

---

## 12. 專案限制

目前資料只有 10 個 Lots，因此這個專案仍然是 prototype。

主要限制包括：

- 尚未使用更多不同 tool / recipe / maintenance state 的 production data
- 沒有 future chronological 或 external production validation
- SPC 目前是 retrospective Phase-I limits
- OOD threshold 仍是目前資料上的 empirical calibration
- Process–Quality correlation、Bootstrap 與 Explainability 都不能直接當成 causal evidence
- 尚未建立正式 deployment monitoring、drift detection、retraining 與 rollback policy

---

## 13. Tech Stack

- Python
- pandas
- NumPy
- SciPy
- scikit-learn
- netCDF4
- matplotlib
- joblib
- Jupyter
- ElasticNet
- PLS Regression
- Ridge
- SVR
- PCA
- SPC
- Leave-One-Lot-Out Cross-Validation
