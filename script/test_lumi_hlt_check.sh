#!/bin/bash
# test_lumi_hlt_check.sh -- offline test of script/lumi_hlt_check.sh with a fake brilcalc, a fake normtag directory and
# a synthetic golden JSON (nothing here is a real luminosity). Prints PASS/FAIL per check; exit 0 if all pass.
# LUMI_BRILWS_ENV / LUMI_BRILCONDA_BIN point at test files or at nothing, so the real lxplus setup is never used.
#   /bin/bash script/test_lumi_hlt_check.sh
H=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/hidden" "$T/nt" "$T/cwd"
cat > "$T/hidden/brilcalc" <<'EOF'
#!/bin/bash
# fake brilcalc: logs its arguments, prints per-run rows and a Summary block like brilcalc's table style;
# with --hltpath one row per path version (two versions); FAIL_BEGIN=<run> makes that call fail
echo "$*" >> "$FAKE_LOG"
[ "$1" = "--version" ] && { echo "fake 3.7.4"; exit 0; }
b=""; p=""
while [ $# -gt 0 ]; do case "$1" in --begin) b="$2"; shift 2;; --hltpath) p="$2"; shift 2;; *) shift;; esac; done
[ -n "${FAIL_BEGIN:-}" ] && [ "$b" = "$FAIL_BEGIN" ] && { echo "Traceback: fake failure"; exit 1; }
echo "#Data tag : fake"
if [ -n "$p" ]; then
  echo "| 379412:9000 | 01/01/24 | 10 | ${p%\*}X_v1 | 0.5 | 0.4 |"
  echo "#Summary: "
  echo "| hltpath | nfill | nrun | ncms | totdelivered(/fb) | totrecorded(/fb) |"
  echo "| ${p%\*}X_v1 | 1 | 2 | 17 | 1.0 | 0.4 |"
  echo "| ${p%\*}X_v2 | 1 | 2 | 17 | 1.0 | 0.5 |"
  echo "| pattern=[$p] |"
else
  echo "| 379412:9000 | 01/01/24 | 10 | 10 | 0.5 | 99.0 |"
  echo "#Summary: "
  echo "| nfill | nrun | nls | ncms | totdelivered(/fb) | totrecorded(/fb) |"
  echo "| 1 | 2 | 17 | 17 | 115.0 | 109.95 |"
  echo "#(run,ls) in json but not in results: [$(printf '%0.s(1,1),' $(seq 1 300))]"
fi
EOF
chmod +x "$T/hidden/brilcalc"; cp "$T/hidden/brilcalc" "$T/bin/brilcalc"
echo '{}' > "$T/nt/normtag_BRIL.json"; echo '{}' > "$T/nt/normtag_PHYSICS.json"
echo '{"379412": [[1, 10]], "386951": [[1, 5], [7, 8]]}' > "$T/golden.json"
touch "$T/cwd/HLT_PFHTxyz"   # a file the unquoted pattern would glob to
# env files the way a site setup might define brilcalc: a function that touches an unset variable, and an alias
printf 'brilcalc() { : "${SOME_UNSET_VARIABLE}"; "%s/hidden/brilcalc" "$@"; }\n' "$T" > "$T/env_function"
printf 'alias brilcalc=%q\n' "$T/hidden/brilcalc" > "$T/env_alias"
export FAKE_LOG=$T/calls.txt LUMI_NT_DIR=$T/nt LUMI_BRILWS_ENV=$T/none LUMI_BRILCONDA_BIN=$T/none
pass=0; fail=0
ck() { if eval "$2"; then pass=$((pass+1)); echo "PASS $1"; else fail=$((fail+1)); echo "FAIL $1"; fi; }
S="$H/lumi_hlt_check.sh"

out=$(cd "$T/cwd" && PATH=$T/bin:$PATH /bin/bash "$S" --json "$T/golden.json"); rc=$?
ck "normal run: exit 0" '[ $rc -eq 0 ]'
ck "ENV line: version and setup" 'echo "$out" | grep -qx "ENV|brilcalc=fake 3.7.4|setup=PATH"'
ck "JSON facts: runs, first, last, ls" 'echo "$out" | grep -q "^JSON|$T/golden.json|bytes=[0-9]*|md5=[0-9a-f]\{32\}|runs=2|first=379412|last=386951|ls=17$"'
ck "both normtags found in the directory" '[ $(echo "$out" | grep -c "^NORMTAG|$T/nt/normtag_\(BRIL\|PHYSICS\).json|present|") -eq 2 ]'
ck "9 LUMI calls per normtag (whole, C-I, 7 eras)" '[ $(echo "$out" | grep -c "^== LUMI normtag_BRIL ") -eq 9 ] && [ $(echo "$out" | grep -c "^== LUMI normtag_PHYSICS ") -eq 9 ]'
ck "C-I range from the era list" 'echo "$out" | grep -qx "== LUMI normtag_BRIL eras 379412-387121"'
ck "era header and its brilcalc arguments" 'echo "$out" | grep -A1 -x "== LUMI normtag_PHYSICS era D 380253-380947" | grep -q -- "--begin 380253 --end 380947"'
ck "summary block printed (recorded column)" '[ $(echo "$out" | grep -c "| 1 | 2 | 17 | 17 | 115.0 | 109.95 |") -eq 18 ]'
ck "long check-json lines cut at 400 characters" '[ $(echo "$out" | grep "^#(run,ls)" | awk "{print length}" | sort -n | tail -1) -le 400 ]'
ck "3 HLT calls with the first normtag" '[ $(echo "$out" | grep -c "^== HLT normtag_BRIL ") -eq 3 ]'
ck "hltpath pattern passed literally (no glob to the file in cwd)" 'echo "$out" | grep -q "| pattern=\[HLT_PFHT\*\] |" && ! grep -q "HLT_PFHTxyz" $FAKE_LOG'
ck "HLTSUM sums the versions and divides by the era-range total" 'echo "$out" | grep -qx "HLTSUM|normtag_BRIL|HLT_PFHTX|versions=2|recorded=0.9000|of_eras_total=0.0082"'
ck "HLTSUM ignores per-run rows before the Summary" '[ $(echo "$out" | grep -c "^HLTSUM|") -eq 3 ]'
ck "per-run rows not printed" '! echo "$out" | grep -q "379412:9000"'
ck "WORKDIR line" 'echo "$out" | grep -q "^WORKDIR|"'

: > $FAKE_LOG
out=$(PATH=$T/bin:$PATH FAIL_BEGIN=380253 /bin/bash "$S" --json "$T/golden.json"); rc=$?
ck "a failing call: ERR line with its tail, exit 3, the rest still run" '[ $rc -eq 3 ] && [ $(echo "$out" | grep -c "^ERR|LUMI normtag_.* era D 380253-380947: brilcalc exit 1") -eq 2 ] && echo "$out" | grep -q "Traceback: fake failure" && [ $(echo "$out" | grep -c "^== HLT ") -eq 3 ]'

: > $FAKE_LOG
out=$(PATH=$T/bin:$PATH /bin/bash "$S" --json "$T/golden.json" --dry-run); rc=$?
ck "dry run: CMD lines, brilcalc never called, exit 0" '[ $rc -eq 0 ] && [ $(echo "$out" | grep -c "^CMD|brilcalc lumi ") -eq 21 ] && [ ! -s $FAKE_LOG ] && ! echo "$out" | grep -q "^HLTSUM"'

out=$(PATH=$T/bin:$PATH /bin/bash "$S" --json "$T/nothere.json"); rc=$?
ck "missing golden JSON: exit 2" '[ $rc -eq 2 ] && echo "$out" | grep -q "^ERR|golden JSON .* not readable"'

out=$(PATH=$T/bin:$PATH LUMI_NT_DIR=$T/empty /bin/bash "$S" --json "$T/golden.json"); rc=$?
ck "no normtag: exit 2" '[ $rc -eq 2 ] && echo "$out" | grep -q "^ERR|no normtag found"'

out=$(PATH=/usr/bin:/bin HOME=$T /bin/bash "$S" --json "$T/golden.json"); rc=$?
ck "no brilcalc anywhere: exit 2 with the hint" '[ $rc -eq 2 ] && echo "$out" | grep -q "^ERR|brilcalc not found" && echo "$out" | grep -q "LUMI_BRILWS_ENV="'

out=$(PATH=/usr/bin:/bin HOME=$T LUMI_BRILWS_ENV=$T/env_function /bin/bash "$S" --json "$T/golden.json"); rc=$?
ck "env file defining a function that uses an unset variable" '[ $rc -eq 0 ] && echo "$out" | grep -qx "ENV|brilcalc=fake 3.7.4|setup=env:$T/env_function" && [ $(echo "$out" | grep -c "^HLTSUM|") -eq 3 ]'

out=$(cd "$T/cwd" && PATH=/usr/bin:/bin HOME=$T LUMI_BRILWS_ENV=$T/env_alias /bin/bash "$S" --json "$T/golden.json"); rc=$?
ck "env file defining an alias; noglob back on after it" '[ $rc -eq 0 ] && echo "$out" | grep -q "setup=env:$T/env_alias" && echo "$out" | grep -q "| pattern=\[HLT_PFHT\*\] |"'

out=$(PATH=$T/bin:$PATH /bin/bash "$S" --json "$T/golden.json" --normtag "$T/nt/normtag_PHYSICS.json" --eras "X:1:2" --paths "HLT_A_v*"); rc=$?
ck "explicit normtag, eras and paths" '[ $rc -eq 0 ] && [ $(echo "$out" | grep -c "^== LUMI ") -eq 3 ] && echo "$out" | grep -qx "== HLT normtag_PHYSICS HLT_A_v\* eras 1-2" && echo "$out" | grep -q "^HLTSUM|normtag_PHYSICS|HLT_A_vX|versions=2|recorded=0.9000|of_eras_total=0.0082$"'

out=$(PATH=$T/bin:$PATH /bin/bash "$S" --json "$T/golden.json" --normtag "$T/nt/normtag_PHYSICS.json" --hlt-normtag "$T/nt/normtag_BRIL.json" --eras "X:1:2" --paths "HLT_A_v*"); rc=$?
ck "--hlt-normtag outside --normtag: one more era-range call for the total" '[ $rc -eq 0 ] && [ $(echo "$out" | grep -c "^== LUMI ") -eq 4 ] && echo "$out" | grep -q "^HLTSUM|normtag_BRIL|.*|of_eras_total=0.0082$"'
echo "RESULT: $pass PASS, $fail FAIL"
[ $fail -eq 0 ]
