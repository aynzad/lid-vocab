#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote


DEFAULT_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def github_anchor(text: str) -> str:
    anchor = text.strip().lower()
    anchor = anchor.replace("&", "")
    anchor = re.sub(r"[^a-z0-9 _-]", "", anchor)
    anchor = anchor.replace(" ", "-")
    return anchor


def inline_markdown(text: str) -> str:
    parts: list[str] = []
    position = 0
    for match in re.finditer(r"\[([^\]]+)\]\(#([^)]+)\)", text):
        parts.append(html.escape(text[position : match.start()]))
        parts.append(
            f'<a href="#{html.escape(match.group(2), quote=True)}">'
            f"{html.escape(match.group(1))}</a>"
        )
        position = match.end()
    parts.append(html.escape(text[position:]))
    return "".join(parts)


def render_notebook_html(
    markdown: str,
    *,
    direction: str = "ltr",
    font_family: str = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    lang: str = "en",
    google_font_url: str | None = None,
    local_font_dir: Path | None = None,
) -> str:
    lines = markdown.splitlines()
    body: list[str] = []
    in_index_page = False
    in_index_list = False
    in_category = False
    in_ol = False
    pending_anchor: str | None = None

    def close_ol() -> None:
        nonlocal in_ol
        if in_ol:
            body.append("</ol>")
            in_ol = False

    def close_index_page() -> None:
        nonlocal in_index_page, in_index_list
        if in_index_list:
            body.append("</ul>")
            in_index_list = False
        if in_index_page:
            body.append("</section>")
            in_index_page = False

    def close_category() -> None:
        nonlocal in_category
        close_ol()
        if in_category:
            body.append("</section>")
            in_category = False

    for line in lines:
        anchor_match = re.fullmatch(r'<a id="([^"]+)"></a>', line)
        if anchor_match:
            pending_anchor = anchor_match.group(1)
            continue

        if line.startswith("# "):
            close_category()
            close_index_page()
            in_index_page = True
            body.append('<section class="index-page">')
            body.append(f"<h1>{inline_markdown(line[2:])}</h1>")
            continue

        if line in {"## Category Index", "## فهرست دسته‌ها"}:
            close_ol()
            body.append(f'<h2 id="category-index">{inline_markdown(line[3:])}</h2>')
            body.append('<ul class="category-index">')
            in_index_list = True
            continue

        if line.startswith("## "):
            close_category()
            close_index_page()
            heading = line[3:]
            in_category = True
            anchor = pending_anchor or github_anchor(heading)
            pending_anchor = None
            body.append(f'<section class="category" id="{html.escape(anchor, quote=True)}">')
            body.append(f"<h2>{inline_markdown(heading)}</h2>")
            continue

        if line.startswith("- "):
            body.append(f"<li>{inline_markdown(line[2:])}</li>")
            continue

        if line.startswith("1. "):
            close_index_page()
            if not in_ol:
                body.append("<ol>")
                in_ol = True
            body.append(f"<li><p>{inline_markdown(line[3:])}</p>")
            continue

        if line.startswith("    > "):
            body.append(f"<blockquote>{inline_markdown(line[6:])}</blockquote>")
            if line.startswith("    > Questions: "):
                body.append("</li>")
            continue

        if line == "":
            continue

        if in_ol:
            body.append(f"<p>{inline_markdown(line)}</p>")
        else:
            body.append(f"<p>{inline_markdown(line)}</p>")

    close_category()
    close_index_page()

    direction_class = "rtl" if direction == "rtl" else "ltr"
    font_import = f'@import url("{google_font_url}");' if google_font_url else ""
    local_font_faces = ""
    if local_font_dir is not None:
        local_font_faces = "\n".join(
            [
                _font_face("Vazirmatn", 400, local_font_dir / "Vazirmatn-Regular.ttf"),
                _font_face("Vazirmatn", 600, local_font_dir / "Vazirmatn-SemiBold.ttf"),
                _font_face("Vazirmatn", 700, local_font_dir / "Vazirmatn-Bold.ttf"),
            ]
        )

    return f"""<!doctype html>
<html lang="{html.escape(lang, quote=True)}">
<head>
  <meta charset="utf-8">
  <title>LiD Knowledge-Base Notebook: Berlin</title>
  <style>
    {font_import}
    {local_font_faces}
    @page {{
      size: A4;
      margin: 14mm 13mm 16mm;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      color: #111827;
      font-family: {font_family};
      font-size: 10.4pt;
      line-height: 1.34;
      margin: 0;
    }}
    h1 {{
      border-bottom: 2px solid #111827;
      font-size: 25pt;
      letter-spacing: 0;
      margin: 0 0 20mm;
      padding-bottom: 8mm;
    }}
    h2 {{
      border-bottom: 1px solid #9ca3af;
      font-size: 17pt;
      letter-spacing: 0;
      margin: 0 0 7mm;
      padding-bottom: 3mm;
    }}
    .index-page {{
      break-after: page;
      page-break-after: always;
    }}
    .category {{
      break-before: page;
      page-break-before: always;
    }}
    .category-index {{
      columns: 1;
      font-size: 13pt;
      line-height: 1.8;
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .category-index li {{
      border-bottom: 1px solid #e5e7eb;
      padding: 3mm 0;
    }}
    a {{
      color: #111827;
      text-decoration: none;
    }}
    ol {{
      margin: 0;
      padding-left: 8mm;
    }}
    ol > li {{
      break-inside: avoid;
      margin: 0 0 4.2mm;
      padding-left: 1mm;
    }}
    p {{
      margin: 0 0 2mm;
    }}
    blockquote {{
      border-left: 2px solid #cbd5e1;
      color: #475569;
      font-size: 9.1pt;
      margin: 1.4mm 0 0;
      padding: 0 0 0 2.4mm;
    }}
    body.rtl {{
      direction: rtl;
      text-align: right;
    }}
    body.rtl ol {{
      padding-left: 0;
      padding-right: 8mm;
    }}
    body.rtl ol > li {{
      padding-left: 0;
      padding-right: 1mm;
    }}
    body.rtl blockquote {{
      border-left: 0;
      border-right: 2px solid #cbd5e1;
      padding: 0 2.4mm 0 0;
    }}
  </style>
</head>
<body class="{direction_class}">
{chr(10).join(body)}
</body>
</html>
"""


