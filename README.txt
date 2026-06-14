AeroBeam v1.2.0  —  Wing Bending & Stress Analysis
====================================================
For Ultralight and Experimental Aircraft
© Phil Ramer  —  All rights reserved

WHAT IT DOES
------------
AeroBeam v1.2 analyses the primary wing structure of a strut-braced or
cantilever fabric/built-up or aluminum-skin aircraft wing. For each spar
it computes shear force, bending moment, deflection, bending stress, and
margin of safety. It also computes distributed torsional load, wing twist
angle, and — for the first time in a homebuilt design tool — checks your
wing for aerodynamic divergence.

Results are shown numerically in the Summary panel and graphically in the
Plots panel. All analysis runs in under a second.

NEW IN v1.2
-----------
A. Bug fixes
   A1. Default strut tube changed to 3" × 0.065" (eliminates scary result on
       first launch with the old 2" default)
   A2. All Reset fields now fully restore — jury strut and strut fields
       no longer retain the previous session's values
   A3. P-delta warning: if spar compression exceeds 50% of Euler load the
       summary flags it explicitly
   A3b.Strut material dropdown (5 choices: 6061-T6 Al, 4130 normalized/
       annealed, 4140, 1020 mild steel) with correct E and Ftu for each
   A4. Summary panel scrollbar added
   A5. Full Python traceback shown in the error dialog

B. Usability
   B1. Save / Load project files (.aerobeam JSON)
       File → Save / Save As / Open. Share designs by email or forum post.

C. Spar cross-section library  (spar_sections.py)
   Seven spar types: Round Tube, Plain Rectangular, I-Beam, Double I-Beam,
   Box Spar, C-Channel, Routed (monolithic).
   Twelve materials with full properties: 4 aluminium alloys, 5 wood species
   (AC 43.13-1B Table 1), 3 plywood grades.
   Neutral axis, composite EI, and asymmetric cap stress are all computed
   correctly using the parallel-axis theorem on each rectangular element.
   Live cross-section properties update as you type.
   Aluminum angle cap library (24 extruded sizes, Aircraft Spruce catalog).

D. Independent front and rear spar analysis
   Each spar has its own section type, material, and geometry.
   Deflection integrated separately with each spar's EI array.
   GUI: separate tabs for Front Spar and Rear Spar.

E. D-cell leading edge skin
   Closed leading-edge skin (birch ply or aluminium) from LE to front spar.
   Bending contribution included in front spar EI.
   Torsional stiffness GJ computed by Bredt-Batho single-cell formula.

F. Wing structure types
   Three choices in the Wing Structure tab:
     fabric_tube     — standard tube ladder (cantilever or strut-braced)
     fabric_buildup  — built-up spars, optional D-cell and geodetic lattice box
     aluminum_skin   — full stressed skin; top and bottom panel buckling checked

   Geodetic lattice box: wood strips woven diagonally between front and rear
   spars, creating a second closed torsion cell. Inputs: strip material/width/
   thickness/angle, rib spacing (from Wing Geometry), strips per bay.
   Strip spacing is derived automatically as rib_spacing ÷ strips_per_bay.
   GJ solved exactly by two-cell Bredt-Batho with differing shear moduli.
   Typical result: 1/8" × 1" Sitka Spruce at 10" rib spacing adds 4.6×
   more torsional stiffness than the D-cell alone.

   Single_strut configuration: front spar strut-braced, rear spar cantilever.
   Structural torsion T_struct = rsf × w(x) × e_rs(x) added to aerodynamic
   torsion. Typically dominates by 10:1 on a Kitfox-style wing.
   Type A (fabric/tube) blocked for single_strut — not appropriate.

G. Airfoil database  (airfoil_database.py)
   44 airfoils offline (no internet required). Selecting an airfoil auto-fills
   Cm_ac, Cl_alpha, x_ac/c, and t/c. You can always override Cm_ac manually.
   Groups: NACA 4- and 5-digit, Clark Y family, USA series, Göttingen,
   Wortmann FX, NASA LS, Eppler, Riblett GA series.

   All 20 Riblett entries have Cm_ac verified against the bigairfoils.com
   computational dataset (6,389 airfoils, CmCl04 column).
   Key finding: Riblett camber-2 series (GA30-x12, GA35A-x12, etc.) have
   Cm_ac ≈ −0.025 to −0.038 versus NACA 4412 Cm_ac = −0.099. That is
   60–75% less torsional load — a large structural benefit for this type.

H. Torsion analysis
   Distributed aerodynamic torque: T_aero(x) = |Cm_ac| × q × c(x)²
   Structural torque (single_strut): T_struct = rsf × w(x) × (rear−front)×c(x)
   Total torque integrated from tip to root to give T_running(x).
   Twist rate dφ/dx = T(x)/GJ(x) integrated to give φ(x) in degrees.
   Shear stress τ in D-cell skin and geodetic strips both checked against
   their respective allowables with colour-coded margin of safety.

I. Divergence speed check  *** new safety feature ***
   AeroBeam v1.2 is the first homebuilt wing analysis tool to include a
   divergence check. Divergence is a static aeroelastic instability where
   an increase in angle of attack creates a twist that further increases
   the angle, runaway — the wing twists to destruction.

   Formula: V_div = √(2·GJ / (ρ·Cl_α·e·c²))
   where e = distance from aerodynamic centre to shear centre.
   Safety factor: SF = V_div / Vd  (design speed)
   Green: SF ≥ 1.5  Yellow: 1.0–1.5  Red: SF < 1.0 (DO NOT FLY)

   This check runs automatically whenever a D-cell or skin provides GJ > 0.
   Open-section spars (fabric/tube without D-cell) have no divergence
   resistance and the check is skipped with a note.

J. Margin of safety
   Metal spars: MS_ult = Ftu/σ − 1  and  MS_yield = Fty/σ − 1
   Wood spars:  MS_bend = Fb×kd/σ − 1  (kd = knockdown factor, default 0.75)
   Combined:    MS_comb = 1/√((σ/Ftu)² + (τ/Fsu)²) − 1  (von Mises)
   Reported at the governing station (maximum |sigma|), not at the root.
   Color: Green ≥ 0.50 / Yellow 0.00–0.50 / Red < 0.00

K. +g / −g comparison
   Both cases run automatically. Solid lines = +g, dashed = −g on all plots.
   Summary shows governing (worst) case for each spar.

L. Distributed wing weight relief
   Checkbox in Loads & Config tab. Subtracts Wing_Weight / b_half [lb/in]
   uniformly along span rather than as a point reduction at ng_lift.

M. Export
   File → Export PDF: 3-page PDF (inputs, plots, results summary).
   File → Export Excel: full spanwise arrays for all cases including torsion.

WOOD KNOCKDOWN FACTOR
---------------------
Default 0.75 per AC 43.13-1B for lumber not individually sorted and
graded. If you are using certified aircraft-grade Sitka Spruce with
documented moisture content and no knots, use 1.0. Values between
0.75 and 1.0 may be appropriate for select lumber with careful inspection.
This is a design decision — consult a DER if in doubt.

DIVERGENCE — WHAT TO DO IF SF < 1.5
-------------------------------------
1. Increase D-cell or skin thickness. GJ scales with the skin thickness.
2. Move the shear centre aft (increase front spar chord percentage).
3. Reduce the aerodynamic centre to shear centre offset (e).
4. Use a lower-Cm_ac airfoil (Riblett camber-2 series, for example).
5. Add a geodetic box — it typically provides 4–6× the GJ of the D-cell alone.

FILES
-----
  spar_sections.py         Material DB, 7 cross-section types, D-cell,
                           geodetic panel, aluminum skin panel
  airfoil_database.py      44-airfoil offline database (verified Cm_ac)
  wing_stress_analyzer.py  Physics engine
  wing_stress_gui.py       Tkinter GUI
  common_tube_spars.py     Tube quick-select database (unchanged from v1.1)
  wing_stress.spec         PyInstaller build spec (unchanged)
  build_portable.bat       Build script for portable .exe (unchanged)
  README.txt               This file

DISCLAIMER
----------
AeroBeam is an engineering tool for preliminary design only.
Results must be verified by a qualified licensed engineer before
any aircraft is built or flown. The author accepts no responsibility
for the use or misuse of this software.

Structural loads are highly dependent on how and where the aircraft
is flown. Analysis at design load factor does not guarantee safety
at all flight conditions.

The divergence check is a simplified closed-form estimate. A full
flutter and aeroelastic analysis requires specialised methods and
is beyond the scope of this tool.

