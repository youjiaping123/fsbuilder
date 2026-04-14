from pathlib import Path

DATA = [
    ("Models", 91),
    ("Analysis Parsing", 83),
    ("Analysis Provider", 60),
    ("Analysis Service", 96),
    ("Application", 88),
    ("CLI", 93),
    ("Gen Renderers", 98),
    ("Gen Service", 78),
    ("WebUI API", 97),
    ("WebUI Server", 24),
]


def main() -> None:
    labels = ",".join("{" + name + "}" for name, _ in DATA)
    coordinates = "\n".join(f"        ({value},{{{name}}})" for name, value in DATA)
    content = rf"""\begin{{tikzpicture}}
\begin{{axis}}[
    width=0.95\linewidth,
    height=8.5cm,
    xbar,
    xmin=0,
    xmax=100,
    xlabel={{Coverage (\%)}},
    symbolic y coords={{{labels}}},
    ytick=data,
    y dir=reverse,
    bar width=0.52cm,
    nodes near coords,
    nodes near coords align={{horizontal}},
    grid=major,
    grid style={{dashed,gray!30}},
    tick label style={{font=\small}},
    label style={{font=\small}},
]
\addplot[fill=blue!45, draw=blue!70!black] coordinates {{
{coordinates}
}};
\end{{axis}}
\end{{tikzpicture}}
"""
    target = Path(__file__).with_name("coverage_chart_tikz.tex")
    target.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
