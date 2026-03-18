import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from dateutil.relativedelta import relativedelta

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fakturnik",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --cream: #F7F3EE;
    --ink: #1A1714;
    --rust: #C4501A;
    --sage: #4A6741;
    --amber: #D4860A;
    --muted: #8C8480;
    --border: #DDD8D2;
    --card: #FFFFFF;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--cream) !important;
    color: var(--ink);
}

.main { background-color: var(--cream) !important; }
.block-container { padding-top: 2rem; max-width: 1200px; }

/* Header */
.fakturnik-header {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 0.25rem;
}
.fakturnik-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.8rem;
    color: var(--ink);
    letter-spacing: -0.02em;
    line-height: 1;
}
.fakturnik-subtitle {
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
}

/* Metric cards */
.metric-row { display: flex; gap: 16px; margin: 1.5rem 0; flex-wrap: wrap; }
.metric-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    flex: 1;
    min-width: 160px;
}
.metric-card.danger { border-left: 4px solid var(--rust); }
.metric-card.warning { border-left: 4px solid var(--amber); }
.metric-card.ok { border-left: 4px solid var(--sage); }
.metric-label {
    font-size: 0.72rem;
    font-family: 'DM Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 4px;
}
.metric-value {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: var(--ink);
    line-height: 1;
}
.metric-value.danger { color: var(--rust); }
.metric-value.warning { color: var(--amber); }
.metric-value.ok { color: var(--sage); }

