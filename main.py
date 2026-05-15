import streamlit as st
from db_utils import init_db, seed_champions
from logger_config import logger
from auth_service import AuthService

st.set_page_config(page_title="LoL Pick Öneri", page_icon="🎮", layout="centered")

init_db()
seed_champions()
logger.info("Uygulama başlatıldı.")

if 'user' not in st.session_state:
    st.session_state.user = None

st.title("LoL Takım Sinerji Pick Öneri Aracı")

if st.session_state.user is None:
    with st.form("login"):
        username = st.text_input("Kullanıcı adı")
        if st.form_submit_button("Giriş / Kayıt") and username:
            user = AuthService.get_user(username)
            if not user:
                AuthService.create_user(username)
                user = AuthService.get_user(username)
            st.session_state.user = user
            logger.info(f"Kullanıcı giriş yaptı: {username}")
            st.rerun()
else:
    st.success(f"Hoş geldin, **{st.session_state.user['username']}**!")
    if st.button("Çıkış"):
        st.session_state.user = None
        st.rerun()
st.markdown("---")
st.markdown("""
### Nasıl Çalışır?
1. Banları gir (isteğe bağlı)
2. Düşman takımını rollerine göre seç
3. Kendi takımındaki diğer şampiyonları rollerine göre seç
4. Kendi rolünü belirle, havuzunu daralt, ML seçeneğini aktif et
5. Analiz et, en iyi 3 pick'i gör ve geri bildirim ver.
""")
