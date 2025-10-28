# CCPP HBD Solver

복합화력(CCPP) 3압력 HRSG Heat Balance Data(HBD) 자동화 엔진

---

## 0. 목적

이 저장소는 복합화력 발전소(CCPP)의 3압력 HRSG(HP/IP/LP) 사이클에 대한 열수지(Heat Balance Data)를 자동으로 계산하고,
정형화된 보고서(Excel, SVG 다이어그램 등)를 생성하는 파이프라인을 제공합니다.

우리가 풀고 싶은 문제:

- 외기 조건, 가스터빈(GT) 성능, HRSG pinch/approach, 복수기 조건 등이 바뀔 때마다 엔지니어가 수동으로 열수지 계산과 표 작성하는 반복 업무를 없앤다.
- 벤더 A vs 벤더 B, 여름 vs 겨울, 복수기 진공 조건 변화 등 다양한 "케이스"를 JSON으로 저장하고 언제든 재현 가능하게 만든다.
- 계약 검토/성능 검증 시 "우리가 사용한 기준 HBD"를 근거 있는 수치로 바로 뽑아낸다.

---

## 1. 시스템 구성

### 1.1 디렉토리 구조 (초기 설계안)

```
ccpp-hbd-solver/
├─ README.md
├─ agent.md
├─ defaults/
│   └─ defaults.json                # 기본 가정치 모음 (pinch, eff 등)
├─ data/
│   ├─ plant_case_summer_35C.json   # 케이스 입력 예시
│   └─ plant_case_winter_5C.json
├─ src/
│   ├─ ambient/
│   │   └─ ambient_correction.py    # 외기조건 보정 로직
│   ├─ gt_block/
│   │   └─ gt_solver.py             # 가스터빈 성능/연료/배기가스 계산
│   ├─ hrsg_block/
│   │   └─ hrsg_solver.py           # 3압력 HRSG 열수지 반복 수렴
│   ├─ st_block/
│   │   └─ st_solver.py             # HP/IP/LP 스팀터빈 팽창 출력 계산
│   ├─ condenser_loop/
│   │   └─ condenser_solver.py      # 복수기/급수 루프 질량·에너지 수지
│   ├─ plant_summary/
│   │   └─ plant_summary.py         # Net MW, 효율, 밸런스 클로저 등 집계
│   ├─ reporter/
│   │   ├─ excel_reporter.py        # Summary/Streams 시트 작성
│   │   └─ diagram_svg.py           # 블록 다이어그램 SVG 생성
│   └─ utils/
│       ├─ steam_props.py           # IAPWS-IF97 기반 물/증기 물성 계산
│       └─ unit_helpers.py          # 단위 변환, 라운딩 등
├─ run_case.py                      # CLI 엔트리포인트
├─ run_gui.py                       # Tkinter GUI 실행 스크립트
└─ output/
    ├─ sample_case.xlsx
    └─ sample_case.svg
```

### 1.2 실행 흐름

1. `run_case.py --case data/plant_case_summer_35C.json --out output/summer_35C`
2. `run_case.py`는 다음 순서로 동작한다:
   - 입력 JSON 로드 → defaults 병합
   - `ambient_correction.py`와 `gt_solver.py`로 실제 GT 운전점 산출
   - `hrsg_solver.py`로 HP/IP/LP 증기유량 수렴 (pinch/approach 반영)
   - `st_solver.py`로 스팀터빈 출력 계산
   - `condenser_solver.py`로 복수기/급수 루프 닫고 mass balance 확인
   - `plant_summary.py`로 Net MW/효율 산정
   - 결과 dict에 메타데이터(케이스명, commit hash, timestamp, 수렴여부) 부착
   - `excel_reporter.py` / `diagram_svg.py` 호출해 보고서 산출
3. 산출물:
   - `output/<case_name>.xlsx` → Summary / Streams 시트
   - `output/<case_name>.svg` → GT→HRSG(HP/IP/LP)→ST→Condenser 블록다이어그램

### 1.3 데스크톱 GUI

CLI와 동일한 파이프라인을 Tkinter 기반 GUI로도 제공한다. GUI는 입력 편집, 실시간 결과 확인, 리포트 내보내기를 한 화면에서 수행할 수 있도록 구성되어 있다.

1. 실행: `python run_gui.py`
2. 주요 기능:
   - **입력 편집 탭**: Ambient, Gas Turbine, HRSG, Steam Turbine, Condenser, Balance of Plant 항목을 탭별 폼으로 편집.
   - **케이스 관리**: JSON 케이스 불러오기/저장, 기본값으로 초기화, 케이스 이름 지정.
   - **결과 뷰어**: Summary, GT, HRSG, ST, Condenser, Mass Balance, Calculation Trace를 트리/텍스트 뷰로 확인.
   - **보고서 내보내기**: Excel, SVG, 계산 추적(JSON), 결과(JSON)를 선택한 디렉터리에 즉시 저장.
