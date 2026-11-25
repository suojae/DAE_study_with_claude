# RDB-01. 도서관 대출 — "책"과 "책 한 권"은 다르다

> 난이도 ★☆☆ · 연습 개념: 1:N, M:N, Gerund(속성 있는 관계) · 예상 20분

## 시나리오

동네 도서관의 대출 시스템을 만든다.

- 회원은 회원번호, 이름, 연락처를 가진다.
- 도서는 ISBN, 제목, 출판사, 출간연도가 있다. **저자는 여러 명**일 수 있고, 한 저자가 여러 책을 쓴다.
- 인기 있는 책은 **같은 책을 여러 권** 소장한다. 각 권에는 도서관이 붙인 **등록번호**(바코드)가 있고, 비치 위치(서가)가 다르다.
- 회원은 한 번에 **최대 5권**까지 빌린다. 대출마다 대출일, 반납 예정일, 실제 반납일을 기록한다.
- 같은 권은 시간이 지나면서 **여러 회원에게 여러 번** 대출된다. 단, **같은 시점에 두 명이 같은 권을 빌릴 수는 없다.**

## 샘플 데이터

| 등록번호 | ISBN | 제목 | 서가 |
|---|---|---|---|
| B-0001 | 978-89-001 | 데이터 모델링 입문 | A-3 |
| B-0002 | 978-89-001 | 데이터 모델링 입문 | A-3 |
| B-0003 | 978-89-777 | SQL 첫걸음 | C-1 |

| 회원 | 등록번호 | 대출일 | 반납 예정 | 반납일 |
|---|---|---|---|---|
| 홍길동 | B-0001 | 11-01 | 11-15 | 11-10 |
| 김철수 | B-0001 | 11-12 | 11-26 | (미반납) |
| 홍길동 | B-0002 | 11-12 | 11-26 | (미반납) |

## 할 일

1. 엔티티와 관계를 찾아 ERD를 그린다 (카디널리티 포함).
2. PostgreSQL 기준 DDL을 쓴다.
3. 아래 쿼리가 가능한지 확인한다.
   - "데이터 모델링 입문" 중 지금 빌릴 수 있는 권은?
   - 홍길동이 지금 빌리고 있는 책 목록

## 체크 질문

- 샘플 데이터에서 "데이터 모델링 입문"이 두 줄인 이유는? 이걸 테이블 하나로 두면 무슨 문제가 생기나?
- 대출일·반납일은 회원에 붙나, 책에 붙나, 아니면 다른 곳에 붙나?
- "같은 시점에 같은 권을 두 명이 못 빌린다"는 규칙을 **DB가** 지키게 하려면?

<details>
<summary>💡 힌트</summary>

- 도서관에는 "작품으로서의 책(ISBN)"과 "서가에 꽂힌 물리적인 한 권(등록번호)"이 따로 있다.
- 대출 = 회원과 "한 권" 사이의 관계인데, 자기 속성(대출일·반납일)이 있다 → 22강의 Gerund.
- 미반납 = `returned_at IS NULL`. PostgreSQL은 **조건부 UNIQUE 인덱스**(partial index)를 지원한다.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 엔티티와 관계

```
author >──< book ──< book_copy ──< loan >── member
         (book_author)
```

| 관계 | 카디널리티 | 메모 |
|---|---|---|
| book – author | M:N | `book_author`로 풀고 저자 순서(`author_order`)를 속성으로 |
| book – book_copy | 1:N | 책 1종에 여러 권. 한 권은 반드시 한 책에 속함 (최소 1) |
| book_copy – loan | 1:N | 한 권은 시간에 따라 여러 번 대출 |
| member – loan | 1:N | 회원 한 명이 여러 번 대출 |

### DDL

```sql
CREATE TABLE member (
  member_id   BIGSERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  phone       TEXT
);

CREATE TABLE book (
  isbn          TEXT PRIMARY KEY,           -- 자연키가 안정적이라 그대로 PK
  title         TEXT NOT NULL,
  publisher     TEXT,
  published_year INT
);

CREATE TABLE author (
  author_id   BIGSERIAL PRIMARY KEY,
  name        TEXT NOT NULL
);

CREATE TABLE book_author (                  -- M:N 해소. 순수 연결 테이블 → 복합 PK
  isbn         TEXT   NOT NULL REFERENCES book(isbn),
  author_id    BIGINT NOT NULL REFERENCES author(author_id),
  author_order SMALLINT NOT NULL,           -- 제1저자, 공저자 순서
  PRIMARY KEY (isbn, author_id)
);

CREATE TABLE book_copy (
  copy_id     TEXT PRIMARY KEY,             -- 등록번호(바코드)
  isbn        TEXT NOT NULL REFERENCES book(isbn),
  shelf       TEXT
);

CREATE TABLE loan (                         -- Gerund: 관계인데 자기 속성이 있음
  loan_id     BIGSERIAL PRIMARY KEY,
  member_id   BIGINT NOT NULL REFERENCES member(member_id),
  copy_id     TEXT   NOT NULL REFERENCES book_copy(copy_id),
  loaned_at   DATE   NOT NULL,
  due_at      DATE   NOT NULL,
  returned_at DATE,                         -- NULL = 아직 대출 중
  CHECK (due_at >= loaned_at),
  CHECK (returned_at IS NULL OR returned_at >= loaned_at)
);

-- "같은 권은 동시에 한 명만": 미반납 대출은 권마다 최대 1개
CREATE UNIQUE INDEX uq_loan_open_copy ON loan (copy_id) WHERE returned_at IS NULL;
```

### 쿼리 확인

```sql
-- 지금 빌릴 수 있는 권
SELECT c.copy_id, c.shelf
FROM book_copy c
JOIN book b ON b.isbn = c.isbn
WHERE b.title = '데이터 모델링 입문'
  AND NOT EXISTS (
    SELECT 1 FROM loan l WHERE l.copy_id = c.copy_id AND l.returned_at IS NULL
  );
```

### 포인트

- **책(book) ≠ 한 권(book_copy).** 테이블 하나로 두면 제목·출판사가 권 수만큼 중복되고, 제목을 고치면 여러 행을 고쳐야 한다. 현실에서 "무엇을 세는가"를 먼저 정하면 엔티티가 갈린다.
- `loan`은 회원과 한 권을 잇는 관계지만 대출일·반납일이 있어서 **테이블**이 된다. 대출일을 `book_copy`에 넣으면 이력이 사라진다.
- `loan`에 `(copy_id, member_id)` UNIQUE를 걸면 **틀린다.** 같은 사람이 같은 권을 나중에 또 빌릴 수 있다. 진짜 규칙은 "미반납 대출이 권마다 하나"다.
- "최대 5권"은 행 하나만 봐서는 판단할 수 없는 규칙이라 CHECK로 못 건다. 앱 로직 + 트랜잭션(또는 트리거)으로 처리한다. **모든 규칙을 DB 제약으로 걸 수 있는 건 아니다**는 것도 알아두기.

### 흔한 실수

- `book`에 `is_loaned BOOLEAN` 컬럼 → 권이 여러 개면 의미가 없고, 대출 이력도 남지 않는다.
- 저자를 `authors TEXT` 컬럼에 "홍길동, 김철수"로 저장 → 저자별 검색·집계가 불가능 (1정규형 위반).

</details>
