# DW-05. 주문 처리 흐름 — 행을 업데이트하는 팩트

> 난이도 ★★★ · 연습 개념: accumulating snapshot fact, 마일스톤 날짜, lag(소요 시간) 팩트 · 예상 30분
> 참고: 『The Data Warehouse Toolkit』 4장 Accumulating Snapshot, 6장 Order Management

## 시나리오

RDB-07 배달앱의 주문 상태 이력을 분석한다. 원천에는 상태 변경 이력이 쌓인다.

| 주문 | 상태 | 시각 |
|---|---|---|
| O-1 | 접수 | 18:00:10 |
| O-1 | 조리 중 | 18:02:40 |
| O-1 | 배달 중 | 18:21:00 |
| O-1 | 완료 | 18:43:30 |
| O-2 | 접수 | 18:05:00 |
| O-2 | 취소 | 18:09:00 |
| O-3 | 접수 | 18:10:00 |
| O-3 | 조리 중 | 18:30:00 |

현업 질문:

1. 가게별 평균 **접수 → 조리 시작** 시간 (사장님 응답 속도)
2. 평균 **배달 소요 시간** (배달 중 → 완료)
3. 지금 **조리 중에 머물러 있는** 주문 수 (O-3처럼)
4. 단계별 이탈: 접수 100건 중 조리까지 간 건, 배달까지 간 건, 완료된 건
5. 저녁 피크(18~20시) 접수 주문의 평균 총 소요 시간

## 할 일

1. 상태 이력을 그대로 팩트로 두는 방식(트랜잭션 팩트)으로 질문 1번 SQL을 써본다. 얼마나 복잡한가?
2. **주문 1건 = 1행**인 accumulating snapshot 팩트를 설계한다.
3. 주문이 진행되면서 이 행이 **어떻게 바뀌는지** 설명한다.
4. 질문 1, 3, 4번 SQL을 쓴다.

## 체크 질문

- 아직 일어나지 않은 단계의 시각은 뭘로 채우나?
- 이 팩트는 INSERT만 하나, UPDATE도 하나? 파이프라인에서 어떻게 갱신하나?
- 시간 차이(lag)를 미리 계산해서 넣어야 하나, 쿼리에서 계산해야 하나?

<details>
<summary>💡 힌트</summary>

- accumulating snapshot은 **흐름(파이프라인)이 명확한 프로세스**에 쓴다. 마일스톤마다 날짜 · 시각 컬럼이 있고, 단계가 진행될 때마다 같은 행을 갱신한다.
- 트랜잭션 팩트에서 "접수 → 조리"를 구하려면 같은 주문의 두 행을 짝지어야 한다 (self join 또는 pivot).
- lag는 미리 계산해 두면 `AVG(lag)` 한 줄로 끝난다.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 트랜잭션 팩트로 1번을 풀면

```sql
SELECT o.store_key,
       AVG(TIMESTAMP_DIFF(c.changed_at, r.changed_at, SECOND)) AS avg_accept_sec
FROM fct_order_status r
JOIN fct_order_status c
  ON c.order_id = r.order_id AND c.status = 'cooking'
JOIN dim_order o ON o.order_id = r.order_id
WHERE r.status = 'received'
GROUP BY 1;
```

질문마다 단계 쌍을 self join해야 한다. 단계가 5개면 조합이 많아지고, 질문 4번(단계별 이탈)은 더 복잡하다.

### accumulating snapshot

grain: **주문 1건 = 1행**. 단계가 진행될 때마다 같은 행을 갱신한다.

