# HBD Agent Repository Guidelines

이 문서는 저장소 전반에 적용되는 개발 지침을 정의한다.

## 범위
- 이 문서는 저장소 전체에 적용된다. 더 세부적인 지침이 필요한 경우, 하위 디렉터리에 별도의 `AGENTS.md`를 추가한다.

## 개발 원칙
1. **Poetry 환경**
   - 모든 Python 의존성은 Poetry로 관리한다.
   - 새로운 패키지를 추가할 때는 `poetry add` 또는 `poetry add --group dev`를 사용하고, 잠금 파일(`poetry.lock`)을 최신 상태로 유지한다.
   - 가상환경은 `.venv/` 대신 Poetry가 관리하도록 둔다.
2. **소스 구조**
   - 실행 코드는 `src/ccpp_hbd_solver/` 하위 모듈에 두고, 테스트는 `tests/`에 둔다.
   - 공통 설정 및 정적 데이터는 `defaults/`, `data/` 등 전용 디렉터리를 사용한다.
3. **설정/기본값 처리**
   - 열수지 계산에 필요한 기본값은 `defaults/defaults.json`에서 로드하며, 갱신 시 README와 agent.md의 기본값 표를 함께 수정한다.
4. **문서화**
   - 계산 로직, 데이터 구조, I/O 계약 변경 시 README와 agent.md를 반드시 업데이트한다.
5. **품질**
   - 새로운 기능에는 가능한 한 테스트를 작성한다(`pytest`).
   - 모듈은 순수 함수 스타일을 유지하고, 전역 mutable 상태를 사용하지 않는다.

## 커밋 및 PR
- 커밋 메시지는 `<type>(<module>): <summary>` 형식을 사용한다.
- PR 설명에는 변경 요약, 테스트 결과, 관련 이슈를 포함한다.
