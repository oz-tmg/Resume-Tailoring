% -- Encoding UTF-8 without BOM

\ProvidesClass{cv-style}[2015/02/27 CV class]
\NeedsTeXFormat{LaTeX2e}

\DeclareOption{espanol}{\def\@cv@espanol{}}
\DeclareOption{print}{\def\@cv@print{}}
\DeclareOption*{%
  \PassOptionsToClass{\CurrentOption}{article}%
}
\ProcessOptions\relax
\LoadClass{article}

%----------------------------------------------------------------------------------------
% Colors %
%----------------------------------------------------------------------------------------
\RequirePackage{xcolor}

\definecolor{white}{RGB}{255,255,255}

\definecolor{darkgray}{HTML}{333333}
\definecolor{gray}{HTML}{4D4D4D}
\definecolor{lightgray}{HTML}{999999}

\definecolor{blue}{HTML}{66D9EE}
\definecolor{red}{HTML}{FA2772}
\definecolor{orange}{HTML}{FE9720}
\definecolor{green}{HTML}{A7E22E}
\definecolor{purple}{HTML}{9358FE}
\definecolor{aquamarine}{HTML}{36AF90}
\definecolor{uvicblue}{HTML}{334cff} % Custom blue color
\definecolor{isured}{HTML}{f52a12} 
\definecolor{bogazblue}{HTML}{0b01d7}
\definecolor{navyblue}{HTML}{3b4c74}

\definecolor{date}{HTML}{A4A4A4}

\ifdefined\@cv@print
  \colorlet{blue}{gray}
  \colorlet{red}{gray}
  \colorlet{orange}{gray}
  \colorlet{green}{gray}
  \colorlet{purple}{gray}
  \colorlet{aquamarine}{gray}
  \colorlet{fillheader}{white}
  \colorlet{header}{gray}
\else
  \colorlet{fillheader}{gray}
  \colorlet{header}{white}
\fi
\colorlet{textcolor}{gray}
\colorlet{headercolor}{gray}

%----------------------------------------------------------------------------------------
% Fonts %
%----------------------------------------------------------------------------------------

\RequirePackage[quiet]{fontspec}
%\RequirePackage[math-style=TeX,vargreek-shape=unicode]{unicode-math}
\RequirePackage{unicode-math}
\newfontfamily\bodyfont{Roboto-Regular}[Path=fonts/]
\newfontfamily\bodyfontit{Roboto-LightItalic}[Path=fonts/]
\newfontfamily\thinfont{Roboto-Thin}[Path=fonts/]
\newfontfamily\headingfont{RobotoCondensed-Bold}[Path=fonts/]

\defaultfontfeatures{Mapping=tex-text}
\setmainfont[Mapping=tex-text, Color=textcolor, Path = fonts/]{Roboto-Light}

