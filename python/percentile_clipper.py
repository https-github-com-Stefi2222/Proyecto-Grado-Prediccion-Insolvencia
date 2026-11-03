"""Transformador del modelo Random Forest final.
Debe quedar en python/ y estar disponible al cargar el archivo joblib.
"""
from sklearn.base import BaseEstimator, TransformerMixin
import pandas as pd

class PercentileClipper(
    BaseEstimator,
    TransformerMixin
):

    def __init__(self, lower=0.01, upper=0.99):
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):

        X_df = pd.DataFrame(
            X,
            columns=getattr(
                X,
                "columns",
                None
            )
        ).copy()

        self.lower_bounds_ = X_df.quantile(
            self.lower
        )

        self.upper_bounds_ = X_df.quantile(
            self.upper
        )

        return self

    def transform(self, X):

        X_df = pd.DataFrame(
            X,
            columns=getattr(
                X,
                "columns",
                None
            )
        ).copy()

        return X_df.clip(
            lower=self.lower_bounds_,
            upper=self.upper_bounds_,
            axis=1
        )


