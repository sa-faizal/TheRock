# TheRock generic-GFX local validation package

This is an unpublished, local-only test package for the TheRock generic-target
experiment. It contains focused test executables, not ROCm runtime libraries.

Run:

    run-generic-gfx-validation --all

Use `--rocm-path PATH` when the matching ROCm 10.1.0 generic-target packages
are installed somewhere other than `/opt/rocm-10.1-generic`.

## Test classification and exit behavior

* CPU-only phase: rocRAND `parse_common_architectures`, plus the rocFFT
  `rtc_cache_arch_candidates_exact_first` and
  `rtc_cache_generic_db_key_fallback` cases. These validate collapse and cache
  selection without launching a kernel.
* GPU phase: the complete rocRAND focused executable (host/device dispatch and
  kernels), the complete rocFFT focused executable (including HIPRTC), and the
  MIOpen CK loader executable. MIOpen's process-wide HIP test listener requires
  a GPU even when a `CPU_*` filter is selected.
* MIOpen's CK implementation plugin is supported only for gfx12 in this build;
  gfx10.3 MIOpen CK-loader tests can legitimately skip. Other rocRAND/rocFFT
  tests should run on gfx1030-1036 and gfx1200-1201.

Exit codes: `0` means all selected groups passed, `1` means a selected test
failed, `2` means setup/usage failure, and `77` means `--gpu-only` was requested
but no supported GPU was detected. With `--all`, the CPU phase still runs and a
missing GPU is reported as a skip rather than a package failure.

The launcher builds `LD_LIBRARY_PATH` from the matching ROCm tree at runtime.
The packaged executables have their build-machine RUNPATH removed.
