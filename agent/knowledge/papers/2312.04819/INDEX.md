# ACORM (arXiv:2312.04819)

%%% FILE: iclr2024_conference.tex
\documentclass{article} 
\usepackage{iclr2024_conference,times}
\usepackage[T1]{fontenc}
\usepackage{graphicx} 


\input{math_commands.tex}
\usepackage{booktabs}




\usepackage[ruled,linesnumbered]{algorithm2e}


\usepackage{hyperref}
\usepackage{url}
\usepackage{enumitem}
\usepackage{amsthm}
\usepackage{subfigure}
\usepackage{soul}


\usepackage{color}
\newcommand{\zzz}[1]{\textcolor{red}{[zzz: #1]}}

\newtheorem{theorem}{Theorem}
\newtheorem{lemma}{Lemma}
\newtheorem{definition}{Definition}


\title{Attention-Guided Contrastive Role Representations for Multi-agent Reinforcement Learning}





\author{
Zican~Hu$^1$, Zongzhang~Zhang$^2$, Huaxiong~Li$^1$, Chunlin~Chen$^1$, Hongyu~Ding$^1$, Zhi~Wang$^{1}$\thanks{Corresponding author.}\vspace{0.2em}\\
\normalsize $^1~$Department of Control Science and Intelligent Engineering, Nanjing University \\
\normalsize $^2~$School of Artificial Intelligence, Nanjing University\\
\texttt{\{zicanhu,hongyuding\}@smail.nju.edu.cn}\\
\texttt{\{zzzhang,huaxiongli,clchen,zhiwang\}@nju.edu.cn}
}








\newcommand{\fix}{\marginpar{FIX}}
\newcommand{\new}{\marginpar{NEW}}


\begin{document}


\maketitle

\begin{abstract}
Real-world multi-agent tasks usually involve dynamic team composition with the emergence of roles, which should also be a key to efficient cooperation in multi-agent reinforcement learning (MARL). Drawing inspiration from the correlation between roles and agent's behavior patterns, we propose a novel framework of \textbf{A}ttention-guided \textbf{CO}ntrastive \textbf{R}ole representation learning for \textbf{M}ARL (\textbf{ACORM}) to promote behavior heterogeneity, knowledge transfer, and skillful coordination across agents. First, we introduce mutual information maximization to formalize role representation learning, derive a contrastive learning objective, and concisely approximate the distribution of negative pairs. Second, we leverage an attention mechanism to prompt the global state to attend to learned role representations in value decomposition, implicitly guiding agent coordination in a skillful role space to yield more expressive credit assignment. Experiments on challenging StarCraft II micromanagement and Google research football tasks demonstrate the state-of-the-art performance of our method and its advantages over existing approaches. Our code is available at \href{https://github.com/NJU-RL/ACORM}{https://github.com/NJU-RL/ACORM}.
\end{abstract}



\section{INTRODUCTION}
Cooperative multi-agent reinforcement learning (MARL) aims to coordinate a system of agents towards optimizing global returns~\citep{vinyals2019grandmaster}, and has witnessed significant prospects in various domains, such as autonomous vehicles~\citep{zhou2020smarts}, smart grid~\citep{chen2021powernet}, robotics~\citep{yu2023asynchronous}, and social science~\citep{leibo2017multi}.
Training reliable control policies for coordinating such systems remains a major challenge.
The centralized training with decentralized execution (CTDE)~\citep{foerster2016learning} hybrids the merits of independent Q-learning~\citep{foerster2017stabilising} and joint action learning~\citep{sukhbaatar2016learning}, and becomes a compelling paradigm that exploits the centralized training opportunity for training fully decentralized policies~\citep{wang2023more}.
Subsequently, numerous popular algorithms are proposed, including VDN~\citep{sunehag2018value}, QMIX~\citep{rashid2020monotonic}, MAAC~\citep{iqbal2019actor}, and MAPPO~\citep{yu2022surprising}.


Sharing policy parameters is crucial for scaling these algorithms to massive agents with accelerated cooperation learning~\citep{fu2022revisiting}.
However, it is widely observed that agents tend to acquire homogeneous behaviors, which might hinder diversified exploration and sophisticated coordination~\citep{christianos2021scaling}.
Some methods~\citep{li2021celebrating,jiang2021emergence,liu2023contrastive} attempt to promote individualized behaviors by distinguishing each agent from the others, while they often neglect the prospect of effective team composition with implicit task allocation.
Real-world multi-agent tasks usually involve dynamic team composition with the emergence of roles~\citep{shao2022self,hu2022policy}.~\footnote{Taking the football game~\citep{kurach2020google} as an example, the midfielders are primarily responsible for delivering the ball to the forwards to coordinate shots on goal in the offensive phase, while they need to drop back and join the defenders to block passing lanes on the defensive.}
Early works introduce the role concept into multi-agent systems~\citep{dastani2003role,sims2008automated,lhaksmana2018role}, while they usually require prior domain knowledge to pre-define role responsibilities.
Recently, ROMA~\citep{wang2020roma} learns emergent roles conditioned solely on current observations, and RODE~\citep{wang2021rode} associates each role with a fixed subset of the joint action space. 
COPA~\citep{liu2021coach} allows dynamic role allocation via distributing a global view of team composition to each agent during execution.
Some works decompose the task into a set of skills~\citep{liu2022heterogeneous} or subtasks~\citep{yang2022ldsa,iqbal2022alma} with a hierarchical structure for control.
Overall, existing role-based methods still suffer from several deficiencies, such as insufficient characterization of complex behaviors for role emergence, neglect of evolving team dynamics, or relaxation of the CTDE constraint.



To better leverage dynamic role assignment, we propose a novel framework of \textbf{A}ttention-guided \textbf{CO}ntrastive \textbf{R}ole representation learning for \textbf{M}ARL (\textbf{ACORM}).
Our main insight is to learn a compact role representation that can capture complex behavior patterns of agents, and use that role representation to promote behavior heterogeneity, knowledge transfer, and skillful coordination across agents.
First, we formalize the learning objective as mutual information maximization between the role and its representation, to maximally reduce role uncertainty given agent's behaviors while minimally preserving role-irrelevant information.
We introduce a contrastive learning method to optimize the infoNCE loss, a mutual information lower bound.
To concisely approximate the distribution of negative pairs, we extract agent behaviors by encoding its trajectory into a latent space, and periodically partition all agents into several clusters according to their latent embeddings where points from different clusters are paired as negative.
Second, during centralized training, we employ an attention mechanism to prompt the global state to attend to learned role representations in value decomposition.
The attention mechanism implicitly guides agent coordination in a skillful role space, thus yielding more expressive credit assignment with the emergence of roles.~\footnote{Taking StarCraft II as an example, the acquired roles represent diverse strategies in a team-based manner, such as focusing fire, sneaking attack, and drawing fire.
Agents with similar role representations learn a specialized strategy more efficiently by more positive information sharing, and the attention mechanism is responsible for coordinating these heterogeneous behaviors more strategically with clearer role extraction in the team.}


ACORM is fully compatible with CTDE methods, and we realize ACORM on top of two popular MARL algorithms, QMIX~\citep{rashid2020monotonic} and MAPPO~\citep{yu2022surprising}, \textcolor{black}{benchmarked on challenging StarCraft multi-agent challenge (SMAC)~\citep{samvelyan2019starcraft} and Google research football (GRF)~\citep{kurach2020google} environments.}
Experiments demonstrate that ACORM achieves state-of-the-art performance on most scenarios. 
Visualizations of learned role representations, heterogeneous behavior patterns, and attentional value decomposition shed further light on our advantages.
Ablation studies confirm that ACORM promotes higher coordination capacity by virtue of contrastive role representation learning and attention-guided credit assignment, respectively, even if agents have the same innate characteristics.
In summary, our contributions are threefold:
\begin{itemize}[itemsep=0em, leftmargin=1.5em]
\vspace{-0.5em}
    \item We propose a general role representation learning framework based on contrastive learning, which effectively tackles agent homogenization and facilitates efficient knowledge transfer.

    \item We leverage role representations to realize more expressive credit assignment via an attention mechanism, promoting strategical coordination in a sophisticated role space.

    \item We build our method on top of popular QMIX and MAPPO, and \textcolor{black}{conduct extensive experiments on SMAC and GRF to demonstrate our state-of-the-art performance and advantages.}
\end{itemize}





\section{Method}
In this section, we present the ACORM framework.
We consider cooperative multi-agent tasks formulated as a Dec-POMDP~\citep{oliehoek2016concise}, $G=\langle I, S, A, P, R, \Omega, O, n, \gamma \rangle$, where $I$ is a finite set of $n$ agents, $s\in S$ is the global state, and $\gamma\in [0,1)$ is the discount factor.
At each time step, each agent $i$ draws an observation $o_i\in O$ from $\Omega(s,i)$ and selects a local action $a_i\in A$.
After executing the joint action $\bm{a}=[a_1,...,a_n]^\top\in A^n$, the system transitions to a next state $s'$ according to $P(s'|s,\bm{a})$ and receives a reward $r=R(s,\bm{a})$ shared by all agents. 


Our idea is to learn a compact role representation that can characterize complex behavior patterns of agents, and use the role information to facilitate individual policy learning and guide agent coordination.
Agents with similar roles can enjoy higher learning efficiency via more aggressive knowledge transfer, and agent heterogeneity is also guaranteed with the discrimination of diverse roles.
Formally, we propose the following definition of the role and its representation.
\begin{definition}
Given a cooperative multi-agent task $G=\langle I, S, A, P, R, \Omega, O, n, \gamma \rangle$, each agent $i$ is associated with a role $M_i\in\mathcal{M}$ that describes its behavior pattern.
Each role $M_i$ is quantified by a role representation $z_i\in\mathcal{Z}$, which is obtained by training a complex function as $z_i = f\left(\rho_i\right)$, where $\rho_i\in\Gamma\equiv (O,A)^l$ is the local trajectory of agent $i$, and $l$ is the number of observation-action pairs.
$\pi_{z_i}: O\times A\times \mathcal{Z}\to [0,1]$ is the individual policy for agent $i$.
\end{definition}




ACORM consists of individual Q-networks in Fig.~\ref{Fig1}(b) and a mixing network in Fig.~\ref{Fig1}(a).
We introduce mutual information maximization to formalize role representation learning, and derive a contrastive learning objective that optimizes agent embeddings $\{e^t_i\}_{i=1}^n$ in a self-supervised way to acquire contrastive role representations $\{z_i^t\}_{i=1}^n$, which is shown in Fig.~\ref{Fig1}(c) and will be introduced in detail in Section~\ref{sec:role}.
In value decomposition, we employ multi-head attention (MHA) to prompt the global state to attend to learned role patterns, guiding skillful agent coordination in the high-level role space for facilitating expressive credit assignment, as described in Fig.~\ref{Fig1}(d) and in Section~\ref{sec:attention}.
Appendix~B presents the pseudocode, and Appendix~C gives the extension to MAPPO.

\begin{figure}[tb]
\centering\includegraphics[width=0.98\textwidth]{ACORM_QMIX.jpg}
\caption{The ACORM framework based on QMIX. (a) The overall architecture.
(b) The structure of shared individual Q-network.
(c) The detail of contrastive role representation learning, where $z_i$ is the query $q$, and $z_{i'}/z_{i^*}$ are positive/negative keys $k_+/k_-$. 
(d) The attention module that incorporates learned role representations into the mixing network's input for better value decomposition.
}
\label{Fig1}
\end{figure}




\subsection{Contrastive Role Representations}\label{sec:role}
Our objective is to ensure that agents with similar behavior patterns exhibit closer role representations, while those with notably different strategies are pushed away from each other.
This stands in contrast to using a one-hot ID to preserve the agent's individuality, which lacks adequate discrimination under the paradigm of parameter sharing.
Hence, the primary issues we aim to tackle are: i) how to define a feasible metric to quantify the degree of similarity between agent's behaviors, and ii) how to develop an efficient method to optimize the discrimination of role representations.


\textbf{Agent Embedding.} 
To tackle the first issue, we learn an agent embedding $e_i^t$ from each agent's trajectory to extract complex agent behaviors with contextual knowledge as $e_i^t=f_{\phi}(o_i^t, a^{t-1}_i, e^{t-1}_i)$, where $\phi$ is a shared gated recurrent unit (GRU) encoder, $o^t_i$ is the current observation, $a^{t-1}_i$ is the last action, and $e^{t-1}_i$ is the hidden state of the GRU.
Naturally, the distance between the obtained agent embeddings can serve as the metric to measure the behavior dissimilarity between agents.


\textbf{Contrastive Learning.} 
An ideally discriminative role representation should be dependent on roles associated with agent's behavior patterns, while remaining invariant across agent identities.
We introduce mutual information to measure the mutual dependency between the role and its representation.
Formally, mutual information aims to quantify the uncertainty reduction of one random variable when the other one is observed.
To tackle the second issue, we propose to maximize the mutual information between the role and its representation, and learn a role encoder that maximally reduces role uncertainty while minimally preserving role-irrelevant information.
Mathematically, we formalize the role encoder $\theta$ as a probabilistic encoder $z^t \!\sim\! f_{\theta}(z^t|e^t)$, where $z^t$ denotes the role representation at time $t$, and $e^t\!=\!f_{\phi}(\sum_{t'=1}^t(o^{t'},a^{t'-1}))$ denotes the agent embedding obtained from the history trajectory.~\footnote{Here, we use the superscript $t$ for highlighting the time-evolving property of role representations and relevant variables, and we will partially omit it for simplicity in the below.}
Role $M$ follows the role distribution $P(M)$, and the distribution of agent embedding $e$ is determined by its role.
The learning objective for the role encoder is:
\begin{equation}
    \max~I(z; M) = \mathbb{E}_{z,M}\left[\log \frac{p(M|z)}{p(M)}\right].
    \label{mi}
\end{equation}
In practice, directly optimizing mutual information is intractable.
Inspired by the noise contrastive estimation (InfoNCE)~\citep{oord2018representation} in the literature of contrastive learning~\citep{laskin2020curl,yuan2022robust}, we derive a lower bound of Eq.~(\ref{mi}) with the following theorem.

\begin{theorem}
    Let $\mathcal{M}$ denote a set of roles following the role distribution $P(M)$, and $|\mathcal{M}|\!=\!K$.
    $M\!\in\! \mathcal{M}$ is a given role.
    Let $e\!=\!f_{\phi}(\sum_t (o^t,a^{t-1}))$, $z\!\sim\! f_{\theta}(z|e)$, and $h(e,z)\!=\!\frac{p(z|e)}{p(z)}$, where $\sum_t(o^t,a^{t-1})$ is the agent's local trajectory following a given policy.
    For any role $M^*\!\in\!\mathcal{M}$, let $e^*$ denote the agent embedding generated by the role $M^*$, then we have
    \begin{equation}
        I(z; M) \ge \log K +  \mathbb{E}_{\mathcal{M},z,e}\left[\log\frac{h(e,z)}{\sum_{M^*\in\mathcal{M}}h(e^*,z)}\right].
        \label{mi_bound_main}
    \end{equation}
\end{theorem}

The proof of this theorem is given in Appendix~A.
Since we cannot evaluate $p(z)$ or $p(z|e)$ directly, we turn to techniques of NCE and importance sampling based on comparing the target value with randomly sampled negative values.
Hence, we approximate $h$ with the exponential of a score function $S(z, z^*)$ that is a similarity metric between latent codes of two examples.
We derive a sampling version of the tractable lower bound to be the role encoder's learning objective as
\begin{equation}
    \min_{\theta}\mathcal{L}_K \!= \!- \mathbb{E}_{M_i\in\mathcal{M}, (e,e')\sim M_i, z\sim f_{\theta}(z|e)} \!\!\left[ \log \frac{\exp (S(z,z'))}{\exp (S(z,z')) + \sum_{M^*\in\mathcal{M}\backslash M_i}\exp(S(z,z^*))} \right]\!\!,
    \label{nce_loss}
\end{equation}
where $\mathcal{M}$ is the set of training roles, $e,e'$ are two instances of agent embeddings sampled from the dataset of role $M_i$, and $z,z'$ are latent representations of $e,e'$. 
For any role $M^*\!\in\!\mathcal{M}\backslash M_i$, $z^*$ is the representation of agent embedding $e^*$ sampled by role $M^*$.
Following the literature, we denote $(e,e')_{M_i}$ as a positive pair and denote $\{(e,e^*)\}_{M^*\in\mathcal{M}\backslash M_i}$ as negative pairs.
The objective in Eq.~(\ref{nce_loss}) optimizes for a $K$-way classification loss to classify the positive pair out of all pairs.
Minimizing the InfoNCE loss $\mathcal{L}_K$ maximizes a lower bound on mutual information in Eq.~(\ref{mi_bound_main}), and this bound becomes tighter as $K$ becomes larger.
The role encoder ought to extract shared features in agent embeddings of the same role to maximize the score of positive pairs, while capturing essential distinctions across various roles to decrease the score of negative pairs.




\textbf{Negative Pairs Generation.}
Periodically, we partition all $n$ agents into $K$ clusters $\{C_j\}_{j=1}^K$ according to agent embeddings.\footnote{In this paper, we simply use K-means~\citep{hartigan1979algorithm} based on Euclidean distances between agent embeddings.
Moreover, it can be easily extended to more complex clustering methods such as Gaussian mixture models~\citep{bishop2006pattern}.
In Appendix~D, we conduct the hyperparameter analysis about the influence of different $K$ values and how to determine the number of clusters automatically.}
Naturally, we encourage role representations from the same cluster to stay close to each other, while differing from agents in other clusters.
For agent $i$, we denote its role representation $z_i$ as the query $q$, and role representations of other agents as the keys $\mathbb{K}=\{z_1,...,z_n\}\backslash z_i$.
Points from the same cluster as the query, $i\in C_j$, are set as positive keys $\{k_+\}$ and those from different clusters are set as negative $\{k_-\} = \mathbb{K}\backslash \{k_+\}$.
In practice, we use bilinear products~\citep{laskin2020curl} for the score function in Eq.~(\ref{nce_loss}), and similarities between the query and keys are computed as $q^\top W k$, where $W$ is a learnable parameter matrix.
The InfoNCE loss in Eq.~(\ref{nce_loss}) is rearranged as 
\begin{equation}
    \mathcal{L}_K \!=\!-\log \frac{\exp(q^\top W k_+)}{\exp(q^\top Wk_+)+\exp(q^\top Wk_-)} \!=\! -\log \frac{\sum\nolimits_{i'\in C_j}\exp(z_i^\top Wz_{i'})}{\sum\limits_{i'\in C_j}\!\!\!\exp(z_i^\top Wz_{i'})\!+\!\!\!\sum\limits_{i^*\notin C_j}\!\!\!\exp(z_i^\top Wz_{i^*})}.
\label{nce_loss2}
\end{equation}
Following the MoCo method~\citep{he2020momentum}, we maintain a query encoder $\theta_q$ and a key encoder $\theta_k$, and use a momentum update to facilitate the key representations' consistency as
\begin{equation}\label{soft_update}
    \theta_k \gets \beta \theta_k + (1-\beta) \theta_q,
\end{equation}
where $\beta \!\in\! [0,1)$ is a momentum coefficient, and only parameters $\theta_q$ are updated by backpropagation.





\subsection{Attention-Guided Role Coordination}\label{sec:attention}
After acquiring agents' contrastive role representations from their \textit{local} information, we introduce an attention mechanism in value decomposition to enhance agent coordination in the sophisticated role space with a \textit{global} view.
Popular CTDE algorithms, such as QMIX, realize behavior coordination across agents via a mixing network that estimates joint action-values as a monotonic combination of per-agent values, and the mixing network weights are conditioned on the system's global state.
Naturally, it is interesting to incorporate the learned role information into the mixing network to facilitate skillful coordination across roles.
The simplest approach is to concatenate the global state and role representations for generating mixing network weights, while it fails to exploit the internal structure to effectively extract correlations in the role space.
Fortunately, the attention mechanism~\citep{vaswani2017attention} aligns perfectly with our intention by prompting the global state to attend to learned role patterns, thus providing more expressive credit assignment in value decomposition.


The attention mechanism aims to draw global dependencies without regard to their distance in the input or output sequences, and has gained substantial popularity as a fundamental building block of compelling sequence modeling and transduction models, such as GPT~\citep{brown2020language}, vision transformers~\citep{dosovitskiy2021image}, and decision transformers~\citep{chen2021decision}.
An attention function can be described as mapping a query and a set of key-value pairs to a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query and corresponding key.
As role representations are learned based on extracting agent behaviors from history trajectories, we also use a GRU to encode the history states $(\bm{s}^0, \bm{s}^1,..., \bm{s}^t)$ into a state embedding $\bm{\tau}^t$ for facilitating information matching between states and role representations.
Then, we set the state embedding $\bm{\tau} \in \mathbb{R}^{d_s\times d}$ as the query, and the role representations $\bm{z}=[z_1,...,z_n]^\top \in \mathbb{R}^{n\times d}$ as both the key and value, where $d$ is the dimension of role representation and $d_s$ is the length of state embedding. 
Formally, we calculate a weighted combination of role representations as
\begin{equation}\label{att_i}
    \bm{\tau}_{\text{atten}}=\sum\nolimits_{i=1}^n \alpha_i v_i=\sum\nolimits_{i=1}^n \alpha_i \cdot z_i W^V,
\end{equation}
where the value $v_i$ is a linear transformation of $z_i$ by a shared parameter matrix $W^V\in \mathbb{R}^{d\times d_v}$.
The attention weight $\alpha_i$ computes the relevance between the state embedding $\bm{\tau}$ and the $i$-th agent's role representation $z_i$, and we apply a softmax function to obtain the weight as
\begin{equation}\label{af}
    \alpha_i=\frac{\exp\left(\frac{1}{\sqrt{d_k}} \cdot \bm{\tau} W^Q \cdot \left(z_i W^K\right)^\top\right)}{\sum_{j=1}^{n}\exp\left(\frac{1}{\sqrt{d_k}} \cdot \bm{\tau} W^Q \cdot \left(z_j W^K\right)^\top\right)},
\end{equation}
where $W^Q, W^K \!\in\! \mathbb{R}^{d\times d_k}$ are shared parameter matrices for linear transformation of query-key pairs, and $1/\sqrt{d_k}$ is a factor that scales the dot-product attention. 
We use multi-head attention (MHA) for allowing the model to jointly attend to information from different representation subspaces at different positions, and obtain the aggregated output as
\begin{equation}\label{att_all}
\bm{\tau}_{\text{mha}}=\text{Concat}\left(\bm{\tau}_{\text{atten}}^1,...,\bm{\tau}_{\text{atten}}^H \right)W^O,
\end{equation}
where $\bm{\tau}_{\text{atten}}^h~(h\in\{1,2,...,H\})$ is the attention output using projections of $W^Q_h, W^K_h$, and $W^V_h$, and $W^O\in \mathbb{R}^{H\cdot d_v\times d}$ is the parameter matrix for combining outputs of all heads.
Finally, the MHA output is combined with the global state to be responsible for generating weights of the mixing network, as shown in Fig.~\ref{Fig1}(d).
In this way, we flexibly leverage role representations to offer more comprehensive information for value decomposition.
By allowing the global state to attend to the learned role patterns, the attention mechanism implicitly guides the agent coordination in a skillful role space, thus yielding more expressive credit assignment with the emergence of roles.



\section{Experiments}
We evaluate ACORM to answer the following questions: 
(i) Can ACORM facilitate learning efficiency and stability in complex multi-agent domains? If so, what are the respective contributions of different modules to the performance gains? (See Sec.~\ref{sec:performanceNablation}). 
(ii) Can ACORM learn meaningful role representations associated with agent's behavior patterns and achieve effective dynamic team composition? (See Sec.~\ref{sec:visualization}).
(iii) Can ACORM successfully attend to learned role representations to realize skillful role coordination and more expressive credit assignment? (See Sec.~\ref{sec:visual_atten}).


\textbf{Implementations.} 
We choose SMAC~\citep{samvelyan2019starcraft} as the first testbed for its rich maps and convenient visualization tools, and realize ACORM on top of the popular QMIX algorithm.
For visualization, we render game scenes, and show agent embeddings and role representations using t-SNE.
\textcolor{black}{Appendix~C gives evaluation results on the GRF benchmark, and  Appendix D shows the algorithm architecture, experimental settings and results of MAPPO-based ACORM.}



\textbf{Baselines.} 
We compare ACORM to \texttt{QMIX} and six baselines: 1) \texttt{RODE}~\citep{wang2021rode} with action space decomposition; 2) \texttt{EOI}~\citep{jiang2021emergence} that encourages diversified individuality via training an observation-to-identity classifier; 3) \texttt{MACC}~\citep{yuan2022multi} that uses attention to concentrate on most related subtasks; 4) \texttt{CDS}~\citep{li2021celebrating} that introduces diversity in both optimization and representation; 5) \texttt{CIA}~\citep{liu2023contrastive} that boosts credit-level distinguishability via contrastive learning; and 6) \texttt{GoMARL}~\citep{zang2023automatic} with an automatic grouping mechanism.





