import streamlit as st
from db_utils import init_db, seed_champions, get_user, create_user

st.set_page_config(page_title="LoL Takım Pick Öneri", layout="centered")

# Veritabanını ve örnek verileri her açılışta kontrol et
init_db()
seed_champions()

# Session state
if 'user' not in st.session_state:
    st.session_state.user = None

st.title("LoL Takım Sinerji Pick Öneri Aracı")

if st.session_state.user is None:
    st.subheader("Giriş Yap")
    with st.form("login"):
        username = st.text_input("Kullanıcı adı")
        login_btn = st.form_submit_button("Giriş / Kayıt")
        if login_btn and username:
            user = get_user(username)
            if user is None:
                create_user(username)
                user = get_user(username)
            st.session_state.user = user
            st.rerun()
else:
    st.success(f"Hoş geldin, **{st.session_state.user['username']}**!")
    if st.session_state.user['is_pro']:
        st.info("Pro üye – sınırsız analiz hakkın var.")
    else:
        st.info("Ücretsiz üye – günlük 5 analiz hakkın var.")
    if st.button("Çıkış"):
        st.session_state.user = None
        st.rerun()

st.markdown("---")
st.markdown("""
### Nasıl Çalışır?
1. Düşman takımının seçtiği 5 şampiyonu ve kendi takımında kesinleşmiş şampiyonları gir.
2. İstersen sadece kendi oynadığın şampiyon havuzunu seç.
3. Uygulama, düşman takımın zayıf yönlerini analiz eder ve en uygun 3 pick’i önerir.
""")
