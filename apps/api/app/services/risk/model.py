"""Serving wrapper for the operational risk model.

Loads the artifact written by ``ml/sentinel_ml/train_operational.py``: an XGBoost JSON booster
plus Platt calibration parameters and validation-chosen thresholds. Nothing is unpickled.

Explanations are exact TreeSHAP values computed by XGBoost itself (``pred_contribs``) in the
model's log-odds space, before calibration. Calibration is monotonic, so the ranking and the
direction of each contribution carry over to the calibrated score.
"""

import hashlib
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import xgboost as xgb

from app.services.risk.features import FEATURE_DESCRIPTIONS, FEATURE_NAMES, FEATURE_VERSION

ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "risk_models"
DEFAULT_MODEL_VERSION = "operational-v1"


class ModelArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class Contribution:
    feature: str
    label: str
    value: float
    contribution: float  # log-odds, raw model


@dataclass(frozen=True)
class Prediction:
    probability: float
    raw_probability: float
    base_value: float
    contributions: list[Contribution]


class RiskModel:
    def __init__(self, directory: Path) -> None:
        meta_path = directory / "metadata.json"
        booster_path = directory / "booster.json"
        if not meta_path.is_file() or not booster_path.is_file():
            raise ModelArtifactError(f"Risk model artifact missing in {directory.name}")
        self.metadata: dict[str, Any] = json.loads(meta_path.read_text())
        digest = hashlib.sha256(booster_path.read_bytes()).hexdigest()
        if digest != self.metadata["artifact"]["booster_sha256"]:
            raise ModelArtifactError("Risk model booster does not match its metadata digest")
        if tuple(self.metadata["features"]) != FEATURE_NAMES:
            raise ModelArtifactError("Risk model features differ from the serving feature code")
        if self.metadata["dataset"]["feature_version"] != FEATURE_VERSION:
            raise ModelArtifactError("Risk model was trained on a different feature version")
        self.version: str = self.metadata["model_version"]
        self.feature_version: str = FEATURE_VERSION
        cal = self.metadata["calibration_params"]
        self._a = float(cal["a"])
        self._b = float(cal["b"])
        self.high_threshold = float(self.metadata["thresholds"]["high"])
        self.medium_threshold = float(self.metadata["thresholds"]["medium"])
        self.limitations: list[str] = list(self.metadata["limitations"])
        self._booster = xgb.Booster()
        self._booster.load_model(booster_path)
        self._booster.feature_names = None  # trained on a bare numpy matrix

    def _matrix(self, rows: list[dict[str, float]]) -> xgb.DMatrix:
        data = np.array([[row[name] for name in FEATURE_NAMES] for row in rows], dtype=float)
        return xgb.DMatrix(data)

    def calibrate(self, raw: float) -> float:
        return 1.0 / (1.0 + math.exp(self._a * raw + self._b))

    def predict(self, rows: list[dict[str, float]]) -> list[Prediction]:
        if not rows:
            return []
        matrix = self._matrix(rows)
        raw = self._booster.predict(matrix)
        contribs = self._booster.predict(matrix, pred_contribs=True)
        out = []
        for i, row in enumerate(rows):
            per_feature = contribs[i][:-1]
            items = [
                Contribution(
                    feature=name,
                    label=FEATURE_DESCRIPTIONS[name],
                    value=float(row[name]),
                    contribution=float(per_feature[j]),
                )
                for j, name in enumerate(FEATURE_NAMES)
            ]
            items.sort(key=lambda c: abs(c.contribution), reverse=True)
            out.append(
                Prediction(
                    probability=self.calibrate(float(raw[i])),
                    raw_probability=float(raw[i]),
                    base_value=float(contribs[i][-1]),
                    contributions=items,
                )
            )
        return out

    def band(self, probability: float) -> str:
        if probability >= self.high_threshold:
            return "HIGH"
        if probability >= self.medium_threshold:
            return "MEDIUM"
        return "LOW"


@lru_cache
def get_model(version: str = DEFAULT_MODEL_VERSION) -> RiskModel:
    if not version.replace("-", "").replace(".", "").isalnum():
        raise ModelArtifactError("Invalid model version")
    return RiskModel(ARTIFACT_ROOT / version)
