# AeroBeam Aerospace Standards Matrix

Status: standards alignment checklist for beta development.

This matrix is not a certification basis. It identifies which AeroBeam methods
are based on accepted aerospace structures practice, which are simplified
screening methods, and which are not yet validated enough to be presented as
design-sizing methods.

## Reference categories

The program should use and cite recognized sources such as:

- **14 CFR / FAR 23.303** - factor of safety, limit and ultimate load concepts.
- **FAA AC 43.13-1B** - acceptable methods, wood material allowables, repair and
  construction guidance for non-transport aircraft.
- **Bruhn, Analysis and Design of Flight Vehicle Structures** - wing beam,
  column, plate buckling, shear web and built-up member methods.
- **NACA / NASA technical notes** - plate buckling, panel buckling, tube
  crippling, airfoil data, and classical wing structures examples.
- **Timoshenko / Gere** - Euler-Bernoulli beam theory, columns, elastic
  stability.
- **Roark / Young** - beam formulas and structural idealizations.
- **Bredt-Batho thin-wall torsion theory** - closed-cell torsion and shear flow.
- **Original AeroBeam spreadsheet** - project-specific benchmark source; useful
  only after its assumptions are documented.

## Required output classification

Every numerical result exposed to users should be tagged internally and in the
report as one of:

- **STANDARD** - established preliminary method, benchmarked.
- **PRELIMINARY** - established method with simplifications, benchmark pending.
- **EXPERIMENTAL** - AeroBeam approximation or unvalidated coupling model.
- **DISPLAY** - visualization or informational value only.

## Matrix

| Output / feature | Method basis | Required reference / benchmark | Current status | Production requirement |
| --- | --- | --- | --- | --- |
| Limit/ultimate load entry | FAR 23.303 load-factor concept | User guide examples for normal/utility/aerobatic categories | PRELIMINARY | Explicitly define whether entered `n` is limit or ultimate. |
| Dynamic pressure | ISA + `q = 1/2 rho V^2` | Atmosphere unit test | STANDARD after test | Add unit test at sea level and altitude. |
| Schrenk lift distribution | Schrenk approximation | Spreadsheet + hand numerical comparison | PRELIMINARY | Benchmark root shear/moment for known planforms. |
| Elliptical lift distribution | Classical lifting assumption | Closed-form root moment for cantilever | PRELIMINARY | Add benchmark test. |
| Uniform lift distribution | Elementary beam loading | Closed-form cantilever shear/moment/deflection | STANDARD after benchmark | Add golden benchmark. |
| Shear/moment integration | Beam equilibrium | Closed-form cases | STANDARD after benchmark | Validate sign and integration accuracy. |
| Cantilever deflection | Euler-Bernoulli beam theory | Closed-form `wL^4/(8EI)` style cases | STANDARD after benchmark | Add constant-EI benchmark. |
| Strut-braced support deflection | Indeterminate beam with point support | Original spreadsheet + independent beam model | PRELIMINARY | Benchmark support reactions and deflection. |
| Load-bearing jury support | Indeterminate beam with two supports | Independent beam/frame model | EXPERIMENTAL | Must be validated or labelled experimental in UI/report. |
| Main strut axial load | Statics/trigonometry | Hand free-body diagram | PRELIMINARY | Add benchmark values for `Fv`, `Fa`, `Ps`. |
| Strut Euler buckling | Euler column, assumed `K=1` | Timoshenko/Gere, Bruhn column examples | PRELIMINARY | Add K-factor input or clearly state pin-ended. |
| Jury-braced Euler length | Column braced at intermediate point | Euler column segment length | PRELIMINARY | Benchmark longest unsupported segment logic. |
| P-delta amplification | Beam-column amplification | Known beam-column example | EXPERIMENTAL/PRELIMINARY | Validate for strut-braced wing segment before production. |
| Round tube section | Annulus area/I | Hand calculation | STANDARD after test | Add section benchmark. |
| Plain rectangular section | `I = bh^3/12` | Hand calculation | STANDARD after test | Add benchmark. |
| Built-up I-beam section | transformed section + parallel axis | Hand calculation for symmetric/asymmetric caps | PRELIMINARY | Add NA/EI benchmark. |
| Box spar section | rectangular element assembly | Hand calculation | PRELIMINARY | Add benchmark. |
| Aluminum C-spar section | rectangular element approximation | Hand calc + local buckling review | PRELIMINARY | Add benchmark and attachment caveat. |
| Aluminum angle cap conversion | equivalent flat-bar area | Bruhn-style idealization or documented assumption | EXPERIMENTAL/PRELIMINARY | Validate stress and buckling idealization. |
| D-cell bending contribution | thin skin transformed elements | Hand section calculation | EXPERIMENTAL/PRELIMINARY | Validate with real airfoil geometry. |
| D-cell torsion | Bredt-Batho single cell | Closed-cell torsion hand example | PRELIMINARY | Add GJ/shear-flow benchmark. |
| Two-cell torsion | Bredt-Batho multi-cell | two-cell hand example | PRELIMINARY | Add `q1/q2/GJ` benchmark. |
| Geodetic equivalent panel | equivalent shear thickness approximation | truss/shear-panel independent model | EXPERIMENTAL | Keep labelled experimental until benchmarked. |
| Rib torsion transfer | ribs as distributed shear beams | frame/beam model | EXPERIMENTAL | Keep labelled experimental until benchmarked. |
| Rear spar coupling factor | stiffness-blend approximation | independent two-spar + torsion model | EXPERIMENTAL | Keep labelled experimental until benchmarked. |
| Aluminum skin buckling | flat plate buckling | NACA/Bruhn example | PRELIMINARY | Define boundary conditions and post-buckling meaning. |
| Web shear buckling | plate buckling coefficient | Bruhn/NACA example | PRELIMINARY | Add benchmark and stiffener boundary statement. |
| Web bending buckling | plate compression buckling | Bruhn/NACA example | PRELIMINARY | Add benchmark. |
| Cap column buckling | Euler column between ribs | Bruhn/Timoshenko example | EXPERIMENTAL/PRELIMINARY | Validate axis and restraint assumptions. |
| Tube wall crippling | simplified cylindrical shell/crippling warning | NASA SP-8007 or handbook example | EXPERIMENTAL/PRELIMINARY | Treat as warning only until validated. |
| Divergence speed | simplified closed-form aeroelastic divergence | aeroelastic text example | EXPERIMENTAL | Keep labelled screening-only. |
| Margin of safety | `allowable/applied - 1` | standard stress margin definition | PRELIMINARY | Clarify allowables and ultimate vs limit load. |
| Combined stress interaction | simplified interaction equation | material-specific failure criterion | EXPERIMENTAL/PRELIMINARY | Validate per material family. |

