# CCPP HBD Case Schema v0.3

본 문서는 v0.3 케이스 스키마 구조, 허용 범위, 검증 규칙을 요약한다. 정식 JSON Schema 정의는 [`schema/case.schema.json`](../schema/case.schema.json)에 수록되어 있으며, 예시 파일은 `data/plant_case_summer_35C.json`, `data/plant_case_winter_5C.json`을 참고한다.

## 1. 최상위 구조

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `schema_version` | `"0.3"` | 필수 스키마 버전 태그. |
| `units_system` | `"SI_IF97"` | 단위 체계(°C, bar(abs), kg/s, MW + IAPWS-IF97 물성) 고정. |
| `fixed` | object | 단일 케이스 입력. 모든 필수 값이 이 블록에 존재해야 한다. |
| `vary` | object (선택) | 키 경로(`ambient.Ta_C` 등)별 후보 값 배열. 그리드 러너가 조합을 생성할 때 사용한다. 기본값 `{}`. |
| `devices` | array (선택) | 파이프라인 훅을 통해 동작하는 변동 장치 정의. 기본값 `[]`. |
| `constraints` | object (선택) | 케이스 전역 제약 완화 허용 여부. |
| `meta` | object (선택) | 작성자/노트 등 자유 형식 메타데이터. |

### 1.1 키 경로 문법

- 소문자 스네이크 케이스 모듈명 + 점(`.`)으로 중첩 필드를 지정한다.
- `gas_turbine.corr_coeff.dPower_pct_per_K`처럼 세 단계 이상도 지원한다.
- 허용 경로는 Schema `vary.propertyNames.pattern` 조건과 일치해야 한다.

## 2. `fixed` 블록 세부 항목

### 2.1 `plant`

| 경로 | 단위 | 허용범위 | 비고 |
| --- | --- | --- | --- |
| `plant.topology` | enum | `single-shaft-1x1`, `multi-shaft-2x1`, `multi-shaft-3x1` | 사이트 열수지 구성. |
| `plant.site_name` | 문자열 |  | 선택 입력. |

### 2.2 `ambient`

| 경로 | 단위 | 허용범위 | 비고 |
| --- | --- | --- | --- |
| `ambient.Ta_C` | °C | -40 ~ 60 | 외기 건구온도 |
| `ambient.RH_pct` | % | 0 ~ 100 | 상대습도 |
| `ambient.P_bar` | bar(abs) | 0.8 ~ 1.1 | 대기압 |

### 2.3 `gas_turbine`

| 경로 | 단위 | 허용범위 | 비고 |
| --- | --- | --- | --- |
| `gas_turbine.ISO_power_MW` | MW | 50 ~ 600 | ISO 정격 전력 |
| `gas_turbine.ISO_heat_rate_kJ_per_kWh` | kJ/kWh | 8,000 ~ 12,000 | ISO 열소비율 |
| `gas_turbine.fuel_LHV_kJ_per_kg` | kJ/kg | 38,000 ~ 52,000 | 연료 저위발열량 |
| `gas_turbine.ISO_exhaust_temp_C` | °C | 450 ~ 700 | ISO 배기 온도 |
| `gas_turbine.ISO_exhaust_flow_kg_s` | kg/s | 200 ~ 900 | ISO 배기유량 |
| `gas_turbine.corr_coeff.dPower_pct_per_K` | %/K | -1.0 ~ 0.0 | 온도당 전력 변화율 |
| `gas_turbine.corr_coeff.dFlow_pct_per_K` | %/K | 0.0 ~ 1.0 | 온도당 유량 변화율 |
| `gas_turbine.corr_coeff.dExhT_K_per_K` | K/K | 0.0 ~ 2.0 | 온도당 배기온 변화 |
| `gas_turbine.performance_blend.mode` | enum | `linear`, `vendor_blend` | 보정 모드 선택. |
| `gas_turbine.performance_blend.vendor_curve_id` | 문자열 |  | vendor 데이터 키. |
| `gas_turbine.performance_blend.blend_weight` | - | 0.0 ~ 1.0 | 벤더 커브 가중치. |

### 2.4 `hrsg`

| 경로 | 단위 | 허용범위 | 비고 |
| --- | --- | --- | --- |
| `hrsg.stack_temp_min_C` | °C | 70 ~ 150 | 굴뚝 최소온도 제약 |
| `hrsg.feedwater_temp_C` | °C | 60 ~ 150 | 급수 온도 (선택) |

각 압력단(`hp`, `ip`, `lp`) 필드는 아래 규칙을 공유한다.

| 경로 | 단위 | 허용범위 |
| --- | --- | --- |
| `pressure_bar` | bar(abs) | 0.5 ~ 200 |
| `steam_temp_C` | °C | 150 ~ 620 |
| `pinch_K` | K | 3 ~ 30 |
| `approach_K` | K | 2 ~ 20 |

#### 2.4.1 `hrsg.constraints`

| 필드 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `pinch_mode` | enum | `enforce` | `relax` 선택 시 핀치 제약 경고만 기록. |
| `approach_mode` | enum | `enforce` | 위와 동일. |
| `stack_mode` | enum | `enforce` | 위와 동일. |

#### 2.4.2 `hrsg.devices`

- `duct_burner`: `duty_MW`(0~200), `stack_temp_cap_C`(90~200)
- `bypass`: `fraction`(0~0.5) – 배기가스 우회 비율.
- `attemperators[]`: `target`(`hp`/`ip`/`lp`), `steam_temp_C`, `m_dot_max_kg_s`.

### 2.5 기타 블록

| 경로 | 단위 | 허용범위 | 비고 |
| --- | --- | --- | --- |
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
- 허용되는 경로는 `plant.`, `ambient.`, `gas_turbine.`, `hrsg.`, `steam_turbine.`, `condenser.`, `bop.` prefix를 가져야 한다.

예시:

```json
"vary": {
  "ambient.Ta_C": [5, 15, 35],
  "condenser.vacuum_kPa_abs": [6.0, 8.0, 12.0]
}
```

## 4. `devices` 블록

각 항목은 `attemperator`, `duct_firing`, `gt_inlet_cool` 중 하나여야 하며, 상세 필드는 JSON Schema 정의를 따른다. GUI/CLI 파이프라인은 `device.type`에 해당하는 플러그인을 순차 실행한다.

## 5. 전역 `constraints`

| 필드 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `allow_relaxed_pinch` | boolean | false | HRSG 핀치 위반 시 실패 대신 경고 허용 여부. |
| `allow_relaxed_stack` | boolean | false | 스택 최소온도 위반 시 실패 대신 경고 허용 여부. |

## 6. 기본값 출처

`defaults/defaults.json` 상단 `_notes` 항목에 각 키별 근거 링크가 정리되어 있다. 문서 내 챕터는 다음을 참고한다.

- [Steam Turbine Defaults](#25-기타-블록)
- [HRSG Defaults](#24-hrsg)
- [Condenser Defaults](#25-기타-블록)
- [BOP Defaults](#25-기타-블록)

## 7. 예시 파일 개요

- `data/plant_case_summer_35C.json` : 35°C 외기, 덕트버너 + HP 어템퍼레이터 포함.
- `data/plant_case_winter_5C.json` : 5°C 외기, stack 제약 완화 모드.

두 예시는 스키마 v0.3 구조와 `hrsg.devices`/`constraints` 확장 사용법을 보여준다.
