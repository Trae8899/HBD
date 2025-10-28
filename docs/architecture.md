# CCPP HBD Solver Architecture

이 문서는 저장소의 핵심 실행 흐름과 GUI 다이어그램 구성 요소를 요약한다. 실제 계산 로직은 순수 함수로 작성되며, `src/ccpp_hbd_solver/` 하위 모듈에서 단계별로 분리되어 있다.

## Runtime Pipeline

입력 JSON은 기본값과 병합된 후 다음 순서로 처리된다. 각 단계는 `PipelineArtifacts.trace`에 세부 데이터를 남긴다.

```text
load_case → merge_case_with_defaults → apply_site_corrections
       ↓                            ↓
     case                         defaults
       ↓                              │
  run_pipeline(case) ─────────────────┘
       │
       ├─ ambient_correction.apply_site_corrections()
       ├─ gt_block.solve_gt_block()
       ├─ hrsg_block.solve_hrsg_block()
       ├─ st_block.solve_steam_turbine()
       ├─ condenser_loop.solve_condenser_loop()
       └─ plant_summary.summarize_plant()
```

각 블록의 책임은 다음과 같다.

| 단계 | 책임 | 주요 출력 |
| --- | --- | --- |
| Ambient | 외기 온도 보정 계수 계산 | `power_multiplier`, `flow_multiplier` |
| GT Block | 전기출력, 연료 열투입, 배기가스 조건 | `electric_power_MW`, `fuel_heat_input_MW_LHV`, `exhaust` |
| HRSG Block | HP/IP/LP 스팀 유량 및 굴뚝 온도 | `hp/ip/lp.steam_flow_kg_s`, `stack_temp_C` |
| ST Block | HP/IP/LP 섹션별 발전량 | `hp_section.power_MW`, `electric_power_MW` |
| Condenser Loop | 복수기 열부하, 냉각수 상태 | `heat_rejected_MW`, `cw_outlet_C` |
| Plant Summary | Net MW, 효율, 밸런스 수렴 | `summary`, `mass_energy_balance`, `meta.warnings` |

모든 단계는 실패 시 예외 대신 `converged`/`warnings` 필드로 상태를 보고한다. `run_case.py` 및 GUI 모두 `PipelineArtifacts` 객체를 활용하여 결과(`result`), 세부 추적(`trace`), 병합된 입력(`merged_case`)을 공유한다.

## GUI Diagram Layout

`DiagramCanvas`는 Tkinter 캔버스 위에 플랜트 구성도를 그린다. 주요 노드와 스트림은 아래 좌표 기준으로 배치된다.

```
+-----------+    GT exhaust     +-----------+   HP/IP/LP steam   +-----------+   LP exhaust   +------------+
| Gas Turbine | ─────────────▶ |   HRSG    | ─────────────────▶ | Steam Turbine | ───────────▶ |  Condenser |
+-----------+                  +-----------+                    +-----------+                 +------------+
   (80,160)                      (220,120)                        (400,120/190/260)             (520,285)
```

각 블록/스트림 위에는 다음 정보가 오버레이 된다.

- Gas Turbine: 전기출력, 연료 열투입, 배기가스 온도
- HRSG: HP/IP/LP 증기 유량, 굴뚝 온도, 수렴 경고 시 노란색 강조
- Steam Turbine: 섹션별 발전량 및 총 발전량
- Condenser: 열 방출량, 냉각수 출구 온도
- Summary 배지: Net MW, 효율, closure error

입력 편집은 `HOTSPOTS` 사양에 정의된 클릭 가능한 사각형으로 이루어지며, 영어/한국어 레이블과 단위, 허용 범위를 함께 노출한다. 우클릭 시 허용범위와 단위 정보를 표시하는 도움말이 열린다.

## Artifact Outputs

파이프라인 실행 결과는 공통 포맷으로 내보낸다.

- Excel (`reporter/excel_reporter.py`): Summary/Streams/Calculations 시트
- SVG (`reporter/diagram_svg.py`): 주요 블록과 스트림 값 시각화
- JSON (`run_case.py`): `_result.json`, `_calculations.json`

GUI에서도 동일한 내보내기 함수를 호출하므로 CLI와 동일한 아티팩트를 확보할 수 있다.
