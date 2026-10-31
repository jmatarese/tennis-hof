# Project documents

The guiding documents for this project. They set out the scope, intent and
starting hypotheses. **They are context, not rules:** the team is free to
reject the preliminary framework, choose different variables or methods, and
reach different conclusions.

| Document | What it is | Cite as |
|---|---|---|
| [Research Project Brief v0.2](UChicago_Tennis_Hall_Eligibility_Research_Project_Brief_v0.2.md) ([.docx](UChicago_Tennis_Hall_Eligibility_Research_Project_Brief_v0.2.docx)) | The research question, scope (singles, Open Era), guardrails, stress tests, deliverables. October 2026 | `\citep{brief}` |
| [Working Paper v0.1](ITHF_Quantitative_Framework_Player_Eligibility_Working_Paper_v0.1.md) ([.docx](ITHF_Quantitative_Framework_Player_Eligibility_Working_Paper_v0.1.docx)) | The preliminary six-dimension hypothesis and its illustrative 100-point weights. September 2026 | `\citep{workingpaper}` |

The `.docx` files are the originals. The `.md` files are plain-text copies
made with `uvx --from 'markitdown[docx]' markitdown FILE.docx -o FILE.md`, so
agents can read them and git can show what changed between versions. When a
new version arrives, add the new `.docx`, regenerate its `.md`, and update this
table in the same PR.

## The points that shape the code most

- **The question:** can a transparent framework decide whether a player's
  *actual* career achievements meet a Hall-caliber standard? Not a GOAT
  ranking, not injury counterfactuals, not reproducing past votes.
- **Scope:** singles; the Open Era from 1968; the 1968–71 period's treatment is
  decided after a data audit, not assumed. Men and women under one framework,
  possibly calibrated separately.
- **Hall status is validation metadata,** kept out of model construction where
  appropriate. At least one approach should not use it at all.
- **Data:** preserve raw data and provenance; prefer explicit missingness to
  invented proxies; never silently map modern tournament categories onto
  historically different events.
- **Guardrails:** write hypotheses, definitions and stress tests down before
  looking at results; never change a rule because one player lands on the
  "wrong" side.
- **Stress-test careers** (named in advance, not desired outcomes): del Potro,
  Roddick, Stich, Gerulaitis, Gottfried, Austin, Connolly, McEnroe, Muster,
  Ferrer, Safin, Hewitt, Sampras/Agassi, Evert/Navratilova.
