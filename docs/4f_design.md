# 720 nm 4f reflection experiment

> This document describes the original q/ray baseline. The additive scalar-wave
> engine, finite detector, corrected splitter artwork and updated validation are
> documented in [wave_review_response.md](wave_review_response.md).

## Implemented experiment and assumptions

This is a scalar, paraxial, ideal thin-lens model in air. A 720 nm, 10 mW CW
Gaussian source has an input waist radius of 0.5 mm at the virtual object plane.
The sample is a flat, uniform, specular reflector with assumed R=0.8. This is
an engineering starting point, not a measured material reflectance. All quoted
waists are **1/e² intensity radii**, not diameters. No objective is needed for
the chosen 0.25 mm sample waist. The old default scene and its tests are retained.

Open `examples/reflection_4f_720nm.json` or click **Load 720 nm reflection 4f**.
Click Sample or a virtual probe to see its local incident Gaussian profile;
click return-screen to see the detected return beam. The two Fourier-probe
readings are outbound and inbound; select the desired branch/readout.

| Element / plane | X, Y [mm] | Normal angle | Parameter |
|---|---|---|---|
| Laser | 100, 450 | 0° | 720 nm, 10 mW; waistOffset=150 mm |
| Object plane (virtual probe) | 250, 450 | 0° | w=0.5 mm |
| Ideal 50:50 non-polarizing splitter | 350, 450 | −45° | R=0.5 |
| Lens 1 | 450, 450 | 0° | f₁=200 mm, Ø25.4 mm |
| Fourier plane (virtual probe) | 650, 450 | 0° | Shared focal plane |
| Lens 2 | 750, 450 | 0° | f₂=100 mm, Ø25.4 mm |
| Sample | 850, 450 | 0° | R=0.8, ideal flat surface |
| Return detector | 350, 350 | 90° | 100 mm from splitter, sample conjugate |
| Dump monitor | 350, 700 | 90° | Represents initial rejected splitter port |

Illumination travels east to the sample, retraces both lenses, then the splitter
routes the return north. Lens separation is 300 mm. Object-to-sample distance
is 2(f₁+f₂)=600 mm ("4f" is the usual relay name even with unequal focal lengths).
The sample-to-detector return also travels 600 mm: sample→L2 100, L2→L1 300,
L1→splitter 100, splitter→detector 100 mm. The detector is an **image-conjugate
plane**, not an arbitrary distance after the splitter. Source-to-detector path
is 750+600=1350 mm, below the cumulative per-branch 2500 mm cap.

The virtual object plane requires a prepared input wavefront: q at the laser
is −150+i1090.830782496 mm. A real laser is not automatically such a source;
measure its waist/M² and add input mode matching (e.g. a telescope/spatial filter)
before claiming the same sample spot. The unobserved backward splitter output
returns toward the source. The current engine treats laser elements as sources,
not absorbing/isolating surfaces; a real layout needs isolation and beam dumps.
The dump monitor in the model is not a specification for a power-rated beam dump.

## ABCD and Gaussian theory

Use a local forward optical axis for every branch; flat mirrors unfold with
identity ABCD. Angles of component **normals** use screen coordinates (+Y down).

```
P(L) = [[1,L],[0,1]]       L(f) = [[1,0],[-1/f,1]]
M = P(f₂)L(f₂)P(f₁+f₂)L(f₁)P(f₁)
  = [[−f₂/f₁,0],[0,−f₁/f₂]] = [[−0.5,0],[0,−2]]
q_out = (A q_in+B)/(C q_in+D),   q=z+i z_R
z_R = π w₀² / λ,                1/q=1/R − iλ/(πw²)
```

ABCD is tracked along actual simulated branches and displayed in the GUI from
the **laser origin**, not from the virtual object plane. To compare with the
relay matrix, remove the initial 150 mm propagation. The sample matrix from
the laser is [[−0.5,−75 mm],[0,−2]].

| Quantity | Independent theory |
|---|---|
| Input Rayleigh length | 1090.830782496 mm |
| Sample waist | abs(f₂/f₁) × w₀ = 0.250000 mm |
| Sample q | i272.707695624 mm |
| Fourier-plane X | X(L1)+f₁ = X(L2)−f₂ = 650 mm |
| Object→Fourier matrix | [[0,200 mm],[−0.005/mm,0]] |
| Fourier waist | λ f₁/(π w₀) = 0.091673247221 mm |
| Fourier q | i36.6692988884 mm |
| Return detector q / waist | i1090.830782496 mm / 0.500000 mm |
| Sample incident power | 10×0.5 = 5 mW |
| Detector power | 10×0.5×0.8×0.5 = 2 mW |

For an ideal input waist the shared Fourier plane is also a Gaussian waist.
These two meanings are not generally interchangeable: with a different input
curvature a geometrical Fourier plane need not contain the minimum Gaussian
radius. A q-only calculation also does not propagate an arbitrary object's
spatial-frequency spectrum.

## Metric hardware review — provisional catalog candidates

**Official catalog access is blocked by the environment HTTP proxy (CONNECT
403).** The URLs below identify candidates for review, not catalog-verified
specifications, stock, pricing, or a purchasing approval. No catalog pages were
successfully retrieved. Domain additions `www.thorlabs.com` and `thorlabs.com`
were saved to the environment configuration draft. Review/save those settings
and publish to enable a later official-catalog check. Do not order before checking
720 nm coating curves, EFL at 720 nm, clear aperture, damage threshold and thread
compatibility. Simulated focal lengths are exact ideal values; real catalog EFLs
may be specified at another wavelength and have manufacturing tolerances.

