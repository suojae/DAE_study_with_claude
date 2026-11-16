# 지표 봇이 데이터를 못 찾던 문제 — MCP 서버 자기소개 개선

> 2026-11 · 사내 지표 조회 MCP 서버 + Slack 봇(Hermes Agent)
> 관련 TIL: [트러블슈팅 노트](../../2026/11/16-hermes-slack-bot-mcp-troubleshooting.md)

## 한 줄 요약

봇에게 "어제 DAU"를 물으면 **지표 서버를 두고도 "어떤 데이터 소스요?"라고 되물었다.** 원인은 봇이 아니라 서버의 자기소개에 **다루는 데이터 범위**가 없던 것이었다. 서버가 Cube 메타데이터에서 범위를 읽어 자기소개에 싣게 바꿨다.

## AS-IS / TO-BE

| AS-IS | TO-BE |
|---|---|
| ![AS-IS 대화](images/01-asis-chat.png) | ![TO-BE 대화](images/02-tobe-chat.png) |
| 도구를 부르지 않고 데이터 소스를 되물음 | `list_metrics` → `query` 호출 후 숫자로 답함 |

### 왜 달라졌나 — 봇이 받는 서버 소개 글

| AS-IS | TO-BE |
|---|---|
| ![AS-IS 소개 글](images/03-asis-instructions.png) | ![TO-BE 소개 글](images/04-tobe-instructions.png) |
| "지표 조회 도구다" + 조회 규칙뿐 | 맨 앞에 `다루는 데이터 — 방문: 유저 수, …` 목록 |

## 문제 → 원인 → 해결

```mermaid
flowchart LR
    P["❓ 어제 DAU?"] --> A{"서버 소개만 보고<br/>DAU가 여기 있는지<br/>알 수 있나?"}
    A -- "AS-IS ❌" --> X["되물음"]
    A -- "TO-BE ✅" --> Y["list_metrics → query"]
```

| 단계 | 내용 |
|---|---|
| 증상 | 지표를 물으면 MCP 도구를 안 부르고 데이터 소스를 되물음 |
| 잘못 짚은 첫 대응 | 봇 쪽 지침(SOUL.md)에 조회 절차를 길게 적음 → 서버 지침과 중복, 문구가 이미 어긋남 |
| 원인 | MCP 클라이언트는 서버의 `instructions`와 도구 `description`만 보고 호출 여부를 정함. 거기에 데이터 범위가 없었음. 지표 정의(Cube description)는 도구를 부른 **뒤에야** 읽힘 |
| 해결 | `initialize`·`tools/list` 요청마다 서버가 Cube `/meta`를 읽어 cube·measure 제목 목록을 소개 글 앞에 붙임 |

## 설계 판단

| 판단 | 이유 |
|---|---|
| 범위를 코드에 고정하지 않고 Cube에서 자동 생성 | 손으로 적으면 지표가 추가·변경될 때마다 낡음 |
| 지표 **이름만** 싣고 정의는 뺌 | 소개 글이 길어지고 정의가 두 곳에 생김 — 정의는 `list_metrics`에서 |
| `instructions`와 `list_metrics` 설명 두 곳에 | `instructions`를 LLM에 넘기지 않는 클라이언트도 있음 |
| Cube 장애 시 범위 없이 예전 소개로 응답 | 서버 소개가 Cube 때문에 실패하면 안 됨 — 경고 로그만 남김 |
| 봇 쪽 지침은 역할만 남김 | 모든 클라이언트가 읽는 곳(서버)에 정보를 둬야 한 곳만 고침 |

**트레이드오프:** 연결마다 Cube 호출이 1회 늘고, 그 호출에 타임아웃이 없음 → Cube가 느리면 연결도 느려짐.

## 결과

- 단위·통합 테스트 추가 10개, 변경 3개 (전체 970개 통과)
- 결정 기록(ADR) 작성
- 효과: _재배포 후 TO-BE 캡처와 함께 기록_

---

## 📸 촬영 체크리스트 (다 찍으면 이 섹션 삭제)

- [ ] SOUL.md를 역할만 남게 줄인다 (AS-IS·TO-BE 조건을 같게)
- [ ] **재배포 전** 새 대화에서 `어제 일별 활성 사용자 수 알려줘` → `images/01-asis-chat.png`
- [x] AS-IS 서버 소개 글 → `images/03-asis-instructions.png`
- [ ] PR 머지·재배포
- [ ] 같은 질문 → `images/02-tobe-chat.png`
- [ ] TO-BE 서버 소개 글 → 실제 응답을 `images/04-tobe-instructions.json`(`{"instructions","list_metrics"}`)으로 저장 후 `python3 render_instructions.py images/04-tobe-instructions.json TO-BE images/04-tobe-instructions.png`
- [ ] 🔒 프롬프트의 사용자@호스트·IP·이메일·사내 도메인 가리기 (`export PS1='$ '`)
- [ ] 두 캡처의 창 크기·글자 크기 맞추기
