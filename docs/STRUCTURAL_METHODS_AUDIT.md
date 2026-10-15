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
| Cantilever deflection | `_deflect_cantilever`, `_add_twist_to_deflection` | integrate curvature `M/EI` from the root, then add twist about the shear center. Nose-up twist lowers a point aft of the shear center by phi times that distance. Bending stress stays on the moment. | A/B | Standard Euler-Bernoulli beam plus the rigid-rib kinematic offset used by Peery and Megson. Assumes small deflection and no shear deflection. |
| Strut-braced deflection | `_deflect_strut` | root slope correction to enforce zero deflection at strut station | B | Reasonable for an ideal vertical support point. Needs expanded independent beam benchmarks and clarity that strut axial flexibility is ignored. |
| Main strut reaction | `_support_reactions`, no jury case | root moment relief `R = M_root / strut_bl` | A/B | Standard statics for a single vertical support. Assumes vertical component only and ideal support. |
| Jury strut | `_strut_effective_buckling_length`, `_jury_brace_demand` | Bruhn column brace: pin-ended Euler length is the longer segment; brace demand is 2.5% of lift-strut compression. No spar bending relief. | A/B | Matches Bruhn's lift-strut idealization. Not a second wing support. |
| Jury front/rear tube-link stiffness | `_jury_coupling_stiffness` | same-tube front/rear jury links projected to vertical stiffness and combined as springs in series | C | Reported only. It is not applied to spar bending. The jury remains a lift-strut column brace. |
| Strut axial load | `_strut_forces` | vertical reaction resolved by strut angle | A/B | Standard trigonometry. Assumes all vertical reaction goes through one equivalent strut member. |
| Strut Euler buckling | `_strut_forces`, `_strut_effective_buckling_length` | `Pe = pi^2 E I / L_eff^2`; jury uses longest segment | A/B | Standard Euler column. Boundary-condition factor K is implicitly 1.0. UI/report should state pin-ended assumption. |
| P-delta | `_pdelta` | scalar amplification `1/(1 - P/Pe)` | B/C | Recognized column amplification form, but applied globally to bending array. Needs benchmark for strut-braced wing segment and clear limits. |
| Cross-section EI / NA | `_composite_props`, spar classes | parallel-axis theorem with transformed section. Built-up cap width and thickness are entered at the root and the tip and change linearly outboard of the taper-start station. Web height follows the local chord. Web gauge stays at the entered root thickness. | A/B | Standard for built-up sections. Needs benchmark cases for asymmetric caps, C-spar, box spar, and tube. |
| Round tube properties | `RoundTube` | annulus area and `I = pi/64(OD^4-ID^4)` | A | Standard. |
| Aluminum angle equivalent cap | `AluminumAngle`, GUI conversion | equivalent flat bar area for cap input | B/C | Useful approximation. Needs explicit documentation: valid for bending area approximation, not full local angle buckling/rivet design. |
| D-cell bending contribution | `DCellSkin` / usage | nose geometry from the thickness curve; bending still uses the spar section | C | The torsion nose is no longer a rectangle. Spar bending does not add the nose skin as a cap. |
| Single-cell D-cell torsion | `DCellSkin.GJ` | Bredt-Batho on the thickness-curve nose | B | Area and skin length are integrated. The aft bay between spars remains a rectangle. |
| Two-cell D-cell + geodetic / skin torsion | `two_cell_bredt`, `_gj_arrays` | two-cell Bredt-Batho with differing shear moduli | B/C | Method is standard for closed thin-wall cells. Geodetic equivalent skin thickness is an AeroBeam approximation and needs benchmark. |
| Geodetic / drag-truss strip demand | `GeodeticPanel`, `_torsion` | reports shear flow, strip force, and axial stress demand using an ANC-18-style two-spar drag-truss framing plus equivalent shear thickness | C/D | Demand output only. Bond/joint/attachment sizing and local member stability are outside AeroBeam. |
| Rib torsion demand | `_torsion`, `rib_tie_stiffness` | Bay torque is airload torque plus the spar-transfer couple on cantilever and single-strut wings. Plywood and formed aluminum are shear panels. Dow foam with spruce caps is a sandwich beam. | B/C | Demand, web shear, and foam-cap stress only. AeroBeam does not size rib geometry. Glue is not checked. |
| Rear spar load path | `_one_case` | Cantilever and single-strut: ribs lock both spars to one curve and split the external moment by EI. Dual strut: both spars share the relieved bending by the entered load share. | B | The entered load share remains the airload the rib receives. Geodetic strip force stays a demand. |
| Aluminum skin wing box | `SkinPanel`, `WingBox`, `_gj_arrays` | simplified skin panels and two-cell torsion | C | Partial model. Reports effective-width and cap/stringer demand only. Does not size stringers, fasteners, frames, rivets, or post-buckled diagonal tension fields. |
| Skin compression buckling | `skin_compression_buckling` | flat plate buckling | B/C | Standard basis, but boundary conditions and post-buckled load redistribution are simplified. Report treats as warning for semi-monocoque. |
| Web shear/bending buckling | `web_buckling`, `web_bending_buckling` | Timoshenko metal plate; orthotropic long plate for wood and plywood | B | Simply supported. Solid wood uses E_T/E_L = 0.05. Plywood uses E_90/E_0 = 0.50. |
| Cap column buckling | `cap_column_buckling` | Euler column between ribs using strong-axis assumption | C | The strong-axis/web-restraint assumption is not universally valid. Needs review for each cap attachment type. |
| Tube wall crippling | `_compute_buckling` | simplified NASA SP-8007 style expression with imperfection factor | C | Useful warning only. Not a complete local buckling/crippling design method. |
| Local fitting / bearing load demand | `fitting_loads`, `summary_text` | reports root, strut, and jury reaction demands plus required bearing area from a user allowable | Display | No bearing, lug, bushing, bolt, doubler, or local crush sizing is performed. |
| Divergence | `_divergence`, `_shear_center_x` | uniform-wing formula with thin-wall shear center | C | Screening only, not flutter. Open tubes use the spar axis. A nose plus an aft cell uses the outer wall. |
| Margin of safety | `_ms` | stress ratio allowables, simple combined interaction | B/C | Basic stress margin is standard; combined bending/torsion interaction is simplified and not a full failure criterion for all materials. |

