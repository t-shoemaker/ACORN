#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer


def load_lines(path: Path) -> list[str]:
    """Load a line-separated file."""
    with path.open("r") as fin:
        doc = [row.strip() for row in fin.readlines()]

    return doc


def parse_row(row: str) -> tuple[int, list[int]]:
    """Parse a bag-of-words feature row.

    Format: [rating tok_idx:tok_count tok_idx:tok_count ...]

    """
    row = row.split()
    rating, feats = int(row[0]), row[1:]
    feats = np.asarray([tok.split(":") for tok in feats], dtype=int)

    return rating, feats


def to_corpus(
    dataset: list[int], vocab: list[str], lemmatize: bool = True
) -> tuple[list[int], list[str]]:
    """Expand the bag-of-words features into 'documents' of n-repeated
    tokens.
    """
    ratings, feats = [], []
    for row in dataset:
        rating, vec = row
        ratings.append(rating)

        vec = [[vocab[tok[0]]] * tok[1] for tok in vec]
        if lemmatize:
            vec = [[LEMMATIZER.lemmatize(tok) for tok in toks] for toks in vec]

        vec = " ".join([" ".join(toks) for toks in vec])
        feats.append(vec)

    return ratings, feats


def main(args: argparse.Namespace) -> None:
    """Run the script."""
    # Load the files
    BoW_path, vocab_path = Path(args.bow), Path(args.vocab)
    BoW = load_lines(BoW_path)
    vocab = load_lines(vocab_path)

    # Parse the data and separate the ratings from the vectors
    dataset = [parse_row(row) for row in BoW]
    ratings, corpus = to_corpus(dataset, vocab, args.no_lemmatize)

    # Make a DTM
    stop_words = stopwords.words("english")
    vectorizer = CountVectorizer(
        max_df=args.max_df, min_df=args.min_df, stop_words=stop_words
    )
    vectorizer.fit(corpus)

    # Make a DataFrame and add the ratings as the last column
    DTM = vectorizer.transform(corpus)
    DTM = pd.DataFrame(
        DTM.todense(), columns=vectorizer.get_feature_names_out()
    )
    DTM.loc[:, "user_rating"] = ratings
    DTM.to_parquet(args.outfile)

    print(DTM.info())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert the IMDB review dataset to a DataFrame"
    )
    parser.add_argument("--bow", type=str, help="BoW.feat file")
    parser.add_argument("--vocab", type=str, help="imdb.vocab file")
    parser.add_argument("--outfile", type=str, help="DTM file (parquet)")
    parser.add_argument("--no_lemmatize", action="store_false")
    parser.add_argument("--max_df", type=float, default=0.95)
    parser.add_argument("--min_df", type=float, default=0.01)
    args = parser.parse_args()

    LEMMATIZER = WordNetLemmatizer()
    main(args)
