import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
from dateutil.relativedelta import relativedelta
import json
import base64
import os

st.set_page_config(
    page_title="Panel fakturowy – Ermon",
    page_icon="assets/logo.png" if os.path.exists("assets/logo.png") else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Logo base64 helper ─────────────────────────────────────────────────────────
def get_logo_b64():
    for path in ["logo.png", "assets/logo.png"]:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None

LOGO_B64 = get_logo_b64()
LOGO_HTML = f'<img src="data:image/png;base64,{LOGO_B64}" style="height:40px;display:block;filter:brightness(1.1);" />' if LOGO_B64 else "<span style=\"font-family:\'Syne\',sans-serif;font-size:1.5rem;font-weight:800;color:#fff;\">Ermon.</span>"

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --purple:    #2c016d;
    --pink:      #ff466b;
    --blue:      #3337bd;
    --bg:        #12062a;
    --surface:   #1c0d3a;
    --surface2:  #261550;
    --border:    #3d2070;
    --text:      #f5f0ff;
    --muted:     #a090c8;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
.main, .block-container { background-color: var(--bg) !important; }
.block-container { padding: 3rem 2.5rem 2rem 2.5rem !important; max-width: 1200px; }
header[data-testid="stHeader"] { background-color: var(--bg) !important; }
div[data-testid="stAppViewContainer"] { background-color: var(--bg) !important; }
div[data-testid="stDecoration"] { display: none !important; }

/* Header */
.top-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.header-right { text-align: right; }
.header-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin: 0;
}
.header-date {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* Nav buttons */
.stButton > button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    border-radius: 6px !important;
    padding: 0.45rem 1.2rem !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    color: var(--muted) !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    border-color: var(--pink) !important;
    color: var(--pink) !important;
    background: var(--surface2) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--purple), var(--blue)) !important;
    border-color: var(--blue) !important;
    color: #fff !important;
}

/* Summary cards */
.summary-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 2.5rem;
}
.summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    position: relative;
    overflow: hidden;
}
.summary-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--purple), var(--blue));
}
.summary-card.alert::before {
    background: linear-gradient(90deg, var(--pink), #ff8fa3);
}
.card-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 8px;
}
.card-value {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: var(--text);
    line-height: 1;
}
.card-value.alert { color: var(--pink); }
.card-value.ok { color: #7b8fff; }

/* Section heading */
.section-heading {
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--muted);
    margin: 0 0 1.25rem 0;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid var(--border);
}
.section-heading span {
    color: var(--pink);
    margin-left: 8px;
}

/* Client card */
.client-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 14px;
    overflow: hidden;
}
.client-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
}
.client-name {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
}
.client-nip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted);
    margin-top: 2px;
}
.client-total {
    font-family: 'Syne', sans-serif;
    font-size: 1.2rem;
    font-weight: 800;
    color: var(--pink);
    text-align: right;
}
.client-total-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    text-align: right;
}

/* Positions table */
.positions-table {
    width: 100%;
    border-collapse: collapse;
}
.positions-table th {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    text-align: left;
    padding: 8px 1.25rem;
    background: var(--surface2);
}
.positions-table td {
    padding: 10px 1.25rem;
    font-size: 0.88rem;
    border-bottom: 1px solid var(--border);
    color: var(--text);
}
.positions-table tr:last-child td { border-bottom: none; }
.pos-name { font-weight: 500; }
.pos-kwota {
    font-family: 'JetBrains Mono', monospace;
    color: #7b8fff;
    font-weight: 500;
    text-align: right;
}
.pos-stala {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    padding: 2px 8px;
    border-radius: 4px;
    background: #1a0540;
    color: var(--muted);
    border: 1px solid var(--border);
}