3. 실행 흐름:
   - 케이스 값을 입력하거나 `Load case…`로 JSON을 불러온다.
   - `Run solver`를 눌러 계산 결과를 확인한다.
   - 필요 시 `Export reports`로 산출물을 저장한다.

GUI를 통해 입력-출력 관계를 빠르게 검토하고, 계산 과정(trace)도 즉시 확인할 수 있다.

---

## 2. 단위·기준

### 2.1 단위

- 온도: °C
- 압력: bar(abs) 또는 kPa(abs). 변수명에 `_abs` 명시
- 유량: kg/s
- 엔탈피/엔트로피: kJ/kg, kJ/kg-K
- 전력: MW
- 효율: % (리포트 단계에서만 %로 포맷)

코드 내부 계산은 효율을 항상 소수(0.0 ~ 1.0)로 유지하고, reporter에서만 곱하기 100 후 %로 표현한다.

### 2.2 열역학 표준

- 스팀(물/증기) 성질은 IAPWS-IF97 계열 공식(또는 동등 정확도의 라이브러리)을 사용한다.
- 엔탈피, 엔트로피, 비열(cp), 포화조건 등은 하드코딩하지 않고 `utils/steam_props.py`를 통해 호출한다.
- GT 연료 투입량, 배기가스 조건 등은 가스터빈 블록에서만 책임진다. 다른 블록이 임의로 재계산하지 않는다.

---

## 3. 수렴 규칙

### 3.1 HRSG 반복 수렴

- 목표: HP/IP/LP 스팀 유량을 찾는다.
- 입력: GT 배기가스 유량/온도, 각 압력레벨의 목표 압력/과열온도, pinch/approach, 최소 굴뚝온도.
- 방법:
  1. HP 유량 가정 → 필요 열량 Q_req_HP 계산
  2. 배기가스에서 회수 가능한 Q_avail을 계산하고 pinch/approach 위반 여부 확인
  3. HP 유량을 조정해 만족시키면, 남은 배기가스 열량으로 IP 반복
  4. IP 정리 후 남은 열량으로 LP 반복
  5. 전체 질량/에너지 밸런스 에러율이 허용 범위(기본 0.5% 이하)일 때까지 루프
- 최대 반복 횟수는 코드 상수(`MAX_ITER_HRSG`, 초기 제안값 50).
- 수렴 실패 시에도 partial result를 기록하고, `converged=false`로 결과에 남긴다.

### 3.2 전 플랜트 밸런스

- 모든 블록을 통과한 뒤, 전체 질량/에너지 밸런스 에러율(`closure_error_pct`)을 계산한다.
- 허용 기준: 0.5% 이하.
- 초과일 경우 `mass_energy_balance.converged=false`.

---

## 4. 보안과 민감도

### 4.1 Vendor 커브 / 보증 파라미터

- GT 성능 커브(외기온도에 따른 출력 감소율 등), HRSG pinch/approach, ST 효율 커브 등은 상업적 민감 정보다.
- 이 값들은 `data/*.json` 파일에 들어가며, 이 JSON은 사내 기밀로 취급한다.
- 공개 Repo에는 예제/더미 값만 올린다. 실제 값은 별도 private Repo 또는 사내 Vault에서 관리하고 CI/CD로 주입한다.

### 4.2 리포트 내 정보 최소화

- Reporter는 계약/협상에 필요한 요약치만 담는다.
- 벤더명, 상세 커브 raw data 등은 넣지 않는다.
- 메타데이터(케이스 파일명, commit hash, timestamp)는 항상 Summary 시트 하단에 박는다. 추적성은 확보하되, 민감 계산근거는 노출하지 않는다.

---

## 5. 코드 개발 지침

### 5.1 언어 / 런타임

- Python 3.11 이상 가정.
- 외부 라이브러리:
  - 수치 해석: `math`, `numpy` 등 기본 범위
  - 물성치: IAPWS-IF97 계열 혹은 동등 수준 구현
  - Excel 생성: `openpyxl` 또는 유사 라이브러리
  - SVG 생성: 표준 Python string 템플릿 기반 (추가 의존성 최소화)
- 외부 라이브러리는 실제 환경 정책에 따라 조정 가능. 외부 의존성은 반드시 Poetry로 관리한다.

### 5.2 모듈 책임 분리

각 모듈은 다음 형태를 지킨다:

```python
def solve_xxx(input_dict: dict) -> dict:
    """
    input_dict: 모듈 입력
    return: 계산 결과 dict (순수 값만; 부수효과 없음)
    """
```

