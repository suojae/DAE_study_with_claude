# 모델링 드릴 (Modeling Drills)

하루에 **RDB 모델링 1문제 + DW 모델링 1문제**를 푼다.

- `rdb/` — 요구사항 → ERD → 테이블(DDL). 운영 DB 설계 연습
- `dw/` — 비즈니스 질문 → 스타 스키마(fact · dim). 분석용 설계 연습

## 푸는 법 (하루 30~40분)

1. 문제의 **시나리오**와 **샘플 데이터**만 읽는다. 힌트와 답은 접어둔 채로.
2. 종이나 [dbdiagram.io](https://dbdiagram.io)에 먼저 그린다.
   - RDB: 엔티티 → 관계 → 카디널리티 → 식별자 → DDL
   - DW: 킴벌 4단계 — **① 비즈니스 프로세스 → ② grain(한 행이 뭔가) → ③ 차원 → ④ 팩트**
3. 문제 아래 **체크 질문**에 스스로 답해본다.
4. 막히면 💡 힌트, 다 그렸으면 ✅ 모범 답안을 열어 비교한다.
5. 내 풀이와 다른 점, 헷갈린 점을 `solutions/`에 남긴다. 가장 많이 배운 건 TIL 노트(`YYYY/MM/DD-*.md`)로 승격한다.

> 모범 답안은 "정답"이 아니라 **하나의 합리적인 설계**다. 내 답이 다르면 "어떤 비즈니스 규칙을 다르게 가정했나"를 적어보는 게 핵심.

## 게임 모드

[`game.html`](game.html)을 브라우저로 열면 같은 문제를 게임처럼 풀 수 있다. 바로 플레이: **https://suojae.github.io/DAE_study_with_claude/** (`main`에 `game.html`이 바뀌면 GitHub Actions가 자동 배포)

- 한 판 = 브리핑 → 퀴즈 5~7문제(객관식 · 분류 · 계산 · 버그 찾기) → **보스전**(직접 설계 후 모범 답안 체크리스트로 대조)
- 목숨은 PK 열쇠 3개, 남은 열쇠 = 별 개수. 연속 정답 콤보 XP, 레벨
- 오늘의 퀘스트: RDB 1판 + DW 1판 → 연속 기록. 틀린 문제는 오답노트에 쌓이고 복습 모드로 다시 푼다
- 진도는 브라우저 localStorage에 저장된다
- 새 문제를 추가하면 `game.html`의 `STAGES` 배열에도 한 항목 추가

## 1주 차 로드맵

| Day | RDB | 연습 개념 | DW | 연습 개념 |
|---|---|---|---|---|
| 1 | [도서관 대출](rdb/01-library-loan.md) | 1:N · M:N · Gerund, "책 vs 책 한 권" | [편의점 POS 매출](dw/01-convenience-store-sales.md) | 4단계 설계 · grain · 가산성 |
| 2 | [학원 분반](rdb/02-academy-sections.md) | Weak entity · 부분 키 · 복합 FK | [날짜 차원](dw/02-date-dimension.md) | date dim · role-playing |
| 3 | [사내 조직도](rdb/03-org-chart.md) | 재귀 관계 · 다중 관계 | [학원 출석](dw/03-attendance-factless.md) | factless fact · coverage |
| 4 | [단체 채팅방](rdb/04-group-chat.md) | 속성 있는 M:N · 복합 FK로 규칙 강제 | [창고 재고](dw/04-inventory-snapshot.md) | periodic snapshot · 반가산 |
| 5 | [병원 예약](rdb/05-clinic-booking.md) | 3항 관계 · 겹침 방지 | [주문 처리 흐름](dw/05-order-fulfillment.md) | accumulating snapshot |
| 6 | [결제 수단](rdb/06-payment-methods.md) | 슈퍼타입/서브타입 | [회원 등급 변경](dw/06-customer-scd2.md) | SCD Type 1 · Type 2 |
| 7 | [배달앱 주문](rdb/07-delivery-order.md) | 종합 · 주문 시점 스냅샷 | [공동 강의 매출](dw/07-co-instructor-bridge.md) | bridge table · 중복 집계 |

난이도는 뒤로 갈수록 올라간다. Day 7은 앞에서 배운 걸 전부 섞은 종합 문제.

## 진도

- [ ] Day 1
- [ ] Day 2
- [ ] Day 3
- [ ] Day 4
- [ ] Day 5
- [ ] Day 6
- [ ] Day 7
