# domain/ml/model.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


FEATURE_COLUMNS = [
    "days_since_last_effective",
    "weighted_7d",
    "weighted_14d",
    "weighted_30d",
    "effective_7d",
    "effective_14d",
    "effective_30d",
    "active_days_7d",
    "active_days_14d",
    "active_days_30d",
    "trend_weighted_7d_vs_prev7d",
    "consistency_30d",
]


@dataclass(frozen=True)
class TrainResult:
    model: Pipeline
    roc_auc: float
    n_samples: int
    positive_rate: float


def train_inactivity_model(df: pd.DataFrame, random_state: int = 42) -> TrainResult:
    if df.empty:
        raise ValueError("Dataset vazio. Não há dados suficientes para treinar.")

    # target
    y_col = "y_inactive_next_7d"
    if y_col not in df.columns:
        raise ValueError(f"Coluna target '{y_col}' não existe no dataset.")

    X = df[FEATURE_COLUMNS].copy()
    y = df[y_col].astype(int).copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), FEATURE_COLUMNS),
        ],
        remainder="drop",
    )

    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        solver="lbfgs",
    )

    model = Pipeline(steps=[("pre", pre), ("clf", clf)])
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)

    return TrainResult(
        model=model,
        roc_auc=float(auc),
        n_samples=int(len(df)),
        positive_rate=float(y.mean()),
    )


def save_model(model: Pipeline, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, p)


def load_model(path: str | Path) -> Pipeline:
    return joblib.load(Path(path))


def predict_risk(model: Pipeline, features_row: dict[str, float]) -> float:
    """
    Retorna probabilidade de ficar inativo nos próximos 7 dias (0..1).
    """
    X = pd.DataFrame([{k: float(features_row.get(k, 0.0)) for k in FEATURE_COLUMNS}])
    X.replace([float("inf")], 9999.0, inplace=True)
    X.fillna(0.0, inplace=True)
    return float(model.predict_proba(X)[0, 1])