전역 mutable 상태 금지. I/O만으로 동작.

### 5.3 예외 / 에러 처리

- 수렴 실패, 비현실적 입력 등은 `raise` 대신 `converged=false`로 결과 dict에 기록.
- 절대 Silent Fail 금지. 항상 meta에 이유를 적는다. 예:

```json
"meta": {
  "warnings": [
    "Condenser vacuum below 5 kPa_abs is outside validated range"
  ]
}
```

### 5.4 라운딩과 표시

- 내부 계산은 가능한 한 full precision 유지.
- Reporter에서만 사람이 읽는 값으로 라운딩한다.
  - 온도: 1 decimal °C
  - 압력: 0.1 bar abs
  - 유량: 0.1 kg/s
  - 전력: 0.1 MW
  - 효율: 0.1 %
- 라운딩 규칙은 reporter 모듈에 상수로 모아둔다.

### 5.5 커밋 메시지 규약

- `feat(hrsg): add 3-pressure pinch solver`
- `fix(st): correct isentropic expansion for IP section`
- `refactor(reporter): move rounding logic to constants`
- `chore(defaults): update default pinch for HP from 10K to 9K`

형식: `<type>(<module>): <short summary>`

### 5.6 브랜치 운용 (초기 제안)

- `main`: 검증된 상태. 보고서에 직접 사용할 수 있는 버전만.
- `dev/*`: 기능 개발 브랜치. 예: `dev/hrsg-solver`.
- PR시 요구사항:
  - 최소 1명 리뷰
  - 수렴 안정성(closure_error_pct ≤ 0.5%) 유지되는지 케이스 1개 이상으로 확인 스크린샷/엑셀 첨부

---

## 6. 사용 예시

```bash
# 1) 케이스 파일 준비
cp data/plant_case_summer_35C.json data/tmp_case.json
# tmp_case.json 안에서 외기온도, 복수기 진공 등 수정

# 2) 실행 (콘솔 요약 + 계산 로그 경로 표시)
python run_case.py --case data/tmp_case.json --out output/tmp_case --show-steps

# 3) 산출 확인
ls output/tmp_case
  tmp_case.xlsx
  tmp_case.svg
  tmp_case_calculations.json
  tmp_case_result.json
```

- 콘솔에는 입력 요약, GT/HRSG/ST/Condenser 블록별 주요 지표, 수렴 정보가 섹션별로 표기된다.
- `tmp_case.xlsx`의 Summary 시트 하단에는 입력 케이스 파일명, solver commit hash, UTC timestamp, converged 여부가 자동으로 기록된다.
- `tmp_case_calculations.json`에는 각 블록별 계산 로그가 JSON 구조로 저장되어 추적성을 확보한다.
- `tmp_case.svg`는 GT→HRSG→ST→Condenser 블록 다이어그램과 주요 유량/전력 값을 함께 나타낸다.

---

## 7. 책임 범위 / 비범위

포함 범위

- 3압력 HRSG(HP/IP/LP) 기반 정상상태 열수지
- Net MW, Net 효율(%LHV), 복수기 부하 등 계약/성능평가에 직접 쓰는 값
- 벤더 간/조건 간 비교

비범위 (초기 버전)

- 과도응답(시동/정지, 램프율)
- 배출가스 환경규제(NOₓ, CO 등)
- 비용/경제성 해석
- 장주기 부식/피로/크리프 해석 등 기계적 신뢰성 분석
- 다중 GT/다중 ST의 복잡한 헤더 공유(후속 단계에서 확장 가능)

---

## 8. 유지보수 원칙

- `agent.md` = 동작 규칙서 (HBD Agent behavior contract)
- `README.md` = 저장소 운영 및 개발 규칙서
- 설계 변경(예: pinch 기본값 조정, 수렴 기준 변경 등)이 생기면 다음 순서로 업데이트한다:
  1. `defaults/defaults.json` 수정
  2. 관련 solver 코드 수정
  3. `agent.md`와 `README.md`에 해당 변경 반영
  4. commit hash 기록 후 main에 머지

---

## 9. 요약

이 저장소는 "입력 JSON만 바꾸면 CCPP HBD가 동일 규칙으로 재현 가능하게 나온다"는 것을 목표로 한다.

- 3압력 HRSG(HP/IP/LP)까지 포함한 정상상태 열수지
- 단위/물성/수렴조건 표준화
- 결과 재현성 확보(케이스 파일명, git commit hash, timestamp)
- 민감 파라미터(벤더 커브 등)의 안전한 분리

이 기준을 지키면, HBD는 개인의 엑셀 감각이 아니라 조직의 표준 자산이 된다.
