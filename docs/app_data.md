App Data
========

The application version of ACORN features a small corpus of sentences, which
originates from an [early paper][paper] about ACORN. Vincent Giuliano and Paul
Jones, the paper's authors, compiled a larger version of this corpus to test
their retrieval technique; in an appendix, they sampled several sentences to
show as examples. The application uses this subset.

Giuliano and Jones's work was commissioned by the US Air Force, and the corpus
reflects this: terms and phrases include "NATO," "missile interception,"
"transonic bombers." The subset is small enough to include in its entirety
[here][here]. Of particular note is the corpus's sentence-level design. For the
earliest version of ACORN, a 'document' is a 'sentence,' which contains only
one occurrence of each term of phrase ('one hot encoding' in today's parlance).

[paper]: https://apps.dtic.mil/sti/citations/AD0290313
[here]: https://github.com/t-shoemaker/ACORN/blob/main/docs/acorn_app_demo_corpus.pdf

