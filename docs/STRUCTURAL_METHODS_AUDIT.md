# AeroBeam Structural Methods Audit

Status: preliminary audit, not a validation report.

Date: 2026-06-15

## Purpose

This document records what AeroBeam currently calculates, the structural
idealization behind each calculation, whether that idealization is an
established preliminary method or an AeroBeam-specific approximation, and what
must be benchmarked before the result should be trusted for design decisions.

AeroBeam is not approved for airworthiness decisions. It is a preliminary
design and education tool until every critical load path below has been
benchmarked against hand calculations, aeronautical engineering references, and
at least one independent structural method.

## Confidence categories

- **A - Standard preliminary method**: Common textbook / handbook approach,
  implemented in a direct way. Still requires unit and benchmark tests.
- **B - Standard method with simplifying assumptions**: Based on a recognized
  method, but boundary conditions, load paths, or geometry are simplified.
- **C - AeroBeam approximation**: Engineering approximation introduced to make
  early trade studies possible. Must be clearly labelled in UI/report.
- **D - Experimental / do not rely on yet**: Should be benchmarked, redesigned,
  or disabled before production release.

## Model inventory

| Area | Code location | Current method | Category | Audit finding |
| --- | --- | --- | --- | --- |
| Atmosphere / dynamic pressure | `isa_density`, `dynamic_pressure_psi` | ISA density approximation and `q = 1/2 rho V^2` | A | Suitable for preliminary work. Verify units in regression tests. |
| Lift distribution | `_lift_dist` | uniform, elliptical, chord-based, Schrenk average | A/B | Schrenk and elliptical are established preliminary methods. Needs hand/numerical benchmark for every distribution. |
| Shear and moment integration | `_shear_moment` | numerical tip-to-root integration of distributed load | A | Direct beam shear/moment integration. Needs sign convention documentation and golden cases. |
| Cantilever deflection | `_deflect_cantilever` | integrate curvature `M/EI` from root | A/B | Standard Euler-Bernoulli beam integration. Assumes small deflection and no shear deflection. |
| Strut-braced deflection | `_deflect_strut` | root slope correction to enforce zero deflection at strut station | B | Reasonable for an ideal vertical support point. Needs expanded independent beam benchmarks and clarity that strut axial flexibility is ignored. |
| Main strut reaction | `_support_reactions`, no jury case | root moment relief `R = M_root / strut_bl` | A/B | Standard statics for a single vertical support. Assumes vertical component only and ideal support. |
| Jury strut as load-bearing support | `_support_reactions`, jury case | solves main/jury reactions using root moment equilibrium plus beam compatibility | C/D | Recently added based on design intuition. It is plausible but not yet benchmarked. Needs derivation, free-body diagram, and comparison to frame/beam model before production. |
| Jury front/rear soft coupling | `_elastic_coupled_rear_response` | optional discrete spring between front and rear spars at jury BL | C | Sensitivity tool for jury systems tying both spars. Requires user stiffness and independent frame validation. |
| Strut axial load | `_strut_forces` | vertical reaction resolved by strut angle | A/B | Standard trigonometry. Assumes all vertical reaction goes through one equivalent strut member. |
| Strut Euler buckling | `_strut_forces`, `_strut_effective_buckling_length` | `Pe = pi^2 E I / L_eff^2`; jury uses longest segment | A/B | Standard Euler column. Boundary-condition factor K is implicitly 1.0. UI/report should state pin-ended assumption. |
| P-delta | `_pdelta` | scalar amplification `1/(1 - P/Pe)` | B/C | Recognized column amplification form, but applied globally to bending array. Needs benchmark for strut-braced wing segment and clear limits. |
| Cross-section EI / NA | `_composite_props`, spar classes | parallel-axis theorem with transformed section | A/B | Standard for built-up sections. Needs benchmark cases for asymmetric caps, C-spar, box spar, and tube. |
| Round tube properties | `RoundTube` | annulus area and `I = pi/64(OD^4-ID^4)` | A | Standard. |
| Aluminum angle equivalent cap | `AluminumAngle`, GUI conversion | equivalent flat bar area for cap input | B/C | Useful approximation. Needs explicit documentation: valid for bending area approximation, not full local angle buckling/rivet design. |
| D-cell bending contribution | `DCellSkin` / usage | simplified rectangular enclosed-area and skin elements | C | Geometry is simplified. Needs comparison to actual airfoil/D-cell geometry. |
| Single-cell D-cell torsion | `DCellSkin.GJ` | Bredt-Batho closed thin-wall estimate | B | Bredt-Batho is standard; geometry and material shear modulus assumptions need validation. |
| Two-cell D-cell + geodetic / skin torsion | `two_cell_bredt`, `_gj_arrays` | two-cell Bredt-Batho with differing shear moduli | B/C | Method is standard for closed thin-wall cells. Geodetic equivalent skin thickness is an AeroBeam approximation and needs benchmark. |
| Geodetic / drag-truss strip demand | `GeodeticPanel`, `_torsion` | reports shear flow, strip force, and axial stress demand using an ANC-18-style two-spar drag-truss framing plus equivalent shear thickness | C/D | Demand output only. Full ANC-18 sizing of joints, glue, compression strips, and details is not implemented. |
| Rib torsion demand | `_torsion` | reports required rib bay torque and front/rear attach reactions | C | Demand output only. AeroBeam no longer sizes rib geometry/materials. |
| Rear spar load path for cantilever/single-strut | `_one_case`, `_elastic_coupled_rear_response` | rear spar beam with torsion-couple load elastically connected to front spar by distributed geodetic/skin springs | C | Scalar `kappa` blend removed; still needs quantitative calibration before using for final rear spar sizing. |
| Aluminum skin wing box | `SkinPanel`, `WingBox`, `_gj_arrays` | simplified skin panels and two-cell torsion | C | Partial model. Does not include stringers, fasteners, shear flow/rivet loads, effective width iteration, or post-buckled diagonal tension. |
| Skin compression buckling | `skin_compression_buckling` | flat plate buckling | B/C | Standard basis, but boundary conditions and post-buckled load redistribution are simplified. Report treats as warning for semi-monocoque. |
| Web shear/bending buckling | `web_buckling`, `web_bending_buckling` | plate buckling coefficient estimates | B/C | Standard-style preliminary checks. Needs verification against Bruhn/NACA examples and correct stiffener boundary assumptions. |
| Cap column buckling | `cap_column_buckling` | Euler column between ribs using strong-axis assumption | C | The strong-axis/web-restraint assumption is not universally valid. Needs review for each cap attachment type. |
| Tube wall crippling | `_compute_buckling` | simplified NASA SP-8007 style expression with imperfection factor | C | Useful warning only. Not a complete local buckling/crippling design method. |
| Divergence | `_divergence` | closed-form divergence speed using estimated shear center | C/D | Simplified estimate. Shear center is approximate; no aeroelastic coupling/eigenvalue analysis. Must be labelled screening-only. |
| Margin of safety | `_ms` | stress ratio allowables, simple combined interaction | B/C | Basic stress margin is standard; combined bending/torsion interaction is simplified and not a full failure criterion for all materials. |

