# Data files: mouse examples and references

**All four experimental Excel workbooks are mouse examples.** Their contents
are unchanged; `mouse_` was added to their names for clarity.

| File | Species / purpose |
| --- | --- |
| `mouse_data_timeline_experiment.xlsx` | Mouse longitudinal measurements |
| `mouse_metadata_timeline_experiment.xlsx` | Metadata for those mice |
| `mouse_data_pre-post_experiment.xlsx` | Mouse pre/post measurements |
| `mouse_metadata_pre-post_experiment.xlsx` | Metadata for those mice |
| `VF_Calculator_Up-down.xlsx` | Mouse master/reference calibration and historical k table |
| `filaments_rat.csv` | Rat nominal force reference, **not experimental rat data** |
| `dixon_k.csv` | Species-independent response-pattern coefficients |

Use **Mouse** with the bundled examples. There is no rat experimental example
workbook or rat master workbook. Rat users supply raw responses and final IDs;
logs, delta, and thresholds are calculated in Python.

The legacy input column `mouse` means animal ID and may contain rat IDs. GUI
users can map other column names. CLI uses `mouse`, `xo_series`, `last_filament`.
Older saved sessions/scripts must update example paths to the `mouse_` filenames.

[Calculations](../docs/filament_sets.md) · [Boundaries](../docs/boundary_handling.md) ·
[Papers](../docs/references.md).
