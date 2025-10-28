# CCPP HBD Case Schema v0.2

이 문서는 v0.2 케이스 스키마의 구조, 허용 범위, 검증 규칙을 요약한다. 정식 JSON Schema 정의는 [`schema/case.schema.json`](../schema/case.schema.json) 에 수록되어 있으며, 예시 파일은 `data/plant_case_summer_35C.json`, `data/plant_case_winter_5C.json`을 참고한다.

## 1. 최상위 구조

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `version` | `"0.2"` (선택) | 스키마 버전 태그. 생략 시 내부적으로 `0.2`로 간주한다. |
| `fixed` | object | 단일 케이스 입력. 모든 필수 값이 이 블록에 존재해야 한다. |
| `vary` | object (선택) | 키 경로(`ambient.Ta_C` 등)별 후보 값 배열. 그리드 러너가 조합을 생성할 때 사용한다. 기본값 `{}`. |
| `devices` | array (선택) | 파이프라인 훅을 통해 동작하는 변동 장치 정의. 기본값 `[]`. |
| `meta` | object (선택) | 작성자/노트 등 자유 형식 메타데이터. |

### 1.1 키 경로 문법

- 소문자 스네이크 케이스 모듈명 + 점(`.`)으로 중첩 필드를 지정한다.
- `gas_turbine.corr_coeff.dPower_pct_per_K` 처럼 세 단계까지 지원한다.
- 허용 경로는 Schema의 `vary.propertyNames.enum`과 동일하다.

## 2. `fixed` 블록 세부 항목

| 경로 | 단위 | 허용범위 | 비고 |
| --- | --- | --- | --- |
| `ambient.Ta_C` | °C | -40 ~ 60 | 외기 건구온도 |
| `ambient.RH_pct` | % | 0 ~ 100 | 상대습도 |
| `ambient.P_bar` | bar(abs) | 0.8 ~ 1.1 | 대기압 |
| `gas_turbine.ISO_power_MW` | MW | 50 ~ 600 | ISO 정격 전력 |
| `gas_turbine.ISO_heat_rate_kJ_per_kWh` | kJ/kWh | 8,000 ~ 12,000 | ISO 열소비율 |
| `gas_turbine.fuel_LHV_kJ_per_kg` | kJ/kg | 38,000 ~ 52,000 | 연료 저위발열량 |
| `gas_turbine.ISO_exhaust_temp_C` | °C | 450 ~ 700 | ISO 배기 온도 |
| `gas_turbine.ISO_exhaust_flow_kg_s` | kg/s | 200 ~ 900 | ISO 배기유량 |
| `gas_turbine.corr_coeff.dPower_pct_per_K` | %/K | -1.0 ~ 0.0 | 온도당 전력 변화율 |
| `gas_turbine.corr_coeff.dFlow_pct_per_K` | %/K | 0.0 ~ 1.0 | 온도당 유량 변화율 |
| `gas_turbine.corr_coeff.dExhT_K_per_K` | K/K | 0.0 ~ 2.0 | 온도당 배기온 변화 |
| `hrsg.hp.pressure_bar` | bar(abs) | 60 ~ 160 | HP 증기압 |
| `hrsg.hp.steam_temp_C` | °C | 450 ~ 600 | HP 과열증기 온도 |
| `hrsg.hp.pinch_K` | K | 5 ~ 20 | HP 핀치 |
| `hrsg.hp.approach_K` | K | 3 ~ 15 | HP 어프로치 |
| `hrsg.ip.pressure_bar` | bar(abs) | 15 ~ 60 | IP 증기압 |
| `hrsg.ip.steam_temp_C` | °C | 400 ~ 600 | IP 과열증기 온도 |
| `hrsg.ip.pinch_K` | K | 8 ~ 20 | IP 핀치 |
| `hrsg.ip.approach_K` | K | 4 ~ 15 | IP 어프로치 |
| `hrsg.lp.pressure_bar` | bar(abs) | 1 ~ 15 | LP 증기압 |
| `hrsg.lp.steam_temp_C` | °C | 150 ~ 350 | LP 증기 온도 |
| `hrsg.lp.pinch_K` | K | 10 ~ 25 | LP 핀치 |
| `hrsg.lp.approach_K` | K | 5 ~ 15 | LP 어프로치 |
| `hrsg.stack_temp_min_C` | °C | 70 ~ 150 | 굴뚝 최소온도 제약 |
| `hrsg.feedwater_temp_C` | °C | 60 ~ 150 | 급수 온도 (선택) |
| `steam_turbine.isentropic_eff_hp` | η | 0.75 ~ 0.92 | HP 등엔트로피 효율 |
| `steam_turbine.isentropic_eff_ip` | η | 0.75 ~ 0.92 | IP 등엔트로피 효율 |
| `steam_turbine.isentropic_eff_lp` | η | 0.75 ~ 0.90 | LP 등엔트로피 효율 |
| `steam_turbine.mech_elec_eff` | η | 0.95 ~ 0.995 | 기계/발전기 효율 |
| `condenser.vacuum_kPa_abs` | kPa(abs) | 4 ~ 15 | 복수기 진공 |
| `condenser.cw_inlet_C` | °C | 5 ~ 35 | 냉각수 입구 온도 |
| `bop.aux_load_MW` | MW | 0 ~ 60 | 보조부하 |

