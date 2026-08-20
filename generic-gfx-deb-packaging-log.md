# Generic GFX Debian packaging report

Date: 2026-08-20

## Inputs and naming

- Source build: `/tmp/therock-generic-ninja`
- ROCm version: `10.1.0`
- Device targets in payloads: `gfx10-3-generic` and `gfx12-generic`
- Standard package output: `/tmp/therock-generic-debs/runtime`
- Standard native-package install prefix: `/opt/rocm/core-10.1`
- Self-contained validation install prefix: `/opt/rocm-10.1-generic`

The build used two local artifact suffixes, `generic-collapse-validation` and
`generic`. A symlink-only catalog at
`/tmp/therock-generic-debs/runtime-artifacts-standard` presents both groups
under `generic-collapse-validation`. TheRock's package-name normalization then
emits the expected `-generic` suffix. Original artifacts were not modified.

## Standard package command

```shell
/tmp/therock-packaging-venv/bin/python \
  build_tools/packaging/linux/build_package.py \
  --artifacts-dir /tmp/therock-generic-debs/runtime-artifacts-standard \
  --dest-dir /tmp/therock-generic-debs/runtime \
  --target generic-collapse-validation \
  --pkg-type deb \
  --rocm-version 10.1.0 \
  --version-suffix generic1 \
  --runpath-pkg \
  --pkg-names \
    amdrocm-fft amdrocm-fft-devel \
    amdrocm-rocalution amdrocm-rocalution-devel \
    amdrocm-hiptensor amdrocm-hiptensor-devel \
    amdrocm-rand amdrocm-rand-devel \
    amdrocm-ccl-devel amdrocm-profiler-base amdrocm-ck \
    amdrocm-rccl amdrocm-rccl-devel \
    amdrocm-rocshmem amdrocm-rocshmem-devel \
    amdrocm-dnn amdrocm-dnn-devel
```

TheRock produced 34 standard DEBs: versioned payload packages and their
non-versioned dependency packages. The complete generated list is in
`built_packages.txt`. Representative payload sizes are:

| Package | DEB size |
| --- | ---: |
| `amdrocm-dnn10.1-generic` | 509,848,436 bytes |
| `amdrocm-ck10.1-generic` | 155,881,872 bytes |
| `amdrocm-hiptensor10.1-generic` | 55,023,472 bytes |
| `amdrocm-rccl10.1` | 32,679,272 bytes |
| `amdrocm-rand10.1-generic` | 18,930,052 bytes |
| `amdrocm-profiler-base10.1` | 5,287,452 bytes |
| `amdrocm-rocalution10.1-generic` | 4,580,240 bytes |
| `amdrocm-fft10.1-generic` | 2,590,188 bytes |
| `amdrocm-rocshmem10.1` | 2,205,768 bytes |

## Self-contained GPU validation package

The standard package subset does not include the base ROCm/LLVM/HIP packages
needed for a dependency-complete install. A monolithic fallback was therefore
assembled from the populated MIOpen dependency closure and overlaid with all
populated collapsed-project install trees.

- File: `amdrocm-generic-local_10.1.0~genericgfx1_amd64.deb`
- Package: `amdrocm-generic-local`
- Version: `10.1.0~genericgfx1`
- Size: 2,004,148,530 bytes
- SHA-256: `2c6cff2e38785859151254931846fe49e4aa68e7098610dcd423d4b2098a3cd2`
- Installed prefix: `/opt/rocm-10.1-generic`

This package includes:

- `libamdhip64` and `libhsa-runtime64`
- `rocfft_kernel_cache_gfx10-3-generic.db`
- `rocfft_kernel_cache_gfx12-generic.db`
- RCCL device images for both generic targets
- `libMIOpenCKGroupedConv_gfx12-generic.so`
- `librocshmem_device_gfx12-generic.bc`

## Validation

- All 35 top-level DEBs passed `dpkg-deb --info`.
- Every payload archive was fully read with `dpkg-deb --contents`.
- `SHA256SUMS` contains checksums for all 35 DEBs.
- Representative runtime libraries use `$ORIGIN`-relative RUNPATHs.
- `ldd` on `libMIOpen.so.1` with the packaged library directory found no
  unresolved dependencies.
- Packages were inspected only; none were installed on the build machine.

## Residual notes

- Use the monolithic runtime package with the separate GPU validation package
  for transfer to the GPU host. The 34 stock packages are useful for validating
  native packaging structure but are not a complete ROCm repository by
  themselves.
- The stock rocFFT artifact slice was materialized before its generic AOT
  databases were populated, so the small standard `amdrocm-fft10.1-generic`
  package omits those databases. The monolithic package explicitly includes
  both databases.
- Local unit-test artifact slices contained manifests without the focused test
  executables, so empty stock `*-test` DEBs were intentionally not included.
- A first package-label experiment was truncated by TheRock to `-gfx10`; those
  trial packages are quarantined under `superseded-gfx10` and are not part of
  the top-level deliverable.
