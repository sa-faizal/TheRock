#!/bin/bash
# Service Health Check Script for TheRock Dashboard

echo "=================================="
echo "TheRock Dashboard Health Check"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Backend (Port 8000)
echo "1. Checking Backend (Port 8000)..."
if curl -s --max-time 3 http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
    
    # Get health data
    HEALTH=$(curl -s http://localhost:8000/api/health)
    GITHUB_OK=$(echo $HEALTH | grep -o '"github":true' | wc -l)
    ANTHROPIC_OK=$(echo $HEALTH | grep -o '"anthropic":true' | wc -l)
    
    if [ $GITHUB_OK -eq 1 ]; then
        echo -e "${GREEN}  ✓ GitHub token configured${NC}"
    else
        echo -e "${RED}  ✗ GitHub token missing${NC}"
    fi
    
    if [ $ANTHROPIC_OK -eq 1 ]; then
        echo -e "${GREEN}  ✓ Anthropic API key configured${NC}"
    else
        echo -e "${RED}  ✗ Anthropic API key missing${NC}"
    fi
else
    echo -e "${RED}✗ Backend is NOT running${NC}"
    echo "  Start with: cd backend && python3 app.py"
fi
echo ""

# Check Frontend (Port 3000)
echo "2. Checking Frontend (Port 3000)..."
if curl -s --max-time 3 http://localhost:3000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${RED}✗ Frontend is NOT running${NC}"
    echo "  Start with: cd frontend && python3 -m http.server 3000"
fi
echo ""

# Check CORS
echo "3. Checking CORS Configuration..."
CORS=$(curl -s -H "Origin: http://localhost:3000" -I http://localhost:8000/api/health 2>&1 | grep -i "access-control-allow-origin")
if [ ! -z "$CORS" ]; then
    echo -e "${GREEN}✓ CORS is properly configured${NC}"
    echo "  $CORS"
else
    echo -e "${YELLOW}⚠ Could not verify CORS (backend might be down)${NC}"
fi
echo ""

# Check port forwarding
echo "4. Checking Port Forwarding..."
PORTS=$(lsof -i :3000,8000 2>/dev/null | grep LISTEN | wc -l)
if [ $PORTS -eq 2 ]; then
    echo -e "${GREEN}✓ Both ports are listening${NC}"
    lsof -i :3000,8000 | grep LISTEN | awk '{print "  Port " $9 " - " $1 " (PID: " $2 ")"}'
else
    echo -e "${YELLOW}⚠ Not all services detected${NC}"
fi
echo ""

# Test API endpoint
echo "5. Testing API Issues Endpoint..."
if curl -s --max-time 5 http://localhost:8000/api/issues?limit=1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Issues endpoint is working${NC}"
    ISSUE_COUNT=$(curl -s http://localhost:8000/api/issues?limit=100 | grep -o '"number":' | wc -l)
    echo "  Found $ISSUE_COUNT issues"
else
    echo -e "${RED}✗ Issues endpoint failed${NC}"
fi
echo ""

# Final recommendation
echo "=================================="
echo "Recommendations:"
echo "=================================="

BACKEND_OK=$(curl -s --max-time 3 http://localhost:8000/api/health > /dev/null 2>&1 && echo "1" || echo "0")
FRONTEND_OK=$(curl -s --max-time 3 http://localhost:3000/ > /dev/null 2>&1 && echo "1" || echo "0")

if [ $BACKEND_OK -eq 1 ] && [ $FRONTEND_OK -eq 1 ]; then
    echo -e "${GREEN}✓ All services are running!${NC}"
    echo ""
    echo "Access the dashboard at:"
    echo "  → http://localhost:3000"
    echo ""
    echo "If using port forwarding (Cursor/VSCode):"
    echo "  1. Check Ports panel for forwarded ports"
    echo "  2. Access: http://localhost:FORWARDED_PORT/?api=http://localhost:BACKEND_PORT/api"
    echo ""
    echo "Test page available at:"
    echo "  → http://localhost:3000/test.html"
elif [ $BACKEND_OK -eq 0 ] && [ $FRONTEND_OK -eq 0 ]; then
    echo -e "${RED}✗ Both services are down${NC}"
    echo ""
    echo "Start backend:"
    echo "  cd $(dirname $0)/backend"
    echo "  python3 app.py"
    echo ""
    echo "Start frontend (in another terminal):"
    echo "  cd $(dirname $0)/frontend"
    echo "  python3 -m http.server 3000"
elif [ $BACKEND_OK -eq 0 ]; then
    echo -e "${RED}✗ Backend is down${NC}"
    echo ""
    echo "Start backend:"
    echo "  cd $(dirname $0)/backend"
    echo "  python3 app.py"
else
    echo -e "${RED}✗ Frontend is down${NC}"
    echo ""
    echo "Start frontend:"
    echo "  cd $(dirname $0)/frontend"
    echo "  python3 -m http.server 3000"
fi

echo ""
echo "For detailed troubleshooting, see:"
echo "  $(dirname $0)/TROUBLESHOOTING.md"
echo ""



