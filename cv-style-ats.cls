% =============================================================================
%  cv-style-ats.cls — ATS-friendly single-column resume class
% -----------------------------------------------------------------------------
%  Companion class to cv-style.cls. Same colour palette, same Roboto fonts,
%  but a single-column "sections" layout matching the recruiter-prepared
%  resume Alex received in May 2026. No aside / sidebar / photo — the layout
%  flows cleanly through ATS parsers while still presenting visual identity
%  via the navy header band and atsblue section rules.
%
%  Differences from cv-style.cls:
%    • single column (no \begin{aside}, no textpos sidebar)
%    • compact navy header without circular self-portrait
%    • new "section" style: atsblue uppercase heading + 0.5pt rule underline
%    • new commands: \atsheader, \techskills/\skillgroup, \impactbox/\impactcell,
%      \jobcompany, \jobrole, \jobbullets, \edublock/\edudegree
%
%  The Jinja2 template `templates/resume-ats.tex.j2` is the canonical consumer
%  of these macros — see that file for usage examples.
% =============================================================================

\ProvidesClass{cv-style-ats}[2026/05/12 ATS-friendly CV class]
\NeedsTeXFormat{LaTeX2e}

\DeclareOption{print}{\def\@cvats@print{}}
\DeclareOption*{%
  \PassOptionsToClass{\CurrentOption}{article}%
}
\ProcessOptions\relax
\LoadClass{article}

%----------------------------------------------------------------------------------------
% Colours — palette mirrors cv-style.cls for visual continuity
%----------------------------------------------------------------------------------------
\RequirePackage{xcolor}

\definecolor{white}{RGB}{255,255,255}
\definecolor{darkgray}{HTML}{333333}
\definecolor{gray}{HTML}{4D4D4D}
\definecolor{lightgray}{HTML}{999999}
\definecolor{date}{HTML}{A4A4A4}

\definecolor{navyblue}{HTML}{3b4c74}      % header background — same as cv-style.cls
\definecolor{atsblue}{HTML}{2E5B9C}        % section headings + accents (recruiter PDF tone)
\definecolor{accent}{HTML}{2E5B9C}         % alias for company names
\definecolor{impactbg}{HTML}{E4ECF7}       % key-impact-metrics callout fill
\definecolor{headerlink}{HTML}{9DC2F2}     % web links inside the navy header — light
                                           % blue, high-contrast against navyblue

\ifdefined\@cvats@print
  \colorlet{atsblue}{gray}
  \colorlet{accent}{gray}
  \colorlet{header}{gray}
  \colorlet{headerlink}{gray}
  \colorlet{impactbg}{white}
\else
  \colorlet{header}{white}
\fi
\colorlet{textcolor}{gray}

%----------------------------------------------------------------------------------------
% Fonts
%----------------------------------------------------------------------------------------
\RequirePackage[quiet]{fontspec}
\RequirePackage{unicode-math}
\newfontfamily\bodyfont{Roboto-Regular}[Path=fonts/]
\newfontfamily\bodyfontit{Roboto-LightItalic}[Path=fonts/]
\newfontfamily\thinfont{Roboto-Thin}[Path=fonts/]
\newfontfamily\headingfont{RobotoCondensed-Bold}[Path=fonts/]

\defaultfontfeatures{Mapping=tex-text}
\setmainfont[Mapping=tex-text, Color=textcolor, Path=fonts/]{Roboto-Light}

