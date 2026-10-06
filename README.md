# Von Frey Up-Down Analysis Tool

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20762768.svg)](https://doi.org/10.5281/zenodo.20762768)

A GUI and CLI tool for computing 50% withdrawal thresholds from von Frey up-down data and producing publication-ready figures with statistical analysis.

## Table of Contents

- [Background](#background)
- [Features](#features)
- [Getting set up](#getting-set-up)
  - [Requirements](#requirements)
  - [Clone the repository](#1-clone-the-repository)
  - [Create and activate a virtual environment](#2-create-and-activate-a-virtual-environment)
  - [Install dependencies](#3-install-dependencies)
  - [Verify the installation](#4-verify-the-installation)
  - [Confirm the filament reference file](#5-confirm-the-filament-reference-file)
  - [Launch the GUI](#6-launch-the-gui)
- [Quick start with example data](#quick-start-with-example-data)
  - [Option A — Timeline (longitudinal / SNI)](#option-a--timeline-longitudinal--sni)
  - [Option B — Pre-post (factorial)](#option-b--pre-post-factorial)
  - [CLI: compute thresholds only](#cli-compute-thresholds-only)
- [Worked example: pre-post experiment](#worked-example-pre-post-experiment)
- [The Dixon Up-Down Method](#the-dixon-up-down-method)
  - [Reference file: `VF_Calculator_Up-down.xlsx`](#reference-file-vf_calculator_up-downxlsx)
  - [Log column choice (`Log` vs `Log_new`)](#log-column-choice-log-vs-log_new)
- [Data format requirements](#data-format-requirements)
  - [Experimental data file](#experimental-data-file)
  - [Metadata file (optional)](#metadata-file-optional)
  - [Multi-block pre-post data files](#multi-block-pre-post-data-files)
- [Example datasets](#example-datasets)
  - [Timeline experiment (longitudinal)](#timeline-experiment-longitudinal)
  - [Pre-post experiment (factorial)](#pre-post-experiment-factorial)
- [GUI workflow](#gui-workflow)
  - [Step 1: Data](#step-1-data)
  - [Step 2: Groups & timepoints](#step-2-groups--timepoints)
  - [Step 3: Appearance](#step-3-appearance)
  - [Step 4: Preview](#step-4-preview)
  - [Step 5: Statistics](#step-5-statistics)
  - [Step 6: Export](#step-6-export)
- [Command-line interface](#command-line-interface)
- [Statistical methods](#statistical-methods)
  - [Repeated-measures two-way ANOVA](#repeated-measures-two-way-anova)
  - [Pairwise t-tests with multiple comparison correction](#pairwise-t-tests-with-multiple-comparison-correction)
  - [Linear mixed-effects model](#linear-mixed-effects-model)
  - [Delta score analysis (pre-post)](#delta-score-analysis-pre-post)
  - [Significance on plots](#significance-on-plots)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Citation](#citation)
  - [Methodological references](#methodological-references)
- [License](#license)

## Species and calculation choices

**All bundled experimental Excel workbooks are mouse examples**, now named
`mouse_*.xlsx`. Use the Mouse setting for those files. The existing
`VF_Calculator_Up-down.xlsx` is the **mouse master**.

- **Mice:** choose calculated `Log_new` or stored master `Log` values. Both use
  the threshold formula; historical mouse results are preserved.
- **Rats:** no master Excel file is required. Logs, ladder spacing, and thresholds
  are calculated from the nominal target forces (0.4–15 g), using a standalone
  species-independent k table. Use a custom CSV for measured calibration.
- **Plots:** mouse maximum defaults to 10 g; rat defaults to an adjustable 20 g.
- **Boundaries:** rows are retained with explicit flags; select a policy before
  plotting or statistics. Numerical endpoint substitution is an explicit choice.

Read the [calculation guide](docs/filament_sets.md),
[boundary policy guide](docs/boundary_handling.md), and
[annotated papers/FAQ](docs/references.md) before analyzing a new ladder.

## Background

The von Frey test is a standard method for assessing mechanical sensitivity in rodents. An animal is placed on a mesh platform and its hindpaw is probed with calibrated nylon monofilaments of increasing or decreasing force. The experimenter records whether the animal withdraws its paw (positive response, `x`) or not (negative response, `o`).

The **up-down method** (Dixon, 1980; Chaplan et al., 1994) is an efficient procedure that adjusts the stimulus intensity based on the animal's response: after a withdrawal, a lighter filament is applied (step down); after no withdrawal, a heavier filament is applied (step up). The sequence of responses is recorded as a string of `x` and `o` characters (e.g., `oxooxo`), and this pattern, together with the final filament used, determines the **50% withdrawal threshold** — the estimated force at which the animal has a 50% probability of withdrawing.

This tool automates the threshold computation from raw response series, generates publication-quality figures for longitudinal and factorial experimental designs, and provides built-in statistical analysis with multiple comparison correction.

## Features

- **50% threshold computation** using the Dixon up-down method with tabulated k-statistics
- **Filament sets:** unchanged legacy mouse calibration, a sourced rat reference (~0.4–15 g), or a custom calibrated CSV ladder. See [filament sets and method limits](docs/filament_sets.md).
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

Mouse analysis requires `data/VF_Calculator_Up-down.xlsx`; rat/custom analysis does not require an Excel master. This file is included in the repository and must not be edited (see [Reference file](#reference-file-vf_calculator_up-downxlsx) below).

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

These are **mouse data**. Select the Mouse filament set. The example contains
boundary observations; choose the lab's policy in Step 1 before plotting or
statistics (see [boundary guide](docs/boundary_handling.md)).

1. **Launch the GUI:** `python run.py`
2. **Step 1 — Data**
   - Filament reference: `data/VF_Calculator_Up-down.xlsx`
   - Data file: `data/mouse_data_timeline_experiment.xlsx`
   - Metadata: `data/mouse_metadata_timeline_experiment.xlsx`
   - Map **Mouse ID** in metadata to `animal_id` (data file uses `mouse`)
   - Map **Sex column** to `sex`
   - Click **Compute Thresholds**
3. **Step 2** — Compare groups using `group_name` from metadata (e.g. SNI vs uninjured vs drug). Keep all five timepoints for a **longitudinal** plot; set intervention marker at `0` (SNI surgery day) if desired.
4. **Steps 3–6** — appearance, preview, statistics, export

### Option B — Pre-post (factorial)

These are **mouse data**. Select the Mouse filament set.

1. **Step 1 — Data**
   - Data file: `data/mouse_data_pre-post_experiment.xlsx`
   - Metadata: `data/mouse_metadata_pre-post_experiment.xlsx`
   - Map sex to `sex`; mouse IDs match between files (`mouse`)
2. **Step 2** — Active timepoints: `pre` and `post` only. Use **panel factors** and **compare within figure** as in the [pre-post worked example](#worked-example-pre-post-experiment) below.
3. Continue through preview, statistics, and export.

### CLI: compute thresholds only

```bash
python run.py --compute \
  --data data/mouse_data_timeline_experiment.xlsx \
  --metadata data/mouse_metadata_timeline_experiment.xlsx \
  --output results/
```

```bash
python run.py --compute \
  --data data/mouse_data_pre-post_experiment.xlsx \
  --metadata data/mouse_metadata_pre-post_experiment.xlsx \
  --output results/
```

Batch mode writes `vf_thresholds.xlsx` with a `threshold_50` column; it does not run plots or statistics.

For rat data, add `--filament-set rat`. For your own calibrated ladder, add
`--filament-set custom --custom-filaments my_ladder.csv`. The GUI offers the same
choices in Step 1. IDs in `last_filament` must match the selected ladder; see the
[rat ID mapping, calibration sources, and custom CSV format](docs/filament_sets.md).
Output also records the selected set, log column, and delta.

---

## Worked example: pre-post experiment

The file `data/mouse_data_pre-post_experiment.xlsx` has **multiple sessions per mouse** (`drug` × `treatment` × `pre`/`post`). Use **panel factors** to choose which sessions each figure shows, and **compare within each figure** for the factor you want to contrast (e.g. `sal` vs `drug`).

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
| **d** (delta) | Legacy: 0.441428571; rat/custom: mean adjacent interval in the selected ladder’s log column |

The log value of each filament is computed from its force as: `Log = log10(10 * force_in_grams * 1000)`.

### Reference file: `VF_Calculator_Up-down.xlsx`

This mouse master ships in the `data/` folder and contains two lookup tables:

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

   ⚠️ **Filaments 4 and 5:** stored `Log` values differ from logs recomputed from the listed forces (see below). The bundled calibration is retained for compatibility.

2. **k-statistic lookup table** — 248 entries mapping supported x/o response patterns (2 to 9 characters) to its corresponding k value. For example: `OX → -0.500`, `OXOOXO → 0.168`, `OOXXOO → 0.000`.

> **Do not edit this file** unless you know what you are doing. The k-statistic table and filament forces must stay as shipped. Stored logs and listed forces disagree for filaments 4 and 5; verify calibration before interpreting these values (see next section).

### Log column choice (`Log` vs `Log_new`)

The original `VF_Calculator_Up-down.xlsx` spreadsheet stores a `Log` column for each filament. For **filament 4** (0.158 g), the stored value **differs from the force-derived log**:

| Source | Filament 4 log value |
|--------|----------------------|
| `Log` column in Excel | **3.22** |
| Computed from force: `log10(10 × 0.158 × 1000)` | **3.199** (`Log_new`) |

Filament 5 also differs substantially: its listed force is 0.178 g (`Log_new` = 3.250), while its stored `Log` is 3.61. Other entries can differ slightly due to rounding. Changing log columns can therefore change thresholds, especially for filament 5. This tool preserves the reference values; confirm laboratory calibration before interpreting discrepancies.

The tool therefore offers two options:

| Option | Description | When to use |
|--------|-------------|-------------|
| **`Log_new`** (default) | Recomputed from each filament’s force using the formula above | Use when the listed forces are the intended calibration |
| **`Log`** | Values copied from the original Excel `Log` column | Only if you need **bit-for-bit compatibility** with older analyses or the legacy Excel calculator |

For mice, select in **Step 1** or use `--log-column Log_new` / `--log-column Log`. Rats always use calculated `Log_new`; no rat master is used.

---

## Data format requirements

### Experimental data file

The legacy `mouse` column means animal ID and can contain rat IDs.

An Excel (`.xlsx`) or CSV file with one row per mouse per timepoint per experimental block. Required columns:

| Column | Description | Example |
|--------|-------------|---------|
| `mouse` | Unique animal identifier | `1441` |
| *timepoint column* | Timepoint label (any column name) — numeric (days) or categorical (text) | `-1`, `3`, `14` or `pre`, `post` |
| `xo_series` | String of `x` (withdraw) and `o` (no withdraw) characters | `oxooxo` |
| `last_filament` | Integer ID of the final filament in the selected ladder (1–8 for legacy/rat; custom CSV IDs otherwise) | `5` |

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

**Mouse data only.** There is no bundled rat experimental dataset.

The `data/` folder contains the filament calculator plus **two worked examples**. Each example consists of a **von Frey data file** (measurements) and a **metadata file** (animal information). Load both in Step 1.

| File | Role |
|------|------|
| `VF_Calculator_Up-down.xlsx` | Mouse master reference (not needed for rats/custom) |
| `mouse_data_timeline_experiment.xlsx` | Von Frey measurements — timeline / SNI design |
| `mouse_metadata_timeline_experiment.xlsx` | Animal metadata — timeline experiment |
| `mouse_data_pre-post_experiment.xlsx` | Von Frey measurements — pre-post design |
| `mouse_metadata_pre-post_experiment.xlsx` | Animal metadata — pre-post experiment |

---

### Timeline experiment (longitudinal)

**Biological design:** Mice are tested with von Frey filaments **before and at several timepoints after** induction of chronic pain using the **spared nerve injury (SNI)** model. Timepoints are expressed as **days relative to SNI** (surgery at day 0). The example includes injured (SNI) animals, uninjured controls, and a pharmacological treatment group.

**Files**

| File | Rows | Key columns |
|------|------|-------------|
| `mouse_data_timeline_experiment.xlsx` | 295 | `mouse`, `Timepoint_SNI_day`, `xo_series`, `last_filament` |
| `mouse_metadata_timeline_experiment.xlsx` | 59 | `animal_id`, `sex`, `group_name`, `group_id`, `cohort`, `include_in_analysis`, `comments` |

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
| `mouse_data_pre-post_experiment.xlsx` | 144 | `mouse`, `drug`, `treatment`, `timepoint`, `xo_series`, `last_filament` |
| `mouse_metadata_pre-post_experiment.xlsx` | 24 | `mouse`, `sex`, `condition`, `group`, `accept` |

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
| `--filament-set` | `legacy`, `rat`, or `custom` | `legacy` |
| `--custom-filaments` | Calibrated CSV ladder; required only for `custom` | — |
| `--boundary-policy` | `flag`, `endpoints`, or `exclude`; flags and policy are exported | `flag` |
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
│   ├── VF_Calculator_Up-down.xlsx       # Mouse master only
│   ├── filaments_rat.csv               # Rat nominal target-force ladder
│   ├── dixon_k.csv                     # Species-independent response coefficients
│   ├── mouse_data_timeline_experiment.xlsx    # Example: von Frey (timeline / SNI)
│   ├── mouse_metadata_timeline_experiment.xlsx
│   ├── mouse_data_pre-post_experiment.xlsx    # Example: von Frey (pre-post)
│   └── mouse_metadata_pre-post_experiment.xlsx
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

> Sandoval Ortega, R. A. (2026). Von Frey Up-Down Analysis Tool (Version 1.0.0) [Computer software]. *Zenodo*. https://doi.org/10.5281/zenodo.20762768

Source code: https://github.com/raqueladaia/vf_updown_analysis

Machine-readable citation metadata is in [`CITATION.cff`](CITATION.cff).

### Methodological references

The following sources explain the up-down method, filament calibration, log
spacing, and boundary conventions. See the [annotated reference guide and FAQ](docs/references.md)
for how each source relates to this tool and which methods are implemented.

- Dixon, W. J. (1980). Efficient analysis of experimental observations. *Annual Review of Pharmacology and Toxicology*, 20, 441–462. [DOI / publisher](https://doi.org/10.1146/annurev.pa.20.040180.002301).

- Chaplan, S. R., Bach, F. W., Pogrel, J. W., Chung, J. M., & Yaksh, T. L. (1994). Quantitative assessment of tactile allodynia in the rat paw. *Journal of Neuroscience Methods*, 53(1), 55–63. [DOI / publisher](https://doi.org/10.1016/0165-0270(94)90144-9) · [PubMed](https://pubmed.ncbi.nlm.nih.gov/7990513/).

- Bradman, M. J., Ferrini, F., Salio, C., & Merighi, A. (2015). Practical mechanical threshold estimation in rodents using von Frey hairs/Semmes–Weinstein monofilaments: Towards a rational method. *Journal of Neuroscience Methods*, 255, 92–103. [DOI / publisher](https://doi.org/10.1016/j.jneumeth.2015.08.010) · [Full-text author manuscript](https://iris.unito.it/retrieve/e27ce427-6b39-2581-e053-d805fe0acbaa/Bradman%20JNM%20Postprint%2C%202015.pdf).

- Christensen, S. L., et al. (2020). Von Frey testing revisited: Provision of an online algorithm for improved accuracy of 50% thresholds. *European Journal of Pain*, 24, 783–790. [DOI / publisher](https://doi.org/10.1002/ejp.1528) · [Full-text author manuscript](https://backend.orbit.dtu.dk/ws/files/213362370/Pesei_Christensen_et_al_2019_European_Journal_of_Pain.pdf).

- Gonzalez-Cano, R., Boivin, B., Bullock, D., Cornelissen, L., Andrews, N., & Costigan, M. (2018). Up–Down Reader: An Open Source Program for Efficiently Processing 50% von Frey Thresholds. *Frontiers in Pharmacology*, 9, 433. [DOI / open-access full text](https://doi.org/10.3389/fphar.2018.00433).

- Marvizon, J. C., Walwyn, W., Minasyan, A., Chen, W., & Taylor, B. K. (2015). Latent sensitization: A model for stress-sensitive chronic pain. *Current Protocols in Neuroscience*, 71, 9.50.1–9.50.14. [DOI / publisher](https://doi.org/10.1002/0471142301.ns0950s71) · [Open-access full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC4532319/).

- Ding, X., et al. (2018). BDNF contributes to the neonatal incision-induced facilitation of spinal long-term potentiation and the exacerbation of incisional pain in adult rats. *Neuropharmacology*, 137, 114–132. [DOI / publisher](https://doi.org/10.1016/j.neuropharm.2018.04.032) · [Institution-hosted full text](https://nri.bjmu.edu.cn/docs/2020-08/4bb5d5f639024eb8abe3147429f2ee39.pdf).

- NIH/NINDS Preclinical Screening Platform for Pain. *Rat hind paw mechanical allodynia behavior (von Frey filaments) method*. [Full protocol](https://pspp.ninds.nih.gov/TestDescription/TestPWT).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
