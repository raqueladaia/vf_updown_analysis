# Mouse, rat, and custom filament calculations

All bundled experimental Excel files are **mouse examples**, named `mouse_*`.
`VF_Calculator_Up-down.xlsx` is the **mouse master**, not a rat master.
Do not reinterpret mouse example IDs using the rat preset. See [data guide](../data/README.md).

## Choose a calculation

| Choice | Filament input | Logarithm | Delta | Excel master? |
| --- | --- | --- | --- | --- |
| Mouse `Log_new` (default) | Master's force column | `log10(force_g * 10000)`, rounded to 3 decimals | Historical 0.441428571 | Mouse workbook |
| Mouse `Log` | Master | Stored `Log` values | Historical 0.441428571 | Mouse workbook |
| Rat | Nominal target forces below | Calculated at full precision | Mean adjacent calculated log interval | None |
| Custom | Ordered CSV | Calculated `Log_new`; optional reference `Log` | Mean adjacent selected log interval | None |

All modes calculate `threshold_50 = 10**(Xf + k * delta) / 10000`.
Mouse `Log` uses the master's logarithms, not precomputed animal thresholds.
`Log_new` calculates logs but does not recalibrate the physical filaments.

## Rat preset: target forces, not reverse-calculated handle forces

The [NIH/NINDS protocol](https://pspp.ninds.nih.gov/TestDescription/TestPWT)
specifies these handles. Nominal forces are also listed in the
[published rat protocol](https://pmc.ncbi.nlm.nih.gov/articles/PMC4532319/).

| `last_filament` ID | Handle code (identification only) | Target force (g) |
| --- | --- | --- |
| 1 | 3.61 | 0.4 |
| 2 | 3.84 | 0.6 |
| 3 | 4.08 | 1 |
| 4 | 4.31 | 2 |
| 5 | 4.56 | 4 |
| 6 | 4.74 | 6 |
| 7 | 4.93 | 8 |
| 8 | 5.18 | 15 |

`filaments_rat.csv` contains nominal labels, **not measurements of your kit**.
Use a custom CSV for laboratory calibration or a different tested subset.
Rat `Log_new` is calculated from force; the master-log option is disabled.
Delta is `log10(15 / 0.4) / 7 = 0.224861610...`.

These IDs are positions in the eight-filament ladder, not positions in a
20-piece kit, handle codes, or gram values. Rat ID 4 is 2 g; handle 4.08 / 1 g
is rat ID 3. Remap IDs or preserve your recorded IDs in a custom CSV.

### Why do handle codes and calculated logs differ?

The historical Chaplan convention uses printed handle numbers. Code 4.08
mathematically implies `10**4.08 / 10000 = 1.2023 g`, although its target label
is 1 g. Calculating from 1 g gives `Xf = 4.000`. Christensen et al. favor target
forces over handle codes and recommend individual calibration. The app's rat
mode uses target forces. See [papers and FAQ](references.md).

## Species-independent k table

`dixon_k.csv` contains the 248 pattern coefficients transcribed unchanged from
the workbook's `values_analysis` A:B table at repository commit
`e8727f0fd35bd954a169193b2b6f49eab811f6cc`. These coefficients describe response
patterns, not species or calibration. Rat/custom analysis reads this standalone
table, requiring **no Excel master**. Tests compare every coefficient with the
original. This is a traceable transcription of the repository table, not an
independent reconstruction of Dixon's original statistical tables.

## GUI and CLI

Select the species in Step 1. Changing a ladder, log option, boundary policy,
or input file invalidates thresholds, plots, and statistics until recomputation.
Mouse plots default to **10 g maximum**. Selecting rat defaults to **20 g**,
adjustable in Step 3. This is a display limit, never an experimental cutoff.
Plots warn if values exceed a fixed log-axis maximum.

```bash
python run.py --compute --data my_rat_data.csv --filament-set rat --output results/
python run.py --compute --data my_data.csv --filament-set custom \
  --custom-filaments my_calibrated_ladder.csv --output results/
```

Exports include the set, log column, delta, boundary policy, status, and boundary
limit for every row. A separate `*_filaments.csv` preserves the ladder used.

## Custom CSV and spacing

Include every step in the experimental ladder, even steps not reached in these
data. Forces must increase in row order. IDs must be unique positive integers;
they need not be consecutive and there is no eight-row limit.

```csv
Filament_number,Force (g)
10,1
20,2
30,4
40,8
```

This is a synthetic format example, not a recommended testing range. Optional
`Log` values represent an explicit reference convention. Without them, both
columns equal `log10(force_g * 10000)`. Invalid calibration entries are rejected.

This is the **mean-spacing Dixon approximation**, not Christensen's exact-
likelihood method. GUI and CLI warn if any log step differs from the mean by
more than 50%, the tolerance discussed in that paper. Passing this diagnostic
does not establish accuracy. Strongly uneven ladders require methodological review.

## Mouse compatibility and limitations

Mouse calculations preserve the force table, k table, rounding, and fixed delta.
Mouse ID 4 lists 0.158 g with stored log 3.22 (calculated 3.199); ID 5 lists
0.178 g with stored log 3.61 (calculated 3.250). These mismatches are preserved
and disclosed; verify lab calibration before changing historical analyses.

Starting filaments and stopping rules are not inferred or fully validated.
Unsupported patterns remain flagged. See [boundary handling](boundary_handling.md).
