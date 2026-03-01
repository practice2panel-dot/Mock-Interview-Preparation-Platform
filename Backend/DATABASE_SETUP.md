# PostgreSQL Database Setup - Quick Guide

## Problem
Error: `database "interview_db" does not exist`

## Solution: Database Create Karein

### Step 1: PostgreSQL Check Karein

1. **PostgreSQL running hai?**
   - Windows: **Services** app kholen
   - Search karein: `postgresql`
   - Status **Running** hona chahiye

### Step 2: Database Create Karein

**Option A: Command Line Se (Easiest)**

1. **Command Prompt** kholen (cmd)
2. Ye command run karein:
   ```cmd
   psql -U postgres
   ```
   - Password enter karein (agar set hai)

3. PostgreSQL prompt pe ye commands run karein:
   ```sql
   CREATE DATABASE interview_db;
   \q
   ```

**Option B: pgAdmin Se (GUI)**

1. **pgAdmin** kholen
2. **Servers** → **PostgreSQL** → **Databases** pe right-click
3. **Create** → **Database**
4. **Database name**: `interview_db`
5. **Save** click karein

**Option C: SQL Command Direct**

Command Prompt mein:
```cmd
psql -U postgres -c "CREATE DATABASE interview_db;"
```

### Step 3: .env File Update Karein

`Backend/.env` file mein check karein:

```env
PGDATABASE=interview_db
PGUSER=postgres
PGPASSWORD=your_postgres_password
PGHOST=localhost
PGPORT=5432
```

**Important:**
- `PGDATABASE` exactly `interview_db` hona chahiye (jo aapne create kiya)
- `PGUSER` usually `postgres` hota hai
- `PGPASSWORD` apna PostgreSQL password

### Step 4: Test Karein

Backend server restart karein:
```bash
cd Backend
python start_server.py
```

Agar "Users table initialized" dikhe, to database connection theek hai! ✅

## Alternative: Different Database Name Use Karein

Agar aapka database ka naam different hai (e.g., `mydb`), to:

1. `.env` file mein update karein:
   ```env
   PGDATABASE=mydb
   ```

2. Backend restart karein

## Troubleshooting

### "psql: command not found"
- PostgreSQL bin folder ko PATH mein add karein
- Ya phir pgAdmin use karein (Option B)

### "password authentication failed"
- Correct password enter karein
- Ya phir PostgreSQL password reset karein

### "connection refused"
- PostgreSQL service check karein (Step 1)
- Port 5432 check karein (firewall issue ho sakta hai)

## Quick Test

Database create hone ke baad, test karein:

```cmd
psql -U postgres -d interview_db -c "SELECT 1;"
```

Agar `1` dikhe, to database theek se create ho gaya hai! ✅





