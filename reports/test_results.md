# 720 nm 4f automated verification

작성일: 2026-11-09

작성 시각: 20:08:35 KST (UTC+09:00)

{'passed': 104, 'failed': 0, 'error': 0, 'skipped': 0}

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
| test_fresnel.FresnelGUITests.test_manual_fresnel_intensity_phase_and_model_selection | passed | 0 |
| test_fresnel.FresnelTests.test_custom_phase_forward_bench_matches_fourier_and_bypasses_filters | passed | 1.77636e-15 |
| test_fresnel.FresnelTests.test_free_space_against_independent_fresnel_quadrature | passed | 4.22728e-15 |
| test_fresnel.FresnelTests.test_output_phase_and_detuning_are_retained | passed | 5.21098e-16 |
| test_fresnel.FresnelTests.test_phase_only_vortex_has_fourier_dark_core_without_asm | passed | 1.53619e-07 |
| test_fresnel.FresnelTests.test_same_n_different_sampling_and_gaussian_fourier_width | passed | 2.30531e-08 |
| test_fresnel.FresnelTests.test_sampling_path_limit_and_cancellation_remain_explicit | passed | 0 |
| test_fresnel.FresnelTests.test_two_fresnel_steps_and_lens_form_fourier_transform | passed | 1.1999e-15 |
| test_fresnel.FresnelTests.test_unequal_4f_image_and_negative_b_transform | passed | 3.07961e-16 |
| test_laser_stop.LaserStopTests.test_missed_laser_does_not_become_an_infinite_wall | passed | 0 |
| test_laser_stop.LaserStopTests.test_other_laser_is_also_opaque | passed | 0 |
| test_laser_stop.LaserStopTests.test_reflected_slm_order_guides_stop_at_laser | passed | 0 |
| test_laser_stop.LaserStopTests.test_return_stops_at_emitting_laser_before_rear_screen | passed | 0 |
| test_laser_stop.LaserStopTests.test_slm_presets_have_no_segment_past_a_hit_laser | passed | 0 |
| test_manual_wave.ManualWaveTests.test_cancel_and_close_are_cooperative | passed | 0 |
| test_manual_wave.ManualWaveTests.test_only_button_starts_one_job_and_worker_keeps_ui_alive | passed | 0 |
| test_manual_wave.ManualWaveTests.test_resize_selection_and_repaint_use_fixed_preview | passed | 0 |
| test_manual_wave.ManualWaveTests.test_sampling_failure_stops_and_does_not_retry_on_redraw | passed | 0 |
| test_manual_wave.ManualWaveTests.test_scene_grid_and_plane_changes_mark_stale_until_click | passed | 0 |
| test_offaxis.OffAxisGUITests.test_incidence_control_order_guides_and_filter_readout | passed | 0 |
| test_offaxis.OffAxisGeometryTests.test_3d_tangential_wavevector_and_evanescent_orders | passed | 6.93889e-18 |
| test_offaxis.OffAxisGeometryTests.test_correct_nonzero_532nm_example | passed | 4.24776e-06 |
| test_offaxis.OffAxisGeometryTests.test_incidence_control_keeps_relay_axis_and_moves_filter | passed | 2.22045e-16 |
| test_offaxis.OffAxisGeometryTests.test_oblique_order_equation_and_small_angle_approximation | passed | 1.42542e-06 |
| test_offaxis.OffAxisGeometryTests.test_preset_arm_clearance_incidence_and_image_conjugacy | passed | 7.99361e-15 |
| test_offaxis.OffAxisGeometryTests.test_tilt_separates_arms_but_zero_order_remains_specular | passed | 2.57572e-14 |
| test_offaxis.OffAxisGeometryTests.test_zero_and_first_order_guides_filter_separately | passed | 0 |
| test_offaxis.OffAxisWaveTests.test_coherent_residual_passivity_and_dead_space_reflection | passed | 5.55112e-17 |
| test_offaxis.OffAxisWaveTests.test_real_zero_and_selected_order_regions | passed | 0.000587003 |
| test_offaxis.OffAxisWaveTests.test_sample_and_detector_follow_filtered_field | passed | 3.02135e-05 |
| test_offaxis.OffAxisWaveTests.test_tilt_alone_does_not_remove_unmodulated_light | passed | 2.35922e-16 |
| test_offaxis.OffAxisWaveTests.test_wrong_hole_selects_zero_instead_of_first | passed | 1.73864e-06 |
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
| test_profile_figure.ProfileDataTests.test_full_resolution_units_orientation_and_snapshot_ownership | passed | 9.09495e-13 |
| test_profile_figure.ProfileDataTests.test_gaussian_screen_flux_and_projection_are_preserved | passed | 0 |
| test_profile_figure.ProfileFigureGUITests.test_independent_windows_zoom_pan_history_and_cursor_without_fft | passed | 1.11022e-16 |
| test_profile_figure.ProfileFigureGUITests.test_log_normalized_colors_phase_and_toolbar_png_save | passed | 0 |
| test_profile_figure.ProfileFigureGUITests.test_open_snapshot_survives_recalculation_and_gaussian_mode | passed | 0 |
| test_review_diagnostics.GSReviewTests.test_gs_phase_improves_reconstruction_and_filter_tradeoff | passed | 0 |
| test_review_diagnostics.ReviewDiagnosticsTests.test_n_and_fov_convergence_are_checked_separately | passed | 1.00344e-08 |
| test_review_diagnostics.ReviewDiagnosticsTests.test_pixel_envelope_predicts_16_pixel_blaze_main_order | passed | 2.498e-14 |
| test_review_diagnostics.ReviewDiagnosticsTests.test_real_pixel_sampling_and_hologram_illumination_are_explicit | passed | 0 |
| test_review_diagnostics.ReviewDiagnosticsTests.test_sample_actual_mean_angle_matches_selected_order_guide | passed | 0.000154083 |
| test_review_diagnostics.ReviewDiagnosticsTests.test_wave_centroid_and_mean_direction_independent_of_reference_ray | passed | 3.28817e-07 |
| test_review_diagnostics.ReviewDiagnosticsTests.test_wave_job_cancellation_preserves_sampling_guards | passed | N/A |
| test_slm.SLMGUITests.test_slm_controls_phase_import_json_and_fourier_profile | passed | 8.95148e-09 |
| test_slm.SLMTests.test_blaze_fourier_spot_position | passed | 1.11022e-16 |
| test_slm.SLMTests.test_calibrated_reflected_phase_applied_once | passed | 1.48239e-14 |
| test_slm.SLMTests.test_digital_lens_against_abcd_waist | passed | 2.10183e-11 |
| test_slm.SLMTests.test_example_scene_and_actual_fourier_propagation | passed | 8.95148e-09 |
| test_slm.SLMTests.test_phase_only_rejects_amplitude_controls_and_accepts_custom_phase | passed | 0 |
| test_slm.SLMTests.test_quantized_blaze_first_order_efficiency | passed | 0.000651356 |
| test_slm.SLMTests.test_rectangular_area_pixel_fill_and_phase_stroke | passed | 0 |
| test_slm.SLMTests.test_reflective_slm_routes_return_and_applies_efficiency | passed | 2.88658e-14 |
| test_slm.SLMTests.test_slm_keeps_cumulative_2500mm_limit | passed | 0 |
| test_slm.SLMTests.test_uniform_phase_and_uniform_reflection_loss | passed | 2.22045e-16 |
| test_slm.SLMTests.test_validation_and_unresolved_hardware_pixels | passed | N/A |
| test_slm.SLMTests.test_vortex_winding_and_dark_fourier_core | passed | 3.04643e-08 |
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
| test_wave_progress.ProgressGUITests.test_compact_layout_and_collapsible_details | passed | 0 |
| test_wave_progress.ProgressGUITests.test_failed_calculation_does_not_retry_or_finish_bar | passed | 0 |
| test_wave_progress.ProgressGUITests.test_real_completion_history_and_no_redraw_computation | passed | 0 |
| test_wave_progress.ProgressGUITests.test_running_heartbeat_global_badge_and_cancel | passed | 0 |
| test_wave_progress.ProgressStateTests.test_elapsed_time_and_historical_eta_are_honest | passed | 0 |
| test_wave_progress.ProgressStateTests.test_engine_callbacks_are_monotonic_and_preserve_fields | passed | 0 |
| test_wave_progress.ProgressStateTests.test_monotonic_stages_and_terminal_outcomes | passed | 0 |
