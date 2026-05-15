import streamlit as st
from db_utils import init_db, seed_champions
from logger_config import logger
from auth_service import AuthService

st.set_page_config(page_title="LoL Pick Öneri", page_icon="🎮", layout="centered")

# CSS
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_db()
seed_champions()
logger.info("Uygulama başlatıldı.")

if 'user' not in st.session_state:
    st.session_state.user = None

st.title("LoL Takım Sinerji Pick Öneri Aracı")

if st.session_state.user is None:
    st.subheader("Giriş Yap")
    with st.form("login"):
        username = st.text_input("Kullanıcı adı")
        login_btn = st.form_submit_button("Giriş / Kayıt")
        if login_btn and username:
            user = AuthService.get_user(username)
            if user is None:
                AuthService.create_user(username)
                user = AuthService.get_user(username)
            if AuthService.is_admin(username):
                user['is_pro'] = 1
            st.session_state.user = user
            logger.info(f"Kullanıcı giriş yaptı: {username} (Pro: {user['is_pro']})")
            st.rerun()
else:
    st.success(f"Hoş geldin, **{st.session_state.user['username']}**!")
    if st.session_state.user['is_pro'] or AuthService.is_admin(st.session_state.user['username']):
        st.info("👑 Admin/Pro üye – sınırsız analiz hakkına sahipsin.")
    else:
        st.info("Ücretsiz üye – günlük 5 analiz hakkın var.")
    if st.button("Çıkış"):
        st.session_state.user = None
        st.rerun()

st.markdown("---")
st.markdown("""
### Nasıl Çalışır?
1. Banları gir (isteğe bağlı)
2. Kendi rolünü seç
3. Düşman takımını rollerine göre belirle
4. Kendi takımındaki diğer şampiyonları rollerine göre seç
5. İstersen havuzunu daralt, makine öğrenmesi seçeneğini aç
6. **Analiz Et** butonuna tıkla, en iyi 3 öneriyi gör!
""")
