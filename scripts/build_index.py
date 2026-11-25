"""노트의 frontmatter(date, tags)를 읽어 README.md를 다시 만든다.

노트 위치: YYYY/MM/DD-<slug>.md
표준 라이브러리만 쓴다 — Action에서 의존성 설치 없이 돈다.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTE_PATH = re.compile(r"^\d{4}/\d{2}/\d{2}-[^/]+\.md$")
TAG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RECENT_COUNT = 10


def parse_note(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT).as_posix()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit(f"{rel}: frontmatter(---)가 없다")
    meta = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()

    date = meta.get("date", "")
    expected = rel[:7].replace("/", "-") + "-" + rel[8:10]
    if date != expected:
        sys.exit(f"{rel}: date({date})가 경로 날짜({expected})와 다르다")

    raw_tags = meta.get("tags", "").strip("[]")
    tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
    if not tags:
        sys.exit(f"{rel}: tags가 비어 있다")
    for t in tags:
        if not TAG.match(t):
            sys.exit(f"{rel}: 태그 '{t}'는 소문자 케밥케이스가 아니다")

    title_match = re.search(r"^# (.+)$", text[m.end():], re.M)
    title = title_match.group(1).strip() if title_match else path.stem
    return {"path": rel, "date": date, "tags": tags, "title": title}


def build(notes: list[dict]) -> str:
    notes = sorted(notes, key=lambda n: n["path"], reverse=True)
    by_tag = defaultdict(list)
    for n in notes:
        for t in n["tags"]:
            by_tag[t].append(n)
    tags = sorted(by_tag, key=lambda t: (-len(by_tag[t]), t))

    def link(n: dict) -> str:
        return f"[{n['title']}]({n['path']})"

    out = [
        "# TIL",
        "",
        "> 이 파일은 `scripts/build_index.py`가 생성한다 — 직접 고치지 말 것.",
        "",
        f"노트 {len(notes)}개 · 태그 {len(tags)}개",
        "",
        "> 매일 푸는 RDB · DW 모델링 연습문제: [drills/](drills/README.md)",
        "",
        "## 최근 노트",
        "",
    ]
    out += [f"- {n['date']} {link(n)}" for n in notes[:RECENT_COUNT]]
    out += ["", "## 태그", ""]
    out.append(" · ".join(f"[`{t}`](#{t}) {len(by_tag[t])}" for t in tags))
    for t in tags:
        out += ["", f"### {t}", ""]
        out += [f"- {n['date']} {link(n)}" for n in by_tag[t]]
    return "\n".join(out) + "\n"


def main() -> None:
    notes = [
        parse_note(p)
        for p in ROOT.rglob("*.md")
        if NOTE_PATH.match(p.relative_to(ROOT).as_posix())
    ]
    (ROOT / "README.md").write_text(build(notes), encoding="utf-8")
    print(f"README.md: 노트 {len(notes)}개")


if __name__ == "__main__":
    main()
