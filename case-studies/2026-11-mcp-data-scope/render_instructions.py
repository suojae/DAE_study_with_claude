"""봇이 받는 서버 소개 글(instructions·list_metrics 설명)을 비교용 PNG로 그린다.

사용: python3 render_instructions.py <입력.json> <AS-IS|TO-BE> <출력.png>
입력 JSON: {"instructions": "...", "list_metrics": "..."}
"다루는 데이터"로 시작하는 문단은 강조 표시한다.
"""

import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCOPE_MARK = "다루는 데이터"


def block(text: str) -> str:
    out = []
    for para in text.split("\n\n"):
        body = html.escape(para)
        if SCOPE_MARK in para.split("\n")[0]:
            out.append(f'<div class="scope">{body}</div>')
        elif SCOPE_MARK in para:
            head, _, tail = para.partition(SCOPE_MARK)
            out.append(f'<div>{html.escape(head)}<span class="scope">{html.escape(SCOPE_MARK + tail)}</span></div>')
        else:
            out.append(f"<div>{body}</div>")
    return "\n".join(out)


def page(data: dict, label: str) -> str:
    has_scope = SCOPE_MARK in data["instructions"]
    badge = (
        '<span class="badge ok">다루는 데이터 목록 있음</span>'
        if has_scope
        else '<span class="badge no">다루는 데이터 목록 없음</span>'
    )
    return f"""<!doctype html><meta charset="utf-8"><style>
body {{ margin:0; background:#fff; font-family:-apple-system,"Apple SD Gothic Neo",sans-serif; color:#1f2328; }}
.wrap {{ width:960px; padding:32px; }}
h1 {{ font-size:24px; font-weight:600; margin:0 0 6px; }}
.sub {{ color:#59636e; font-size:15px; margin-bottom:16px; }}
.badge {{ display:inline-block; padding:6px 12px; border-radius:6px; font-size:15px; font-weight:600; margin-bottom:20px; }}
.badge.no {{ background:#ffebe9; color:#a40e26; }} .badge.ok {{ background:#dafbe1; color:#116329; }}
.panel {{ border:1px solid #d1d9e0; border-radius:10px; margin-bottom:18px; overflow:hidden; }}
.cap {{ background:#f6f8fa; border-bottom:1px solid #d1d9e0; padding:10px 16px; font-family:Menlo,monospace; font-size:14px; color:#59636e; }}
.txt {{ padding:16px; font-family:Menlo,"Apple SD Gothic Neo",monospace; font-size:14px; line-height:1.6; white-space:pre-wrap; }}
.txt > div + div {{ margin-top:12px; }}
.scope {{ background:#dafbe1; border-left:4px solid #1a7f37; padding:8px 12px; display:block; }}
</style><div class="wrap">
<h1>{label} · 봇이 받는 서버 소개</h1>
<div class="sub">MCP 클라이언트는 이 두 글만 보고 서버를 부를지 정한다</div>
{badge}
<div class="panel"><div class="cap">initialize → result.instructions</div><div class="txt">{block(data["instructions"])}</div></div>
<div class="panel"><div class="cap">tools/list → list_metrics.description</div><div class="txt">{block(data["list_metrics"])}</div></div>
</div>"""


def crop(path: Path) -> None:
    img = Image.open(path).convert("RGB")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    box = ImageChops.difference(img, bg).getbbox()
    if box:
        pad = 64
        img.crop((0, 0, img.width, min(img.height, box[3] + pad))).save(path)


def main() -> None:
    src, label, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]).resolve()
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as d:
        page_path = Path(d) / "page.html"
        page_path.write_text(page(data, label), encoding="utf-8")
        subprocess.run(
            [CHROME, "--headless", "--hide-scrollbars", "--force-device-scale-factor=2",
             "--window-size=1024,4000", f"--screenshot={out}", page_path.as_uri()],
            check=True, capture_output=True,
        )
    crop(out)
    print(out)


if __name__ == "__main__":
    main()
