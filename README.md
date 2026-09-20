# Lama Topup Flask Backend

Render:
- Build Command: pip install -r requirements.txt
- Start Command: gunicorn app:app

Environment variables:
GOXTOP_API_KEY, GOXTOP_BASE_URL, GOXTOP_FREEFIRE_GAME_CODE,
GOXTOP_ORDER_PATH, FRONTEND_ORIGIN, DRY_RUN

API routes:
GET /api/health
GET /api/freefire/products
POST /api/orders

Keep DRY_RUN=true until payment verification and the exact GoXtop
create-order payload are confirmed from the official documentation.
Never put the GoXtop API key in frontend JavaScript.
