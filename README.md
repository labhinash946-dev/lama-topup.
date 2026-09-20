# Lama Topup Flask Backend

## Render settings

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Keep `DRY_RUN=true` while testing.

## GoXtop configuration

Required environment variables:

- `GOXTOP_API_KEY`: your private GoXtop key
- `GOXTOP_BASE_URL`: `https://goxtop.com/api/v.1`
- `GOXTOP_FREEFIRE_GAME_CODE`: `freefire_global`
- `GOXTOP_CREATE_PATH`: `/create`
- `DRY_RUN`: `true` during testing, `false` only after payment verification is implemented

Free Fire package code variables:

- `FF_25_CODE`
- `FF_50_CODE`
- `FF_115_CODE`
- `FF_240_CODE`
- `FF_610_CODE`
- `FF_1240_CODE`
- `FF_2530_CODE`
- `FF_WEEKLY_CODE`
- `FF_MONTHLY_CODE`

Each package code must be the exact GoXtop `Pack`/denomination value returned by the products endpoint. Do not guess these values.

## Routes

- `GET /api/health`
- `GET /api/games`
- `GET /api/products/<game_code>`
- `GET /api/balance`
- `POST /api/orders`
- `GET /api/orders/<partner_orderid>`
- `POST /api/orders/<partner_orderid>/track`

The order payload sent to GoXtop uses `game`, `denom`, `userid`, and `partner_orderid`, with optional `server_code`.

Never put the GoXtop API key in frontend JavaScript or commit it to GitHub.
