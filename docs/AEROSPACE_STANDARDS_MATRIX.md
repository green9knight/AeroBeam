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
- **ANC-18, Design of Wood Aircraft Structures** - wood aircraft structural
  design methods, including two-spar wings, drag-truss systems, plywood
  elements, joints, and wood construction details.
- **Bruhn, Analysis and Design of Flight Vehicle Structures** - wing beam,
  column, plate buckling, shear web and built-up member methods.
- **NACA / NASA technical notes** - plate buckling, panel buckling, tube
  crippling, airfoil data, and classical wing structures examples.
- **Timoshenko / Gere** - Euler-Bernoulli beam theory, columns, elastic
  stability.
- **Roark / Young** - beam formulas and structural idealizations.
- **Bredt-Batho thin-wall torsion theory** - closed-cell torsion and shear flow.
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
| Schrenk lift distribution | Schrenk approximation | hand numerical comparison / aeronautical structures text example | PRELIMINARY | Benchmark root shear/moment for known planforms. |
| Elliptical lift distribution | Classical lifting assumption | Closed-form root moment for cantilever | PRELIMINARY | Add benchmark test. |
| Uniform lift distribution | Elementary beam loading | Closed-form cantilever shear/moment/deflection | STANDARD after benchmark | Add golden benchmark. |
| Shear/moment integration | Beam equilibrium | Closed-form cases | STANDARD after benchmark | Validate sign and integration accuracy. |
| Cantilever deflection | Euler-Bernoulli beam theory | Closed-form `wL^4/(8EI)` style cases | STANDARD after benchmark | Add constant-EI benchmark. |
| Strut-braced support deflection | Indeterminate beam with point support | independent Euler-Bernoulli beam model | PRELIMINARY | Expand support reaction/deflection benchmarks. |
| Jury strut | Bruhn column brace on the lift strut. Euler length is the longer pin-ended segment. Brace demand is 2.5% of lift-strut compression. | Bruhn, Analysis and Design of Flight Vehicle Structures, column bracing | PRELIMINARY | Do not apply the jury strut as a spar support reaction. |
| Jury front/rear tube-link coupling | same-tube jury links projected as axial stiffness springs between spars through the strut node | independent frame/beam model | EXPERIMENTAL/PRELIMINARY | Uses `EA/L * sin²(theta)` and springs in series; link loads/Euler/joints still require separate sizing. |
| Main strut axial load | Statics/trigonometry | Hand free-body diagram | PRELIMINARY | Add benchmark values for `Fv`, `Fa`, `Ps`. |
| Strut Euler buckling | Euler column, assumed `K=1` | Timoshenko/Gere, Bruhn column examples | PRELIMINARY | Add K-factor input or clearly state pin-ended. |
| Jury-braced Euler length | Column braced at intermediate point | Euler column segment length | PRELIMINARY | Benchmark longest unsupported segment logic. |
| P-delta amplification | Beam-column factor `1/(1-P/Pe)` on the spar segment that carries strut compression | Timoshenko beam-column | PRELIMINARY | Outboard of the strut is not amplified. |
| Round tube section | Annulus area/I | Hand calculation | STANDARD after test | Add section benchmark. |
| Plain rectangular section | `I = bh^3/12` | Hand calculation | STANDARD after test | Add benchmark. |
| Built-up I-beam section | transformed section + parallel axis | Hand calculation for symmetric/asymmetric caps | PRELIMINARY | Add NA/EI benchmark. |
| Box spar section | rectangular element assembly | Hand calculation | PRELIMINARY | Add benchmark. |
| Aluminum C-spar section | rectangular element approximation | Hand calc + local buckling review | PRELIMINARY | Add benchmark and attachment caveat. |
| Aluminum angle cap conversion | equivalent flat-bar area | Bruhn-style idealization or documented assumption | EXPERIMENTAL/PRELIMINARY | Validate stress and buckling idealization. |
| D-cell bending contribution | thin skin transformed elements | Hand section calculation | EXPERIMENTAL/PRELIMINARY | Validate with real airfoil geometry. |
| D-cell torsion | Bredt-Batho on a nose cut from the thickness curve | Closed-cell torsion hand example | PRELIMINARY | Area is the thickness-curve integral, not a rectangle. |
| Two-cell torsion | Bredt-Batho multi-cell | two-cell hand example | PRELIMINARY | Add `q1/q2/GJ` benchmark. |
| Geodetic/drag-truss strip demand and stiffness | ANC-18 two-spar/drag-truss framework; strip axial stiffness `k_s = 2 A E sin(theta) cos(theta) / s * f_red`; equivalent shear thickness used for demand reporting | ANC-18 hand examples or independent truss/shear-panel model | EXPERIMENTAL/PRELIMINARY | Reports strip force/stress demand and reduced elastic coupling estimate only; bond/joint/attachment sizing and local member stability remain outside AeroBeam. |
| Rib torsion demand | bay torque is the airload torque plus, for cantilever and single-strut, the couple from the load the rib moves between the spars. Plywood and formed aluminum use the shear panel G t h / gap per rib pitch. The formed flange is the sheet thickness and is not added to the shear area. Dow foam with spruce caps is a sandwich beam: core shear and cap bending in series. | Bruhn/Peery shear panel; sandwich face bending plus core shear | DISPLAY/PRELIMINARY | AeroBeam reports demand, web shear, and foam-cap stress. It does not size ribs. Foam G and Fsu are Styrofoam Panel Core 20 ASTM C273 minimums. Glue is not checked. |
| Rear spar response | Cantilever and single-strut: both spars share one bending curve in proportion to EI. Dual strut: both spars share the relieved bending by the entered load share. | Bruhn/Peery ribs stiff in their own plane | PRELIMINARY | Drag-truss strip force remains demand only. |
| Aluminum skin buckling/effective width/cap-stringer demand | flat plate buckling plus von Karman/Winter effective-width screening | Bruhn/Niu/Megson/NACA examples | PRELIMINARY | Reports effective width, effective skin load, and remaining cap/stringer compression demand only; rivet/fastener/stringer/frame sizing remains separate. |
| Web shear buckling | Timoshenko k_s for metal; Seydel orthotropic stiffness for wood and plywood | Bruhn/NACA example | PRELIMINARY | Simply supported edges. Wood is not the metal formula with nu = 0. |
| Web bending buckling | plate compression buckling | Bruhn/NACA example | PRELIMINARY | Add benchmark. |
| Cap column buckling | Euler column between ribs | Bruhn/Timoshenko example | EXPERIMENTAL/PRELIMINARY | Validate axis and restraint assumptions. |
| Tube wall crippling | simplified cylindrical shell/crippling warning | NASA SP-8007 or handbook example | EXPERIMENTAL/PRELIMINARY | Treat as warning only until validated. |
| Local fitting / bearing load demand | free-body reaction loads at root, strut, and jury fittings plus required bearing area from user allowable | fitting design by separate standards/manual methods | DISPLAY | Reports load and required bearing-area demand only; bearing, lugs, bushings, bolts, doublers, and local tube crush sizing are outside AeroBeam. |
| Divergence speed | Uniform unswept wing, `q = (pi/(2L))^2 GJ / (e c^2 Cl_alpha)`. An inboard torsion box uses the same Rayleigh quotient on spanwise GJ and shear center. | Bisplinghoff / Fung torsional divergence | EXPERIMENTAL | Divergence speed screening. Shear center is the thin-wall flow of the closed contour, or the spar axis for an open tube. Screening only, not flutter, and not a certified speed. |
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
- Uniform cantilever tip deflection cross-checked against an independent
  Euler-Bernoulli finite-element solve.