## 3. `vary` 블록

- 값은 배열(`[]`)로 제공하며, 각 항목은 숫자여야 한다.
- 스키마는 중복 값을 허용하지 않는다(`uniqueItems: true`).
- `run_case.py`는 단일 케이스 실행에 초점을 두므로, `vary`에 값이 있어도 즉시 조합을 실행하지 않는다. 그리드 러너(`run_grid.py`, 작업 예정)는 본 블록을 사용하여 케이스 행렬을 생성한다.

예시:

```json
"vary": {
  "ambient.Ta_C": [5, 15, 35],
  "condenser.vacuum_kPa_abs": [6.0, 8.0, 12.0]
}
```

## 4. `devices` 블록

각 항목은 아래 타입 중 하나여야 한다.

### 4.1 Attemperator

| 필드 | 타입 | 범위 | 설명 |
| --- | --- | --- | --- |
| `type` | `"attemperator"` | 고정 | 장치 식별자 |
| `target` | enum(`hp`,`ip`,`lp`) | — | 어느 압력단에 연결할지 |
| `control.steam_temp_C` | °C | 200 ~ 620 | 목표 과열증기 온도 |
| `limits.m_dot_max_kg_s` | kg/s | 0.1 ~ 20 | 분사유량 상한 |

### 4.2 Duct Firing

| 필드 | 타입 | 범위 | 설명 |
| --- | --- | --- | --- |
| `type` | `"duct_firing"` | 고정 | |
| `hrsg_section` | enum(`economizer`,`evaporator`,`superheater`) | — | 열량이 추가되는 세그먼트 |
| `Q_add_MW` | MW | 1 ~ 200 | 추가 열량 |
| `stack_temp_cap_C` | °C | 90 ~ 200 | 굴뚝 온도 상한 (선택) |

### 4.3 GT Inlet Cooling

| 필드 | 타입 | 범위 | 설명 |
| --- | --- | --- | --- |
| `type` | `"gt_inlet_cool"` | 고정 | |
| `method` | enum(`evaporative`,`chiller`,`fogging`) | — | 냉각 방식 |
| `T_db_target_C` | °C | -10 ~ 30 | 목표 건구온도 |

장치 정의는 파이프라인 훅(`pre_GT`, `pre_HRSG`, `pre_ST`, `pre_Condenser`, `post_HRSG`)에서 적용된다. 현재 코어 솔버는 장치를 직접 사용하지 않지만, 메타데이터(`meta.declared_devices`)로 기록되어 추후 확장에 대비한다.

## 5. 예시 파일

- [`data/plant_case_summer_35C.json`](../data/plant_case_summer_35C.json)
- [`data/plant_case_winter_5C.json`](../data/plant_case_winter_5C.json)

두 파일 모두 `version`, `fixed`, `vary`, `devices` 블록을 포함하며, CLI 실행 시 `fixed` 블록이 기본 케이스로 사용된다.
