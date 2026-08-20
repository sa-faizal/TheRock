# Generic GFX target enablement log

Date started: 2026-08-19

## Scope

Collapse exact `gfx103x` compiler targets to `gfx10-3-generic` and exact
`gfx1200`/`gfx1201` compiler targets to `gfx12-generic` for opted-in TheRock
subprojects. `rocBLAS`/Tensile and `hipBLASLt`/TensileLite remain excluded.

Exact hardware targets remain available for runtime device matching,
distribution metadata, tuning databases, and target-specific data files.

## TheRock infrastructure

Status: implemented and configuration-validated.

### Changes

- Added the `USE_GENERIC_GFX_TARGETS` subproject declaration option.
- Added exact-to-generic compilation target transformation with deduplication.
- Kept project target exclusions ahead of the transformation.
- Exported `THEROCK_AMDGPU_TARGETS_EXACT` and
  `THEROCK_AMDGPU_COMPILE_TARGETS` to opted-in subprojects.
- Removed the obsolete gfx103x CK exclusions now that CK accepts
  `gfx10-3-generic`.
- Opted in the audited non-excluded math, MIOpen, RCCL, and rocSHMEM
  subprojects.

### Validation

- `tests/cmake/test_amdgpu_targets.cmake`: passed with CMake 3.31.6; covers
  family transformation, stable ordering, deduplication, already-generic
  inputs, and unrelated targets.
- Narrow TheRock configuration with `gfx1030;gfx1031;gfx1200;gfx1201`:
  passed for rocRAND and hipRAND.
- Generated toolchains retain
  `THEROCK_AMDGPU_TARGETS_EXACT=gfx1030;gfx1031;gfx1200;gfx1201` while setting
  all compiler target variables to `gfx10-3-generic;gfx12-generic`.

## MIOpen

Status: source-ready; HIP build and hardware validation pending.

### Issue and fix

MIOpen CK plugin generation accepted only exact gfx1200/gfx1201 targets, and
the runtime loader constructed only the exact-device plugin name. Added
`gfx12-generic` plugin generation and an exact-first, generic-second loader
candidate sequence for gfx1200 and gfx1201. Each candidate is independently
opened and checked for required symbols and CK API-version compatibility.

gfx10.3 CK grouped convolution remains unsupported, matching existing exact
MIOpen behavior. gfx1250 remains exact-only. Exact MIOpen database names are
unchanged and continue to receive TheRock's exact target list.

### Files

- `projects/miopen/src/ck_impl/CMakeLists.txt`
- `projects/miopen/src/include/miopen/solver/ck_impl_lib_loader.hpp`
- `projects/miopen/src/solver/ck_impl_lib_loader.cpp`
- `projects/miopen/test/gtest/unit_ck_impl_loader.cpp`

### Validation

- Added CPU tests for gfx1200/gfx1201 fallback, feature-suffixed device names,
  generic self-resolution, and non-collapsed gfx1030/gfx1250 behavior.
- Exact architecture macro audit found no other affected production gates.
- `git diff --check`: passed.
- Remaining: build the plugin and run grouped-convolution solver tests on
  gfx1200 and gfx1201; smoke non-CK MIOpen on gfx10.3; confirm exact databases
  in the installed artifact.

## rocRAND / hipRAND

Status: source-ready; HIP build and hardware validation pending.

### Issue and fix

Host runtime parsing recognized only gfx1030/gfx1201 representatives, while
generic device compilation returned `unknown`. Device dispatch could select an
exact specialization whose trampoline body was compile-time eliminated: a
successful but silent no-op.

Normalize gfx1030-gfx1036 and `gfx10-3-generic` to gfx1030, and normalize
gfx1200/gfx1201 and `gfx12-generic` to gfx1201 on both host and device. Existing
family tuning is reused. No hipRAND wrapper change was necessary.

### Files

- `projects/rocrand/library/src/rng/config_types.hpp`
- `projects/rocrand/test/internal/test_rocrand_config_dispatch.cpp`

### Validation

- Added representative, sibling, generic, and future-target boundary mapping
  tests. Existing host/device matching and generator tests cover the no-op
  regression when built for generic hardware.
- `git diff --check`: passed.
- Remaining: generic HIP builds and dispatch/generation tests on representative
  gfx103x and gfx120x hardware.

## rocFFT / hipFFT

Status: source-ready; HIP build and hardware validation pending.

### Issue and fix

Exact runtime devices opened and queried only exact AOT cache filenames and
architecture keys, while a collapsed build emits family-generic filenames and
keys. Generic AOT generation also skipped tuned exact-family solution kernels.

Added ordered exact-to-generic candidates for only gfx1030-gfx1036 and
gfx1200/gfx1201. Runtime opens both system DB filenames and queries exact then
generic keys within each cache tier. Generic AOT generation includes tuned
solutions from compatible exact members. User-cache priority and exact-row
precedence are retained. No hipFFT wrapper change was necessary.

### Files

