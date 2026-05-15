import streamlit as st
from db_utils import get_champions, check_daily_limit, increment_usage

def analyze_enemy_weaknesses(enemy_champs):
    avg_early = sum(c['early_power'] for c in enemy_champs) / 5
    total_cc = sum(c['cc_level'] for c in enemy_champs)
    total_tank = sum(c['tankiness'] for c in enemy_champs)
    ad_count = sum(1 for c in enemy_champs if c['damage_type'] in ['AD','Mixed'])
    ap_count = sum(1 for c in enemy_champs if c['damage_type'] in ['AP','Mixed'])

    weaknesses = []
    if avg_early < 5:
        weaknesses.append(('weak_early', 'Erken oyunu zayıf'))
    if ad_count >= 4:
        weaknesses.append(('heavy_ad', 'Aşırı AD hasar'))
    if ap_count >= 4:
        weaknesses.append(('heavy_ap', 'Aşırı AP hasar'))
    if total_cc < 10:
        weaknesses.append(('low_cc', 'CC seviyesi düşük'))
    if total_tank < 8:
        weaknesses.append(('squishy', 'Takım dayanıksız (squishy)'))
    return weaknesses

def score_champion(champ, weaknesses):
    score = 0
    for w_type, _ in weaknesses:
        if w_type == 'weak_early':
            score += champ['early_power'] * 2
        elif w_type == 'heavy_ad':
            score += champ['armor_mr'] * 3
            if champ['damage_type'] in ['AP','Mixed']:
                score += 3
        elif w_type == 'heavy_ap':
            score += champ['armor_mr'] * 3
            if champ['damage_type'] in ['AD','Mixed']:
                score += 3
        elif w_type == 'low_cc':
            score += champ['mobility'] * 2 + champ['burst'] * 2
        elif w_type == 'squishy':
            score += champ['burst'] * 3 + champ['mobility'] * 1.5
    return score

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("Lütfen ana sayfadan giriş yap.")
    st.stop()

user = st.session_state.user
if not user['is_pro']:
    daily = check_daily_limit(user['id'])
    if daily >= 5:
        st.error("Günlük ücretsiz analiz hakkınız doldu. Pro üye olun veya yarın tekrar deneyin.")
        st.stop()
    else:
        st.info(f"Bugün {daily}/5 analiz kullanıldı.")

st.title("Takım Kompozisyonu Analizi")

all_champs = get_champions()
champ_names = sorted([c['name'] for c in all_champs])

use_pool = st.checkbox("Sadece kendi oynadığım şampiyonları öner")
if use_pool:
    pool = st.multiselect("Şampiyon havuzun", champ_names)
else:
    pool = champ_names

st.subheader("Düşman Takımı (5 şampiyon)")
enemy_picks = []
for i in range(5):
    pick = st.selectbox(f"Düşman {i+1}", [""] + champ_names, key=f"enemy_{i}")
    if pick:
        enemy_picks.append(pick)

st.subheader("Kendi Takımında Seçilmişler (varsa)")
ally_picks = []
for i in range(4):
    pick = st.selectbox(f"Dost {i+1}", [""] + champ_names, key=f"ally_{i}")
    if pick:
        ally_picks.append(pick)

if st.button("Analiz Et"):
    if len(enemy_picks) != 5:
        st.error("Düşman takımında tam 5 şampiyon seçmelisiniz.")
    else:
        enemy_data = [next(c for c in all_champs if c['name'] == name) for name in enemy_picks]
        ally_data = [next(c for c in all_champs if c['name'] == name) for name in ally_picks]
        excluded_names = set(enemy_picks + ally_picks)

        weaknesses = analyze_enemy_weaknesses(enemy_data)

        st.subheader("Düşman Zayıflıkları")
        if weaknesses:
            for _, desc in weaknesses:
                st.write(f"- {desc}")
        else:
            st.write("Belirgin bir zayıflık tespit edilemedi.")

        candidate_pool = [
            c for c in all_champs
            if c['name'] in pool and c['name'] not in excluded_names
        ]

        if not candidate_pool:
            st.warning("Seçilebilecek uygun şampiyon kalmadı.")
        else:
            scored = []
            for champ in candidate_pool:
                s = score_champion(champ, weaknesses)
                scored.append((champ, s))
            scored.sort(key=lambda x: x[1], reverse=True)
            top3 = scored[:3]

            st.subheader("En İyi 3 Öneri")
            for i, (champ, s) in enumerate(top3, 1):
                st.markdown(f"**{i}. {champ['name']}** ({champ['role']}) – Puan: {s:.1f}")
                reasons = []
                if any(w[0]=='weak_early' for w in weaknesses) and champ['early_power'] >= 7:
                    reasons.append("erken oyunda baskın")
                if any(w[0]=='heavy_ad' for w in weaknesses) and (champ['armor_mr'] >= 4 or champ['damage_type'] in ['AP','Mixed']):
                    reasons.append("AD ağırlıklı takıma karşı etkili")
                if any(w[0]=='heavy_ap' for w in weaknesses) and (champ['armor_mr'] >= 4 or champ['damage_type'] in ['AD','Mixed']):
                    reasons.append("AP ağırlıklı takıma karşı etkili")
                if any(w[0]=='low_cc' for w in weaknesses) and (champ['mobility'] >= 4 or champ['burst'] >= 4):
                    reasons.append("düşük CC'li rakiplere karşı cezalandırıcı")
                if any(w[0]=='squishy' for w in weaknesses) and champ['burst'] >= 4:
                    reasons.append("squishy hedefleri patlatabilir")
                if reasons:
                    st.caption(" + ".join(reasons))
                else:
                    st.caption("Genel denge tercihi")

        if not user['is_pro']:
            increment_usage(user['id'])
