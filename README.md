# CCPP HBD Solver

복합화력(CCPP) 3압력 HRSG Heat Balance Data(HBD) 자동화 엔진.

이 프로젝트는 외기 조건, 가스터빈(GT) 성능, HRSG pinch/approach, 복수기 조건 등을 입력으로 받아 열수지 계산과 보고서(Excel, SVG)를 자동 생성한다. 계산 코어는 순수 함수 스타일로 작성되어 CLI와 GUI에서 동일한 파이프라인을 재사용한다.

---

## 0. 빠른 시작

```bash
# 1) Poetry 설치 (권장: pipx 사용)
pipx install poetry

# 2) 의존성 설치
poetry install

# 3) 단일 케이스 실행 (산출물은 output/ 디렉터리에 저장)
poetry run python run_case.py \
  --case data/plant_case_summer_35C.json \
  --out output/summer35

# 4) GUI 실행 (Tkinter 기반 다이어그램 편집기)
poetry run python run_gui.py

# (선택) 케이스 행렬 실행 예시 - Appendix I 설계에 따라 추후 제공
poetry run python run_grid.py --matrix cases.yml
```

산출물은 `output/<case>` 디렉터리에 저장된다.

| 파일 | 설명 |
| --- | --- |
| `<case>_result.json` | 최종 계산 결과 스냅샷 (summary + meta) |
| `<case>_calculations.json` | 단계별 계산 로그(ambient/GT/HRSG/ST/Condenser) |
| `<case>.xlsx` | Summary/Streams/Calculations 시트를 포함한 Excel 리포트 |
| `<case>.svg` | GT→HRSG→ST→Condenser 플로우 다이어그램 |

---

## 1. 디렉터리 구조

```
ccpp-hbd-solver/
├─ README.md
├─ agent.md
├─ AGENTS.md
├─ defaults/
│   └─ defaults.json             # 기본 가정치 (효율, pinch 등)
├─ data/
│   ├─ plant_case_summer_35C.json
│   └─ plant_case_winter_5C.json
├─ schema/
│   └─ case.schema.json          # JSON Schema v0.2 명세
├─ docs/
│   ├─ architecture.md           # 내부 파이프라인 & 다이어그램 요약
│   └─ case_schema_v0.2.md       # 케이스 스키마 세부 정의
├─ src/
│   └─ ccpp_hbd_solver/
│       ├─ ambient/              # 외기 보정
│       ├─ gt_block/             # GT 출력/연료/배기가스 계산
│       ├─ hrsg_block/           # 3압력 HRSG 수렴 로직
│       ├─ st_block/             # 스팀터빈 팽창 계산
│       ├─ condenser_loop/       # 복수기 및 급수 루프
│       ├─ plant_summary/        # Net MW, 효율, closure 계산
│       ├─ reporter/             # Excel/SVG/콘솔 출력
│       ├─ ui/                   # Tkinter 다이어그램 GUI
│       └─ utils/                # 단위 변환, 물성 헬퍼
├─ run_case.py                   # CLI 엔트리포인트
├─ run_gui.py                    # GUI 런처
└─ pyproject.toml
```

---

## 2. 실행 흐름 (내부 로직)

입력 JSON은 기본값과 병합 후 다음 순서로 처리된다. 세부 내용은 `docs/architecture.md` 참조.

1. **Ambient 보정** – 외기 온도/습도/압력에 따른 보정계수 계산 (`ambient/ambient_correction.py`).
2. **Gas Turbine** – 보정 계수를 적용해 실제 전기출력, 연료 열투입, 배기가스 상태 계산 (`gt_block/gt_solver.py`).
3. **HRSG** – HP/IP/LP 증기 유량을 에너지 가중치 기반으로 배분하고 굴뚝 최소온도를 만족시키도록 조정 (`hrsg_block/hrsg_solver.py`).
4. **Steam Turbine** – 각 섹션 등엔트로피 효율을 적용해 발전량 계산, 기계/발전기 효율 반영 (`st_block/st_solver.py`).
5. **Condenser Loop** – LP 배기 증기를 응축시키고 냉각수 열부하/출구온도를 산출 (`condenser_loop/condenser_solver.py`).
6. **Plant Summary** – Net MW, %LHV, closure error, 경고 메시지를 집계 (`plant_summary/plant_summary.py`).

모든 단계는 입력을 변경하지 않고 결과/추적 데이터를 반환한다. `PipelineArtifacts`는 `result`, `trace`, `merged_case`를 묶어 CLI와 GUI가 동일한 출력을 공유하도록 한다.

---

## 3. 입력/출력 계약

### 3.1 입력 JSON

- 단위: 온도(°C), 압력(bar abs 또는 kPa abs), 유량(kg/s), 전력(MW).
- 효율은 소수(0~1)로 입력하며, 보고서에서만 %로 표시한다.
- v0.2 스키마는 `fixed`/`vary`/`devices` 세 블록으로 구성된다. 자세한 정의는 [`docs/case_schema_v0.2.md`](docs/case_schema_v0.2.md)와 [`schema/case.schema.json`](schema/case.schema.json)을 참조한다.
- 예제는 `data/plant_case_summer_35C.json`, `data/plant_case_winter_5C.json`에 제공되며, 누락된 값은 `defaults/defaults.json`의 기본값을 사용한다.

