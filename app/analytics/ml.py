import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from app.models import ClientOrganization
from .scoring import calculate_engagement_score


def build_training_dataset():
    rows = []

    for org in ClientOrganization.objects.all():
        rows.append({
            "engagement": calculate_engagement_score(org),
            "lifetime_value": org.lifetime_value_estimate or 0,
            "churned": 1 if org.relationship_status == "inactive" else 0
        })

    return pd.DataFrame(rows)


def train_churn_model():
    df = build_training_dataset()

    if len(df) < 5:
        return None

    X = df[["engagement", "lifetime_value"]]
    y = df["churned"]

    model = RandomForestClassifier()
    model.fit(X, y)

    return model


def predict_churn_probability(model, org):
    import numpy as np

    features = np.array([[
        calculate_engagement_score(org),
        org.lifetime_value_estimate or 0
    ]])

    return float(model.predict_proba(features)[0][1]) * 100