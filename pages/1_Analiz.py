import streamlit as st
from db_utils import get_champions, check_daily_limit, increment_usage, save_feedback

# ---------- yardımcı fonksiyonlar ----------
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

def ally_synergy_bonus(champ, ally_champs):
    bonus = 0
    ally_cc = sum(a['cc_level'] for a in ally_champs)
    ally_tank = sum(a['tankiness'] for a in ally_champs)
    ally_burst = sum(a['burst'] for a in ally_champs)
    if ally_cc >= 8:
        bonus += champ['burst'] * 1.5
    if ally_tank <= 3:
        bonus += champ['tankiness'] * 2
    if ally_burst >= 12:
        bonus += champ['cc_level'] * 1.5 + champ['tankiness'] * 1.0
    return bonus

def score_champion(champ, weaknesses, ally_champs):
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
    if ally_champs:
        score += ally_synergy_bonus(champ, ally_champs)
    return score

# ---------- oturum kontrolü ----------
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

# ---------- veri hazırlığı ----------
all_champs = get_champions()
all_names = sorted([c['name'] for c in all_champs])

# session state başlangıç
for key in ['enemy_picks', 'ally_picks', 'pool', 'use_pool', 'role_filter']:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ['enemy_picks','ally_picks','pool'] else (False if key=='use_pool' else 'Any')

# ---------- rol seçimi ----------
st.subheader("Kendi Pozisyonun")
role_filter = st.selectbox("Hangi koridorda oynayacaksın?", ["Any","Top","Jungle","Mid","ADC","Support"],
                           key='role_filter_sel')
st.session_state.role_filter = role_filter

# ---------- yardımcı: seçili seti döndür ----------
def get_selected_set(exclude_key=None, exclude_idx=None):
    selected = set()
    # düşman
    for i in range(5):
        val = st.session_state.get(f"enemy_{i}", "")
        if val and not (exclude_key == 'enemy' and exclude_idx == i):
            selected.add(val)
    # dost
    for i in range(4):
        val = st.session_state.get(f"ally_{i}", "")
        if val and not (exclude_key == 'ally' and exclude_idx == i):
            selected.add(val)
    # havuz
    pool = st.session_state.get("pool", [])
    for val in pool:
        selected.add(val)
    return selected

# ---------- kendi havuzu ----------
use_pool = st.checkbox("Sadece kendi oynadığım şampiyonları öner", value=st.session_state.use_pool)
st.session_state.use_pool = use_pool
if use_pool:
    # havuzda gösterilebilecekler: tüm şampiyonlar eksi düşman/dost seçimleri (havuzun kendisini çıkarmaya gerek yok)
    pool_available = [name for name in all_names if name not in get_selected_set()]
    current_pool = [name for name in st.session_state.pool if name in pool_available]
    pool = st.multiselect("Şampiyon havuzun", pool_available, default=current_pool)
    st.session_state.pool = pool
else:
    st.session_state.pool = []

# ---------- düşman takımı ----------
st.subheader("Düşman Takımı (5 şampiyon)")
enemy_picks = []
for i in range(5):
    current_val = st.session_state.get(f"enemy_{i}", "")
    available = [""] + [name for name in all_names if name not in get_selected_set(exclude_key='enemy', exclude_idx=i) or name == current_val]
    if current_val and current_val not in available:
        current_val = ""
    choice = st.selectbox(f"Düşman {i+1}", available, index=available.index(current_val) if current_val in available else 0, key=f"enemy_{i}_sel")
    st.session_state[f"enemy_{i}"] = choice
    if choice:
        enemy_picks.append(choice)

# ---------- dost takımı ----------
st.subheader("Kendi Takımında Seçilmişler (varsa)")
ally_picks = []
for i in range(4):
    current_val = st.session_state.get(f"ally_{i}", "")
    available = [""] + [name for name in all_names if name not in get_selected_set(exclude_key='ally', exclude_idx=i) or name == current_val]
    if current_val and current_val not in available:
        current_val = ""
    choice = st.selectbox(f"Dost {i+1}", available, index=available.index(current_val) if current_val in available else 0, key=f"ally_{i}_sel")
    st.session_state[f"ally_{i}"] = choice
    if choice:
        ally_picks.append(choice)

# ---------- analiz ----------
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

        # aday havuzu
        if use_pool and st.session_state.pool:
            candidate_pool = [
                c for c in all_champs
                if c['name'] in st.session_state.pool and c['name'] not in excluded_names
                and (role_filter == "Any" or c['role'] == role_filter)
            ]
        else:
            candidate_pool = [
                c for c in all_champs
                if c['name'] not in excluded_names
                and (role_filter == "Any" or c['role'] == role_filter)
            ]

        if not candidate_pool:
            st.warning("Seçilebilecek uygun şampiyon kalmadı.")
        else:
            scored = []
            for champ in candidate_pool:
                s = score_champion(champ, weaknesses, ally_data)
                scored.append((champ, s))
            scored.sort(key=lambda x: x[1], reverse=True)
            top3 = scored[:3]

            st.subheader("En İyi 3 Öneri")
            for i, (champ, s) in enumerate(top3, 1):
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
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
                    if ally_data:
                        ally_cc = sum(a['cc_level'] for a in ally_data)
                        if ally_cc >= 8 and champ['burst'] >= 4:
                            reasons.append("dost takımın yüksek CC'si ile uyumlu")
                        if sum(a['tankiness'] for a in ally_data) <= 3 and champ['tankiness'] >= 4:
                            reasons.append("dost takıma dayanıklılık katıyor")
                    if reasons:
                        st.caption(" + ".join(reasons))
                    else:
                        st.caption("Genel denge tercihi")
                with col2:
                    fb_key = f"fb_{champ['name']}"
                    if fb_key not in st.session_state:
                        st.session_state[fb_key] = None
                    c1, c2 = st.columns(2)
                    if c1.button("👍", key=f"like_{champ['name']}_{i}"):
                        save_feedback(user['id'], champ['name'], 1)
                        st.session_state[fb_key] = "like"
                    if c2.button("👎", key=f"dislike_{champ['name']}_{i}"):
                        save_feedback(user['id'], champ['name'], -1)
                        st.session_state[fb_key] = "dislike"
                    if st.session_state[fb_key] == "like":
                        st.success("👍")
                    elif st.session_state[fb_key] == "dislike":
                        st.info("👎")

            # başarılı analiz hakkı
            if not user['is_pro']:
                increment_usage(user['id'])