/* Table styling */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* Status badges */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-family: 'DM Mono', monospace;
    font-weight: 500;
}
.badge-ok { background: #E8F0E6; color: var(--sage); }
.badge-warn { background: #FDF2DC; color: var(--amber); }
.badge-danger { background: #FAE8E0; color: var(--rust); }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--ink) !important;
}
section[data-testid="stSidebar"] * {
    color: var(--cream) !important;
}
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stSelectbox select {
    background: #2A2520 !important;
    border-color: #3A3530 !important;
    color: var(--cream) !important;
}

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

/* Alert box */
.alert-box {
    background: #FAE8E0;
    border: 1px solid #E8C4B0;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
}
.alert-box strong { color: var(--rust); }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def connect_to_sheet(creds_info: dict, sheet_url: str):
    """Connect to Google Sheets and return the first worksheet."""
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url)
    return sheet.sheet1


def load_data(worksheet) -> pd.DataFrame:
    """Load data from worksheet and return DataFrame."""
    records = worksheet.get_all_records()
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    # Normalize column names
    df.columns = [c.strip() for c in df.columns]
    return df


def compute_status(row, today: date) -> tuple[str, int]:
    """Return (status_label, days_until_due) for a client row."""
    try:
        interval_months = int(row.get("Cykl_miesiecy", 1))
        last_raw = row.get("Ostatnia_faktura", "")
        if not last_raw:
            return "BRAK DANYCH", 0

        last_date = pd.to_datetime(last_raw, dayfirst=True).date()
        next_date = last_date + relativedelta(months=interval_months)
        days_left = (next_date - today).days

        if days_left < 0:
            return "PRZETERMINOWANA", days_left
        elif days_left <= 7:
            return "PILNE", days_left
        elif days_left <= 14:
            return "WKRÓTCE", days_left
        else:
            return "OK", days_left
    except Exception:
        return "BRAK DANYCH", 0


def send_reminder_email(smtp_cfg: dict, recipient: str, subject: str, body: str) -> bool:
    """Send an email reminder. Returns True on success."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_cfg["sender"]
        msg["To"] = recipient
        msg.attach(MIMEText(body, "html", "utf-8"))

        with smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["port"]) as server:
            server.login(smtp_cfg["sender"], smtp_cfg["password"])
            server.sendmail(smtp_cfg["sender"], recipient, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Błąd wysyłki e-mail: {e}")
        return False


def build_email_body(overdue: pd.DataFrame, urgent: pd.DataFrame, period_label: str) -> str:
    def rows_html(df):
        if df.empty:
            return "<p><em>Brak</em></p>"
        rows = ""
        for _, r in df.iterrows():
            days = r["Dni_do_faktury"]
            color = "#C4501A" if days < 0 else "#D4860A"
            days_txt = f"{abs(days)} dni po terminie" if days < 0 else f"za {days} dni"
            rows += f"""
            <tr>
              <td style="padding:8px 12px;border-bottom:1px solid #eee;">{r.get('Klient','—')}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #eee;">{r.get('NIP','—')}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #eee;">{r.get('Kwota_PLN','—')} PLN</td>
              <td style="padding:8px 12px;border-bottom:1px solid #eee;color:{color};font-weight:600;">{days_txt}</td>
            </tr>"""
        return f"<table style='border-collapse:collapse;width:100%;font-family:sans-serif;font-size:14px;'><tr style='background:#f5f5f5;'><th style='padding:8px 12px;text-align:left;'>Klient</th><th style='padding:8px 12px;text-align:left;'>NIP</th><th style='padding:8px 12px;text-align:left;'>Kwota</th><th style='padding:8px 12px;text-align:left;'>Status</th></tr>{rows}</table>"

    return f"""
    <div style="font-family:'Helvetica Neue',sans-serif;max-width:640px;margin:0 auto;color:#1A1714;">
      <div style="background:#1A1714;padding:28px 32px;border-radius:12px 12px 0 0;">
        <h1 style="color:#F7F3EE;font-size:1.5rem;margin:0;letter-spacing:-0.02em;">🧾 Fakturnik – Przypomnienie</h1>
        <p style="color:#8C8480;margin:4px 0 0;font-size:0.85rem;">{period_label}</p>
      </div>
      <div style="background:#fff;padding:28px 32px;border-radius:0 0 12px 12px;border:1px solid #DDD8D2;border-top:none;">

        <h2 style="color:#C4501A;font-size:1rem;margin-top:0;">⚠️ Przeterminowane faktury</h2>
        {rows_html(overdue)}

        <h2 style="color:#D4860A;font-size:1rem;margin-top:24px;">⏰ Pilne – do wystawienia w ciągu 7 dni</h2>
        {rows_html(urgent)}

        <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
        <p style="color:#8C8480;font-size:0.8rem;margin:0;">
          Wiadomość wygenerowana automatycznie przez Fakturnik.<br>
          Sprawdź arkusz Google Sheets, aby zobaczyć pełną listę klientów.
        </p>
      </div>
    </div>
    """


# ── Session state ──────────────────────────────────────────────────────────────
if "worksheet" not in st.session_state:
    st.session_state.worksheet = None
if "df" not in st.session_state:
    st.session_state.df = None
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None


# ── Sidebar – konfiguracja ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Konfiguracja")
    st.markdown("---")

    st.markdown("**Google Sheets**")
    sheet_url = st.text_input(
        "URL arkusza",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        help="Wklej link do arkusza Google Sheets"
    )

    creds_file = st.file_uploader(
        "Klucz Service Account (JSON)",
        type=["json"],
        help="Pobierz z Google Cloud Console → IAM → Service Accounts"
    )

    st.markdown("---")
    st.markdown("**Powiadomienia e-mail (SMTP)**")
    smtp_host = st.text_input("Serwer SMTP", value="smtp.gmail.com")
    smtp_port = st.number_input("Port", value=465, step=1)
    smtp_sender = st.text_input("Adres nadawcy")
    smtp_password = st.text_input("Hasło / App Password", type="password")
    recipients_raw = st.text_area(
        "Odbiorcy (jeden adres na linię)",
        placeholder="kowalska@firma.pl\nnowak@firma.pl"
    )

    st.markdown("---")
    if st.button("🔗 Połącz z arkuszem", use_container_width=True):
        if not sheet_url or not creds_file:
            st.error("Podaj URL arkusza i klucz JSON.")
        else:
            try:
                creds_info = json.load(creds_file)
                ws = connect_to_sheet(creds_info, sheet_url)
                st.session_state.worksheet = ws
                st.session_state.df = load_data(ws)
                st.session_state.last_refresh = datetime.now()
                st.success("✅ Połączono!")
            except Exception as e:
                st.error(f"Błąd połączenia: {e}")

    if st.session_state.worksheet:
        if st.button("🔄 Odśwież dane", use_container_width=True):
            st.session_state.df = load_data(st.session_state.worksheet)
            st.session_state.last_refresh = datetime.now()
            st.success("Dane odświeżone.")


# ── Main content ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="fakturnik-header">
  <span class="fakturnik-title">Fakturnik</span>
  <span class="fakturnik-subtitle">system przypomnień fakturowych</span>
</div>
""", unsafe_allow_html=True)

