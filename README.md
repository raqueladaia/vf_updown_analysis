# Von Frey Up-Down Analysis Tool

A GUI and CLI tool for computing 50% withdrawal thresholds from von Frey up-down data and producing publication-ready figures with statistical analysis.

## Background

The von Frey test is a standard method for assessing mechanical sensitivity in rodents. An animal is placed on a mesh platform and its hindpaw is probed with calibrated nylon monofilaments of increasing or decreasing force. The experimenter records whether the animal withdraws its paw (positive response, `x`) or not (negative response, `o`).

The **up-down method** (Dixon, 1980; Chaplan et al., 1994) is an efficient procedure that adjusts the stimulus intensity based on the animal's response: after a withdrawal, a lighter filament is applied (step down); after no withdrawal, a heavier filament is applied (step up). The sequence of responses is recorded as a string of `x` and `o` characters (e.g., `oxooxo`), and this pattern, together with the final filament used, determines the **50% withdrawal threshold** — the estimated force at which the animal has a 50% probability of withdrawing.

This tool automates the threshold computation from raw response series, generates publication-quality figures for longitudinal and factorial experimental designs, and provides built-in statistical analysis with multiple comparison correction.

## Features

- **50% threshold computation** using the Dixon up-down method with tabulated k-statistics
- **Two experimental designs supported:**
  - **Longitudinal** (3+ timepoints) — individual animal traces + group mean ± SEM line plots
  - **Factorial pre-post** (exactly 2 timepoints) — paired lines and delta plots, with
    **panel factors** to split figures when data files have multiple pre/post blocks per mouse
    (e.g. drug × treatment × light/dark)
- **Statistical analysis:** repeated-measures ANOVA, pairwise t-tests, mixed-effects models, delta score ANOVA
- **Multiple comparison correction:** Holm-Bonferroni, Bonferroni, Benjamini-Hochberg (FDR)
- **Publication-ready figures:** Arial font, editable PDF output (type 42 fonts for Adobe Illustrator), log-scale y-axis, sex-specific encoding, despined axes
- **Export:** PDF, PNG, SVG figures; Excel/CSV data and statistics tables; multi-panel export when several figures are configured
- **GUI** with live plot preview, animal inclusion checklist, and step-by-step workflow
- **CLI** mode for batch threshold computation
- **Session save/load** to preserve your analysis configuration (JSON)

