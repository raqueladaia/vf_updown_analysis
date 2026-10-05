# Boundary observations and analysis policy

All withdrawals (`X`) ending at the lowest tested filament indicate the lower
boundary; all non-withdrawals (`O`) ending at the highest indicate the upper
boundary. These are operationally censored observations, not exact 50% estimates.
Retain the animal, raw responses, final ID, and direction flag.

## Select a predefined policy in Step 1

| Policy | Boundary `threshold_50` | Plots/statistics |
| --- | --- | --- |
| `flag` (default) | Missing; limit/direction stored separately | Blocked for affected data pending policy selection |
| `endpoints` | Lowest/highest tested force under the selected log convention | Included as numerical substitutes with annotations |
| `exclude` | Missing, with explicit exclusion policy | Excluded numerically; counts remain visible |

CLI supports `--boundary-policy flag`, `endpoints`, or `exclude` and exports data
only. Choose endpoint substitution only when it matches the predefined protocol.
Exclusion can bias results by removing the most/least sensitive animals.
The existing t-tests, ANOVA, and mixed models treat substitutes as ordinary
numbers; they are **not censoring-aware models**. Substantial censoring warrants
a suitable censored-data analysis or a documented sensitivity analysis.

For the nominal rat preset, endpoint substitution uses **0.4 g and 15 g**.
These are tested limits, not assertions of true thresholds. Published protocols
use differing assigned floors: Ding et al. (2018) use 0.25 g; Marvizon et al.
(2015) describe 0.5 g for rats, both with a 15 g ceiling. These are not universal
interchangeable defaults. If your protocol specifies another substitution,
retain the flagged export and apply/document it externally. See [papers](references.md).

## Exported status

| `vf_status` | Meaning |
| --- | --- |
| `estimated` | Supported mixed-response pattern, in-range estimate |
| `below_range` / `above_range` | Uniform run ended at its directional endpoint |
| `incomplete_no_reversal` | Uniform run stopped before that endpoint |
| `invalid_boundary_history` | Uniform run exceeds ladder length, inconsistent with adjacent steps without repetition |
| `invalid_series` / `unknown_filament` / `unsupported_pattern` | Input needs review; no numerical estimate |
| `estimate_below_range` / `estimate_above_range` | Mixed-response estimate outside the ladder, retained without clamping |

`vf_boundary_limit_g` preserves the tested limit; `vf_boundary_policy` records the
selected treatment. All input rows remain in exports. Counts appear in GUI
plots/statistical reports, CLI output, and GUI export notes.

Classification uses only the response string and final ID. It cannot establish
compliance with starting-filament or stopping rules. An isolated endpoint
response is not a validated full up-down experiment; consult raw records.
An extrapolated mixed-response estimate differs from a uniform endpoint run,
so the software flags both cases without automatically clamping estimates.
