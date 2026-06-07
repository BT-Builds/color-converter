# Color Converter API

Convert colors between hex, RGB, HSL, and CSS color names.

## Endpoints

- `GET /health` - No auth. Health check.
- `POST /convert` - Convert colors. Auth required.
- `GET /random` - Random color. Auth required.

## Authentication
Include `X-API-Key` header (min 10 characters). Rate limited to 100 requests/minute.

## Example
```bash
curl -X POST https://color-converter-three-omega.vercel.app/convert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"input": "#ff0000", "from_format": "hex", "to_format": "rgb"}'
```

## Postman
[![Run in Postman](https://run.pstmn.io/button.svg)](https://raw.githubusercontent.com/BT-Builds/color-converter/main/postman_collection.json)
