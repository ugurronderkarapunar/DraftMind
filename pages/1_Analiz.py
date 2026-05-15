import streamlit as st
import plotly.graph_objects as go
import time
from champion_repository import repo
from auth_service import require_auth, require_pro_or_limit, AuthService
from pick_service import TeamAnalyzer
from db_utils import save_feedback
from logger_config import logger
from riot_api_client import get_champion_square
from openai_service import generate_pick_reason, generate_win_strategy


def radar_chart(enemy_data):
    """Düşman takımın istatistik radar grafiğini oluşturur."""
    categories = ['Erken Güç', 'Geç Güç', 'CC', 'Tanklık', 'Mobilite', 'Burst']
    values = [
        sum(c['early_power'] for c in enemy_data) / 5,
        sum(c['late_power'] for c in enemy_data) / 5,
        sum(c['cc_level'] for c in enemy_data) / 5,
        sum(c['tankiness'] for c in enemy_data) / 5,
        sum(c['mobility'] for c in enemy_data) / 5,
        sum(c['burst'] for c in enemy_data) / 5,
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Düşman Takım',
            line_color='#C89B3C',
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#F0E6D2'),
    )
    return fig


@require_auth
@require_pro_or_limit
def main():
    st.title("🏆 LoL Akıllı Takım Analizörü")

    all_champs = repo.get_all()
    all_names = [c['name'] for c in all_champs]
    roles = ["Top", "Jungle", "Mid", "ADC", "Support"]

    # Session state
    defaults = {
        'bans': [],
        'enemy_roles': {r: "" for r in roles},
        'ally_roles': {r: "" for r in roles},
        'your_role': 'Top',
        'use_pool': False,
        'pool': [],
        'use_ml': False,
        'use_ai': True,  # Varsayılan AI açık
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ========== ÜST BAR ==========
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown("### 🎯 Kendi Rolün")
            your_role = st.selectbox(
                "",
                roles,
                key="your_role",
                label_visibility="collapsed",
            )
        with col2:
            st.markdown("### 🧠 Zeka Modu")
            use_ai = st.toggle(
                "AI Açıklamalar",
                value=st.session_state.use_ai,
                help="Yapay zeka ile neden analizi",
            )
            st.session_state.use_ai = use_ai
        with col3:
            st.markdown("### 📊 Radar")
            show_radar = st.toggle("Grafik Göster", value=True)

    # ========== BANLAR ==========
    with st.expander("🔨 BANLAR (İsteğe bağlı)", expanded=False):
        ban_count = st.number_input("Kaç ban?", 0, 10, 0, key="ban_count")
        ban_names = []
        ban_cols = st.columns(min(ban_count, 5))
        for i in range(ban_count):
            with ban_cols[i % 5]:
                ban = st.selectbox(f"Ban {i+1}", [""] + all_names, key=f"ban_{i}")
                if ban:
                    ban_names.append(ban)
        st.session_state.bans = ban_names

    # ========== DÜŞMAN TAKIMI ==========
    st.markdown("---")
    st.subheader("👾 Düşman Takımı")
    enemy_cols = st.columns(5)
    enemy_picks = []
    for idx, role in enumerate(roles):
        with enemy_cols[idx]:
            st.markdown(
                f"<p style='color:#C89B3C; text-align:center;'>{role}</p>",
                unsafe_allow_html=True,
            )
            taken = set(
                st.session_state.bans
                + enemy_picks
                + list(st.session_state.ally_roles.values())
            )
            available = [""] + [n for n in all_names if n not in taken]
            current = st.session_state.enemy_roles[role]
            choice = st.selectbox(
                f" ",
                available,
                index=available.index(current) if current in available else 0,
                key=f"enemy_{role}",
                label_visibility="collapsed",
            )
            st.session_state.enemy_roles[role] = choice
            if choice:
                st.image(get_champion_square(choice), width=60)
                enemy_picks.append(choice)

    # ========== DOST TAKIMI ==========
    st.markdown("---")
    st.subheader("🛡️ Kendi Takımın")
    ally_roles_to_show = [r for r in roles if r != your_role]
    ally_cols = st.columns(4)
    ally_picks = []
    for idx, role in enumerate(ally_roles_to_show):
        with ally_cols[idx]:
            st.markdown(
                f"<p style='color:#C89B3C; text-align:center;'>{role}</p>",
                unsafe_allow_html=True,
            )
            taken = set(
                st.session_state.bans
                + enemy_picks
                + ally_picks
                + list(st.session_state.enemy_roles.values())
            )
            available = [""] + [n for n in all_names if n not in taken]
            current = st.session_state.ally_roles.get(role, "")
            choice = st.selectbox(
                f"  ",
                available,
                index=available.index(current) if current in available else 0,
                key=f"ally_{role}",
                label_visibility="collapsed",
            )
            st.session_state.ally_roles[role] = choice
            if choice:
                st.image(get_champion_square(choice), width=60)
                ally_picks.append(choice)

    # ========== HAVUZ & ANALİZ ==========
    col_pool, col_ml, _ = st.columns([2, 1, 1])
    with col_pool:
        use_pool = st.checkbox("🎯 Havuzu daralt", value=st.session_state.use_pool)
        st.session_state.use_pool = use_pool
    with col_ml:
        use_ml = st.checkbox("🤖 ML model", value=st.session_state.use_ml)
        st.session_state.use_ml = use_ml

    if use_pool:
        taken_pool = set(st.session_state.bans + enemy_picks + ally_picks)
        pool_available = [n for n in all_names if n not in taken_pool]
        pool = st.multiselect(
            "Havuzun", pool_available, default=st.session_state.pool
        )
        st.session_state.pool = pool

    # ========== ANALİZ BUTONU ==========
    if st.button("🚀 ANALİZ ET", type="primary", use_container_width=True):
        if len(enemy_picks) != 5:
            st.error("Tüm düşman rolleri seçilmeli!")
            return

        with st.spinner("🔮 Yapay zeka analiz yapıyor..."):
            time.sleep(0.8)

            enemy_data = [
                next(c for c in all_champs if c['name'] == name)
                for name in enemy_picks
            ]
            ally_data = [
                next(c for c in all_champs if c['name'] == name)
                for name in ally_picks
            ]
            excluded_names = set(st.session_state.bans + enemy_picks + ally_picks)

            weaknesses = TeamAnalyzer.analyze_enemy_weaknesses(enemy_data)

            if use_pool and st.session_state.pool:
                candidates = [
                    c
                    for c in all_champs
                    if c['name'] in st.session_state.pool
                    and c['name'] not in excluded_names
                ]
            else:
                candidates = [
                    c
                    for c in all_champs
                    if c['name'] not in excluded_names
                ]
            candidates = [c for c in candidates if c['role'] == your_role]

            if not candidates:
                st.warning("Uygun şampiyon kalmadı.")
                return

            top3 = TeamAnalyzer.get_top_picks(
                candidates,
                weaknesses,
                ally_data,
                use_ml=use_ml,
                enemy_champs=enemy_data,
            )

        st.balloons()

        # ========== RADAR & ZAYIFLIKLAR ==========
        if show_radar:
            st.plotly_chart(radar_chart(enemy_data), use_container_width=True)

        st.markdown("### ⚡ Tespit Edilen Zayıflıklar")
        weak_cols = st.columns(len(weaknesses) if weaknesses else 1)
        for i, (_, desc) in enumerate(weaknesses):
            with weak_cols[i]:
                st.error(f"**{desc}**")

        # ========== ÖNERİ KARTLARI ==========
        st.markdown("---")
        st.markdown("## 🏆 En İyi 3 Seçim")

        card_cols = st.columns(3)
        user = st.session_state.user

        for i, (champ, score) in enumerate(top3):
            with card_cols[i]:
                # Kart
                portrait = get_champion_square(champ['name'])
                st.markdown(
                    f"""
                <div class="champion-card">
                    <img src="{portrait}" width="110" style="border-radius: 50%; border: 3px solid #C89B3C;">
                    <div class="champion-name">{champ['name']}</div>
                    <span class="role-badge">{champ['role']}</span>
                    <div class="metric-value">{score:.1f}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Yapay zeka açıklaması
                if use_ai:
                    with st.spinner("🧠 AI analiz ediyor..."):
                        reason = generate_pick_reason(
                            champ['name'], enemy_data, ally_data, weaknesses
                        )
                    st.info(f"**Neden?** {reason}")
                else:
                    st.caption("Detaylı analiz için AI modunu açın.")

                # Geri bildirim
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👍 Faydalı", key=f"like_{i}"):
                        save_feedback(user['id'], champ['name'], 1)
                with c2:
                    if st.button("👎 Değil", key=f"dislike_{i}"):
                        save_feedback(user['id'], champ['name'], -1)

        # ========== KAZANMA STRATEJİSİ ==========
        st.markdown("---")
        st.markdown("## 🎯 Kazanma Stratejisi")

        if use_ai:
            with st.spinner("🧠 Savaş planı hazırlanıyor..."):
                strategy = generate_win_strategy(enemy_data, ally_data)
            st.markdown(
                f"""
            <div class="strategy-box">
                {strategy}
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Strateji önerisi için AI modunu aktif edin.")

        # Kullanım hakkı
        if not user['is_pro']:
            AuthService.increment_usage(user['id'], user['username'])


if __name__ == "__main__":
    main()
