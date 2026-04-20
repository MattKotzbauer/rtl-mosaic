#!/usr/bin/env bash
# Compile + run every IP self-test in mcp/corpus/tests, report pass/fail.
# A test "passes" if it prints "Mismatches: 0 in N samples".

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORPUS_DIR="${SCRIPT_DIR}/corpus"
MODULES_DIR="${CORPUS_DIR}/modules"
TESTS_DIR="${CORPUS_DIR}/tests"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "${BUILD_DIR}"' EXIT

# All IP IDs (5 existing + 15 new)
IPS=(
  sync_fifo
  async_fifo
  mux4
  register_file
  up_counter
  mux2
  mux8
  decoder_3to8
  priority_encoder
  comparator
  ripple_adder
  cla_adder
  subtractor
  barrel_shifter
  shift_register
  dual_port_ram
  single_port_ram
  down_counter
  edge_detector
  sign_extend
)

pass=0
fail=0
declare -a failed=()

for ip in "${IPS[@]}"; do
  src="${MODULES_DIR}/${ip}.sv"
  tb="${TESTS_DIR}/${ip}_test.sv"
  out="${BUILD_DIR}/${ip}.vvp"
  log="${BUILD_DIR}/${ip}.log"

  if [[ ! -f "${src}" ]]; then
    printf '[FAIL] %-20s missing source: %s\n' "${ip}" "${src}"
    fail=$((fail + 1))
    failed+=("${ip} (no source)")
    continue
  fi
  if [[ ! -f "${tb}" ]]; then
    printf '[FAIL] %-20s missing testbench: %s\n' "${ip}" "${tb}"
    fail=$((fail + 1))
    failed+=("${ip} (no testbench)")
    continue
  fi

  if ! iverilog -g2012 -o "${out}" "${src}" "${tb}" >"${log}" 2>&1; then
    printf '[FAIL] %-20s compile error (see %s)\n' "${ip}" "${log}"
    fail=$((fail + 1))
    failed+=("${ip} (compile)")
    continue
  fi

  vvp "${out}" >"${log}" 2>&1
  if grep -qE "Mismatches:[[:space:]]*0[[:space:]]+in[[:space:]]+[0-9]+[[:space:]]+samples" "${log}"; then
    samples=$(grep -oE "Mismatches:[[:space:]]*0[[:space:]]+in[[:space:]]+[0-9]+" "${log}" | tail -1 | grep -oE "[0-9]+[[:space:]]*$" | tr -d ' ')
    printf '[PASS] %-20s 0 mismatches in %s samples\n' "${ip}" "${samples}"
    pass=$((pass + 1))
  else
    last=$(grep -E "Mismatches:" "${log}" | tail -1)
    printf '[FAIL] %-20s %s (full log: %s)\n' "${ip}" "${last:-no Mismatches line}" "${log}"
    fail=$((fail + 1))
    failed+=("${ip}")
  fi
done

total=${#IPS[@]}
echo
echo "============================================="
echo "Summary: ${pass}/${total} pass, ${fail}/${total} fail"
if (( fail > 0 )); then
  echo "Failed IPs:"
  for f in "${failed[@]}"; do echo "  - ${f}"; done
  exit 1
fi
