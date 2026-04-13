# Procurement Planning Dashboard

An AI-driven procurement forecasting tool that tells you **what to buy, how much, and when** — based on consumption factors, machine count, lead times, and stock levels.

---

## Running Locally

You need two terminals open simultaneously.

### Terminal 1 — Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`.

### Terminal 2 — Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

The app will open at `http://localhost:5173`.

---

## Using the App

1. Upload your Excel file using the sidebar
2. Set the number of machines, planning horizon, safety buffer, and vendor strategy
3. View the procurement table with urgency-coded rows
4. Click any row to see the reasoning for that recommendation
5. Check the **Alerts** tab for Critical and High urgency items
6. Download the plan as Excel from the **Export** tab

---

## Excel File Format

The app expects an Excel file with these columns (names are flexible):

| Column | Required | Description |
|--------|----------|-------------|
| Part No / SKU Code | Optional | Unique part identifier |
| Description | Optional | Part name |
| Category | Optional | Part category |
| Consumption/Month | **Required** | Units consumed per machine per month |
| L1 Vendor | **Required** | Primary vendor name |
| Lead (L1) | **Required** | Primary vendor lead time e.g. `15 days` |
| Price (L1) | **Required** | Primary vendor unit price |
| L2 Vendor | Optional | Secondary vendor name |
| Lead (L2) | Optional | Secondary vendor lead time |
| Price (L2) | Optional | Secondary vendor unit price |
| Current Stock | Optional | Units currently in inventory (defaults to 0) |
| Incoming Stock | Optional | Units already on order |
| MOQ | Optional | Minimum order quantity |
| Pack Size | Optional | Must order in multiples of this |

---

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app — /api/analyze and /api/export
│   ├── schemas/models.py    # Pydantic response models
│   ├── logic/               # Business logic (demand, urgency, reasoning)
│   ├── utils/               # Excel loader and export
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/client.ts        # API calls
│   │   ├── store/useAppStore.ts # Zustand global state
│   │   ├── types/               # TypeScript interfaces
│   │   └── components/          # UI components
│   ├── vite.config.ts           # Proxies /api → localhost:8001
│   └── package.json
│
└── app.py                   # Original Streamlit version (still works)
```

---

## Deploying to Render (Free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set these:
   - **Build command:** `cd frontend && npm install && npm run build && cd ../backend && pip install -r requirements.txt`
   - **Start command:** `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment variable:** `PRODUCTION=true`
5. Deploy — you'll get a public URL

---

## How Urgency is Calculated

| Level | Condition |
|-------|-----------|
| Critical | Stock runs out before supplier can deliver |
| High | Stock covers less than 30 days |
| Medium | Stock covers less than 60 days |
| Low | Sufficient stock, order not urgent |
| No Action | Stock exceeds planning horizon demand |
