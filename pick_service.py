import numpy as np
from typing import List, Dict, Optional
from ml_model import MLPredictor

class TeamAnalyzer:
    @staticmethod
    def analyze_enemy_weaknesses(enemy_champs: List[Dict]) -> List[tuple]:
        stats = {
            'early': [c['early_power'] for c in enemy_champs],
            'late': [c['late_power'] for c in enemy_champs],
            'cc': [c['cc_level'] for c in enemy_champs],
            'tank': [c['tankiness'] for c in enemy_champs],
            'mobility': [c['mobility'] for c in enemy_champs],
            'burst': [c['burst'] for c in enemy_champs]
        }
        ad_count = sum(1 for c in enemy_champs if c['damage_type'] in ['AD','Mixed'])
        ap_count = sum(1 for c in enemy_champs if c['damage_type'] in ['AP','Mixed'])

        weaknesses = []
        if np.mean(stats['early']) < 5:
            weaknesses.append(('weak_early', 'Erken oyunu zayıf'))
        if ad_count >= 4:
            weaknesses.append(('heavy_ad', 'Aşırı AD hasar'))
        if ap_count >= 4:
            weaknesses.append(('heavy_ap', 'Aşırı AP hasar'))
        if sum(stats['cc']) < 10:
            weaknesses.append(('low_cc', 'CC seviyesi düşük'))
        if sum(stats['tank']) < 8:
            weaknesses.append(('squishy', 'Takım dayanıksız'))
        # Yeni: aşırı mobilite
        if np.mean(stats['mobility']) > 3.5:
            weaknesses.append(('high_mobility', 'Çok hareketli takım, kitle kontrolü şart'))
        # Yeni: düşük burst
        if sum(stats['burst']) < 12:
            weaknesses.append(('low_burst', 'Ani hasar potansiyeli düşük'))
        return weaknesses

    @staticmethod
    def ally_synergy_bonus(champ: Dict, ally_champs: List[Dict]) -> float:
        if not ally_champs:
            return 0.0
        ally_cc = sum(a['cc_level'] for a in ally_champs)
        ally_tank = sum(a['tankiness'] for a in ally_champs)
        ally_burst = sum(a['burst'] for a in ally_champs)
        bonus = 0.0
        if ally_cc >= 8:
            bonus += champ['burst'] * 1.5
        if ally_tank <= 3:
            bonus += champ['tankiness'] * 2.0
        if ally_burst >= 12:
            bonus += champ['cc_level'] * 1.5 + champ['tankiness'] * 1.0
        # Yeni: Wombo combo potansiyeli (ör. Orianna + Malphite benzeri)
        if ally_cc >= 10 and champ['cc_level'] >= 4:
            bonus += 3.0
        return bonus

    @staticmethod
    def score_champion_rulebased(champ: Dict, weaknesses: List[tuple], ally_champs: List[Dict]) -> float:
        score = 0.0
        for w_type, _ in weaknesses:
            if w_type == 'weak_early':
                score += champ['early_power'] * 2.0
            elif w_type == 'heavy_ad':
                score += champ['armor_mr'] * 3.0
                if champ['damage_type'] in ['AP','Mixed']:
                    score += 3.0
            elif w_type == 'heavy_ap':
                score += champ['armor_mr'] * 3.0
                if champ['damage_type'] in ['AD','Mixed']:
                    score += 3.0
            elif w_type == 'low_cc':
                score += champ['mobility'] * 2.0 + champ['burst'] * 2.0
            elif w_type == 'squishy':
                score += champ['burst'] * 3.0 + champ['mobility'] * 1.5
            elif w_type == 'high_mobility':
                score += champ['cc_level'] * 3.0  # CC yüksek olanlar tercih
            elif w_type == 'low_burst':
                score += champ['tankiness'] * 2.0  # dayanıklı olup uzun savaş
        if ally_champs:
            score += TeamAnalyzer.ally_synergy_bonus(champ, ally_champs)
        return score

    @staticmethod
    def score_champion_ml(champ: Dict, enemy_champs: List[Dict], ally_champs: List[Dict]) -> Optional[float]:
        try:
            predictor = MLPredictor()
            features = predictor.build_features(champ, enemy_champs, ally_champs)
            return predictor.predict(features)
        except Exception as e:
            return None

    @staticmethod
    def get_top_picks(candidate_pool: List[Dict], weaknesses, ally_champs, use_ml=False, enemy_champs=None):
        scored = []
        for champ in candidate_pool:
            if use_ml and enemy_champs:
                s = TeamAnalyzer.score_champion_ml(champ, enemy_champs, ally_champs)
                if s is None:
                    s = TeamAnalyzer.score_champion_rulebased(champ, weaknesses, ally_champs)
            else:
                s = TeamAnalyzer.score_champion_rulebased(champ, weaknesses, ally_champs)
            scored.append((champ, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:3]
