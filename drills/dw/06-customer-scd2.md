# DW-06. 회원 등급 변경 — "그때" 기준이냐 "지금" 기준이냐

> 난이도 ★★★ · 연습 개념: Slowly Changing Dimension Type 1 / Type 2, 대리키의 진짜 이유 · 예상 30분
> 참고: 『The Data Warehouse Toolkit』 5장 Slowly Changing Dimension Techniques

## 시나리오

쇼핑몰 회원 차원을 설계한다. 회원 정보는 시간이 지나며 바뀐다.

| 날짜 | 회원 | 변경 내용 |
|---|---|---|
| 2026-01-10 | 김회원 | 가입. 등급 브론즈, 거주지 서울 |
| 2026-03-02 | 김회원 | 이름 오타 수정 (김휘원 → 김회원) |
| 2026-05-01 | 김회원 | 등급 실버로 승급 |
| 2026-08-15 | 김회원 | 부산으로 이사 |
| 2026-11-01 | 김회원 | 등급 골드로 승급 |

김회원의 주문: 2월에 3만 원, 6월에 5만 원, 9월에 7만 원, 11월에 10만 원.

현업 질문:

1. **주문 당시 등급** 기준 등급별 매출 — "실버 회원이던 시기에 얼마나 샀나?"
2. **현재 등급** 기준 등급별 매출 — "지금 골드인 회원들이 지금까지 얼마나 샀나?"
3. 지역별 매출은 **주문 당시 거주지** 기준
4. 이름은 항상 **최신 값**으로 보이면 된다. 오타 수정 전 이름은 필요 없다.

## 할 일

1. 속성마다 변경 처리 방식(Type 1 덮어쓰기 / Type 2 새 행)을 정한다.
2. `dim_customer`를 설계하고, 김회원이 몇 행이 되는지 실제 데이터를 채워본다.
3. 팩트가 회원 차원의 **어떤 키**를 들고 있어야 하는지 정한다.
4. 질문 1, 2번 SQL을 쓴다.

## 체크 질문

- 팩트가 회원번호(자연키)만 들고 있으면 "주문 당시 등급"을 알 수 있나?
- Type 2로 행이 여러 개가 되면, "현재 등급" 기준 집계는 어떻게 하나?
- 이름 오타 수정도 Type 2로 하면 무슨 일이 생기나?

<details>
<summary>💡 힌트</summary>

- Type 2는 변경될 때마다 **새 행 + 새 대리키**. 각 행에 유효 기간(`valid_from`, `valid_to`)과 `is_current`.
- 팩트는 주문 시점에 유효했던 행의 **대리키**를 들고 있으면, 조인만 해도 "그때" 값이 나온다.
- "지금" 기준은 자연키로 현재 행을 다시 찾아 붙이면 된다.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 속성별 처리

| 속성 | 방식 | 이유 |
|---|---|---|
| 이름 | Type 1 | 오타 수정. 과거 값이 의미 없음 |
| 등급 | Type 2 | "그때 등급" 분석 필요 |
| 거주지 | Type 2 | "그때 지역" 분석 필요 |

### dim_customer (김회원)

| customer_key | customer_id | name | grade | city | valid_from | valid_to | is_current |
|---|---|---|---|---|---|---|---|
| 101 | C-7 | 김회원 | 브론즈 | 서울 | 2026-01-10 | 2026-04-30 | FALSE |
| 245 | C-7 | 김회원 | 실버 | 서울 | 2026-05-01 | 2026-08-14 | FALSE |
| 388 | C-7 | 김회원 | 실버 | 부산 | 2026-08-15 | 2026-10-31 | FALSE |
| 512 | C-7 | 김회원 | 골드 | 부산 | 2026-11-01 | 9999-12-31 | TRUE |

- 이름 오타 수정(3/2)은 Type 1이라 **행이 늘지 않고**, 모든 행의 이름이 "김회원"으로 덮어써졌다.
- 등급 변경 2번 + 이사 1번 = Type 2 변경 3번 → 4행.

```sql
CREATE TABLE dim_customer (
  customer_key INT PRIMARY KEY,   -- 대리키: 버전마다 다름
  customer_id  STRING,            -- 자연키: 사람마다 같음
  name         STRING,            -- Type 1
  grade        STRING,            -- Type 2
  city         STRING,            -- Type 2
  valid_from   DATE,
  valid_to     DATE,
  is_current   BOOL
);

CREATE TABLE fct_order (
  order_date_key INT,
  customer_key   INT,             -- 주문 시점에 유효했던 버전의 대리키
  order_no       STRING,
  amount         INT64
);
```

김회원의 주문은 2월 → 101, 6월 → 245, 9월 → 388, 11월 → 512를 들고 있다.

### SQL

```sql
-- 1. 주문 당시 등급 기준
SELECT c.grade, SUM(f.amount)
FROM fct_order f
JOIN dim_customer c ON c.customer_key = f.customer_key
GROUP BY 1;
-- 김회원: 브론즈 3만 / 실버 12만 (5+7) / 골드 10만

-- 2. 현재 등급 기준
SELECT cur.grade, SUM(f.amount)
FROM fct_order f
JOIN dim_customer hist ON hist.customer_key = f.customer_key
JOIN dim_customer cur  ON cur.customer_id = hist.customer_id AND cur.is_current
GROUP BY 1;
-- 김회원: 골드 25만 (전부)
```

### 포인트

- **대리키가 필요한 진짜 이유가 여기 있다.** 자연키(`C-7`)는 한 사람에 하나라서 버전을 구분할 수 없다. 버전마다 다른 키가 있어야 팩트가 "그때의 김회원"을 가리킬 수 있다.
- 팩트가 대리키를 들고 있으면 **"그때" 기준은 그냥 조인**, "지금" 기준은 자연키로 한 번 더 조인. 반대로 팩트가 자연키만 들고 있으면 "그때" 기준은 `주문일 BETWEEN valid_from AND valid_to` 조인을 매번 해야 한다.
- 실무에서는 dbt `snapshot`이 원천 테이블의 변경을 감지해 `dbt_valid_from`, `dbt_valid_to`를 자동으로 붙여준다. 그 위에 대리키를 붙이면 Type 2 차원이 된다.
- 모든 속성을 Type 2로 하면 사소한 변경(오타, 전화번호)마다 행이 늘어서 차원이 비대해진다. **분석에서 "그때 값"이 필요한 속성만** Type 2로.

### 흔한 실수

- `valid_to`를 다음 행의 `valid_from`과 같은 날로 둠 → 경계일 주문이 두 행에 매칭돼 매출이 두 번 잡힌다. `valid_to = 다음 valid_from − 1일`로 하거나, 조건을 `>= valid_from AND < valid_to`(반열린 구간)로 통일한다.
- 현재 행의 `valid_to`를 NULL로 둠 → `BETWEEN` 조건에서 빠진다. 먼 미래 날짜(9999-12-31)로 채운다.

</details>
