import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
from champion_repository import repo
from pick_service import TeamAnalyzer

def generate_training_data(n_samples=5000):
    champs = repo.get_all()
    data = []
    targets = []
    for _ in range(n_samples):
        enemy = np.random.choice(champs, 5, replace=False)
        ally = np.random.choice([c for c in champs if c not in enemy], np.random.randint(0,5), replace=False)
        candidate = np.random.choice([c for c in champs if c not in enemy and c not in ally], 1)[0]
        weaknesses = TeamAnalyzer.analyze_enemy_weaknesses(enemy)
        target = TeamAnalyzer.score_champion_rulebased(candidate, weaknesses, ally)
        from ml_model import MLPredictor
        predictor = MLPredictor()  # model yok, sadece build_features için
        features = predictor.build_features(candidate, enemy, ally)[0]
        data.append(features)
        targets.append(target)
    return np.array(data), np.array(targets)

if __name__ == "__main__":
    X, y = generate_training_data(5000)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, "champion_model.pkl")
    print("Model eğitildi ve kaydedildi.")
