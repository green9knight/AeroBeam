# AeroBeam Validation Plan

This plan turns the methods audit into actionable validation work. No new
structural feature should be added until the high-risk items have benchmark
coverage or are clearly disabled/labelled experimental.

## Phase 1 - Freeze and identify outputs

- Freeze physics changes except bug fixes.
- List every scalar and array exported by `WingStressAnalyzer`.
- Mark each as:
  - `standard`,
  - `preliminary`,
  - `experimental`,
  - `display-only`.

## Phase 2 - Golden benchmark files

Create a `benchmarks/` directory:

```text
benchmarks/
  cases/
    01_uniform_cantilever.aerobeam
    02_elliptical_cantilever.aerobeam
    ...
  expected/
    01_uniform_cantilever.json
    02_elliptical_cantilever.json
```

Each expected file should contain only defensible values and tolerances:

```json
{
  "V_root": {"value": 1234.5, "rtol": 0.005},
  "M_root": {"value": 56789.0, "rtol": 0.005},
  "z_tip_front": {"value": 1.23, "rtol": 0.02}
}
```

## Phase 3 - Minimum benchmark set

### Beam and load cases

1. Uniform cantilever, constant EI, closed form.
2. Elliptical lift, constant EI, independent numerical integration.
3. Schrenk lift, compare to original spreadsheet.
4. Strut-braced single support, compare to original spreadsheet.
5. Strut-braced plus jury support, compare to an independent beam model.

### Sections

6. Round tube area/I/weight.
7. Plain rectangular wood spar.
8. Symmetric I-beam.
9. Asymmetric I-beam.
10. Box spar.
11. Aluminum C-spar.

### Torsion

12. D-cell single-cell Bredt.
13. Two-cell Bredt with known hand solution.
14. Geodetic equivalent panel against an independent truss/shear panel model.
15. Rib torsion transfer against a frame/beam model.

### Stability and margins

16. Main strut Euler buckling.
17. Jury-braced Euler buckling length.
18. Web shear buckling handbook example.
19. Cap column buckling handbook example.
20. Skin buckling handbook/NACA example.
21. P-delta amplification known beam-column example.

## Phase 4 - Test automation

Add tests that:

- load every benchmark `.aerobeam`,
- run `WingStressAnalyzer`,
- compare selected outputs to expected tolerances,
- fail loudly if a future code change changes validated behavior.

Initial harness:

- `tests/test_benchmarks.py`
- `benchmarks/cases/01_uniform_cantilever.aerobeam`
- `benchmarks/expected/01_uniform_cantilever.json`

This first case covers only root shear/moment for a uniform cantilever beam.
It is a harness seed, not sufficient validation.

## Phase 5 - UI/report safety language

Add a permanent report section:

```text
Method status:
  Standard: lift integration, section EI, basic bending stress
  Preliminary: buckling warnings, P-delta
  Experimental: coupled rear-spar/geodetic/rib torsion, divergence
```

## Exit criteria for production release

- All Phase 3 benchmark tests pass.
- Every experimental output is either validated, removed, or visibly labelled.
- Saved beta files have migration tests.
- PDF report contains method assumptions.
- A qualified aircraft structures engineer has reviewed the methods document.
