# Changelog

## [0.5.0] - 2026-10-07

### Breaking Changes (local MCP only)

- MCP 응답을 2.0 typed 구조(`version`, `source`, `warnings`, 검색 outcomes)로
  변경하고 오류를 `isError: true`로 구분합니다. CLI JSON 1.0은 유지합니다.
- MCP `precedents_get.legacy_map_path`를 제거했습니다. 명시적 code 검색은
  자동 tree 폴백을 하지 않습니다. MCP 입력·호출·응답 제한을 적용합니다.

### Added

- `laws_diff` MCP 도구와 11개 도구의 output schema, snapshot 출처,
  검색 부분 실패·경로 검색 범위, KST 기본 날짜를 추가했습니다.
- Python MCP SDK 2.2 이상, 3 미만을 사용합니다. 로컬 stdio 진입점은 유지합니다.

### Fixed

- Read disambiguated law filenames and require a choice for duplicate law names.
- Accept returned law paths and dated precedent filenames.
- Exclude sections from an earlier chapter in article parent headings.

## [0.4.0] — 2026-09-05

### Breaking Changes

- 기존 `laws as-of`, `laws get`의 `--semantic 시행일자`와 대응 MCP 호출은
  공포일자 결과로 조용히 폴백했습니다. 이제 파일 frontmatter의 시행일자를 기준으로
  실제 선택하므로, 같은 요청이 다른 개정본을 반환할 수 있습니다. 기존 공포일자 선택이
  필요한 자동화는 `--semantic 공포일자` 또는 `semantic="공포일자"`를 명시하세요.
- Python API `resolve_as_of(..., semantic="시행일자")`는 더 이상 공포일자 결과를
  반환하지 않고 오류를 냅니다. frontmatter를 제공하는
  `resolve_as_of_with_frontmatter()`를 사용해야 합니다.

### Added

- `laws as-of`, `laws get`, `laws article`, `laws diff`와 MCP `laws_get`, `laws_article`이
  `공포일자`와 `시행일자` 기준을 모두 지원합니다. `시행일자`는 각 개정 파일의
  frontmatter를 읽어 실제로 선택하며, 더 이상 공포일자 선택으로 폴백하지 않습니다.
- MCP와 CLI JSON 응답에 `semantic`, `requested_date`, `resolved_version_date`,
  선택 commit SHA를 추가했습니다. `laws_article`은 공포일자, 시행일자, 출처,
  법령ID, 법령MST도 한 번에 반환합니다.
- 1970년 이전 날짜 조회에서는 Git의 epoch 보정 날짜 대신 frontmatter의 실제
  공포일자 또는 시행일자를 사용합니다.

### Changed

- 기본 `semantic`은 `공포일자`로 유지됩니다. 시행일자 선택은 파일 단위이며 조문별
  시행일, 부칙의 적용례와 경과조치는 판정하지 않습니다.
- `legalize-cli[mcp]`가 FastMCP 기반 서버와 호환되는 MCP SDK 1.x를 설치하도록
  `mcp<2` 상한을 명시했습니다.

## [0.3.3] — 2026-07-01

### Changed

- MIT 단일 라이선스를 `MIT OR Apache-2.0` 듀얼 라이선스로 변경했습니다.
  `LICENSE`를 `LICENSE-MIT`와 `LICENSE-APACHE`로 나누고, `pyproject.toml`
  메타데이터를 PEP 639 SPDX 표현식(`license`, `license-files`)으로 전환했습니다.

## [0.3.2] — 2026-06-05

### Fixed

- MCP `laws_get` 응답에서 법령 frontmatter의 `공포일자`/`시행일자`가
  `datetime.date` 객체로 남아 JSON 직렬화에 실패하던 문제를 수정했습니다.

### Changed

- `ruff check .`와 `pyright .`가 로컬 개발 환경에서 그대로 통과하도록
  미사용 import와 pyright 설정을 정리했습니다.

## [0.3.1] — 2026-05-08

### Fixed

- GitHub Trees API의 `truncated: true` 응답을 감지하면 하위 tree를 나누어
  다시 조회하도록 수정했습니다. 이로써 `ordinance-kr`의 `서울특별시` 자치법규와
  `precedent-kr`의 뒤쪽 사건종류가 누락되던 문제를 해결했습니다.
- GitHub commits API pagination을 끝까지 따라가도록 수정해 법령 개정 이력 조회가
  첫 페이지만 사용하는 부분 결과가 되지 않도록 했습니다.
- GitHub code search의 pagination을 `--limit` 범위까지 처리하고,
  `incomplete_results=true` 응답에서는 tree 전략으로 fallback하도록 수정했습니다.

### Changed

- README의 MCP 설정 예시를 `uvx --from legalize-cli[mcp] legalize-mcp`
  중심으로 정리하고, `pipx`/`pip` 설치 흐름을 보조 경로로 명확히 구분했습니다.
- 패키지 메타데이터의 author와 GitHub 저장소 URL을 현재 관리 정보에 맞게 갱신했습니다.
- GitHub Contents/Blobs API 크기 제한 설명을 공식 문서 기준에 맞게 정정했습니다.

## [0.3.0] — 2026-05-05

### Added

- `legalize admrules list|get` 명령을 추가해 `legalize-kr/admrule-kr`
  행정규칙 저장소를 조회합니다.
- `legalize ordinances list|get` 명령을 추가해 `legalize-kr/ordinance-kr`
  자치법규 저장소를 조회합니다.
- `legalize search --in admrules|ordinances|all` 및 MCP
  `admrules_*`, `ordinances_*` 도구를 추가했습니다.

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
