# DW-01. 편의점 POS 매출 — 킴벌 4단계로 첫 스타 스키마

> 난이도 ★☆☆ · 연습 개념: 4단계 설계, grain 선언, 가산 / 비가산 팩트, degenerate dimension · 예상 25분
> 참고: 『The Data Warehouse Toolkit』 3장 Retail Sales

## 시나리오

편의점 프랜차이즈(전국 300개 점포)의 POS 데이터로 매출 분석 마트를 만든다.

POS 원천 데이터 (영수증 한 장에 여러 줄):

| 영수증번호 | 점포 | 판매시각 | 상품 | 수량 | 정가 | 할인 | 결제금액 | 행사 | 계산원 |
|---|---|---|---|---|---|---|---|---|---|
| R-1001 | 강남역점 | 11-25 08:12 | 삼각김밥 참치 | 2 | 1,200 | 0 | 2,400 | — | 직원A |
| R-1001 | 강남역점 | 11-25 08:12 | 바나나우유 | 1 | 1,700 | 200 | 1,500 | 1+1 | 직원A |
| R-1002 | 선릉역점 | 11-25 08:15 | 아메리카노 | 1 | 1,500 | 0 | 1,500 | — | 직원B |

상품 마스터에는 카테고리(대/중/소), 브랜드, **원가**가 있다. 점포 마스터에는 지역, 상권 유형(오피스 · 주거 · 대학가), 개점일이 있다.

## 현업이 묻는 질문

1. 점포별 · 일별 매출과 **매출총이익**(매출 − 원가)
2. 카테고리별 시간대(아침 · 점심 · 저녁 · 심야) 판매량
3. 1+1 행사 상품의 행사 기간 매출 vs 평소 매출
4. 오피스 상권 점포의 평일 vs 주말 매출
5. 영수증 한 장당 평균 구매 금액(객단가)

## 할 일

킴벌 4단계를 **순서대로** 적는다.

1. 비즈니스 프로세스
2. grain (팩트 테이블 한 행이 무엇인지 **한 문장으로**)
3. 차원
4. 팩트 (가산 / 반가산 / 비가산 표시)

그리고 스타 스키마를 그리고 질문 5개에 답하는 SQL 중 1번과 5번을 써본다.

## 체크 질문

- grain을 "영수증 한 장"으로 잡으면 어떤 질문에 답할 수 없나?
- 정가(단가)를 SUM하면 의미가 있나?
- 영수증번호는 차원 테이블이 필요한가?
- 판매시각을 날짜 차원 하나에 다 넣을 수 있나? (1년 × 1,440분이면 몇 행?)

<details>
<summary>💡 힌트</summary>

- grain은 **가장 잘게** 잡는다. 잘게 잡으면 위로 합칠 수 있지만, 크게 잡으면 다시 쪼갤 수 없다.
- 단가는 비가산. 저장은 하되 집계에는 `SUM(금액) / SUM(수량)`으로 다시 계산한다.
- 영수증번호처럼 속성 없이 번호만 있는 차원 = **degenerate dimension** → 팩트에 그냥 컬럼으로.
- 날짜와 시각(시간대)은 차원을 나눈다.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 4단계

1. **프로세스**: POS 판매
2. **grain**: "영수증 한 장의 상품 한 줄(POS 라인 아이템)"
3. **차원**: 날짜, 시간대, 점포, 상품, 행사, 계산원 (+ 영수증번호는 degenerate)
4. **팩트**: 수량, 정가 금액, 할인 금액, 결제 금액, 원가 금액 — 전부 **가산**

### 스타 스키마

```
              dim_date
                 │
dim_time_of_day ─┤
                 │
dim_store ───── fct_pos_sales ───── dim_product
                 │
dim_promotion ───┤
                 │
              dim_cashier
```

```sql
CREATE TABLE fct_pos_sales (
  date_key        INT    NOT NULL,   -- 20261125
  time_of_day_key INT    NOT NULL,   -- 0812 (하루 1,440분)
  store_key       INT    NOT NULL,
  product_key     INT    NOT NULL,
  promotion_key   INT    NOT NULL,   -- 행사 없음도 '행사 없음' 행으로 (NULL 금지)
  cashier_key     INT    NOT NULL,
  receipt_no      STRING NOT NULL,   -- degenerate dimension
  quantity        INT64,
  gross_amount    INT64,             -- 정가 × 수량
  discount_amount INT64,
  net_amount      INT64,             -- 결제 금액
  cost_amount     INT64              -- 원가 × 수량 (판매 시점 원가)
);

CREATE TABLE dim_product (
  product_key  INT PRIMARY KEY,      -- 대리키
  product_code STRING,               -- 원천 자연키
  name STRING, brand STRING,
  category_l STRING, category_m STRING, category_s STRING
);

CREATE TABLE dim_store (
  store_key INT PRIMARY KEY,
  store_code STRING, name STRING,
  region STRING, trade_area STRING,  -- 오피스 / 주거 / 대학가
  opened_on DATE
);

CREATE TABLE dim_time_of_day (
  time_of_day_key INT PRIMARY KEY,   -- 0000 ~ 2359
  hour INT, minute INT,
  day_part STRING                    -- 아침 / 점심 / 저녁 / 심야
);
```

### SQL

```sql
-- 1. 점포별 · 일별 매출과 매출총이익
SELECT d.full_date, s.name AS store,
       SUM(f.net_amount)                 AS sales,
       SUM(f.net_amount - f.cost_amount) AS gross_profit
FROM fct_pos_sales f
JOIN dim_date  d ON d.date_key  = f.date_key
JOIN dim_store s ON s.store_key = f.store_key
GROUP BY 1, 2;

-- 5. 객단가 = 매출 / 영수증 수
SELECT SUM(net_amount) / COUNT(DISTINCT receipt_no) AS avg_basket
FROM fct_pos_sales;
```

### 포인트

- **grain을 영수증 단위로 잡으면** 2번(카테고리별), 3번(행사 상품) 질문에 답할 수 없다. 영수증에는 상품이 여러 개라 상품 차원을 붙일 수 없다.
- **원가는 판매 시점 값을 팩트에** 넣는다. 상품 마스터의 원가는 바뀌기 때문에, 차원에서 가져오면 과거 이익이 바뀐다 (RDB-07의 스냅샷과 같은 이야기).
- 매출총이익은 따로 저장하지 않아도 `net − cost`로 계산되지만, 자주 쓰면 미리 계산해 넣어도 된다. 두 값이 **둘 다 가산**이라 차이도 가산이다.
- 이익률(%)은 **비가산**. 저장하지 말고 `SUM(이익) / SUM(매출)`로 매번 계산한다. 점포별 이익률을 평균내면 틀린다.
- 행사 없는 판매도 `promotion_key = 0 ('행사 없음')`으로 넣는다. 팩트의 FK에 NULL이 있으면 JOIN에서 행이 빠져 매출이 줄어든다.
- 객단가처럼 **영수증 단위 지표**는 `COUNT(DISTINCT receipt_no)`로 구한다. degenerate dimension이 여기서 쓰인다.

### 흔한 실수

- 영수증 총액(`receipt_total`)을 라인마다 넣음 → 영수증에 3줄이면 SUM이 3배. **grain이 다른 값을 한 테이블에 섞지 않는다.**
- 시각까지 날짜 차원에 넣어 1년에 52만 행짜리 차원을 만듦. 날짜(365행)와 시간대(1,440행)로 나누면 작고 재사용도 쉽다.

</details>