**Bundled examples:** see [Example datasets](#example-datasets) — timeline (SNI) and pre-post designs, each with separate measurement and metadata files in `data/`.

---

## Getting set up

### Requirements

- **Python 3.9 or later**
- **Git** (to clone the repository)
- **Arial** font recommended for publication figures (usually pre-installed on Windows/macOS)

### 1. Clone the repository

```bash
git clone https://github.com/raqueladaia/vf_updown_analysis.git
cd vf_updown_analysis
```

> If your local folder has a different name (e.g. `vF_analysis`), use that directory instead.

### 2. Create and activate a virtual environment

Using a virtual environment keeps dependencies isolated from your system Python.

**Windows (PowerShell or Command Prompt):**

```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your shell prompt when the environment is active.

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

| Package | Purpose |
|---------|---------|
| PyQt6 | GUI framework |
| matplotlib | Plotting |
| seaborn | Plot styling |
| pandas | Data handling |
| numpy | Numerical computation |
| scipy | t-tests |
| statsmodels | ANOVA, mixed-effects models |
| pingouin | Repeated-measures ANOVA, effect sizes |
| openpyxl | Excel file reading/writing |

### 4. Verify the installation

Run the lightweight smoke test (no GUI window opens):

**Windows:**

```powershell
venv\Scripts\python.exe tests\smoke_test.py
```

**macOS / Linux:**

```bash
python tests/smoke_test.py
```

Expected output:

```
smoke_test: OK
```

If this fails, check that the virtual environment is activated and all packages installed without errors.

### 5. Confirm the filament reference file

The threshold calculator requires `data/VF_Calculator_Up-down.xlsx`. This file is included in the repository and must not be edited (see [Reference file](#reference-file-vf_calculator_up-downxlsx) below).

### 6. Launch the GUI

From the project root, with the virtual environment activated:

```bash
python run.py
```

Alternative entry points (equivalent):

```bash
python -m src
python -m src.main
```

---

## Quick start with example data

After setup, you can try the bundled examples without your own files. Each experiment ships as a **pair of files**: von Frey measurements + animal metadata.

### Option A — Timeline (longitudinal / SNI)

1. **Launch the GUI:** `python run.py`
2. **Step 1 — Data**
   - Filament reference: `data/VF_Calculator_Up-down.xlsx`
   - Data file: `data/data_timeline_experiment.xlsx`
   - Metadata: `data/metadata_timeline_experiment.xlsx`
   - Map **Mouse ID** in metadata to `animal_id` (data file uses `mouse`)
   - Map **Sex column** to `sex`
   - Click **Compute Thresholds**
3. **Step 2** — Compare groups using `group_name` from metadata (e.g. SNI vs uninjured vs drug). Keep all five timepoints for a **longitudinal** plot; set intervention marker at `0` (SNI surgery day) if desired.
4. **Steps 3–6** — appearance, preview, statistics, export

### Option B — Pre-post (factorial)

1. **Step 1 — Data**
   - Data file: `data/data_pre-post_experiment.xlsx`
   - Metadata: `data/metadata_pre-post_experiment.xlsx`
   - Map sex to `sex`; mouse IDs match between files (`mouse`)
2. **Step 2** — Active timepoints: `pre` and `post` only. Use **panel factors** and **compare within figure** as in the [pre-post worked example](#worked-example-pre-post-experiment) below.
3. Continue through preview, statistics, and export.

### CLI: compute thresholds only

```bash
python run.py --compute \
  --data data/data_timeline_experiment.xlsx \
  --metadata data/metadata_timeline_experiment.xlsx \
  --output results/
```

```bash
python run.py --compute \
  --data data/data_pre-post_experiment.xlsx \
  --metadata data/metadata_pre-post_experiment.xlsx \
  --output results/
```

Batch mode writes `vf_thresholds.xlsx` with a `threshold_50` column; it does not run plots or statistics.

---

## Worked example: pre-post experiment

The file `data/data_pre-post_experiment.xlsx` has **multiple sessions per mouse** (`drug` × `treatment` × `pre`/`post`). Use **panel factors** to choose which sessions each figure shows, and **compare within each figure** for the factor you want to contrast (e.g. `sal` vs `drug`).

> **Incomplete data:** this example file has no measurements for **`sal` + `chronic`** (neither pre nor post). `drug` + `chronic` includes both pre and post. Plan analyses accordingly — e.g. compare sal vs drug for **acute** treatment only, or use `drug` + chronic as a separate panel.

| Goal | Step 2 configuration |
|------|----------------------|
| Compare **sal vs drug** after **acute** administration | **Separate figures by:** `treatment` → `acute`. **Compare within each figure:** `drug` |
| Compare **sal vs drug** after **chronic** administration (drug arm only) | **Separate figures by:** `treatment` → `chronic`. **Compare within each figure:** `drug` (only the `drug` level has data) |
| Separate figures for acute vs chronic, compare sal vs drug in each | **Separate figures by:** `treatment` → All. **Compare within each figure:** `drug` |
| Compare **control vs experimental** (metadata) within acute sal vs drug | **Separate figures by:** `treatment` → `acute`. **Compare within each figure:** `drug` and `condition` *(if both needed, pick one as compare factor per analysis)* |

Use the **Figure panel** dropdown in Step 4 to preview each generated figure. Statistics and export run for **all panels** when multiple figures are configured.

---

## The Dixon Up-Down Method

The 50% withdrawal threshold is computed using the formula:

```
threshold = 10^(Xf + k * d) / 10,000
```

Where:

| Variable | Meaning |
|----------|---------|
| **Xf** | Log value of the final filament in the series |
| **k** | Tabulated statistic determined by the x/o response pattern |
| **d** (delta) | Mean log interval between filaments = 0.4414 |

The log value of each filament is computed from its force as: `Log = log10(10 * force_in_grams * 1000)`.

### Reference file: `VF_Calculator_Up-down.xlsx`

This file ships with the repository in the `data/` folder and contains two lookup tables:

1. **Filament reference table** — Calibration data for 8 von Frey filaments:

   | Filament | Force (g) | Log (in Excel) | Marking |
   |----------|-----------|----------------|---------|
   | 1 | 0.0045 | 1.65 | 0.008 |
   | 2 | 0.0230 | 2.36 | 0.020 |
   | 3 | 0.0680 | 2.83 | 0.070 |
   | 4 | 0.1580 | 3.22 ⚠️ | 0.160 |
   | 5 | 0.1780 | 3.61 | 0.400 |
   | 6 | 1.2020 | 4.08 | 1.000 |
   | 7 | 2.0410 | 4.31 | 2.000 |
   | 8 | 5.4950 | 4.74 | 6.000 |

   ⚠️ **Filament 4 only:** the `Log` value stored in the Excel file (3.22) does not match the value obtained from the standard formula using the listed force (see below).

2. **k-statistic lookup table** — 248 entries mapping every possible x/o response pattern (2 to 9 characters) to its corresponding k value. For example: `OX → -0.500`, `OXOOXO → 0.168`, `OOXXOO → 0.000`.

> **Do not edit this file** unless you know what you are doing. The k-statistic table and filament forces must stay as shipped. The incorrect filament-4 `Log` entry is a known legacy issue in the original calculator spreadsheet (see next section).

### Log column choice (`Log` vs `Log_new`)

The original `VF_Calculator_Up-down.xlsx` spreadsheet stores a `Log` column for each filament. For **filament 4** (0.158 g), that value is **incorrect**:

| Source | Filament 4 log value |
|--------|----------------------|
| `Log` column in Excel | **3.22** |
| Computed from force: `log10(10 × 0.158 × 1000)` | **3.199** (`Log_new`) |

All other filaments match between `Log` and `Log_new` (to three decimal places). Because the 50% threshold formula uses the log of the **final filament**, sessions ending on filament 4 will give slightly different thresholds depending on which column you choose.

The tool therefore offers two options:

| Option | Description | When to use |
|--------|-------------|-------------|
| **`Log_new`** (default) | Recomputed from each filament’s force using the formula above | **Recommended** — corrects the filament 4 error |
| **`Log`** | Values copied from the original Excel `Log` column | Only if you need **bit-for-bit compatibility** with older analyses or the legacy Excel calculator |

Select in **Step 1** of the GUI, or with `--log-column Log_new` / `--log-column Log` in CLI mode.

---

## Data format requirements

### Experimental data file

An Excel (`.xlsx`) or CSV file with one row per mouse per timepoint per experimental block. Required columns:

| Column | Description | Example |
|--------|-------------|---------|
| `mouse` | Unique animal identifier | `1441` |
| *timepoint column* | Timepoint label (any column name) — numeric (days) or categorical (text) | `-1`, `3`, `14` or `pre`, `post` |
| `xo_series` | String of `x` (withdraw) and `o` (no withdraw) characters | `oxooxo` |
| `last_filament` | Integer number (1–8) of the final filament in the series | `5` |

The timepoint column can have any name. You map it in the GUI.

### Metadata file (optional)

An Excel or CSV file with one row per mouse. Used to assign groups, sex, and other experimental variables.

| Column | Description | Example |
|--------|-------------|---------|
| `mouse` (or map e.g. `animal_id`) | Must match the data file | `1441` |
| `sex` | `male` or `female` — used for sex encoding on plots | `female` |
| *group column(s)* | Any column(s) defining experimental groups | `group_name`, `condition`, `phase` |
| `accept` / `include_in_analysis` (optional) | Inclusion flag: `1` = include, `0` = exclude by default | `1` |

If your metadata file uses a column named `gender` instead of `sex`, map it in Step 1 (the tool auto-detects columns whose names contain “sex” or “gender”). The timeline example uses `animal_id` rather than `mouse` — map that column as the mouse ID in Step 1.

### Multi-block pre-post data files

Some experiments record **multiple pre/post pairs per mouse** in one file, distinguished by extra columns (panel factors), for example:

| mouse | drug | treatment | timepoint | xo_series | last_filament |
|-------|------|-----------|-----------|-----------|---------------|
| 4812 | sal | acute | pre | ooooxxoxx | 6 |
| 4812 | sal | acute | post | ... | ... |
| 4812 | drug | acute | pre | ... | ... |
| 4812 | drug | chronic | pre | ... | ... |

**Rules:**

- Each analysis compares **only pre vs post** (exactly two active timepoints).
- In Step 2, use **Separate figures by** to fix which session(s) each figure shows (e.g. `treatment=acute` only, or All for every combination).
- Use **Compare within each figure** for factors you want to contrast on the same plot (e.g. `drug` for sal vs drug).
- A column cannot be both a panel factor and a compare factor.
- If metadata has an `accept` or `include_in_analysis` column, animals with value `0` appear in the Step 4 checklist **unchecked** (excluded from plots and group means). You can check them to include them in the analysis.

Do **not** load incompatible timepoints into one pre-post analysis — exclude extras in Step 2 or split the file.

---

## Example datasets

The `data/` folder contains the filament calculator plus **two worked examples**. Each example consists of a **von Frey data file** (measurements) and a **metadata file** (animal information). Load both in Step 1.

| File | Role |
|------|------|
| `VF_Calculator_Up-down.xlsx` | Required reference for threshold computation (do not edit) |
| `data_timeline_experiment.xlsx` | Von Frey measurements — timeline / SNI design |
| `metadata_timeline_experiment.xlsx` | Animal metadata — timeline experiment |
| `data_pre-post_experiment.xlsx` | Von Frey measurements — pre-post design |
| `metadata_pre-post_experiment.xlsx` | Animal metadata — pre-post experiment |

---

### Timeline experiment (longitudinal)

**Biological design:** Mice are tested with von Frey filaments **before and at several timepoints after** induction of chronic pain using the **spared nerve injury (SNI)** model. Timepoints are expressed as **days relative to SNI** (surgery at day 0). The example includes injured (SNI) animals, uninjured controls, and a pharmacological treatment group.

**Files**

| File | Rows | Key columns |
|------|------|-------------|
| `data_timeline_experiment.xlsx` | 295 | `mouse`, `Timepoint_SNI_day`, `xo_series`, `last_filament` |
| `metadata_timeline_experiment.xlsx` | 59 | `animal_id`, `sex`, `group_name`, `group_id`, `cohort`, `include_in_analysis`, `comments` |

**Measurements:** **59 mice** (one row per animal per timepoint), with timepoints **−1, 3, 7, 14, 21** (day −1 = pre-SNI baseline; surgery at day 0). Every animal has **five** complete observations.

**Metadata groups (`group_name`):** `SNI` (injured, *n* = 24), `drug` (*n* = 23), `uninjured` (*n* = 12). All 59 metadata animals have von Frey measurements in the data file. Map metadata **mouse ID** to `animal_id`. Use `group_name` as the comparison factor in Step 2.

The metadata column `include_in_analysis` flags three animals as excluded from the original study (`0`). These appear **unchecked** in the Step 4 animal checklist after you compute thresholds; you can re-include them by checking their boxes.

**Suggested workflow:** Longitudinal line plot; optional intervention line at **x = 0** (SNI). Compare `SNI` vs `uninjured` and/or `drug` across time. Enable sex encoding for male/female line styles.

---

### Pre-post experiment (factorial)

**Biological design:** **Uninjured** mice are tested **before and after** either **acute** or **chronic** administration of a chemogenetic drug (values `sal` vs `drug` in the data file). Metadata assigns `control` vs `experimental` cohorts.

**Files**

| File | Rows | Key columns |
|------|------|-------------|
| `data_pre-post_experiment.xlsx` | 144 | `mouse`, `drug`, `treatment`, `timepoint`, `xo_series`, `last_filament` |
| `metadata_pre-post_experiment.xlsx` | 24 | `mouse`, `sex`, `condition`, `group`, `accept` |

**Measurements:** 24 mice × up to four sessions per mouse (`drug` × `treatment` × `pre`/`post`).

**Data completeness (important):**

| drug | treatment | pre | post |
|------|-----------|-----|------|
| sal | acute | ✓ (24 mice) | ✓ |
| drug | acute | ✓ | ✓ |
| drug | chronic | ✓ | ✓ |
| sal | chronic | — | — |

There are **no** `sal` + `chronic` sessions in this example file. Chronic post-threshold data exist for the **drug** condition only. This mirrors an incomplete experiment and is useful for learning how **panel factors** restrict analyses to valid subsets (e.g. acute sal vs drug, or chronic drug pre vs post).

**Suggested workflow:** Factorial pre-post mode (`pre` vs `post`). Use panel factors for `treatment` (and optionally `condition` from metadata). Compare `drug` within each figure. See the [worked example](#worked-example-pre-post-experiment) above.

---

## GUI workflow

The GUI follows a 6-step workflow in the left sidebar.

### Step 1: Data

- Load **experimental data** (Excel or CSV)
- Load **filament reference** (`data/VF_Calculator_Up-down.xlsx`)
- Optionally load **metadata** for group/sex
- Map column names (mouse, timepoint, `xo_series`, `last_filament`)
- Choose log column (`Log_new` recommended)
- Click **Compute Thresholds**

### Step 2: Groups & timepoints

**Pre-post (≤2 active timepoints):**

- **Separate figures by (panel factors)** — columns that split data into different figures. Check **All** for every level, or pick specific values. Multiple panel factors create all combinations (e.g. light/dark × acute/chronic = 4 figures).
- **Compare within each figure** — factors compared on the same plot (e.g. `drug` for sal vs drug). Shown with different colors.
- Exclude or reorder timepoints; pre/post labels are inferred automatically when exactly two timepoints remain.

**Longitudinal (3+ timepoints):**

- Select group columns from metadata and/or data file
- Exclude or reorder timepoints
- Set optional **intervention marker** (vertical dashed line at a numeric x-value)

The status line reports how many figures will be generated and whether pre/post pairing is valid.

### Step 3: Appearance

- **Plot type** is auto-suggested from the design (longitudinal vs paired vs delta)
- Set **colors** per group/condition
- **Sex encoding:**
  - *Longitudinal:* markers (● male, ▲ female) and line styles (solid/dotted) when enabled
  - *Paired pre-post:* line styles only (solid male, dotted female); group means shown as thick pre→post lines with SEM
- Axis labels, title, figure size, log/linear y-axis

### Step 4: Preview

- Live matplotlib canvas
- **Figure panel** dropdown when multiple panel combinations exist
- **Animal checklist** — uncheck animals to exclude from traces and group means (exploratory). Animals with `accept` or `include_in_analysis` equal to `0` in metadata start unchecked.
- Regenerate after changing settings

### Step 5: Statistics

- **Longitudinal:** RM two-way ANOVA (default), pairwise t-tests, or mixed-effects model
- **Pre-post:** delta scores, ANOVA on deltas, post-hoc comparisons (Cohen's d reported)
- Multiple comparison correction: Holm-Bonferroni (default), Bonferroni, FDR
- Significance annotations on plots when analysis has been run

### Step 6: Export

- Figures: **PDF** (Illustrator-compatible), **PNG**, **SVG** — one file per panel when multiple figures are configured
- Data and statistics: Excel / CSV
- **Session** save/load via File menu (Ctrl+S / Ctrl+O)

---

## Command-line interface

| Argument | Description | Default |
|----------|-------------|---------|
| *(no flags)* | Launch the GUI | — |
| `--compute` | Run threshold computation only (no GUI) | — |
| `--data` | Path to von Frey data file (required with `--compute`) | — |
| `--metadata` | Path to metadata file (optional) | — |
| `--filament-ref` | Path to filament reference file | `data/VF_Calculator_Up-down.xlsx` |
| `--output` | Output directory | `.` |
| `--log-column` | `Log_new` or `Log` | `Log_new` |

Output file: `vf_thresholds.xlsx` in the output directory.

---

## Statistical methods

### Repeated-measures two-way ANOVA

Default for longitudinal designs. Uses `pingouin.mixed_anova` with group as between-subject factor and timepoint as within-subject factor. Greenhouse-Geisser correction when sphericity is violated. Reports F, df, p, partial eta-squared.

### Pairwise t-tests with multiple comparison correction

Welch's t-test at each timepoint; all p-values corrected together (Holm, Bonferroni, or FDR). Reports t, df, Cohen's d.

### Linear mixed-effects model

`threshold ~ C(group) * C(timepoint)` with random intercept per mouse. Falls back to additive model if interaction model fails.

### Delta score analysis (pre-post)

For each panel figure:

1. Delta = post − pre per animal (respecting pairing columns when multiple drugs/treatments exist per mouse)
2. ANOVA on deltas
3. Post-hoc pairwise tests with correction

### Significance on plots

`*` p < 0.05, `**` p < 0.01, `***` p < 0.001, `n.s.` otherwise, with corrected p-values when enabled.

---

## Project structure

```
vf_updown_analysis/
├── run.py                          # Main entry point
├── requirements.txt
├── tests/
│   └── smoke_test.py               # Quick install verification (no GUI)
├── data/
│   ├── VF_Calculator_Up-down.xlsx       # Required filament & k-stat tables
│   ├── data_timeline_experiment.xlsx    # Example: von Frey (timeline / SNI)
│   ├── metadata_timeline_experiment.xlsx
│   ├── data_pre-post_experiment.xlsx    # Example: von Frey (pre-post)
│   └── metadata_pre-post_experiment.xlsx
└── src/
    ├── main.py                     # CLI argument parsing
    ├── core/
    │   ├── vf_threshold.py         # 50% threshold (Dixon up-down)
    │   ├── statistics.py           # Tests, corrections, effect sizes
    │   └── data_loader.py          # Loading, validation, panel facets
    ├── plotting/
    │   ├── longitudinal.py
    │   ├── factorial.py            # Paired & delta plots
    │   └── plot_utils.py
    └── gui/
        ├── app.py
        ├── data_input.py           # Step 1
        ├── group_config.py         # Step 2
        ├── plot_config.py          # Steps 3–4
        ├── export_panel.py         # Steps 5–6
        └── state.py
```

---

## Troubleshooting

### `ModuleNotFoundError` when running the app

Activate the virtual environment and reinstall:

```bash
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### Smoke test fails

Run with the venv Python explicitly (Windows):

```powershell
venv\Scripts\python.exe tests\smoke_test.py
```

### NaN threshold values

Usually invalid `xo_series`, blank cells, or `last_filament` outside 1–8. Check the NaN count after **Compute Thresholds**.

### Pre-post validation errors in Step 2

Each mouse must have exactly one pre and one post row **per panel**. If animals have multiple drugs or treatments, put the varying factor under **Compare within each figure** (e.g. `drug`), not under **Separate figures by** with multiple values that break pairing.

### Mixed-effects model fails to converge

Try RM-ANOVA or pairwise t-tests; check for groups with n < 2 or empty cells.

### Figures not editable in Illustrator

PDFs use `fonttype=42` (TrueType). Ensure Arial is installed.

---

## Citation

If you use this tool in your research, please cite:

> Sandoval Ortega, R. A. (2026). Von Frey Up-Down Analysis Tool. GitHub repository. https://github.com/raqueladaia/vf_updown_analysis

Methodological references:

> Dixon, W. J. (1980). Efficient analysis of experimental observations. *Annual Review of Pharmacology and Toxicology*, 20, 441-462.

> Chaplan, S. R., Bach, F. W., Pogrel, J. W., Chung, J. M., & Yaksh, T. L. (1994). Quantitative assessment of tactile allodynia in the rat paw. *Journal of Neuroscience Methods*, 53(1), 55-63.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
