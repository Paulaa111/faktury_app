import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
from dateutil.relativedelta import relativedelta
import json

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Faktury – panel",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg: #0F0F0F;
    --surface: #1A1A1A;
    --surface2: #222222;
    --border: #2E2E2E;
    --text: #F0EDE8;
    --muted: #6B6660;
    --gold: #C9A84C;
    --gold-dim: #8A6E30;
    --green: #4CAF7D;
    --red: #E05252;
    --amber: #E09A2E;
}
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
.main, .block-container { background-color: var(--bg) !important; }
.block-container { padding: 2rem 2.5rem; max-width: 1100px; }

.page-header { border-bottom: 1px solid var(--border); padding-bottom: 1.25rem; margin-bottom: 2rem; }
.page-title { font-family: 'Playfair Display', serif; font-size: 2.2rem; color: var(--gold); letter-spacing: -0.01em; margin: 0; line-height: 1; }
.page-meta { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--muted); margin-top: 6px; text-transform: uppercase; letter-spacing: 0.1em; }

.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 2rem; }
.summary-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem 1.5rem; }
.summary-card.highlight { border-color: var(--gold-dim); }
.card-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }
.card-value { font-family: 'Playfair Display', serif; font-size: 1.9rem; color: var(--text); line-height: 1; }
.card-value.gold { color: var(--gold); }

