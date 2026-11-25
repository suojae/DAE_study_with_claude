# RDB-06. 결제 수단 — 비슷하지만 조금씩 다른 것들

> 난이도 ★★☆ · 연습 개념: 슈퍼타입/서브타입(17강 계층), 테이블로 옮기는 3가지 방법 · 예상 30분

## 시나리오

쇼핑몰의 결제 수단 관리 기능이다.

- 회원은 결제 수단을 여러 개 등록한다. 종류는 세 가지.
  - **카드**: 카드사, 카드번호 끝 4자리, 유효기간(월/연), PG 결제 토큰
  - **계좌**: 은행, 계좌번호 끝 4자리, 예금주명, 자동이체 동의 일시
  - **간편결제**: 제공사(카카오페이 · 네이버페이 · 토스페이), 연동 토큰
- 공통 정보: 별칭("회사 카드"), 등록일, 삭제 여부
- 회원마다 **기본 결제 수단은 최대 1개**.
- 주문 하나를 **여러 결제 수단으로 나눠 낼 수 있다** (예: 포인트 3,000원 + 카드 27,000원). 결제 건마다 금액, 결제 시각, 승인번호를 기록한다.
- 결제 수단을 삭제해도 **과거 결제 기록은 남아야 한다.**

## 할 일

1. 슈퍼타입 / 서브타입을 찾는다.
2. 테이블로 옮기는 세 가지 방법을 각각 스케치한다.
   - (A) 테이블 하나에 전부 (single table)
   - (B) 공통 테이블 + 종류별 테이블 (table per type)
   - (C) 종류별 테이블만 (table per concrete class)
3. 하나를 고르고 DDL을 쓴다.
4. "기본 결제 수단은 최대 1개"를 DB로 강제한다.

## 체크 질문

- (C)를 고르면 `payment.payment_method_id`는 어느 테이블을 가리켜야 하나?
- (A)를 고르면 카드에 `bank_name`이 들어가는 걸 어떻게 막나?
- 카드번호 전체를 저장해도 되나?

<details>
<summary>💡 힌트</summary>

- 결제(`payment`)가 "결제 수단"을 **종류에 상관없이** 참조해야 한다 → 공통 부모가 있으면 FK 하나로 끝난다.
- 서브타입이 슈퍼타입의 PK를 **그대로 자기 PK로** 쓰면 1:1이 보장된다 (식별 관계).
- 카드번호 원문은 PCI-DSS 대상이다. 서비스 DB에는 PG가 준 토큰과 끝 4자리만.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 세 가지 비교

| | (A) single table | (B) table per type | (C) concrete only |
|---|---|---|---|
| 테이블 | `payment_method` 1개 | 공통 1 + 종류별 3 | 종류별 3 |
| 결제의 FK | 하나 | 하나 (공통 테이블) | **셋 중 하나** → FK 불가 |
| 종류별 NOT NULL | CHECK로 복잡하게 | 컬럼마다 그대로 | 그대로 |
| 전체 목록 조회 | 쉬움 | JOIN 필요 | UNION 필요 |
| 종류 추가 | 컬럼 추가 (NULL 증가) | 테이블 추가 | 테이블 추가 + 결제 FK 문제 |

결제가 "아무 결제 수단이나" 참조해야 하므로 (C)는 탈락. 종류별 속성이 서로 많이 달라서 (A)는 NULL 투성이가 된다 → **(B)**.

### DDL (B)

