# Database Name Fix - Agar Aapne Different Database Name Use Kiya Hai

## Problem
Error: `database "interview_db" does not exist`

Agar aapne dusra database banaya hai aur usme backup restore kiya hai, to database name different hoga.

## Solution: .env File Update Karein

### Step 1: Apna Database Name Check Karein

**Option A: pgAdmin Se**
1. **pgAdmin** kholen
2. **Servers** → **PostgreSQL** → **Databases** expand karein
3. Apne database ka naam dekhein (jo aapne create kiya)

**Option B: Command Line Se**
```cmd
psql -U postgres -l
```
Yeh command se saare databases dikhenge. Apna database name note karein.

### Step 2: .env File Update Karein

`Backend/.env` file kholen aur `PGDATABASE` update karein:

**Agar aapka database name `mydb` hai:**
```env
PGDATABASE=mydb
```

**Agar aapka database name `interview_platform` hai:**
```env
PGDATABASE=interview_platform
```

**Agar aapka database name kuch aur hai:**
```env
PGDATABASE=your_actual_database_name
```

### Step 3: Complete .env Configuration

`.env` file mein yeh settings honi chahiye:

```env
# Database Configuration
PGDATABASE=your_actual_database_name
PGUSER=postgres
PGPASSWORD=your_postgres_password
PGHOST=localhost
PGPORT=5432
```

**Important:**
- `PGDATABASE` = Apna actual database name (jo aapne create kiya)
- `PGUSER` = Usually `postgres` hota hai
- `PGPASSWORD` = Apna PostgreSQL password
- `PGHOST` = Usually `localhost`
- `PGPORT` = Usually `5432`

### Step 4: Backend Restart Karein

```bash
cd Backend
python start_server.py
```

Agar "Users table initialized" dikhe, to sab theek hai! ✅

## Alternative: Interview_db Name Se Database Create Karein

Agar aap `interview_db` name use karna chahte ho:

### Step 1: Database Create Karein

**Command Line Se:**
```cmd
psql -U postgres
```
Phir PostgreSQL prompt pe:
```sql
CREATE DATABASE interview_db;
\q
```

**Ya Direct Command:**
```cmd
psql -U postgres -c "CREATE DATABASE interview_db;"
```

### Step 2: Backup Restore Karein

```cmd
psql -U postgres -d interview_db -f your_backup_file.sql
```

Ya pgAdmin se:
1. **interview_db** pe right-click
2. **Restore** select karein
3. Backup file select karein
4. **Restore** click karein

### Step 3: .env File Check Karein

```env
PGDATABASE=interview_db
```

## Quick Check: Database Name Kya Hai?

Backend server start karte waqt error message mein database name dikhega:
```
database "interview_db" does not exist
```

Yahan jo name dikhega, woh `.env` file mein `PGDATABASE` ke against hona chahiye.

## Troubleshooting

### "Database does not exist" error
- `.env` file mein `PGDATABASE` sahi database name hai?
- Database actually create hua hai? (pgAdmin ya `psql -l` se check karein)

### "Password authentication failed"
- `.env` file mein `PGPASSWORD` sahi password hai?

### "Connection refused"
- PostgreSQL service running hai? (Windows: Services app check karein)

