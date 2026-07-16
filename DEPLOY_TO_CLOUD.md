# 🚀 Deploy Real Estate CRM to Cloud

## Quick Deploy (5 minutes)

### Option 1: Render.com (Recommended - Easiest)

**Step 1: Push to GitHub**
```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Ready for cloud deployment"
git remote add origin https://github.com/YOUR_USERNAME/RealEstate_CRM.git
git push -u origin main
```

**Step 2: Deploy on Render**
1. Go to [render.com](https://render.com) and sign up (free)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `real-estate-crm`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Click **"Create Web Service"**

**Step 3: Access Your CRM**
- Your app will be live at: `https://real-estate-crm.onrender.com`
- Login: `admin` / `admin`
- Change password after first login!

---

### Option 2: Railway.app

**Step 1: Deploy**
1. Go to [railway.app](https://railway.app) and sign up
2. Click **"New Project"** → **"Deploy from GitHub"**
3. Select your repository
4. Railway auto-detects Python and deploys

**Step 2: Configure**
- Add environment variable: `CRM_DB_PATH=/app/data/real_estate_crm.db`
- Railway provides a public URL automatically

---

### Option 3: Fly.io (Always-On)

**Step 1: Install Fly CLI**
```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

**Step 2: Launch**
```bash
fly launch
# Follow the prompts
fly deploy
```

**Step 3: Access**
```bash
fly apps list  # See your app URL
```

---

## Free Tier Comparison

| Platform | Free Tier | Sleep After | Data Persistence | Custom Domain |
|----------|-----------|-------------|------------------|---------------|
| **Render** | ✅ Yes | 15 min | ❌ No (needs paid plan) | ✅ Yes |
| **Railway** | ✅ $5 credit | Never (while credit lasts) | ✅ Yes | ✅ Yes |
| **Fly.io** | ✅ Pay-as-you-go | Never | ✅ Yes | ✅ Yes |

## Important Notes

### First Login
- Default credentials: `admin` / `admin`
- **Change password immediately after first login!**
- The database is created automatically on first run

### Data Backup
Since free tiers may lose data on redeploy:
1. Use the **Backup** feature in the app (Tools → Backup)
2. Download backup files regularly
3. Consider upgrading to a paid plan for production use

### Custom Domain (Optional)
After deployment, you can add a custom domain:
1. **Render:** Settings → Custom Domains → Add your domain
2. **Railway:** Settings → Networking → Custom Domain
3. **Fly.io:** `fly certs add yourdomain.com`

### Environment Variables
For advanced configuration, set these in your hosting platform:
```
CRM_DB_PATH=/app/data/real_estate_crm.db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
ADMIN_EMAIL=your@email.com
```

## Troubleshooting

### App Won't Start
1. Check logs in your hosting dashboard
2. Verify all dependencies are in `requirements.txt`
3. Ensure `backend/main.py` exists and is correct

### Database Errors
1. The app auto-creates the SQLite database
2. If data is lost, restore from backup
3. For persistent data, use PostgreSQL addon

### Slow First Load
- Free tiers "sleep" after inactivity
- First request takes 30-60 seconds to wake up
- This is normal for free hosting

## Next Steps

After successful deployment:
1. ✅ Test all features in the browser
2. ✅ Change default admin password
3. ✅ Add your company information (Settings)
4. ✅ Import your data (if any)
5. ✅ Share the URL with your team
6. ✅ Bookmark the URL on mobile devices (PWA support)

## Mobile Access

Your CRM works great on mobile:
1. Open the URL in Chrome/Safari on your phone
2. Tap the menu → "Add to Home Screen"
3. Now it works like a native app!

---

**Need help?** Check your hosting platform's documentation or deployment logs.
