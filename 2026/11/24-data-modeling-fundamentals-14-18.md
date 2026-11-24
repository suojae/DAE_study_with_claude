---
date: 2026-11-24
tags: [data-modeling, er-diagram, dimensional-modeling, dbt, data-quality]
---

# 데이터 모델링 기초 — 관계 · 엔티티 계층 · 속성 제약 (14~18강)

> 강의: Udemy *Mastering Data Modeling Fundamentals* (Alan Simon)
> 범위: 14강 ~ 18강 + 질문하면서 정리한 내용

---

## 1. 14강 — 관계 (Relationships)

- 관계 = 엔티티 사이의 **개념적 연결**. 이름(동사)을 붙이고, 정보·제약을 담을 수 있다.
- **표기법별 차이**
  - Classic E-R(Chen): 엔티티 사이에 **마름모** → 이름은 마름모 안(또는 위)
  - Crow's foot: **선 하나**로 연결 → 이름은 선 위(위아래 배치면 옆)
- **Single naming vs Double naming**
  - Single: 이름 하나 → `Teacher teaches Class` ✅ / `Class teaches Teacher` ❌
  - Double: 읽는 방향마다 이름 → `teaches` / `is taught by`
  - 툴이 이름 하나만 허용하면 → `Teaches / Taught by`처럼 **슬래시**로 이어 쓴다
- 관계 이름을 따라 모델을 "탐색"하며 **비즈니스 규칙을 검증**한다
  - 교사 한 명이 수업 몇 개? 교사가 두 학과에 소속 가능? 학생 0명 수업도 수업인가?
  - 👉 "상식으로 생각하지 말고, **비즈니스 규칙**이 뭔지 생각하라"
- 예고: 카디널리티, Binary / Ternary / Recursive 관계 (섹션 5)

---

## 2. 16강 — 왜 현실의 복잡성이 중요한가 (섹션 4 도입)

- 개념 모델의 목표 = **현실과 최대한 가깝게** 그리기 → 실제 DB에 맞추는 건 그다음
- 현실은 **규칙과 제약** 투성이 → 모델에 담아야 한다
- 섹션 4 순서: **계층(17) → 속성 제약(18) → 강한/약한 엔티티(19)**
  - 보는 범위가 넓어지는 순서: 엔티티 구성 → 엔티티 내부 → 엔티티 사이
  - 강한/약한 엔티티는 관계(섹션 5)로 넘어가는 **다리**

| 단계 | 보는 범위 | 질문 |
|---|---|---|
| 계층 | 엔티티 구성 | 무엇을 나누고 무엇을 묶을까? |
| 속성 제약 | 엔티티 내부 | 이 값은 어떤 규칙을 지켜야 하나? |
| 강/약 엔티티 | 엔티티 사이 | 이 엔티티는 혼자 존재할 수 있나? |
| 관계 (섹션 5) | 엔티티 사이 | 몇 개와 어떻게 연결되나? |

---

## 3. 17강 — 엔티티 계층 (Hierarchies)

### 언제 쓰나
- 두 개 이상의 엔티티가 **많이 비슷한데 일부가 다를 때**
- 예: 정년트랙 교수(tenure year) vs 겸임 강사(contract length) — ID·이름·주소는 공통

### 따로 두면 생기는 문제
- `teaches` 관계를 **두 번** 그려야 함
- "전체 강사의 수업" 조회 시 두 데이터를 **UNION** 해야 함 → 불필요하게 복잡

### 해결: 슈퍼타입 / 서브타입
```
          Faculty Member  ← 부모 (Supertype): 공통 속성
           /            \
  Tenure-class        Adjunct  ← 자식 (Subtype): 고유 속성
```
- 관계는 부모 하나에만: `Faculty Member teaches Class`
- **상속(Inheritance)**: 자식은 부모 속성을 논리적으로 물려받는다 (DB 저장 방식이 아니라 의미상)
- 계층 = 특별한 엔티티이자 **특별한 관계(is-a)**

### is-a vs has-a
| | is-a | has-a |
|---|---|---|
| 뜻 | A는 B의 **한 종류**다 | A가 B를 **가진다 / 연결된다** |
| 예 | 겸임 강사 → 교수 | 교수 → 수업 |
| 모델링 | **계층** | **관계** |

👉 판별법: "A**는** B**이다**"가 말이 되면 is-a

