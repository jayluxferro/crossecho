"""Interpretable ML fallback: ridge regression / gradient-boosted trees.

Only activated if the analytic model's forecasting RMSE exceeds
config.ANALYTIC_RMSE_THRESHOLD (default 0.15).

Features: [ζ_eff, distance, victim_2q_density, attacker_size_ratio,
           T1_attacker, T1_victim, T2_attacker, T2_victim]

Both ridge and GBT are inherently interpretable:
- Ridge: linear coefficients = feature importance
- GBT: SHAP values or built-in feature importance
"""

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge


def _build_feature_vector(
    zeta_eff: float,
    distance: int,
    victim_2q_density: float,
    attacker_size_ratio: float,
    t1_attacker: float,
    t1_victim: float,
    t2_attacker: float,
    t2_victim: float,
) -> np.ndarray:
    """Build a standardized feature vector for ML correction."""
    return np.array([
        zeta_eff * 1e6,          # convert GHz → kHz for nicer scale
        float(distance),
        victim_2q_density,
        attacker_size_ratio,
        t1_attacker,
        t1_victim,
        t2_attacker,
        t2_victim,
    ])


def train_correction_model(
    X_train: np.ndarray,  # noqa: N803
    y_train: np.ndarray,
    method: str = "ridge",
) -> Ridge | GradientBoostingRegressor:
    """Train an interpretable correction model.

    Args:
        X_train: Feature matrix (n_samples, n_features).
        y_train: Measured leakage values.
        method: "ridge" for linear regression or "gbt" for gradient-boosted trees.

    Returns:
        Trained model with predict() and feature_importances_ or coef_.
    """
    if method == "ridge":
        model = Ridge(alpha=1.0, fit_intercept=True)
    elif method == "gbt":
        model = GradientBoostingRegressor(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.05,
            random_state=42,
        )
    else:
        raise ValueError(f"Unknown method: {method}. Use 'ridge' or 'gbt'.")

    model.fit(X_train, y_train)
    return model


def predict_correction(
    model: Ridge | GradientBoostingRegressor,
    X: np.ndarray,  # noqa: N803
) -> np.ndarray:
    """Apply the correction model to new feature vectors."""
    return model.predict(X)


def feature_importance(
    model: Ridge | GradientBoostingRegressor,
) -> dict[str, float]:
    """Extract feature importance from the model.

    Returns mapping of feature name → importance score.
    """
    feature_names = [
        "zeta_eff_khz",
        "distance",
        "victim_2q_density",
        "attacker_size_ratio",
        "t1_attacker",
        "t1_victim",
        "t2_attacker",
        "t2_victim",
    ]

    if isinstance(model, Ridge):
        importances = np.abs(model.coef_)
    else:
        importances = model.feature_importances_

    return dict(zip(feature_names, importances.tolist()))
