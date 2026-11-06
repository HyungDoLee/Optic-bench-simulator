# 720 nm 4f automated verification

2026-11-06T15:06:31.752059+09:00

{'passed': 40, 'failed': 0, 'error': 0, 'skipped': 0}

Errors are absolute differences in the measurement units. The maximum per test mixes units; see JSON for each measurement and tolerance.
Existing regression assertions retain their original verdict/tolerance. Inequality error means constraint violation. N/A means the test has no scalar numerical comparison (e.g. JSON validation or list comparison).

| Test | Status | Max absolute error |
|---|---|---|
| test_four_f.FourFGUITests.test_screen_click_shows_profile_and_shared_path | passed | 0 |
| test_four_f.FourFTests.test_720nm_and_saved_example | passed | 0 |
| test_four_f.FourFTests.test_abcd_4f_analytic | passed | 0 |
| test_four_f.FourFTests.test_fourier_plane_position_and_waist | passed | 2.77556e-17 |
| test_four_f.FourFTests.test_misplaced_lens_is_detectable | passed | 8.52651e-14 |
| test_four_f.FourFTests.test_reflected_graph_includes_shared_path | passed | 0 |
| test_four_f.FourFTests.test_round_trip_detector | passed | 2.27374e-13 |
| test_four_f.FourFTests.test_round_trip_exceeding_cap_stops_before_detector | passed | 0 |
| test_four_f.FourFTests.test_sample_reflectivity_and_scene_validation | passed | 0 |
| test_four_f.FourFTests.test_sample_waist_and_q | passed | 5.68434e-14 |
| test_four_f.FourFTests.test_strict_cap_and_screen_boundary | passed | 0 |
| test_four_f.FourFTests.test_traced_abcd_matches_q_on_every_segment | passed | 0 |
| test_four_f.FourFTests.test_virtual_probes_preserve_beam | passed | 0 |
| test_optics.OpticsTests.test_branch_inherits_cumulative_length | passed | N/A |
| test_optics.OpticsTests.test_cumulative_2p5m_mirror_cavity | passed | 0 |
| test_optics.OpticsTests.test_default_scene_hits_screen | passed | 1.13687e-13 |
| test_optics.OpticsTests.test_gaussian_free_space | passed | 0 |
| test_optics.OpticsTests.test_legacy_json_accepted | passed | 0 |
| test_optics.OpticsTests.test_lens_abcd | passed | 5.85487e-12 |
| test_optics.OpticsTests.test_lens_chief_ray_off_axis | passed | 0 |
| test_optics.OpticsTests.test_lens_chief_ray_on_axis | passed | 0 |
| test_optics.OpticsTests.test_mirror_90_degree_bend | passed | 2.22045e-16 |
| test_optics.OpticsTests.test_no_screen_outside_aperture | passed | 0 |
| test_optics.OpticsTests.test_reject_bad_scene | passed | N/A |
| test_optics.OpticsTests.test_screen_radius_matches_manual_abcd | passed | 0 |
| test_optics.OpticsTests.test_screen_tilt_projected_beam | passed | 0 |
| test_optics.OpticsTests.test_splitter_branch_powers | passed | 0 |
| test_wave_optics.WaveGUITests.test_splitter_artwork_and_wave_screen | passed | 2.88658e-14 |
| test_wave_optics.WaveTests.test_890nm_orders_na_and_energy_budget | passed | 0 |
| test_wave_optics.WaveTests.test_aperture_power_and_actual_diffraction | passed | 0.041081 |
| test_wave_optics.WaveTests.test_asm_gaussian_against_analytic_and_grid_refinement | passed | 1.00344e-08 |
| test_wave_optics.WaveTests.test_coherent_splitter_unitarity_and_recombination | passed | 4.54747e-13 |
| test_wave_optics.WaveTests.test_complex_sample_phase_and_resolved_grating | passed | 0 |
| test_wave_optics.WaveTests.test_defocus_curvature_and_waist_displacement | passed | 1.59162e-12 |
| test_wave_optics.WaveTests.test_finite_detector_and_responsivity | passed | 0.0031668 |
| test_wave_optics.WaveTests.test_fourier_peak_scale_mask_and_image_inversion | passed | 1.33227e-15 |
| test_wave_optics.WaveTests.test_image_conjugacy_not_just_waist | passed | 0 |
| test_wave_optics.WaveTests.test_phase_sample_changes_fourier_but_not_ideal_image_intensity | passed | 4.31879e-07 |
| test_wave_optics.WaveTests.test_sampling_guards_and_cumulative_cap | passed | 0 |
| test_wave_optics.WaveTests.test_traced_4f_wave_against_independent_theory | passed | 2.01157e-11 |
