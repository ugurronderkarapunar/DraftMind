import joblib
import numpy as np
import pandas as pd
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'champion_model.pkl')

class MLPredictor:
    def __init__(self):
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
        else:
            self.model = None

    def build_features(self, champ, enemy_champs, ally_champs):
        """
        Özellik vektörü:
        - Aday şampiyonun tüm sayısal özellikleri (10 adet)
        - Düşman takımın ortalama ve std'leri (10*2 = 20)
        - Dost takımın ortalama ve std'leri (20)
        - Düşman hasar tipi dağılımı (AD/AP/Mixed oranları) (3)
        - Dost takım hasar tipi dağılımı (3)
        Toplam: ~56 özellik
        """
        def champ_to_array(c):
            return [c['early_power'], c['late_power'], c['cc_level'], c['tankiness'],
                    c['mobility'], c['burst'], c['armor_mr']]
        
        enemy_arr = np.array([champ_to_array(c) for c in enemy_champs])
        ally_arr = np.array([champ_to_array(c) for c in ally_champs]) if ally_champs else np.zeros((0,7))
        
        enemy_mean = enemy_arr.mean(axis=0) if len(enemy_arr) > 0 else np.zeros(7)
        enemy_std = enemy_arr.std(axis=0) if len(enemy_arr) > 0 else np.zeros(7)
        ally_mean = ally_arr.mean(axis=0) if len(ally_arr) > 0 else np.zeros(7)
        ally_std = ally_arr.std(axis=0) if len(ally_arr) > 0 else np.zeros(7)

        def damage_dist(champs):
            ad = sum(1 for c in champs if c['damage_type'] == 'AD')
            ap = sum(1 for c in champs if c['damage_type'] == 'AP')
            mixed = sum(1 for c in champs if c['damage_type'] == 'Mixed')
            total = len(champs) if len(champs) > 0 else 1
            return [ad/total, ap/total, mixed/total]

        enemy_dmg = damage_dist(enemy_champs)
        ally_dmg = damage_dist(ally_champs)
        
        features = np.concatenate([champ_to_array(champ), enemy_mean, enemy_std, ally_mean, ally_std, enemy_dmg, ally_dmg])
        return features.reshape(1, -1)

    def predict(self, features):
        if self.model:
            return float(self.model.predict(features)[0])
        return None
