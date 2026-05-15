import streamlit as st
import pandas as pd
import numpy as np
from champion_repository import repo
from auth_service import require_auth, require_pro_or_limit, AuthService
from pick_service import TeamAnalyzer
from logger_config import logger

# ---------- Sayfa yapılandırması ----------
st.set_page_config(page_title="LoL Pick Öneri", layout="wide")

@require_auth
@require_pro_or_limit
def main():
    st.title("Takım Kompozisyonu Analizi")
    
    all_champs = repo.get_all()
    all_names = [c['name'] for c in all_champs]

    # ---------- Rol bazlı seçim için yardımcı veri ----------
    roles = ["Top", "Jungle", "Mid", "ADC", "Support"]
    
    # ---------- Session state başlatma ----------
    defaults = {
        'bans': [],
        'enemy_roles': {r: "" for r in roles},
        'ally_roles': {r: "" for r in roles},
        'ally_roles_filled': {r: False for r in roles},
        'role_filter': 'Any',
        'use_pool': False,
        'pool': [],
        'use_ml': False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ---------- Banlar ----------
    with st.expander("🔨 Banlanan Şampiyonlar (İsteğe bağlı)", expanded=False):
        ban_count = st.number_input("Kaç ban var?", 0, 10, 0)
        ban_names = []
        for i in range(ban_count):
            ban = st.selectbox(f"Ban {i+1}", [""] + all_names, key=f"ban_{i}")
            if ban:
                ban_names.append(ban)
        st.session_state.bans = ban_names

    # ---------- Rol tabanlı düşman seçimi ----------
    st.subheader("👾 Düşman Takımı")
    enemy_cols = st.columns(5)
    enemy_picks = []
    for idx, role in enumerate(roles):
        with enemy_cols[idx]:
            # Seçenekler: banlılar ve diğer seçilmişler çıkarılsın
            taken = set(st.session_state.bans + enemy_picks + list(st.session_state.ally_roles.values()))
            available = [""] + [n for n in all_names if n not in taken]
            current = st.session_state.enemy_roles[role]
            if current and current not in available:
                current = ""
            choice = st.selectbox(f"{role}", available, index=available.index(current) if current in available else 0, key=f"enemy_{role}")
            st.session_state.enemy_roles[role] = choice
            if choice:
                enemy_picks.append(choice)

    # ---------- Dost takımı (kendi takımındaki diğerleri) ----------
    st.subheader("🛡️ Kendi Takımın (Senden başka seçilmişler)")
    ally_cols = st.columns(4)  # 5. sensin
    roles_to_fill = ["Top", "Jungle", "Mid", "ADC", "Support"]
    # Kullanıcının rolünü seç
    your_role = st.selectbox("Senin rolün:", ["Any"] + roles_to_fill, key="your_role")
    st.session_state.role_filter = your_role
    # Dost seçimlerinde senin rolün hariç diğer roller gösterilsin
    ally_roles_to_show = [r for r in roles_to_fill if r != your_role or your_role == "Any"]
    
    ally_picks = []
    for idx, role in enumerate(ally_roles_to_show):
        with ally_cols[idx]:
            taken = set(st.session_state.bans + enemy_picks + ally_picks + list(st.session_state.enemy_roles.values()))
            available = [""] + [n for n in all_names if n not in taken]
            current = st.session_state.ally_roles.get(role, "")
            if current and current not in available:
                current = ""
            choice = st.selectbox(f"Dost {role}", available, index=available.index(current) if current in available else 0, key=f"ally_{role}")
            st.session_state.ally_roles[role] = choice
            if choice:
                ally_picks.append(choice)

    # ---------- Kullanıcı havuzu ve ML seçeneği ----------
    col1, col2 = st.columns(2)
    with col1:
        use_pool = st.checkbox("Sadece kendi oynadığım şampiyonları öner", value=st.session_state.use_pool)
        st.session_state.use_pool = use_pool
    with col2:
        use_ml = st.checkbox("🧠 Makine öğrenmesi ile öner (deneysel)", value=st.session_state.use_ml)
        st.session_state.use_ml = use_ml

    if use_pool:
        taken_pool = set(st.session_state.bans + enemy_picks + ally_picks)
        pool_available = [n for n in all_names if n not in taken_pool]
        pool = st.multiselect("Havuzun", pool_available, default=st.session_state.pool)
        st.session_state.pool = pool

    # ---------- Analiz ----------
    if st.button("🚀 Analiz Et", type="primary"):
        if len(enemy_picks) != 5:
            st.error("Düşman takımında tüm roller seçilmeli!")
            return
        
        enemy_data = [next(c for c in all_champs if c['name'] == name) for name in enemy_picks]
        ally_data = [next(c for c in all_champs if c['name'] == name) for name in ally_picks]
        excluded_names = set(enemy_picks + ally_picks + st.session_state.bans)

        weaknesses = TeamAnalyzer.analyze_enemy_weaknesses(enemy_data)

        # Aday havuzu
        if use_pool and st.session_state.pool:
            candidates = [c for c in all_champs if c['name'] in st.session_state.pool and c['name'] not in excluded_names]
        else:
            candidates = [c for c in all_champs if c['name'] not in excluded_names]
        if your_role != "Any":
            candidates = [c for c in candidates if c['role'] == your_role]

        if not candidates:
            st.warning("Uygun şampiyon kalmadı.")
            return

        # Zayıflıkları göster
        st.subheader("📊 Düşman Zayıflıkları")
        if weaknesses:
            for _, desc in weaknesses:
                st.markdown(f"- ⚡ {desc}")
        else:
            st.success("Belirgin zayıflık yok, dengeli bir takım.")

        # Önerileri al
        top3 = TeamAnalyzer.get_top_picks(candidates, weaknesses, ally_data,
                                          use_ml=st.session_state.use_ml, enemy_champs=enemy_data)

        # Görsel öneri kartları
        st.subheader("🏆 En İyi 3 Öneri")
        cols = st.columns(3)
        for i, (champ, score) in enumerate(top3):
            with cols[i]:
                # Basit görsel: Emoji ile rol gösterimi
                role_emoji = {"Top":"🛡️","Jungle":"🌳","Mid":"🔥","ADC":"🏹","Support":"💚"}.get(champ['role'],"❓")
                st.markdown(f"### {role_emoji} {champ['name']}")
                st.metric("Puan", f"{score:.1f}")
                # Nedenleri (önceki mantıkla)
                reasons = []
                # (aynı reason mantığı)
                st.caption(" + ".join(reasons) if reasons else "Genel denge")

        # Geri bildirim butonları
        st.subheader("Geri Bildirim")
        fb_cols = st.columns(len(top3))
        from db_utils import save_feedback
        user = st.session_state.user
        for i, (champ, _) in enumerate(top3):
            with fb_cols[i]:
                if st.button(f"👍 {champ['name']}", key=f"like_{i}"):
                    save_feedback(user['id'], champ['name'], 1)
                    st.success("Teşekkürler!")
                if st.button(f"👎 {champ['name']}", key=f"dislike_{i}"):
                    save_feedback(user['id'], champ['name'], -1)
                    st.info("Geri bildirim alındı.")

        # Hakkı düş
        if not user['is_pro']:
            AuthService.increment_usage(user['id'])
            logger.info(f"Kullanıcı {user['username']} analiz yaptı.")

if __name__ == "__main__":
    main()