.invoice-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.invoice-table th { font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); text-align: left; padding: 8px 14px; border-bottom: 1px solid var(--border); }
.invoice-table td { padding: 13px 14px; border-bottom: 1px solid var(--border); color: var(--text); vertical-align: middle; }
.invoice-table tr:hover td { background: var(--surface2); }
.invoice-table tr:last-child td { border-bottom: none; }
.klient-name { font-weight: 500; font-size: 0.95rem; }
.kwota { font-family: 'IBM Plex Mono', monospace; font-weight: 500; color: var(--gold); }
.uwagi-cell { font-size: 0.82rem; color: var(--muted); font-style: italic; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 100px; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; }
.badge-now  { background: #2A1F0A; color: var(--amber); border: 1px solid #5A3F10; }
.badge-ok   { background: #0F2018; color: var(--green); border: 1px solid #1A4030; }
.badge-late { background: #2A0F0F; color: var(--red);   border: 1px solid #5A1010; }

.section-title { font-family: 'Playfair Display', serif; font-size: 1.2rem; color: var(--text); margin: 0 0 1rem 0; }
.section-sub { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--muted); margin-top: -0.75rem; margin-bottom: 1.25rem; text-transform: uppercase; letter-spacing: 0.08em; }

.stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea {
    background: var(--surface2) !important; border: 1px solid var(--border) !important;
    color: var(--text) !important; border-radius: 8px !important; font-family: 'IBM Plex Sans', sans-serif !important;
}
.stTextInput label, .stNumberInput label, .stSelectbox label, .stTextArea label {
    color: var(--muted) !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important;
}
.stButton > button {
    background: var(--gold) !important; color: #0F0F0F !important; border: none !important;
    border-radius: 8px !important; font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 600 !important; padding: 0.5rem 1.5rem !important;
}
.stButton > button:hover { background: #E0BC6A !important; }
div[data-testid="stTabs"] button { font-family: 'IBM Plex Mono', monospace !important; font-size: 0.78rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; color: var(--muted) !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: var(--gold) !important; border-bottom-color: var(--gold) !important; }
</style>
""", unsafe_allow_html=True)


# ── Google Sheets connection ───────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUMNS = ["nazwa", "nip", "kwota", "cykl_miesiecy", "ostatnia_faktura", "uwagi"]

@st.cache_resource(ttl=30)
def get_worksheet(sheet_url: str):
    """Connect and return worksheet (cached 30s)."""
    try:
        # Works both locally (uploaded JSON) and on Streamlit Cloud (st.secrets)
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
        else:
            st.error("Brak konfiguracji Google – sprawdź Secrets w Streamlit Cloud.")
            return None

        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        sh = client.open_by_url(sheet_url)
        ws = sh.sheet1

        # Ensure header row exists
        existing = ws.row_values(1)
        if existing != COLUMNS:
            ws.clear()
            ws.append_row(COLUMNS)

        return ws
    except Exception as e:
        st.error(f"Błąd połączenia z arkuszem: {e}")
        return None


def load_clients(ws) -> list[dict]:
    try:
        records = ws.get_all_records()
        return records
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return []


def add_client(ws, klient: dict):
    row = [str(klient.get(col, "")) for col in COLUMNS]
    ws.append_row(row)


def update_client(ws, row_idx: int, klient: dict):
    # row_idx is 0-based in list → sheet row = idx + 2 (1 for header, 1 for 1-based)
    sheet_row = row_idx + 2
    for col_i, col in enumerate(COLUMNS, start=1):
        ws.update_cell(sheet_row, col_i, str(klient.get(col, "")))


def delete_client(ws, row_idx: int):
    sheet_row = row_idx + 2
    ws.delete_rows(sheet_row)


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_status(klient: dict, today: date) -> tuple[str, str]:
    try:
        cykl = int(klient.get("cykl_miesiecy", 1))
        ostatnia = str(klient.get("ostatnia_faktura", "")).strip()
        if not ostatnia:
            return "BRAK DATY", "badge-late"
        last = date.fromisoformat(ostatnia)
        next_date = last + relativedelta(months=cykl)
        days = (next_date - today).days
        if days < 0:
            return f"PO TERMINIE ({abs(days)}d)", "badge-late"
        elif days <= 10:
            return f"ZA {days} DNI", "badge-now"
        else:
            return f"ZA {days} DNI", "badge-ok"
    except Exception:
        return "BŁĄD DATY", "badge-late"


def should_invoice_now(klient: dict, today: date) -> bool:
    try:
        cykl = int(klient.get("cykl_miesiecy", 1))
        ostatnia = str(klient.get("ostatnia_faktura", "")).strip()
        if not ostatnia:
            return True
        last = date.fromisoformat(ostatnia)
        next_date = last + relativedelta(months=cykl)
        return (next_date - today).days <= 10
    except Exception:
        return False


def render_table(clients_list: list, today: date):
    rows_html = ""
    for c in sorted(clients_list, key=lambda x: float(x.get("kwota", 0) or 0), reverse=True):
        label, cls = get_status(c, today)
        uwagi = c.get("uwagi", "") or "—"
        try:
            kwota_fmt = f"{float(c.get('kwota', 0)):,.2f}"
        except Exception:
            kwota_fmt = "—"
        rows_html += f"""
        <tr>
            <td><span class="klient-name">{c.get('nazwa','—')}</span></td>
            <td><span class="kwota">{kwota_fmt} PLN</span></td>
            <td>{c.get('nip','—')}</td>
            <td><span class="badge {cls}">{label}</span></td>
            <td><span class="uwagi-cell">{uwagi}</span></td>
        </tr>"""
    st.markdown(f"""
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:2rem;">
        <table class="invoice-table">
            <thead><tr><th>Klient</th><th>Kwota</th><th>NIP</th><th>Status</th><th>Uwagi</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if "role" not in st.session_state:
    st.session_state.role = "szef"
if "sheet_url" not in st.session_state:
    # Try to get from secrets
    st.session_state.sheet_url = st.secrets.get("sheet_url", "")

today = date.today()
miesiac = today.strftime("%B %Y").capitalize()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="page-header">
    <div class="page-title">🧾 Panel fakturowy</div>
    <div class="page-meta">{miesiac}</div>
</div>
""", unsafe_allow_html=True)

# ── Sheet URL input (if not in secrets) ───────────────────────────────────────
if not st.session_state.sheet_url:
    st.warning("Podaj URL arkusza Google Sheets żeby zacząć.")
    url_input = st.text_input("URL arkusza Google Sheets",
                              placeholder="https://docs.google.com/spreadsheets/d/...")
    if url_input:
        st.session_state.sheet_url = url_input
        st.rerun()
    st.stop()

# ── Connect ────────────────────────────────────────────────────────────────────
ws = get_worksheet(st.session_state.sheet_url)
if ws is None:
    st.stop()

clients = load_clients(ws)

# ── Role switcher ──────────────────────────────────────────────────────────────
col_r1, col_r2, col_r3 = st.columns([1, 1, 6])
with col_r1:
    if st.button("👁️ Widok szefa", use_container_width=True,
                 type="primary" if st.session_state.role == "szef" else "secondary"):
        st.session_state.role = "szef"
        st.rerun()
with col_r2:
    if st.button("✏️ Zarządzaj", use_container_width=True,
                 type="primary" if st.session_state.role == "admin" else "secondary"):
        st.session_state.role = "admin"
        st.rerun()

st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# WIDOK SZEFA
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.role == "szef":

    do_wystawienia = [c for c in clients if should_invoice_now(c, today)]
    pozostale      = [c for c in clients if not should_invoice_now(c, today)]

    try:
        suma = sum(float(c.get("kwota", 0) or 0) for c in do_wystawienia)
    except Exception:
        suma = 0.0

    st.markdown(f"""
    <div class="summary-grid">
        <div class="summary-card highlight">
            <div class="card-label">Do wystawienia teraz</div>
            <div class="card-value gold">{len(do_wystawienia)}</div>
        </div>
        <div class="summary-card">
            <div class="card-label">Łączna kwota</div>
            <div class="card-value">{suma:,.0f} <span style="font-size:1rem;color:var(--muted)">PLN</span></div>
        </div>
        <div class="summary-card">
            <div class="card-label">Pozostałe (OK)</div>
            <div class="card-value">{len(pozostale)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Do wystawienia</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Faktury wymagające działania w tym okresie</div>', unsafe_allow_html=True)

    if not do_wystawienia:
        st.success("✅ Wszystkie faktury są aktualne – nie ma nic do wystawienia.")
    else:
        render_table(do_wystawienia, today)

    if pozostale:
        with st.expander(f"📋 Pozostali klienci – {len(pozostale)} (faktura jeszcze nie wymagana)"):
            render_table(pozostale, today)


# ══════════════════════════════════════════════════════════════════════════════
# WIDOK ADMIN
# ══════════════════════════════════════════════════════════════════════════════
else:
    tab1, tab2 = st.tabs(["➕ Dodaj klienta", "📝 Lista i edycja"])

    with tab1:
        st.markdown('<div class="section-title">Nowy klient</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Dane zapisują się automatycznie do arkusza</div>', unsafe_allow_html=True)

        with st.form("dodaj_klienta", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nazwa  = st.text_input("Nazwa klienta *", placeholder="ABC Sp. z o.o.")
                nip    = st.text_input("NIP", placeholder="123-456-78-90")
            with col2:
                kwota  = st.number_input("Kwota faktury (PLN) *", min_value=0.0, step=100.0, format="%.2f")
                cykl   = st.selectbox("Cykl fakturowania", [1, 2, 3, 6, 12],
                                      format_func=lambda x: {1:"Co miesiąc",2:"Co 2 miesiące",
                                                              3:"Co kwartał",6:"Co pół roku",12:"Co rok"}[x])
            ostatnia = st.date_input("Data ostatniej faktury", value=date.today())
            uwagi    = st.text_area("Uwagi (opcjonalne)", placeholder="np. usługi IT, abonament...", height=80)

            submitted = st.form_submit_button("➕ Dodaj klienta", use_container_width=True)
            if submitted:
                if not nazwa:
                    st.error("Podaj nazwę klienta.")
                else:
                    nowy = {
                        "nazwa": nazwa.strip(),
                        "nip": nip.strip(),
                        "kwota": kwota,
                        "cykl_miesiecy": int(cykl),
                        "ostatnia_faktura": ostatnia.isoformat(),
                        "uwagi": uwagi.strip(),
                    }
                    with st.spinner("Zapisuję do arkusza..."):
                        add_client(ws, nowy)
                        get_worksheet.clear()
                    st.success(f"✅ Dodano: **{nazwa}**")
                    st.rerun()

    with tab2:
        st.markdown('<div class="section-title">Wszyscy klienci</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Zmiany zapisują się od razu do arkusza Google Sheets</div>', unsafe_allow_html=True)

        if not clients:
            st.info("Brak klientów. Dodaj pierwszego w zakładce obok.")
        else:
            for i, c in enumerate(clients):
                try:
                    kwota_display = f"{float(c.get('kwota', 0)):,.0f}"
                except Exception:
                    kwota_display = "—"

                with st.expander(f"**{c.get('nazwa','—')}** · {kwota_display} PLN · co {c.get('cykl_miesiecy',1)} mies."):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        new_nazwa  = st.text_input("Nazwa",  value=c.get("nazwa",""),  key=f"n_{i}")
                        new_nip    = st.text_input("NIP",    value=c.get("nip",""),    key=f"nip_{i}")
                        new_uwagi  = st.text_area("Uwagi",   value=c.get("uwagi",""), key=f"u_{i}", height=80)
                    with col_b:
                        try:
                            kwota_val = float(c.get("kwota", 0) or 0)
                        except Exception:
                            kwota_val = 0.0
                        new_kwota = st.number_input("Kwota (PLN)", value=kwota_val,
                                                    step=100.0, format="%.2f", key=f"k_{i}")
                        cykl_options = [1, 2, 3, 6, 12]
                        try:
                            cykl_default = cykl_options.index(int(c.get("cykl_miesiecy", 1)))
                        except Exception:
                            cykl_default = 0
                        new_cykl = st.selectbox("Cykl (mies.)", cykl_options, index=cykl_default, key=f"c_{i}",
                                                format_func=lambda x: {1:"Co miesiąc",2:"Co 2 miesiące",
                                                                        3:"Co kwartał",6:"Co pół roku",12:"Co rok"}[x])
                        try:
                            default_date = date.fromisoformat(str(c.get("ostatnia_faktura", date.today().isoformat())))
                        except Exception:
                            default_date = date.today()
                        new_data = st.date_input("Ostatnia faktura", value=default_date, key=f"d_{i}")

                    col_save, col_del = st.columns([2, 1])
                    with col_save:
                        if st.button("💾 Zapisz zmiany", key=f"save_{i}"):
                            updated = {
                                "nazwa": new_nazwa, "nip": new_nip,
                                "kwota": new_kwota, "cykl_miesiecy": int(new_cykl),
                                "ostatnia_faktura": new_data.isoformat(), "uwagi": new_uwagi,
                            }
                            with st.spinner("Zapisuję..."):
                                update_client(ws, i, updated)
                                get_worksheet.clear()
                            st.success("✅ Zapisano!")
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ Usuń", key=f"del_{i}", type="secondary"):
                            with st.spinner("Usuwam..."):
                                delete_client(ws, i)
                                get_worksheet.clear()
                            st.rerun()
