# RDB-07. 배달앱 주문 — 종합 문제

> 난이도 ★★★ · 연습 개념: 지금까지 전부 + 주문 시점 스냅샷, 상태 이력 · 예상 40분

## 시나리오

배달앱의 가게 · 메뉴 · 주문 · 리뷰를 설계한다.

**가게와 메뉴**
- 가게는 이름, 주소, 최소 주문 금액, 영업 상태가 있다.
- 메뉴는 가게에 속하고, 메뉴 카테고리(대표 메뉴 · 사이드 · 음료)로 묶인다. 가격과 판매 상태가 있다.
- 메뉴마다 **옵션 그룹**이 있다. 그룹마다 최소 · 최대 선택 개수가 있다.
  - "맛 선택" — 필수, 정확히 1개 (순한맛 / 매운맛)
  - "토핑 추가" — 선택, 0~3개 (치즈 +1,000 / 계란 +500 / 떡 +1,000)
- 사장님은 메뉴 가격과 이름을 **언제든 바꾼다.**

**주문**
- 고객이 가게 하나에 주문한다. 배달 주소, 요청사항, 주문 상태가 있다.
- 주문에는 메뉴 여러 개, 메뉴마다 수량과 선택한 옵션들이 있다.
- 상태: 접수 → 조리 중 → 배달 중 → 완료 (중간에 취소 가능). **상태가 바뀐 시각을 전부** 남긴다.

**리뷰**
- 완료된 주문에 리뷰를 **최대 1개** 쓴다. 별점(1~5), 내용, 사진 여러 장.
- 사장님은 리뷰에 **답글을 최대 1개** 단다.

## 할 일

1. 전체 ERD를 그린다. 각 관계에 카디널리티와 필수/선택을 표시한다.
2. 이번 주에 연습한 개념이 어디에 쓰였는지 표시한다 (Weak? Gerund? 재귀? 계층?).
3. 핵심 테이블 DDL을 쓴다.
4. "3개월 전 주문 내역을 열었는데 지금 가격이 보이는" 버그가 나지 않게 설계한다.

## 체크 질문

- 주문상품이 `menu_id`만 들고 있으면, 사장님이 가격을 올린 뒤 과거 주문 금액은 어떻게 보이나?
- 배달 주소를 `customer.address`에서 JOIN해서 보여주면 무슨 문제가 생기나?
- "주문 1 : 리뷰 최대 1"을 어떻게 강제하나?
- 옵션 그룹의 "최소 1, 최대 1"은 DB 제약으로 걸 수 있나?

<details>
<summary>💡 힌트</summary>

- **주문은 계약서다.** 계약 시점의 이름 · 가격 · 주소를 주문 쪽에 복사(스냅샷)한다. 원본 FK는 분석용으로 같이 남긴다.
- 상태 이력 = 주문 1 : 상태 변경 N. 현재 상태는 주문 테이블에 캐시로 두면 조회가 편하다.
- 1:1 선택 관계는 자식 쪽 FK에 UNIQUE.
- "옵션을 정확히 1개 골랐나"는 여러 행에 걸친 규칙이라 CHECK로는 어렵다 → 앱 로직.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 개념 지도

| 테이블 | 이번 주 개념 |
|---|---|
| `menu`, `option_group`, `option_item` | 1:N 사슬. `option_item`은 그룹 없이 의미가 없음 (존재 종속) |
| `order_item` | 주문 ↔ 메뉴 M:N을 푸는 Gerund (수량 · 당시 가격) |
| `order_item_option` | 주문상품 ↔ 옵션 M:N을 푸는 Gerund |
| `order_status_history` | 주문 1 : 이력 N, Weak 성격 (주문 없이는 의미 없음) |
| `review` – `owner_reply` | 1:1 선택 관계 두 단계 |
| `review_photo` | 리뷰의 다중값 속성 → 별도 테이블 |

### DDL (핵심)