if st.session_state.last_refresh:
    st.caption(f"Ostatnie odświeżenie: {st.session_state.last_refresh.strftime('%d.%m.%Y %H:%M')}")

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ── No data state ──────────────────────────────────────────────────────────────
if st.session_state.df is None:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Zacznij od połączenia z arkuszem")
        st.markdown("""
        **Jak zacząć:**
        1. Skonfiguruj Service Account w [Google Cloud Console](https://console.cloud.google.com)
        2. Udostępnij arkusz Google Sheets dla adresu e-mail Service Account
        3. Wklej URL arkusza i wgraj klucz JSON po lewej stronie

        **Wymagane kolumny w arkuszu:**

        | Kolumna | Opis | Przykład |
        |---|---|---|
        | `Klient` | Nazwa klienta | ABC Sp. z o.o. |
        | `NIP` | NIP klienta | 123-456-78-90 |
        | `Kwota_PLN` | Kwota faktury | 2500 |
        | `Ostatnia_faktura` | Data ostatniej faktury | 01.01.2025 |
        | `Cykl_miesiecy` | Co ile miesięcy wystawiać | 1 |
        | `Uwagi` | Opcjonalne uwagi | — |
        """)
    with col2:
        st.markdown("### Przykładowy szablon")
        sample = pd.DataFrame({
            "Klient": ["ABC Sp. z o.o.", "XYZ S.A."],
            "NIP": ["123-456-78-90", "987-654-32-10"],
            "Kwota_PLN": [2500, 5000],
            "Ostatnia_faktura": ["01.02.2025", "15.01.2025"],
            "Cykl_miesiecy": [1, 1],
            "Uwagi": ["usługi IT", "abonament"],
        })
        st.dataframe(sample, hide_index=True, use_container_width=True)
        csv = sample.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Pobierz szablon CSV", csv, "szablon_fakturnik.csv", "text/csv")
    st.stop()

# ── Data loaded ────────────────────────────────────────────────────────────────
df = st.session_state.df.copy()
today = date.today()

# Compute statuses
statuses = [compute_status(row, today) for _, row in df.iterrows()]
df["Status"] = [s[0] for s in statuses]
df["Dni_do_faktury"] = [s[1] for s in statuses]

# Segment
overdue = df[df["Status"] == "PRZETERMINOWANA"].copy()
urgent = df[df["Status"] == "PILNE"].copy()
soon = df[df["Status"] == "WKRÓTCE"].copy()
ok = df[df["Status"] == "OK"].copy()

# ── Metric cards ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="metric-row">
  <div class="metric-card danger">
    <div class="metric-label">Przeterminowane</div>
    <div class="metric-value danger">{len(overdue)}</div>
  </div>
  <div class="metric-card warning">
    <div class="metric-label">Pilne (≤7 dni)</div>
    <div class="metric-value warning">{len(urgent)}</div>
  </div>
  <div class="metric-card warning">
    <div class="metric-label">Wkrótce (≤14 dni)</div>
    <div class="metric-value" style="color:var(--amber)">{len(soon)}</div>
  </div>
  <div class="metric-card ok">
    <div class="metric-label">Na bieżąco</div>
    <div class="metric-value ok">{len(ok)}</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Wszystkich klientów</div>
    <div class="metric-value">{len(df)}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Alert for overdue ──────────────────────────────────────────────────────────
