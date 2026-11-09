"""Reproducible LOCAL pixel-array benchmark; does not run the full bench/SDK."""
import json
from pathlib import Path
import sys
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hologram_validation import illumination_sampling,gs_filter_benchmark


def main():
    generated=datetime.now(timezone(timedelta(hours=9),name='KST'))
    report=dict(generated_at=generated.isoformat(),
        hardware_parameters_are_examples=True,
        narrow_beam=illumination_sampling(.5,.008,512,6,2048,5),
        expanded_beam=illumination_sampling(2.048,.008,512,6,2048,5),
        benchmark=gs_filter_benchmark())
    output=ROOT/'reports'
    (output/'hologram_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    b=report['benchmark'];small,large=b['filters']
    text=f'''# Local pixel-array / GS / pinhole validation

작성일: {generated:%Y-%m-%d}

작성 시각: {generated:%H:%M:%S} KST (UTC+09:00)

This is an example 512×512, 8 µm pixel-array synthesis benchmark at normal
incidence, not a complete 5° bench ASM run, manufacturer calibration or experiment.
The scalar analytic square-pixel sinc envelope represents only the primary
Fourier zone. Higher lattice orders are not traced or falsely renormalized.

- 2048 / 6 mm gives dx={report['narrow_beam']['dx_um']:.7g} µm.
- 8 µm pixels at 5° need N≥{report['narrow_beam']['required_n_four_samples']} for 4 samples/pixel.
- 512 pixels span 4.096 mm; w=0.5 mm illuminates a 125-pixel 1/e² diameter.
- Relative intensity at that hologram edge: {report['narrow_beam']['edge_relative_intensity']:.7g}.
- With w=2.048 mm, relative edge intensity: {report['expanded_beam']['edge_relative_intensity']:.7g}.
- GS iterations: {b['gs_iterations']}; final unfiltered discrete NRMSE: {b['gs_final_nrmse']:.7g}.

| Pinhole radius | Desired-field passed fraction | Residual passed fraction | Coherent image NRMSE |
|---|---|---|---|
| {small['radius_mm']} mm | {small['target_pass_fraction']:.7g} | {small['residual_pass_fraction']:.7g} | {small['coherent_reconstruction_nrmse']:.7g} |
| {large['radius_mm']} mm | {large['target_pass_fraction']:.7g} | {large['residual_pass_fraction']:.7g} | {large['coherent_reconstruction_nrmse']:.7g} |

The target is two Gaussian Fourier spots. A larger hole passes substantially
more of this target but also more residual light. These are not universal
pinhole settings, hologram quality, or measured LCOS extinction ratios.
The pupil restricting the input Gaussian is an external optical aperture;
SLM amplitude is not programmed. No full-bench 512-pixel image import, GS GUI
editor, polarization response or hardware LUT is implied by this benchmark.

See the JSON for exact inputs, power units and model boundaries. See
test_results.md for independent acceptance checks and full regression status.
'''
    (output/'hologram_validation.md').write_text(text,encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
