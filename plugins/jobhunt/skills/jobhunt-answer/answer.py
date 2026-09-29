#!/usr/bin/env python3
"""Measure an answer to an application question against the form's limit.

Forms cut answers off rather than refuse them, so a length that is over is
worth knowing before pasting, not after.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import jobhunt as jh  # noqa: E402

#: Application forms cut answers off rather than refuse them, so a length that
#: is over is worth knowing before pasting, not after.
DEFAULT_LIMIT = 0


def work(argv):
    parser = argparse.ArgumentParser(prog="answer", description=__doc__)
    parser.add_argument("answer", nargs="?", help="your draft; omit to read stdin")
    parser.add_argument("--question", default="", required=False,
                        help="the question being answered")
    parser.add_argument("--file", help="read the answer from this file")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="the form's character limit, if it states one")
    args = parser.parse_args(argv)

    if args.file:
        body = Path(args.file).read_text(encoding="utf-8")
    elif args.answer:
        body = args.answer
    else:
        body = sys.stdin.read()

    over = []
    if args.limit and len(body) > args.limit:
        over.append(f"The answer is {len(body)} characters; the form allows "
                    f"{args.limit}. It will be cut off, not refused.")

    jh.emit({"chars": len(body), "words": len(body.split()), "over_limit": over})
    for line in over:
        print(line, file=sys.stderr)
    return jh.UNFIT if over else jh.OK


if __name__ == "__main__":
    raise SystemExit(jh.run_cli(work))
