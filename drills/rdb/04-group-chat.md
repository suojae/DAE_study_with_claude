# RDB-04. 단체 채팅방 — 연결 테이블에 규칙 심기

> 난이도 ★★☆ · 연습 개념: 속성 있는 M:N, 복합 FK로 비즈니스 규칙 강제, 재귀(답장) · 예상 30분

## 시나리오

메신저의 채팅 기능을 설계한다.

- 사용자는 여러 채팅방에 참여하고, 채팅방에는 여러 사용자가 있다.
- 방마다 참여자의 **역할**(방장 · 부방장 · 일반), **참여 시각**, **알림 on/off**가 다르다.
- 방에서 나갔다가 **다시 들어올 수 있다.**
- 메시지는 보낸 사람, 방, 내용, 보낸 시각이 있다. **방 멤버만** 메시지를 보낼 수 있다.
- 메시지는 다른 메시지에 **답장**할 수 있다.
- 사용자마다 방별로 **어디까지 읽었는지** 저장해서 "안 읽은 메시지 수"를 보여준다.

## 샘플 데이터

| 방 | 사용자 | 역할 | 참여 | 나감 |
|---|---|---|---|---|
| 데이터팀 | 종혁 | 방장 | 10-01 | — |
| 데이터팀 | 민수 | 일반 | 10-03 | 10-20 |
| 데이터팀 | 민수 | 일반 | 11-02 | — |

| msg_id | 방 | 보낸 사람 | 내용 | 답장 대상 |
|---|---|---|---|---|
| 101 | 데이터팀 | 종혁 | 배포했어요 | — |
| 102 | 데이터팀 | 민수 | 확인! | 101 |

## 할 일

1. ERD를 그린다. 멤버십(방-사용자)이 왜 테이블이 되는지 설명한다.
2. "방 멤버만 메시지를 보낼 수 있다"를 **앱 코드 없이 DB 제약으로** 강제할 방법을 찾는다.
3. 재입장(민수) 처리 방식을 정한다.
4. 읽음 처리를 어떻게 저장할지 정한다. (메시지 × 사용자마다 행을 만들면?)

## 체크 질문

- 역할 · 참여 시각은 사용자에 붙나, 방에 붙나?
- `message.sender_id`가 `user`만 참조하면 어떤 잘못된 데이터가 들어올 수 있나?
- 1,000명 방에 메시지 1만 개면 "메시지별 읽음 테이블"은 몇 행이 되나?

<details>
<summary>💡 힌트</summary>

- 메시지가 `(room_id, user_id)`를 **멤버십 테이블에 복합 FK**로 걸면, 멤버가 아닌 조합은 INSERT 자체가 실패한다.
- 재입장: (a) 행을 하나로 두고 `left_at`만 갱신 vs (b) 참여할 때마다 새 행(이력). (b)라면 UNIQUE를 어떻게 걸어야 할까?
- 읽음은 "어디까지 읽었나" 하나만 있으면 된다 → `last_read_message_id`.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 구조

```
app_user ──< room_member >── room
               │
               └──< message (sender) ── reply_to → message (재귀)
```

`room_member`는 Gerund다. 역할 · 참여 시각 · 알림 설정 · 읽은 위치는 **"이 사람이 이 방에서"**의 속성이라 사용자에도 방에도 붙일 수 없다.

### DDL (재입장은 행 하나를 재사용하는 방식)

```sql
CREATE TABLE app_user (
  user_id  BIGSERIAL PRIMARY KEY,
  nickname TEXT NOT NULL
);

CREATE TABLE room (
  room_id    BIGSERIAL PRIMARY KEY,
  title      TEXT,
  is_direct  BOOLEAN NOT NULL DEFAULT FALSE,   -- 1:1 방 여부
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE room_member (
  room_id              BIGINT NOT NULL REFERENCES room(room_id),
  user_id              BIGINT NOT NULL REFERENCES app_user(user_id),
  role                 TEXT   NOT NULL DEFAULT 'member'
                         CHECK (role IN ('owner', 'admin', 'member')),
  joined_at            TIMESTAMPTZ NOT NULL,
  left_at              TIMESTAMPTZ,                  -- NULL = 참여 중
  notify               BOOLEAN NOT NULL DEFAULT TRUE,
  last_read_message_id BIGINT,                       -- 읽음 위치
  PRIMARY KEY (room_id, user_id)                     -- 순수 연결 + 자식(message)이 복합 FK로 참조
);

CREATE TABLE message (
  message_id  BIGSERIAL PRIMARY KEY,
  room_id     BIGINT NOT NULL,
  sender_id   BIGINT NOT NULL,
  body        TEXT   NOT NULL,
  sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  reply_to_id BIGINT REFERENCES message(message_id),  -- 재귀 1:N
  FOREIGN KEY (room_id, sender_id)
    REFERENCES room_member(room_id, user_id)          -- 멤버만 보낼 수 있다
);

CREATE INDEX ix_message_room_time ON message (room_id, message_id);

-- 방장은 방마다 1명
CREATE UNIQUE INDEX uq_room_owner ON room_member (room_id) WHERE role = 'owner';
```

### 재입장: 왜 "행 재사용"을 골랐나

| | (a) 행 하나, `left_at` 갱신 | (b) 참여할 때마다 새 행 |
|---|---|---|
| PK / UNIQUE | `(room_id, user_id)` | `(room_id, user_id, joined_at)` + "참여 중은 하나" partial UNIQUE |
| 메시지의 복합 FK | 단순 | `joined_at`까지 들고 다녀야 해서 복잡 |
| 참여 이력 | 마지막 기록만 | 전부 남음 |

메신저에서 "언제 들어왔다 나갔다"의 전체 이력은 핵심 기능이 아니라고 보고 (a)를 골랐다. 이력이 필요하면 **`room_member_event`(입장/퇴장 로그)를 별도 테이블**로 두는 게, 멤버십 테이블을 복잡하게 만드는 것보다 낫다.

### 안 읽은 메시지 수

```sql
SELECT count(*)
FROM message m
JOIN room_member rm ON rm.room_id = m.room_id AND rm.user_id = :me
WHERE m.room_id = :room
  AND m.message_id > COALESCE(rm.last_read_message_id, 0);
```

메시지 × 사용자마다 읽음 행을 만들면 1,000명 × 1만 = **1,000만 행**. "어디까지 읽었나" 하나면 1,000행이다. 메시지 ID가 시간 순으로 증가한다는 성질을 이용한 설계다.

### 포인트

- **복합 FK는 규칙을 심는 도구다.** `message.sender_id → app_user`로만 걸면 방에 없는 사람의 메시지가 들어갈 수 있다. `(room_id, sender_id) → room_member`로 걸면 DB가 거부한다. 자식이 참조할 거라면 연결 테이블의 PK를 복합 키로 두는 게 오히려 유리한 경우.
- 나간 멤버의 과거 메시지는 남아야 하므로 멤버십 행을 **지우지 않고** `left_at`만 채운다. 그래서 FK도 깨지지 않는다.
- 단, 이 제약은 "지금 참여 중"까지는 보장하지 못한다 (`left_at`이 찬 멤버도 FK는 통과). 그 부분은 앱 로직 몫.

### 흔한 실수

- `room`에 `member_ids BIGINT[]` 배열 → 멤버별 역할·알림 설정을 둘 곳이 없다.
- 1:1 방의 중복 생성 (A→B 방과 B→A 방이 따로 생김). `(least(a,b), greatest(a,b))` 조합에 UNIQUE를 거는 별도 테이블로 막을 수 있다.

</details>
