import re
import random
import secrets
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from mangum import Mangum

app = FastAPI(title="Color Converter API", version="1.0.0")
# === BT Builds Standard Middleware (auto-injected) ===
from fastapi.middleware.cors import CORSMiddleware as _BTCors
app.add_middleware(_BTCors, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], expose_headers=["X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset"])

@app.middleware("http")
async def _bt_add_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "btbuilds"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# Color names to hex mapping (CSS color names)
COLOR_NAMES = {
    "aliceblue": "#f0f8ff", "antiquewhite": "#faebd7", "aqua": "#00ffff",
    "aquamarine": "#7fffd4", "azure": "#f0ffff", "beige": "#f5f5dc",
    "bisque": "#ffe4c4", "black": "#000000", "blanchedalmond": "#ffebcd",
    "blue": "#0000ff", "blueviolet": "#8a2be2", "brown": "#a52a2a",
    "burlywood": "#deb887", "cadetblue": "#5f9ea0", "chartreuse": "#7fff00",
    "chocolate": "#d2691e", "coral": "#ff7f50", "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc", "crimson": "#dc143c", "cyan": "#00ffff",
    "darkblue": "#00008b", "darkcyan": "#008b8b", "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9", "darkgreen": "#006400", "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b", "darkolivegreen": "#556b2f", "darkorange": "#ff8c00",
    "darkorchid": "#9932cc", "darkred": "#8b0000", "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f", "darkslateblue": "#483d8b", "darkslategray": "#2f4f4f",
    "darkturquoise": "#00ced1", "darkviolet": "#9400d3", "deeppink": "#ff1493",
    "deepskyblue": "#00bfff", "dimgray": "#696969", "dodgerblue": "#1e90ff",
    "firebrick": "#b22222", "floralwhite": "#fffaf0", "forestgreen": "#228b22",
    "fuchsia": "#ff00ff", "gainsboro": "#dcdcdc", "ghostwhite": "#f8f8ff",
    "gold": "#ffd700", "goldenrod": "#daa520", "gray": "#808080",
    "green": "#008000", "greenyellow": "#adff2f", "honeydew": "#f0fff0",
    "hotpink": "#ff69b4", "indianred": "#cd5c5c", "indigo": "#4b0082",
    "ivory": "#fffff0", "khaki": "#f0e68c", "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5", "lawngreen": "#7cfc00", "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6", "lightcoral": "#f08080", "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2", "lightgray": "#d3d3d3", "lightgreen": "#90ee90",
    "lightpink": "#ffb6c1", "lightsalmon": "#ffa07a", "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa", "lightslategray": "#778899", "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0", "lime": "#00ff00", "limegreen": "#32cd32",
    "linen": "#faf0e6", "magenta": "#ff00ff", "maroon": "#800000",
    "mediumaquamarine": "#66cdaa", "mediumblue": "#0000cd", "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db", "mediumseagreen": "#3cb371", "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a", "mediumturquoise": "#48d1cc", "mediumvioletred": "#c71585",
    "midnightblue": "#191970", "mintcream": "#f5fffa", "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5", "navajowhite": "#ffdead", "navy": "#000080",
    "oldlace": "#fdf5e6", "olive": "#808000", "olivedrab": "#6b8e23",
    "orange": "#ffa500", "orangered": "#ff4500", "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa", "palegreen": "#98fb98", "paleturquoise": "#afeeee",
    "palevioletred": "#db7093", "papayawhip": "#ffefd5", "peachpuff": "#ffdab9",
    "peru": "#cd853f", "pink": "#ffc0cb", "plum": "#dda0dd",
    "powderblue": "#b0e0e6", "purple": "#800080", "rebeccapurple": "#663399",
    "red": "#ff0000", "rosybrown": "#bc8f8f", "royalblue": "#4169e1",
    "saddlebrown": "#8b4513", "salmon": "#fa8072", "sandybrown": "#f4a460",
    "seagreen": "#2e8b57", "seashell": "#fff5ee", "sienna": "#a0522d",
    "silver": "#c0c0c0", "skyblue": "#87ceeb", "slateblue": "#6a5acd",
    "slategray": "#708090", "snow": "#fffafa", "springgreen": "#00ff7f",
    "steelblue": "#4682b4", "tan": "#d2b48c", "teal": "#008080",
    "thistle": "#d8bfd8", "tomato": "#ff6347", "turquoise": "#40e0d0",
    "violet": "#800080", "wheat": "#f5deb3", "white": "#ffffff",
    "whitesmoke": "#f5f5f5", "yellow": "#ffff00", "yellowgreen": "#9acd32"
}

HEX_TO_NAME = {v: k for k, v in COLOR_NAMES.items()}

rate_limits = {}

def verify_api_key(x_api_key: str = None):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="API key required")
    if len(x_api_key) < 10:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

