import streamlit as st
from datetime import date
from db_utils import get_connection
from logger_config import logger
import functools

class AuthService:
    @staticmethod
    def get_user(username):
        conn = get_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        return dict(user) if user else None

    @staticmethod
    def create_user(username):
        conn = get_connection()
        try:
            conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
            conn.commit()
            logger.info(f"Yeni kullanıcı oluşturuldu: {username}")
        except Exception as e:
            logger.error(f"Kullanıcı oluşturulamadı: {e}")
        finally:
            conn.close()

    @staticmethod
    def check_daily_limit(user_id):
        today = date.today().isoformat()
        conn = get_connection()
        row = conn.execute("SELECT count FROM usage WHERE user_id = ? AND analysis_date = ?", (user_id, today)).fetchone()
        conn.close()
        return row['count'] if row else 0

    @staticmethod
    def increment_usage(user_id):
        today = date.today().isoformat()
        conn = get_connection()
        conn.execute(
            "INSERT INTO usage (user_id, analysis_date, count) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, analysis_date) DO UPDATE SET count = count + 1",
            (user_id, today))
        conn.commit()
        conn.close()
        logger.debug(f"Kullanıcı {user_id} için analiz hakkı artırıldı.")

    @staticmethod
    def set_pro(username):
        conn = get_connection()
        conn.execute("UPDATE users SET is_pro = 1 WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        logger.info(f"{username} Pro üye oldu.")

# Yetkilendirme dekoratörü
def require_auth(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' not in st.session_state or st.session_state.user is None:
            st.warning("Lütfen ana sayfadan giriş yap.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def require_pro_or_limit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = st.session_state.user
        if not user['is_pro']:
            daily = AuthService.check_daily_limit(user['id'])
            if daily >= 5:
                st.error("Günlük ücretsiz analiz hakkınız doldu. Pro üye olun veya yarın tekrar deneyin.")
                st.stop()
            else:
                st.info(f"Bugün {daily}/5 analiz kullanıldı.")
        return func(*args, **kwargs)
    return wrapper