/* Badge */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.badge-late { background: #3d0020; color: var(--pink); border: 1px solid #7a0040; }
.badge-now  { background: #1a1040; color: #a0aaff; border: 1px solid #3337bd; }
.badge-ok   { background: #0a1a30; color: #5580cc; border: 1px solid #1a3060; }

/* Form overrides */
.stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput label, .stNumberInput label, .stSelectbox label, .stTextArea label, .stCheckbox label {
    color: var(--muted) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
div[data-testid="stTabs"] button {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: var(--muted) !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--pink) !important;
    border-bottom-color: var(--pink) !important;
}
section[data-testid="stSidebar"] { background: var(--surface) !important; }
</style>
""", unsafe_allow_html=True)


# ── Google Sheets ──────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Sheet structure:
# Sheet1 = Klienci: id | nazwa | nip | cykl_miesiecy | ostatnia_faktura
# Sheet2 = Pozycje: klient_id | nazwa_pozycji | kwota | stala (TRUE/FALSE)

@st.cache_resource(ttl=30)
def get_workbook(sheet_url: str):
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
        else:
            st.error("Brak konfiguracji Google – sprawdź Secrets.")
            return None
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        sh = client.open_by_url(sheet_url)

        # Ensure sheets exist with headers
        sheet_names = [ws.title for ws in sh.worksheets()]

        if "Klienci" not in sheet_names:
            ws_k = sh.add_worksheet("Klienci", 100, 5)
        else:
            ws_k = sh.worksheet("Klienci")
        if ws_k.row_values(1) != ["id", "nazwa", "nip", "cykl_miesiecy", "ostatnia_faktura"]:
            ws_k.clear()
            ws_k.append_row(["id", "nazwa", "nip", "cykl_miesiecy", "ostatnia_faktura"])

        if "Pozycje" not in sheet_names:
            ws_p = sh.add_worksheet("Pozycje", 500, 4)
        else:
            ws_p = sh.worksheet("Pozycje")
        if ws_p.row_values(1) != ["klient_id", "nazwa_pozycji", "kwota", "stala"]:
            ws_p.clear()
            ws_p.append_row(["klient_id", "nazwa_pozycji", "kwota", "stala"])

        return sh
    except Exception as e:
        st.error(f"Blad polaczenia: {e}")
        return None


def load_klienci(sh) -> list[dict]:
    ws = sh.worksheet("Klienci")
    return ws.get_all_records()

def load_pozycje(sh) -> list[dict]:
    ws = sh.worksheet("Pozycje")
    return ws.get_all_records()

def next_id(klienci: list[dict]) -> str:
    if not klienci:
        return "1"
    ids = [int(k.get("id", 0)) for k in klienci if str(k.get("id","")).isdigit()]
    return str(max(ids) + 1) if ids else "1"

def add_klient(sh, klient: dict):
    ws = sh.worksheet("Klienci")
    ws.append_row([
        klient["id"], klient["nazwa"], klient["nip"],
        klient["cykl_miesiecy"], klient["ostatnia_faktura"]
    ])

def update_klient(sh, klient: dict):
    ws = sh.worksheet("Klienci")
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if str(r.get("id")) == str(klient["id"]):
            sheet_row = i + 2
            ws.update(f"A{sheet_row}:E{sheet_row}", [[
                klient["id"], klient["nazwa"], klient["nip"],
                klient["cykl_miesiecy"], klient["ostatnia_faktura"]
            ]])
            break

def delete_klient(sh, klient_id: str):
    ws_k = sh.worksheet("Klienci")
    ws_p = sh.worksheet("Pozycje")
    # Delete client row
    records = ws_k.get_all_records()
    for i, r in enumerate(records):
        if str(r.get("id")) == str(klient_id):
            ws_k.delete_rows(i + 2)
            break
    # Delete all positions for this client
    poz = ws_p.get_all_records()
    rows_to_delete = []
    for i, p in enumerate(poz):
        if str(p.get("klient_id")) == str(klient_id):
            rows_to_delete.append(i + 2)
    for row in sorted(rows_to_delete, reverse=True):
        ws_p.delete_rows(row)

def save_pozycje(sh, klient_id: str, pozycje: list[dict]):
    ws = sh.worksheet("Pozycje")
    # Remove existing positions for this client
    all_poz = ws.get_all_records()
    rows_to_delete = []
    for i, p in enumerate(all_poz):
        if str(p.get("klient_id")) == str(klient_id):
            rows_to_delete.append(i + 2)
    for row in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row)
    # Add new positions
    for p in pozycje:
        ws.append_row([klient_id, p["nazwa"], p["kwota"], str(p["stala"])])


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
        return "BLAD DATY", "badge-late"

def should_invoice_now(klient: dict, today: date) -> bool:
    try:
        cykl = int(klient.get("cykl_miesiecy", 1))
        ostatnia = str(klient.get("ostatnia_faktura", "")).strip()
        if not ostatnia:
            return True
        last = date.fromisoformat(ostatnia)
        return (last + relativedelta(months=cykl) - today).days <= 10
    except Exception:
        return False

def get_klient_pozycje(pozycje: list[dict], klient_id: str) -> list[dict]:
    return [p for p in pozycje if str(p.get("klient_id")) == str(klient_id)]

def suma_pozycji(pozycje: list[dict]) -> float:
    try:
        return sum(float(p.get("kwota", 0) or 0) for p in pozycje)
    except Exception:
        return 0.0


# ── Session state ──────────────────────────────────────────────────────────────
if "role" not in st.session_state:
    st.session_state.role = "szef"
if "sheet_url" not in st.session_state:
    st.session_state.sheet_url = st.secrets.get("sheet_url", "")

today = date.today()
miesiac = today.strftime("%B %Y").upper()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-header">
    <div>{LOGO_HTML}</div>
    <div class="header-right">
        <div class="header-title">Panel Fakturowy</div>
        <div class="header-date">{miesiac}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Sheet URL ──────────────────────────────────────────────────────────────────
if not st.session_state.sheet_url:
    st.warning("Podaj URL arkusza Google Sheets.")
    url_input = st.text_input("URL arkusza", placeholder="https://docs.google.com/spreadsheets/d/...")
    if url_input:
        st.session_state.sheet_url = url_input
        st.rerun()
    st.stop()

sh = get_workbook(st.session_state.sheet_url)
if sh is None:
    st.stop()

klienci = load_klienci(sh)
pozycje = load_pozycje(sh)

# ── Role switcher ──────────────────────────────────────────────────────────────
col_r1, col_r2, col_r3 = st.columns([1, 1, 6])
with col_r1:
    if st.button("Widok szefa", use_container_width=True,
                 type="primary" if st.session_state.role == "szef" else "secondary"):
        st.session_state.role = "szef"
        st.rerun()
with col_r2:
    if st.button("Zarzadzaj", use_container_width=True,
                 type="primary" if st.session_state.role == "admin" else "secondary"):
        st.session_state.role = "admin"
        st.rerun()

st.markdown("<div style='margin-bottom:1.75rem'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# WIDOK SZEFA
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.role == "szef":

    do_wyst  = [k for k in klienci if should_invoice_now(k, today)]
    pozostale = [k for k in klienci if not should_invoice_now(k, today)]
    suma_total = sum(suma_pozycji(get_klient_pozycje(pozycje, k["id"])) for k in do_wyst)

    st.markdown(f"""
    <div class="summary-grid">
        <div class="summary-card alert">
            <div class="card-label">Do wystawienia</div>
            <div class="card-value alert">{len(do_wyst)}</div>
        </div>
        <div class="summary-card">
            <div class="card-label">Laczna kwota</div>
            <div class="card-value">{suma_total:,.0f} PLN</div>
        </div>
        <div class="summary-card">
            <div class="card-label">Na biezaco</div>
            <div class="card-value ok">{len(pozostale)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Faktury do wystawienia ─────────────────────────────────────────────────
    st.markdown(f'<div class="section-heading">Do wystawienia <span>{len(do_wyst)}</span></div>', unsafe_allow_html=True)

    if not do_wyst:
        st.success("Wszystkie faktury sa aktualne.")
    else:
        for k in sorted(do_wyst, key=lambda x: suma_pozycji(get_klient_pozycje(pozycje, x["id"])), reverse=True):
            kpoz = get_klient_pozycje(pozycje, k["id"])
            total = suma_pozycji(kpoz)
            label, cls = get_status(k, today)

            rows_html = ""
            for p in kpoz:
                stala_badge = '<span class="pos-stala">STALA</span>' if str(p.get("stala","")).upper() == "TRUE" else '<span class="pos-stala" style="opacity:0.4">ZMIENNA</span>'
                try:
                    kwota_fmt = f"{float(p.get('kwota',0)):,.2f} PLN"
                except Exception:
                    kwota_fmt = "—"
                rows_html += f"""
                <tr>
                    <td class="pos-name">{p.get('nazwa_pozycji','—')}</td>
                    <td>{stala_badge}</td>
                    <td class="pos-kwota">{kwota_fmt}</td>
                </tr>"""

            if not kpoz:
                rows_html = '<tr><td colspan="3" style="color:var(--muted);padding:12px 1.25rem;font-size:0.82rem;">Brak pozycji – dodaj w panelu Zarzadzaj</td></tr>'

            st.markdown(f"""
            <div class="client-card">
                <div class="client-card-header">
                    <div>
                        <div class="client-name">{k.get('nazwa','—')}</div>
                        <div class="client-nip">NIP: {k.get('nip','—')} &nbsp;·&nbsp; <span class="badge {cls}">{label}</span></div>
                    </div>
                    <div>
                        <div class="client-total-label">Suma faktury</div>
                        <div class="client-total">{total:,.2f} PLN</div>
                    </div>
                </div>
                <table class="positions-table">
                    <thead><tr><th>Pozycja</th><th>Typ</th><th style="text-align:right">Kwota</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            """, unsafe_allow_html=True)

    # ── Pozostali ──────────────────────────────────────────────────────────────
    if pozostale:
        with st.expander(f"Pozostali klienci – {len(pozostale)} (faktura jeszcze nie wymagana)"):
            for k in pozostale:
                kpoz = get_klient_pozycje(pozycje, k["id"])
                total = suma_pozycji(kpoz)
                label, cls = get_status(k, today)
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:10px 0;border-bottom:1px solid var(--border);">
                    <div>
                        <span style="font-weight:600">{k.get('nazwa','—')}</span>
                        <span style="color:var(--muted);font-size:0.8rem;margin-left:10px">NIP: {k.get('nip','—')}</span>
                    </div>
                    <div style="display:flex;gap:12px;align-items:center;">
                        <span style="font-family:'JetBrains Mono',monospace;color:#7b8fff">{total:,.0f} PLN</span>
                        <span class="badge {cls}">{label}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# WIDOK ADMIN
# ══════════════════════════════════════════════════════════════════════════════
else:
    tab1, tab2 = st.tabs(["Dodaj klienta", "Lista i edycja"])

    with tab1:
        st.markdown('<div class="section-heading">Nowy klient</div>', unsafe_allow_html=True)

        with st.form("nowy_klient", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nazwa  = st.text_input("Nazwa klienta *", placeholder="ABC Sp. z o.o.")
                nip    = st.text_input("NIP", placeholder="123-456-78-90")
            with col2:
                cykl   = st.selectbox("Cykl fakturowania", [1,2,3,6,12],
                                      format_func=lambda x: {1:"Co miesiac",2:"Co 2 miesiace",
                                                              3:"Co kwartal",6:"Co pol roku",12:"Co rok"}[x])
                ostatnia = st.date_input("Data ostatniej faktury", value=date.today())

            st.markdown("**Pozycje na fakturze**")
            st.caption("Dodaj od 1 do 6 pozycji. Zaznacz 'Stala' jesli kwota sie nie zmienia.")

            pozycje_form = []
            for i in range(6):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    pnazwa = st.text_input(f"Pozycja {i+1}", placeholder="np. Obsluga social media", key=f"pn_{i}")
                with c2:
                    pkwota = st.number_input(f"Kwota {i+1} (PLN)", min_value=0.0, step=100.0, format="%.2f", key=f"pk_{i}")
                with c3:
                    pstala = st.checkbox("Stala", key=f"ps_{i}")
                if pnazwa and pkwota > 0:
                    pozycje_form.append({"nazwa": pnazwa, "kwota": pkwota, "stala": pstala})

            submitted = st.form_submit_button("Dodaj klienta", use_container_width=True)
            if submitted:
                if not nazwa:
                    st.error("Podaj nazwe klienta.")
                elif not pozycje_form:
                    st.error("Dodaj co najmniej jedna pozycje z nazwa i kwota.")
                else:
                    kid = next_id(klienci)
                    nowy = {
                        "id": kid, "nazwa": nazwa.strip(), "nip": nip.strip(),
                        "cykl_miesiecy": int(cykl),
                        "ostatnia_faktura": ostatnia.isoformat(),
                    }
                    with st.spinner("Zapisuje..."):
                        add_klient(sh, nowy)
                        save_pozycje(sh, kid, [{"nazwa": p["nazwa"], "kwota": p["kwota"], "stala": p["stala"]} for p in pozycje_form])
                        get_workbook.clear()
                    st.success(f"Dodano: {nazwa} z {len(pozycje_form)} pozycjami.")
                    st.rerun()

    with tab2:
        st.markdown('<div class="section-heading">Wszyscy klienci</div>', unsafe_allow_html=True)

        if not klienci:
            st.info("Brak klientow. Dodaj pierwszego w zakladce obok.")
        else:
            for k in klienci:
                kid = str(k.get("id"))
                kpoz = get_klient_pozycje(pozycje, kid)
                total = suma_pozycji(kpoz)

                with st.expander(f"{k.get('nazwa','—')}  ·  {total:,.0f} PLN  ·  {len(kpoz)} pozycji"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        new_nazwa = st.text_input("Nazwa", value=k.get("nazwa",""), key=f"kn_{kid}")
                        new_nip   = st.text_input("NIP",   value=k.get("nip",""),   key=f"knip_{kid}")
                    with col_b:
                        cykl_opt = [1,2,3,6,12]
                        try:
                            cykl_idx = cykl_opt.index(int(k.get("cykl_miesiecy",1)))
                        except Exception:
                            cykl_idx = 0
                        new_cykl = st.selectbox("Cykl", cykl_opt, index=cykl_idx, key=f"kc_{kid}",
                                                format_func=lambda x: {1:"Co miesiac",2:"Co 2 miesiace",
                                                                        3:"Co kwartal",6:"Co pol roku",12:"Co rok"}[x])
                        try:
                            default_date = date.fromisoformat(str(k.get("ostatnia_faktura", date.today().isoformat())))
                        except Exception:
                            default_date = date.today()
                        new_data = st.date_input("Ostatnia faktura", value=default_date, key=f"kd_{kid}")

                    st.markdown("**Pozycje:**")
                    new_poz = []
                    for i in range(6):
                        existing = kpoz[i] if i < len(kpoz) else {}
                        c1, c2, c3 = st.columns([3, 2, 1])
                        with c1:
                            pn = st.text_input(f"Pozycja {i+1}", value=existing.get("nazwa_pozycji",""),
                                               key=f"epn_{kid}_{i}", placeholder="nazwa pozycji")
                        with c2:
                            try:
                                pkv = float(existing.get("kwota", 0) or 0)
                            except Exception:
                                pkv = 0.0
                            pk = st.number_input(f"Kwota {i+1}", value=pkv, step=100.0,
                                                 format="%.2f", key=f"epk_{kid}_{i}")
                        with c3:
                            ps_val = str(existing.get("stala","")).upper() == "TRUE"
                            ps = st.checkbox("Stala", value=ps_val, key=f"eps_{kid}_{i}")
                        if pn and pk > 0:
                            new_poz.append({"nazwa": pn, "kwota": pk, "stala": ps})

                    col_s, col_d = st.columns([2, 1])
                    with col_s:
                        if st.button("Zapisz zmiany", key=f"ksave_{kid}"):
                            updated = {
                                "id": kid, "nazwa": new_nazwa, "nip": new_nip,
                                "cykl_miesiecy": int(new_cykl),
                                "ostatnia_faktura": new_data.isoformat(),
                            }
                            with st.spinner("Zapisuje..."):
                                update_klient(sh, updated)
                                save_pozycje(sh, kid, [{"nazwa": p["nazwa"], "kwota": p["kwota"], "stala": p["stala"]} for p in new_poz])
                                get_workbook.clear()
                            st.success("Zapisano!")
                            st.rerun()
                    with col_d:
                        if st.button("Usun", key=f"kdel_{kid}", type="secondary"):
                            with st.spinner("Usuwam..."):
                                delete_klient(sh, kid)
                                get_workbook.clear()
                            st.rerun()
