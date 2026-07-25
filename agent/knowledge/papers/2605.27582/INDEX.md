# Uni-LaViRA (arXiv:2605.27582)

%%% FILE: main.tex
\documentclass[conference]{IEEEtran}
\usepackage{amsmath,amsfonts}
\usepackage{algorithmic}
\usepackage{algorithm}
\usepackage{array}
\usepackage[caption=false,font=normalsize,labelfont=sf,textfont=sf]{subfig}
\usepackage{textcomp}
\usepackage{stfloats}
\usepackage{cuted}  
\usepackage{url}
\usepackage{verbatim}
\usepackage{graphicx}
\usepackage{cite}
\hyphenation{op-tical net-works semi-conduc-tor IEEE-Xplore}

\usepackage{subfiles}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{multirow}
\usepackage{wrapfig}
\usepackage{colortbl}
\usepackage{makecell}
\usepackage{pifont}
\newcommand{\cmark}{\ding{51}\xspace}
\newcommand{\ys}[1]{(ys:#1)}
\newcommand{\diffvsprior}[1]{#1}

\usepackage{xspace}
\usepackage{bm}
\usepackage{amssymb}
\usepackage{hyperref}
\definecolor{hyperblue}{rgb}{0,0,1}
\hypersetup{colorlinks,linkcolor=hyperblue,citecolor=hyperblue,urlcolor=hyperblue}
\graphicspath{{figs/}}
\newcommand{\ourmethod}{Uni-LaViRA\xspace}


\renewcommand{\thetable}{\Roman{table}}


\usepackage{iftex}
\ifPDFTeX\else\usepackage{lmodern}\fi



\makeatletter
\AtBeginDocument{
  \long\def\@makecaption#1#2{
    \def\@IEEEcaptype@tmp{table}
    \ifx\@captype\@IEEEcaptype@tmp
      
      {\normalfont\footnotesize\centering {#1.}\nobreakspace\nobreakspace #2\par}
      \@IEEEtablecaptionsepspace
      \vskip 4pt
    \else
      
      \@IEEEfigurecaptionsepspace
      \setbox\@tempboxa\hbox{\normalfont\footnotesize {#1.}\nobreakspace\nobreakspace #2}
      \ifdim \wd\@tempboxa >\hsize
        \setbox\@tempboxa\hbox{\normalfont\footnotesize {#1.}\nobreakspace\nobreakspace}
        \parbox[t]{\hsize}{\normalfont\footnotesize\noindent\unhbox\@tempboxa #2}
      \else
        \ifCLASSOPTIONconference \hbox to\hsize{\normalfont\footnotesize\hfil\box\@tempboxa\hfil}
        \else \hbox to\hsize{\normalfont\footnotesize\box\@tempboxa\hfil}\fi
      \fi
    \fi}
}
\makeatother

\begin{document}

\title{Uni-LaViRA: Language-Vision-Robot Actions Translation for Unified
Embodied Navigation}

\author{
  \IEEEauthorblockN{
    Hongyu~Ding\textsuperscript{1,2,*},
    Sizhuo~Zhang\textsuperscript{3,*},
    Ziming~Xu\textsuperscript{1,*},
    Jinwen~Guo\textsuperscript{1},
    Hongxiu~Liu\textsuperscript{1},
    Xingzhi~Cheng\textsuperscript{1},\\
    Zixuan~Chen\textsuperscript{1},
    Haifei~Qi\textsuperscript{4},
    Duo~Wang\textsuperscript{4},
    Hao~Xu\textsuperscript{1},
    Jieqi~Shi\textsuperscript{1,\textdagger},
    Yifan~Zhang\textsuperscript{2,\textdagger},\\
    Jing~Huo\textsuperscript{1,\textdagger},
    Jian~Cheng\textsuperscript{2},
    Yang~Gao\textsuperscript{1},
    and~Jiebo~Luo\textsuperscript{5}
  }
  \vspace{8pt}
  \IEEEauthorblockA{
    \textsuperscript{1}Nanjing University, Nanjing, China \quad
    \textsuperscript{3}Beihang University, Beijing, China\\
    \textsuperscript{2}Institute of Automation, Chinese Academy of Sciences, Beijing, China\\
    \textsuperscript{4}BMW (Nanjing) Information Technology Co., Ltd., Nanjing, China\\
    \textsuperscript{5}University of Rochester, Rochester, NY, USA
  }
  \vspace{6.3pt}
  \IEEEauthorblockA{
    \normalsize Project page: \url{https://xetroubadour.github.io/Uni-LaViRA/}
  }
}

\maketitle



\setlength\stripsep{-15pt}
\begin{strip}
  {\centering
   \includegraphics[width=\textwidth]{teaser.pdf}\par}
  \vspace{3pt}
  \refstepcounter{figure}\label{fig:teaser}
  {\footnotesize Fig.~\thefigure.\quad \textbf{\ourmethod in one picture.}
  (Left) A single zero-shot agentic architecture realises
  Language\,$\rightarrow$\,Vision\,$\rightarrow$\,Robot
  Action translation across four task families and four real
  embodiments.  (Right) With zero training effort, \ourmethod reaches
  state-of-the-art performance against training navigation foundation
  models that consume millions of samples and thousands of
  GPU-hours.\par}
  \vspace{17.5pt}
\end{strip}

\begin{abstract}
Embodied navigation requires an agent to map language and visual observations
to a stream of spatial actions that drive a real robot through environments it
has never seen. The dominant approach has been to scale vision-language-action
(VLA) foundation models on ever-larger collections of robot trajectories. This
paper argues that, for navigation specifically, generality can be obtained
structurally, not only through data scale. The underlying decision structure
of navigation reduces to a single \emph{Language-Vision-Robot Actions
Translation}. The language action emits semantic-level directional command and
the vision action emits a pixel-level visual target. Both outputs lie inside
the natural output manifold of pretrained multimodal large language models
(MLLMs), so the task can be reasoned about by an \emph{agent} rather than
learned from robot data. Therefore, we present \textbf{\ourmethod}, a unified
agentic architecture that extends the same insight to four task families
(VLN-CE, ObjectNav, EQA, and Aerial-VLN) and to four heterogeneous real robots
(Wheeled, Quadruped, Humanoid robot, and a self-built UAV) in a zero-shot
manner. Two agent-loop mechanisms make this unification practical. TODO List
Memory (TDM) rewrites a structured checklist of pending sub-goals at every
step, reciting the unfinished items back into the agent's most recent
attention window. Second Chance Backtrack (SCB) rolls the robot back to the
pre-error state and conditions the agent's next plan on the failed
sub-trajectory, turning single-pass navigation into a self-correcting process.
With zero training effort, \ourmethod reaches 60.7\% SR on VLN-CE R2R, 51.3\%
on VLN-CE RxR, 77.7\% on HM3D-v2, 60.0\% on HM3D-OVON, 54.7\% on MP3D-EQA, and
40.00\% on OpenUAV, matching or even surpassing recent training navigation
foundation models that consume millions of samples and thousands of GPU-hours.
\end{abstract}

\begin{IEEEkeywords}
Embodied AI, Embodied navigation, multimodal large language models, zero-shot
navigation, agentic systems.
\end{IEEEkeywords}

\section{Introduction}
\label{sec:introduction}

Embodied navigation, the problem of moving a physical
agent through a previously unseen environment in response to a
language instruction, sits at the intersection of computer vision,
natural language understanding, and robotics.  It has emerged as
one of the central testbeds for general-purpose embodied
intelligence.
Its task families have expanded over the past decade. Vision-and-language
navigation (VLN-CE)~\cite{anderson2018vision,krantz2020beyond,ku2020rxr}
requires an agent to follow step-by-step natural-language instructions through
indoor scenes. Object-goal navigation
(ObjectNav)~\cite{batra2020objectnav,ramakrishnan2021hm3d,yokoyama2024hm3dovon}
asks the agent to locate an instance of a named object category in an
unfamiliar environment. Embodied question answering
(EQA)~\cite{das2018eqa,majumdar2024openeqa} couples navigation with active
perception, requiring the agent to explore until it can answer a question
grounded in the scene. Aerial vision-and-language navigation
(Aerial-VLN)~\cite{wang2024openuav} extends instruction following to outdoor,
three-dimensional flight.  These tasks differ in instruction format, sensing
modality, and embodiment, but share a common substrate.  The agent must
perceive a visual scene, interpret a language input, and emit a sequence of
spatial actions that move it toward an intended state.  {Building a single
system that generalises across this spectrum is a long-standing goal of the
field.}


Over the past two years, the dominant answer to generality in embodied
navigation has converged on a single recipe, training ever-larger
vision-language-action (VLA) foundation models on ever-growing collections of
robot trajectories~\cite{zhang2024navid,
zhang2024uninavid,cheng2024navila,wei2025streamvln,zhang2025navfom}. Each
generation grows training data and compute by orders of magnitude and reports
commensurate gains on performance and task coverage, in effect aiming at a
scaling law for embodied navigation. This line of work stakes cross-task and
cross-embodiment generalisation on data scale. {This paper argues for a
complementary source.} For navigation specifically, generality can be obtained
structurally rather than through data scale alone, once the task is decomposed
in the right way. Across VLN-CE, ObjectNav, EQA, and Aerial-VLN, the
underlying decision structure is stable across all four. The agent reasons
about the instruction, grounds it in the current observation, and emits a
spatial action. {Our conference work LaViRA~\cite{ding2025lavira} made the
central observation that this structure can be realised as a
\emph{Language-Vision-Robot Actions Translation}. The language action emits
semantic-level directional command and the vision action emits a pixel-level
visual target. Both outputs coincide with representations that modern
multimodal large language models (MLLMs) encounter repeatedly during
pretraining.} Every level therefore lands inside what we call the
\emph{natural output manifold} of foundation models, and the task can be
reasoned about by an agent rather than learned by a policy trained on robot
data. {This observation has, we believe, received less attention than it
warrants from a community largely focused on scaling end-to-end navigation
VLAs.}

Our position can be framed as a simple question that motivates this work: does
a task's action space fall inside or outside the pretrained manifold of modern
MLLMs? Within embodied AI, this splits tasks into two regimes, those that are
contact-rich and those that are mostly contact-free. Long-horizon dexterous
manipulation sits firmly on the contact-rich side. Its action semantics, such
as joint torques, contact forces, and impedance schedules, emerge from
continuous physical interaction with objects. They appear as raw numerical
sequences that MLLMs rarely encounter during pretraining. As a result, they
sit firmly outside the MLLM manifold, and such tasks still require end-to-end
VLA learning~\cite{black2024pi0,kim2024openvla}. Mainstream navigation methods
today, by contrast, are mostly contact-free, although cluttered scenes can
still involve incidental collisions or light interaction. A navigating agent
does not negotiate forces with the world but moves through it, and its
decisions reduce naturally to spatial reasoning in language, vision, and
coordinate space. {This physical property is precisely what makes the LaViRA
decomposition possible, and it is what allows navigation, alone among embodied
behaviours, to fully inherit the generalisation power of pretrained MLLMs
without any additional training.}

Beyond the unified framework itself, \ourmethod introduces two mechanisms that
address recurring failure modes of online agentic navigation. The first,
\emph{TODO List Memory} (TDM), reflects a key lesson from recent practice in
long-horizon agent
design~\cite{yao2023react,shinn2023reflexion,huang2022inner}. A long-horizon
agent benefits less from a longer context than from a better-attended one.
Rather than feeding the agent a growing conversation history at every step,
TDM maintains an explicit, dynamically updated list of the sub-tasks implied
by the instruction, {recording what has been completed, what remains, and what
is in progress}. This serves two purposes. It forces the agent to commit to a
high-level plan in a structured form before it emits the next language-level
action, turning each step into an explicit plan-then-act decision rather than
an implicit one. And by rewriting the list at every decision step, TDM
\emph{recites} the unfinished sub-goals back into the agent's most recent
attention window. The second mechanism, Second Chance Backtrack (SCB),
revisits how navigation agents should handle their own mistakes. Backtracking
itself is not new. SmartWay~\cite{shi2025smartway} introduced a backtrack
action for VLN-CE, and LaViRA~\cite{ding2025lavira} used a basic action-level reversal. Both treat
an erroneous step as something to be undone and discarded. SCB takes the
opposite stance. When the agent detects a recent decision that has led the
trajectory off-instruction, it rolls the robot back to the pre-error spatial
state and conditions the next plan on the failed sub-trajectory. The agent
then re-plans with explicit awareness of what did not work. Treating errors as
informative rather than as noise turns single-pass agentic navigation into a
self-correcting process.

This paper is a systematic extension of our preliminary conference version
LaViRA~\cite{ding2025lavira}, which validated the Language--Vision--Robot
Actions Translation idea on a single task family (VLN-CE). LaViRA established
the three-level agentic spine, but three limitations of the conference version
become bottlenecks as soon as one tries to apply the same architecture beyond
instruction-following VLN. \textbf{(L1) Single-task scope.} The conference
prompt schemas, action set, and stopping logic were specialised to
step-by-step instruction following. A single architecture covering ObjectNav,
EQA, and Aerial-VLN under one prompt interface had not been demonstrated.
\textbf{(L2) Attention drift on long instructions.} On RxR, where mean
instruction length is roughly four times that of R2R at about $120$ words, and
on multi-stage UAV flight plans, the LaViRA Language Action Model frequently
forgot which intermediate sub-goals had been satisfied. The agent then emitted
\texttt{stop} prematurely after the first matched landmark. \textbf{(L3) Error
reasoning after a wrong decision.} LaViRA included a primitive reversal action
that returned the agent to the previous waypoint, but the failed
sub-trajectory was discarded, so recovery was effectively a blind retry.

Relative to the conference version, the present manuscript extends the work
along the following four axes.

\begin{itemize}
\item \textbf{From single-task to unified embodied navigation
(addressing~L1).}
We extend the three-level agentic framework from VLN-CE alone to
four heterogeneous task families, namely VLN-CE,
ObjectNav, EQA, and Aerial-VLN, under a
single prompt interface, action set, and controller stack, with
the Language Action Model and Vision Action
Model reused verbatim across tasks.
\item \textbf{TODO List Memory (TDM, addressing~L2).}
We introduce a structured working-memory mechanism that maintains
the agent's progress as an explicit, dynamically updated list of
pending and completed sub-tasks.  TDM
externalises the agent's plan into a form that is re-read at every
decision step, so long multi-clause instructions remain fully
tracked across long horizons.
\item \textbf{Second Chance Backtrack (SCB, addressing~L3).}
We extend LaViRA's primitive reversal action into a full
error-aware re-planning mechanism.  Erroneous trajectories are not
erased but presented back to the agent as reasoning context after
the embodiment is restored to its pre-error state.  This turns
single-pass agentic navigation into a self-correcting process.
\item \textbf{Cross-embodiment real-world deployment and extensive
new analyses.}
The same agentic core is deployed on four heterogeneous real
robots, a wheeled bimanual Agilex Cobot~Magic, a Unitree~G1
humanoid, a Unitree~Go1 quadruped, and a self-built quadrotor UAV,
by swapping only the low-level controller.  We additionally
provide per-task TDM/SCB ablations, a $1{,}800$-trial failure-mode
taxonomy, and an inference-cost analysis.
\end{itemize}

\begin{table}[!t]
\centering
\caption{Scope of LaViRA and \ourmethod. The latter generalises the
agentic core from one task family on two embodiments to four families on four
heterogeneous robots, and adds two new agent-loop mechanisms.}
\label{tab:lavira-vs-unilavira}
\footnotesize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.1}

\resizebox{0.85\columnwidth}{!}{
\begin{tabular}{@{}c c c@{}}
\toprule
\textbf{Aspect} & \textbf{LaViRA} & \textbf{\ourmethod} \\
\midrule
Task families     & 1               & 4 \\
Real embodiments  & 2               & 4 \\
Working memory    & Prompt history  & TDM \\
Error recovery    & 1-step revert   & SCB \\
Failure analysis  & Qualitative     & Quantitative + scaling \\
\bottomrule
\end{tabular}
}

\end{table}

Table~\ref{tab:lavira-vs-unilavira} summarises the scope and methodological
insights distinguishing the two versions. The remainder of this paper is
organised as follows. Section~\ref{sec:related} reviews related work on
vision-and-language navigation, zero-shot navigation pipelines, navigation
foundation models, and agentic AI systems. Section~\ref{sec:method} presents
the \ourmethod framework, including the unified problem definition, the
agentic architecture, the TODO List Memory and Second Chance Backtrack
mechanisms, and the unified inference procedure. Section~\ref{sec:experiments}
reports zero-shot results across the four task families, validates the
100-episode subset, compares against trained foundation models, and provides
ablation studies, an inference-cost analysis, and a failure-mode taxonomy.
Section~\ref{sec:realworld} reports real-robot deployments across the four
heterogeneous platforms, and Section~\ref{sec:conclusion} concludes.

\section{Related Work}
\label{sec:related}

\subsection{Vision-and-Language Navigation}

VLN was introduced by Anderson~et~al.~\cite{anderson2018vision} in the
discrete Matterport3D graph setting~\cite{chang2017matterport3d} and later
extended to continuous environments (VLN-CE) by
Krantz~et~al.~\cite{krantz2020beyond}, with multilingual dense instructions
introduced in RxR~\cite{ku2020rxr}. Learned methods have progressed steadily
through cross-modal alignment~\cite{hong2021vlnbert,chen2022duet}, explicit
map representations~\cite{wang2023gridmm,an2023bevbert, an2024etpnav},
large-scale data augmentation~\cite{wang2023scalevln}, and curriculum
learning~\cite{zhu2020babywalk}. The strongest end-to-end supervised methods on VLN-CE R2R are recent
foundation models such as OmniNav~\cite{xue2025omninav} and
ABot-N0~\cite{chen2026abotn0}, which reach roughly $66$--$70\%$ SR by training
on heterogeneous robot data; we discuss this regime in detail in
Section~\ref{subsec:nav_foundation_models}. All of these methods rely on
environment-specific training. The learned weights encode scene priors from
the training distribution and do not transfer to new environments, task
variations, or embodiments without costly retraining. \ourmethod matches and
in several cases surpasses these methods with zero robot data, indicating that
scene-specific learning is not required when the action space already lies
inside the natural output manifold of pretrained MLLMs.

\subsection{Zero-Shot Navigation}

Zero-shot methods avoid robot-data training but introduce other dependencies.
\emph{Waypoint-based} approaches pair an LLM with a pretrained waypoint
predictor~\cite{qiao2024opennav,shi2025smartway,hong2022bridging}. The
predictor proposes discrete candidates and the LLM selects among them, but the
pretrained predictor is itself environment-specific and its candidate set
bounds where the agent can go. \emph{Value-mapping} approaches generate a
semantic heatmap from a VLM and navigate toward the
peak~\cite{chen2025canav,long2024instructnav,yokoyama2024vlfm,
yin2025gcvln,zhou2023esc,kuang2024openfmnav}. These exploit strong VLMs for
open-vocabulary grounding, but typically use the LLM only \emph{offline} to
parse the instruction. A third line treats LLMs as planners over discrete
topological graphs~\cite{zhou2024navgpt,chen2024mapgpt,long2024discussnav}, a
formulation that does not extend naturally to continuous control. Lifelong,
multi-modal-goal systems such as GOAT~\cite{chang2024goat,khanna2024goatbench}
contribute instance-aware semantic memory but still rely on trained skills for
navigation primitives. {The conference version of this work,
LaViRA~\cite{ding2025lavira}, established the three-level agentic
decomposition on VLN-CE. The present paper extends it to four task families
and adds the two agent-loop mechanisms developed in
Sections~\ref{subsec:tdm}--\ref{subsec:scb}.} \ourmethod requires no waypoint
predictor, because the Vision Action Model grounds directly on raw pixels, and
keeps the Language Action Model reasoning online at every decision step in
continuous environments.

\subsection{Navigation Foundation Models}
\label{subsec:nav_foundation_models}

The most prominent contemporary alternative is to train a single VLA model on
heterogeneous robot data and let scale do the work. Starting from VLM-based
navigation on monocular video~\cite{zhang2024navid}, subsequent foundation
models pushed along orthogonal axes of unified task
coverage~\cite{zhang2024uninavid,xue2025omninav}, action-space tokenisation
for new embodiments~\cite{cheng2024navila}, streaming
inference~\cite{wei2025streamvln}, memory
architectures~\cite{zeng2025janusvln,wei2025internvlan1}, and large-scale
cross-embodiment training~\cite{zhang2025navfom,chen2026abotn0}. Across
roughly two years, training data has grown from below $1$\,M to over $16$\,M
trajectories spanning quadrupeds, drones, wheeled robots, humanoids, and
vehicles, while reported SR on VLN-CE R2R has climbed from below $40\%$ to
roughly $70\%$. The sequence reads as a coherent attempt to demonstrate a
\emph{scaling law for embodied navigation}: each generation grows training
data, compute, and task coverage by orders of magnitude, with reported
performance climbing in step. {\ourmethod takes the opposite stance. Because
the decision structure of navigation already lies inside the natural output
manifold of pretrained MLLMs, no training above the low-level controller is
required, and each upper-level agent inherits MLLM backbone improvements
directly without consuming additional robot data.}

\subsection{Agentic AI in the Physical World}

The rise of agentic AI, in which foundation models reason, plan, and act
through structured interaction with tools and
environments~\cite{yao2023react}, has reshaped thinking about AI capabilities
across domains. Representative systems range from SayCan~\cite{ahn2022saycan}
and Code-as-Policies~\cite{liang2023cap} to Voyager~\cite{wang2024voyager},
Inner Monologue~\cite{huang2022inner}, Reflexion~\cite{shinn2023reflexion},
and Agent-S~\cite{agashe2025agents}. Hierarchical decomposition has a long
history in reinforcement learning~\cite{bellman1966dynamic,sutton1999between}
and has appeared in VLN as feudal planners~\cite{liu2023azhp,zhao2025nava3}.

\textbf{Memory representations for long-horizon agents.}
MemGPT~\cite{packer2023memgpt} treats the context window as an OS-managed
virtual memory with explicit paging between a fast working set and an external
store; Generative Agents~\cite{park2023generative} maintain a time-stamped
memory stream with periodic reflection that summarises recent events into
higher-level beliefs; MemoryBank~\cite{zhong2024memorybank} adds long-term
retention with an Ebbinghaus-style forgetting schedule; and
Voyager~\cite{wang2024voyager} grows a structured skill library as procedural
memory for embodied agents. These representations are designed for
general-purpose conversational or open-ended agents and store mostly free-form
items; long-horizon embodied navigation specifically needs to track which
sub-goals of a multi-clause instruction are still pending and which have
already been satisfied at a specific scene observation. The
TDM mechanism we propose in this paper sits in the same lineage but is
tailored to navigation: it maintains an ordered, verifiable checklist of
sub-goals that the agent re-reads and updates at every step, so completion is
grounded in observations rather than left to free-form recall.

\textbf{Error recovery in navigation.} SmartWay~\cite{shi2025smartway} and
LaViRA~\cite{ding2025lavira} both treat a failed step as
something to be undone and discarded. Discarding the failed sub-trajectory,
however, also discards the signal of \emph{why} the previous decision was
wrong, so the agent re-decides from the same prior with no new evidence and
frequently repeats the same mistake. SCB, the second mechanism
we introduce, instead conditions the re-decision on the failed
sub-trajectory itself, turning error evidence into planning context. This is
closer in spirit to the self-critique pattern of
Reflexion~\cite{shinn2023reflexion} but operates at the spatial-trajectory
level rather than the text-trial level.

\section{The \ourmethod Framework}
\label{sec:method}

\textbf{Difference from LaViRA.} Our method builds upon the three-level
Language-Vision-Robot pipeline originally introduced in
LaViRA~\cite{ding2025lavira}. In the present version, we extend it by scaling
from one task family and two embodiments to four task families and four
heterogeneous embodiments, and by adding two agent-loop mechanisms, TODO List
Memory (Section~\ref{subsec:tdm}) and Second Chance Backtrack
(Section~\ref{subsec:scb}). This extension is necessary because the conference
version's prompts and action set were specialised to instruction following,
its working memory degraded on long-horizon directives, and its blind-retry
recovery left repeated errors uncorrected, all of which become bottlenecks
once the pipeline is applied to ObjectNav, EQA, and Aerial-VLN.

Section~\ref{subsec:problem} abstracts the four task families into a single
decision problem. Section~\ref{subsec:architecture} instantiates the
three-level spine under the resulting unified interface.
Sections~\ref{subsec:tdm} and~\ref{subsec:scb} introduce TODO List Memory and
Second Chance Backtrack, the two new agent-loop mechanisms that this paper
adds to the LaViRA spine. Section~\ref{subsec:algorithm} assembles them into a
single per-episode loop.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=0.85\linewidth]{pipeline.pdf}
  \caption{\textbf{The \ourmethod pipeline.}  Language Action emits a
  tool call, Vision Action grounds it on the agent's first-person view
  along the chosen direction, and Robot Action dispatches it.  TDM
  maintains an online checklist; SCB rewinds to a prior waypoint when
  a sub-goal fails. Together, the three-level decomposition
  and the two agent-loop mechanisms turn each step into a verifiable,
  self-correcting decision shared by all four task families.}
  \label{fig:pipeline}
\end{figure*}

\subsection{Problem Definition}
\label{subsec:problem}

We consider four families of embodied navigation. The first three run inside
Habitat-Sim~\cite{krantz2020beyond}. Vision-and-language navigation in
continuous environments (VLN-CE)~\cite{anderson2018vision,ku2020rxr} covers
R2R and RxR. Object-goal navigation (ObjectNav) covers HM3D-v2 and HM3D-OVON.
Embodied question answering (EQA) uses
MP3D-EQA~\cite{das2018eqa,majumdar2024openeqa}. Aerial vision-and-language
navigation (Aerial-VLN) uses OpenUAV~\cite{wang2024openuav} inside AirSim.
Despite differing simulators, embodiments, and goal specifications, all four
families share the same input and output interface from the policy's perspective.

\textbf{Unified interface.} At every decision step $t$, an agent receives
\begin{itemize}
  \item a task specification $\mathcal{T}$ expressed in natural
  language.  This is a route description for
  VLN-CE, an object category or open-vocabulary phrase for
  ObjectNav, a question for EQA, or a flight directive for Aerial-VLN.
  \item an egocentric observation $\mathcal{O}_t$ consisting of RGB and
  aligned depth. In simulation, ground robots carry only a single front-view
  RGB-D camera; the front, left, right, and back views are obtained by
  rotating the robot in place at each waypoint. The
  UAV carries five fixed cameras providing front, left, right, back, and
  downward views directly.
  \item the current pose $(x_t, y_t, z_t, \theta_t)$ in the world
  frame, exposed by the simulator.
  \item a structured history $\mathcal{H}_t$ of previously visited
  waypoints, keyed observations, and prior decisions.
\end{itemize}
It must emit a low-level action $\mathcal{A}_t$ in the embodiment'

[... truncated for index ...]

