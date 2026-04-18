from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from data_processing import (
    MODEL_COLUMNS,
    MODEL_LOGIC_VERSION,
    TARGET_COLUMN,
    load_config,
    prepare_training_data,
    resolve_project_path,
)


def train_and_save_model(config_path: str | Path = "config.json") -> dict[str, Any]:
    config = load_config(config_path)
    training_config = config.get("training", {})

    frame = prepare_training_data(config_path)
    features = frame[MODEL_COLUMNS]
    labels = frame[TARGET_COLUMN]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=float(training_config.get("test_size", 0.2)),
        random_state=int(training_config.get("random_state", 42)),
        stratify=labels,
    )

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=320,
                    max_depth=12,
                    min_samples_leaf=2,
                    class_weight="balanced_subsample",
                    random_state=int(training_config.get("random_state", 42)),
                ),
            ),
        ]
    )

    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    accuracy = float(accuracy_score(y_test, predictions))

    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
    report = {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in report.items()}

    classifier = pipeline.named_steps["classifier"]
    feature_importance = dict(
        sorted(
            {
                column: float(value)
                for column, value in zip(MODEL_COLUMNS, classifier.feature_importances_)
            }.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    metrics = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "logic_version": MODEL_LOGIC_VERSION,
        "feature_columns": MODEL_COLUMNS,
        "samples": int(frame.shape[0]),
        "train_samples": int(x_train.shape[0]),
        "test_samples": int(x_test.shape[0]),
        "accuracy": accuracy,
        "class_distribution": labels.value_counts().to_dict(),
        "feature_importance": feature_importance,
        "classification_report": report,
    }

    model_path = resolve_project_path(config_path, config["paths"]["model"])
    metrics_path = resolve_project_path(config_path, config["paths"]["metrics"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    artifact = {
        "pipeline": pipeline,
        "feature_columns": MODEL_COLUMNS,
        "classes": sorted(labels.unique().tolist()),
        "sklearn_version": sklearn.__version__,
        "logic_version": MODEL_LOGIC_VERSION,
        "metrics": metrics,
    }
    joblib.dump(artifact, model_path)

    with metrics_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)

    return metrics


def _format_metrics(metrics: dict[str, Any]) -> str:
    return (
        f"Model training complete\n"
        f"Samples: {metrics['samples']}\n"
        f"Accuracy: {metrics['accuracy']:.4f}\n"
        f"Class distribution: {metrics['class_distribution']}"
    )


if __name__ == "__main__":
    metrics_output = train_and_save_model()
    print(_format_metrics(metrics_output))