## Highest-risk models to freeze or label experimental

These are the places where AeroBeam currently risks sounding more authoritative
than the model supports:

1. **Rear spar path**
   - Cantilever and single-strut spars share one bending curve, split by EI.
   - Dual-strut spars still share the relieved bending by the entered load share.
   - Geodetic strip force is a demand. It does not spring the spars together.
   - Joints, glue, and local strip buckling stay outside the solver.

2. **Jury strut**
   - Treated as a Bruhn column brace on the lift strut.
   - It does not relieve spar shear, moment, or deflection.
   - The reported jury load is 2.5% of the negative-g lift-strut compression.

3. **Geodetic / drag-truss strip demand**
   - ANC-18 is now the governing reference for wood two-spar/drag-truss framing.
   - AeroBeam reports strip force/stress demand only.
   - Bond/joint/attachment sizing and local member stability are outside the
     program scope.
   - The equivalent shear stiffness still needs derivation and benchmark
     examples before it can be used as a validated stiffness model.

4. **Rib torsion demand**
   - Cantilever and single-strut bay torque includes the spar-to-spar couple.
   - Plywood and formed-aluminum stiffness is the shear-panel value. A Dow-foam rib adds spruce-cap bending in series with the core shear. AeroBeam does not size the rib.
   - Rib buckling, attachments, and local details remain separate design tasks.

5. **Aluminum skin post-buckling**
   - Current output estimates effective width and remaining cap/stringer demand.
   - It does not size stringers, frames, fasteners, rivets, or diagonal tension
     field behavior.

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
4. Jury-braced lift strut: Euler length is the longer pin-ended segment, and
   the brace demand is 2.5% of lift-strut compression. The spar reaction is
   unchanged.
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
   - jury strut brace demand,

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
geodetic/rear-spar load-path, rib reaction demand, jury-strut fittings, post-buckling, and
divergence models require formal validation before release claims should be
made.
