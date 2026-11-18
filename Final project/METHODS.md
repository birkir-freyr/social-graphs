# Semester methods reference — DTU 02805

Practical reference for planning the final project, based on **Weeks 1–7** of Social Graphs and Interactions, Fall 2026. Reviewed 18 November 2026.

This guide combines the weekly exercise answers and notebooks in the local course folder with the analyses in this repository. It covers the methods in those materials, including exercises that were not used for the group website. No later weekly folders were available in the reviewed material. Methods discussed as possible stronger checks are identified as such; their inclusion does not mean we carried them out.

Use this file as shared context when working with a coding assistant: point it to the relevant sections and define the project question, dataset and intended claim before requesting an analysis.

## Contents

- [Choose methods by question](#choose-methods-by-question)
- [Week 1 — Representing and describing networks](#week-1--representing-and-describing-networks)
- [Week 2 — Models, clustering and null comparisons](#week-2--models-clustering-and-null-comparisons)
- [Week 3 — Paths, centrality, robustness and mixing](#week-3--paths-centrality-robustness-and-mixing)
- [Week 4 — Communities, weights and backbones](#week-4--communities-weights-and-backbones)
- [Week 5 — Turning language into data](#week-5--turning-language-into-data)
- [Week 6 — Similarity, topics and word embeddings](#week-6--similarity-topics-and-word-embeddings)
- [Week 7 — Contextual models, validation and retrieval](#week-7--contextual-models-validation-and-retrieval)
- [A workflow for the final project](#a-workflow-for-the-final-project)
- [Reusable code and source material](#reusable-code-and-source-material)

## Choose methods by question

| Project question | Start with | Comparison or validation |
|---|---|---|
| What does this network look like? | Degree, density, components, isolates, degree distributions | Audit node/edge definitions and missing observations |
| Is it unusually clustered or a small world? | Local clustering, transitivity, shortest paths | Ensembles of size-matched and degree-preserving nulls |
| Which nodes are important? | Degree, closeness/harmonic, betweenness, PageRank | Match the importance definition to the question; compare with degree-controlled expectations |
| Which nodes keep it connected? | Articulation points and node-removal experiments | Random deletion orders; static versus adaptive targeting |
| Do similar nodes connect? | Degree/attribute assortativity, neighbor-degree plots | Degree-preserving rewiring or attribute-label permutations |
| Are there groups in the links? | Louvain, greedy modularity, Girvan–Newman or Infomap | Seed stability, null graphs, NMI/ARI and external labels |
| Can a node belong to several groups? | Clique percolation or link communities | Parameter sensitivity and unassigned-node coverage |
| How can a dense weighted graph be drawn? | Global threshold or disparity backbone | Retained edges/nodes/components across thresholds |
| Which words or phrases characterize texts? | Frequencies, concordances, n-grams, collocations | Length normalization, raw passages and preprocessing sensitivity |
| Which documents are similar? | TF-IDF/cosine and dense document embeddings | Read matched passages; inspect names, boilerplate and page scope |
| Which themes recur? | LDA or BERTopic | Representative documents, seeds, topic/cluster settings and outliers |
| How is a word used? | Concordance, PPMI, Word2Vec/GloVe | Context windows, corpus choice and polysemy checks |
| Can text produce a network? | NER → entity resolution → co-occurrence edges | Annotated spans, alias audit and sentence/paragraph sensitivity |
| What sentiment does text express? | Lexicon, TF-IDF/logistic regression, contextual classifier | Held-out labels, in-domain examples, controlled sentences and truncation audit |
| Can we search the collection? | Sparse TF-IDF and dense passage retrieval | Queries fixed before inspection, relevance judgments and evidence passages |

## Week 1 — Representing and describing networks

### 1. Define the graph before measuring it

Specify the node unit, edge rule, direction, weights, time interval and population boundary. An edge can mean a hyperlink, collaboration, repeated interaction or co-occurrence; each supports different interpretations. A historical aggregate can connect people who were never active at the same time, so questions about actual spreading may require time information.

- **Directed:** $A\to B$ need not imply $B\to A$. Preserve the arrows if reachability or incoming visibility matters.
- **Undirected:** the relation is symmetric, or a documented projection treats either arrow as one pair.
- **Weighted:** state whether weight means frequency, strength, distance or cost. This determines how algorithms should use it.
- **Simple graph versus multigraph:** decide how repeated edges and self-loops are treated. For the philosopher data, repeated undirected pairs are aggregated by summing their weights.

Add the complete node roster before the edges. Otherwise, isolates disappear and change averages, distributions and coverage. Validate IDs, duplicate records, endpoints and self-loops against the chosen graph definition.

### 2. Edge lists and adjacency matrices

An edge list records source/target pairs, optionally with weights. For adjacency matrix $A$, using rows as sources, $A_{ij}=1$ means $i\to j$.

- Undirected matrices are symmetric; simple loop-free graphs have zero diagonal.
- Directed row sums give out-degree; column sums give in-degree.
- Weighted row/column sums give outgoing/incoming strength.
- Converting to undirected merges reciprocal arrows. For binary data, use an either-direction rule; do not count a reciprocal pair as two undirected edges.

**Use for:** loading data, checking representations and moving between graph algorithms and matrix calculations. A symmetrization rule for weights must be stated separately: sum and maximum answer different questions.

### 3. Basic summaries

For a simple, loop-free graph with $n$ nodes and $m$ edges:

| Quantity | Undirected | Directed |
|---|---|---|
| Degree total | $\sum_i k_i=2m$ | $\sum_i k_i^{in}=\sum_i k_i^{out}=m$ |
| Mean degree | $2m/n$ | Mean in-degree = mean out-degree = $m/n$ |
| Density | $2m/[n(n-1)]$ | $m/[n(n-1)]$ |

Count isolates, connected components and the largest component. In directed graphs distinguish **weak connectivity** (ignore arrows) from **strong connectivity** (mutual directed reachability). State whether a result uses the whole graph, the largest connected component or a strongly connected component.

**Interpretation:** Marvel in-degree measures incoming mentions within the frozen roster. Out-degree measures links authored on a page. Neither automatically measures general popularity.

### 4. Degree distributions and mixed binning

Compute $P(k)=\#\{i:k_i=k\}/n$; inspect incoming and outgoing distributions separately when their mechanisms differ. Compare ordinary and logarithmic axes.

The course's mixed-binning approach keeps narrow bins where observations are dense and widens tail bins. Divide each bin's count by both the total population and its width. Use a documented geometric position for logarithmic display, integer-aware boundaries and consistent endpoint inclusion.

Zero degrees cannot be plotted at zero on a log axis. Our Week 1 figure uses $u=k+1$ while retaining all nodes. Report that shift; it changes the appearance of the low-degree region. Check that bin counts sum to the roster size and bin densities integrate to one.

**Pitfall:** a smoother or straighter plot does not establish a power law. Do not estimate an exponent by fitting a line to arbitrarily shifted, binned points.

### 5. Layouts and small manual checks

Seeded force layouts make graph drawings repeatable. Node size can encode degree/strength and color can encode communities or attributes. Stable input ordering also matters for reproducibility.

Geometric distance in the drawing is not shortest-path distance. A layout cannot establish reachability or community validity. Check a few degrees, triangles, matrix entries and removal effects by hand before trusting a larger pipeline.

## Week 2 — Models, clustering and null comparisons

### 6. Erdős–Rényi models: $G(n,p)$ and $G(n,m)$

In undirected $G(n,p)$, each possible edge occurs independently with probability $p$:

$$
E[m]=p\binom n2,\qquad E[k]=(n-1)p,\qquad P(k=0)=(1-p)^{n-1}.
$$

Degree is exactly binomial and approximately Poisson in the sparse large-network regime. Expected local closure is governed by $p$; treatment of degree-zero/one nodes affects an all-node clustering average. $G(n,m)$ instead samples graphs with exactly the specified number of edges.

**Use for:** a baseline preserving size and density but discarding observed degree heterogeneity. Simulate several realizations and compare distributions, maximum degree, isolates, clustering and distances. Matching only average degree does not preserve hubs.

### 7. Giant-component transition and finite-size experiments

Sweep mean degree $c$ and track the largest-component fraction across repeated random graphs. In sparse ER networks, a macroscopic giant emerges above $c=1$ in the large-network limit; the transition is gradual in finite samples. A giant component does not mean the entire graph is connected.

For $c>1$, the giant-fraction relation $S=1-e^{-cS}$ and the rough distance scaling $\ln n/\ln c$ provide model intuition, with care near criticality. State what stays fixed when changing $n$, $p$ or $c$.

### 8. Local clustering, mean clustering and transitivity

If node $i$ has $k_i$ neighbors and $e_i$ edges among those neighbors:

$$
C_i=\frac{2e_i}{k_i(k_i-1)},\qquad C=\frac1n\sum_i C_i.
$$

Our convention sets $C_i=0$ for $k_i<2$ and includes those zeros in the mean.

$$
T=\frac{3\times\text{triangles}}{\sum_i\binom{k_i}{2}}
 =\frac{\sum_i\binom{k_i}{2}C_i}{\sum_i\binom{k_i}{2}}.
$$

Transitivity weights high-degree neighborhoods more heavily. Mean clustering gives every node equal weight. Their difference is informative when hubs have different closure from low-degree nodes.

**Pitfall:** numerator edges connect neighbors to one another; edges from the focal node to its neighbors do not belong in that numerator.

### 9. Watts–Strogatz and the small-world comparison

Start from a ring lattice and rewire edges with probability $q$. Compare clustering $C(q)$ and average shortest-path length $L(q)$, often normalized by their $q=0$ values, over repeated realizations.

A small-world regime combines paths comparable to a random reference with substantially greater clustering. A few rewired connections can shorten paths while most local triangles remain. The exercise uses $C(q)\approx C(0)(1-q)^3$ as an approximate intuition.

Check connectivity before computing a full-network path mean; report disconnected cases rather than silently switching to their giant components. Label error bars as SD, SE or confidence intervals. Fully rewired WS is not exactly ER: its construction retains degree constraints.

### 10. Growth and preferential attachment

The Barabási–Albert mechanism adds nodes over time and favors existing nodes in proportion to degree:

$$
\Pr(\text{choose }i)=\frac{k_i}{\sum_j k_j}.
$$

An endpoint-list sampler implements this by listing a node once per incident edge and sampling the list. Specify the seed graph, links per new node and whether multiple targets are chosen with replacement. The exercise also compares **uniform attachment with growth** and a size-matched static random graph to separate the ingredients.

**Use for:** testing whether a proposed growth mechanism can reproduce broad degree patterns. Check sampling probabilities empirically and compare with a reference implementation. Similar degree plots do not establish that preferential attachment generated the observed data.

### 11. CCDFs and assessing power-law claims

The empirical complementary cumulative distribution is

$$
\widehat F(k)=\frac{\#\{i:k_i\ge k\}}n.
$$

It avoids histogram-bin choices, although adjacent cumulative points are correlated. For a power-law tail $P(k)\propto k^{-\gamma}$, the asymptotic CCDF slope is $1-\gamma$, not $-\gamma$.

The exercise's stronger testing plan is to fit a **discrete** tail above an estimated cutoff, report exponent/cutoff/tail count/uncertainty, assess goodness of fit with calibrated simulations and compare alternatives on the same support. Repeat cutoff selection in simulated fits and account for the empirical body when needed. Lognormal, exponential and cutoff-power-law alternatives can remain hard to distinguish in small samples.

**Coverage:** we plotted and critiqued the empirical tail; the repo does not claim a completed formal power-law fit. A broad observed tail neither proves an exact asymptotic law nor identifies a generating mechanism.

### 12. Choose a null that preserves the relevant constraints

| Null | Preserved | What it helps ask |
|---|---|---|
| $G(n,m)$ | Node count and edge count | Is the pattern beyond size/density alone? |
| Stub-pairing configuration multigraph | Degree sequence, counting loops/multiplicity | What follows from degrees in a multigraph ensemble? |
| Simple-graph degree-preserving swaps | Each labeled node's degree | Is organization unusual after controlling for hubs? |
| Directed degree-preserving swaps | Each node's in-degree and out-degree | Is reciprocity or directed organization beyond those degrees? |
| Attribute-label permutations | Fixed graph and label frequencies | Are attributes associated with network position or connections? |

Converting a configuration multigraph to a simple graph and deleting loops generally changes its degrees. Audit that loss. It is not an exact-degree simple-graph null.

For swaps, start independent runs from the observed graph, record successful swaps/seeds and verify every preserved degree. The exercises use $10m$ successful swaps as a practical rule and inspect additional swaps for sensitivity. This is not a proof of mixing or uniform sampling. Connectivity is unconstrained unless explicitly imposed.

### 13. Null distributions, z-scores and empirical tests

Measure the same statistic on the observed graph and every null graph, using identical scope and conventions. Report the null mean, sample SD and the observed value.

$$
z=\frac{T_{obs}-\overline T_{null}}{s_{null}},\qquad
p_+=\frac{1+\#\{b:T_b\ge T_{obs}\}}{B+1}.
$$

Choose the alternative before seeing results. Our equal-tail two-sided test uses $\min(1,2\min(p_+,p_-))$. With 100 simulations, the smallest corrected one-sided value is $1/101$; this two-sided convention has minimum $2/101$. Zero null SD makes a z-score undefined.

Statistics fixed by construction cannot be tested meaningfully against that null: exact degrees already fix the isolate count. Large z-scores describe extremeness under the chosen simulated model; they are not causal proof. Many nodewise comparisons also require care with selecting and presenting only extreme results.

### 14. Reciprocity and the friendship paradox

**Reciprocity:** the fraction of directed edges whose reverse also exists. A reciprocal pair contributes two reciprocated edges. Compare against directed in/out-degree-preserving nulls when testing excess mutual linking.

**Friendship paradox under uniform edge-endpoint sampling:** a sampled endpoint has probability proportional to degree, giving

$$
E[k_{endpoint}]=\frac{\langle k^2\rangle}{\langle k\rangle}
=\langle k\rangle+\frac{\operatorname{Var}(k)}{\langle k\rangle}.
$$

**Person-first sampling**, used in our Week 2 post, selects a nonisolated person uniformly and then a neighbor uniformly:

$$
E[k_{friend}]=\frac1{n_+}\sum_{i:k_i>0}\frac1{k_i}\sum_{j\in N(i)}k_j.
$$

These are different experiments. Degree-preserving shuffles fix the endpoint expectation, but can change the person-first expectation. The paradox concerns an average; it does not say every person has fewer friends than their friends. State the isolate denominator and whether ties count when reporting the fraction of sampled friends at least as connected as the sampled person.

## Week 3 — Paths, centrality, robustness and mixing

### 15. BFS and distance summaries

A walk may repeat vertices; a path does not. Breadth-first search explores successive distance rings and finds shortest paths in an unweighted graph. It runs in $O(n+m)$ from one source. Repeat over sources for all-pairs distances and compare a hand-written implementation against a library on small cases.

- **Average path length:** average pair distance on a stated population of pairs.
- **Eccentricity:** a node's greatest distance to another node in a connected graph.
- **Diameter:** greatest eccentricity; **radius:** smallest eccentricity.
- **Center:** nodes achieving the radius.

Follow arrows in directed graphs. Report unreachable-pair fractions and whether the mean uses reachable ordered pairs, an SCC or another explicitly chosen scope. For weighted graphs, BFS no longer solves the general shortest-path problem; use appropriate distance weights and a weighted path algorithm, such as Dijkstra for nonnegative lengths.

### 16. Choose centrality by the meaning of importance

| Measure | Definition/idea | Appropriate interpretation and caveat |
|---|---|---|
| Degree | $k_i$, often divided by $n-1$ | Immediate connections; incoming and outgoing links have different meanings |
| Closeness | $(n-1)/\sum_{j\ne i}d(i,j)$ on a connected undirected graph | Short average distance; disconnected/directed conventions must be stated |
| Harmonic | $\sum_{j\ne i}1/d(i,j)$, with $1/\infty=0$ | Distance-based reach that accommodates unreachable nodes; normalization varies |
| Betweenness | $\sum_{s<t;\,s,t\ne i}\sigma_{st}(i)/\sigma_{st}$ in an undirected graph | Brokerage along shortest paths; split credit across tied paths and state normalization |
| Eigenvector | Importance proportional to importance of neighbors | Recursive prestige; direction, connectivity and convergence affect the result |
| PageRank | Random-surfer stationary score with teleportation | Incoming prestige with each source's vote divided across its outgoing links |

There is no universally best centrality. Shortest-path centralities describe a modeled route system; hyperlinks do not establish actual information flow. Compare rankings, inspect high-betweenness/low-degree cases and evaluate node scores against degree-preserving shuffles to ask what is unusual beyond degree.

For directed closeness/harmonic measures, explicitly choose distances **to** or **from** a node; library orientation conventions matter.

### 17. PageRank iteration and random walks

For uniform teleportation and dangling redistribution:

$$
PR_i^{(t+1)}=\frac{1-\alpha}{n}
+\alpha\left(\sum_{j\to i}\frac{PR_j^{(t)}}{k_j^{out}}
+\frac{\sum_{j:k_j^{out}=0}PR_j^{(t)}}n\right).
$$

Update all entries from the previous vector simultaneously. Teleportation avoids trapping the surfer in a closed subset; dangling mass is redistributed rather than discarded. Check convergence, score sum and agreement with a reference implementation across damping settings.

For an ordinary random walk on a connected undirected graph, stationary mass is $k_i/(2m)$. Convergence can require addressing periodicity. Uniform-teleportation PageRank is not generally equal to that degree formula.

### 18. Articulation points and removal experiments

An articulation point is a node whose deletion increases the component count. Compare individual removal effects with degree and betweenness; a high centrality need not imply a large immediate disconnection.

For repeated removals, track the largest connected component against the number/fraction deleted:

1. Remove high-degree nodes or high-betweenness nodes.
2. State whether scores are fixed initially or **recomputed after every removal**.
3. Compare with many random deletion orders on the same starting graph.
4. Plot random medians/quantiles and report a defined fragmentation threshold.

Our Week 3 post uses the undirected 277-node giant component, adaptive attacks and 500 random orders. Keep the original component size as a denominator when comparing curves so that deletion and fragmentation remain interpretable. Pointwise random quantiles describe variation across simulated orders; they are not automatically simultaneous confidence bands.

### 19. Assortativity, neighbor degree and homophily

Degree assortativity is the Pearson correlation of endpoint degrees across edges. Positive values indicate similar-degree endpoints; negative values indicate hub–low-degree mixing. Plot average neighbor degree $k_{nn}(k)$ to see patterns hidden by one coefficient. Regular graphs can give an undefined correlation because degree variance is zero.

Compare with degree-preserving nulls: a raw negative coefficient may largely follow from the degree sequence and simple-graph constraints. Directed graphs have distinct source/target in/out-degree pairings; name the pairing.

Attribute assortativity measures categorical mixing. Test it by permuting labels while holding graph structure fixed when that matches the hypothesis. Audit how labels were assigned, missing categories and multivalued attributes. Association in observed links does not identify a causal preference mechanism.

### 20. Cliques

A $k$-clique contains every one of the $k(k-1)/2$ possible undirected edges. A **maximal** clique cannot be enlarged; a **maximum** clique is a largest clique in the graph. Members of a $k$-clique must each have degree at least $k-1$.

**Use for:** tightly interconnected subgroups and the input to clique percolation. Complete connectivity is a stricter condition than community structure, and exhaustive clique enumeration can be expensive.

## Week 4 — Communities, weights and backbones

### 21. Girvan–Newman and dendrograms

Compute edge betweenness, remove the highest-scoring edge, **recompute** and repeat. Successive splits produce a dendrogram of candidate partitions. Choose and report the cut rule, for example the level with greatest modularity measured on the original graph.

**Use for:** understanding bottlenecks and hierarchical splitting in manageable graphs. Scores change after deletion; sorting the initial scores once does not implement the algorithm. Repeated betweenness calculations are costly on large networks.

### 22. Modularity

For an undirected graph and a partition into communities $c$:

$$
Q=\frac1{2m}\sum_{ij}\left(A_{ij}-\frac{k_i k_j}{2m}\right)\mathbf1[c_i=c_j]
=\sum_c\left[\frac{l_c}{m}-\left(\frac{K_c}{2m}\right)^2\right].
$$

Here $l_c$ counts internal edges once and $K_c$ sums members' **full-graph** degrees. The baseline discounts internal connections expected from degree alone. One community gives $Q=0$ at the standard resolution parameter; some partitions have negative $Q$.

**Use for:** evaluating a stated partition and optimizing structural grouping. Positive or high $Q$ alone is insufficient: optimization also finds apparent structure in random graphs. Report graph scope, weights and resolution; small groups can be merged at the chosen modularity resolution.

### 23. Greedy modularity and Louvain

- **Greedy merging:** begin with singleton groups and merge communities to improve modularity. Early merges constrain later possibilities.
- **Louvain:** move individual nodes to improve modularity, then aggregate communities into weighted super-nodes and repeat.

Run several seeds and report both quality and membership stability. Similar $Q$ can hide different assignments. Compare with the **same optimization procedure applied to many null graphs**. A null comparison of optimized $Q$ should not be replaced by the score of one arbitrary null partition.

Inspect representative/high-degree members before assigning human group names. Compare external labels such as era where available, with care for missing or multivalued metadata.

### 24. NMI, ARI and stability

Normalized mutual information (NMI) compares information shared by two partitions; identical partitions up to label renaming score 1. Adjusted Rand index (ARI) compares pair assignments and adjusts for chance; identical partitions score 1, chance-like agreement is around 0 and values may be negative.

Use these to compare seeds, algorithms, preprocessing variants and external labels on the **same roster**. Include membership/contingency tables when explaining disagreements. Arbitrary cluster IDs must not be interpreted as persistent identities. State the convention when treating outliers as one label or reducing LDA mixtures to their argmax. Agreement measures are not standalone measures of substantive topic quality.

### 25. Overlapping groups: clique percolation and link communities

**Clique percolation:** find $k$-cliques and join cliques sharing $k-1$ nodes. The connected sets of cliques define communities. For triangles, adjacency requires a shared edge, not just one node. A node can belong to multiple communities or none. Vary $k$ and report coverage; small $k$ can produce one sprawling group, while large $k$ excludes most nodes.

**Link communities:** cluster edges using similarity of adjacent links' neighborhood contexts. Nodes inherit the groups of their incident edges and can overlap. A hierarchy can be cut using a criterion such as partition density. This was discussed in the exercises; the implemented alternative community method was Infomap.

The **overlap paradox** explains why a person connecting several contexts can have low local neighborhood density: their different groups do not necessarily connect to one another.

### 26. Infomap

Infomap seeks a partition that compresses a random walk's trajectory using the map equation. It groups regions where flow tends to remain, using a different objective from modularity.

**Use for:** checking whether flow-based groups agree with link-density-based groups. Report directed/undirected, weighted/unweighted, seed and hierarchical/two-level settings. Compare memberships with Louvain and read plausible disagreements. Codelength and modularity are different objectives and cannot be compared numerically as one quality scale.

### 27. Strength and weighted paths/modularity

Node strength is $s_i=\sum_j w_{ij}$. Compare strength and degree, using scatterplots and a rank correlation such as Spearman's, to find nodes with many weak links or fewer strong ones.

If a positive weight encodes tie strength, the exercises use length $\ell_{ij}=1/w_{ij}$ for shortest paths. If it already encodes distance or cost, use that meaning directly. State the transformation and treatment of zero/missing weights.

Weighted modularity replaces degrees with strengths and edge counts with total weight:

$$
Q_w=\sum_c\left[\frac{W_c}{W}-\left(\frac{S_c}{2W}\right)^2\right].
$$

Here $W$ is total undirected edge weight, $W_c$ internal weight and $S_c$ summed strengths. Weighted and unweighted analyses answer different questions; a larger raw $Q$ in one does not establish a better model.

### 28. Global thresholds and the disparity filter

A **global threshold** keeps edges with $w\ge t$. It is simple but can erase a small node's strongest relationship because its absolute weight is modest.

The **disparity filter** evaluates an edge relative to each endpoint's strength. At endpoint $i$, for $k_i>1$:

$$
p_{ij}=w_{ij}/s_i,\qquad a_{ij}=(1-p_{ij})^{k_i-1}.
$$

Our OR rule retains an undirected edge if either endpoint's significance is **strictly less** than threshold $\alpha$. Smaller $\alpha$ is more selective. Our degree-one convention gives endpoint significance 1, so that endpoint does not automatically preserve the edge; document this because conventions differ.

Compare retained edges, linked nodes, isolates and largest-component size across $\alpha$ and against comparable global thresholds. Keep the node roster even after filtering. Backbone significance is a local weight-allocation criterion, not proof that an edge is an objectively true relationship.

### 29. Exact threshold sweeps and network figures

The repo's Week 4 extension sorts edge significance values and processes **equal-score batches together**. Union-find joins components as edges are added, allowing every largest-component event to be located without repeatedly traversing the graph. Reverse this process to interpret tightening the filter. At equality an edge is absent under the strict inequality rule.

For a defensible drawing:

1. Select and report a backbone if filtering is needed.
2. Compute the layout from the backbone.
3. Show meaningful communities detected on the full analysis graph, stating its scope.
4. Size nodes using a justified measure.
5. Label important nodes and disclose how much was removed.

Filtering can make groups appear sharply separated while isolating most of the original population. Counts belong beside the visual story.

### 30. Literature-search validation

The OpenAlex exercise compares broad search hits, focused queries, title samples and citation counts. Save the exact query/date, inspect a reproducible sample for relevance and distinguish “papers using a method” from “papers citing a foundational article.” A binomial interval such as Wilson's describes uncertainty from the relevance sample, not missing database coverage or annotation ambiguity.

**Use for:** a carefully bounded literature overview. The historical counts in the exercise should not be presented as current counts without a new query.

## Week 5 — Turning language into data

### 31. Tokenization, vocabulary and preprocessing

Distinguish raw characters, token pieces, token IDs and model input. A **token** is an occurrence; a **type** is a distinct form; a vocabulary is the retained set of types. Declare the document unit before constructing counts.

Compare hand rules, regex tokens, spaCy word tokens and subword tokens. BPE repeatedly merges frequent adjacent pieces when learning its vocabulary; a word can subsequently be represented by several known pieces. Model input limits count model tokens/wordpieces, not necessarily words.

Preprocessing changes the measurement:

- Lowercasing merges case distinctions, including names and ordinary words.
- Punctuation/hyphen rules change `Spider-Man`, `X-Men` and acronyms.
- Stopwords can include useful negation or names such as `May`.
- Lemmatization can merge `fight` and `fights`, but loses their surface distinction.
- Number filtering can remove dates, issue numbers or other useful evidence.

Audit concrete raw-text examples and change one choice at a time when attributing an effect. Token boundaries and named-entity boundaries need not coincide.

### 32. Frequencies, relative frequencies, hapax and Heaps' law

Count tokens and types, rank types by count and normalize by a declared token total when comparing differently sized texts. A **hapax** type occurs once. Stopword filtering changes both vocabulary and the denominator of relative frequency.

A **Heaps curve** plots vocabulary size $V(T)$ against cumulative token count $T$; the descriptive relation $V(T)\approx KT^\beta$ summarizes sublinear vocabulary growth. Record document order because it changes the observed accumulation curve. Inspect whether new names and compounds continue expanding vocabulary.

**Use for:** corpus characterization, data-size planning and auditing tokenizer coverage. The guide does not claim that a formal Heaps exponent was fitted in the exercises.

### 33. Zipf plots

Plot frequency versus rank on ordinary and log–log axes. A Zipf-like relation is $f(r)\propto r^{-s}$. Compare full articles with templated descriptions, documenting the fitting/display range and preprocessing.

The exercise's fitted slope and $R^2$ are descriptive. An approximately linear segment does not prove an exact inverse-rank law. Changes in size and text composition are confounded when comparing full pages with descriptions.

### 34. Concordance and similar contexts

A **concordance/KWIC** shows windows around each occurrence of a chosen token. Use it to separate senses, names, quotations and editorial boilerplate. A **similar-context** search returns other tokens appearing in comparable surrounding frames.

Shared context is not synonymy: `power` and `character` can both occur in `his ___ and`. Retain raw text and offsets so a count or interpretation can be checked. Regex matches and tokenizer matches may disagree, for example when a regex matches `power` inside `power-hungry`.

### 35. N-grams and collocations

Unigrams count individual tokens; bigrams/trigrams count adjacent ordered pairs/triples. Do not create n-grams across document boundaries, and state whether sentence boundaries are respected.

Raw counts favor common phrases. An association score such as likelihood ratio compares a pair's observed co-occurrence with what its marginals predict. Inspect enough occurrences to avoid interpreting a rare or templated phrase as a general theme.

**Use for:** repeated phrases and local word order. Bigrams distinguish `Thor defeats` from `Loki defeats`; unordered unigram counts cannot recover who defeated whom.

### 36. Bag of Words and sparse document-term matrices

Construct $X_{dt}$ with documents as rows, vocabulary terms as columns and occurrence counts as cells. Row sums are lengths under that tokenizer; column sums are corpus term counts. Sparsity is $1-\mathrm{nnz}(X)/(N\times V)$.

Use a sparse representation because most documents contain only a fraction of the vocabulary. Check a small hand-built matrix before fitting the full corpus. In our exercises, default `CountVectorizer` lowercases, retains word tokens of at least two characters and splits hyphens; it does not automatically reproduce custom rules preserving `x-men`.

**Use for:** prevalence, lexical comparison, topic-model inputs and supervised features. Bag of Words discards order, negation scope and context-dependent meaning.

### 37. Longest shared token sequences and a text-reuse network

Our Week 5 post tokenizes pages, indexes shared 8-token seeds, extends matches to maximal contiguous runs and retains the longest run for each pair. Source offsets recover both raw passages. This is contiguous matching, not the noncontiguous longest-common-subsequence problem.

Connect pages when their longest run has at least $t$ tokens and sweep $t$ to inspect edge counts, active pages and components. The saved index supports thresholds of at least 8; it cannot recover all matches below its seed length.

**Use for:** exact repeated phrasing, quotations and near-duplicate passages. Shared text may be a plot summary, bibliography or common quotation. It does not establish copying direction or plagiarism.

## Week 6 — Similarity, topics and word embeddings

### 38. TF, DF, IDF and TF-IDF

For the course definition:

$$
TF_{dt}=\frac{X_{dt}}{\sum_u X_{du}},\qquad
DF_t=\#\{d:X_{dt}>0\},\qquad
IDF_t=\ln\frac N{DF_t},\qquad
W_{dt}=TF_{dt}IDF_t.
$$

A term in every document gets zero IDF. Common terms are discounted and distinctive terms gain weight. Use only vocabulary terms with positive DF and define how empty documents are handled.

**Implementation trap:** the exercise distinguishes this from scikit-learn's smoothed IDF with an added 1. Disabling smoothing still leaves an added 1 in its IDF formula. Our repo builds the course weights explicitly. Raw versus relative TF only rescales a whole document and therefore leaves its cosine unchanged; changing the IDF formula changes direction and can change rankings.

### 39. Cosine, nearest neighbors and contribution audits

$$
\cos(a,b)=\frac{a\cdot b}{\|a\|\|b\|}.
$$

Positive rescaling leaves cosine unchanged. For L2-normalized vectors it equals their dot product. Zero vectors have undefined mathematical cosine; flag them and state any software convention.

Rank nearest documents, exclude self-matches and define deterministic tie-breaking. For normalized TF-IDF vectors, each term contributes $a_t b_t$ to pair cosine; list the largest contributors and inspect both source passages.

**Use for:** transparent document similarity. Names can dominate rare-word overlap: Storm matches Human Torch partly through his surname. Umbrella pages and particular incarnations can also look similar without being interchangeable entities.

### 40. Capitalization-based name filtering and sensitivity

The course heuristic flags alphabetic forms capitalized in more than half of their occurrences. Rebuild the vocabulary/weights without those forms and compare top neighbors, neighbor overlap and term contributions.

This is a type-level proxy, not NER. It can remove ordinary sentence-initial words and miss names. The repo's Week 6 experiment compares the same five-neighbor task before and after filtering, preserving removed-term counts and raw evidence. An improvement in one example does not imply that every removed feature was unwanted information.

### 41. Comparing two corpora or network communities

Plot each term's normalized frequency in corpus A against its rate in corpus B, as in Scattertext. Diagonal terms are common at similar rates; off-diagonal terms are comparatively characteristic. Log axes and log rate ratios make a broad frequency range visible.

Specify denominators, minimum support and smoothing for zero rates. Display offsets used to show zeros on log axes are separate from smoothing used in a score. Inspect whether one long page or repeated name explains a supposed community marker. Compare results under a changed support cutoff and use top-list overlap, such as Jaccard similarity, to summarize sensitivity.

### 42. LDA topic modeling

Latent Dirichlet Allocation models documents as mixtures over topics and topics as distributions over words. Fit it to **counts**, as in the exercises, and retain both document-topic mixtures and topic-word weights.

Choose and record topic count, vocabulary filters, priors/model settings, iterations and seed. Inspect leading words, several high-weight pages and actual passages before naming a topic. A topic can reflect media/adaptation boilerplate rather than an in-universe theme; leaving an incoherent topic unnamed is valid.

Repeat seeds and topic counts. Align topics by their word distributions before comparing them because topic IDs are arbitrary. Compare community-average mixtures, stating whether pages or tokens receive equal weight. A document's 0.70 topic weight is a model mixture value, not a definitive labeling of exactly 70% of its meaning. An argmax discards the remaining mixture.

**Use for:** interpretable recurring lexical patterns and mixed membership. The exercises also use 20 Newsgroups as a contrasting corpus to inspect recognizable topics and preprocessing artifacts.

### 43. Word-context matrices, PMI and PPMI

Count target-context events inside a specified window. Rows are **words**, not documents; columns are context words. Define direction, window width, sentence boundaries and minimum counts.

$$
PMI(w,c)=\ln\frac{P(w,c)}{P(w)P(c)},\qquad PPMI(w,c)=\max(0,PMI(w,c)).
$$

Derive joint and marginal probabilities from the same event table. PPMI emphasizes pairs occurring more often than independence predicts, clipping negative evidence to zero. Common contexts no longer dominate merely because of raw frequency; rare pairs can still receive inflated scores, so support thresholds matter.

Compare word rows with cosine. Similarity of whole context profiles is different from the two target words occurring beside one another. Keep original token positions when filtering vocabulary so that distant words are not accidentally pulled into the window.

### 44. Word2Vec: Skip-gram, CBOW and negative sampling

- **Skip-gram:** predict neighboring context words from a center word.
- **CBOW:** predict the center word from its surrounding bag of context words.
- **Negative sampling:** contrast observed pairs with words sampled from a noise distribution, avoiding a full-vocabulary update for every pair. Noise pairs are not verified semantic opposites or impossible co-occurrences.

Record corpus/tokenization, dimensions, window, minimum count, frequent-word subsampling, epochs, seed and worker count. The exercise uses a fixed-seed, single-worker Marvel Skip-gram model and compares a smaller window.

**Use for:** dense static word vectors and corpus-specific associations. One vector merges a word's senses: `hammer` can reflect Mjolnir and the Hammer family/company. Coordinate dimensions do not need individual human meanings for cosine to be useful. A single seed/window comparison does not establish a universal effect.

### 45. GloVe and comparing embedding sources

GloVe learns static word vectors from aggregate co-occurrence statistics. The exercise compares general pretrained Wikipedia/Gigaword GloVe with Marvel Word2Vec and explicit PPMI vectors.

Different corpora, algorithms, windows and vocabulary cutoffs can all change neighbors. When several change at once, do not attribute the result to only one. Audit out-of-vocabulary words. Similar context can connect synonyms, opposites, names or topical associates.

### 46. Document fingerprints and semantic axes

The exercise constructs character vectors from weighted averages of high-TF-IDF fingerprint words. Define an axis as the mean of one pole's word vectors minus the mean of the other pole's vectors, for example magic minus science, and project character vectors onto it.

State whether word vectors, character vectors and the axis are normalized; with normalized character and axis, the score is a cosine. Record missing pole/fingerprint words. Compare rankings under another embedding and inspect large movers.

**Use for:** exploring an explicitly defined contrast. The axis reflects the pole choice, training data and document representation; it is not an objective, corpus-independent character trait.

## Week 7 — Contextual models, validation and retrieval

### 47. Contextual and sentence/document embeddings

Static embeddings return one vector per type. Contextual encoders compute token representations from surrounding text, allowing `bank` in a river sentence to differ from `bank` in a finance sentence. Sentence encoders pool text into vectors intended for comparison.

Distinguish pretraining, inference and fine-tuning. In our atlas/search exercises the pretrained encoder is frozen; encoding Marvel is inference, not new training on Marvel.

The reviewed implementation uses pinned `all-MiniLM-L6-v2`, producing 384-dimensional vectors with a 256-wordpiece input limit. It creates contiguous windows of at most 180 whitespace words, shortening them to at most 254 wordpieces before special tokens. Chunks are normalized; each page is the normalized equal mean of its chunk vectors. Equal weighting lets a short final chunk count as much as a full one. Preserve raw offsets and verify text coverage rather than silently truncating a page.

### 48. Corpus atlases: PCA and t-SNE

Use dense document vectors to explore a collection in 2D:

- **PCA:** a linear projection; report explained variance for the displayed components.
- **t-SNE:** a nonlinear visualization emphasizing local neighborhoods; record perplexity, initialization and seed.

Compute actual nearest neighbors in the original representation and compare them with neighbors in the map. Recolor the same coordinates by network communities, LDA or embedding clusters to compare views fairly. Large gaps and distances between distant t-SNE groups are not literal semantic distances. Neither map is a replacement for the original-vector nearest-neighbor index.

### 49. BERTopic, UMAP, HDBSCAN and c-TF-IDF

The exercised pipeline uses:

1. The same document embeddings as the atlas.
2. UMAP to reduce dimension for clustering.
3. HDBSCAN to identify density-based groups, retaining label `-1` for outliers.
4. Class-based TF-IDF to describe groups with characteristic words.

Record UMAP neighbors/components/metric/seed and HDBSCAN minimum cluster size/minimum samples. Here name filtering changes the **word descriptions**, not the raw-text embeddings used to form clusters.

Compare with LDA and hyperlink communities on the same pages using ARI and representative documents. Vary minimum cluster size while holding other settings fixed. Report outlier coverage and group merges. A hard embedding cluster, a topic mixture and a graph community are different objects based on different evidence.

### 50. Sentiment instruments: lexicon, logistic regression and contextual classifier

**Lexicon:** combine word polarities using a declared sum/mean rule. VADER adds rules for features such as negation and intensification beyond a plain lookup.

**Supervised lexical baseline:** TF-IDF unigram/bigram features with logistic regression. For a positive class encoded 1:

$$
\log\frac{P(y=1\mid x)}{1-P(y=1\mid x)}=b+\beta^\top x.
$$

A positive coefficient raises log-odds holding other features fixed; it is not a causal or universal property of the word. Fit vocabulary and IDF on training data only, then transform held-out data.

**Contextual classifier:** use a pretrained task-specific model, stating its training task, revision, input limit and truncation rule. The exercise's DistilBERT movie-sentiment model receives only the first 512 wordpieces of long inputs.

Use the same held-out review IDs to compare instruments, while disclosing differing text coverage and possible prior benchmark exposure. Accuracy on movie reviews does not validate sentiment measurement on superhero biographies.

### 51. Validation, controlled sentences and domain shift

Define what the score should measure: reviewer evaluation, narrator attitude, plot-event valence and character morality are different constructs.

Inspect sampled examples before relying on aggregate accuracy. Use minimal changes such as `good` versus `not good`, and mixed/ironic examples such as a hero dying while saving others. Check false positives/negatives, confidence, long-input coverage and what text the model actually received.

Validate on examples from the intended domain with a clear annotation policy and independent human review where possible. A model score of 0.97 is not demonstrated 97% correctness on a new domain. If aggregating sentence scores into a document or narrative curve, specify segmentation, weighting and smoothing; the curve measures the instrument's response to wording.

### 52. NER, BIO tagging and span evaluation

Named-entity recognition finds spans and assigns types. BIO tags mark **B**eginning, **I**nside and **O**utside an entity; specify categories such as PERSON/GPE before judging output.

Preserve raw offsets and compare with annotated spans. Under strict evaluation both boundaries and entity type must match:

$$
Precision=\frac{TP}{TP+FP},\qquad Recall=\frac{TP}{TP+FN}.
$$

Inspect truncated names, superhero aliases tagged as organizations, titles tagged as locations and creators/actors counted as people. A small assistant-labeled sample is an editable diagnostic reference, not independent human ground truth or a reliable corpus-wide accuracy estimate.

### 53. Entity resolution and co-occurrence networks

Resolve mentions to identities using an explicit alias table or reviewed rules: `Iron Man` and `Tony Stark` can identify one person, while a title such as `Ghost Rider` may refer to several incarnations. Keep raw mentions and unresolved ambiguity visible.

Define the co-occurrence unit, then connect distinct resolved entities sharing that unit. The exercises compare sentences with original blank-line paragraphs, counting an edge once per unit and retaining isolated vertices.

Audit the resulting graph with source evidence. Wider units add edges between names with no explicit interaction; `Tony has never met Loki` still creates a co-occurrence edge. PERSON includes real creators and voice actors unless filtered. Incomplete resolution can split a character across several vertices, altering degree and communities.

**Use for:** mapping textual association. Calling it a friendship or interaction network requires additional relationship extraction and validation.

### 54. Sparse and dense retrieval

**Sparse retrieval:** transform a query with the corpus vocabulary/IDF and rank documents by TF-IDF cosine. Exact names and terms work well; paraphrases with no lexical overlap can fail. Out-of-vocabulary query terms are ignored, so flag a query with no usable nonzero representation.

**Dense retrieval:** encode the query and documents/passages with a compatible encoder and rank by cosine. Compare normalized page means with best-passage scores:

$$
score(q,d)=\max_{p\in passages(d)}\cos(q,p).
$$

The repo compares whole-page TF-IDF, dense page means, 180-word passages and 60-word passages. Passage limits also enforce the encoder's wordpiece cap. Maximum-passage scoring gives long documents more opportunities to match. Sparse and dense cosine magnitudes are not directly comparable quality scores.

### 55. Retrieval evaluation and RAG error diagnosis

Save queries and intended targets before inspecting rankings. Report target ranks and inspect top results with a stated relevance rubric. An absent target is a corpus-coverage failure; a plausible alternate incarnation can be relevant even if it is not the intended page.

Keep returned passages and surrounding source text. A top-ranked page does not guarantee its selected passage supports every query constraint: our Venom result can retrieve an alternate version explicitly described as non-extraterrestrial.

The exercise uses a 0/1/2 rubric for irrelevant/partially relevant/directly relevant results. These assistant judgments cover selected results, not exhaustive independent ground truth. Vary chunk size and report both improvements and regressions.

**RAG:** retrieval selects evidence; generation writes an answer from it. Diagnose missing/irrelevant retrieved evidence separately from an answer that invents or misrepresents a claim despite adequate evidence. Our search implementation stops at retrieval and does not implement a generation stage.

### 56. Bias tracing through the full pipeline

Trace the chain from the underlying social/editorial process to corpus coverage, text extraction, preprocessing, pretrained models, identity resolution, graph construction, aggregation and the final claim.

Concrete checks from the exercises include auditing character-versus-creator nodes, separating plot from publication/adaptation sections, checking missing pages, stratifying by page length, reviewing aliases and rebuilding sentence/paragraph networks. Compare rankings, edge overlap and communities after a justified change.

Several methods agreeing can reflect shared coverage or boilerplate rather than independent confirmation. Explain whose annotations or judgments were used and retain examples so they can be reviewed.

## A workflow for the final project

### 1. Write the question and measurement contract

Record the population, time window, data source, node/document unit, edge rule and intended meaning of the output. State one primary comparison and what observation would challenge the proposed explanation. Separate exploratory questions from hypotheses fixed before seeing results.

### 2. Freeze and audit the inputs

Preserve raw files, source URLs, download dates, IDs, licenses/access constraints and hashes. Check missing nodes/pages, duplicates, aliases, isolates, self-loops, repeated edges and text extraction. Keep raw text/offsets alongside derived features.

### 3. Establish a simple baseline

For networks: report size, degrees, density, isolates, components and a basic layout. For text: report document lengths, tokenizer rules, vocabulary, sparse counts and raw examples. Validate a few calculations by hand and check invariants before adding models.

### 4. Choose a small set of complementary analyses

Possible combinations grounded in the semester:

| Aim | Connected analysis |
|---|---|
| Explain brokerage | Degree and betweenness → degree-preserving null scores → inspect unusual brokers → adaptive removal versus random orders |
| Explain group structure | Louvain/Infomap → seed stability and null modularity → community term rates or LDA mixtures → inspect exceptions |
| Compare structure with language | Hyperlink communities → TF-IDF/dense similarity → NMI/ARI or membership tables → raw evidence for agreement/disagreement |
| Build a network from documents | NER audit → alias resolution → sentence/paragraph graphs → creator/character audit → robustness of centrality and groups |
| Build evidence-based search | TF-IDF baseline → dense page/passage retrieval → fixed queries and relevance judgments → chunk-size sensitivity and passage support |

Choose methods because they answer the question. A clear, validated comparison is more useful than including every method in this file.

### 5. Match uncertainty and sensitivity to the claim

Use repeated realizations for random models, degree/label constraints for the relevant null, repeated seeds for stochastic grouping and held-out labels for prediction. Vary a small set of defensible preprocessing/parameter choices. Record which choices change the conclusion.

Prespecify test tails and key statistics where possible. Report effect sizes and empirical resolution alongside p-values. Label exploratory outliers and case studies selected after inspecting results. Subjective annotations and small samples need their limitations stated beside the associated result.

### 6. Make each claim reviewable

For every important conclusion retain:

- The exact input scope and definition of the statistic.
- The relevant baseline/null, parameters and seeds.
- Numerical outputs with uncertainty or run-to-run variation.
- Representative source passages, graph records or manual checks.
- A limitation tied to that particular interpretation.

Avoid treating a graph layout as a distance metric, a topic label as an automatic discovery, a classifier score as validity, or a co-occurrence edge as a social interaction.

### 7. Package the analysis and communicate it

Keep data processing, measurement and presentation separable. Save machine-readable tables, package/model versions and deterministic tie rules. Pin model revisions and distinguish cached-vector reproduction from fresh model inference.

Write captions specifying population, direction/weights, filters, denominators and error-bar meaning. If reusing this website's download system, refresh its reproduction packages after changing bundled analyses. A project report should connect the question, method, baseline, result and interpretation in that order.

## Reusable code and source material

### Code already in this repository

These scripts reproduce the particular website stories. They provide patterns to adapt, rather than implementations of every method above.

| Week | Entry point | Reusable parts |
|---|---|---|
| 1 | [build_week1.py](../analysis/build_week1.py), [week1.ipynb](../analysis/week1.ipynb) | Validated directed loader, components, mixed-bin degree distributions, seeded layout, removal example |
| 2 | [build_week2.py](../analysis/build_week2.py) | Exact person-first/endpoint expectations, degree swaps, $G(n,m)$ ensembles, corrected empirical tests |
| 3 | [build_week3.py](../analysis/build_week3.py) | Adaptive degree/betweenness attacks, single-removal effects, random-order envelopes |
| 4 | [build_week4.py](../analysis/build_week4.py), [plot_week4.py](../analysis/plot_week4.py) | Weight aggregation, disparity significance, exact tied-threshold sweep, union-find and backbone figures |
| 5 | [build_week5.py](../analysis/build_week5.py) | Shared-token-run index, exact matching, raw spans and thresholded reuse networks |
| 6 | [build_week6.py](../analysis/build_week6.py) | Unsmoothed TF-IDF, name-filter comparison, nearest neighbors and cosine contributions |
| 7 | [build_week7.py](../analysis/build_week7.py), [encode_week7.py](../analysis/encode_week7.py) | Sparse/dense rankings, cached vectors, passage offsets and optional pinned-model inference |

Frozen graph/text inputs live under [site/data](../site/data); saved Week 7 query/vector inputs live under [analysis/data](../analysis/data). See [README.md](../README.md) for setup, commands, validation and the separate Week 6/7 dependency files. [package_reproducibility.py](../analysis/package_reproducibility.py) builds the website's downloadable analysis packages.

### Materials reviewed outside the repository

The local course folder was `Documents/Master DTU/Haustönn 2026/socialgraphs`. These files remain there; they have not been copied into this repository:

| Week | Reviewed exercise sources |
|---|---|
| 1 | `Week1/Questions.md`, `exercises_1_4_1_5_1_7.md`, degree-distribution and toolbox notebooks |
| 2 | `Week2/exercise_2_1_random_networks.md`, `exercise_2_3_clustering.md`, small-world/attachment/power-law/null/friendship answer sheets and companion notebook sections, `exercise_2_7_models_by_hand.md` |
| 3 | `Week3/exercise_3_answers.md`, companion notebook sections |
| 4 | `Week4/exercise_4_answers.md`, `exercise_4_4_openalex.md`, `exercise_4_13_go_nuts.md` |
| 5 | `Week5/exercise_5_answers.md`, companion notebook sections |
| 6 | `Week6/exercise_6_answers.md`, companion notebook sections |
| 7 | `Week7/exercise_7_answers.md`, companion notebook sections |
| Cross-check | `Exam1/study-plan.md` and `Exam2/study-plan.md` methods checklists |

The week-by-week exercise answers provide the source for methods not implemented in this repo, such as LDA, Word2Vec, the corpus atlas, BERTopic, sentiment and NER. The original assignment pages are [Week 1](https://sunelehmann.com/socialgraphs2026-web/weeks/week1.html), [Week 2](https://sunelehmann.com/socialgraphs2026-web/weeks/week2.html), [Week 3](https://sunelehmann.com/socialgraphs2026-web/weeks/week3.html), [Week 4](https://sunelehmann.com/socialgraphs2026-web/weeks/week4.html), [Week 5](https://sunelehmann.com/socialgraphs2026-web/weeks/week5.html), [Week 6](https://sunelehmann.com/socialgraphs2026-web/weeks/week6.html) and [Week 7](https://sunelehmann.com/socialgraphs2026-web/weeks/week7.html). This guide summarizes the saved work; those links identify the course sources and were not re-fetched for this review.
