# legalize-cli

GitHub REST API로 한국 법령·판례·행정규칙·자치법규를 조회하는 CLI — 클론 없이, 인증 없이 바로 사용.

[legalize-kr](https://github.com/legalize-kr) 미러에서 한국 법령, 법원 판례, 행정규칙, 자치법규를 직접 명령줄로 조회합니다. LLM/에이전트 소비(`--json` 지원)와 사람이 직접 탐색하는 용도 모두를 위해 설계되었습니다.

## 설치

Python 3.10+가 필요합니다.

```bash
# 권장: 한 번 설치해 계속 사용
pipx install legalize-cli

# venv 또는 CI 내부
pip install legalize-cli

# 설치 없이 바로 실행
uvx legalize-cli laws list --json
```

MCP 서버까지 사용하려면 `mcp` extra가 필요합니다.

```bash
# 설치 없이 MCP 서버 실행
uvx --from legalize-cli[mcp] legalize-mcp

# 또는 한 번 설치해 계속 사용
pipx install 'legalize-cli[mcp]'
legalize-mcp
```

AI Agent용 스킬/플러그인 설치 안내는 [`legalize-kr/agent-skills`](https://github.com/legalize-kr/agent-skills)를 참고하세요.

## AI Agent 스킬/플러그인

[`legalize-kr/agent-skills`](https://github.com/legalize-kr/agent-skills)는
Claude Code, Claude Cowork, Cursor, Codex, Gemini CLI, Cline, Warp 등에서
Legalize-KR 데이터를 더 쉽게 쓰기 위한 스킬/플러그인 저장소입니다.

- `cli-tools`: `legalize` CLI와 로컬 stdio MCP 서버(`legalize-mcp`)를 제공합니다.
- `agent-skills`: 각 AI Agent가 Legalize-KR 데이터셋, CLI, MCP, Git 저장소 접근법을 이해하도록 설치 가능한 스킬과 플러그인 메타데이터를 제공합니다.

스킬만 설치하려면:

```bash
npx skills add legalize-kr/agent-skills --skill legalize-kr
```

Claude Code 플러그인으로 설치하려면:

```bash
claude plugin marketplace add legalize-kr/agent-skills
claude plugin install legalize-kr@legalize-kr-marketplace
```

비개발자에게는 GitHub Releases에서 제공되는 `legalize-kr-plugin.zip`을
Claude Cowork에 업로드하는 경로가 가장 단순합니다. 실제 도구 호출이 필요하면
이 저장소의 `legalize-mcp`를 로컬 MCP 서버로 함께 연결합니다.

## 빠른 시작

```bash
# 법률 목록 조회 (JSON, 처음 5개)
legalize laws list --category 법률 --json | jq '.items[:5]'

# 민법 전문 조회 (2015-06-01 기준)
legalize laws get 민법 --date 2015-06-01

# 민법 특정 조문 조회
legalize laws article 민법 제839조의2 --date 2015-06-01 --json

# 민법 두 시점 비교 (조문별 변경 내역)
legalize laws diff 민법 민법 --date-a 2015-01-01 --date-b 2024-01-01 --mode article

# 법령에서 키워드 검색
legalize search "부동산 점유취득시효" --in laws --json

# 자치법규 조회
legalize ordinances list --jurisdiction 서울특별시 --type 조례 --json
```

## GitHub 토큰 설정 (Rate Limit 해결)

### 왜 필요한가?

GitHub API는 인증 없이 **시간당 60회** 요청만 허용합니다. 토큰을 사용하면 **시간당 5,000회**로 늘어납니다.

| 상태 | 요청 한도 |
|------|-----------|
| 미인증 (기본) | 60 req/hr (IP당) |
| GitHub 토큰 사용 | 5,000 req/hr |

명령당 소비 요청 수:

| 명령 | 소비 요청 수 (콜드) |
|------|---------------------|
| `laws list` | 1회 (이후 1시간 캐시) |
| `laws get <name> --date D --semantic 공포일자` | 2회 (커밋 조회 + 파일 조회) |
| `laws get <name> --semantic 시행일자` | 2회 이상 (커밋 조회 + 후보 개정본 frontmatter 조회) |
| `laws diff A B --semantic 공포일자` | 4회 (as-of 해석 2회 × 2) |
| `laws diff A B --semantic 시행일자` | 4회 이상 (각 시점의 후보 개정본 frontmatter 조회) |
| `search --heavy-content-scan` | 최대 N회 (후보 수만큼); 토큰 없으면 `--yes-exhaust-quota` 필요 |

### 토큰 발급 방법

**방법 1: GitHub CLI 사용 (가장 간단)**

```bash
# GitHub CLI 설치 후 로그인
gh auth login

# 현재 로그인된 토큰을 환경변수로 설정
export GITHUB_TOKEN=$(gh auth token)
```

**방법 2: Personal Access Token (PAT) 직접 발급**

1. [GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens) 접속
2. **"Generate new token (classic)"** 클릭
3. Note: `legalize-cli` 입력
4. 권한 선택: **`public_repo` 스코프만 체크** (공개 저장소 읽기 전용으로 충분)
5. 생성된 토큰을 복사

```bash
# 환경변수로 설정 (셸 프로파일에 추가 권장)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**방법 3: Fine-grained Personal Access Token (더 안전)**

1. [GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta) 접속
2. **"Generate new token"** 클릭
3. Repository access: **"Public Repositories (read-only)"** 선택
4. 별도 권한 추가 없이 생성

```bash
export GITHUB_TOKEN=github_pat_xxxxxxxxxxxxxxxxxxxx
```

### 토큰 적용 방법

우선순위 순서로 세 가지 방식을 지원합니다:

```bash
# 1순위: 매 명령에 직접 전달
legalize laws list --token ghp_xxxx

# 2순위: 표준 환경변수 (권장)
export GITHUB_TOKEN=ghp_xxxx
legalize laws list

# 3순위: legalize-cli 전용 환경변수
export LEGALIZE_GITHUB_TOKEN=ghp_xxxx
legalize laws list
```

셸 프로파일(`~/.bashrc`, `~/.zshrc`)에 추가하면 매번 설정할 필요가 없습니다:

```bash
echo 'export GITHUB_TOKEN=$(gh auth token)' >> ~/.zshrc
```

### 현재 인증 상태 확인

```bash
legalize auth status --json
```

출력 예시:

```json
{
  "schema_version": "1.0",
  "kind": "auth.status",
  "token_present": true,
  "token_source": "GITHUB_TOKEN",
  "token_preview": "ghp_…****",
  "rate_limit": {
    "limit": 5000,
    "remaining": 4987,
    "used": 13,
    "reset": "2024-01-15T11:00:00+09:00"
  }
}
```

## MCP 서버 (LLM/에이전트 통합)

현재 대화에 Legalize-KR MCP 도구가 이미 제공되면 로컬 설치 없이 먼저 호출합니다.
법령은 `laws_get` 또는 `laws_article`로 조회하고, 판례·행정규칙·자치법규는
검색이나 목록에서 받은 `path`를 해당 `*_get`의 `identifier`로 전달합니다.
검색 결과는 문서 후보이므로 전문을 읽기 전 본문 내용을 확정하지 않습니다.
현재 시행 중인 법령을 요청하면 `semantic="시행일자"`를 명시하고 파일 단위 제한을 밝힙니다.
자세한 예시는 [스킬의 MCP 조회 흐름](https://github.com/legalize-kr/agent-skills/blob/main/skills/legalize-kr/references/mcp-workflows.md)을 참고하세요.

Claude Desktop, Cursor 등 MCP 지원 클라이언트에 legalize-kr을 tool로 등록할 수 있습니다.

`legalize-mcp`는 로컬 stdio MCP 서버입니다. Claude Desktop, Claude Code, Cursor, Gemini CLI 같은 호스트 앱이 이 명령을 실행하고 표준입출력으로 통신합니다.

### 실행 방식 선택

```bash
# 별도 설치 없이 실행
uvx --from legalize-cli[mcp] legalize-mcp

# 격리 환경에 한 번 설치
pipx install 'legalize-cli[mcp]'

# venv 또는 CI 내부
pip install 'legalize-cli[mcp]'
```

### 제공 Tool 목록

| Tool | 설명 |
|------|------|
| `laws_list` | 법령 목록 조회 (카테고리·페이지 필터) |
| `laws_get` | 법령 전문 조회 (공포일자 또는 시행일자 기준) |
| `laws_article` | 특정 조문 조회 (제839조 등, 공포일자 또는 시행일자 기준) |
| `search` | 법령·판례·행정규칙·자치법규 키워드 검색 |
| `precedents_list` | 판례 목록 조회 (법원·사건종류 필터) |
| `precedents_get` | 판례 전문 조회 (사건번호·판례일련번호) |
| `admrules_list` | 행정규칙 목록 조회 (종류·기관 필터) |
| `admrules_get` | 행정규칙 전문 조회 |
| `ordinances_list` | 자치법규 목록 조회 (종류·지자체 필터) |
| `ordinances_get` | 자치법규 전문 조회 |

### Claude Desktop 설정

`~/Library/Application Support/Claude/claude_desktop_config.json` 에 추가:

```json
{
  "mcpServers": {
    "legalize-kr": {
      "command": "uvx",
      "args": ["--from", "legalize-cli[mcp]", "legalize-mcp"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

`pipx install 'legalize-cli[mcp]'`로 이미 설치했다면 `legalize-mcp`를 직접 실행해도 됩니다.

```json
{
  "mcpServers": {
    "legalize-kr": {
      "command": "legalize-mcp",
      "env": {
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

`legalize-mcp` 대신 `legalize mcp serve`를 사용하는 경우:

```json
{
  "mcpServers": {
    "legalize-kr": {
      "command": "legalize",
      "args": ["mcp", "serve"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

### Cursor / VS Code (MCP 설정)

`.cursor/mcp.json` 또는 `.vscode/mcp.json`:

```json
{
  "servers": {
    "legalize-kr": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "legalize-cli[mcp]", "legalize-mcp"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

### 직접 실행 (테스트용)

```bash
# stdio 서버 직접 실행
legalize mcp serve

# 또는 단축 엔트리포인트
legalize-mcp

# 설치 없이 실행 확인
uvx --from legalize-cli[mcp] legalize-mcp
```

### 사용 예시 (Claude에서)

MCP 서버 등록 후 Claude에게 자연어로 질문할 수 있습니다:

> "민법 제750조 조문을 알려줘"
> "부동산 점유취득시효 관련 판례를 검색해줘"
> "근로기준법이 2020년과 2024년 사이에 어떻게 바뀌었는지 확인해줘"

### 토큰 설정

MCP 서버는 환경변수를 자동으로 읽습니다. `env` 설정에 `GITHUB_TOKEN`을 추가하거나 시스템 환경변수로 미리 설정해두면 됩니다. 토큰 없이도 동작하지만 시간당 60회 제한이 있습니다 (토큰 사용 시 5,000회).

**토큰 발급 방법:**

```bash
# 방법 1: GitHub CLI (가장 간단)
gh auth login
export GITHUB_TOKEN=$(gh auth token)
```

GitHub CLI가 없다면 직접 발급합니다:

1. [GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens) 접속
2. **"Generate new token (classic)"** 클릭
3. 권한: **`public_repo`** 스코프만 체크 (공개 저장소 읽기 전용으로 충분)
4. 생성된 토큰을 `claude_desktop_config.json`의 `env.GITHUB_TOKEN`에 입력

더 안전한 Fine-grained token을 사용하려면 [GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta)에서 **"Public Repositories (read-only)"** 권한으로 생성합니다. 자세한 내용은 [GitHub 토큰 설정](#github-토큰-설정-rate-limit-해결) 섹션을 참고하세요.

## 명령 레퍼런스

### 날짜 기준 선택

`laws as-of`, `laws get`, `laws article`, `laws diff`와 MCP `laws_get`, `laws_article`은
`공포일자`와 `시행일자`를 모두 지원합니다. `semantic` 또는 `--semantic`의 기본값은
기존 동작과 호환되는 `공포일자`입니다.

- `공포일자`: 그 날짜까지 공포된 최신 파일 버전을 선택합니다. 선택한 파일의 시행일이
  더 뒤라면 JSON 응답의 `warning`으로 시행 전임을 알립니다.
- `시행일자`: 각 개정 파일 frontmatter의 `시행일자`가 기준일 이하인 최신 파일 버전을
  선택합니다. 시행일자가 공포일자보다 늦은 개정은 시행 전에는 선택되지 않습니다.

이 선택은 파일 단위입니다. 하나의 공포본 안에서 조문별 시행일이 다르거나 부칙의
적용례·경과조치가 있는 경우에는 개별 조문의 실제 적용 여부를 판정하지 않습니다.
`laws get`, `laws article`, MCP `laws_get`, MCP `laws_article`의
`file_effective_date_only: true`는 이 한계를 명시합니다. 1970년 이전 공포본은 Git 날짜가 1970-01-01로 보정되어 있으므로,
해당 날짜 조회에서는 frontmatter의 실제 공포일자 또는 시행일자를 사용합니다.

### `laws list` — 법령 목록 조회

```bash
legalize laws list [--category 법률|시행령|시행규칙|대통령령|all] [--page N] [--page-size M] [--json]
```

JSON 응답: `{"schema_version": "1.0", "kind": "laws.list", "total": N, "items": [{"name", "path", "category"}], ...}`

### `laws as-of` — 특정 시점 기준 법령 목록

특정 날짜에 선택되는 법령 파일을 나열합니다 (기본값: 오늘, KST).

```bash
legalize laws as-of [--date YYYY-MM-DD] [--category 법률|...] [--include-repealed] [--semantic 공포일자|시행일자] [--json]
```

### `laws get` — 법령 전문 조회

```bash
legalize laws get <법령명> [--category 법률|시행령|...] [--date YYYY-MM-DD] [--semantic 공포일자|시행일자] [--json]
```

JSON 응답: `{"schema_version": "1.0", "kind": "laws.get", "law", "semantic", "requested_date", "resolved_version_date", "resolved_commit_date", "resolved_commit_sha", "file_effective_date_only", "frontmatter", "body"}`

### `laws article` — 특정 조문 조회

```bash
legalize laws article <법령명> <조문번호> [--category X] [--date YYYY-MM-DD] [--semantic 공포일자|시행일자] [--json]
```

조문번호 형식 모두 허용: `제839조`, `839`, `839조의2`, `839-2`, `제839조의2`

JSON 응답: `{"schema_version": "1.0", "kind": "laws.article", "semantic", "requested_date", "resolved_version_date", "공포일자", "시행일자", "출처", "법령ID", "법령MST", "file_effective_date_only", "article_no", "status", "annotations", "content", "parent_structure"}`. `status`는 삭제 조문 여부이며, 시행 여부 판정은 아닙니다.

### `laws diff` — 두 버전 비교

주로 동일 법령의 시점 간 변경을 비교합니다.

```bash
legalize laws diff <법령-a> <법령-b> [--date-a D] [--date-b D] [--semantic 공포일자|시행일자] [--mode unified|side-by-side|article] [--json]
```

JSON 응답의 `a`와 `b`에는 각각 `semantic`, `resolved_version_date`,
`resolved_commit_date`, `resolved_commit_sha`가 포함됩니다.

article 모드 상태값: `modified | added | removed | renamed | whitespace-only`

### `precedents list` — 판례 목록 조회

```bash
legalize precedents list [--court 대법원|하급심] [--type 민사|형사|가사|...] [--page N] [--page-size M] [--json]
```

### `precedents get` — 판례 전문 조회

사건번호, 판례일련번호, 또는 경로로 단일 판례를 조회합니다.

```bash
legalize precedents get <사건번호|path> [--json] [--legacy-map <path>]
```

조회 순서:
1. **새 복합 파일명** (`{법원명}_{선고일자}_{사건번호}.md`) 우선 검색
2. **레거시 파일명** (`{사건번호}.md`) fallback
3. **`--legacy-map`** 지정 시 `legacy-paths.json` 매핑 테이블 최종 fallback

### `admrules list` / `admrules get` — 행정규칙 조회

```bash
legalize admrules list [--type 고시|훈령|예규|공고|...] [--agency 기관명] [--page N] [--page-size N] [--json]
legalize admrules get <행정규칙명|path> [--type X] [--agency 기관명] [--json]
```

### `ordinances list` / `ordinances get` — 자치법규 조회

```bash
legalize ordinances list [--type 조례|규칙|훈령|예규|고시|...] [--jurisdiction 광역] [--subdivision 기초|_본청|_교육청] [--json]
legalize ordinances get <자치법규명|path> [--type X] [--jurisdiction 광역] [--subdivision 기초] [--json]
```

### `search` — 키워드 검색

법령, 판례, 행정규칙, 자치법규 전체에서 키워드를 검색합니다.

```bash
legalize search <키워드> [--in laws|precedents|admrules|ordinances|all] [--strategy auto|code|tree|metadata] [--json]
```

검색 전략:
- `code`: GitHub 코드 검색 (토큰 필수, 가장 정확)
- `tree`: 토큰 없이 경로명 매칭 (빠름)
- `metadata`: 기존 호환용 별칭이며 현재는 `tree`와 동일하게 처리
- `auto`: 토큰 유무에 따라 자동 선택

### `cache info` / `cache clear` — 캐시 관리

```bash
legalize cache info [--json]
legalize cache clear [--older-than 7d] [--yes]
```

### `auth status` — 인증 상태 확인

```bash
legalize auth status [--json]
```

## 사용 예시

### 예시 1: 민법 특정 조문의 시점별 변화 추적

```bash
# 2015년과 2024년의 재산분할 관련 조문 비교
legalize laws diff 민법 민법 \
  --date-a 2015-01-01 \
  --date-b 2024-01-01 \
  --mode article \
  --json | jq '.articles[] | select(.status == "modified")'
```

### 예시 2: 조문 내용을 LLM에 투입

```bash
# 민법 제839조의2 전문을 JSON으로 가져와서 LLM 컨텍스트로 사용
legalize laws article 민법 제839조의2 --json | jq '{
  조문: .article_no,
  상태: .status,
  기준일: .resolved_commit_date,
  본문: .content
}'
```

### 예시 3: 부동산 관련 판례 검색 (토큰 없이)

```bash
# 판례 메타데이터 인덱스에서 검색 (API 비용 없음)
legalize search "부동산 점유취득시효" --in precedents --strategy metadata --json | \
  jq '.items[:5] | .[] | {사건번호: .사건번호, 법원: .법원명, 날짜: .선고일자}'
```

### 예시 4: 법령 전문 검색 (토큰 사용)

```bash
# GitHub 코드 검색으로 법령 본문에서 키워드 검색 (토큰 필수)
export GITHUB_TOKEN=$(gh auth token)
legalize search "개인정보 처리" --in laws --strategy code --json | jq '.items'
```

### 예시 5: 법령 개정 이력 탐색

```bash
# 근로기준법 현재 전문 확인
legalize laws get 근로기준법

# 5년 전 시점과 비교
legalize laws diff 근로기준법 근로기준법 \
  --date-a 2019-01-01 \
  --date-b 2024-01-01 \
  --mode unified
```

### 예시 6: 특정 날짜 기준 유효 법령 목록 (시행일자 기준)

```bash
# 2020-01-01 기준 시행 중인 법률 목록 (시행일자 기준)
legalize laws as-of --date 2020-01-01 --semantic 시행일자 --category 법률 --json | \
  jq '.items | length'
```

### 예시 7: 공포 후 시행 전과 시행일 기준 선택

```bash
# 2026-03-01 공포, 2026-07-01 시행 파일을 2026-04-01에 확인하면 warning이 포함됩니다.
legalize laws article 예시법 1 --date 2026-04-01 --semantic 공포일자 --json

# 그 날짜에 시행 중인 파일 버전을 선택합니다.
legalize laws article 예시법 1 --date 2026-04-01 --semantic 시행일자 --json
```

### 예시 8: 오프라인 모드 (네트워크 없이 캐시 조회)

```bash
# 캐시된 데이터만 사용 (네트워크 차단 환경에서 유용)
legalize laws get 민법 --offline
legalize search "손해배상" --in precedents --offline --json
```

### 예시 9: 판례 전문 조회

```bash
# 대법원 판례 목록에서 민사 판례 5개 확인
legalize precedents list --court 대법원 --type 민사 --page-size 5 --json

# 사건번호로 특정 판례 조회
legalize precedents get "2022다12345" --json
```

### 예시 10: 행정규칙·자치법규 조회

```bash
legalize admrules list --agency 행정안전부 --type 고시 --page-size 5 --json
legalize ordinances get "서울특별시 테스트 조례" --type 조례 --jurisdiction 서울특별시 --json
```

### 예시 11: CI/CD에서 사용 (GitHub Actions)

```yaml
# .github/workflows/law-check.yml
- name: 법령 최신 상태 확인
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    uvx legalize-cli laws get 개인정보보호법 --json > current-law.json
```

### 예시 12: 캐시 워밍 (대량 조회 전 준비)

```bash
# 자주 사용하는 법령 미리 캐시
for law in 민법 형법 상법 근로기준법 개인정보보호법; do
  legalize laws get "$law" > /dev/null
  echo "$law 캐시 완료"
done
```

## 전역 플래그

| 플래그 | 설명 |
|--------|------|
| `--json` | 기계가 읽기 쉬운 JSON 출력 (안정적 스키마) |
| `--token <t>` | `$GITHUB_TOKEN` 환경변수를 직접 덮어씀 |
| `--no-cache` | 디스크 캐시 우회 |
| `--cache-dir <p>` | 캐시 디렉터리 경로 직접 지정 |
| `--offline` | 네트워크 호출 거부; 캐시만 읽음 |
| `-v` / `-vv` | stderr에 로그 상세도 증가 |

## JSON 스키마 버전 관리

모든 `--json` 출력에 `"schema_version": "1.0"`이 포함됩니다.

- **마이너 버전 증가** (1.0 → 1.1): 필드 추가만 — 1.x 소비자는 계속 동작
- **메이저 버전 증가** (1.0 → 2.0): 파괴적 변경

CI에서 `tests/unit/test_json_schema_version.py`로 강제 검증합니다.

## 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 일반 오류 |
| 4 | 해당 날짜에 없음 |
| 5 | 불명확한 헤딩 레벨 (파서) |
| 6 | upstream force-push로 인한 캐시 일관성 오류 |
| 7 | Rate limit 초과 / 인증 필요 |
| 8 | 인증 오류 |
| 9 | 오프라인 모드이나 네트워크 필요 |
| 10 | 파서 오류 |

## 캐시

위치: `~/.cache/legalize-cli/` (`$XDG_CACHE_HOME/legalize-cli/` 또는 `$LEGALIZE_CLI_CACHE_DIR`로 변경 가능)

| 서브디렉터리 | TTL | 내용 |
|-------------|-----|------|
| `trees/` | 1시간 | 저장소 트리 목록 |
| `commits/` | 10분 | 경로별 커밋 목록 |
| `contents/` | 7일 | 법령/판례/행정규칙/자치법규 마크다운 (경로 + author_date 키) |
| `precedent-index/` | 24시간 | precedent-kr/metadata.json (~34MB) |
| `search/` | 1시간 | 코드 검색 결과 |
| `etag/` | 7일 | 조건부 재검증용 ETag 본문 |

## Force-push 안전성

`legalize-kr`, `precedent-kr`, `admrule-kr`, `ordinance-kr` 저장소는 파이프라인이 이력을 재구성할 때 주기적으로 force-push될 수 있습니다. 이 도구는 캐시 데이터를 커밋 SHA가 아닌 `(path, author_date)` 기준으로 주소를 지정합니다. 경로별 핑거프린트가 재빌드 후 콘텐츠 변경을 감지하고 오래된 캐시 항목을 자동으로 무효화합니다.

## 문제 해결

**"legalize-mcp: command not found"**
```bash
# 설치 없이 실행할 수 있는지 먼저 확인
uvx --from legalize-cli[mcp] legalize-mcp

# 계속 사용할 환경이라면 설치
pipx install 'legalize-cli[mcp]'
```

**"Rate limit exceeded"**
```bash
export GITHUB_TOKEN=$(gh auth token)
# 또는 GitHub에서 PAT 발급 후:
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**"Code search requires authentication"**
```bash
# 토큰 없이 검색하려면 전략을 명시적으로 지정
legalize search "키워드" --strategy tree        # 경로명 매칭
legalize search "키워드" --strategy metadata     # 판례 인덱스만
```

**오래된 캐시**
```bash
legalize cache clear
# 또는 특정 기간 이전 캐시만 삭제
legalize cache clear --older-than 1d --yes
```

## 개발자 가이드

### 테스트 실행

```bash
cd cli-tools
pip install -e ".[dev]"
pytest
```

### 카세트 재녹화

테스트는 실제 GitHub API를 매번 호출하지 않고 `tests/fixtures/`의 JSON·Markdown 픽스처와 `httpx.MockTransport`를 사용합니다. API 응답 형식이 바뀌거나 새 테스트 케이스를 추가할 때 실제 네트워크로 라이브 테스트를 실행해 픽스처를 갱신합니다.

```bash
LEGALIZE_CLI_LIVE=1 ./scripts/record-cassettes.sh
```

라이브 테스트만 별도로 실행하려면:

```bash
LEGALIZE_CLI_LIVE=1 pytest tests/live/
```

### 의존성

| 패키지 | 용도 |
|--------|------|
| `typer` | CLI 프레임워크 |
| `httpx` | HTTP 클라이언트 |
| `pydantic` | 데이터 검증 |
| `PyYAML` | frontmatter 파싱 |
| `regex` | 한국어 조문 번호 파싱 |
| `python-dateutil` | 날짜 파싱 |

## 라이선스

- 법령/판례/행정규칙/자치법규 텍스트: 공개 도메인 (대한민국 정부 저작물)
- 이 도구: MIT
