# CCPP HBD Solver Architecture

이 문서는 CCPP HBD 파이프라인의 실행 흐름, 모듈 경계, 장치 훅 인터페이스, 경고 코드, GUI 다이어그램 핫스팟 정의를 정리한다.

## Runtime Pipeline

```mermaid
flowchart LR
    A[Load case JSON/Excel] --> B[Merge defaults]
    B --> C[Apply device hooks (pre_*)]
    C --> D[Ambient corrections]
    D --> E[GT block]
    E --> F[HRSG block]
    F --> G[Steam turbine block]
    G --> H[Condenser loop]
    H --> I[Plant summary]
    I --> J[Reporter (Excel/SVG/JSON)]
    I --> K[Trace export]
```

파이프라인은 `PipelineArtifacts`에 `result`, `trace`, `merged_case`를 모아 CLI(`run_case.py`)와 GUI(`run_gui.py`)가 동일한 계산 핵심을 공유하도록 한다.

### Module Boundaries

| 모듈 | 파일 | 주요 책임 |
| --- | --- | --- |
| Ambient | `src/ccpp_hbd_solver/ambient/ambient_correction.py` | 외기 보정 계수 계산, GT 보정에 사용 |
| GT Block | `src/ccpp_hbd_solver/gt_block/gt_solver.py` | 실제 전력, 연료 열투입, 배기가스 상태 계산 |
| HRSG Block | `src/ccpp_hbd_solver/hrsg_block/hrsg_solver.py` | HP/IP/LP 증기량 배분, 굴뚝 최소온도 제약 확인 |
| Steam Turbine | `src/ccpp_hbd_solver/st_block/st_solver.py` | 각 단 등엔트로피 효율 적용, 발전량 산출 |
| Condenser Loop | `src/ccpp_hbd_solver/condenser_loop/condenser_solver.py` | 복수기 열부하, 냉각수 조건 계산 |
| Plant Summary | `src/ccpp_hbd_solver/plant_summary/plant_summary.py` | Net MW, %LHV, mass/energy closure 집계 |
| Reporter | `src/ccpp_hbd_solver/reporter/*` | Excel, SVG, 콘솔 출력, 계산 로그 저장 |

### Device Hook Lifecycle

장치(Device)는 파이프라인 단계 진입 전후에 주입되는 플러그인이다. 훅 이름과 시점은 다음과 같다.

- `pre_GT` → Ambient 보정 후, GT 블록 실행 전
- `pre_HRSG` → GT 블록 결과를 사용하기 직전
- `post_HRSG` → HRSG 수렴 직후, 스팀터빈 입력 수정 가능
- `pre_ST` → Steam Turbine 계산 직전
- `pre_Condenser` → Condenser 루프 계산 직전

장치 프로토콜 예시는 Appendix I와 동일하다.

```python
class Device(Protocol):
    name: str

    def apply(self, hook: str, model: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Return updated model plus warning messages for the active hook."""
```

`run_case.py`는 현재 `devices` 블록을 메타 정보(`meta.declared_devices`)로만 기록하며, 장치 로더/실행기는 추후 확장 시 추가된다.

## GUI Diagram Layout

`DiagramCanvas`(`src/ccpp_hbd_solver/ui/diagram_canvas.py`)는 고정 좌표계에 GT → HRSG → ST → Condenser 흐름을 배치한다. 주요 노드는 다음 위치를 사용한다.

- Gas Turbine: (80, 130) ~ (200, 210)
- HRSG: (220, 90) ~ (320, 310)
- Steam Turbine HP/IP/LP: (360, 110/180/250) ~ (460, 160/230/300)
- Condenser: (520, 280) ~ (680, 360)

핫스팟은 아래 표의 ID와 경로를 따른다. `HSxx` 번호는 문서 전용 식별자이며, 실제 Canvas 아이템 ID는 런타임에 생성된다.

