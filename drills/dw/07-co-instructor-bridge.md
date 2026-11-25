# DW-07. 공동 강의 매출 — M:N이 스타 스키마에 들어오면

> 난이도 ★★★ · 연습 개념: multivalued dimension, bridge table, 가중치(allocation), 중복 집계 · 예상 35분
> 참고: 『The Data Warehouse Toolkit』 8장 Multivalued Dimensions and Bridge Tables

## 시나리오

온라인 강의 플랫폼의 매출 마트다. 강의 하나를 **강사 여러 명이 공동으로** 진행할 수 있다. 정산 비율은 강의마다 계약으로 정한다.

| 강의 | 강사 | 정산 비율 |
|---|---|---|
| 수능 수학 완성 | 김수학 | 100% |
| 국어 + 사탐 패키지 | 이국어 | 60% |
| 국어 + 사탐 패키지 | 박사탐 | 40% |

판매:

| 주문 | 강의 | 금액 |
|---|---|---|
| P-1 | 수능 수학 완성 | 100,000 |
| P-2 | 국어 + 사탐 패키지 | 200,000 |
| P-3 | 국어 + 사탐 패키지 | 200,000 |

현업 질문:

1. 강의별 매출 → 수학 10만, 패키지 40만, **합계 50만**
2. 강사별 **정산 매출** → 김수학 10만, 이국어 24만, 박사탐 16만, 합계 50만
3. 강사별 **참여 매출** (비율 무시, 참여한 강의 매출 전체) → 이국어 40만, 박사탐 40만. 합계는 의미 없음
4. 강사별 판매 **건수**

## 할 일

1. 판매 팩트에 `instructor_key`를 하나만 넣을 수 없는 이유를 쓴다.
2. 강사를 판매 팩트에 그냥 조인하면 질문 1번 합계가 얼마가 되는지 계산해본다.
3. bridge table을 설계한다.
4. 질문 1, 2, 3번 SQL을 쓰고, 합계가 맞는지 확인한다.

## 체크 질문

- 판매 1건 ↔ 강사 여러 명 = 어떤 카디널리티인가? (RDB 연습에서는 이걸 어떻게 풀었나?)
- 강사를 조인한 상태로 `SUM(금액)`을 하면 왜 틀어지나?
- 정산 비율이 강의 도중 바뀌면? (2027년부터 이국어 50%, 박사탐 50%)

<details>
<summary>💡 힌트</summary>

- 판매 팩트 grain은 "주문 1건의 강의 1개"다. 강사가 여러 명이면 팩트에 강사 FK를 둘 수 없다.
- 강의 ↔ 강사를 잇는 연결 테이블(bridge)에 **가중치**를 넣으면, `금액 × 가중치`의 합이 원래 금액과 같아진다.
- 가중치 합은 강의마다 정확히 1이어야 한다. dbt 테스트로 검증.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 왜 그냥 조인하면 틀리나

패키지 판매 1건이 강사 2명과 조인되면 **2행**이 된다. 질문 1번을 강사 조인 상태로 SUM하면:

- 수학 10만 + 패키지(20만 × 2명 × 2건) 80만 = **90만** ← 실제 50만

이게 JOIN 뻥튀기(fan-out)다.

### 설계

```
fct_course_sales ── dim_course ──< bridge_course_instructor >── dim_instructor
```

```sql
CREATE TABLE fct_course_sales (
  date_key    INT,
  course_key  INT,
  customer_key INT,
  order_no    STRING,         -- degenerate
  amount      INT64
);

CREATE TABLE bridge_course_instructor (
  course_key       INT,
  instructor_key   INT,
  allocation       NUMERIC,   -- 정산 비율. 강의별 합 = 1.0
  valid_from       DATE,      -- 비율 변경 이력 (SCD2처럼)
  valid_to         DATE
);
```

판매 팩트는 **강사를 모른다.** 강의만 안다. 강사는 강의를 통해 bridge로 연결된다.

### SQL

```sql
-- 1. 강의별 매출: 브리지를 안 거침 → 50만
SELECT course_key, SUM(amount) FROM fct_course_sales GROUP BY 1;

-- 2. 강사별 정산 매출: 가중치 곱 → 합계 50만 유지
SELECT b.instructor_key, SUM(f.amount * b.allocation) AS settled_sales
FROM fct_course_sales f
JOIN dim_date d ON d.date_key = f.date_key
JOIN bridge_course_instructor b
  ON b.course_key = f.course_key
 AND d.full_date >= b.valid_from AND d.full_date < b.valid_to
GROUP BY 1;

-- 3. 강사별 참여 매출: 가중치 없이 (impact report). 합계를 내면 안 됨
SELECT b.instructor_key, SUM(f.amount) AS involved_sales
FROM fct_course_sales f
JOIN dim_date d ON d.date_key = f.date_key
JOIN bridge_course_instructor b
  ON b.course_key = f.course_key
 AND d.full_date >= b.valid_from AND d.full_date < b.valid_to
GROUP BY 1;

-- 4. 강사별 판매 건수
SELECT b.instructor_key, COUNT(DISTINCT f.order_no)
FROM fct_course_sales f
JOIN bridge_course_instructor b USING (course_key)
GROUP BY 1;
```

### 가중치 검증 (dbt)

```sql
-- tests/assert_bridge_allocation_sums_to_one.sql : 결과가 0행이어야 통과
SELECT course_key, valid_from, SUM(allocation) AS total
FROM {{ ref('bridge_course_instructor') }}
GROUP BY 1, 2
HAVING ABS(SUM(allocation) - 1.0) > 0.0001
```

### 포인트

- 킴벌은 bridge를 거친 집계를 두 종류로 나눈다.
  - **가중치 적용(weighted)**: 합계가 원래 매출과 같다. 정산, 재무 보고용.
  - **가중치 없음(impact)**: "이 강사가 관여한 매출". 강사별로는 맞지만 **더하면 중복**이다.
  리포트에 어느 쪽인지 반드시 적는다.
- 이번 주 RDB에서 계속 나온 **M:N → 연결 테이블** 패턴이 DW에서는 bridge table로 다시 나온다. 차이는 DW에서는 "합계가 틀어지지 않게" 가중치까지 설계해야 한다는 것.
- 비율이 바뀌면 bridge에 **유효 기간**을 둔다. 판매일 기준으로 그때의 비율이 적용된다 (DW-06 SCD2와 같은 원리).
- Cube 같은 시맨틱 레이어에서 이 조인을 정의할 때 relationship을 잘못 잡으면 measure가 중복 집계된다. 브리지를 거치는 measure는 따로 정의하는 게 안전하다.

### 흔한 실수

- 판매 팩트에 `main_instructor_key` 하나만 넣고 끝냄 → 공동 강사 정산이 불가능.
- 팩트 grain을 "판매 × 강사"로 바꾸고 금액을 비율대로 쪼개 넣음 → 가능한 설계지만, 그러면 강의별 판매 건수를 셀 때 `COUNT(DISTINCT)`가 필요해지고 팩트 행이 강사 수만큼 늘어난다. bridge와 장단점을 비교해볼 것.

</details>
