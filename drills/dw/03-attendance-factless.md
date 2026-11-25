# DW-03. 학원 출석 — 숫자가 없는 팩트 테이블

> 난이도 ★★☆ · 연습 개념: factless fact table (이벤트형, coverage형), "일어나지 않은 일" 분석 · 예상 25분
> 참고: 『The Data Warehouse Toolkit』 13장 Education, Factless Fact Tables

## 시나리오

RDB-02의 학원에서 출석 분석 마트를 만든다.

원천 데이터:
- **수강신청**: 학생이 분반에 등록 (등록일, 수강 취소일)
- **수업 회차**: 분반마다 날짜별 수업 (2026-1학기 MATH1 1반, 3/4 수업, 3/6 수업 …)
- **출석 체크**: 학생이 수업 회차에 입실하면 키오스크에 기록 (입실 시각)

현업 질문:

1. 분반별 · 회차별 **출석 인원**
2. 강사별 평균 **출석률**
3. **결석이 3회 이상**인 학생 명단 (상담 대상)
4. 요일별 결석률 (금요일에 결석이 많은가?)
5. 지각(수업 시작 10분 뒤 입실) 비율

## 할 일

1. 출석 팩트의 grain을 정한다.
2. 팩트 테이블에 **측정값(숫자)**이 있나? 없다면 그래도 팩트인가?
3. 질문 3번(결석)을 출석 팩트만으로 답할 수 있나? 안 된다면 무엇이 더 필요한가?
4. 필요한 팩트 테이블을 모두 설계하고 질문 2, 3번 SQL을 쓴다.

## 체크 질문

- 결석은 출석 체크 테이블에 **행이 없다**. 없는 행을 어떻게 셀까?
- "이 학생은 이 수업을 들었어야 했다"는 정보는 어디에 있나?
- 지각 여부는 차원인가, 팩트인가?

<details>
<summary>💡 힌트</summary>

- 측정값 없이 "누가 · 언제 · 어디서 만났다"는 **사건 자체**를 기록하는 팩트 = factless fact. 집계는 `COUNT(*)`.
- "일어날 수 있었던 일"의 목록 = **coverage 팩트**. 결석 = coverage − 실제 출석.
- 수업 회차 × 그 분반에 등록된 학생 = 출석했어야 하는 목록.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 팩트 두 개

| 팩트 | grain | 측정값 |
|---|---|---|
| `fct_attendance` (이벤트형) | 학생 1명이 수업 회차 1번에 **입실한** 기록 | 없음 (+ 선택: 지각 분) |
| `fct_class_roster` (coverage형) | 수업 회차 1번에 **출석해야 했던** 학생 1명 | 없음 |

```sql
CREATE TABLE fct_class_roster (       -- 출석 대상자 (coverage)
  date_key        INT NOT NULL,        -- 수업일
  class_session_key INT NOT NULL,      -- 수업 회차 (분반 · 강사 · 강의실 포함)
  student_key     INT NOT NULL
);

CREATE TABLE fct_attendance (          -- 실제 출석 (event)
  date_key          INT NOT NULL,
  class_session_key INT NOT NULL,
  student_key       INT NOT NULL,
  checkin_time_key  INT NOT NULL,      -- 입실 시각
  late_minutes      INT64              -- 시작 기준 늦은 분 (0 이상). 선택적 측정값
);

CREATE TABLE dim_class_session (
  class_session_key INT PRIMARY KEY,
  term STRING, course_code STRING, section_no INT,
  instructor_name STRING, room STRING,
  session_seq INT,                     -- 몇 회차
  starts_at_time STRING                -- '19:00'
);
```

`fct_class_roster`는 파이프라인에서 만든다: **수업 회차 × (그 날짜에 수강 중인) 수강신청**.

### SQL

```sql
-- 2. 강사별 출석률 = 실제 출석 / 출석 대상
SELECT s.instructor_name,
       COUNT(a.student_key) / COUNT(*) AS attendance_rate
FROM fct_class_roster r
JOIN dim_class_session s USING (class_session_key)
LEFT JOIN fct_attendance a
  ON a.class_session_key = r.class_session_key
 AND a.student_key       = r.student_key
GROUP BY 1;

-- 3. 결석 3회 이상
SELECT r.student_key, COUNT(*) AS absences
FROM fct_class_roster r
LEFT JOIN fct_attendance a
  ON a.class_session_key = r.class_session_key
 AND a.student_key       = r.student_key
WHERE a.student_key IS NULL
GROUP BY 1
HAVING COUNT(*) >= 3;
```

### 포인트

- **숫자가 없어도 팩트다.** 팩트 테이블의 본질은 "측정값"이 아니라 **"사건의 기록"**이다. 집계는 `COUNT(*)`.
- 출석 팩트만으로는 결석을 셀 수 없다. 없는 행은 셀 수 없으니까. 그래서 **"있었어야 하는 것"의 목록(coverage)**을 따로 만든다. 킴벌 책의 유명한 예시는 "행사 중이었는데 안 팔린 상품" — 판매 팩트에는 안 팔린 상품이 없다.
- 지각은 `late_minutes`로 넣거나, `is_late` 같은 플래그 차원으로 둘 수 있다. 분 단위 숫자가 있으면 "평균 지각 시간"까지 답할 수 있어서 더 유연하다.
- 출석률을 `AVG(학생별 출석률)`로 내면 틀릴 수 있다. 수업 수가 다른 학생이 섞이면 가중치가 어긋난다. **분자 합 / 분모 합**으로 계산한다.

### 흔한 실수

- 출석 팩트에 결석 행까지 `status = 'absent'`로 넣는 설계 → 가능은 하지만, 그러면 그 테이블은 사실상 coverage 팩트다. 원천에 결석 기록이 없으면 파이프라인에서 만들어 넣어야 하므로 어디서 만들지 정해야 한다.
- 수강 취소한 학생을 coverage에서 빼지 않음 → 취소 이후 수업이 전부 결석으로 잡혀 상담 대상에 뜬다.

</details>
