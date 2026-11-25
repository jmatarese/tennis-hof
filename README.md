# Tennis Hall of Fame ranking

An objective ranking of ATP and WTA players for the International Tennis Hall of Fame:
score every career from match results and rankings, test the method against
real inductions, and write the paper. Every change goes through a pull request,
and every pull request gets a report showing what it did to the rankings.

**Latest paper:** [paper.pdf](https://github.com/jmatarese/tennis-hof/releases/download/latest/paper.pdf) ·
**Latest rankings:** [rankings.csv](https://github.com/jmatarese/tennis-hof/releases/download/latest/rankings.csv)

The default branch is **`master`**.

**Start here:** [`docs/`](docs/README.md) holds the project brief and working
paper, which set the scope, intent and guardrails. They're guidance, not rules.

## Joining the team

1. Accept the GitHub invitation (check your email or [github.com/notifications](https://github.com/notifications)).
2. Set up your machine (below), then run `uv run hof doctor` until it's all green.
3. Read [`docs/README.md`](docs/README.md) and skim the [open issues](https://github.com/jmatarese/tennis-hof/issues): they're the team's open questions.
4. Your first pull request: add yourself to [`AUTHORS.md`](AUTHORS.md) and to
   `\author{...}` in `paper/main.tex`, following the daily loop below.

## First-time setup

### macOS

1. Open **Terminal**. If `brew --version` says "command not found", install
   [Homebrew](https://brew.sh), the Mac package manager:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   When it finishes it prints **Next steps**: run the commands it shows, then
   open a new Terminal window.
2. Install Git and the GitHub CLI, and log in to GitHub:
   ```bash
   brew install git gh
   gh auth login
   ```
3. Clone the repo and run the setup script:
   ```bash
   gh repo clone jmatarese/tennis-hof
   cd tennis-hof
   bash scripts/setup.sh
   ```

The script installs [uv](https://docs.astral.sh/uv/), which installs the right
Python and every package. You never install Python yourself. At the end it runs
`hof doctor`, which lists anything still missing and the exact command to fix it.

### Windows (recommended: WSL)

1. In PowerShell **as Administrator**, run `wsl --install`, restart, then open
   **Ubuntu** from the Start menu and choose a Linux username and password.
2. In the Ubuntu terminal, install Git and the GitHub CLI and log in. Ubuntu's
   own `gh` is years old, so install it from GitHub's package source
   ([instructions](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)), then:
   ```bash
   gh auth login        # if no browser opens, paste the URL into your Windows browser
   ```
3. Clone into your **Linux home folder** (not `/mnt/c/...`) and run the setup script:
   ```bash
   cd ~
   gh repo clone jmatarese/tennis-hof
   cd tennis-hof
   bash scripts/setup.sh
   ```

Edit with [VS Code](https://code.visualstudio.com/) and its **WSL** extension:
run `code .` inside the repo from Ubuntu.

### Windows without WSL

1. Open **PowerShell** and install Git and the GitHub CLI:
   ```powershell
   winget install --id Git.Git -e
   winget install --id GitHub.cli -e
   ```
2. Close PowerShell, open a new one, and log in to GitHub:
   ```powershell
   gh auth login
   ```
3. Clone the repo and run the setup script:
   ```powershell
   gh repo clone jmatarese/tennis-hof
   cd tennis-hof
   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
   ```

### Nothing works on my machine

Open the repo on GitHub → **Code** → **Codespaces** → **Create codespace on master**.
You get VS Code in the browser with everything already installed.

## Daily loop

```bash
git switch master && git pull        # 1. start from the latest master
git switch -c better-slam-weights    # 2. a branch for one idea
# ... edit code ...
uv run hof check                     # 3. lint, format and tests: what CI runs
git add -A && git commit -m "Weight Slam finals by round reached"
git push -u origin HEAD              # 4. push your branch
gh pr create --fill                  # 5. open a pull request
```

Then wait a few minutes. CI runs the checks, and a bot comment appears on your
PR with the **Hall of Fame report**: who crossed the line, who moved, how the
method now scores against real inductions, and how long it took. A teammate
reviews, and you **squash and merge**.

You can't push to `master` or merge without a passing CI run and one approval.
That is on purpose.

## Commands

Everything goes through one command, `hof`. Run `uv run hof --help`.

| Command | What it does |
|---|---|
| `uv run hof setup` | First-time setup: git hook, data snapshot, LaTeX |
| `uv run hof doctor` | Checks your machine and tells you how to fix what is wrong |
| `uv run hof check` | Lint, format and tests. Same as CI. Add `--fix` to auto-fix style |
| `uv run hof run` | Runs the method; writes `results/rankings.csv` and `results/metrics.json` |
| `uv run hof diff A B` | Compares two runs. This is the PR report, locally |
| `uv run hof paper` | Builds `paper/build/main.pdf` from the latest run |

To see what your branch does before you push (commit first):

```bash
git switch master && uv run hof run --out results/master
git switch -      && uv run hof run --out results/mine
uv run hof diff results/master results/mine
```

## What CI does

| Workflow | When | Blocks merge? |
|---|---|---|
| **CI / check** | Every PR, on Linux, macOS and Windows | Yes (Linux and Windows) |
| **CI / setup script** | Every PR: runs the setup script from scratch | No |
| **Report** | Every PR: runs master and the PR, posts the comparison | No |
| **Publish** | Every merge to master: rebuilds the paper and rankings | — |

## Layout

```
src/hof/            the method, as a Python package
  data.py             the pinned data snapshot: fetch, validate, flag, load
  features.py         career statistics per player (PLACEHOLDER)
  model.py            the score and the ITHF baseline rule (PLACEHOLDER)
  pipeline.py         runs it all, times each stage, writes results/
  evaluate.py         precision, recall, F1, AUC against real inductions
  report.py           compares two runs (the PR comment)
  paper.py            writes paper/generated/ and builds the PDF
tests/              what must stay true; see the docstring in each file
  fixtures/data/      a small frozen slice of the real data the tests run on
  test_pipeline/      golden files: the expected rankings and metrics on the fixture
data/snapshot.toml  which version of the Hugging Face dataset we use (commit hash)
data/inductees.csv  actual Hall of Fame inductees, one source URL per row
docs/               the project brief and working paper (.docx originals + .md copies)
paper/main.tex      the paper; numbers come from paper/generated/results.tex
scripts/            setup scripts; build_inductees.py and make_fixture.py rebuild data files
```

## Rules of thumb

- **Logic lives in `src/hof/`.** Notebooks are for looking at results; they
  import from `hof` and hold no logic. Outputs are stripped on commit.
- **Never type a number into the paper.** Add it to `paper.py` and `\input` it.
- **A method change changes the golden files.** If a `*_golden_file` test
  fails and you meant it, run `uv run pytest --force-regen` (that run reports
  failures while it rewrites the files; run `uv run pytest` again to see it
  pass), then commit the result. Reviewers read that diff.
- **A data change is its own PR.** Updating the snapshot or the inductee list
  never rides along with a method change.
- **Write your prediction in the PR before reading the report.** The interesting
  PRs are the ones where you were wrong.
- **A PR that makes the method worse is still a result.** Close it with a note
  saying what you learned; it may go in the paper.

## License

Code: MIT (see `LICENSE`). Data: Jeff Sackmann's ATP and WTA data,
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
