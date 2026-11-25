# DW-02. 날짜 차원 — 가장 지루하고 가장 많이 쓰는 테이블

> 난이도 ★☆☆ · 연습 개념: date dimension 속성 설계, role-playing dimension · 예상 20분
> 참고: 『The Data Warehouse Toolkit』 3장 Calendar Date Dimension, 6장 Role-Playing Dimensions

## 시나리오

온라인 쇼핑몰 주문 분석 마트에서 쓸 날짜 차원을 만든다. 주문 한 건(주문 라인)에는 날짜가 **세 개** 있다.

| 주문번호 | 상품 | 주문일 | 결제일 | 배송완료일 | 금액 |
|---|---|---|---|---|---|
| O-1 | 패딩 | 2026-12-31 | 2026-12-31 | 2027-01-03 | 129,000 |
| O-2 | 머플러 | 2027-02-16 | 2027-02-17 | 2027-02-20 | 25,000 |

현업 질문:

1. 주말 주문 비중은?
2. 설 연휴 기간 주문량은 평소의 몇 배?
3. "주문은 12월, 배송완료는 1월"인 주문은 몇 건? 연말 물류 지연 분석용
4. 회사 회계연도는 **3월 시작**이다. 회계 분기별 매출을 보고 싶다.
5. 월급날(매월 25일) 직후 3일간 매출이 높은가?
6. 주차별 매출 (ISO 주차)

## 할 일

1. `dim_date`의 컬럼을 설계한다. 질문 1~6에 답하는 데 필요한 속성을 모두 넣는다.
2. 날짜가 세 개인 팩트에서 날짜 차원을 **어떻게 세 번** 쓰는지 설계한다.
3. 질문 3번 SQL을 쓴다.

## 체크 질문

- `EXTRACT(DAYOFWEEK FROM order_date)`로 계산하면 되는데 왜 차원 테이블을 따로 만들까?
- 설 연휴는 매년 날짜가 다르다. SQL 함수로 계산할 수 있나?
- 주문일 · 결제일 · 배송완료일마다 날짜 차원 테이블을 따로 만들어야 하나?
- 배송이 아직 안 끝난 주문의 `배송완료일_key`는 뭘로 채우나?

<details>
<summary>💡 힌트</summary>

- 공휴일, 회계 분기, "월급날 직후" 같은 **회사 고유 달력**은 함수로 못 만든다. 테이블에 미리 적어둔다.
- 같은 차원을 역할만 바꿔 여러 번 참조하는 것 = **role-playing dimension**. 테이블은 하나, 뷰 또는 별칭으로 여러 번.
- "아직 없음"은 NULL 대신 **특수 행**(예: `date_key = 99991231, '미정'`).

</details>

<details>
<summary>✅ 모범 답안</summary>

### dim_date

| 컬럼 | 예 (2027-02-16) | 쓰는 질문 |
|---|---|---|
| `date_key` | 20270216 | 조인 키 (YYYYMMDD 정수) |
| `full_date` | 2027-02-16 | |
| `day_of_week_name` | 화요일 | |
| `is_weekend` | FALSE | 1 |
| `is_holiday` | FALSE | 2 |
| `holiday_name` | NULL (설 연휴 날짜면 '설날 연휴') | 2 |
| `year`, `month`, `day` | 2027, 2, 16 | |
| `year_month` | 2027-02 | 3 |
| `fiscal_year` | FY2026 | 4 (3월 시작이라 2027-02는 FY2026) |
| `fiscal_quarter` | FQ4 | 4 |
| `days_after_payday` | NULL (25일 이후 0~3일만 값) | 5 |
| `iso_year`, `iso_week` | 2027, 7 | 6 |
| `is_last_day_of_month` | FALSE | 월말 집계 |

```sql
CREATE TABLE dim_date (
  date_key           INT PRIMARY KEY,
  full_date          DATE,
  day_of_week_name   STRING,
  is_weekend         BOOL,
  is_holiday         BOOL,
  holiday_name       STRING,
  year INT, month INT, day INT,
  year_month         STRING,
  fiscal_year        STRING,
  fiscal_quarter     STRING,
  days_after_payday  INT,
  iso_year INT, iso_week INT,
  is_last_day_of_month BOOL
);
-- 특수 행: 날짜 미정
INSERT INTO dim_date (date_key, full_date, day_of_week_name)
VALUES (99991231, NULL, '미정');
```

### role-playing

```sql
CREATE TABLE fct_order_line (
  order_date_key     INT NOT NULL,   -- → dim_date
  paid_date_key      INT NOT NULL,   -- → dim_date
  delivered_date_key INT NOT NULL,   -- → dim_date (미배송 = 99991231)
  product_key        INT NOT NULL,
  order_no           STRING,         -- degenerate
  amount             INT64
);

-- 역할별 뷰: BI 도구에서 컬럼 이름이 헷갈리지 않게
CREATE VIEW dim_order_date     AS SELECT date_key AS order_date_key,     full_date AS order_date,     year_month AS order_year_month     FROM dim_date;
CREATE VIEW dim_delivered_date AS SELECT date_key AS delivered_date_key, full_date AS delivered_date, year_month AS delivered_year_month FROM dim_date;
```

### 질문 3

```sql
SELECT COUNT(*)
FROM fct_order_line f
JOIN dim_date od ON od.date_key = f.order_date_key
JOIN dim_date dd ON dd.date_key = f.delivered_date_key
WHERE od.month = 12 AND dd.month = 1
  AND dd.year = od.year + 1;
```

### 포인트

- 날짜 차원이 필요한 진짜 이유는 **회사 달력**이다. 요일은 함수로 되지만 공휴일 · 회계연도 · 사내 이벤트는 안 된다. 그리고 모든 마트가 **같은 정의**를 쓰게 된다 ("주말"의 정의가 리포트마다 다르면 숫자가 안 맞는다).
- **테이블은 하나, 역할은 여러 개.** 날짜 차원을 세 벌 만들면 공휴일을 고칠 때 세 군데를 고쳐야 한다.
- 미배송을 NULL로 두면 `JOIN dim_date`에서 그 주문이 **사라진다.** 특수 행으로 두면 "미배송 N건"이 집계에 남는다.
- BigQuery 실무에서는 팩트에 `DATE` 컬럼을 그대로 두고 `dim_date`를 `full_date`로 조인하는 경우도 많다. 정수 키든 DATE든, **회사 달력 속성을 한 테이블에서 관리한다**는 원칙이 핵심.

### 흔한 실수

- `is_holiday`를 리포트 SQL마다 `CASE WHEN date IN ('2027-02-16', …)`로 하드코딩 → 다음 해에 전부 고장.
- 회계연도를 `year`로 착각. 3월 시작이면 2027-02는 FY2026이다. 어떤 기준인지 컬럼 이름에 박는다.

</details>