\newcommand{\italica}[1]{%
    {\color{gray}\bodyfontit #1}%
}

%----------------------------------------------------------------------------------------
% Header %
%----------------------------------------------------------------------------------------

\RequirePackage{tikz}
\usepackage{fontawesome5} 

\newcommand{\header}[9]{%
  \begin{tikzpicture}[remember picture,overlay]
    \node [rectangle, fill=navyblue, anchor=north, minimum width=\paperwidth, minimum height=3.5cm] (box) at (current page.north){};
    % LEFT-aligned content block
    \node[anchor=north west, xshift=1.0cm, yshift=-0.5cm] (name) at (box.north west) {%
      \begin{minipage}[t]{0.75\paperwidth} % adjust width as needed
        \fontsize{35pt}{45pt}\color{header}%
        {\thinfont #1} {\bodyfont #2} \\[0.5em]
        \fontsize{14pt}{18pt}\color{header} 
        {\bodyfont #9} \\
        \fontsize{12pt}{18pt}\color{header}%
        \begin{tabular}{@{}l@{\hspace{0.5cm}}l@{\hspace{1.5cm}}l@{}}
          \faPhone\ \thinfont #3 & \faEnvelope\ \thinfont #4 & \faLinkedin\ \thinfont #5 \\
          \faMapMarker\ \thinfont #6 & \faGithub \thinfont #7 & \faWordpress \thinfont \ #8
        \end{tabular}
      \end{minipage}
    };
    
    \node[anchor=north east, xshift=-0.3cm, yshift=-0.2cm] at (box.north east) {%
      \tikz \draw [path picture={%
        \node at (path picture bounding box.north east) {%
          \includegraphics[height=3.5cm]{icons/logos/self_portrait.jpg}
        };
      }] (0,2) circle (1.7);
    };
  \end{tikzpicture}
  \vspace{1.2cm}
  \vspace{-2\parskip}
}

\newcommand{\subheader}[2]{%
  \begin{tikzpicture}[remember picture, overlay]
    \node [rectangle, fill=fillheader, anchor=north west, minimum width=\paperwidth, minimum height=2.0cm] (subbox) at (-5.6,-0.75) {};
    
    \node [anchor=north, xshift=-0.0cm, yshift=-0.1cm] at (subbox.north) {%
      \begin{minipage}[t]{0.90\paperwidth}
        %\fontsize{18pt}{22pt}\color{header} {\thinfont \textbf{#1}} \\[0.3em]
        \fontsize{12pt}{14pt}\color{header} {\thinfont \normalsize #2}
      \end{minipage}
    };
  \end{tikzpicture}
  %\vspace{1.8cm}
}
%----------------------------------------------------------------------------------------
%	Last updated command %
%----------------------------------------------------------------------------------------

\RequirePackage[absolute,overlay]{textpos}
\RequirePackage{polyglossia}

\newcommand{\sethyphenation}[3][]{%
  \sbox0{\begin{otherlanguage}[#1]{#2}
    \hyphenation{#3}\end{otherlanguage}}}
%\sethyphenation[<options>]{<language>}{<list of words separated by spaces>}

\ifdefined\@cv@espanol
  \setdefaultlanguage{english}
  \def\lastupdatedtext{Última Actualización el}
\else
  \setdefaultlanguage[variant=british]{english}
  \def\lastupdatedtext{Last Updated on}
\fi

\setlength{\TPHorizModule}{0.01\paperwidth}
\setlength{\TPVertModule}{0.01\paperwidth}

\newcommand{\lastupdated}{ 
  \begin{textblock}{10}(11.3, 0.05)
    \raggedleft
    \fontsize{8pt}{10pt}\color{date}\thinfont 
    \lastupdatedtext{} \today
  \end{textblock}}

%----------------------------------------------------------------------------------------
% Structure %
%----------------------------------------------------------------------------------------
\RequirePackage{parskip}

\newcounter{colorCounter}
\def\@sectioncolor#1#2#3{%
  {%
    \color{%
      \ifcase\value{colorCounter}%
        blue\or%
        red\or%
        orange\or%
        green\or%
        purple\or%
        aquamarine\else%
        headercolor\fi%
    } #1#2#3%
  }%
  \stepcounter{colorCounter}%
}

\renewcommand{\section}[1]{
  {\par\vspace{\parskip}
  {%
    \LARGE\headingfont\color{headercolor}%
    \@sectioncolor #1%
  }
  \par\vspace{\parskip}}
}

\renewcommand{\subsection}[1]{
  \par\vspace{.5\parskip}%
  \Large\headingfont\color{headercolor} #1%
  \par\vspace{.25\parskip}%
}

\newcommand{\jobtitle}[1]{%
    {\color{gray}\bodyfontit #1}%
}

\pagestyle{empty}

%----------------------------------------------------------------------------------------
% List environment %
%----------------------------------------------------------------------------------------

\setlength{\tabcolsep}{0pt}
\newenvironment{entrylist}{%
  \begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}ll}
}{%
  \end{tabular*}
}
\renewcommand{\bfseries}{\headingfont\color{headercolor}}
%\newcommand{\entry}[4]{%
%  #1&\parbox[t]{12.8cm}{%
%    \textbf{#2}%
%    \hfill%
%    {\footnotesize\addfontfeature{Color=lightgray} #3}\\%
%    #4\vspace{\parsep}%
%  }\\}
\newcommand{\entry}[4]{%
  \parbox[t]{1.8cm}{\raggedright #1}%  % Date box with fixed width and ragged-right alignment
  &  
  \parbox[t]{13cm}{%
    \textbf{#2}%
    \hfill%
    {\footnotesize\addfontfeature{Color=lightgray} #3}\\%
    #4\vspace{\parsep}%
  }\\
}

\usepackage{graphicx}
\usepackage{wrapfig}
\usepackage{tikz}

\newcommand{\roundedimage}[3][0.2cm]{%
    \begin{tikzpicture}
        \node[inner sep=0pt, rounded corners=#1, draw=none, clip] (image) {\includegraphics[width=#2]{#3}};
    \end{tikzpicture}
}

\newcommand{\roundpic}[1]{\begin{figure}[H]\tikz  \draw [path picture={ \node at (path picture bounding box.center){\includegraphics[height=3.5cm]{#1}} ;}] (0,2) circle (1.7) ;\end{figure}}

% About Me Section
\newcommand{\aboutme}[1]{%
    \noindent
    #1
}

\RequirePackage{multirow,tabularx}
\newcommand{\cvachievement}[3]{%
  \noindent\begin{tabularx}{3.6cm}{@{}p{1em} @{\hspace{0.5ex}} >{\raggedright\arraybackslash}X@{}}
  \multirow{2}{*}{\scriptsize\color{accent}\BeginAccSupp{method=escape,ActualText={#1: }}#1\EndAccSupp{}} & \scriptsize\bfseries\textcolor{emphasis}{#2}\\
  & \scriptsize #3
  \end{tabularx}%
  \smallskip
}
%----------------------------------------------------------------------------------------
% Side block %
%----------------------------------------------------------------------------------------

\setlength{\TPHorizModule}{1cm}
\setlength{\TPVertModule}{1cm}
\newenvironment{aside}{%
  \let\oldsection\section
  \renewcommand{\section}[1]{
    \par\vspace{\baselineskip}{\Large\headingfont\color{headercolor} ##1}
  }
  \begin{textblock}{3.6}(1, 1.87)
  %\begin{minipage}[c]{3cm\textwidth}
  \begin{flushright}
  \obeycr
}{%
  \restorecr
  \end{flushright}
  \end{textblock}
  %\end{minipage}
  \let\section\oldsection
}

\newcommand{\cvsection}[2][]{%
  \nointerlineskip\bigskip%  %% bugfix in v1.6.2
  \ifstrequal{#1}{}{}{\marginpar{\vspace*{\dimexpr1pt-\baselineskip}\raggedright\input{#1}}}%
  {\color{heading}\cvsectionfont\MakeUppercase{#2}}\\[-1ex]%
  {\color{headingrule}\rule{\linewidth}{2pt}\par}\medskip
}

\newcommand{\divider}{\textcolor{body!30}{\hdashrule{\linewidth}{0.6pt}{0.5ex}}\medskip}

%----------------------------------------------------------------------------------------
% Other tweaks %
%----------------------------------------------------------------------------------------

\RequirePackage[left=5.6cm,top=1cm,right=1cm,bottom=1cm,nohead,nofoot]{geometry}
\RequirePackage{hyperref}
\hypersetup{
    pdftitle=CV/Resume \textbar{} Alex Oswald,
    pdfauthor=Alex Oswald,
    pdfsubject=CV/Resume%
    }