import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from joblib import dump, load

class TFIDFStore:
    def __init__(self, out_dir: str, tfidf_params: dict):
        self.out_dir = out_dir
        self.tfidf_path = os.path.join(out_dir, "tfidf.joblib")
        self.params = dict(
            max_features=tfidf_params.get("max_features", 20000),
            ngram_range=tuple(tfidf_params.get("ngram_range", [1, 2])),
            min_df=tfidf_params.get("min_df", 1),
            max_df=tfidf_params.get("max_df", 1.0),
        )
        os.makedirs(out_dir, exist_ok=True)
        self.vectorizer = None

    def fit_or_load(self, texts):
        if os.path.exists(self.tfidf_path):
            self.vectorizer = load(self.tfidf_path)
            return "loaded"
        vec = TfidfVectorizer(**self.params)
        vec.fit(texts)
        dump(vec, self.tfidf_path)
        self.vectorizer = vec
        return "fitted"

    def transform(self, texts):
        if self.vectorizer is None:
            raise RuntimeError("Vectorizer not initialized")
        X = self.vectorizer.transform(texts)
        return X

def load_templates_csv(csv_path: str):
    # CSV: id,template
    df = pd.read_csv(csv_path)
    if not {"id", "template"}.issubset(df.columns):
        raise ValueError("dict_templ.csv must contain columns: id,template")
    df = df.dropna(subset=["template"])
    df["id"] = df["id"].astype(int)
    df = df.sort_values("id").reset_index(drop=True)
    return df

