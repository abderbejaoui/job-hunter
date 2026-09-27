#!/usr/bin/env python3
"""Render a CV or a cover letter to PDF, using the browser already installed.

Nothing becomes a file until it is fit to send: a document carrying a blocking
issue - an unfilled placeholder, a missing name - is refused here rather than
discovered by the employer. The markdown is written first either way, so a
machine with no browser still produces something sendable.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import jobhunt as jh  # noqa: E402


def work(argv):
    parser = argparse.ArgumentParser(prog="pdf", description=__doc__)
    parser.add_argument("source", help="cv.yaml or letter.yaml")
    parser.add_argument("--out", help="where to write the PDF")
    parser.add_argument("--theme", default="neutral",
                        help="neutral, classic, or a #hex colour for the accent")
    parser.add_argument("--template",
                        help="a LaTeX template: a built-in name, or a path to "
                             "a .tex file. Omitted, LaTeX is used anyway when "
                             "a TeX engine is installed; the browser if not")
    parser.add_argument("--browser", action="store_true",
                        help="render through the browser even if TeX is there")
    args = parser.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        print(f"No such file: {source}", file=sys.stderr)
        return jh.BLOCKED

    raw = jh.yaml_load(source.read_text(encoding="utf-8"))
    letter = "paragraphs" in raw or source.stem.startswith("letter")
    document = jh.build(jh.CoverLetter if letter else jh.TailoredCV, raw)

    theme = jh.branded(args.theme) if args.theme.startswith("#") else jh.resolve(args.theme)
    out = Path(args.out) if args.out else source.with_suffix(".pdf")

    # Written before the PDF is attempted, so the document survives a machine
    # with no browser.
    markdown = out.with_suffix(".md")
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(jh.to_markdown(document), encoding="utf-8")

    blocked = jh.blocking_issues(document)
    if blocked:
        jh.emit({"markdown": str(markdown), "pdf": None,
                 "blocking": [f"{i.path}: {i.message}" for i in blocked]})
        raise jh.ExportBlocked(blocked)

    if args.browser and args.template:
        print("--browser and --template ask for different renderers.",
              file=sys.stderr)
        return jh.BLOCKED

    try:
        if args.browser:
            jh.write_pdf(jh.to_html(document, theme), out)
            how = "browser"
        else:
            how = jh.export(document, out, theme, args.template)
    except jh.PdfError as exc:
        jh.emit({"markdown": str(markdown), "pdf": None, "error": str(exc)})
        print(str(exc), file=sys.stderr)
        return jh.OK  # the markdown is real and sendable; this is not a failure

    jh.emit({"markdown": str(markdown), "pdf": str(out),
             "bytes": out.stat().st_size, "theme": theme.name, "rendered": how})
    print(f"Wrote {out} and {markdown} ({how})", file=sys.stderr)
    return jh.OK


if __name__ == "__main__":
    raise SystemExit(jh.run_cli(work))
