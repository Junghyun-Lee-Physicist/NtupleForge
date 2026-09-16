# `script/runlogs/` -- 실행 기록 (runlog.sh 가 남기는 것)

> **목적**: lxplus 에서 돌린 각 단계가 *실제로 실행되었고 어떻게 끝났는지* 를 저장소 안에서 확인할 수 있게 한다.
> 화면 출력을 대화창에 붙이는 것에 의존하지 않는다. **대상 독자**: 명령을 돌리는 사람, 결과를 읽는 AI 세션, 나중에 재현하려는 사람.
> **상태**: 2026-09-16 도입. 규칙은 `../runlog.sh` 헤더가 정본이다.

## 어떻게 쓰나

```bash
/bin/bash script/runlog.sh <step> -- <원래 명령 그대로>
```

`<step>` 은 `[A-Za-z0-9_.-]` 짧은 토큰. 예: `ul16pre_miniaodv2`, `das_scan_2024_had`, `sweep_run3_2016`.

## 무엇이 남나

| 파일 | 내용 |
|---|---|
| `run_<step>_<UTC>.log` | **머리**: step, 시작 UTC, host, cwd, git HEAD 와 수정된 추적 파일 수, 정확한 명령, `CMSSW_BASE`, ROOT/dasgoclient 버전, proxy 잔여 시간. **본문**: 명령의 stdout+stderr(화면에도 그대로 나옴). **꼬리**: 종료 UTC, 소요 초, **EXIT 코드**, 실행 중 `script/`·`branches/` 아래에 생기거나 바뀐 파일과 크기. |
| `LEDGER.tsv` | 실행 한 번에 한 줄: `utc_start step exit wall_s host git_head log outputs`. **이 파일 하나로 "무엇을 언제 돌렸고 성공했나"를 훑는다.** |
| `nocommit/` | 명령에 `crab` 이 들어간 실행의 로그. **gitignore 대상.** CRAB 전사에는 pre-signed S3 서명이 찍힌다(`docs/03_DECISIONS.md` D-2026-08-17-no-logs-in-git). |

## 읽는 법

- 성공 여부는 **꼬리의 `EXIT`** 와 LEDGER 의 `exit` 열. 0 이 아니면 본문 끝부분에 원인이 있다.
- 무엇이 만들어졌는지는 꼬리의 `outputs` 목록. 기대한 파일이 없으면 명령은 돌았어도 일이 안 된 것이다.
- 어느 코드로 돌렸는지는 `git_head`. `modified_tracked_files` 가 0 이 아니면 커밋되지 않은 변경 위에서 돈 것이다.
- 재현하려면 머리의 `cmd` 줄을 그대로 복사한다(`printf %q` 형태라 공백·따옴표가 보존된다).

## 규칙

- 저장소에 **커밋한다**(`nocommit/` 제외). 작다: DAS 조회는 수십~수백 줄, 스윕은 수십 줄.
- 같은 step 을 다시 돌리면 새 UTC 스탬프로 새 파일이 생기고 LEDGER 에 한 줄 더 붙는다. 지우지 않는다.
- validation ledger(사람용 표) 를 만들 때 이 LEDGER.tsv 의 `log` 열을 근거 링크로 쓴다.