### Exclusive vs Inclusive
| | Exclusive (배타적) | Inclusive (포괄적) |
|---|---|---|
| 의미 | 자식 중 **하나만** (XOR) | **둘 다** 가능 (OR) |
| 예 | 교수 = 정년트랙 **또는** 겸임 | 대학 직원 = 교수 / 행정 / **둘 다** |
| 표기 | **X** 있음 | X 없음 |
| 구현 | `type` 컬럼 하나 | `is_faculty`, `is_admin` 등 여부 컬럼 / 역할 테이블 |

- Crow's foot에서는 **반달 기호** (X 유무로 구분)
- **다단계 계층** 가능 (대학 직원[포괄] → 교수[배타] → 정년/겸임), 어느 층이든 관계를 맺을 수 있음
- ⚠️ 배타적으로 만들었다가 "둘 다"인 사람이 생기면 구조를 갈아엎어야 함 → 처음에 꼭 물어보기

---

## 4. 18강 — 속성 제약 (Attribute Constraints)

### ① 데이터 타입 / 크기
- `CREATE TABLE`에서 컬럼 타입 정하는 것과 같은 개념
- 개념 모델에선 대략적으로(string) → 논리 모델로 갈 때 툴이 DB 타입으로 **매핑**(VARCHAR 등)

### ② NULL 허용 여부 ⭐
- **기계적으로 NOT NULL 붙이지 말고 실제 데이터를 보고** 정하라 ("샘플 데이터가 친구다")
- 예: `first_name` — 이름이 하나뿐인 사람도 있음 → NULL 허용 or NOT NULL + `[none]` 표시값
- `address_2`는 보통 NULL 허용
- NULL을 허용해야 하는 상황
  - 데이터가 **점점 채워지는** 경우 (마케팅 리드: IP → 이름 → 주소…)
  - **서드파티 데이터** (품질 통제 불가)
  - 공공 보건 클리닉 사례: NOT NULL로 막으면 **데이터를 아예 못 받음**

### ③ 값의 범위 / 목록
- 범위: 학생 나이 10~20, 교수 나이 18~120, 등록금 $0~$50,000
- 목록: 교수 직급(Professor / Associate / Assistant / Lecturer), 학년(Freshman … **Unspecified**)
- 👉 `Unspecified` = 모르면 NULL 대신 **"모름"을 명시적인 값으로** 넣는 방법

### dbt 테스트와 대응
| 강의 개념 | dbt |
|---|---|
| NOT NULL | `not_null` |
| 허용 값 목록 | `accepted_values` |
| 범위 | `dbt_utils.accepted_range` |

---

## 5. 질문하면서 정리한 것들

### Chen 표기법 vs Crow's foot
| | Chen (Classic E-R) | Crow's foot (IE) |
|---|---|---|
| 엔티티 / 관계 / 속성 | 사각형 / **마름모** / **타원** | 사각형 / **선** / 사각형 **안 목록** |
| 카디널리티 | 1, N, M | 선 끝 **까마귀 발** |
| 주로 쓰는 곳 | 교과서, 정보처리기사 | 실무 툴 (ERDCloud, dbdiagram, Workbench, DataGrip, ERwin) |

- Chen 추가 기호: 밑줄 타원 = 식별자, 이중 타원 = 다중값 속성, 이중 사각형 = 약한 엔티티
- 실무에서 Chen을 잘 안 쓰는 이유: 컬럼이 많으면 타원이 폭발함

### 계층이 항상 좋은가? → 개념 모델 ≠ 물리 모델
- 개념 모델: 현실의 **의미**를 기록 → 계층으로 그리는 게 맞음
- 물리 모델: **조회 패턴**을 보고 구현 방식을 고름

| 방식 | 구조 | 장점 | 단점 |
|---|---|---|---|
| ① Single Table | 한 테이블 + `type` 컬럼 | JOIN 없음, 단순 | 해당 없는 컬럼은 NULL |
| ② Joined | 부모 + 자식 테이블 | 개념 모델과 1:1, 정규화 | 조회마다 JOIN |
| ③ Concrete Table | 자식 테이블만 (공통 컬럼 중복) | 한 종류만 조회 시 빠름 | 전체 조회 시 UNION |

- "tenure 교수만 자주 조회" → ③ 또는 ① + type 필터
- 분석(dbt mart)에서는 용도별로 다시 만듦 (`dim_faculty`에 `faculty_type` 등)
- JPA `@Inheritance(SINGLE_TABLE / JOINED / TABLE_PER_CLASS)`와 그대로 대응

