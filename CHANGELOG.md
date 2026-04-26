# Changelog

## [0.2.1] — 2026-04-26

### Changed

- **SEP `--` → `_`** (single underscore). 가독성 우선 결정으로 구분자를 변경.
  파일명 형식: `{법원명}_{선고일자}_{사건번호}.md`
  (예: `대법원_1948-04-02_4281민상298.md`).
  - `SEP.py` 의 상수가 `"_"` 로 갱신됨.
  - 합성 파일명 파싱은 좌측 anchor `split(SEP, 2)` 로 수행 (법원명에는 `_` 가
    없고 선고일자는 고정 `YYYY-MM-DD` 포맷이므로 처음 두 번의 split 이 항상
    (법원명, 선고일자) 슬롯을 분리, 잔여가 사건번호).
  - lookup pattern 도 `*__{caseno}.md` → `*_{caseno}.md` 로 자동 갱신
    (`fetch.py` 가 `SEP` 상수를 참조).
  - **호환성**: precedent-kr 가 force-push 된 후에 동작합니다. force-push
    이전 데이터에서는 legacy `{caseno}.md` fallback (조회 순서 #3) 으로 동작.

## [0.2.0] — 2026-04-26

### Added

- **`SEP.py`** — `SEP` 상수 모듈 신규 추가 (당시 값 `"--"`, 0.2.1 에서 `"_"` 로 변경).
  Python pipeline(`legalize-pipeline/precedents/converter.py`) 및
  Rust 컴파일러(`compiler-for-precedent/src/render.rs`)와 동기화.

- **복합 파일명 조회 (새 grammar)** — `legalize precedents get <사건번호>` 및
  MCP `precedents_get` 이 `*{SEP}{사건번호}.md` 패턴(composite key)을 우선 검색.
  기존 `{사건번호}.md` (legacy) 패턴은 두 번째 fallback으로 유지.

- **`--legacy-map` 옵션** — `legalize precedents get --legacy-map <path>` 로
  `legacy-paths.json` 파일을 지정하면 새/구 파일명 모두 불일치 시 매핑 테이블로
  최종 fallback 조회.

- **MCP `precedents_get`** 에 `legacy_map_path` 파라미터 추가 (선택적).

### Lookup resolution order

1. Path-looking input (`/` 포함 + `.md` 끝) → 직접 fetch
2. 새 grammar: tree에서 `*{SEP}{caseno}.md` 검색
3. Legacy fallback: tree에서 `{caseno}.md` 검색
4. `legacy-paths.json` fallback (`--legacy-map` 지정 시)

이 순서는 `precedent-kr` force-push 이전/이후 모두 동작하도록 설계되었습니다.

---

## [0.1.1] — 2026-04-18

- 내부 버전 정렬 및 패키지 메타데이터 업데이트.

## [0.1.0] — 2026-04-16

- 최초 릴리스.
