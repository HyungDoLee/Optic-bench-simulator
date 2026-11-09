# Local pixel-array / GS / pinhole validation

2026-11-07T13:57:34.431853+09:00

This is an example 512×512, 8 µm pixel-array synthesis benchmark at normal
incidence, not a complete 5° bench ASM run, manufacturer calibration or experiment.
The scalar analytic square-pixel sinc envelope represents only the primary
Fourier zone. Higher lattice orders are not traced or falsely renormalized.

- 2048 / 6 mm gives dx=2.929688 µm.
- 8 µm pixels at 5° need N≥3012 for 4 samples/pixel.
- 512 pixels span 4.096 mm; w=0.5 mm illuminates a 125-pixel 1/e² diameter.
- Relative intensity at that hologram edge: 2.676057e-15.
- With w=2.048 mm, relative edge intensity: 0.1353353.
- GS iterations: 60; final unfiltered discrete NRMSE: 0.1388952.

| Pinhole radius | Desired-field passed fraction | Residual passed fraction | Coherent image NRMSE |
|---|---|---|---|
| 0.2 mm | 0.04840829 | 2.018252e-05 | 1.973308 |
| 0.5 mm | 0.9600469 | 0.0002102128 | 0.1304329 |

The target is two Gaussian Fourier spots. A larger hole passes substantially
more of this target but also more residual light. These are not universal
pinhole settings, hologram quality, or measured LCOS extinction ratios.
The pupil restricting the input Gaussian is an external optical aperture;
SLM amplitude is not programmed. No full-bench 512-pixel image import, GS GUI
editor, polarization response or hardware LUT is implied by this benchmark.

See the JSON for exact inputs, power units and model boundaries. See
test_results.md for independent acceptance checks and full regression status.
