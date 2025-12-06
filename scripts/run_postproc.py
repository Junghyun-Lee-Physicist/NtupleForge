#!/usr/bin/env python3
# Minimal NanoAOD PostProcessor runner for: branch slimming + simple cut + Golden JSON
# - supports multiple --input and/or --input-list
# - keeps firstEntry / maxEntries
# - passes branchsel/json/cut straight to PostProcessor
# - no shell script needed (python only)

import argparse
import importlib.util
import os
import subprocess
import sys
from typing import List, Optional


def ensure_cmssw() -> None:
    """Load a CMSSW-like runtime if not already in a CMSSW env."""
    if os.environ.get("CMSSW_BASE"):
        return
    r = subprocess.run(
        "bash -lc 'source /cvmfs/cms.cern.ch/cmsset_default.sh; env'",
        shell=True, text=True, capture_output=True
    )
    if r.returncode != 0:
        raise RuntimeError("CMSSW runtime 설정 실패:\n" + r.stderr)
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v


def must_exist(path: str, label: str) -> str:
    ap = os.path.abspath(path)
    if not os.path.exists(ap):
        raise FileNotFoundError(f"[{label}] 파일을 찾을 수 없습니다: {ap}")
    return ap


def load_modules(py_path: Optional[str]) -> List[object]:
    """Load optional user MODULES (a list of Module instances) from a .py file."""
    if not py_path:
        return []
    ap = must_exist(py_path, "modules")
    spec = importlib.util.spec_from_file_location("user_modules", ap)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    if hasattr(mod, "MODULES"):
        return getattr(mod, "MODULES")
    raise RuntimeError(f"{ap} 안에 MODULES 리스트를 정의하세요.")


def read_input_list(list_path: str) -> List[str]:
    paths: List[str] = []
    with open(list_path) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                paths.append(s)
    return paths


def main() -> None:
    ensure_cmssw()
    from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor

    ap = argparse.ArgumentParser(description="Minimal NanoAODTools PostProcessor runner")
    ap.add_argument("--input", action="append", default=[],
                    help="NanoAOD ROOT 경로 (여러 번 지정 가능)")
    ap.add_argument("--input-list", default=None,
                    help="한 줄당 1파일을 적은 텍스트 파일 경로")
    ap.add_argument("--branchsel", required=True,
                    help="keep/drop 규칙 파일 경로")
    ap.add_argument("--cut", default=None,
                    help='예: "nJet>4 && MET_pt>200"')
    ap.add_argument("--json", default=None,
                    help="Golden JSON 파일 경로(데이터일 때)")
    ap.add_argument("--output", default="skim.root",
                    help="최종 병합 산출물 파일명")
    ap.add_argument("--firstEntry", type=int, default=None,
                    help="(선택) 시작 엔트리 오프셋")
    ap.add_argument("--maxEntries", type=int, default=None,
                    help="(선택) 처리 엔트리 수")
    ap.add_argument("--modules", default=None,
                    help="MODULES 리스트를 가진 .py 경로 (옵션)")
    ap.add_argument("--postfix", default="Skim",
                    help="중간 산출물 접미사 (기본: Skim)")
    args = ap.parse_args()

    # 입력 수집
    inputs: List[str] = list(args.input)
    if args.input_list:
        inputs += read_input_list(args.input_list)
    if not inputs:
        raise RuntimeError("입력 파일이 없습니다: --input 또는 --input-list 를 지정하세요.")

    # 로컬 파일들은 존재 체크
    branchsel_abs = must_exist(args.branchsel, "branchsel")
    json_abs = must_exist(args.json, "json") if args.json else None

    # 모듈은 옵션
    modules_list = load_modules(args.modules) if args.modules else []

    # 안전 기본값
    first = 0 if args.firstEntry is None else int(args.firstEntry)
    maxent = -1 if args.maxEntries is None else int(args.maxEntries)

    # 실행
    pp = PostProcessor(
        outputDir=os.getcwd(),
        inputFiles=inputs,
        cut=args.cut,
        branchsel=branchsel_abs,
        modules=modules_list,
        jsonInput=json_abs,
        haddFileName=args.output,
        firstEntry=first,
        maxEntries=maxent,
        postfix=args.postfix,
        provenance=True,  # 권장: 메타데이터 기록
    )
    pp.run()

    final_out = os.path.join(os.getcwd(), args.output)
    if not os.path.exists(final_out):
        raise RuntimeError(f"출력 파일이 보이지 않습니다: {final_out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] run_postproc.py failed: {e}", file=sys.stderr)
        raise