- `projects/rocfft/library/src/include/rtc_cache.h`
- `projects/rocfft/library/src/rtc_cache.cpp`
- `projects/rocfft/library/src/rocfft_aot_helper.cpp`
- `projects/rocfft/library/src/tests/rtc_test.cpp`

### Validation

- Added mapping/order/boundary and solution-compatibility tests.
- Added real SQLite generic-row fallback and exact-row precedence tests.
- Runtime device paths strip architecture feature suffixes before lookup.
- `git diff --check`: passed.
- Remaining: generic AOT builds, internal cache tests, loading generic DBs on
  exact devices, and representative accuracy/startup/performance tests.

## rocWMMA

Status: source-ready for gfx12-generic; gfx10.3 remains unsupported/excluded.

### Issue and fix

`__gfx12_generic__` reached the unsupported-architecture assertion, and the
WMMA implementation had no generic architecture identity.

Added `ROCWMMA_ARCH_GFX12_GENERIC` with ID `0x12FF`, gfx12/wave32 behavior,
and participation only in family enablers and implementations shared by both
gfx1200 and gfx1201. gfx1250-only paths remain separate.

### Files

- `projects/rocwmma/CMakeLists.txt`
- `projects/rocwmma/library/include/rocwmma/internal/config.hpp`
- `projects/rocwmma/library/include/rocwmma/internal/constants.hpp`
- `projects/rocwmma/library/include/rocwmma/internal/wmma_impl.hpp`

### Validation

- Host preprocessing confirmed gfx12, wave32, and block-16 configuration.
- Host static assertion confirmed current architecture ID `0x12FF`.
- `git diff --check`: passed.
- Remaining: HIP device compilation and WMMA smoke tests on gfx1200/gfx1201.

## RCCL

Status: source-ready; HIP build and collective validation pending.

### Issue and fix

RCCL's target allowlist omitted both generics, while gfx12-generic missed
wave32, FP8 support, Simple-protocol system acquire, and LL system-scope store
gates.

Added both targets and extended only conditions shared by the exact family
members. Exact runtime device strings and tuning maps remain unchanged.

### Files

- `projects/rccl/CMakeLists.txt`
- `projects/rccl/src/include/nccl_device/hip_compat.h`
- `projects/rccl/src/include/rccl_float8.h`
- `projects/rccl/src/device/prims_simple.h`
- `projects/rccl/src/device/prims_ll.h`

### Validation

- Standalone preprocessing confirmed wave size 32 for both generic targets.
- Exact architecture gate audit found no remaining unpaired affected gate.
- `git diff --check`: passed.
- Remaining: representative gfx103x/gfx120x collectives, especially no-GDR
  acquire, LL FIFO stores, and FP8 reductions.

## rocSHMEM

Status: source-ready for gfx12-generic; gfx10.3 remains unsupported upstream.

### Issue and fix

GFX12 assembly syntax, cache policy, buffer descriptors, and split wait-counter
paths were gated on exact gfx1201.

Added a local `ROCSHMEM_ARCH_GFX12_FAMILY` predicate for gfx1201 and
gfx12-generic and used it only for those shared paths. gfx1250 remains
independently explicit.

### Files

- `projects/rocshmem/CMakeLists.txt`
- `projects/rocshmem/src/assembly.hpp`

### Validation

- Stubbed-header preprocessing selected GFX12 scope-qualified loads and split
  wait-counter instructions for `__gfx12_generic__`.
- Exact architecture gate audit and `git diff --check`: passed.
- Remaining: system-scope coherency, buffer access, SDMA, and wait-counter
  functional tests on gfx1200/gfx1201. Upstream unit tests are already disabled
  for gfx1201, so manual functional coverage is important.

## Projects already ready at audit time

The TheRock opt-in was added for CK, rocPRIM, hipCUB, rocThrust, rocSPARSE,
hipSPARSE, rocSOLVER, hipSOLVER, rocALUTION, hipTensor, libhipcxx, and
hipthreads. These still require build/configuration smoke testing in this
workspace.

## Hardware validation still required

CPU-only generation can validate configuration, compilation, code-object
targets, and static lookup behavior. Final runtime and performance validation
requires representative gfx10.3 and gfx12 devices.

## Build validation update — 2026-08-20

This section supersedes the earlier source-ready status lines. The full local
build used exact input targets `gfx1030;gfx1031;gfx1200;gfx1201`; opted projects
received `gfx10-3-generic;gfx12-generic`, after their normal support exclusions,
while rocBLAS/Tensile and hipBLASLt/TensileLite retained exact targets.

### Per-project results and changes

- **MIOpen:** The core library and
  `libMIOpenCKGroupedConv_gfx12-generic.so` compiled and linked. The build keeps
  exact gfx1030/gfx1031/gfx1200/gfx1201 databases, skips unsupported gfx10.3 CK,
  and creates the gfx12-generic CK plugin. Runtime lookup tries exact first and
  then gfx12-generic for gfx1200/gfx1201, validating symbols and CK API version
  per candidate. Files changed are the four MIOpen files listed above.
