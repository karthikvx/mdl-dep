import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

def train_default_risk_model():
    # Load dataset
    data = pd.read_csv('data/mortgage_data.csv')
    
    # Train model
    X = data[['loan_amount', 'credit_score', 'dti_ratio']]
    y = data['defaulted']
    model = RandomForestClassifier()
    model.fit(X, y)
    
    # Save model
    joblib.dump(model, 'app/models/default_risk_model.pkl')
