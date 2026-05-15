import streamlit as st
from db_utils import set_pro, generate_personal_key

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("Lütfen giriş yapın.")
    st.stop()

st.title("Pro Üyelik")

user = st.session_state.user
if user['is_pro']:
    st.success("Zaten Pro üyesisiniz. Sınırsız analiz kullanabilirsiniz.")
else:
    st.write("Pro üyelik ile günlük limitsiz analiz ve öncelikli özelliklere erişim sağlayın.")

    tab1, tab2 = st.tabs(["Aktivasyon Kodu", "Kişisel Anahtar Üret"])

    with tab1:
        st.subheader("Hazır Aktivasyon Kodu")
        code = st.text_input("Pro Kodu", type="password")
        if st.button("Yükselt"):
            # Statik kod veya kullanıcıya özel anahtar kontrolü
            if code == "PRO2026" or code == generate_personal_key(user['username']):
                set_pro(user['username'])
                st.session_state.user['is_pro'] = 1
                st.success("Tebrikler, Pro üye oldunuz!")
                st.rerun()
            else:
                st.error("Geçersiz kod.")

    with tab2:
        st.subheader("Kendi Anahtarını Üret")
        st.write("Admin şifresini girerek sana özel bir anahtar oluşturabilirsin.")
        admin_pass = st.text_input("Admin Şifresi", type="password", key="admin")
        if st.button("Anahtar Üret"):
            if admin_pass == "admin123":  # Gerçek projede güvenli hale getirilmeli
                personal_key = generate_personal_key(user['username'])
                st.success(f"Senin özel anahtarın: **{personal_key}**")
                st.info("Bu anahtarı yukarıdaki 'Aktivasyon Kodu' sekmesinde kullanarak Pro olabilirsin.")
            else:
                st.error("Yanlış admin şifresi.")