### 상속은 ERD에서 어떻게? → PK 공유 1:1 FK
```sql
CREATE TABLE faculty (
  faculty_id   BIGINT PRIMARY KEY,
  faculty_type VARCHAR(10) NOT NULL  -- 구분자
);
CREATE TABLE tenure_faculty (
  faculty_id  BIGINT PRIMARY KEY,                          -- PK이면서
  FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)  -- FK
);
```
- 일반 FK와 차이: **PK = FK**, **1:0..1**, 의미가 **is-a**
- 배타/포괄은 FK만으로 강제 불가 → 구분자 컬럼 + 앱 로직/트리거/CHECK
- 대부분의 ERD 툴은 서브타입 기호가 없어 **1:1 관계선 + 주석**으로 그림

### PK = FK면 상속인가? → 아니다 (둘 다 "그럴 수도 있다")
- PK = FK인데 상속이 아닌 경우: **1:1 수직 분할** (`user_settings`) — has-a
- 상속인데 PK = FK가 아닌 경우
  - ① Single Table (FK 없음), ③ Concrete Table (부모 없음)
  - 자식이 자체 `id` PK + **FK 컬럼에 UNIQUE**
- 1:1의 핵심 = FK가 **자식 테이블 안에서** unique (부모에서 unique한 건 모든 FK가 그렇다)
- 상속 의심 체크리스트
  1. 같은 부모 PK를 참조하는 자식 테이블이 여러 개?
  2. 부모에 구분자 컬럼(`type`, `role`, `kind`)?
  3. 부모 행 **일부만** 자식에 존재?
  4. 자식마다 고유 속성이 다름?
  5. **"A는 B의 한 종류다"가 말이 되나?** ← 최종 판정
- 실무에선 **type 컬럼 + 특정 type일 때만 채워지는 컬럼 묶음** 형태로 숨어 있는 경우가 많음

### 킴벌: 차원에 NULL 대신 'Unknown' 행
- fact의 FK가 NULL이면 → JOIN에서 행이 **조용히 빠져** 합계가 틀림 (에러도 안 남)
- 해결: dimension에 `(-1, 'Unknown')` 행을 미리 만들고, fact에서 NULL 대신 `-1`
  - 합계가 맞고, "출처 모르는 매출"이라는 **품질 문제도 보임**
- dimension 속성값도 NULL 대신 `'Unknown'` (차트 라벨·필터 문제 방지)
- 구분해서 쓰기: **Unknown**(있어야 하는데 모름) vs **Not Applicable**(애초에 해당 없음)
- dbt: `COALESCE(key, -1)` + dimension에 Unknown 행 `UNION ALL` + `not_null`·`relationships` 테스트
- 18강의 `Unspecified`와 같은 아이디어

### 현업에서도 강의 순서대로 하나?
- 아니다. 강의 순서 = **배우기 쉬운 순서**. 현업은 왔다 갔다 하며 반복
- **OLTP 실무 흐름**
  1. 요구사항에서 명사(엔티티)·동사(관계) 뽑기
  2. 핵심 엔티티 + 관계 + **카디널리티** 러프하게 (N:M이면 중간 엔티티)
  3. 식별자(PK) → 강한/약한 엔티티가 갈림
  4. 속성 + 제약
  5. 계층 판단 (속성 채우다 발견되는 경우가 많음)
  6. 물리 모델 (조회 패턴, 반정규화, 인덱스)
  7. 쓰면서 수정
- **분석(킴벌) 흐름**: 질문 → 비즈니스 프로세스 → **Grain** → Dimension/Fact → 원천 매핑 → dbt(staging → intermediate → mart)
- 기존 DB를 거꾸로 읽는 **역공학**이 실무에선 더 흔함
- 순서보다 중요한 것 = **질문을 빠뜨리지 않는 것**

---

## 6. 핵심 질문 체크리스트

- [ ] A는 B의 한 종류인가? → 계층(is-a) / 관계(has-a)
- [ ] 둘 다일 수 있나? → Exclusive / Inclusive
- [ ] 이 값은 비어도 되나? 실제 데이터는 어떤가?
- [ ] 값의 범위·목록이 정해져 있나? 모를 땐 `Unknown`/`Unspecified`?
- [ ] 이 엔티티는 혼자 존재할 수 있나? (19강)
- [ ] 몇 대 몇 관계인가? (섹션 5)

## 7. 다음에 할 것
- 19강: 강한 / 약한 엔티티
- 20강 정리 + 과제 2 (Entity and Attribute Constraints)
- 강의마다 오르비 실제 데이터에 대입해보기
  - 회원 테이블에 숨은 계층? 학생·강사·학부모는 배타적? 포괄적?
  - 적재 중인 테이블에 NULL이면 안 되는데 NULL인 컬럼?
  - 부모 없이 의미 없는 테이블?
