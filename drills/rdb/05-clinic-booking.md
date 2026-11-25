# RDB-05. 병원 예약 — 셋이 동시에 만나는 관계

> 난이도 ★★★ · 연습 개념: 3항(Ternary) 관계, 2항으로 쪼개면 안 되는 이유, 시간 겹침 방지 · 예상 30분

## 시나리오

동네 의원 여러 곳을 묶은 예약 시스템이다.

- 의사, 환자, 진료실이 있다.
- **예약** = 환자가 특정 시간에 특정 의사에게 특정 진료실에서 진료받는 것.
- 의사는 날마다 쓰는 진료실이 바뀐다. 같은 날에도 오전 · 오후가 다를 수 있다.
- 진료 시간은 기본 30분이지만 **초진은 60분**이다.
- 같은 시간에 겹치면 안 되는 것: **의사**, **진료실**, **환자**.
- 진료가 끝나면 진단(상병코드)을 **여러 개** 기록한다.
- 예약은 취소될 수 있다. 취소된 예약은 남겨두지만 겹침 검사에서는 빠진다.

## 샘플 데이터

| 예약 | 환자 | 의사 | 진료실 | 시작 | 종료 | 상태 |
|---|---|---|---|---|---|---|
| 1 | 김환자 | 이의사 | 1진료실 | 09:00 | 10:00 | 완료 |
| 2 | 박환자 | 이의사 | 1진료실 | 10:00 | 10:30 | 완료 |
| 3 | 최환자 | 정의사 | 1진료실 | 14:00 | 14:30 | 예약 |
| 4 | 김환자 | 이의사 | 2진료실 | 15:00 | 15:30 | 취소 |

## 할 일

1. 예약을 **2항 관계 두 개**(환자–의사, 의사–진료실)로 쪼개면 어떤 정보가 사라지는지 샘플 데이터로 보여준다.
2. 예약 테이블을 설계한다.
3. "의사 · 진료실 · 환자는 같은 시간에 겹치면 안 된다"를 DB 제약으로 건다. 진료 시간이 30분과 60분으로 **다르다**는 점에 주의한다.
4. 진단 기록을 설계한다.

## 체크 질문

- `UNIQUE (doctor_id, start_at)`로 겹침을 막을 수 있나? 09:00~10:00 예약이 있는데 09:30 예약이 들어오면?
- 진단은 예약에 붙나, 환자에 붙나?

<details>
<summary>💡 힌트</summary>

- 2항으로 쪼개면 "이의사가 1진료실을 쓴 적 있다"와 "이의사가 김환자를 본 적 있다"는 남지만, **김환자를 몇 시에 어느 방에서** 봤는지는 다시 조합할 수 없다.
- 길이가 다른 구간의 겹침은 UNIQUE로 못 막는다. PostgreSQL에는 구간 타입(`tstzrange`)과 `EXCLUDE USING gist` 제약이 있다.
- 취소 건을 제외하려면 EXCLUDE에도 `WHERE` 조건을 붙일 수 있다.

</details>

<details>
<summary>✅ 모범 답안</summary>

### 2항으로 쪼개면

| 의사–진료실 | 의사–환자 |
|---|---|
| 이의사–1진료실 | 이의사–김환자 |
| 이의사–2진료실 | 이의사–박환자 |

김환자가 1진료실에서 봤는지 2진료실에서 봤는지 알 수 없다. 시간까지 넣으면 더 꼬인다. 세 엔티티가 **한 사건에 동시에** 참여하면 3항 관계로 둬야 한다.

### DDL

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- EXCLUDE에서 = 비교를 쓰기 위해

CREATE TABLE doctor  (doctor_id  BIGSERIAL PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE patient (patient_id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE room    (room_id    BIGSERIAL PRIMARY KEY, name TEXT NOT NULL);

CREATE TABLE appointment (                      -- 3항 관계 + 자기 속성 = Gerund
  appointment_id BIGSERIAL PRIMARY KEY,
  patient_id     BIGINT NOT NULL REFERENCES patient(patient_id),
  doctor_id      BIGINT NOT NULL REFERENCES doctor(doctor_id),
  room_id        BIGINT NOT NULL REFERENCES room(room_id),
  period         TSTZRANGE NOT NULL,            -- [시작, 종료)
  visit_type     TEXT NOT NULL CHECK (visit_type IN ('first', 'follow_up')),
  status         TEXT NOT NULL DEFAULT 'booked'
                   CHECK (status IN ('booked', 'done', 'cancelled', 'no_show')),
  CHECK (NOT isempty(period)),

  -- 취소된 예약은 빼고, 같은 의사 / 진료실 / 환자의 시간 구간이 겹치면 거부
  EXCLUDE USING gist (doctor_id  WITH =, period WITH &&) WHERE (status <> 'cancelled'),
  EXCLUDE USING gist (room_id    WITH =, period WITH &&) WHERE (status <> 'cancelled'),
  EXCLUDE USING gist (patient_id WITH =, period WITH &&) WHERE (status <> 'cancelled')
);

CREATE TABLE diagnosis_code (
  code TEXT PRIMARY KEY,                        -- 상병코드
  name TEXT NOT NULL
);

CREATE TABLE appointment_diagnosis (            -- 예약 ↔ 진단 M:N
  appointment_id BIGINT NOT NULL REFERENCES appointment(appointment_id),
  code           TEXT   NOT NULL REFERENCES diagnosis_code(code),
  is_primary     BOOLEAN NOT NULL DEFAULT FALSE, -- 주상병
  PRIMARY KEY (appointment_id, code)
);
```

`&&`는 "두 구간이 겹친다", `[)` 구간이라 10:00에 끝나는 예약과 10:00에 시작하는 예약은 **겹치지 않는다.**

### 왜 UNIQUE로는 안 되나

`UNIQUE (doctor_id, start_at)`은 **시작 시각이 똑같을 때만** 막는다. 09:00~10:00 예약이 있을 때 09:30 예약은 시작 시각이 달라서 통과한다. 고정 30분 슬롯만 있다면 UNIQUE로 충분하지만, 길이가 섞이면 구간 겹침 제약이 필요하다.

### 포인트

- 진단은 **예약(진료 1회)**에 붙는다. 환자에 붙이면 "언제 진료에서 내린 진단인지"를 잃는다.
- 취소는 삭제가 아니라 상태값. 취소율, 노쇼율 같은 분석에 필요하다 (→ DW 연습과 연결).
- 의사의 진료실 배정표(`doctor_room_schedule`)를 따로 두고, 예약은 배정표 안에서만 잡히게 하는 설계도 가능하다. 그러면 예약은 사실상 "배정표 슬롯–환자"의 2항 관계가 된다. **3항으로 둘지 2항 두 단계로 둘지는 업무 흐름에 따라** 정한다.

### 흔한 실수

- 시작과 종료를 `start_at`, `end_at` 두 컬럼으로만 두고 겹침 검사를 앱에서 `SELECT` 후 `INSERT` → 동시 예약 두 건이 둘 다 통과한다 (경쟁 상태).
- 진단 코드를 `appointment.diagnoses TEXT = 'J00,J02'`로 저장.

</details>
