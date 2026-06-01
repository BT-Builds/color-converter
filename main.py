import re
import random
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from mangum import Mangum

app = FastAPI(title="Color Converter API", version="1.0.0")

# Rate limiting storage
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

# Color names to hex mapping (CSS color names)
COLOR_NAMES = {
    "aliceblue": "#f0f8ff", "antiquewhite": "#faebd7", "aqua": "#00ffff",
    "black": "#000000", "blue": "#0000ff", "brown": "#a52a2a",
    "green": "#008000", "red": "#ff0000", "yellow": "#ffff00",
    "white": "#ffffff", "gray": "#808080", "orange": "#ffa500"
}

HEX_TO_NAME = {v: k for k, v in COLOR_NAMES.items()}

def parse_hex(hex_val: str) -> tuple:
    hex_val = hex_val.lstrip("#")
    if len(hex_val) == 3:
        hex_val = "".join(c * 2 for c in hex_val)
    return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"

def parse_rgb(rgb_val: str) -> tuple:
    match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", rgb_val)
    if not match:
        raise ValueError("Invalid RGB format")
    return tuple(int(m) for m in match.groups())

def rgb_to_hsl(r: int, g: int, b: int) -> tuple:
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

def parse_hsl(hsl_val: str) -> tuple:
    match = re.match(r"hsl\s*\(\s*(\d+)\s*,\s*(\d+)%?\s*,\s*(\d+)%?\s*\)", hsl_val)
    if not match:
        raise ValueError("Invalid HSL format")
    return tuple(int(m) for m in match.groups())

def hsl_to_rgb(h: int, s: int, l: int) -> tuple:
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

def get_closest_color_name(hex_val: str) -> str:
    return HEX_TO_NAME.get(hex_val)

def convert_color(input_val: str, from_fmt: str, to_fmt: str):
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

@app.get("/random")
async def random_color(api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    hex_val = rgb_to_hex(r, g, b)
    h, s, l = rgb_to_hsl(r, g, b)
    return {
        "success": True,
        "data": {
            "hex": hex_val,
            "rgb": f"rgb({r}, {g}, {b})",
            "hsl": f"hsl({h}, {s}%, {l}%)",
            "name": get_closest_color_name(hex_val) or None
        }
    }

handler = Mangum(app)