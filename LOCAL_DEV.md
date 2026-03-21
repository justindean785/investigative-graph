# Local dev — keep it simple

You only need **a running MongoDB** once. After that, every day is the same **two terminals**.

---

## Default recommendation (no Docker, no Windows admin)

**Use [MongoDB Atlas](https://www.mongodb.com/atlas)** (free tier):

1. Create a free cluster → **Database** → **Connect** → Drivers → copy the connection string.
2. Put it in `backend/.env`:
   ```env
   MONGO_URL=<your-atlas-connection-string>
   DB_NAME=trace_analyst
   ```
3. In Atlas, allow your IP (or `0.0.0.0/0` for dev only).

You never run `mongod` on your PC. Skip to **Every day** below.

---

## If you already have Docker Desktop

From the **repo root**:

```powershell
docker compose up -d
```

That starts Mongo on **localhost:27017**. Use in `backend/.env`:

```env
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=trace_analyst
```

Stop later: `docker compose down` (data stays in a Docker volume).

---

## If you installed MongoDB on Windows (MSI)

Prefer **“Install as a service”**, then in an **Administrator** PowerShell:

```powershell
net start MongoDB
```

(If the name differs: `Get-Service *mongo*` and use that name.)

Your `backend/.env` can stay `MONGO_URL=mongodb://127.0.0.1:27017`.

---

## Every day (same no matter how you run Mongo)

**Terminal 1 — backend**

```powershell
cd E:\investigative-graph-1\backend
# .env is loaded automatically if present
uvicorn server:app --host 127.0.0.1 --port 8001 --reload
```

**Terminal 2 — frontend**

```powershell
cd E:\investigative-graph-1\frontend
$env:BROWSER='none'
$env:REACT_APP_BACKEND_URL='http://localhost:8001'
yarn start
```

Open **http://localhost:3000**.

---

## “Which should I use?”

| Situation | Use |
|-----------|-----|
| Don’t want to install DB / fight Windows | **Atlas** |
| Already use Docker | **`docker compose up -d`** |
| Mongo already installed as a service | **`net start MongoDB`** (Admin) |

You don’t have to decide forever — pick one that works today.
