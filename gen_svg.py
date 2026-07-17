#!/usr/bin/env python3
"""One-off generator for dark_mode.svg / light_mode.svg (neofetch-style profile card)."""
import html
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE

# --- ASCII art ---
lines = HERE.joinpath("ascii_raw.txt").read_text().rstrip("\n").split("\n")
lines = [l.rstrip() for l in lines]
indent = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
lines = [l[indent:] for l in lines]
ascii_w = max(len(l) for l in lines)
print(f"ascii: {len(lines)} rows x {ascii_w} cols")

FS_A, LH_A = 12, 12          # ascii font size / line height
FS, LH = 16, 20              # info text font size / line height
PAD = 25
Y0 = 40
CHAR = FS * 0.602            # monospace char width at info size
CHAR_A = FS_A * 0.602
RIGHT_X = int(PAD + ascii_w * CHAR_A + 45)
TOTAL_COLS = 72              # every info line is padded with dots to this width
                             # (update_stats.py must use the same value)
W = int(RIGHT_X + TOTAL_COLS * CHAR + PAD)
H = max(Y0 + len(lines) * LH_A, Y0 + 20 * LH) + PAD
H = int(H)
print(f"card: {W}x{H}, right_x={RIGHT_X}")

THEMES = {
    "dark_mode": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", value="#a5d6ff",
                      add="#3fb950", dele="#f85149", cc="#616e7f", border=""),
    "light_mode": dict(bg="#fffefe", fg="#24292f", key="#953800", value="#0a3069",
                       add="#1a7f37", dele="#cf222e", cc="#6e7781",
                       border=' stroke="#d0d7de" stroke-width="1"'),
}


def row(y, key, parts, dots_id=None):
    """One info line, dot-justified so every line ends at TOTAL_COLS.

    parts: list of (text, css_class, tspan_id) tuples; class/id may be None.
    Line layout: '. ' key ': ' dots ' ' value  ->  len == TOTAL_COLS
    """
    plain_len = sum(len(t) for t, _, _ in parts)
    n = TOTAL_COLS - len(key) - plain_len - 5
    if n < 1:
        raise ValueError(f"line too long for TOTAL_COLS: {key} ({-n + 1} over)")
    dots_attr = f' id="{dots_id}"' if dots_id else ""
    tspans = "".join(
        f'<tspan{f" id=\"{id_}\"" if id_ else ""} class="{cls or "value"}">{html.escape(t)}</tspan>'
        for t, cls, id_ in parts)
    return (f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'
            f'<tspan class="key">{key}</tspan>:'
            f'<tspan{dots_attr} class="cc"> {"." * n} </tspan>{tspans}')


def val(text, id_=None, cls=None):
    return [(text, cls, id_)]


def cc(text):
    return [(text, "cc", None)]


def title(y, name):
    # Plain fg color (white on dark), like Andrew6rant's section headers.
    dashes = "—" * (TOTAL_COLS - len(name) - 1)
    return f'<tspan x="{RIGHT_X}" y="{y}">{name} {dashes}</tspan>'


for theme_name, c in THEMES.items():
    y = Y0
    rows = []
    rows.append(title(y, "umut@ozturk")); y += LH
    rows.append(row(y, "Uptime", val("--", "age_data"), dots_id="age_dots")); y += LH
    rows.append(row(y, "Company", val("Sentez | AI-driven Portfolio Company"))); y += LH
    rows.append(row(y, "Focus", val("AI-powered mobile apps, and mobile games"))); y += LH
    rows.append(row(y, "Apps", val("--", "apps_data"), dots_id="apps_dots")); y += LH
    rows.append(row(y, "Hobbies", val("Gaming, Sports, Anime"))); y += LH

    y += LH  # blank line
    rows.append(title(y, "umut@stack")); y += LH
    rows.append(row(y, "Languages.Programming", val("TypeScript, JavaScript, Swift, Python, C++"))); y += LH
    rows.append(row(y, "Languages.Computer", val("HTML, CSS, JSON, YAML, Bash"))); y += LH
    rows.append(row(y, "Languages.Real", val("English, Turkish, Japanese"))); y += LH
    rows.append(row(y, "Frameworks", val("React Native, Node.js, Firebase, Vite"))); y += LH

    y += LH  # blank line
    rows.append(title(y, "umut@contact")); y += LH
    rows.append(row(y, "Email", val("umutozturk134@gmail.com"))); y += LH
    rows.append(row(y, "LinkedIn", val("linkedin.com/in/umutozturkkk"))); y += LH
    rows.append(row(y, "Web", val("umut-ozturk.com"))); y += LH

    y += LH  # blank line
    rows.append(title(y, "umut@github")); y += LH
    rows.append(row(y, "Repos", val("0", "repo_data") + cc(" (Contributed: ")
                 + val("0", "contrib_data") + cc(")"), dots_id="repo_dots")); y += LH
    rows.append(row(y, "Commits", val("0", "commit_data"), dots_id="commit_dots")); y += LH
    rows.append(row(y, "Followers", val("0", "follower_data"), dots_id="follower_dots")); y += LH
    rows.append(row(y, "Lines of Code", val("0", "loc_data") + cc(" ( ")
                 + val("0++", "loc_add", "addColor") + cc(", ")
                 + val("0--", "loc_del", "delColor") + cc(" )"),
                 dots_id="loc_dots")); y += LH

    ascii_tspans = "\n".join(
        f'<tspan x="{PAD}" y="{Y0 + i * LH_A}">{html.escape(l) if l else " "}</tspan>'
        for i, l in enumerate(lines))

    svg = f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="Consolas,Menlo,monospace" width="{W}px" height="{H}px" font-size="{FS}px">
<style>
.key {{fill: {c['key']};}}
.value {{fill: {c['value']};}}
.addColor {{fill: {c['add']};}}
.delColor {{fill: {c['dele']};}}
.cc {{fill: {c['cc']};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="{W - 1}px" height="{H - 1}px" x="0.5" y="0.5" fill="{c['bg']}" rx="15"{c['border']}/>
<text x="{PAD}" y="{Y0}" fill="{c['fg']}" font-size="{FS_A}px">
{ascii_tspans}
</text>
<text x="{RIGHT_X}" y="{Y0}" fill="{c['fg']}">
{chr(10).join(rows)}
</text>
</svg>
"""
    OUT.joinpath(f"{theme_name}.svg").write_text(svg)
    print(f"wrote {theme_name}.svg")