- Elliptical cantilever root shear and root moment.
- Dynamic pressure `q = 1/2 rho V^2`.
- Uniform, elliptical, chord-based, and Schrenk lift distributions integrate
  to requested total lift.
- Chord-based lift follows the chord ratio.
- Distributed wing-weight relief matches uniform downward load effects on root
  shear and root moment.
- Round tube area, inertia, and EI.
- Plain rectangular section area, neutral axis, and inertia.
- Symmetric same-material I-beam neutral axis and inertia.
- Asymmetric transformed-section I-beam neutral axis and inertia.
- Box spar neutral axis, area, and inertia.
- Aluminum C-spar neutral axis and inertia for the documented web-edge
  idealization.
- Pin-ended main strut Euler buckling.
- Flat skin compression buckling formula.
- Skin effective-width screening formula.
- Remaining cap/stringer compression demand from total panel compression minus
  effective skin compression.
- Web shear buckling formula and shear coefficient.
- Cap column Euler formula.
- Single-cell D-cell Bredt-Batho `GJ`.
- Two-cell Bredt-Batho equilibrium and equal-twist compatibility residuals.
- Strut axial load trigonometry.
- Main strut single-support statics.
- Jury strut leaves spar reactions unchanged and sets the brace demand to
  2.5% of negative-g lift-strut compression. Euler length is the longer segment.
- Local fitting/bearing load demand values match root, strut, and jury reaction loads.
- Required bearing-area demand equals load divided by user allowable.
- Independent two-spar spring FE scaffold verifies zero-coupling and
  high-coupling limiting behavior. Production rear spar response now uses an
  elastic spring solve; AeroBeam `kappa` is a diagnostic relative-deflection
  reduction.
- P-delta scalar amplification formula.
- Divergence screening formula arithmetic.

The following remain explicitly unvalidated/high risk:

- jury-strut end fittings and the stiffness required to enforce the brace point;
- rear spar coupling/rear spar response needs quantitative calibration against
  independent two-spar elastic-connection models;
- rib structural sizing is not performed; AeroBeam only reports required rib
  reactions;
- geodetic equivalent shear stiffness and full ANC-18 drag-truss sizing;
- geodetic/skin torsion sharing;
- geodetic equivalent shear panel thickness;
- divergence speed estimate;
- post-buckled aluminum skin behavior.
