# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.25)

cmake_path(GET CMAKE_CURRENT_LIST_DIR PARENT_PATH _tests_dir)
cmake_path(GET _tests_dir PARENT_PATH _therock_source_dir)
include("${_therock_source_dir}/cmake/therock_amdgpu_targets.cmake")

function(assert_target_list actual_var expected)
  if(NOT "${${actual_var}}" STREQUAL "${expected}")
    message(FATAL_ERROR
      "Unexpected target list '${${actual_var}}'; expected '${expected}'")
  endif()
endfunction()

therock_collapse_amdgpu_targets_to_generic(
  collapsed_targets
  gfx1030 gfx1036 gfx1100 gfx1200 gfx1201 gfx942)
assert_target_list(
  collapsed_targets
  "gfx10-3-generic;gfx1100;gfx12-generic;gfx942")

# Generic inputs and their exact equivalents must deduplicate without changing
# first-seen ordering.
therock_collapse_amdgpu_targets_to_generic(
  collapsed_targets
  gfx10-3-generic gfx1030 gfx12-generic gfx1201)
assert_target_list(
  collapsed_targets
  "gfx10-3-generic;gfx12-generic")

therock_collapse_amdgpu_targets_to_generic(
  collapsed_targets
  gfx900 gfx1101 gfx1250)
assert_target_list(
  collapsed_targets
  "gfx900;gfx1101;gfx1250")
