import streamlit as st
import pandas as pd
import numpy as np
from champion_repository import repo
from auth_service import require_auth, require_pro_or_limit, AuthService
from pick_service import TeamAnalyzer
from db_utils import save_feedback
from logger_config import logger

st.set_page_config(page_title="LoL Pick Öneri", layout="wide")

@require_auth
@require_pro_or_limit
def main():
    st.title("Takım Kompozisyonu Analizi")
    
    all_champs = repo.get_all()
    all_names = [c['name'] for c in all_champs]

    roles = ["Top", "Jungle", "Mid", "ADC", "Support"]
    
    # Session state başlangıcı
    defaults = {
        'bans': [],
        'enemy_roles': {r: "" for r in roles},
        'ally_roles': {r: "" for r in roles},
        'your_role': 'Top',        # varsayılan bir rol seçilsin, "Any" değil
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

    # ---------- Rol seçimi (Kendin) ----------
    st.subheader("🎯 Senin Rolün")
    your_role = st.selectbox("Hangi koridorda oynuyorsun?", roles, key="your_role")
    st.session_state.your_role = your_role

    # ---------- Düşman Takımı ----------
    st.subheader("👾 Düşman Takımı (Rollere göre)")
    enemy_cols = st.columns(5)
    enemy_picks = []
    for idx, role in enumerate(roles):
        with enemy_cols[idx]:
            taken = set(st.session_state.bans + enemy_picks + list(st.session_state.ally_roles.values()))
            available = [""] + [n for n in all_names if n not in taken]
            current = st.session_state.enemy_roles[role]
            if current and current not in available:
                current = ""
            choice = st.selectbox(
                f"Düşman {role}",
                available,
                index=available.index(current) if current in available else 0,
                key=f"enemy_{role}"
            )
            st.session_state.enemy_roles[role] = choice
            if choice:
                enemy_picks.append(choice)

    # ---------- Dost Takımı (Sen hariç diğerleri) ----------
    st.subheader("🛡️ Kendi Takımın (Diğer roller)")
    # Senin rolün dışındaki 4 rolü göster
    ally_roles_to_show = [r for r in roles if r != your_role]
    ally_cols = st.columns(4)
    ally_picks = []
    for idx, role in enumerate(ally_roles_to_show):
        with ally_cols[idx]:
            taken = set(st.session_state.bans + enemy_picks + ally_picks + list(st.session_state.enemy_roles.values()))
            available = [""] + [n for n in all_names if n not in taken]
            current = st.session_state.ally_roles.get(role, "")
            if current and current not in available:
                current = ""
            choice = st.selectbox(
                f"Dost {role}",
                available,
                index=available.index(current) if current in available else 0,
                key=f"ally_{role}"
            )
            st.session_state.ally_roles[role] = choice
            if choice:
                ally_picks.append(choice)

    # ---------- Havuz ve ML seçenekleri ----------
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
        # Geçerli seçim kontrolü
        if len(enemy_picks) != 5:
            st.error("Düşman takımında tüm roller seçilmelidir!")
            return

        if not enemy_picks or len(ally_picks) > 4:
            st.error("Geçersiz seçim.")
            return

        enemy_data = [next(c for c in all_champs if c['name'] == name) for name in enemy_picks]
        ally_data = [next(c for c in all_champs if c['name'] == name) for name in ally_picks]
        excluded_names = set(st.session_state.bans + enemy_picks + ally_picks)

        # Zayıflık analizi
        weaknesses = TeamAnalyzer.analyze_enemy_weaknesses(enemy_data)

        # Aday havuzunu oluştur
        if use_pool and st.session_state.pool:
            candidates = [c for c in all_champs if c['name'] in st.session_state.pool and c['name'] not in excluded_names]
        else:
            candidates = [c for c in all_champs if c['name'] not in excluded_names]

        # Rol filtresi (kullanıcının kendi rolü)
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
        try:
            top3 = TeamAnalyzer.get_top_picks(candidates, weaknesses, ally_data,
                                              use_ml=st.session_state.use_ml, enemy_champs=enemy_data)
        except Exception as e:
            logger.error(f"Öneri hesaplanırken hata: {e}")
            st.error("Öneriler oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.")
            return

        # Görsel öneri kartları
        st.subheader("🏆 En İyi 3 Öneri")
        cols = st.columns(len(top3))
        for i, (champ, score) in enumerate(top3):
            with cols[i]:
                role_emoji = {"Top":"🛡️","Jungle":"🌳","Mid":"🔥","ADC":"🏹","Support":"💚"}.get(champ['role'],"❓")
                st.markdown(f"### {role_emoji} {champ['name']}")
                st.metric("Puan", f"{score:.1f}")
                # Basit nedenler
                reasons = []
                # (Nedenleri daha detaylı ekleyebilirsin)
                st.caption("Uyumlu seçim")

        # Geri bildirim butonları
        st.subheader("Geri Bildirim")
        fb_cols = st.columns(len(top3))
        user = st.session_state.user
        for i, (champ, _) in enumerate(top3):
            with fb_cols[i]:
                col_like, col_dislike = st.columns(2)
                with col_like:
                    if st.button("👍", key=f"like_{i}"):
                        save_feedback(user['id'], champ['name'], 1)
                        st.success("Teşekkürler!")
                with col_dislike:
                    if st.button("👎", key=f"dislike_{i}"):
                        save_feedback(user['id'], champ['name'], -1)
                        st.info("Geri bildirim alındı.")

        # Kullanım hakkını düş
        if not user['is_pro']:
            AuthService.increment_usage(user['id'])
            logger.info(f"Kullanıcı {user['username']} analiz yaptı.")

if __name__ == "__main__":
    main()