### 3.2 결과 구조

`run_pipeline()`은 다음 구조의 dict를 반환한다.

```json
{
  "summary": {"GT_power_MW": ..., "NET_power_MW": ..., "NET_eff_LHV_pct": ...},
  "gt_block": {...},
  "hrsg_block": {..., "converged": true},
  "st_block": {...},
  "condenser_block": {...},
  "mass_energy_balance": {"closure_error_pct": 0.32, "converged": true},
  "meta": {
    "input_case": "plant_case_summer_35C.json",
    "timestamp_utc": "2024-05-01T10:42:03Z",
    "solver_commit": "<git hash>",
    "warnings": []
  }
}
```

closure error가 0.5%를 초과하거나 HRSG가 수렴하지 못하면 `converged`가 `false`로 내려가고 경고 메시지가 `meta.warnings`에 추가된다.

---

## 4. CLI 사용법 (`run_case.py`)

```bash
python run_case.py --case <case.json> --out <output-dir> [--show-steps] [--no-console]
```

- `--show-steps`: 콘솔에 요약 + trace 위치를 출력
- `--no-console`: 콘솔 요약 생략 (CI에서 사용)

CLI는 항상 Excel, SVG, 계산 로그 JSON, 결과 JSON을 함께 생성한다.

---

## 5. GUI 개요 (`run_gui.py`)

Tkinter 기반 다이어그램 편집기는 `DiagramCanvas`를 통해 한 화면에서 입력 편집과 결과 확인을 지원한다.

- **Hotspot 편집**: 각 블록 주변에 배치된 영역을 클릭하면 Spinbox가 열려 값을 수정할 수 있다. 영문/한글 레이블, 단위, 허용 범위를 동시에 표시한다.
- **자동 실행(Auto-run)**: 값 변경 후 0.5초 내 자동으로 파이프라인을 다시 실행한다. 해제하면 수동으로 `Run Solver`를 눌러 실행한다.
- **경고 강조**: HRSG 수렴 실패 또는 closure 초과 시 해당 블록이 노란색으로 강조되고 경고 텍스트가 하단에 표시된다.
- **내보내기**: GUI에서도 Excel/SVG/Trace JSON을 한 번에 내보낼 수 있다.

레이아웃 및 더 자세한 설명은 `docs/architecture.md`의 “GUI Diagram Layout” 절을 참고한다.

---

## 6. Reporter 포맷

- `reporter/excel_reporter.py` – Summary/Streams/Calculations 시트를 가진 XLSX를 생성한다. `openpyxl`이 없으면 내부 XML 빌더로 대체 파일을 만든다.
- `reporter/diagram_svg.py` – GT → HRSG → ST → Condenser 블록과 주요 수치를 포함한 SVG 다이어그램을 생성한다.
- `reporter/console_reporter.py` – CLI 실행 시 콘솔 요약과 계산 로그 저장을 담당한다.

---

## 7. 민감 정보 분리(벤더 커브)

- 공개 저장소에는 벤더 곡선/보증치 등 민감 데이터를 커밋하지 않는다.
- 런타임에 비공개 데이터를 병합할 때는 환경 변수나 CI 시크릿을 사용한다.

예시 (GitHub Actions):

```yaml
- name: Run HBD case with vendor curves
  run: |
    mkdir -p private
    echo "$VENDOR_CURVE_JSON" > private/gt_curves.json
    poetry run python run_case.py \
      --case data/plant_case_summer_35C.json \
      --out output/summer35 \
      --no-console
  env:
    VENDOR_CURVE_JSON: ${{ secrets.VENDOR_CURVE_JSON }}
```

예시 (로컬 실행):

```bash
export DATA_SECRET_PATH=$HOME/hbd_secrets
poetry run python run_case.py --case data/plant_case_summer_35C.json --out output/summer35
```

`ccpp_hbd_solver.pipeline.load_defaults` 이후에 비밀 데이터를 로드하여 병합하면 코어 솔버는 동일한 인터페이스를 유지하면서 민감정보를 분리할 수 있다.

---

## 8. 개발 노트

- Python 3.11 이상, Poetry 프로젝트 구조 (`pyproject.toml`).
- 모든 solver는 순수 함수 스타일을 유지하고, 전역 mutable 상태를 사용하지 않는다.
- `PipelineArtifacts`를 통해 CLI와 GUI가 동일한 계산 결과를 공유하므로, 새로운 리포트나 UI 기능을 추가할 때 재사용 가능하다.
- 계산 로직 또는 데이터 구조가 변경되면 `README.md`, `agent.md`, `defaults/defaults.json`을 동기화한다.

---

## 9. 참고 자료

- 내부 파이프라인과 GUI 구성도: `docs/architecture.md`
- 에이전트 동작 규약: `agent.md`
