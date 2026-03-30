# How to Restart the Backend Server

The backend server needs to be restarted for CORS changes to take effect.

## Steps to Restart:

1. **Stop the current server:**
   - Find the terminal/command prompt where the server is running
   - Press `Ctrl + C` to stop it

2. **Start the server again:**
   ```bash
   cd Backend
   python start_server.py
   ```

3. **Verify it's running:**
   - You should see: "🚀 Starting Path2Hire API server..."
   - Open http://localhost:5000/api/health in your browser
   - Should return: `{"success": true, "message": "API is running", "status": "healthy"}`

## Alternative: Restart via PowerShell

If you need to kill the process and restart:

```powershell
# Kill any process on port 5000
Get-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess | Stop-Process -Force

# Then start the server
cd Backend
python start_server.py
```

## Check if Server is Running

```powershell
# Check if port 5000 is in use
netstat -ano | findstr :5000

# Test the health endpoint
Invoke-WebRequest -Uri http://localhost:5000/api/health
```