\subsection{Performance and Ablation Study}\label{sec:performanceNablation}
For evaluation, all experiments are carried out with five different random seeds, and the mean of the test win rate is plotted as the bold line with 95\% bootstrapped confidence intervals of the mean (shaded).
Appendix~B describes the detailed setting of hyperparameters.

\textbf{Performance.} 
SMAC contains three kinds of maps: \textit{easy}, \textit{hard}, and \textit{super hard}.
Super hard maps are typically complex tasks that require deeper exploration of diversified behaviors and more skillful coordination.
Since ACORM is designed to promote these properties, the performance on these maps is especially significant to validate our research motivation and advantages.
\textcolor{black}{Fig.~\ref{performance_fig} presents the performance of ACORM on six representative tasks, and performance on more maps can be found in Appendix~B.}
ACORM obtains the best performance on all super-hard maps and most of the other maps. 
A noteworthy point is that ACORM outperforms all baselines by the largest margin on super hard maps that demand a significantly higher degree of behavior diversity and coordination: \texttt{MMM2}, \texttt{3s5z\_vs\_3s6z}, and \texttt{corridor}.
In these maps, ACORM gains an evidently faster-increasing trend regarding the test win rate in the first million training steps, which is supposed to benefit from the high efficiency of exploring cooperatively heterogeneous behaviors via our discriminative role assignment.
Moreover, ACORM exhibits the lowest variance in learning curves, signifying not only superior learning efficiency but also enhanced training stability.


\begin{figure}[t]
\begin{center}
\includegraphics[width=0.98\textwidth]{results_smac_main.jpg}
\end{center}
\caption{\textcolor{black}{Performance comparison between ACORM and baselines on six representative maps.}}
\label{performance_fig}
\end{figure}

\begin{figure}[h]
\begin{center}
\includegraphics[wid

[... truncated for index ...]

