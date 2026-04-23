# sections/asides/pg2 — Page 2 Aside, Job Family Variants

## Page 2 Context

Page 2 main body carries three experience entries:

- **Kixeye Inc — Product Analyst, WCRA** (Aug 2019 – Jan 2021)
  Jenkins migration ($27K/mo saved), legacy ETL repair, ML tooling,
  spend conversion improvement, UA strategy revision

- **EA — Data Scientist, Dynamic Experiences** (Nov 2018 – Jul 2019)
  A/B test campaigns, MAB recommendation engines, churn and spend
  conversion models, $2M revenue impact for FIFA 19

- **EA — Business Analyst, FIFA Player Analytics** (Jun 2016 – Nov 2018)
  Executive board reporting, licensing analytics automation ($200K/qtr),
  propensity score matching for companion app valuation (4.2% / 7.0%
  spend uplift), Analyticon 2018 presentation, Madden roadmap influence

The aside co-reads with all three simultaneously. Each family file is
designed to surface the signal most relevant to that reader from the
same three entries.

---

## File Inventory

```
sections/asides/pg2/
  aside-pg2-ds.tex      Senior / Staff Data Scientist
  aside-pg2-de.tex      Data Engineer
  aside-pg2-ae.tex      Analytics Engineer
  aside-pg2-am.tex      Analytics Manager (people management)
  aside-pg2-econ.tex    Economist
  aside-pg2-da.tex      Data Analyst, Staff / Lead IC
```

---

## Family Design Rationale

### DS
Refinement of the original `skills-ds.tex`. Five skill areas
(Experimentation, Personalization/RecSys, Predictive Modeling, Causal
Inference, Model Evaluation) directly echo what the reader sees in the
adjacent entries. Typo corrected: "cannablization" → "cannibalization".
Product Analytics at Scale restored from commented state.

### DE
Frames engineering philosophy rather than tool taxonomy (tools are
covered on page 3). Five areas: pipeline reliability, cost/latency
trade-off thinking, ML pipeline ops, experimentation infrastructure,
and full-stack BI delivery. The WCRA entries carry the strongest DE
signal; the aside amplifies the operational reasoning behind that work.

### AE
Centres on the transformation and delivery thinking visible in the EA
BA role: R/Talend automation of licensing reporting, statistical models
as an analytical layer, KPI trust and consistency as delivery
requirements, and self-service as an outcome. The propensity score
matching study is framed as a rigorous transformation layer feeding
consequential business decisions.

### AM
Surfaces stakeholder reach and cross-functional influence. The EA BA
role is the strongest AM signal in the document: executive board
reporting for EA Sports, cross-studio trust (Motive, BioWare, DICE),
Analyticon presentation, and cross-franchise roadmap influence. The
aside amplifies organizational reach rather than technical methods.

### Economist
The EA BA propensity score matching study is the centrepiece. The aside
names methods explicitly (propensity score matching, DiD, regression
discontinuity, quasi-experimental design, auction theory, game theory)
and frames the applied rigour behind the identification choices.
Includes an optional block for the academic section if it overflowed
from page 1 — see inline comments in the file.

### DA (Staff / Lead IC)
Frames the companion app study and licensing automation as senior IC
ownership signals, not just analytical achievements. Emphasis on:
self-proposed work, identification strategy owned end-to-end, decisions
changed (not deliverables produced), and scope exercised beyond title.
The propensity matching study and Analyticon presentation are the
strongest "operated above title" signals in the document.

---

## Usage in main.tex

Replace the current hardcoded page 2 aside:

```latex
% BEFORE
\begin{aside}%
\input{sections/asides/skills-ds}%
\end{aside}
```

```latex
% AFTER (Phase 1 — swap family prefix per application)
\begin{aside}%
\input{sections/asides/pg2/aside-pg2-ds}   % ← change prefix here
\end{aside}
```

In Phase 2, the build script handles this automatically using the same
`\jobfamily` flag as page 1 and page 3.

---

## Relationship to Original skills-ds.tex

`skills-ds.tex` is superseded by `aside-pg2-ds.tex` for DS
applications. It is retained at root for reference and as a fallback
during the transition period. Once all six pg2 variants are compiled
and proofed, `skills-ds.tex` can be archived to `sections/asides/old/`.

---

## Economist Overflow Note

`aside-pg2-econ.tex` includes a commented-out academic block at the
top for use if `aside-pg1-econ.tex` overflows its vertical budget.
After compiling the Economist variant, check whether the page 1 aside
fits within the Kano / Kixeye-Stillfront vertical span. If it
overflows:

1. Remove the academic block from `aside-pg1-econ.tex`
2. Uncomment the academic block at the top of `aside-pg2-econ.tex`
3. Recompile and verify both pages

The academic block should always appear on the earliest page where it
fits cleanly, which is page 1 in most cases.