- **rocRAND / hipRAND:** Both artifacts built, staged, and populated for both
  generics. The `config_types.hpp` normalization and dispatch tests prevent a
  generic-device build from selecting an exact specialization whose trampoline
  compiles to a silent no-op. No hipRAND wrapper source change was needed.
- **rocFFT / hipFFT:** Both artifacts built and staged. Generated
  `rocfft_kernel_cache_gfx10-3-generic.db` (197,074,944 bytes) and
  `rocfft_kernel_cache_gfx12-generic.db` (207,032,320 bytes). Exact-to-generic
  filename/key fallback and generic AOT solution-family inclusion are in the
  four rocFFT files listed above; no hipFFT wrapper source change was needed.
- **rocWMMA:** The gfx12-generic artifact and supplied HIP samples compiled,
  linked, staged, and populated using generic architecture ID `0x12FF`.
  gfx10.3 remains unsupported and excluded.
- **RCCL:** Both generic device ELFs compiled, linked, resource-aggregated, and
  bundled into the host library; the artifact staged and populated. In addition
  to the five architecture-gate files listed above, changed
  `projects/rccl/tools/rccl-device-compile` and
  `projects/rccl/tools/asm_extract/patch_dispatcher.py`: their old exact-only
  regex parsed either generic spelling as generation 1. Generic-aware parsing
  now returns generation 10 or 12 (including feature suffixes) while preserving
  exact parsing and existing SGPR caps (gfx9 102, gfx10/11/12 106).
- **rocSHMEM:** The gfx12-generic library compiled, device-linked, staged, and
  populated. gfx10.3 remains unsupported upstream.
- **CK:** Completed all 1,442 build steps and linked the device-operation archive
  for both generic targets.
- **rocPRIM / hipCUB / rocThrust:** Configured and populated their header
  artifacts with both generic targets.
- **rocSPARSE / hipSPARSE:** rocSPARSE completed 619 build steps and linked both
  generic device images; hipSPARSE built and staged against it.
- **rocSOLVER / hipSOLVER:** rocSOLVER completed 265 build steps and linked both
  generic device images; hipSOLVER configured, built, linked, and staged.
- **rocALUTION:** Both generic HIP images and the host library compiled, linked,
  staged, and populated.
- **hipTensor:** Built, staged, and populated for gfx12-generic. gfx10.3 remains
  excluded by existing project support.
- **libhipcxx / hipthreads:** Configuration-audited and opted in, but not enabled
  in this artifact-generation build.

### Artifact-generation matrix

| Project group | Compiler targets | Local result |
| --- | --- | --- |
| rocRAND / hipRAND | gfx10-3-generic, gfx12-generic | built, staged, populated |
| rocPRIM / hipCUB / rocThrust | gfx10-3-generic, gfx12-generic | configured and populated |
| CK | gfx10-3-generic, gfx12-generic | full archive build completed |
| rocFFT / hipFFT | gfx10-3-generic, gfx12-generic | both AOT DBs and wrapper artifact built |
| rocSPARSE / hipSPARSE | gfx10-3-generic, gfx12-generic | libraries/wrapper built and staged |
| rocSOLVER / hipSOLVER | gfx10-3-generic, gfx12-generic | libraries/wrapper built and staged |
| rocALUTION | gfx10-3-generic, gfx12-generic | built, staged, populated |
| rocWMMA | gfx12-generic | samples and artifact built |
| hipTensor | gfx12-generic | built, staged, populated |
| MIOpen | gfx10-3-generic, gfx12-generic | core library and gfx12 CK plugin built/staged |
| RCCL | gfx10-3-generic, gfx12-generic | device ELFs bundled; artifact populated |
| rocSHMEM | gfx12-generic | device-linked artifact built/populated |
| rocBLAS / hipBLASLt | exact targets | intentionally retained exact; dependency artifacts built locally |

### Local build-environment findings

- rocFFT AOT generation required `HIP_DEVICE_LIB_PATH`,
  `HIPRTC_COMPILE_OPTIONS_APPEND`, and `AMD_COMGR_SAVE_LLVM_TEMPS=1` on this
  machine. Without the diagnostic LLVM-temporary switch the local COMGR/HIPRTC
  path left OCML symbols unresolved; this is a compiler/runtime integration
  item rather than a rocFFT collapse-source failure.
- MIOpen's build needed a temporary generated-build suppression for an
  old-style-cast warning originating in the host SQLite header. No MIOpen source
  was changed for it.
- Temporary CMake/Ninja/Python tooling, unpacked Ubuntu development headers, and
  a temporary venv were used only under `/tmp`. KPack split artifacts were
  disabled because the host lacked the optional splitter.
- `hipSPARSELt` is exact/excluded. Aggregate BLAS artifact population attempted
  its independent all-architecture build and stopped on missing host Python
  development headers. That did not block hipSPARSE or hipSOLVER themselves,
  which both built and staged.
- Hardware execution remains required for representative gfx103x/gfx120x
  correctness, collective/coherency, accuracy, and performance validation.