## Release rule

No output may be marketed or labelled as "validated", "certified",
"airworthiness ready", or "production sizing" until:

1. its matrix row is classified STANDARD or PRELIMINARY with benchmark coverage;
2. assumptions are visible in the PDF report;
3. regression tests protect the benchmark;
4. high-risk experimental outputs are either removed or clearly watermarked.

## Current automated benchmark coverage

The following rows now have initial automated checks. These tests do not
complete validation, but they provide regression protection for standard
formula implementations:

- Uniform cantilever shear, root moment, and tip deflection.
- Elliptical cantilever root shear and root moment.
- Dynamic pressure `q = 1/2 rho V^2`.
- Uniform, elliptical, chord-based, and Schrenk lift distributions integrate
  to requested total lift.
- Chord-based lift follows the chord ratio.
- Round tube area, inertia, and EI.
- Plain rectangular section area, neutral axis, and inertia.
- Symmetric same-material I-beam neutral axis and inertia.
- Asymmetric transformed-section I-beam neutral axis and inertia.
- Box spar neutral axis, area, and inertia.
- Aluminum C-spar neutral axis and inertia for the documented web-edge
  idealization.
- Pin-ended main strut Euler buckling.
- Flat skin compression buckling formula.
- Web shear buckling formula and shear coefficient.
- Cap column Euler formula.
- Single-cell D-cell Bredt-Batho `GJ`.
- Two-cell Bredt-Batho equilibrium and equal-twist compatibility residuals.
- Strut axial load trigonometry.
- P-delta scalar amplification formula.
- Divergence screening formula arithmetic.

The following remain explicitly unvalidated/high risk:

- load-bearing jury support reactions beyond the basic regression checks;
- rear spar coupling factor and rear spar load path in cantilever/single-strut
  configurations;
- rib/geodetic/skin torsion sharing;
- geodetic equivalent shear panel thickness;
- divergence speed estimate;
- post-buckled aluminum skin behavior.
