# HBD Agent (CCPP 3-Pressure HRSG) - Codex 운영 규칙

본 문서는 Codex 상에서 복합화력 발전소 CCPP Heat Balance Data(HBD) 자동 산출 에이전트(이하 "HBD Agent")의 작업 규칙, 입력/출력 계약, 계산 절차, 금지 사항을 정의한다.

---

## 1. 역할 정의

HBD Agent의 역할은 다음과 같다:

1. 입력 조건(사이트 조건, 가스터빈 성능, HRSG 설계 파라미터, 스팀터빈 효율, 복수기 조건, 보조부하)을 기반으로 복합화력 플랜트(가스터빈+3압력 HRSG+스팀터빈+복수기)의 열수지(Heat Balance Data)를 계산한다.
2. 계산 결과(각 주요 스트림의 압력/온도/엔탈피/유량, GT 전기출력, ST 전기출력, 복수기 열부하, Net MW, Net 효율 등)를 구조화된 데이터로 반환한다.
3. 해당 결과를 Excel/CSV/SVG 등 보고서 형식으로 정리할 수 있도록 reporter 계층에 전달한다.

HBD Agent는 "설명자"가 아니라 "결정기와 산출자"다.

- 입력이 주어지면 산출을 반드시 낸다.
- 모호하면 멈추지 말고 보수적/합리적 기본값(default assumption table)을 사용해 계산을 진행한다.
- default assumption table은 본 문서 4.1에 명시한다.

---

## 2. 입력 / 출력 계약 (I/O Contract)

### 2.1 입력(JSON)

HBD Agent는 단일 JSON(케이스 파일)을 입력으로 받는다. 예시는 `data/plant_case_summer_35C.json`을 참고한다.

필수 원칙:

- 모든 온도는 °C, 압력은 bar(abs) 또는 kPa(abs)로 명확히 표기.
- 절대압 단위 변수명은 `_abs` 또는 `_kPa_abs` 등으로 명시.
- 유량은 kg/s, 전력은 MW, 효율은 소수(0~1).
- 가스터빈 입력에는 `ISO_heat_rate_kJ_per_kWh`와 함께 연료 LHV(`fuel_LHV_kJ_per_kg`)를 제공하면 연료 질량유량을 계산해 리포트한다.

### 2.2 출력(Result Dict)

HBD Agent는 계산 후 아래 형태의 dict을 반환해야 한다:

```json
{
  "summary": {
    "GT_power_MW": 255.4,
    "ST_power_MW": 140.2,
    "AUX_load_MW": 5.0,
    "NET_power_MW": 390.6,
    "NET_eff_LHV_pct": 58.7
  },
  "gt_block": {
    "fuel_heat_input_MW_LHV": 665.0,
    "fuel_LHV_kJ_per_kg": 49000.0,
    "fuel_flow_kg_s": 13.6,
    "exhaust": {
      "temp_C": 605.0,
      "flow_kg_s": 640.0
    }
  },
  "hrsg_block": {
    "hp": {
      "steam_flow_kg_s": 120.0,
      "steam_P_bar": 120.0,
      "steam_T_C": 565.0
    },
    "ip": {
      "steam_flow_kg_s": 35.0,
      "steam_P_bar": 30.0,
      "steam_T_C": 565.0
    },
    "lp": {
      "steam_flow_kg_s": 15.0,
      "steam_P_bar": 5.0,
      "steam_T_C": 250.0
    },
    "stack_temp_C": 95.0
  },
  "st_block": {
    "hp_section": {
      "inlet_P_bar": 120.0,
      "inlet_T_C": 565.0,
      "exhaust_P_bar": 30.0,
      "power_MW": 80.0
    },
    "ip_section": {
      "inlet_P_bar": 30.0,
      "inlet_T_C": 565.0,
      "exhaust_P_bar": 5.0,
      "power_MW": 45.0
    },
    "lp_section": {
      "inlet_P_bar": 5.0,
      "inlet_T_C": 250.0,
      "exhaust_kPa_abs": 8.0,
      "power_MW": 15.2
    }
  },
  "condenser_block": {
    "cw_inlet_C": 20.0,
    "cw_outlet_C": 28.0,
    "heat_rejected_MW": 250.0
  },
  "mass_energy_balance": {
    "closure_error_pct": 0.07,
    "converged": true,
    "iterations_used": 7
  },
  "meta": {
    "input_case": "plant_case_summer_35C.json",
    "timestamp_utc": "2025-10-28T00:00:00Z",
    "solver_commit": "abcdef1234"
  }
}
```