| Need / quantity | Candidate or required specification | Relation to this model |
|---|---|---|
| Relay lens 1 ×1 | [AC254-200-B](https://www.thorlabs.com/thorproduct.cfm?partnumber=AC254-200-B), nominal Ø25.4 mm, f=200 mm, B-coating candidate | Thin lens, verify 720 nm transmission and EFL |
| Relay lens 2 ×1 | [AC254-100-B](https://www.thorlabs.com/thorproduct.cfm?partnumber=AC254-100-B), nominal Ø25.4 mm, f=100 mm, B-coating candidate | Thin lens, verify chromatic shift and orientation |
| Input/return separator ×1 | [BS014](https://www.thorlabs.com/thorproduct.cfm?partnumber=BS014), NIR 50:50 cube candidate | Ideal zero-thickness splitter; real glass path, dispersion and s/p imbalance absent |
| Lens mounts ×2 | [LMR1/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=LMR1/M), Ø1-inch mount with metric post attachment candidate | Mechanical mount is outside the current model |
| Posts, holders, bases | [TR50/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=TR50/M), [PH50/M](https://www.thorlabs.com/thorproduct.cfm?partnumber=PH50/M) candidates; choose bases and M6 table screws | Match optical axis height, M4 post/mount and M6 bench hardware |
| Sample XYZ/tip-tilt holder ×1 | Metric stage; travel/flatness/clearance matched to sample | Flat reflector position and normal only; no stage mechanics |
| Detector ×1 | Silicon beam profiler/camera with characterized QE at 720 nm, pixel size, active area ≥~3 mm, ND attenuation; e.g. [BC106N-VIS](https://www.thorlabs.com/thorproduct.cfm?partnumber=BC106N-VIS) candidate | Screen displays ideal continuous intensity, no camera response |
| 720 nm source + input preparation | Existing tunable/diode source, power control and telescope/spatial filter as needed | User-configured ideal Gaussian; laser hardware not specified |
| Isolation / polarization / dumps | 720 nm-compatible isolator, optional HWP/PBS/QWP return separator, suitable dumps for all rejected ports | Not modeled; a PBS/QWP arrangement needs polarization propagation |

Here "metric" refers to mechanical **M4/M6** mounting and mm dimensions. Optical
Ø1 inch=25.4 mm remains a common catalog size. SM1/RMS objective/barrel threads
are optical standards and must not be mistaken for M4/M6 or converted by force.
A nominal 25 mm breadboard grid should be matched to actual M6 table hardware.

For a much smaller sample spot, consider an infinity-corrected objective specified
for 720 nm and its manufacturer's tube lens. Confirm NA, working distance,
entrance-pupil fill, correction wavelength, coverglass, mounting thread, and
the compatible tube-lens focal length. It is unnecessary for the present
250 µm radius. An objective is **not** implemented as a misleading high-NA thin
lens: the current q engine cannot validate high-NA focusing or aberrations.

## Missing physics and proposed next stages

1. **Sample contrast / Fourier analysis:** introduce a complex surface response
   r(x,y,λ), angular-spectrum or Fresnel/FFT propagation, and pupil/filter masks.
   Height h changes reflected phase by Δφ≈4πh cosθ/λ. Roughness needs scattering
   (e.g. a measured BRDF), not a scalar reflectivity. Current profiles cannot
   reveal surface structure or height; they only predict a specular Gaussian.
2. **Polarization and realistic splitters:** Jones matrices for coherent fully
   polarized light; Mueller/Stokes for partial polarization. Include s/p Fresnel
   coefficients, PBS extinction, QWP retardance at 720 nm, and glass propagation.
3. **Finite-aperture/high-NA propagation:** pupil clipping and diffraction,
   vector Debye/Richards–Wolf focusing when paraxial optics fails. Near normal
   incidence with this small beam, the chosen relay is within a paraxial regime.
   Validate numerical sampling and energy conservation against analytical cases.
4. **Measured optics/source/detector:** catalog dispersion/principal planes,
   lens thickness and measured M²; camera pixel integration, QE, saturation,
   dark/read/shot noise, absolute calibration and finite area collection.
5. **Microscopy and real experiments:** objective/tube-lens model, focus scan,
   image-plane versus back-focal-plane detection (a removable Bertrand/relay
   lens for Fourier imaging), alignment and sample-stage error budget. A virtual
   probe cannot physically measure the shared focal plane without disturbing it.
6. **Pulsed operation, if required:** pulse bandwidth, GDD, pulse duration and
   fluence/damage checks. Current power and coating assumptions are CW only.

## Reproducing the verification

```
python -m pip install -r requirements.txt
python app.py
python tools/verify_4f.py --output reports
```

Without DISPLAY the GUI test is explicitly skipped. On Linux with Xvfb and
xauth installed, run the following to include GUI clicking and actual rendering:

```
xvfb-run -a -s "-screen 0 1600x1200x24" python tools/verify_4f.py --output reports --capture-dir reports/screenshots
```

For this cloud review a signed Debian Xvfb package was extracted outside the
checkout and used with system Python/Tk 8.6/Pillow 11.1.0. The X server was
terminated after tests. Screenshots are real GUI captures, not generated images.
`reports/test_results.json` records actual/expected values, absolute/relative
errors and tolerances; `test_results.md` and `unittest.log` retain outcomes.
The unmodified original regression assertions are also observed by the runner;
non-numerical validation/list comparisons have N/A numerical error. No test was
disabled to obtain a passing report.
