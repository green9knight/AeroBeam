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
3. Schrenk lift, compare to independent numerical integration / accepted
   aeronautical structures examples.
4. Strut-braced single support, compare to independent beam/frame calculations.
5. Jury-braced lift strut, compare Euler length and 2.5% brace demand to Bruhn. The jury strut is not a spar support.
6. Jury front/rear tube-link coupling, compare to an independent frame/beam
   model with the same tube axial stiffness and link geometry.

### Sections

7. Round tube area/I/weight.
8. Plain rectangular wood spar.
9. Symmetric I-beam.
10. Asymmetric I-beam.
11. Box spar.
12. Aluminum C-spar.

### Torsion

13. D-cell single-cell Bredt.
14. Two-cell Bredt with known hand solution.
15. Geodetic/drag-truss strip demand against ANC-18 examples or an independent
    truss/shear panel model.
16. Rib bay torque/reaction demand against a frame/beam model; rib structural
    sizing remains a separate design task.

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
- `tests/test_section_standards.py`
- `tests/test_stability_torsion_standards.py`
- `tests/test_loads_aero_standards.py`
- `benchmarks/cases/01_uniform_cantilever.aerobeam`
- `benchmarks/cases/02_elliptical_cantilever.aerobeam`
- `benchmarks/expected/01_uniform_cantilever.json`
- `benchmarks/expected/02_elliptical_cantilever.json`

Current coverage:

- root shear, root moment, front spar root moment, and tip deflection for a
  uniform cantilever beam;
- independent Euler-Bernoulli finite-element cross-check for uniform
  cantilever tip deflection;
- independent two-spar spring finite-element scaffold for zero/high coupling
  limiting behavior and `kappa` monotonicity;
- root shear and root moment for an elliptical cantilever beam using
  `M = 4 L b / (3 pi)`;
- round tube area/I/EI;
- plain rectangular section `bh^3/12`;
- symmetric same-material I-beam neutral axis and inertia.
- asymmetric transformed-section I-beam neutral axis and inertia;
- box spar neutral axis, area, and inertia;
- aluminum C-spar neutral axis and inertia including the web-edge idealization;
- pin-ended Euler strut buckling;
- flat skin compression buckling;
- skin effective width using `be = min(b, 1.9*t*sqrt(E/sigma))`;
- remaining cap/stringer compression demand from effective-width skin load;
- web shear buckling;
- cap column buckling;
- single-cell D-cell Bredt-Batho `GJ`.
- two-cell Bredt-Batho equilibrium and equal-twist compatibility residuals.
- geodetic strip force consistency with the equivalent shear thickness relation.
- geodetic axial-strip shear stiffness formula. The reduction factor does not change spar bending.
- dynamic pressure `q = 1/2 rho V^2`;
- lift distributions integrate to requested total lift;
- chord-based lift follows chord ratio;
- distributed wing-weight relief reduces root shear and root moment by the
  expected uniform-load amounts;
- strut axial load trigonometry;
- main strut single-support static reaction;
- jury strut column brace: spar reaction unchanged, Euler length reduced to
  the longer segment, brace demand equal to 2.5% of negative-g compression;
- P-delta scalar amplification formula;
- divergence screening formula arithmetic.

This is a harness seed, not sufficient validation.

The two-spar coupling scaffold validates limiting behavior only. It does not
yet calibrate AeroBeam's scalar `kappa` against quantitative two-spar
elastic-connection outputs for production sizing.

## Phase 5 - UI/report safety language

Add a permanent report section:

```text
Method status:
  Standard: lift integration, section EI, basic bending stress
  Preliminary: buckling warnings, P-delta
  Experimental: coupled rear-spar/geodetic torsion, rib reaction demand, divergence
```

## Exit criteria for production release

- All Phase 3 benchmark tests pass.
- Every experimental output is either validated, removed, or visibly labelled.
- Saved beta files have migration tests.
- PDF report contains method assumptions.
- A qualified aircraft structures engineer has reviewed the methods document.
