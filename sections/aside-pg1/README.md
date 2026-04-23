# sections/asides/pg1 — Page 1 Aside, Job Family Variants

## File Inventory

```
sections/asides/pg1/
  aside-pg1-ds.tex      Senior / Staff Data Scientist
  aside-pg1-de.tex      Data Engineer
  aside-pg1-ae.tex      Analytics Engineer
  aside-pg1-am.tex      Analytics Manager (people management)
  aside-pg1-econ.tex    Economist
  aside-pg1-da.tex      Data Analyst, Staff / Lead IC
```

## Where These Fit in the Repo

The current project is flat (all .tex files at root). The target
directory structure implied by main.tex's \input paths is:

```
/
  main.tex
  info.tex
  cv-style.cls
  sections/
    about_me.tex
    education.tex
    experience/
      kano.tex
      kix_sfg.tex
      kixeye.tex
      ea.tex
      pretio.tex
      tinymob.tex
    asides/
      experience-breakdown.tex   ← retired; kept for reference
      achievements.tex           ← default fallback; AI sorter target
      skills-ds.tex              ← page 2 aside
      skills-de.tex              ← page 3 aside
      education-side.tex
      references.tex
      interests.tex
      certificates.tex
      pg1/                       ← THIS DIRECTORY
        aside-pg1-ds.tex
        aside-pg1-de.tex
        aside-pg1-ae.tex
        aside-pg1-am.tex
        aside-pg1-econ.tex
        aside-pg1-da.tex
  icons/
    logos/
      kano_logo.png
      kixeye_horse_logo.png
      ea_sports.png
      pretio-interactive.png
      tinymob_games_logo.png
      self_portrait.jpg
    main/
      phone.png
      mail.png
  fonts/
    (Roboto font files)
```

## How to Use — Phase 1 (Manual Swap)

In `main.tex`, replace the current first aside block:

```latex
% BEFORE (current)
\begin{aside}%
\vspace{3.5cm}%
\section{EXPERIENCE BREAKDOWN}
\vspace{-0.1cm}%
\noindent\rule{\textwidth}{0.4pt}
\input{sections/asides/experience-breakdown.tex}%
\noindent\rule{\textwidth}{0.4pt}%
\vspace{-0.1cm}%
\section{KEY VICTORIES}%
\input{sections/asides/achievements.tex}%
\end{aside}
```

```latex
% AFTER (Phase 1 — swap the filename per application)
\begin{aside}%
\vspace{3.5cm}%
\input{sections/asides/pg1/aside-pg1-ds}   % ← change family prefix here
\end{aside}
```

Change `aside-pg1-ds` to the appropriate family file before each compile:
- `aside-pg1-ds`    → Data Scientist
- `aside-pg1-de`    → Data Engineer
- `aside-pg1-ae`    → Analytics Engineer
- `aside-pg1-am`    → Analytics Manager
- `aside-pg1-econ`  → Economist
- `aside-pg1-da`    → Data Analyst (Staff / Lead IC)

## How to Use — Phase 2 (Build Script, future)

The build script will accept a family argument and write a
`jobfamily.tex` shim that main.tex reads to select the correct file
automatically. No manual editing of main.tex required.

```bash
./build.sh DS "Senior Data Scientist - Stripe"
# → output/AlexOswald_CV_DS_Stripe.pdf
```

## How to Use — Phase 3 (AI Sorter integration, future)

The achievement-sorter artifact will be extended to:
1. Accept a job family selection (dropdown)
2. Accept a job posting (text area)
3. Output a posting-tuned instance of the family file with
   Key Victories ranked and rewritten for that specific posting
4. Write the result to sections/asides/pg1/aside-pg1-active.tex
   which the build script uses instead of the static family file

## Design Notes

**Vertical budget:** Each family file is sized to fit within the
vertical space occupied by the Kano and Kixeye/Stillfront entries
on page 1. Content that overflows into the lower half of page 1
(alongside Kixeye Inc.) loses the co-reading benefit. If a family
file overflows, trim the methods list before trimming the victories.

**Word breaks:** The aside column is 3.6cm wide (set in cv-style.cls).
Manual hyphenation breaks (e.g. `discon- tinuity`, `model- ling`) are
intentional and match the existing style of achievements.tex and
skills-ds.tex. Adjust if reflow causes overfull hbox warnings.

**Key Victories authoring standard:** All victory entries should be
written as problem-outcome pairs with at least one concrete number.
Entries that name a category without a number (e.g. "Experimentation
Leadership") do not meet the standard and should be revised before use.

**ATS note:** Maintain a single-column fallback PDF for ATS-heavy
application pipelines (Workday, Greenhouse, Lever). The aside content
in each family file should inform the summary and skills sections of
that fallback — it should not disappear entirely.