## Highest-risk models to freeze or label experimental

These are the places where AeroBeam currently risks sounding more authoritative
than the model supports:

1. **Rear spar coupling through geodetic/skin**
   - Rear response now uses an elastic spring solve instead of a scalar blend.
   - Reported `kappa` is diagnostic relative-deflection reduction, not the
     governing solver.
   - Needs quantitative calibration against 2-spar beam/frame or truss models.

2. **Load-bearing jury strut reactions**
   - The compatibility solve is plausible but new.
   - Needs a clean free-body diagram, sign convention review, and comparison to
     hand frame / finite-element beam models.

3. **Geodetic / drag-truss strip demand**
   - ANC-18 is now the governing reference for wood two-spar/drag-truss framing.
   - AeroBeam reports strip force/stress demand but does not complete ANC-18
     joint, glue, compression-member, or detail checks.
   - The equivalent shear stiffness still needs derivation and benchmark
     examples before it can be used as a validated stiffness model.

4. **Rib torsion demand**
   - AeroBeam reports rib bay torque and attach reaction demand only.
   - Rib sizing, rib buckling, attachments, and local details remain separate
     design tasks outside the current solver.

5. **Aluminum skin post-buckling**
   - Current skin buckling warning does not size post-buckled skin/stringer
     systems.
   - Good as a warning, not as a final design check.

6. **Divergence**
   - Current calculation is a screening estimate only.
   - Shear center and GJ assumptions dominate the result.

## What should be shown in UI/report

Until validation is complete, the report should distinguish:

- **Standard beam results**: lift, shear, moment, basic deflection, simple
  section stress.
- **Preliminary buckling warnings**: web, cap, skin, tube local instability.
- **Experimental coupling/torsion results**: geodetic/rear-spar coupling,
  single-strut torsion transfer, rib demand, divergence estimate.

Suggested report language:

> Coupled rear-spar/geodetic torsion and rib reaction-demand results are preliminary AeroBeam
> approximations. Use them for design comparison only until validated against
> an independent structural model.

## Required benchmark cases before production

Create saved `.aerobeam` files and expected numerical outputs for each:

1. Uniform cantilever beam, constant EI, closed-form shear/moment/deflection.
2. Elliptical cantilever lift case, constant EI, independent numerical check.
3. Strut-braced beam with one ideal support, benchmark against independent
   beam/frame calculations.
4. Strut-braced beam with load-bearing jury support, benchmark against a
   statically indeterminate beam calculation.
5. Round tube spar stress and EI, hand-calculated.
6. Symmetric and asymmetric I-beam EI/NA, hand-calculated.
7. Box spar EI/NA/weight, hand-calculated.
8. D-cell single-cell Bredt torsion, hand-calculated.
9. Two-cell Bredt example with known `q1`, `q2`, and GJ.
10. Geodetic panel equivalent stiffness, independent truss/shear-panel model.
11. Rib bay torque/reaction demand, independent beam/frame model.
12. Aluminum skin panel buckling, textbook/NACA example.
13. Web shear buckling with stiffener spacing, Bruhn/NACA example.
14. Cap column buckling with known boundary assumptions.
15. P-delta amplification for a known column/beam-column case.

## Recommended next code actions

1. Add visible **Experimental** tags in summary/PDF for:
   - rear spar coupling factor,
   - geodetic torsion sharing,
   - rib reaction demand,
   - divergence speed,
   - load-bearing jury support until benchmarked.

2. Add a `benchmarks/` directory:
   - `cases/*.aerobeam`
   - `expected/*.json`
   - tests that compare analyzer output to expected tolerances.

3. Separate solver modules:
   - `loads.py`
   - `sections.py`
   - `beam.py`
   - `struts.py`
   - `torsion.py`
   - `buckling.py`
   - `reports.py`

4. Add an assumptions block to every PDF report.

5. Disable or clearly watermark experimental outputs if beta users treat them
   as design sign-off values.

## Immediate conclusion

AeroBeam is suitable for beta exploration and comparison of concepts. It is not
yet suitable for production structural sizing without the benchmark program
above. The basic beam/section math is the strongest part. The coupled torsion,
geodetic/rear-spar load-path, rib reaction demand, load-bearing jury, post-buckling, and
divergence models require formal validation before release claims should be
made.
