# DW-04. 창고 재고 — 더하면 안 되는 숫자

> 난이도 ★★☆ · 연습 개념: periodic snapshot fact, 반가산(semi-additive) 팩트, 트랜잭션 팩트와의 비교 · 예상 30분
> 참고: 『The Data Warehouse Toolkit』 4장 Inventory

## 시나리오

이커머스 물류센터 3곳(이천 · 용인 · 김해)의 재고 분석 마트를 만든다.

원천 데이터는 **입출고 기록**이다.

| 시각 | 창고 | 상품 | 유형 | 수량 |
|---|---|---|---|---|
| 11-01 09:00 | 이천 | 패딩 M | 입고 | +500 |
| 11-01 14:00 | 이천 | 패딩 M | 출고 | −120 |
| 11-02 10:00 | 이천 | 패딩 M | 출고 | −80 |
| 11-02 11:00 | 이천 | 패딩 M | 반품입고 | +5 |

현업 질문:

1. 11월 30일 기준 창고별 · 상품별 재고 수량과 재고 금액
2. 11월 **평균** 재고 수량
3. 11월 한 달 출고 수량 합계
4. 재고 회전율 = 출고 수량 ÷ 평균 재고
5. 재고가 0이었던 날이 며칠인가 (품절일수)

## 할 일

1. 입출고 기록만으로 질문 1~5에 답할 수 있는지 판단한다. 가능해도 **빠르고 쉬운지** 생각한다.
2. 일별 재고 스냅샷 팩트를 설계한다. grain을 적는다.
3. 각 팩트가 어떤 차원 방향으로 더할 수 있는지 표로 정리한다.
4. 질문 1, 2번 SQL을 쓴다.

## 체크 질문

- 11월 1일 재고 380 + 11월 2일 재고 305 = 685. 이 숫자는 의미가 있나?
- 같은 날 이천 재고 + 용인 재고는?
- 재고가 0인 날에도 스냅샷 행을 만들어야 하나?

<details>
<summary>💡 힌트</summary>

- 재고 수량은 **어느 순간의 상태(잔액)**다. 은행 잔고처럼, 날짜 방향으로는 더하면 안 된다. 다른 방향(창고, 상품)으로는 더해도 된다 → 반가산.
- 날짜 방향으로는 **평균**이나 **마지막 날 값**을 쓴다.
- 트랜잭션 팩트(입출고)와 스냅샷 팩트(일별 재고)는 **둘 다** 둔다. 질문 종류가 다르다.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 팩트 두 개

| 팩트 | 종류 | grain | 측정값 |
|---|---|---|---|
| `fct_inventory_txn` | 트랜잭션 | 입출고 1건 | 수량(±) |
| `fct_inventory_daily` | 주기적 스냅샷 | **창고 × 상품 × 하루 마감** 1행 | 재고 수량, 재고 금액, 당일 입고 · 출고 수량 |

```sql
CREATE TABLE fct_inventory_daily (
  date_key           INT NOT NULL,
  warehouse_key      INT NOT NULL,
  product_key        INT NOT NULL,
  on_hand_qty        INT64,     -- 마감 재고 (반가산)
  on_hand_value      INT64,     -- 마감 재고 × 단가 (반가산)
  received_qty       INT64,     -- 당일 입고 (가산)
  shipped_qty        INT64      -- 당일 출고 (가산)
);
```

입출고가 없는 날에도 **전날 재고를 이어서 행을 만든다.** 그래야 평균과 품절일수가 맞는다.

### 가산성

| 팩트 | 창고 방향 합 | 상품 방향 합 | 날짜 방향 합 |
|---|---|---|---|
| `on_hand_qty` | ✅ | ✅ | ❌ → 평균 또는 기말값 |
| `on_hand_value` | ✅ | ✅ | ❌ |
| `shipped_qty` | ✅ | ✅ | ✅ |

### SQL

```sql
-- 1. 11/30 기준 재고
SELECT w.name, p.name, f.on_hand_qty, f.on_hand_value
FROM fct_inventory_daily f
JOIN dim_warehouse w USING (warehouse_key)
JOIN dim_product   p USING (product_key)
WHERE f.date_key = 20261130;

-- 2. 11월 평균 재고 (상품별, 전 창고 합)
SELECT product_key,
       SUM(on_hand_qty) / COUNT(DISTINCT date_key) AS avg_on_hand
FROM fct_inventory_daily
WHERE date_key BETWEEN 20261101 AND 20261130
GROUP BY 1;

-- 5. 품절일수
SELECT product_key, warehouse_key, COUNTIF(on_hand_qty = 0) AS stockout_days
FROM fct_inventory_daily
WHERE date_key BETWEEN 20261101 AND 20261130
GROUP BY 1, 2;
```

2번에서 `AVG(on_hand_qty)`를 쓰면 **창고별 행의 평균**이 나온다. "전 창고 합계의 일평균"이 필요하면 날짜별로 먼저 합치고(`SUM`) 그다음 날짜 수로 나눈다.

### 포인트

- 입출고 기록만 있어도 누적합으로 재고를 계산할 수 있다. 하지만 "11월 30일 재고"를 구하려면 **처음부터 모든 기록을 더해야** 한다. 스냅샷은 그 계산을 미리 해둔 것이다.
- 스냅샷 행은 매일 `창고 수 × 상품 수`만큼 생긴다. 3창고 × 1만 상품 × 365일 = 연 1,095만 행. 크지만 BigQuery에서는 날짜 파티션으로 충분히 다룰 수 있다.
- **반가산 팩트는 컬럼 설명에 반드시 적어둔다.** BI 도구는 기본으로 SUM을 하니까, Cube 같은 시맨틱 레이어에서 measure 타입을 `last` 또는 평균으로 지정해 두는 게 안전하다.
- 계좌 잔고, 포인트 잔액, 구독자 수, MAU 같은 "상태값"도 전부 같은 패턴이다.

### 흔한 실수

- 월간 리포트에서 `SUM(on_hand_qty)`를 그대로 씀 → 재고가 30배로 보인다.
- 재고 변동이 없는 날을 건너뛰어 스냅샷을 만듦 → `COUNT(DISTINCT date_key)`가 줄어 평균 재고가 부풀고, 품절일수도 틀린다.

</details>