```sql
CREATE TABLE fct_order_fulfillment (
  order_id            STRING NOT NULL,     -- degenerate
  store_key           INT    NOT NULL,
  customer_key        INT    NOT NULL,

  -- 마일스톤 (role-playing 날짜/시각). 미도달 = NULL 또는 '미정' 키
  received_at         TIMESTAMP,
  cooking_at          TIMESTAMP,
  delivering_at       TIMESTAMP,
  completed_at        TIMESTAMP,
  cancelled_at        TIMESTAMP,
  received_date_key   INT,                 -- 날짜 차원 조인용

  -- lag 팩트 (초). 미도달이면 NULL
  accept_lag_sec      INT64,               -- 접수 → 조리
  cook_lag_sec        INT64,               -- 조리 → 배달
  delivery_lag_sec    INT64,               -- 배달 → 완료
  total_lag_sec       INT64,               -- 접수 → 완료

  -- 단계 도달 플래그 (0/1, 가산)
  reached_cooking     INT64,
  reached_delivering  INT64,
  reached_completed   INT64,
  is_cancelled        INT64,

  current_status      STRING,
  order_amount        INT64
);
```

### 행이 변하는 모습 (O-3)

| 시점 | cooking_at | delivering_at | accept_lag_sec | reached_delivering | current_status |
|---|---|---|---|---|---|
| 18:10 접수 | NULL | NULL | NULL | 0 | received |
| 18:30 조리 | 18:30:00 | NULL | 1200 | 0 | cooking |
| (이후 배달) | 18:30:00 | 채워짐 | 1200 | 1 | delivering |

### SQL

```sql
-- 1. 가게별 평균 접수 → 조리
SELECT store_key, AVG(accept_lag_sec) FROM fct_order_fulfillment GROUP BY 1;

-- 3. 조리 중에 머무른 주문
SELECT COUNT(*) FROM fct_order_fulfillment WHERE current_status = 'cooking';

-- 4. 단계별 이탈 (퍼널)
SELECT COUNT(*)                AS received,
       SUM(reached_cooking)    AS cooking,
       SUM(reached_delivering) AS delivering,
       SUM(reached_completed)  AS completed
FROM fct_order_fulfillment;
```

### 파이프라인

- 매 실행마다 **최근 상태가 바뀐 주문**만 골라 상태 이력을 pivot해서 `MERGE`한다.
- dbt라면 `materialized='incremental'`, `unique_key='order_id'`, `incremental_strategy='merge'`. 업데이트 대상을 찾는 기준은 `received_at`이 아니라 **마지막 상태 변경 시각**이어야 한다. 3일 전 접수된 주문도 오늘 완료될 수 있다.

### 세 가지 팩트 비교

| | 트랜잭션 | 주기적 스냅샷 (DW-04) | 누적 스냅샷 (이번) |
|---|---|---|---|
| grain | 사건 1건 | 기간 1개 × 대상 | 프로세스 1건 (처음 ~ 끝) |
| 행 갱신 | 안 함 | 안 함 (매 기간 새 행) | **함** |
| 날짜 컬럼 | 1개 | 1개 (스냅샷 일자) | 마일스톤 수만큼 |
| 강한 질문 | "몇 건, 얼마" | "그때 잔액은" | "단계 사이 얼마나 걸렸나" |

### 포인트

- 단계별 lag와 도달 플래그를 **미리 계산해 두면** 퍼널과 소요 시간 분석이 `SUM`, `AVG` 한 줄이 된다.
- 트랜잭션 팩트(상태 이력)는 **버리지 않는다.** "취소 직전 상태가 뭐였나" 같은 질문은 이력이 있어야 답할 수 있다. 누적 스냅샷은 그 위에 얹는 요약이다.
- 상태가 뒤로 가는 경우(배달 중 → 조리 중 재조리)가 있으면 누적 스냅샷이 표현하기 어렵다. 흐름이 **한 방향**인 프로세스에 맞는 패턴.

### 흔한 실수

- 증분 갱신 조건을 `received_at >= 어제`로 잡음 → 어제 이전에 접수돼서 오늘 완료된 주문이 영원히 "배달 중"으로 남는다.
- 미도달 lag를 0으로 채움 → 평균 소요 시간이 실제보다 짧게 나온다. **NULL이어야 AVG에서 빠진다.**

</details>
