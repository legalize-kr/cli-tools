# Changelog

## [0.2.0] — 2026-04-26

### Added

- **`SEP.py`** — `SEP = "--"` 상수 모듈 신규 추가.
  preflight 측정에서 `__` 18건·`~` 2건 침입이 확인되어 `--`(이중 hyphen) 채택.
  Python pipeline(`legalize-pipeline/precedents/converter.py`) 및
  Rust 컴파일러(`compiler-for-precedent/src/render.rs`)와 동기화.

- **복합 파일명 조회 (새 grammar)** — `legalize precedents get <사건번호>` 및
  MCP `precedents_get` 이 `*__{사건번호}.md` 패턴(composite key)을 우선 검색.
  기존 `{사건번호}.md` (legacy) 패턴은 두 번째 fallback으로 유지.

- **`--legacy-map` 옵션** — `legalize precedents get --legacy-map <path>` 로
  `legacy-paths.json` 파일을 지정하면 새/구 파일명 모두 불일치 시 매핑 테이블로
  최종 fallback 조회.

- **MCP `precedents_get`** 에 `legacy_map_path` 파라미터 추가 (선택적).

### Lookup resolution order

1. Path-looking input (`/` 포함 + `.md` 끝) → 직접 fetch
2. 새 grammar: tree에서 `*__{caseno}.md` 검색
3. Legacy fallback: tree에서 `{caseno}.md` 검색
4. `legacy-paths.json` fallback (`--legacy-map` 지정 시)

이 순서는 `precedent-kr` force-push 이전/이후 모두 동작하도록 설계되었습니다.

---

## [0.1.1] — 2026-04-18

- 내부 버전 정렬 및 패키지 메타데이터 업데이트.

## [0.1.0] — 2026-04-16

- 최초 릴리스.