| ID | 경로 | 레이블(EN) | 단위 | 허용 범위 |
| --- | --- | --- | --- | --- |
| HS01 | `ambient.Ta_C` | Ambient T | °C | -20.0 ~ 55.0 |
| HS02 | `ambient.RH_pct` | Relative Humidity | % | 0.0 ~ 100.0 |
| HS03 | `ambient.P_bar` | Ambient Pressure | bar abs | 0.8 ~ 1.1 |
| HS04 | `gas_turbine.ISO_power_MW` | GT ISO Power | MW | 50.0 ~ 600.0 |
| HS05 | `gas_turbine.ISO_heat_rate_kJ_per_kWh` | ISO Heat Rate | kJ/kWh | 8000.0 ~ 12000.0 |
| HS06 | `gas_turbine.fuel_LHV_kJ_per_kg` | Fuel LHV | kJ/kg | 38000.0 ~ 52000.0 |
| HS07 | `gas_turbine.ISO_exhaust_temp_C` | ISO Exhaust T | °C | 450.0 ~ 700.0 |
| HS08 | `gas_turbine.ISO_exhaust_flow_kg_s` | ISO Exhaust Flow | kg/s | 200.0 ~ 900.0 |
| HS09 | `gas_turbine.corr_coeff.dPower_pct_per_K` | ΔPower | %/K | -1.0 ~ 0.0 |
| HS10 | `gas_turbine.corr_coeff.dFlow_pct_per_K` | ΔFlow | %/K | 0.0 ~ 1.0 |
| HS11 | `gas_turbine.corr_coeff.dExhT_K_per_K` | ΔExhaust T | K/K | 0.0 ~ 2.0 |
| HS12 | `hrsg.hp.pressure_bar` | HP Pressure | bar abs | 60.0 ~ 160.0 |
| HS13 | `hrsg.hp.steam_temp_C` | HP Steam T | °C | 450.0 ~ 600.0 |
| HS14 | `hrsg.hp.pinch_K` | HP Pinch | K | 5.0 ~ 20.0 |
| HS15 | `hrsg.hp.approach_K` | HP Approach | K | 3.0 ~ 15.0 |
| HS16 | `hrsg.ip.pressure_bar` | IP Pressure | bar abs | 15.0 ~ 60.0 |
| HS17 | `hrsg.ip.steam_temp_C` | IP Steam T | °C | 400.0 ~ 600.0 |
| HS18 | `hrsg.ip.pinch_K` | IP Pinch | K | 8.0 ~ 20.0 |
| HS19 | `hrsg.ip.approach_K` | IP Approach | K | 4.0 ~ 15.0 |
| HS20 | `hrsg.lp.pressure_bar` | LP Pressure | bar abs | 1.0 ~ 15.0 |
| HS21 | `hrsg.lp.steam_temp_C` | LP Steam T | °C | 150.0 ~ 350.0 |
| HS22 | `hrsg.lp.pinch_K` | LP Pinch | K | 10.0 ~ 25.0 |
| HS23 | `hrsg.lp.approach_K` | LP Approach | K | 5.0 ~ 15.0 |
| HS24 | `hrsg.stack_temp_min_C` | Stack Min T | °C | 70.0 ~ 130.0 |
| HS25 | `steam_turbine.isentropic_eff_hp` | HP η | η | 0.75 ~ 0.92 |
| HS26 | `steam_turbine.isentropic_eff_ip` | IP η | η | 0.75 ~ 0.92 |
| HS27 | `steam_turbine.isentropic_eff_lp` | LP η | η | 0.75 ~ 0.90 |
| HS28 | `steam_turbine.mech_elec_eff` | Mech/Gen η | η | 0.95 ~ 0.995 |
| HS29 | `condenser.vacuum_kPa_abs` | Condenser Vacuum | kPa abs | 4.0 ~ 15.0 |
| HS30 | `condenser.cw_inlet_C` | CW Inlet | °C | 5.0 ~ 35.0 |
| HS31 | `bop.aux_load_MW` | Aux Load | MW | 0.0 ~ 50.0 |

## Error & Warning Codes

경고/에러는 `result.meta.warnings[]`에 문자열로 기록된다. 기본 코드와 의미는 아래와 같다.

| 코드 | 설명 | 권장 조치 |
| --- | --- | --- |
| `HRSG_PINCH_VIOLATION` | 지정한 핀치/어프로치 제약을 만족하지 못함 | 입력 핀치/어프로치 재조정, 세그먼트 수/완화계수 확인 |
| `ATTEMP_LIMIT_REACHED` | Attemperator 최대 분사유량 도달 | `limits.m_dot_max_kg_s` 증설 또는 목표 온도 조정 |
| `CLOSURE_GT_0P5` | 전체 플랜트 mass/energy closure > 0.5% | GT/HRSG/Condenser 파라미터 검토, 반복 조건 확인 |
| `HRSG_STACK_TEMP_LOW` | 굴뚝 최소온도 미달 | `hrsg.stack_temp_min_C` 상향 또는 duct firing 검토 |

코드 표는 `docs/case_schema_v0.2.md`와 함께 유지보수하며, GUI 경고 배지 및 콘솔 로그에 동일 메시지를 사용한다.

## Artifact Outputs

| 산출물 | 위치 | 내용 |
| --- | --- | --- |
| Excel | `output/<case>.xlsx` | Summary/Streams/Calculations 시트, 라운딩 규칙은 Reporter 상수에 집중 |
| SVG | `output/<case>.svg` | GT→HRSG→ST→Condenser 다이어그램 및 주요 수치 |
| Result JSON | `output/<case>_result.json` | 파이프라인 결과 스냅샷 + 메타데이터 |
| Calculations JSON | `output/<case>_calculations.json` | 단계별 trace, 반복 정보 포함 |

CLI와 GUI는 동일한 Reporter 함수를 호출하므로 어느 인터페이스에서 실행하든 위 산출물을 공유한다.