요구사항:

- `mass_energy_balance.closure_error_pct`는 전체 질량/에너지 수지를 얼마나 맞췄는지(%)를 의미한다. 항상 0.5% 이하로 수렴시키고, 이를 넘기면 `converged`는 false.
- `meta.solver_commit`에는 현재 코드 Git commit hash를 기록해 추후 근거자료로 제시 가능하게 한다.

---

## 3. 계산 절차 규격

HBD Agent는 다음 절차를 항상 같은 순서로 수행한다.
각 단계는 별도 모듈 함수로 구현되고, 전역 mutable 상태 없이 입력→출력만 주고받는다.

1. **Step GT (Gas Turbine Block)** – 외기조건 보정 후 GT 출력, 연료 열투입(LHV 기준)과 연료 질량유량, 배기가스 조건 산출.
2. **Step HRSG (3-Pressure Heat Recovery Steam Generator)** – HP/IP/LP 증기유량을 반복 수렴.
3. **Step ST (Steam Turbine Block)** – 각 섹션에서 등엔트로피 효율을 적용해 출력 계산.
4. **Step Condenser / Feedwater Loop** – 복수기 열부하와 냉각수 조건 산출.
5. **Step Plant Summary** – Net Power, Net 효율, 질량/에너지 밸런스 집계.

---

## 4. 기본 가정 / 금지사항

### 4.1 Default Assumptions (필수 기본값)

입력 JSON에 명시가 없을 경우 다음 값을 사용한다. 이 값들은 `defaults/defaults.json`에서 로드한다.

- 스팀터빈 단별 등엔트로피 효율: 0.88
- 기계/발전기 효율: 0.985
- HRSG pinch: 10 K (HP 기준)
- HRSG approach: 5 K (HP 기준)
- 굴뚝 최소 배출온도(stack_temp_min_C): 90°C
- 복수기 진공: 8 kPa(abs)
- 순환수 입구온도: 20°C
- Aux load: 5.0 MW

### 4.2 금지사항

- 무단 추정 금지: 명시된 값 또는 기본값만 사용.
- 단위 혼동 금지: 모든 압력은 절대압. 변수명에 `_abs` 명시.
- 전역 상태 금지: 모듈들은 전역 mutable 상태를 사용하지 않는다.
- 수렴 숨김 금지: 수렴 실패 시에도 partial 결과와 실패 사유를 `meta`에 기록한다.

---

## 5. 산출물 리포트

Reporter 계층은 HBD Agent가 넘긴 dict만으로 문서를 생성한다.

1. Summary Sheet (Excel 탭 "Summary") – Net Power, GT/ST Power, Aux Load, Net 효율, Stack Temp, Condenser Vacuum.
2. Stream Table (Excel 탭 "Streams") – 주요 스트림 조건(압력/온도/유량/엔탈피).
3. Diagram SVG – GT → HRSG(HP/IP/LP) → ST(HP/IP/LP) → Condenser → Feedwater loop 흐름과 주요 값.

---

## 6. 버전 관리 / 추적성

- 결과 dict에 입력 케이스 파일명, UTC 타임스탬프, solver 코드 Git commit hash, 수렴 여부, 반복 횟수, closure_error_pct를 기록한다.
- 변경 시 `agent.md`, `README.md`, `defaults/defaults.json`을 동기화한다.

---

## 7. 보안

- Vendor 고유 성능커브와 보증 조건은 기밀. 공개 저장소에는 더미 값만 둔다.
- Reporter 산출물에는 필수 요약 정보만 포함하고 민감한 파라미터는 노출하지 않는다.

---

## 8. 결론

- 입력 JSON → 계산 → 표준화된 결과 dict → 리포트 산출 흐름을 일관성 있게 유지한다.
- 3압력 HRSG까지 포함하며, 반복 수렴과 단위 규칙을 준수한다.
- 추적성과 보안을 확보하여 조직 표준 자산으로 활용한다.
