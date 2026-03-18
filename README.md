# 🧾 Fakturnik – Instrukcja uruchomienia

System przypomnień o fakturach oparty na Google Sheets + Streamlit.

---

## ✅ Co robi aplikacja?

- Łączy się z Twoim arkuszem Google Sheets z listą klientów
- Oblicza, które faktury są **przeterminowane**, **pilne** lub **wkrótce** do wystawienia
- Wysyła **e-mail z przypomnieniem** do współpracowników
- Działa lokalnie – każdy w zespole może uruchomić na swoim komputerze

---

## 🚀 Uruchomienie krok po kroku

### 1. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 2. Uruchomienie aplikacji

```bash
streamlit run app.py
```

Aplikacja otworzy się automatycznie w przeglądarce pod adresem `http://localhost:8501`

---

## 📊 Struktura arkusza Google Sheets

Utwórz arkusz z **dokładnie takimi nagłówkami** w pierwszym wierszu:

| Kolumna | Opis | Przykład |
|---|---|---|
| `Klient` | Pełna nazwa klienta | ABC Sp. z o.o. |
| `NIP` | NIP klienta | 123-456-78-90 |
| `Kwota_PLN` | Kwota faktury brutto | 2500 |
| `Ostatnia_faktura` | Data ostatniej faktury (DD.MM.RRRR) | 01.02.2025 |
| `Cykl_miesiecy` | Co ile miesięcy wystawiać fakturę | 1 |
| `Uwagi` | Opcjonalne uwagi | usługi IT |

---

## 🔑 Konfiguracja Google Cloud (jednorazowo)

### Krok 1 – Utwórz projekt i Service Account

1. Wejdź na [console.cloud.google.com](https://console.cloud.google.com)
2. Utwórz nowy projekt (lub użyj istniejącego)
3. Włącz **Google Sheets API** i **Google Drive API**:
   - Menu → APIs & Services → Enable APIs
   - Wyszukaj "Google Sheets API" → Enable
   - Wyszukaj "Google Drive API" → Enable

### Krok 2 – Utwórz Service Account i pobierz klucz

1. Menu → IAM & Admin → Service Accounts
2. Kliknij **"Create Service Account"**
3. Podaj dowolną nazwę, np. `fakturnik-bot`
4. Kliknij **"Create and Continue"** → pomiń role → **"Done"**
5. Kliknij na utworzone konto → zakładka **"Keys"**
6. **"Add Key" → "Create new key" → JSON** → pobierz plik

### Krok 3 – Udostępnij arkusz dla Service Account

1. Otwórz pobrany plik JSON i znajdź `"client_email"` – skopiuj ten adres
2. Otwórz swój arkusz Google Sheets
3. Kliknij **"Udostępnij"** (przycisk w prawym górnym rogu)
4. Wklej adres `client_email` jako edytora → **"Wyślij"**

---

## 📧 Konfiguracja e-mail (Gmail)

Jeśli używasz Gmaila:

1. Włącz weryfikację dwuetapową na koncie Google
2. Wejdź na [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Utwórz **App Password** dla "Aplikacja: Poczta"
4. Skopiowane hasło wklej w polu "Hasło / App Password" w aplikacji

Ustawienia SMTP dla Gmaila:
- **Serwer:** `smtp.gmail.com`
- **Port:** `465`

---

## 🎨 Statusy faktur

| Status | Opis | Kolor |
|---|---|---|
| **PRZETERMINOWANA** | Termin minął | 🔴 Czerwony |
| **PILNE** | Termin za ≤7 dni | 🟡 Żółty |
| **WKRÓTCE** | Termin za 8–14 dni | 🟡 Żółty |
| **OK** | Więcej niż 14 dni | 🟢 Zielony |

---

## 💡 Wskazówki

- Kliknij **"Odśwież dane"** w panelu bocznym, aby pobrać najnowsze dane z arkusza
- Możesz eksportować aktualny widok do pliku CSV
- Podgląd e-maila dostępny przed wysłaniem w zakładce "Wyślij przypomnienia"