```sql
CREATE TABLE store (
  store_id      BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  address       TEXT NOT NULL,
  min_order_amt INT  NOT NULL DEFAULT 0
);

CREATE TABLE menu (
  menu_id   BIGSERIAL PRIMARY KEY,
  store_id  BIGINT NOT NULL REFERENCES store(store_id),
  category  TEXT   NOT NULL,
  name      TEXT   NOT NULL,
  price     INT    NOT NULL CHECK (price >= 0),
  on_sale   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE option_group (
  option_group_id BIGSERIAL PRIMARY KEY,
  menu_id         BIGINT   NOT NULL REFERENCES menu(menu_id),
  name            TEXT     NOT NULL,
  min_select      SMALLINT NOT NULL DEFAULT 0,
  max_select      SMALLINT NOT NULL,
  CHECK (min_select >= 0 AND max_select >= min_select)
);

CREATE TABLE option_item (
  option_item_id  BIGSERIAL PRIMARY KEY,
  option_group_id BIGINT NOT NULL REFERENCES option_group(option_group_id),
  name            TEXT   NOT NULL,
  extra_price     INT    NOT NULL DEFAULT 0
);

CREATE TABLE customer_order (                 -- order는 예약어라 피함
  order_id        BIGSERIAL PRIMARY KEY,
  customer_id     BIGINT NOT NULL,
  store_id        BIGINT NOT NULL REFERENCES store(store_id),
  -- 스냅샷: 주문 시점의 값을 복사
  store_name      TEXT   NOT NULL,
  delivery_addr   TEXT   NOT NULL,
  request_note    TEXT,
  total_amount    INT    NOT NULL,
  status          TEXT   NOT NULL DEFAULT 'received'
                    CHECK (status IN ('received','cooking','delivering','done','cancelled')),
  ordered_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_item (
  order_item_id BIGSERIAL PRIMARY KEY,
  order_id      BIGINT NOT NULL REFERENCES customer_order(order_id),
  menu_id       BIGINT REFERENCES menu(menu_id),     -- 원본 참조 (메뉴가 지워지면 NULL 가능)
  menu_name     TEXT   NOT NULL,                     -- 스냅샷
  unit_price    INT    NOT NULL,                     -- 스냅샷: 주문 당시 가격
  quantity      INT    NOT NULL CHECK (quantity > 0)
);

CREATE TABLE order_item_option (
  order_item_id  BIGINT NOT NULL REFERENCES order_item(order_item_id),
  option_item_id BIGINT NOT NULL REFERENCES option_item(option_item_id),
  option_name    TEXT   NOT NULL,                    -- 스냅샷
  extra_price    INT    NOT NULL,                    -- 스냅샷
  PRIMARY KEY (order_item_id, option_item_id)
);

CREATE TABLE order_status_history (
  order_id   BIGINT NOT NULL REFERENCES customer_order(order_id),
  status     TEXT   NOT NULL,
  changed_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (order_id, changed_at)
);

CREATE TABLE review (
  review_id  BIGSERIAL PRIMARY KEY,
  order_id   BIGINT NOT NULL UNIQUE REFERENCES customer_order(order_id),  -- 주문당 최대 1개
  rating     SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  body       TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE review_photo (
  review_id BIGINT   NOT NULL REFERENCES review(review_id),
  seq       SMALLINT NOT NULL,
  url       TEXT     NOT NULL,
  PRIMARY KEY (review_id, seq)
);

CREATE TABLE owner_reply (
  review_id  BIGINT PRIMARY KEY REFERENCES review(review_id),  -- PK = FK → 리뷰당 최대 1개
  body       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 포인트

- **스냅샷 vs 참조.** `menu`는 "지금" 상태, `order_item`은 "그때" 상태다. 주문 화면 · 영수증 · 정산은 스냅샷을 쓰고, "메뉴별 판매량" 같은 분석은 `menu_id`를 쓴다. 두 개를 **같이** 남긴다.
- 이 감각이 그대로 DW로 이어진다. DW에서 "그때 기준"으로 분석하려고 만드는 게 **SCD Type 2**(DW-06)다.
- `owner_reply`처럼 **PK를 FK로 쓰면** 1:1이 자동으로 보장된다. `review.order_id UNIQUE`도 같은 효과.
- `status`(현재)와 `order_status_history`(이력)를 둘 다 두는 건 의도된 중복이다. 둘이 어긋나지 않게 **같은 트랜잭션에서** 갱신한다.
- 옵션 그룹의 최소/최대 선택은 여러 행을 세야 하는 규칙이라 앱 로직에서 검증한다. 모델에는 `min_select`, `max_select`로 **규칙 자체를 데이터로** 남겨둔다.

### 흔한 실수

- 주문 금액을 저장하지 않고 매번 `메뉴 가격 × 수량`으로 계산 → 가격이 바뀌면 과거 매출이 바뀐다. 정산 데이터가 틀어지는 대표 원인.
- 옵션을 `order_item.options JSON`으로만 저장 → 당장은 편하지만 "치즈 토핑이 몇 번 팔렸나" 분석이 어려워진다. JSON으로 둘 거라면 분석 파이프라인에서 풀어줄 계획이 있어야 한다.

</details>
