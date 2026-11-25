# RDB-03. 사내 조직도 — 자기 자신을 가리키는 관계

> 난이도 ★★☆ · 연습 개념: 재귀 관계(1:N, M:N), 같은 두 엔티티 사이의 다중 관계 · 예상 25분

## 시나리오

HR 시스템의 조직 데이터를 설계한다.

- 직원은 사번, 이름, 직급, 입사일이 있다.
- 직원은 **직속 상사가 1명** 있다. 대표이사만 상사가 없다.
- 부서는 트리 구조다. 예: `개발본부 > 플랫폼실 > 데이터팀`. 부서마다 상위 부서가 최대 1개.
- 직원은 **한 부서에 소속**된다.
- 부서마다 **부서장이 1명** 있다. 부서장도 직원이다. 공석일 수도 있다.
- 사내 멘토링 제도가 있다. 한 직원이 여러 명을 멘토링하고, 한 직원이 여러 멘토를 둘 수 있다. 멘토링마다 **시작일과 종료일**이 있다.

## 샘플 데이터

| 사번 | 이름 | 상사 | 부서 |
|---|---|---|---|
| 1 | 대표 | — | 경영 |
| 2 | 김본부 | 1 | 개발본부 |
| 3 | 이실장 | 2 | 플랫폼실 |
| 4 | 박팀장 | 3 | 데이터팀 |
| 5 | 최사원 | 4 | 데이터팀 |

| 부서 | 상위 부서 | 부서장 |
|---|---|---|
| 개발본부 | — | 김본부 |
| 플랫폼실 | 개발본부 | 이실장 |
| 데이터팀 | 플랫폼실 | 박팀장 |

| 멘토 | 멘티 | 시작 | 종료 |
|---|---|---|---|
| 박팀장 | 최사원 | 2026-03-01 | 2026-08-31 |
| 이실장 | 최사원 | 2026-09-01 | — |

## 할 일

1. 재귀 관계를 모두 찾는다. (몇 개인가?)
2. 직원 ↔ 부서 사이의 관계를 모두 찾는다. (몇 개인가?)
3. DDL을 쓴다.
4. "김본부 산하의 모든 직원"을 조회하는 SQL을 쓴다.

## 체크 질문

- "상사"를 위한 별도 테이블이 필요한가?
- 상사(1:N 재귀)와 멘토링(M:N 재귀)은 테이블로 바꿀 때 어떻게 다른가?
- 직원 ↔ 부서의 "소속"과 "부서장"을 관계 하나로 합칠 수 있나?
- 부서와 부서장이 서로를 참조하면 INSERT 순서에 무슨 문제가 생기나?

<details>
<summary>💡 힌트</summary>

- 재귀는 3개: 직원→상사, 부서→상위 부서, 직원↔직원 멘토링.
- 1:N 재귀는 **컬럼 하나**(`manager_id`), M:N 재귀는 **연결 테이블**.
- 직원 → 부서 "소속"(N:1)과 부서 → 직원 "부서장"(1:1)은 의미가 다른 별개 관계다 (22강 다중 관계).
- 서로 참조하는 FK는 한쪽을 NULL 허용으로 두거나 `DEFERRABLE` 제약으로 푼다.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 관계 정리

| 관계 | 종류 | 구현 |
|---|---|---|
| 직원 → 상사(직원) | 재귀 1:N | `employee.manager_id` |
| 부서 → 상위 부서 | 재귀 1:N | `department.parent_id` |
| 직원 ↔ 직원 멘토링 | 재귀 M:N + 속성 | `mentoring` 테이블 |
| 직원 → 부서 (소속) | N:1 | `employee.department_id` |
| 부서 → 직원 (부서장) | 1:1, 선택 | `department.head_employee_id` |

### DDL

```sql
CREATE TABLE department (
  department_id    BIGSERIAL PRIMARY KEY,
  name             TEXT NOT NULL,
  parent_id        BIGINT REFERENCES department(department_id),   -- 재귀, 최상위는 NULL
  head_employee_id BIGINT UNIQUE                                  -- FK는 아래에서 추가
);

CREATE TABLE employee (
  employee_id   BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  title         TEXT,
  hired_at      DATE NOT NULL,
  manager_id    BIGINT REFERENCES employee(employee_id),          -- 재귀, 대표는 NULL
  department_id BIGINT NOT NULL REFERENCES department(department_id),
  CHECK (manager_id <> employee_id)                               -- 자기 자신이 상사 X
);

-- 순환 참조: 부서가 먼저 생기고, 부서장은 나중에 지정
ALTER TABLE department
  ADD CONSTRAINT fk_department_head
  FOREIGN KEY (head_employee_id) REFERENCES employee(employee_id);

CREATE TABLE mentoring (
  mentoring_id BIGSERIAL PRIMARY KEY,
  mentor_id    BIGINT NOT NULL REFERENCES employee(employee_id),
  mentee_id    BIGINT NOT NULL REFERENCES employee(employee_id),
  started_at   DATE   NOT NULL,
  ended_at     DATE,
  CHECK (mentor_id <> mentee_id),
  CHECK (ended_at IS NULL OR ended_at >= started_at),
  UNIQUE (mentor_id, mentee_id, started_at)   -- 같은 짝이 다시 멘토링할 수 있으니 시작일 포함
);
```

`head_employee_id`에 `UNIQUE`를 건 이유: 한 사람이 두 부서의 장을 겸하지 못한다는 규칙을 가정했다. 겸직이 가능한 회사라면 UNIQUE를 뺀다 — **비즈니스 규칙에 따라 제약이 바뀐다.**

### 산하 전체 직원 (재귀 CTE)

```sql
WITH RECURSIVE subordinates AS (
  SELECT employee_id, name, manager_id, 1 AS depth
  FROM employee
  WHERE manager_id = 2                     -- 김본부의 직속
  UNION ALL
  SELECT e.employee_id, e.name, e.manager_id, s.depth + 1
  FROM employee e
  JOIN subordinates s ON e.manager_id = s.employee_id
)
SELECT * FROM subordinates ORDER BY depth;
```

### 포인트

- **재귀 1:N은 컬럼 하나.** "상사 테이블"을 따로 만들면 같은 사람이 두 테이블에 존재하게 된다.
- **재귀 M:N은 연결 테이블.** 컬럼 이름을 `employee_id_1`, `employee_id_2`로 짓지 말고 `mentor_id`, `mentee_id`처럼 **역할 이름**으로 짓는다. 재귀 관계에서는 양쪽이 같은 엔티티라 역할 이름이 없으면 방향을 알 수 없다.
- **소속과 부서장은 다른 관계.** 하나로 합쳐서 `employee.is_head BOOLEAN`으로 두면 "부서장이 그 부서 소속이 아닐 수도 있는" 상황(겸임, 대행)을 표현할 수 없고, 한 부서에 부서장이 둘 생기는 것도 못 막는다.

### 흔한 실수

- 순환(A의 상사가 B, B의 상사가 A)을 DB가 막아주지 않는다. CHECK는 같은 행만 보기 때문. 앱 로직에서 막거나, 재귀 CTE로 주기적으로 검사한다.
- 부서 트리를 `path TEXT = '개발본부/플랫폼실/데이터팀'`로만 저장 → 부서 이름이 바뀌면 하위 부서의 경로를 전부 고쳐야 한다. 조회 성능 때문에 경로를 쓰더라도 `parent_id`가 원본이어야 한다.

</details>
