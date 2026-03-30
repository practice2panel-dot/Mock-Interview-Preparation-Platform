# How to Start Backend Server

## Quick Start

### Windows (PowerShell):
```powershell
cd Backend
python start_server.py
```

### Windows (Command Prompt):
```cmd
cd Backend
python start_server.py
```

## What to Look For

When server starts successfully, you should see:
```
OpenAI API Key loaded successfully (length: 51)
Users table initialized
🚀 Starting Path2Hire API server...
Running on http://0.0.0.0:5000
```

## Common Issues

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "Database connection error"
- Check `.env` file - `PGDATABASE=fyp` (your database name)
- Make sure PostgreSQL is running
- Verify database credentials

### "Port 5000 already in use"
- Close other applications using port 5000
- Or change PORT in `.env` file

## Verify Server is Running

Open in browser: http://localhost:5000/api/health

Should return:
```json
{"success": true, "message": "API is running", "status": "healthy"}
```

## Keep Server Running

- **DON'T close the terminal** - server needs to keep running
- To stop: Press `Ctrl + C` in the terminal
- To restart: Stop and run `python start_server.py` again