\newcommand{\italica}[1]{{\color{gray}\bodyfontit #1}}

%----------------------------------------------------------------------------------------
% Geometry — single column, ATS-friendly margins
%----------------------------------------------------------------------------------------
\RequirePackage[left=0.55in, right=0.55in, top=0.4in, bottom=0.5in, nohead, nofoot]{geometry}

%----------------------------------------------------------------------------------------
% Common packages
%
% NOTE: The ATS layout intentionally avoids icon fonts — contact info is
% rendered as plain text so it parses cleanly through ATS pipelines. If
% you want to reintroduce icons here later, add:
%   \RequirePackage{fontawesome5}
% and wrap each contact line in the appropriate \fa* command.
%----------------------------------------------------------------------------------------
\RequirePackage{tikz}
\RequirePackage{tabularx}
\RequirePackage{array}
\RequirePackage{enumitem}
\RequirePackage{parskip}
\RequirePackage{polyglossia}
\RequirePackage{graphicx}
\RequirePackage{hyperref}

\setdefaultlanguage[variant=british]{english}

% Compat macro for templates that call \sethyphenation (defined the same
% way in cv-style.cls). Lets the same template prelude work in both classes.
\newcommand{\sethyphenation}[3][]{%
  \sbox0{\begin{otherlanguage}[#1]{#2}%
    \hyphenation{#3}\end{otherlanguage}}}

% hidelinks: hyperref makes links clickable but applies NO colour or border
% of its own. Link colour is then controlled entirely by explicit \textcolor,
% which lets header links be light blue (legible on navy) while any future
% body links can be coloured independently. See \headerhref below.
\hypersetup{
    pdftitle=CV/Resume \textbar{} Alex Oswald,
    pdfauthor=Alex Oswald,
    pdfsubject=CV/Resume,
    hidelinks,
}

% \headerhref{url}{display text} — a clickable link whose visible text is
% rendered in `headerlink` (light blue). Used for the email / LinkedIn /
% GitHub links in the navy header, where atsblue would be too dark to read.
\newcommand{\headerhref}[2]{\href{#1}{\textcolor{headerlink}{#2}}}

\pagestyle{empty}
\setlength{\parindent}{0pt}

%----------------------------------------------------------------------------------------
% Header — navy band with name, tagline and right-aligned contact info
%
% Args (positional, 9 — same convention as cv-style.cls so the template
% can switch templates without rewriting personal-info plumbing):
%   #1 firstname
%   #2 lastname
%   #3 phone
%   #4 email
%   #5 linkedin   (already wrapped in \href{}{handle-text})
%   #6 github     (already wrapped in \href{}{display-text})
%   #7 location   (e.g. "Vancouver, BC, Canada")
%   #8 headerTitle (subtitle line, e.g. "Senior Analytics Engineer | Games Industry")
%   #9 keywordLine (tagline, e.g. "dbt • Snowflake • Python • ...")
%
% The blog URL is intentionally omitted from the ATS header — the recruiter
% version Alex was given doesn't include it, and the keyword line carries
% more ATS signal.
%
% Note: arg #7 (location) is built by renderer._compose_header_location and
% may be longer than just "Victoria, BC" — e.g. when --location-mode=us it
% includes "US Citizen & Canadian PR · Open to Relocation (Seattle)". The
% right-column minipage uses \raggedleft so longer location lines wrap
% gracefully across two visual lines without breaking the header layout.
%----------------------------------------------------------------------------------------
\newcommand{\atsheader}[9]{%
  \begin{tikzpicture}[remember picture, overlay]
    \node[
      rectangle, fill=navyblue, anchor=north,
      minimum width=\paperwidth, minimum height=3.1cm
    ] (atsbox) at (current page.north) {};
    % LEFT block — name + subtitle + keyword line
    \node[anchor=north west, xshift=0.55in, yshift=-0.42cm] (left) at (atsbox.north west) {%
      \begin{minipage}[t]{0.56\paperwidth}
        {\fontsize{22pt}{25pt}\bodyfont\bfseries\color{header} #1 #2}\\[0.22em]
        {\fontsize{10.5pt}{12pt}\bodyfont\color{header} #8}\\[0.13em]
        {\fontsize{8pt}{10pt}\thinfont\color{header} #9}
      \end{minipage}%
    };
    % RIGHT block — contact info; location (#7) may wrap to two lines
    \node[anchor=north east, xshift=-0.55in, yshift=-0.42cm] (right) at (atsbox.north east) {%
      \begin{minipage}[t]{0.38\paperwidth}
        \raggedleft
        {\fontsize{8pt}{10.5pt}\thinfont\color{header}%
          #3 \\
          #4 \\
          linkedin: #5 \\
          #6 \\
          #7%
        }
      \end{minipage}%
    };
  \end{tikzpicture}%
  % Reserve vertical space below the header band before body content begins.
  % Tuned so the first section heading sits just clear of the 3.1cm navy
  % band while keeping the header-to-summary gap tight.
  \vspace*{2.25cm}\par%
}

%----------------------------------------------------------------------------------------
% Section heading — atsblue uppercase + thin 0.5pt rule underline
%----------------------------------------------------------------------------------------
\renewcommand{\section}[1]{%
  \par\vspace{0.45em}%
  {\headingfont\large\color{atsblue}\MakeUppercase{#1}}\par
  \vspace{-0.4em}%
  {\color{atsblue}\rule{\linewidth}{0.5pt}}\par
  \vspace{0.25em}%
}

% Sub-section: lighter (used inside Education / inside long lists)
\renewcommand{\subsection}[1]{%
  \par\vspace{0.3em}%
  {\headingfont\normalsize\color{atsblue} #1}\par
  \vspace{0.1em}%
}

%----------------------------------------------------------------------------------------
% Technical-skills key/value table
%
% Usage:
%   \begin{techskills}
%     \skillgroup{Pipeline & Orchestration}{Apache Airflow, Prefect, ...}
%     \skillgroup{Data Modeling & dbt}{dbt (models, tests, docs), ...}
%     ...
%   \end{techskills}
%----------------------------------------------------------------------------------------
% Wrapping tabularx in \newenvironment misbehaves with its width-scanner,
% so the skills table uses a plain `tabular` with fixed-width p columns.
% Combined left+right ≈ 0.95\linewidth; remaining gutter goes to spacing.
% Set in \small so concise skill groups fit on a single line.
\newenvironment{techskills}{%
  \small
  \begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.27\linewidth}@{\hspace{0.6em}}>{\raggedright\arraybackslash}p{0.67\linewidth}@{}}
}{%
  \end{tabular}\par\vspace{0.2em}%
}

\newcommand{\skillgroup}[2]{%
  {\headingfont\color{atsblue} #1} & #2 \\[0.4em]
}

%----------------------------------------------------------------------------------------
% Key-impact-metrics callout
%
% Usage:
%   \begin{impactbox}
%     \impactcell{13x}{Report latency improvement (14 hrs $\rightarrow$ <1 hr)} &
%     \impactcell{$220K+/yr}{Annual cloud cost savings ...} &
%     \impactcell{$14M}{Acquisition overestimation ...} &
%     \impactcell{$2M+}{Incremental FIFA 19 revenue ...}
%   \end{impactbox}
%
% Implementation note: we capture the tabular into a savebox first, then wrap
% the savebox in \colorbox. Putting `\begin{tabular}` directly inside
% \colorbox's argument breaks `&` tokenization on some xelatex versions.
%----------------------------------------------------------------------------------------
\newsavebox{\impactSbox}

\newenvironment{impactbox}{%
  \begin{lrbox}{\impactSbox}%
    \begin{minipage}{\dimexpr\linewidth-2\fboxsep\relax}%
      \vspace{0.25em}%
      \centering
      \begin{tabular}{@{}*{4}{>{\centering\arraybackslash}p{0.225\linewidth}}@{}}
}{%
      \end{tabular}\par
      \vspace{0.25em}%
    \end{minipage}%
  \end{lrbox}%
  \par\noindent\colorbox{impactbg}{\usebox{\impactSbox}}\par
  \vspace{0.4em}%
}

\newcommand{\impactcell}[2]{%
  {\fontsize{18pt}{20pt}\bodyfont\bfseries\color{atsblue} #1}\\[0.25em]
  {\footnotesize\color{darkgray} #2}%
}

% Three-cell variant for families that surface fewer metrics.
\newenvironment{impactbox*}{%
  \begin{lrbox}{\impactSbox}%
    \begin{minipage}{\dimexpr\linewidth-2\fboxsep\relax}%
      \vspace{0.25em}%
      \centering
      \begin{tabular}{@{}*{3}{>{\centering\arraybackslash}p{0.3\linewidth}}@{}}
}{%
      \end{tabular}\par
      \vspace{0.25em}%
    \end{minipage}%
  \end{lrbox}%
  \par\noindent\colorbox{impactbg}{\usebox{\impactSbox}}\par
  \vspace{0.4em}%
}

%----------------------------------------------------------------------------------------
% Key-achievements box
%
% Usage:
%   \begin{achievementbox}{Key Achievements}
%     \achievement{Reporting Modernisation}{Migrated analytics ETLs off Domino ...}
%     \achievement{Self-Service Delivery}{Cut 14-hr daily refresh to under 1 hr ...}
%     ... (4 entries)
%   \end{achievementbox}
%
% A light-shaded box (same fill as the impact-metrics callout) holding a
% single-column list. Argument #1 is the section heading — emitted by the
% environment itself (NOT a separate \section call) so heading + box stay
% together.
%
% Page-fit mechanics (this took some doing):
%  - The achievement items are captured into \achieveSbox via lrbox, then
%    \colorbox-wrapped.
%  - Heading + rule + shaded box are assembled into ONE \vbox (\achieveOuter).
%    A \vbox is inherently unbreakable, so the heading can never orphan from
%    its box.
%  - \boxmaxdepth=0pt while that \vbox is packed forces it to zero depth —
%    all its extent becomes height. Without this, the colorbox's large depth
%    propagates to the \vbox, and the page builder (which caps a trailing
%    box's depth at \maxdepth and bills the excess as height) mis-estimates
%    the room needed and bumps the whole box to the next page even when it
%    plainly fits. Zero depth makes the page-fit accounting exact.
%----------------------------------------------------------------------------------------
\newsavebox{\achieveSbox}
\newsavebox{\achieveOuter}

\newenvironment{achievementbox}[1]{%
  \def\@achievetitle{#1}%
  \begin{lrbox}{\achieveSbox}%
    \begin{minipage}[t]{\dimexpr\linewidth-2\fboxsep\relax}%
      \small
      \vspace{0.1em}%
      \begin{itemize}[
          leftmargin=1.5em, itemsep=0.2em, parsep=0pt, topsep=0.1em,
          label={\textcolor{atsblue}{\rule[0.15ex]{0.55ex}{0.55ex}}}, labelsep=0.55em
      ]%
}{%
      \end{itemize}%
      \vspace{0.1em}%
    \end{minipage}%
  \end{lrbox}%
  % Assemble heading + rule + shaded box into one zero-depth \vbox.
  \par\addvspace{0.45em}%
  \setbox\achieveOuter=\vbox{%
    \boxmaxdepth=\z@
    \hsize=\linewidth \@parboxrestore \parindent=\z@
    {\headingfont\large\color{atsblue}\MakeUppercase{\@achievetitle}}\par
    \vspace{-0.4em}%
    {\color{atsblue}\rule{\linewidth}{0.5pt}}\par
    \vspace{0.25em}%
    \noindent\colorbox{impactbg}{\usebox{\achieveSbox}}\par
  }%
  % Add the assembled box in VERTICAL mode (no \noindent / no enclosing
  % paragraph). \box in vmode stacks it as a true vertical box; wrapping it
  % in a paragraph instead would make it a giant "line" and wreck the
  % page-fit accounting.
  \box\achieveOuter
  \addvspace{0.4em}%
}

\newcommand{\achievement}[2]{%
  \item {\headingfont\color{atsblue} #1} — #2%
}

%----------------------------------------------------------------------------------------
% Experience block — company / role / bullets
%
% Usage:
%   \jobcompany{Kano Apps}{Casual Games}
%   \jobrole{Senior Analytics Engineer}{May 2025 -- Feb 2026}
%   \jobsummary{Hired to modernize the studio's analytics stack ...}
%   \begin{jobbullets}
%     \item Introduced dbt to standardize ...
%   \end{jobbullets}
%----------------------------------------------------------------------------------------
\newcommand{\jobcompany}[2]{%
  \par\vspace{0.6em}%
  {\Large\bodyfont\bfseries\color{atsblue} #1%
    \ifx&#2&\else{ — \color{atsblue}#2}\fi}\par
  \vspace{-0.1em}%
}

% \jobrole{title}{dates}{location}
%   Title (bold) on the left; the right side shows the location and dates
%   in italic, separated by a bullet. If the location (#3) is empty the
%   bullet and location are dropped so only the dates show.
\newcommand{\jobrole}[3]{%
  \noindent{\bodyfont\bfseries\color{darkgray} #1}\hfill
  {\italica{\ifx\relax#3\relax #2\else #3 \textbullet\ #2\fi}}\par
  \vspace{0.05em}%
}

\newcommand{\jobsummary}[1]{%
  \noindent #1\par
  \vspace{0.05em}%
}

\newenvironment{jobbullets}{%
  \begin{itemize}[
      leftmargin=1.2em, itemsep=0.10em, parsep=0pt, topsep=0.15em,
      label={\textbullet}, labelsep=0.4em
  ]%
}{%
  \end{itemize}%
}

% Sub-section header inside a job block (used by "Responsibilities:" / "Outcomes:")
\newcommand{\jobsubhead}[1]{%
  \par\vspace{0.15em}%
  {\bodyfont\bfseries\color{darkgray} #1:}\par
  \vspace{-0.4em}%
}

%----------------------------------------------------------------------------------------
% Education block — two-column row of \edudegree's
%
% Usage:
%   \begin{edublock}
%     \edudegree{Master of Arts, Economics}{University of Victoria}{Sept 2011 -- Aug 2014}
%     &
%     \edudegree{Bachelor of Science, Economics (Minor: Mathematics)}{Illinois State University}{Sept 2006 -- May 2010}
%   \end{edublock}
%----------------------------------------------------------------------------------------
\newenvironment{edublock}{%
  \par\noindent
  \begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.47\linewidth}@{\hspace{0.6em}}>{\raggedright\arraybackslash}p{0.47\linewidth}@{}}
}{%
  \end{tabular}\par
  \vspace{0.2em}%
}

\newcommand{\edudegree}[3]{%
  \bodyfont\bfseries\color{darkgray} #1 \\[0.05em]
  {\footnotesize\color{gray} #2 \,\textbar\, #3}%
}

% Single-column education entry (for when there's only one degree in scope)
\newcommand{\edusingle}[3]{%
  \par\noindent
  {\bodyfont\bfseries\color{darkgray} #1}\par
  {\footnotesize\color{gray} #2 \,\textbar\, #3}\par
  \vspace{0.2em}%
}

%----------------------------------------------------------------------------------------
% Certifications block (compact list, used when certs_placement="education")
%----------------------------------------------------------------------------------------
\newenvironment{certlist}{%
  \begin{itemize}[
      leftmargin=1.2em, itemsep=0.10em, parsep=0pt, topsep=0.15em,
      label={\textbullet}, labelsep=0.4em
  ]%
}{%
  \end{itemize}%
}

\newcommand{\certentry}[3]{%
  \item \textbf{#1} — #2 \ \italica{(#3)}%
}
