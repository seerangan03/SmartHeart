"""
SmartHeart - Machine Learning Model
Trains and saves a heart disease prediction model using scikit-learn.
Uses a RandomForest classifier on synthetic/realistic medical data.
"""
import os
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'heart_model.pkl')


def generate_training_data(n=3000):
    """
    Generate realistic synthetic medical training data based on
    known risk factor distributions for heart disease.
    """
    np.random.seed(42)

    # Age: 25-80
    age = np.random.randint(25, 80, n)
    # Gender: 0=Female, 1=Male
    gender = np.random.randint(0, 2, n)
    # Systolic BP: 90-200
    bp = np.random.randint(90, 200, n)
    # Cholesterol: 120-400
    cholesterol = np.random.randint(120, 400, n)
    # Heart Rate: 50-200
    heart_rate = np.random.randint(50, 200, n)
    # Blood Sugar: 0=No, 1=Yes (fasting > 120 mg/dl)
    sugar = np.random.randint(0, 2, n)
    # Chest Pain: 0=Typical angina, 1=Atypical, 2=Non-anginal, 3=Asymptomatic
    chest_pain = np.random.randint(0, 4, n)

    # Compute risk label based on known medical correlations
    risk_score = (
        (age > 50).astype(int) * 2 +
        (gender == 1).astype(int) * 1 +
        (bp > 140).astype(int) * 2 +
        (cholesterol > 240).astype(int) * 2 +
        (heart_rate > 100).astype(int) * 1 +
        sugar * 2 +
        (chest_pain == 0).astype(int) * 3 +
        np.random.normal(0, 1, n)
    )
    y = (risk_score > 4).astype(int)

    X = np.column_stack([age, gender, bp, cholesterol, heart_rate, sugar, chest_pain])
    return X, y


def train_model():
    """Train and persist the heart disease prediction model."""
    X, y = generate_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', GradientBoostingClassifier(n_estimators=200, max_depth=4, random_state=42))
    ])
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"[ML] Model trained. Test accuracy: {acc:.3f}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    """Load existing model or train a new one."""
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return train_model()


def predict_risk(age, gender, bp, cholesterol, heart_rate, sugar, chest_pain):
    """
    Run prediction and return risk percentage + severity label.
    Returns: (risk_percent: float, severity: str, explanation: str)
    """
    model = load_model()
    X = np.array([[age, gender, bp, cholesterol, heart_rate, sugar, chest_pain]])

    prob = model.predict_proba(X)[0][1]  # probability of heart disease
    risk_percent = round(prob * 100, 1)

    if risk_percent < 25:
        severity = 'Low'
        color = '#27ae60'
        explanation = (
            "Your cardiovascular indicators are within healthy ranges. "
            "Continue maintaining a balanced diet, regular exercise, and routine check-ups. "
            "No immediate medical intervention required."
        )
    elif risk_percent < 50:
        severity = 'Moderate'
        color = '#f39c12'
        explanation = (
            "Some risk factors have been detected that may elevate your cardiovascular risk. "
            "It is advisable to consult your physician for a detailed evaluation, "
            "lifestyle modifications, and possible monitoring."
        )
    elif risk_percent < 75:
        severity = 'High'
        color = '#e67e22'
        explanation = (
            "Multiple significant risk factors are present. Immediate consultation with a "
            "cardiologist is strongly recommended. Diagnostic tests such as ECG, stress test, "
            "or echocardiogram may be required."
        )
    else:
        severity = 'Critical'
        color = '#c0392b'
        explanation = (
            "CRITICAL ALERT: Your risk profile indicates a very high probability of heart disease. "
            "Seek emergency medical evaluation immediately. Do not delay medical attention. "
            "Invasive investigations or urgent intervention may be necessary."
        )

    return risk_percent, severity, explanation, color


def get_feature_importance():
    """Return feature names and importance scores for visualization."""
    model = load_model()
    clf = model.named_steps['clf']
    features = ['Age', 'Gender', 'Blood Pressure', 'Cholesterol', 'Heart Rate', 'Blood Sugar', 'Chest Pain']
    importance = clf.feature_importances_.tolist()
    return features, importance
