# RDB-02. 학원 분반 — 혼자서는 이름이 없는 엔티티

> 난이도 ★★☆ · 연습 개념: Weak entity, 부분 키(partial key), 식별 관계, 복합 FK · 예상 25분

## 시나리오

입시 학원의 수강 관리 시스템이다.

- 과목은 과목코드(`MATH1`, `ENG2` …)와 과목명이 있다.
- 과목마다 **분반**이 여러 개 열린다. 분반 번호는 **과목 안에서만** 1, 2, 3 … 으로 매긴다. 즉 `MATH1`의 1반과 `ENG2`의 1반은 다른 반이다.
- 학기가 바뀌면 분반 번호를 다시 1부터 매긴다. (2026-1학기 `MATH1` 1반 ≠ 2026-2학기 `MATH1` 1반)
- 분반마다 담당 강사 1명, 강의실, 요일·시간, 정원이 있다.
- 학생은 여러 분반을 수강신청한다. 신청일과 최종 성적(A~F, 학기 중엔 비어 있음)을 기록한다.
- **같은 학생이 같은 분반을 두 번 신청할 수는 없다.**

## 샘플 데이터

| 학기 | 과목 | 분반 | 강사 | 강의실 | 정원 |
|---|---|---|---|---|---|
| 2026-1 | MATH1 | 1 | 김수학 | 301 | 20 |
| 2026-1 | MATH1 | 2 | 이수학 | 302 | 20 |
| 2026-1 | ENG2 | 1 | 박영어 | 301 | 15 |
| 2026-2 | MATH1 | 1 | 김수학 | 303 | 25 |

## 할 일

1. 분반(section)이 Strong인지 Weak인지 판단하고 이유를 쓴다.
2. 분반의 식별자를 정한다.
3. 수강신청(enrollment) 테이블을 **두 가지 방식**으로 설계해본다.
   - (A) 분반의 식별자를 그대로 복합 FK로 받기
   - (B) 분반에 대리키를 붙이고 그걸 FK로 받기
4. 어느 쪽을 고를지, 이유와 함께 결정한다.

## 체크 질문

- "분반 1"이라는 값만으로 반을 찾을 수 있나? 무엇을 더 알아야 하나?
- 과목이 삭제되면 분반은? 분반이 삭제되면 수강신청은? (`ON DELETE` 정책)
- (A) 방식에서 수강신청 테이블의 PK는 컬럼이 몇 개가 되나?

<details>
<summary>💡 힌트</summary>

- 분반 번호는 19강에서 말한 **부분 키**(partial key)다. 아파트의 "1001호"처럼 동(과목 + 학기) 없이는 의미가 없다.
- 학기도 식별자의 일부다. 학기를 빼면 2026-1의 1반과 2026-2의 1반이 충돌한다.
- (A)는 자식 테이블로 갈수록 키가 길어진다. 그게 문제인지 아닌지 판단해본다.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 판단

- `section`은 **Weak entity**. 자기 속성(분반 번호)만으로는 식별이 안 되고, `course_code` + `term`을 빌려야 한다 → **식별 종속**.
- 과목이 없으면 그 과목의 분반도 존재할 수 없다 → **존재 종속**.
- 식별자 = `(term, course_code, section_no)` — 이 중 `section_no`가 부분 키.

### (A) 복합 키를 그대로 내려받기

```sql
CREATE TABLE course (
  course_code TEXT PRIMARY KEY,
  name        TEXT NOT NULL
);

CREATE TABLE section (
  term         TEXT     NOT NULL,          -- '2026-1'
  course_code  TEXT     NOT NULL REFERENCES course(course_code) ON DELETE RESTRICT,
  section_no   SMALLINT NOT NULL,          -- 부분 키
  instructor_id BIGINT  NOT NULL,
  room          TEXT,
  capacity      SMALLINT NOT NULL CHECK (capacity > 0),
  PRIMARY KEY (term, course_code, section_no)
);

CREATE TABLE enrollment (
  term         TEXT     NOT NULL,
  course_code  TEXT     NOT NULL,
  section_no   SMALLINT NOT NULL,
  student_id   BIGINT   NOT NULL,
  enrolled_at  DATE     NOT NULL,
  grade        CHAR(1)  CHECK (grade IN ('A','B','C','D','F')),
  PRIMARY KEY (term, course_code, section_no, student_id),     -- 4개!
  FOREIGN KEY (term, course_code, section_no)
    REFERENCES section(term, course_code, section_no) ON DELETE RESTRICT
);
```

### (B) 대리키 + UNIQUE

```sql
CREATE TABLE section (
  section_id    BIGSERIAL PRIMARY KEY,     -- 번호표
  term          TEXT     NOT NULL,
  course_code   TEXT     NOT NULL REFERENCES course(course_code) ON DELETE RESTRICT,
  section_no    SMALLINT NOT NULL,
  instructor_id BIGINT   NOT NULL,
  room          TEXT,
  capacity      SMALLINT NOT NULL CHECK (capacity > 0),
  UNIQUE (term, course_code, section_no) -- 진짜 식별 규칙은 그대로 지킨다
);

CREATE TABLE enrollment (
  enrollment_id BIGSERIAL PRIMARY KEY,
  section_id    BIGINT  NOT NULL REFERENCES section(section_id) ON DELETE RESTRICT,
  student_id    BIGINT  NOT NULL,
  enrolled_at   DATE    NOT NULL,
  grade         CHAR(1) CHECK (grade IN ('A','B','C','D','F')),
  UNIQUE (section_id, student_id)        -- 같은 반 중복 신청 방지
);
```

### 결정: (B)

| | (A) 복합 키 | (B) 대리키 + UNIQUE |
|---|---|---|
| 의미 전달 | 키만 봐도 "어느 학기 어느 과목 몇 반"인지 보임 | `section_id`만으로는 안 보임 (JOIN 필요) |
| 자식 테이블 | 출석, 과제 제출 … 내려갈수록 키 컬럼이 4개, 5개로 늘어남 | 항상 FK 하나 |
| 키 변경 | 분반 번호를 바꾸면 모든 자식 행 수정 | `section_id`는 그대로 |
| ORM · API | 복합 PK 설정이 번거로움 | `/sections/123` |

이 도메인은 분반 아래로 출석·과제·성적 등 **자식 테이블이 계속 생길 예정**이라 (B)가 낫다. 단, (B)를 고르더라도 **Weak entity라는 사실은 그대로**라서 `UNIQUE (term, course_code, section_no)`와 `NOT NULL` FK가 반드시 있어야 한다.

### 포인트

- `ON DELETE RESTRICT`: 수강생이 있는 분반을 실수로 지우면 성적 기록이 날아간다. 학사 데이터처럼 **이력이 중요한 곳은 CASCADE보다 RESTRICT**(또는 삭제 대신 `closed_at` 같은 상태 컬럼)가 안전하다.
- `grade`는 학기 중에 비어 있으니 NULL 허용. "값이 아직 없음"과 "값이 없음"을 구분해서 생각하기.

### 흔한 실수

- `section`의 UNIQUE에서 `term`을 빠뜨림 → 다음 학기에 1반을 만들 때 충돌.
- `section_no`를 전체에서 유일한 번호(1, 2, 3, … 157)로 바꿔서 Strong으로 만들기 → 모델은 단순해지지만, "MATH1 2반"이라는 현실의 이름을 잃는다. 학원 직원은 157번 반이 아니라 "수학1 2반"으로 말한다.

</details>