if not overdue.empty:
    names = ", ".join(overdue["Klient"].tolist()[:5])
    extra = f" i {len(overdue)-5} więcej" if len(overdue) > 5 else ""
    st.markdown(f"""
    <div class="alert-box">
        <strong>⚠️ Uwaga! {len(overdue)} przeterminowanych faktur:</strong> {names}{extra}
    </div>
    """, unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Wszyscy klienci", "🔔 Wymagają działania", "📧 Wyślij przypomnienia"])

with tab1:
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search = st.text_input("🔍 Szukaj klienta", placeholder="nazwa lub NIP...")
    with col_filter:
        filter_status = st.selectbox("Status", ["Wszystkie", "PRZETERMINOWANA", "PILNE", "WKRÓTCE", "OK"])

    view_df = df.copy()
    if search:
        mask = view_df.apply(lambda r: search.lower() in str(r).lower(), axis=1)
        view_df = view_df[mask]
    if filter_status != "Wszystkie":
        view_df = view_df[view_df["Status"] == filter_status]

    # Color-coded status column
    def style_status(val):
        colors = {
            "PRZETERMINOWANA": "background-color:#FAE8E0;color:#C4501A;font-weight:600;",
            "PILNE": "background-color:#FDF2DC;color:#D4860A;font-weight:600;",
            "WKRÓTCE": "background-color:#FDF2DC;color:#D4860A;",
            "OK": "background-color:#E8F0E6;color:#4A6741;",
        }
        return colors.get(val, "")

    styled = view_df.style.applymap(style_status, subset=["Status"])
    st.dataframe(styled, hide_index=True, use_container_width=True, height=420)

    # Export
    csv_all = view_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Eksportuj widok do CSV", csv_all, f"klienci_{today}.csv", "text/csv")


with tab2:
    if overdue.empty and urgent.empty:
        st.success("✅ Wszystkie faktury są na bieżąco! Żadna nie wymaga pilnego działania.")
    else:
        if not overdue.empty:
            st.markdown("#### ⛔ Przeterminowane")
            st.dataframe(
                overdue[["Klient", "NIP", "Kwota_PLN", "Ostatnia_faktura", "Dni_do_faktury", "Uwagi"]],
                hide_index=True, use_container_width=True
            )
        if not urgent.empty:
            st.markdown("#### ⏰ Pilne – wystaw w ciągu 7 dni")
            st.dataframe(
                urgent[["Klient", "NIP", "Kwota_PLN", "Ostatnia_faktura", "Dni_do_faktury", "Uwagi"]],
                hide_index=True, use_container_width=True
            )
        if not soon.empty:
            st.markdown("#### 📅 Wkrótce – za 8–14 dni")
            st.dataframe(
                soon[["Klient", "NIP", "Kwota_PLN", "Ostatnia_faktura", "Dni_do_faktury", "Uwagi"]],
                hide_index=True, use_container_width=True
            )


with tab3:
    st.markdown("### Wyślij e-mail z przypomnieniami do współpracowników")

    n_issues = len(overdue) + len(urgent)
    if n_issues == 0:
        st.info("ℹ️ Brak przeterminowanych ani pilnych faktur – nie ma o czym przypominać.")
    else:
        st.markdown(f"E-mail będzie zawierał listę **{len(overdue)} przeterminowanych** i **{len(urgent)} pilnych** faktur.")

        recipients_list = [r.strip() for r in recipients_raw.strip().splitlines() if r.strip()] if recipients_raw else []

        col_a, col_b = st.columns(2)
        with col_a:
            custom_subject = st.text_input(
                "Temat wiadomości",
                value=f"[Fakturnik] Przypomnienie – {today.strftime('%B %Y')} · {n_issues} faktur wymaga uwagi"
            )
        with col_b:
            st.markdown(f"**Odbiorcy ({len(recipients_list)}):**")
            if recipients_list:
                for r in recipients_list:
                    st.markdown(f"• `{r}`")
            else:
                st.warning("Dodaj odbiorców w ustawieniach po lewej.")

        if st.button("📧 Wyślij teraz", type="primary", disabled=(not recipients_list or not smtp_sender)):
            smtp_cfg = {
                "host": smtp_host,
                "port": int(smtp_port),
                "sender": smtp_sender,
                "password": smtp_password,
            }
            body = build_email_body(overdue, urgent, today.strftime("%d.%m.%Y"))
            sent, failed = 0, 0
            with st.spinner("Wysyłam..."):
                for addr in recipients_list:
                    ok_flag = send_reminder_email(smtp_cfg, addr, custom_subject, body)
                    if ok_flag:
                        sent += 1
                    else:
                        failed += 1
            if sent:
                st.success(f"✅ Wysłano do {sent} odbiorców.")
            if failed:
                st.error(f"❌ Nie udało się wysłać do {failed} odbiorców. Sprawdź ustawienia SMTP.")

        with st.expander("👁️ Podgląd e-maila"):
            preview_body = build_email_body(overdue, urgent, today.strftime("%d.%m.%Y"))
            st.components.v1.html(preview_body, height=500, scrolling=True)
