"""`hof`: the one command for everything. Run `uv run hof --help`."""

import argparse
import sys
from pathlib import Path

from hof import env, paper, pipeline, report


def _run(args: argparse.Namespace) -> int:
    metrics = pipeline.run(args.out, args.data)
    m = metrics["model"]
    print(f"Wrote {args.out}/rankings.csv and metrics.json")
    print(
        f"Test years: precision {m['precision']:.3f}, recall {m['recall']:.3f}, "
        f"F1 {m['f1']:.3f}, AUC {m['auc']:.3f}"
    )
    return 0


def _diff(args: argparse.Namespace) -> int:
    md = report.markdown(args.base, args.head)
    if args.csv:
        report.compare(args.base, args.head).to_csv(args.csv, index=False, lineterminator="\n")
    if args.out:
        args.out.write_text(md, encoding="utf-8")
    else:
        print(md)
    return 0


def _paper(args: argparse.Namespace) -> int:
    if not (args.run / "metrics.json").exists():
        pipeline.run(args.run)
    print(f"Wrote {paper.build(args.run)}")
    return 0


def main() -> None:
    # Windows terminals default to a legacy encoding; make output UTF-8 everywhere.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(prog="hof", description=__doc__)
    sub = ap.add_subparsers(required=True, metavar="command")

    sub.add_parser("setup", help="first-time setup: hooks, data, LaTeX").set_defaults(
        fn=lambda _: env.setup()
    )
    sub.add_parser(
        "doctor", help="check your machine is ready, and say how to fix it"
    ).set_defaults(fn=lambda _: env.doctor())

    p = sub.add_parser("check", help="lint, format and test (what CI runs)")
    p.add_argument("--fix", action="store_true", help="fix lint and formatting in place")
    p.set_defaults(fn=lambda a: env.check(a.fix))

    p = sub.add_parser("run", help="run the pipeline and write rankings + metrics")
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--data", type=Path, help="a data folder instead of the pinned snapshot")
    p.set_defaults(fn=_run)

    p = sub.add_parser("diff", help="compare two runs as Markdown (the PR report)")
    p.add_argument("base", type=Path)
    p.add_argument("head", type=Path)
    p.add_argument("--out", type=Path, help="write Markdown here instead of printing it")
    p.add_argument("--csv", type=Path, help="also write the full per-player diff")
    p.set_defaults(fn=_diff)

    p = sub.add_parser("paper", help="build paper/build/main.pdf from a run")
    p.add_argument("--run", type=Path, default=Path("results"))
    p.set_defaults(fn=_paper)

    args = ap.parse_args()
    sys.exit(args.fn(args))
