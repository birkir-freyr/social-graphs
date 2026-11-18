# Does Christopher Nolan cast actors in their typical roles?

Working proposal for the final project in DTU 02805, Social Graphs and Interactions.

## Research question

Do characters played in Christopher Nolan films resemble the characters the same
actors had already played for other directors? Is that resemblance stronger than
for comparable roles those actors take with other directors?

We will build an actor–film network, extend it with the actors' earlier films,
and use character-specific text to measure how each Nolan role fits the actor's
previous roles. The comparison with other directors will help establish whether
any pattern is distinctive to Nolan.

## Dataset and scope

- Include all released feature films directed by Nolan and every credited actor
  in those films.
- Gather all available earlier feature-film credits for those actors, without a
  fixed starting year. Record missing credits or character text as coverage gaps.
- For each Nolan role, use films released before that particular Nolan film to
  construct the actor's historical profile. Use earlier films by other directors
  as the main baseline. Release dates approximate the actor's career history at
  that point. Record ambiguous dates and apply a consistent rule.
- Actors with a single Nolan appearance can qualify if they have enough earlier
  roles with usable character text. The pilot will establish a minimum history
  and text requirement before the main analysis.
- Count a recurring character across sequels once when estimating an actor's
  range of roles. Preserve the individual film credits in the network.

TMDB provides movie casts, character names, actor filmographies, and film metadata.
Wikipedia plot sections are a candidate source of character passages. Save source
IDs, retrieval dates, and the original passages so each measurement is traceable.
Use plot overviews to locate relevant evidence, then extract the passages about
the particular character. [TMDB film credits](https://developer.themoviedb.org/reference/movie-credits)
and [actor filmographies](https://developer.themoviedb.org/reference/person-movie-credits).

## Network construction

The main graph is an undirected bipartite network with two node types.

| Element | Meaning |
| --- | --- |
| Actor node | A person identified by a stable source ID |
| Film node | A film, with its director, release date, and genres |
| Actor–film edge | A credited appearance, linked to the character or characters played |
| Character evidence | Source passages and role measurements associated with the casting credit |

Start with every credited cast member in all Nolan-directed feature films. Add earlier
films through those actors' filmographies. The expanded graph's actor population
remains the actors drawn from Nolan's casts, so its outside-film cast lists will
be partial.

For each target role, the actor's eligible earlier film connections define the
historical roles used in the comparison. Report how many actors, films, credits,
and usable character passages survive each selection step.

## Measuring an actor's typical roles

An actor may have several recurring kinds of characters. The pilot will explore
how to describe those patterns using the character's function in the story,
motivations, occupation, and relationships with other characters.

Use sentence embeddings and cosine similarity as a candidate automated measure
of resemblance between character passages. Inspect both the average similarity
to earlier roles and the distribution of individual matches before choosing the
main measure. Reading the closest passages will help explain what drives a score.

Mask character and film names in the comparison text and inspect passages for
shared settings or vocabulary. These choices can change how much a score reflects
the character's role in the story. Select the final measure using the pilot and
human judgments before running the main comparison.

## Comparison and validation

1. For each eligible Nolan role, calculate its resemblance to the same actor's
   earlier roles for other directors.
2. Select roles that actor played for other directors in a comparable release
   period, genre, and billing position. For each comparison role, build its own
   history using only films released before it.
3. Compare typicality scores within each actor, then combine actor-level results
   with equal weight per actor. Account for shared films and repeated actors when
   assessing uncertainty.
4. Check whether conclusions survive alternative eligible comparison films and
   a simpler text representation such as TF-IDF/cosine.
5. Independently label a shared sample of character pairs as a group. Record
   agreement and examine where the automated scores disagree with those labels.
   Keep a separate human-labeled sample for evaluating the final chosen method.

A possible finding is that Nolan roles resemble an actor's previous roles more
strongly, equally strongly, or less strongly than the comparison roles do. Report
the size and uncertainty of the difference, together with the passages that make
it interpretable.

## First pilot

- Collect histories and character passages for three actors, aiming for about
  five usable earlier roles per actor.
- Include supporting roles to test whether enough character-specific text exists.
- Independently label the same 15 character pairs and discuss disagreements.
- Check whether appropriate comparison films exist and whether text similarity
  reflects the intended character traits.
- Count the actors and roles with usable evidence across the full dataset before
  choosing the main measurement and minimum coverage requirements.


## Figures and limitations

The main figure would compare each actor's average typicality in Nolan roles with
their average in matched roles for other directors. A supporting cast matrix or
bipartite diagram can show the dataset, and a small set of character passages can
explain representative matches and disagreements.

The main uncertainties are character-text coverage, the number of eligible actors,
and how genre or passage length affects similarity. The findings describe roles
as represented in the collected text. Evidence about casting intentions or acting
performance would require additional material. Film ratings can provide context
if they help interpret a result.

## Connection to the course

- Week 1 supplies the foundations of nodes, edges, and network representations.
  The Network Atlas explains bipartite networks in Chapter 7.
- Week 2 motivates comparisons against an explicit baseline.
- Weeks 6–7 supply text representations, cosine similarity, embeddings, entity
  resolution, and validation against examples people read themselves.
- Week 8 explicitly suggests actors, films, and crews as a network, with plots
  or reviews supplying the text. Its project brief asks for one research question
  and checked measurements. [Week 8 project and dataset guidance](https://raw.githubusercontent.com/suneman/socialgraphs2026-web/main/docs/weeks/week8.html).

The repository's [semester methods guide](METHODS.md) collects the methods and
validation practices from the weekly work.