def _font_face(font_family: str, font_weight: int, font_path: Path) -> str:
    resolved = font_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Missing font file: {resolved}")
    href = "file://" + quote(str(resolved))
    return f"""@font-face {{
      font-family: "{font_family}";
      font-style: normal;
      font-weight: {font_weight};
      src: url("{href}") format("truetype");
    }}"""


def find_chrome(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        return explicit_path
    if DEFAULT_CHROME.exists():
        return DEFAULT_CHROME
    for name in ("google-chrome", "chromium", "chrome"):
        found = shutil.which(name)
        if found:
            return Path(found)
    raise FileNotFoundError("Could not find Chrome or Chromium for PDF rendering")


def write_pdf(chrome_path: Path, html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(chrome_path),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={pdf_path}",
            "--no-pdf-header-footer",
            str(html_path),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert the generated Berlin LiD notebook Markdown to PDF."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=Path("dist/berlin_notebook.md"),
        type=Path,
        help="Notebook Markdown file.",
    )
    parser.add_argument(
        "--output",
        default=Path("dist/berlin_notebook.pdf"),
        type=Path,
        help="PDF output path.",
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        help="Optional path to keep the intermediate HTML.",
    )
    parser.add_argument(
        "--chrome-path",
        type=Path,
        help="Explicit Chrome or Chromium executable path.",
    )
    parser.add_argument(
        "--direction",
        choices=["ltr", "rtl"],
        default="ltr",
        help="Document text direction.",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="HTML language code.",
    )
    parser.add_argument(
        "--font-family",
        default='-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        help="CSS font-family value.",
    )
    parser.add_argument(
        "--google-font-url",
        help="Optional Google Fonts CSS URL to import in the rendered HTML.",
    )
    parser.add_argument(
        "--local-font-dir",
        type=Path,
        help=(
            "Optional directory containing Vazirmatn-Regular.ttf, "
            "Vazirmatn-SemiBold.ttf, and Vazirmatn-Bold.ttf."
        ),
    )
    args = parser.parse_args()

    markdown = args.input.read_text(encoding="utf-8")
    rendered_html = render_notebook_html(
        markdown,
        direction=args.direction,
        font_family=args.font_family,
        lang=args.lang,
        google_font_url=args.google_font_url,
        local_font_dir=args.local_font_dir,
    )
    chrome_path = find_chrome(args.chrome_path)

    if args.html_output:
        args.html_output.parent.mkdir(parents=True, exist_ok=True)
        args.html_output.write_text(rendered_html, encoding="utf-8")
        html_path = args.html_output
        write_pdf(chrome_path, html_path.resolve(), args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="lid-notebook-pdf-") as tmp:
            html_path = Path(tmp) / "notebook.html"
            html_path.write_text(rendered_html, encoding="utf-8")
            write_pdf(chrome_path, html_path.resolve(), args.output.resolve())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