```sql
CREATE TABLE payment_method (                    -- 슈퍼타입
  payment_method_id BIGSERIAL PRIMARY KEY,
  member_id         BIGINT NOT NULL,
  method_type       TEXT   NOT NULL CHECK (method_type IN ('card', 'account', 'easy_pay')),
  nickname          TEXT,
  is_default        BOOLEAN NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at        TIMESTAMPTZ,                 -- 소프트 삭제: 과거 결제가 참조 중
  UNIQUE (payment_method_id, method_type)        -- 서브타입이 종류까지 함께 참조하도록
);

-- 회원마다 (삭제 안 된) 기본 결제 수단은 최대 1개
CREATE UNIQUE INDEX uq_default_method
  ON payment_method (member_id)
  WHERE is_default AND deleted_at IS NULL;

CREATE TABLE card_method (                       -- 서브타입: 부모 PK = 자기 PK (1:1)
  payment_method_id BIGINT PRIMARY KEY,
  method_type       TEXT NOT NULL DEFAULT 'card' CHECK (method_type = 'card'),
  issuer            TEXT NOT NULL,
  last4             CHAR(4) NOT NULL,
  exp_month         SMALLINT NOT NULL CHECK (exp_month BETWEEN 1 AND 12),
  exp_year          SMALLINT NOT NULL,
  pg_token          TEXT NOT NULL,               -- 카드번호 원문 대신 PG 토큰
  FOREIGN KEY (payment_method_id, method_type)
    REFERENCES payment_method(payment_method_id, method_type)
);

CREATE TABLE account_method (
  payment_method_id BIGINT PRIMARY KEY,
  method_type       TEXT NOT NULL DEFAULT 'account' CHECK (method_type = 'account'),
  bank_code         TEXT NOT NULL,
  last4             CHAR(4) NOT NULL,
  holder_name       TEXT NOT NULL,
  consented_at      TIMESTAMPTZ NOT NULL,
  FOREIGN KEY (payment_method_id, method_type)
    REFERENCES payment_method(payment_method_id, method_type)
);

CREATE TABLE easy_pay_method (
  payment_method_id BIGINT PRIMARY KEY,
  method_type       TEXT NOT NULL DEFAULT 'easy_pay' CHECK (method_type = 'easy_pay'),
  provider          TEXT NOT NULL CHECK (provider IN ('kakaopay', 'naverpay', 'tosspay')),
  link_token        TEXT NOT NULL,
  FOREIGN KEY (payment_method_id, method_type)
    REFERENCES payment_method(payment_method_id, method_type)
);

CREATE TABLE payment (                           -- 주문 1 : 결제 N (분할 결제)
  payment_id        BIGSERIAL PRIMARY KEY,
  order_id          BIGINT NOT NULL,
  payment_method_id BIGINT REFERENCES payment_method(payment_method_id), -- 포인트 결제는 NULL
  point_used        BOOLEAN NOT NULL DEFAULT FALSE,
  amount            INT    NOT NULL CHECK (amount > 0),
  paid_at           TIMESTAMPTZ NOT NULL,
  approval_no       TEXT,
  CHECK (point_used OR payment_method_id IS NOT NULL)
);
```

### 포인트

- **`(id, method_type)` 복합 FK 트릭**: 서브타입 테이블에 `method_type`을 상수 CHECK로 박고 부모의 `(id, type)`을 참조하면, `method_type = 'card'`인 부모에 계좌 행이 붙는 걸 DB가 막는다. 슈퍼타입/서브타입의 **배타성**(한 결제 수단은 한 종류)을 지키는 방법.
- 결제 수단을 지우면 `payment`가 참조하는 행이 사라지니 **소프트 삭제**(`deleted_at`). 기본 결제 수단 UNIQUE에도 `deleted_at IS NULL` 조건을 넣어서, 삭제된 기본 수단이 새 기본 수단 등록을 막지 않게 한다.
- 포인트는 "등록하는 결제 수단"이 아니라서 서브타입으로 만들지 않았다. 모든 걸 계층에 억지로 넣지 않기.

### 흔한 실수

- (A)를 고르고 `card_last4`, `bank_last4`, `easy_pay_provider` … 컬럼을 계속 늘림 → 새 종류(해외카드, 상품권)가 생길 때마다 테이블이 비대해진다.
- 결제 기록이 결제 수단을 FK로만 참조 → 나중에 카드를 교체하면 "그때 어떤 카드였나"가 바뀌어 보일 수 있다. 결제 시점의 `last4`, 카드사를 `payment`에 **스냅샷**으로 남기는 것도 고려 (RDB-07에서 다시 나옴).

</details>