def check_rate_limit(api_key: str):
    import time
    current = int(time.time())
    minute_key = f"{api_key}:{current // 60}"
    if minute_key not in rate_limits:
        rate_limits[minute_key] = 0
    rate_limits[minute_key] += 1
    for k in list(rate_limits.keys()):
        if int(k.split(":")[1]) < current // 60 - 1:
            del rate_limits[k]
    if rate_limits[minute_key] > 100:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return True

class ColorConvertRequest(BaseModel):
    input: str
    from_format: str
    to_format: str

class BulkConvertRequest(BaseModel):
    items: list

def parse_hex(hex_val: str):
    hex_val = hex_val.lstrip("#")
    if len(hex_val) == 3:
        hex_val = "".join(c * 2 for c in hex_val)
    return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"

def parse_rgb(rgb_val: str):
    match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", rgb_val)
    if not match:
        raise ValueError("Invalid RGB format")
    return tuple(int(m) for m in match.groups())

def rgb_to_hsl(r, g, b):
    r, g, b = r/255, g/255, b/255
    mx, mn = max(r, g, b), min(r, g, b)
    diff = mx - mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g - b) / diff) + 360) % 360
    elif mx == g:
        h = 60 * ((b - r) / diff) + 120
    else:
        h = 60 * ((r - g) / diff) + 240
    l = (mx + mn) / 2
    s = 0 if mx == mn else (diff / (1 - abs(2 * l - 1)) if l < 0.5 else diff / (2 - (2 * l - 1)))
    return int(h), int(s * 100), int(l * 100)

def parse_hsl(hsl_val: str):
    match = re.match(r"hsl\s*\(\s*(\d+)\s*,\s*(\d+)%?\s*,\s*(\d+)%?\s*\)", hsl_val)
    if not match:
        raise ValueError("Invalid HSL format")
    return tuple(int(m) for m in match.groups())

def hsl_to_rgb(h, s, l):
    s, l = s/100, l/100
    c = (1 - abs(2*l - 1)) * s
    x = c * (1 - abs((h/60) % 2 - 1))
    m = l - c/2
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

def get_closest_color_name(hex_val: str):
    if hex_val in HEX_TO_NAME:
        return HEX_TO_NAME[hex_val]
    return None

def convert_color(input_val, from_fmt, to_fmt):
    r = g = b = 0
    if from_fmt == "hex":
        r, g, b = parse_hex(input_val)
    elif from_fmt == "rgb":
        r, g, b = parse_rgb(input_val)
    elif from_fmt == "hsl":
        h, s, l = parse_hsl(input_val)
        r, g, b = hsl_to_rgb(h, s, l)
    elif from_fmt == "name":
        hex_val = COLOR_NAMES.get(input_val.lower())
        if not hex_val:
            raise ValueError(f"Unknown color name: {input_val}")
        r, g, b = parse_hex(hex_val)
    else:
        raise ValueError(f"Unknown from_format: {from_fmt}")
    if to_fmt == "hex":
        result = rgb_to_hex(r, g, b)
    elif to_fmt == "rgb":
        result = f"rgb({r}, {g}, {b})"
    elif to_fmt == "hsl":
        h, s, l = rgb_to_hsl(r, g, b)
        result = f"hsl({h}, {s}%, {l}%)"
    elif to_fmt == "name":
        result = get_closest_color_name(rgb_to_hex(r, g, b))
        if not result:
            result = None
    else:
        raise ValueError(f"Unknown to_format: {to_fmt}")
    return {"input": input_val, "from": from_fmt, "to": to_fmt, "result": result}

@app.get("/health")
def health():
    return {"status": "ok", "service": "Color Converter API"}

@app.post("/convert")
async def convert(req: ColorConvertRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    try:
        result = convert_color(req.input, req.from_format, req.to_format)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bulk/convert")
async def bulk_convert(req: BulkConvertRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    if len(req.items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    for item in req.items:
        try:
            input_val = item.get("input")
            from_fmt = item.get("from_format")
            to_fmt = item.get("to_format")
            if not all([input_val, from_fmt, to_fmt]):
                results.append({"input": item.get("input"), "output": None, "error": "Missing required fields: input, from_format, to_format"})
                continue
            output = convert_color(input_val, from_fmt, to_fmt)
            results.append({"input": input_val, "output": output, "error": None})
            successful += 1
        except ValueError as e:
            results.append({"input": item.get("input"), "output": None, "error": str(e)})
        except Exception as e:
            results.append({"input": item.get("input"), "output": None, "error": str(e)})
    
    return {"results": results, "total": len(req.items), "successful": successful}

@app.get("/random")
async def random_color(api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    hex_val = rgb_to_hex(r, g, b)
    h, s, l = rgb_to_hsl(r, g, b)
    return {"success": True, "data": {"hex": hex_val, "rgb": f"rgb({r}, {g}, {b})", "hsl": f"hsl({h}, {s}%, {l}%)", "name": get_closest_color_name(hex_val) or None}}

handler = Mangum(app)