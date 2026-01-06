# Connection Troubleshooting Guide

## Issue: Frontend can't connect to Backend

### Symptoms
- Frontend loads but shows "Error loading issues - Failed to fetch"
- Port 3000 is redirected to 51148 (Cursor port forwarding)
- Backend on port 8000 is not accessible from the forwarded frontend

### Current Status
✅ **Backend is running** on `localhost:8000`
✅ **Frontend is running** on `localhost:3000`
✅ **CORS is properly configured** (Access-Control-Allow-Origin: *)
❌ **Port forwarding mismatch** - Frontend forwarded but backend isn't

---

## Quick Solutions

### Solution 1: Use Localhost Directly (Recommended for Local Development)

**If you're working on the same machine as the servers:**

1. Open your browser
2. Go to: **http://localhost:3000**
3. Everything should work!

**Test it:**
```bash
# Test backend
curl http://localhost:8000/api/health

# Open frontend in browser
xdg-open http://localhost:3000  # Linux
# or just type http://localhost:3000 in your browser
```

---

### Solution 2: Fix Port Forwarding (For Remote Access)

**If you're accessing via SSH/Remote/Cursor port forwarding:**

#### Step 1: Check forwarded ports
In Cursor, open the **Ports** panel (View → Ports) and note which ports are forwarded.

You should see:
- Port 3000 → 51148 (or similar)
- Port 8000 → ????? (may not be forwarded)

#### Step 2: Ensure backend port is also forwarded
If port 8000 is not in the list:
1. In Cursor, manually forward port 8000
2. Note the forwarded port number (e.g., 51149)

#### Step 3: Access with API parameter
```
http://localhost:51148/?api=http://localhost:BACKEND_PORT/api
```

For example, if backend is forwarded to 51149:
```
http://localhost:51148/?api=http://localhost:51149/api
```

---

### Solution 3: Use the Test Page

**We've created a diagnostic tool for you:**

1. Open: **http://localhost:3000/test.html**
   (or http://localhost:51148/test.html if port forwarded)

2. Click the test buttons to see which URL works

3. Copy the working API URL

4. Access the dashboard with that URL:
   ```
   http://localhost:3000/?api=WORKING_URL
   ```

---

## How to Verify Everything is Working

### Test Backend Health
```bash
curl http://localhost:8000/api/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "services": {
    "github": true,
    "anthropic": true
  }
}
```

### Test Backend Issues Endpoint
```bash
curl http://localhost:8000/api/issues?limit=2
```

### Test Frontend is Serving
```bash
curl -I http://localhost:3000
```

**Expected output:**
```
HTTP/1.0 200 OK
```

---

## Understanding the Port Forwarding Issue

```
┌─────────────────────────────────────────────────────────┐
│ Your Machine (Remote/SSH)                                │
│                                                          │
│  Browser → localhost:51148 (Cursor forwards to 3000)    │
│              ↓                                           │
│           Frontend HTML loaded                           │
│              ↓                                           │
│        JavaScript tries: localhost:8000 ❌               │
│        (Not forwarded! Connection fails)                 │
│                                                          │
│  SOLUTION: Forward 8000 OR access via localhost:3000    │
└─────────────────────────────────────────────────────────┘
```

---

## Current Configuration

The frontend (`index.html`) now automatically detects the environment:

1. **URL parameter** (highest priority):
   ```
   http://localhost:3000/?api=http://custom-host:8000/api
   ```

2. **Localhost detection**:
   - If hostname is `localhost` or `127.0.0.1` → uses `http://localhost:8000/api`
   
3. **Remote detection**:
   - Otherwise → uses current hostname with port 8000

---

## Debugging Tips

### Check what's running
```bash
# Check processes on ports
lsof -i :3000
lsof -i :8000

# Check listening ports
ss -tuln | grep -E ":(3000|8000)"
```

### Check CORS headers
```bash
curl -H "Origin: http://localhost:3000" -v http://localhost:8000/api/health 2>&1 | grep -i access-control
```

**Expected:**
```
< access-control-allow-origin: *
< access-control-allow-credentials: true
```

### Browser Console
Open DevTools (F12) → Console tab and look for:
```javascript
Dashboard version: 2026-01-05-v4
API_BASE: http://localhost:8000/api
```

### Browser Network Tab
Open DevTools (F12) → Network tab:
- Look for requests to `/api/issues`
- Check if they're going to the right host
- Check response status (200 = OK, CORS error = see Console)

---

## Still Not Working?

### 1. Clear browser cache
```
Ctrl+Shift+R (Linux/Windows)
Cmd+Shift+R (Mac)
```

### 2. Restart servers
```bash
# Kill and restart backend
pkill -f "python3 app.py"
cd /home/safaizal/projects/TheRock/dashboards/backend
python3 app.py

# Kill and restart frontend
pkill -f "python3 -m http.server 3000"
cd /home/safaizal/projects/TheRock/dashboards/frontend
python3 -m http.server 3000
```

### 3. Check firewall
```bash
# Check if firewall is blocking
sudo iptables -L -n | grep -E "(8000|3000)"

# If needed, allow ports (be careful!)
sudo ufw allow 8000
sudo ufw allow 3000
```

### 4. Test from command line
```bash
# Test full flow
curl -v http://localhost:8000/api/issues?limit=1 | python3 -m json.tool
```

---

## Working Configuration

When everything is working:

```
✓ Backend: http://localhost:8000
  - Health: http://localhost:8000/api/health
  - Issues: http://localhost:8000/api/issues
  - Running: python3 app.py (Terminal 8)

✓ Frontend: http://localhost:3000
  - Serving: python3 -m http.server 3000 (Terminal 9)
  - Auto-detects backend URL
  - Fallback: Use ?api=URL parameter

✓ CORS: Enabled (allow_origins=["*"])

✓ Both services running in TheRock/dashboards/
```

---

## Contact

If still having issues, share:
1. Output of: `curl http://localhost:8000/api/health`
2. Browser console errors (F12 → Console)
3. How you're accessing the page (localhost:3000 or localhost:51148)



