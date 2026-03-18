# 🧾 Panel fakturowy v3 – instrukcja

Dane klientów przechowywane są w Google Sheets – trwale, bez utraty po odświeżeniu.

---

## 🚀 Wdrożenie na Streamlit Cloud

### 1. Wgraj pliki na GitHub
Wgraj `app.py` i `requirements.txt` do repozytorium.

### 2. Utwórz arkusz Google Sheets
- Utwórz pusty arkusz Google Sheets
- Skopiuj jego URL (np. `https://docs.google.com/spreadsheets/d/ABC123/edit`)

### 3. Skonfiguruj Service Account (jeśli jeszcze nie masz)
1. Wejdź na [console.cloud.google.com](https://console.cloud.google.com)
2. Włącz **Google Sheets API** i **Google Drive API**
3. Utwórz Service Account → pobierz klucz JSON
4. Udostępnij arkusz dla adresu e-mail z pliku JSON (jako Edytor)

### 4. Dodaj Secrets w Streamlit Cloud
W panelu Streamlit → **Advanced settings → Secrets** wklej:

```toml
sheet_url = "https://docs.google.com/spreadsheets/d/TWOJ_ID/edit"

[gcp_service_account]
type = "service_account"
project_id = "twoj-projekt"
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "fakturnik@twoj-projekt.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
```

Wartości skopiuj z pobranego pliku JSON.

---

## 👥 Jak używać

### 👁️ Widok szefa
Szef wchodzi na link i widzi:
- Które faktury trzeba wystawić teraz (termin ≤10 dni lub po terminie)
- Kwoty i łączną sumę
- NIP-y i uwagi

### ✏️ Zarządzaj (Ty)
- Dodajesz/edytujesz/usuwasz klientów
- Zmiany zapisują się **natychmiast** do arkusza Google Sheets
- Szef po odświeżeniu strony widzi aktualne dane

---

## 📋 Struktura danych w arkuszu

Aplikacja sama tworzy nagłówki w pierwszym wierszu:

| nazwa | nip | kwota | cykl_miesiecy | ostatnia_faktura | uwagi |
|---|---|---|---|---|---|
| ABC Sp. z o.o. | 123-456-78-90 | 2500 | 1 | 2025-02-01 | usługi IT |
