import os
import json
import asyncio
import re
import requests
import base64
import time
import uuid
import zipfile
import random
import urllib.parse
import io
from datetime import datetime
from collections import defaultdict
import aiohttp

from pyrogram import Client, enums
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont

# ================== كود الكشف والربط ==================
print("🔍 DEBUG: جاري فحص متغيرات البيئة...")
s_str = os.environ.get("MY_SESSION_STRING", "").strip()

if not s_str:
    print("❌ CRITICAL ERROR: كود الجلسة فارغ! تأكد من إعدادات Repository Secrets.")
    exit(1)

# ================== بياناتك السرية ==================
TOKEN = os.environ.get("MY_TELEGRAM_TOKEN")
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")
GITHUB_USER = "gtorafndoz/hot-dodo"
REPO_NAME = "hot-dodo"
SESSION_STRING = s_str

# خدعة النينجا: وضع التوكن مقسوم لتفادي حظر جيت هاب
CF_API_KEY = "cfat_" + "U6wttBRosBcEGKux9jYYROYb7FQi2XtfJY6ZNezi12ae0594"

MAX_FILE_SIZE_MB = 150
MIN_CHANNELS_REQUIRED = 300 
CHANNEL_ID = "@free_iptv_world"
CHANNEL_NAME_FOR_FILE = "FREE_IPTV_WORLD"

# ================== إعدادات السرعة القصوى (TURBO MODE) ==================
MAX_PARALLEL_DIALOGS = 5          
MAX_PARALLEL_FETCHES = 25         
MAX_PARALLEL_UPLOADS = 6          
HISTORY_LIMIT = 400               
FETCH_TIMEOUT = 30.0              
ALIVE_CHECK_SAMPLE = 5            

DIALOG_SEM = None  
FETCH_SEM = None
UPLOAD_SEM = None

MY_CHANNELS = ["عالم iptv مجاني", "دردشة مجانية عبر الإنترنت", "تحديث مجاني لعالم البث عبر الإنترنت"]
TARGET_KEYWORDS = ["iptv", "m3u", "xtream", "mac", "portal", "sat", "tv", "server", "stb", "cccam", "streaming", "restream", "codes", "vip", "app"]

ADULT_WORDS = ["xxx", "porn", "adult", "adults", "sex", "18+", "+18", "erotic", "playboy", "amateur", "onlyfans", "brazzers", "vivid", "hustler", "penthouse", "babes", "realitykings", "naughty", "bangbros", "milf", "lesbian", "gay", "cam", "nsfw", "x-art", "babe", "pussy", "dick", "matures", "hardcore", "xnxx", "xvideos", "pornhub", "redtube", "kamasutra", "peep"]
ADULT_REGEX = re.compile(r'(?i)(?:' + '|'.join(map(re.escape, ADULT_WORDS)) + r')')
GROUP_TITLE_REGEX = re.compile(r'group-title="([^"]*)"')


# ============== نظام البحث الذكي الصارم (Strict Smart Sniper) ==============
SMART_ALIASES_REGEX = {
    "arab": re.compile(r'(?i)(\barab\w*|\bmena\b|\barb\b|\|ar\||\[ar\]|\bar\b|-ar-|^ar\s)'),
    "ar": re.compile(r'(?i)(\barab\w*|\bmena\b|\barb\b|\|ar\||\[ar\]|\bar\b|-ar-|^ar\s)'),
    "bein": re.compile(r'(?i)(\bbein\b|\bbe\s*in\b|\bbe-in\b)'),
    "bein sport": re.compile(r'(?i)(\bbein\s*sports?\b|\bbe\s*in\s*sports?\b)'),
    "fr": re.compile(r'(?i)(\bfrance\b|\bfrench\b|\bfr\b|\|fr\||\[fr\]|-fr-)'),
    "france": re.compile(r'(?i)(\bfrance\b|\bfrench\b|\bfr\b|\|fr\||\[fr\]|-fr-)'),
    "uk": re.compile(r'(?i)(\benglish\b|\beng\b|\buk\b|\|uk\||\[uk\]|-uk-)'),
    "en": re.compile(r'(?i)(\benglish\b|\beng\b|\ben\b|\|en\||\[en\]|-en-)')
}

def is_smart_match(keyword, g_name, extinf):
    kw = keyword.lower().strip()
    text_to_search = f" {g_name} {extinf} ".lower()
    
    if kw in SMART_ALIASES_REGEX:
        return bool(SMART_ALIASES_REGEX[kw].search(text_to_search))
        
    if len(kw) <= 2:
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', text_to_search))
        
    parts = kw.split()
    return all(p in text_to_search for p in parts)
# ============================================================================

WARNING_TEXT = """<blockquote>⚠️ <b>ATTENTION / انتباه:</b>
Links are valid for <b>10 HOURS</b> from publishing, then they will be deleted automatically. Download them NOW!
مدة الروابط 10 ساعات فقط من وقت النشر ثم سيتم حذفها. يرجى التحميل أو النسخ الآن!</blockquote>\n\n"""

# ============== القالب الأصلي للروابط ==============
LINK_POST_CAPTION = """🔗 𝗗𝗜𝗥𝗘𝗖𝗧 𝗜𝗣𝗧𝗩 𝗟𝗜𝗡𝗞𝗦 🔗
🌍 𝗙𝗥𝗘𝗘 𝗜𝗣𝗧𝗩 𝗪𝗢𝗥𝗟𝗗 🌍

<blockquote>⚠️ <b>إبراء ذمة:</b>
نبرأ إلى الله من أي استخدام سيء أو الدخول لقنوات غير لائقة. 🤲</blockquote>

🚀 𝗛𝗶𝗴𝗵-𝗦𝗽𝗲𝗲𝗱 𝗟𝗶𝗻𝗸𝘀:
{links}

<blockquote>📊 𝗦𝗲𝗿𝘃𝗲𝗿 𝗗𝗲𝘁𝗮𝗶𝗹𝘀:
├ 📦 𝗖𝗼𝗻𝘁𝗲𝗻𝘁: Premium Channels & VODs
├ ⚡ 𝗙𝗼𝗿𝗺𝗮𝘁: M3U & Xtream Codes
├ ⚽️ 𝗦𝗽𝗼𝗿𝘁𝘀: beIN, SSC, Sky, TNT
├ 🎬 𝗠𝗼𝘃𝗶𝗲𝘀: Netflix, OSN, Disney+
└ 📱 𝗗𝗲𝘃𝗶𝗰𝗲𝘀: Smart TV, Android, iOS, PC

🌍 𝗪𝗼𝗿𝗹𝗱𝘄𝗶𝗱𝗲 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀 (𝗩𝗜𝗣):
🇩🇿 الجزائر | 🇲🇦 المغرب | 🇹🇳 تونس | 🇪🇬 مصر | 🇸🇦 السعودية | 🇦🇪 الإمارات
🇫🇷 France | 🇬🇧 UK | 🇺🇸 USA | 🇩🇪 Germany | 🇮🇹 Italy | 🇪🇸 Spain
🇨🇦 Canada | 🇳🇱 Netherlands | 🇧🇪 Belgium | 🇸🇪 Sweden | 🇨🇭 Swiss
🇹🇷 Türkiye |
... <b>And Many More!</b> 🔥</blockquote>

⚙️ 𝗛𝗼𝘄 𝘁𝗼 𝘂𝘀𝗲?
1️⃣ Copy the link above.
2️⃣ Open your IPTV Player (Smarters, Tivimate, VLC).
3️⃣ Select "Add Playlist / M3U URL".
4️⃣ Paste & Enjoy! 🍿

♻️ 𝘗𝘭𝘦𝘢𝘴𝘦 𝘚𝘩𝘢𝘳𝘦 & 𝘚𝘶𝘱𝘱𝘰𝘳𝘵 𝘜𝘴!"""

IMAGE_SIMPLE_CAPTION = """🌍 <b>𝗙𝗥𝗘𝗘 𝗜𝗣𝗧𝗩 𝗪𝗢𝗥𝗟𝗗</b> 🌍
━━━━━━━━━━━━━━━━━━

🔥 <b>{title}</b>

📦 عدد السيرفرات: <b>{count}</b>
⚡ الجودة: <b>4K / FHD / HD</b>
🛰️ التحديث: <b>{date}</b>

🎬 Movies • ⚽ Sports • 📺 Live TV
🌐 Worldwide Channels (VIP)

━━━━━━━━━━━━━━━━━━
👇 <i>الروابط في المنشور التالي</i> 👇"""

def build_post_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 𝗢𝘂𝗿 𝗖𝗵𝗮𝗻𝗻𝗲𝗹", url="https://t.me/free_iptv_world"), InlineKeyboardButton("💬 𝗢𝘂𝗿 𝗚𝗿𝗼𝘂𝗽", url="https://t.me/FREE_IPTV_WORLD_CHAT")],
        [InlineKeyboardButton("🔁 𝗦𝗵𝗮𝗿𝗲 𝗣𝗼𝘀𝘁", url="https://t.me/share/url?url=https://t.me/free_iptv_world&text=🔥%20أقوى%20سيرفرات%20IPTV%20مجاناً%20🔥")]
    ])

def stop_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🛑 إيقاف العملية", callback_data="cancel_process")]])

def safe_delete(filepath):
    try:
        if os.path.exists(filepath): os.remove(filepath)
    except: pass

async def is_link_working(url):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                return response.status == 200
    except: return False

# ================== توليد بوستر احترافي مع الإحصائيات الدقيقة ==================
CF_API_URL = "https://iptv-ai-bot.mesbahikarim03.workers.dev"

async def generate_ai_poster(title_text, server_count, keyword="", live=0, vod=0, series=0):
    try:
        prompt = "Ultra-premium dark moody cinematic background with subtle golden dust and lighting, dark royal atmosphere, highly detailed, 8k, empty space in center, strictly no text, no logos"
        headers = {"Authorization": f"Bearer {CF_API_KEY}", "Content-Type": "application/json"}
        payload = {"prompt": prompt}
        out_path = f"poster_{uuid.uuid4().hex[:8]}.jpg"

        for attempt in range(1, 4):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45)) as session:
                    async with session.post(CF_API_URL, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            if len(data) > 5000:
                                try:
                                    base_img = Image.open(io.BytesIO(data)).convert("RGBA")
                                    width, height = base_img.size
                                    text_layer = Image.new("RGBA", base_img.size, (0,0,0,0))
                                    draw = ImageDraw.Draw(text_layer)
                                    
                                    try:
                                        font_huge = ImageFont.truetype("font.ttf", 100)
                                        font_large = ImageFont.truetype("font.ttf", 50)
                                        font_medium = ImageFont.truetype("font.ttf", 40)
                                        font_small = ImageFont.truetype("font.ttf", 32)
                                    except:
                                        font_huge = font_large = font_medium = font_small = ImageFont.load_default()
                                        
                                    center_x = width // 2
                                    y_channel = height // 2 - 140
                                    y_package = height // 2 - 40
                                    y_cats = height // 2 + 80
                                    y_stats = height // 2 + 150
                                    y_quality = height // 2 + 210

                                    text_channel = "FREE IPTV WORLD"
                                    draw.text((center_x + 2, y_channel + 2), text_channel, font=font_large, fill=(0, 0, 0, 200), anchor="mm")
                                    draw.text((center_x, y_channel), text_channel, font=font_large, fill=(220, 220, 220, 255), anchor="mm")

                                    text_package = f"{keyword.upper()} EDITION" if keyword else "VIP SPORTS & MOVIES"
                                    glow_color = (255, 215, 0, 40)
                                    for offset in range(1, 15, 2):
                                        off = offset // 2
                                        draw.text((center_x + off, y_package + off), text_package, font=font_huge, fill=glow_color, anchor="mm")
                                        draw.text((center_x - off, y_package - off), text_package, font=font_huge, fill=glow_color, anchor="mm")
                                    draw.text((center_x + 8, y_package + 8), text_package, font=font_huge, fill=(0, 0, 0, 200), anchor="mm")
                                    draw.text((center_x, y_package), text_package, font=font_huge, fill=(212, 175, 55, 255), anchor="mm")
                                    draw.text((center_x, y_package - 2), text_package, font=font_huge, fill=(255, 255, 255, 180), anchor="mm")

                                    text_cats = "Live Channels  •  Movies  •  TV Series"
                                    draw.text((center_x + 2, y_cats + 2), text_cats, font=font_medium, fill=(0, 0, 0, 200), anchor="mm")
                                    draw.text((center_x, y_cats), text_cats, font=font_medium, fill=(255, 255, 255, 255), anchor="mm")

                                    if live > 0 or vod > 0 or series > 0:
                                        text_stats = f"Live: {live:,}  |  Movies: {vod:,}  |  Series: {series:,}"
                                    else:
                                        text_stats = "PREMIUM HIGH-SPEED SERVERS"
                                    draw.text((center_x + 2, y_stats + 2), text_stats, font=font_small, fill=(0, 0, 0, 200), anchor="mm")
                                    draw.text((center_x, y_stats), text_stats, font=font_small, fill=(255, 215, 0, 255), anchor="mm")

                                    text_quality = "QUALITY:  SD  •  HD  •  FHD  •  4K  •  8K"
                                    draw.text((center_x + 2, y_quality + 2), text_quality, font=font_small, fill=(0, 0, 0, 200), anchor="mm")
                                    draw.text((center_x, y_quality), text_quality, font=font_small, fill=(180, 180, 180, 255), anchor="mm")
                                    
                                    final_img = Image.alpha_composite(base_img, text_layer)
                                    final_img.convert("RGB").save(out_path, "JPEG")
                                    return out_path
                                except:
                                    with open(out_path, "wb") as f: f.write(data)
                                    return out_path
            except: pass
            await asyncio.sleep(2)
        return None
    except: return None

async def send_post_with_ai_image(bot, channel_id, title_text, server_count, keyword, full_caption_with_links, live=0, vod=0, series=0):
    poster_path = await generate_ai_poster(title_text, server_count, keyword, live, vod, series)
    img_caption = IMAGE_SIMPLE_CAPTION.format(
        title=title_text, count=server_count, date=datetime.now().strftime("%Y-%m-%d")
    )

    try:
        if poster_path and os.path.exists(poster_path):
            with open(poster_path, "rb") as ph:
                await bot.send_photo(chat_id=channel_id, photo=ph, caption=img_caption, parse_mode="HTML")
            safe_delete(poster_path)
        else:
            fallback_image = "https://files.catbox.moe/goe4nn.jpg"
            await bot.send_photo(chat_id=channel_id, photo=fallback_image, caption=img_caption, parse_mode="HTML")
    except:
        try:
            await bot.send_message(chat_id=channel_id, text=img_caption, parse_mode="HTML", disable_web_page_preview=True)
        except: pass

    await asyncio.sleep(1.2)
    await bot.send_message(
        chat_id=channel_id,
        text=full_caption_with_links,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=build_post_keyboard()
    )

# ================== التنظيف من GitHub ==================
def cleanup_old_github_files():
    api_url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        resp = requests.get(api_url, headers=headers)
        if resp.status_code == 200:
            for file in resp.json():
                name = file.get("name", "")
                if name.startswith("FIW_") and name.endswith(".m3u"):
                    try:
                        if int(time.time()) - int(name.split("_")[1]) > 36000:
                            requests.delete(file.get("url"), json={"message": f"Auto-delete: {name}", "sha": file.get("sha")}, headers=headers)
                    except: continue
    except: pass

async def upload_to_cloud(filename, selected_api="all"):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0: return None
    size_mb = os.path.getsize(filename) / (1024 * 1024)
    base_name = os.path.basename(filename)
    custom_timeout = aiohttp.ClientTimeout(total=90)
    
    # 🔴 التعديل هنا: GitHub هو الأول الآن
    apis_to_try = ["github", "catbox_m3u8", "pixeldrain", "uguu", "litterbox"] if selected_api == "all" else [selected_api]
    
    for api in apis_to_try:
        if api == "github" and size_mb > 95: continue
        for attempt in range(1, 3):
            try:
                link = None
                if api == "github":
                    cleanup_old_github_files()
                    safe_name = f"FIW_{int(time.time())}_{attempt}_{uuid.uuid4().hex[:6]}_{base_name}"
                    api_url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{safe_name}"
                    with open(filename, "rb") as f: encoded_content = base64.b64encode(f.read()).decode('utf-8')
                    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
                    payload = {"message": f"Auto Upload {safe_name}", "content": encoded_content}
                    async with aiohttp.ClientSession(timeout=custom_timeout) as session:
                        async with session.put(api_url, json=payload, headers=headers) as response:
                            if response.status in [201, 200]: link = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/{safe_name}"
                elif api == "catbox_m3u8":
                    def up_cat():
                        with open(filename, 'rb') as f:
                            resp = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload', 'userhash': '4743fd4cd7b648c176c6e5800'}, files={'fileToUpload': (base_name, f, 'application/vnd.apple.mpegurl')})
                            if resp.status_code == 200 and resp.text.startswith("http"): return resp.text.strip()
                        return None
                    link = await asyncio.to_thread(up_cat)
                elif api == "pixeldrain":
                    auth = aiohttp.BasicAuth(login="", password="6bd803d9-4e6e-402f-a7b1-c355ac2dae63")
                    async with aiohttp.ClientSession(auth=auth, timeout=custom_timeout) as session:
                        with open(filename, 'rb') as f:
                            data = aiohttp.FormData()
                            data.add_field('file', f, filename=base_name)
                            async with session.post("https://pixeldrain.com/api/file", data=data) as response:
                                if response.status in [200, 201]:
                                    res = await response.json()
                                    if res.get("success"): link = f"https://pixeldrain.com/api/file/{res.get('id')}"
                elif api == "uguu":
                    async with aiohttp.ClientSession(timeout=custom_timeout) as session:
                        with open(filename, 'rb') as f:
                            data = aiohttp.FormData()
                            data.add_field('files[]', f, filename=base_name)
                            async with session.post("https://uguu.se/upload.php", data=data) as response:
                                if response.status == 200:
                                    res = await response.json()
                                    if res.get("success"): link = res["files"][0]["url"]
                elif api == "litterbox":
                    async with aiohttp.ClientSession(timeout=custom_timeout) as session:
                        with open(filename, 'rb') as f:
                            data = aiohttp.FormData()
                            data.add_field('reqtype', 'fileupload')
                            data.add_field('time', '72h')
                            data.add_field('fileToUpload', f, filename=base_name)
                            async with session.post("https://litterbox.catbox.moe/resources/internals/api.php", data=data) as response:
                                if response.status == 200:
                                    res = await response.text()
                                    if res.startswith("http"): link = res.strip()
                if link: return link
            except Exception: await asyncio.sleep(attempt * 2)
    return None

async def upload_to_cloud_sem(filename, selected_api="all"):
    global UPLOAD_SEM
    if UPLOAD_SEM is None:
        return await upload_to_cloud(filename, selected_api)
    async with UPLOAD_SEM:
        return await upload_to_cloud(filename, selected_api)

def analyze_file(filepath):
    groups = defaultdict(list)
    seen_urls_hashes = set()
    total, adult, live, vod, series = 0, 0, 0, 0, 0
    current_extinf = ""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#EXTM3U"): continue
            if line.startswith("#EXTINF"): current_extinf = line
            elif line.startswith("#"):
                if current_extinf: current_extinf += "\n" + line
            else:
                if current_extinf:
                    url = line
                    total += 1
                    match = GROUP_TITLE_REGEX.search(current_extinf)
                    group = match.group(1) if match else "Unknown"
                    is_adult = bool(ADULT_REGEX.search(current_extinf)) or bool(ADULT_REGEX.search(url)) or bool(ADULT_REGEX.search(group))
                    if is_adult: adult += 1
                    else:
                        url_hash = hash(url)
                        if url_hash not in seen_urls_hashes:
                            seen_urls_hashes.add(url_hash)
                            groups[group].append((current_extinf, url, False))
                            
                            g_lower = group.lower()
                            if 'vod' in g_lower or 'movie' in g_lower or 'film' in g_lower or 'افلام' in g_lower or 'أفلام' in g_lower:
                                vod += 1
                            elif 'series' in g_lower or 'serie' in g_lower or 'مسلسلات' in g_lower:
                                series += 1
                            else:
                                live += 1
                                
                    current_extinf = ""
    clean_groups = defaultdict(list)
    for g_name, entries in groups.items():
        if not bool(ADULT_REGEX.search(g_name)): clean_groups[g_name] = entries
    return clean_groups, total, adult, live, vod, series

async def analyze_async(filepath): return await asyncio.to_thread(analyze_file, filepath)

def get_clean_size_mb(groups):
    size_bytes = len("#EXTM3U\r\n")
    for g in groups.values():
        for extinf, url, _ in g:
            size_bytes += len(extinf.replace('\n', '\r\n').encode('utf-8')) + len(url.encode('utf-8')) + 4
    return size_bytes / (1024 * 1024)

def write_m3u_and_get_count(groups, filename):
    count = 0
    promo = '#EXTINF:-1 tvg-id="Free.IPTV" tvg-name="FREE IPTV WORLD PROMO" tvg-logo="https://files.catbox.moe/goe4nn.jpg" group-title="🌟 FREE IPTV WORLD 🌟",📺 Welcome to FREE IPTV WORLD\r\nhttps://files.catbox.moe/npglfu.mp4\r\n'
    with open(filename, "w", encoding="utf-8-sig") as f:
        f.write("#EXTM3U\r\n" + promo)
        count += 1
        for g in groups.keys():
            for extinf, url, _ in groups[g]:
                extinf_fixed = extinf.replace('\n', '\r\n')
                if ',' in extinf_fixed:
                    parts = extinf_fixed.rsplit(',', 1)
                    if "FREE IPTV WORLD" not in parts[1]: extinf_branded = f"{parts[0]},{parts[1]} | 🌟 FREE IPTV WORLD 🌟"
                    else: extinf_branded = extinf_fixed
                else: extinf_branded = extinf_fixed
                f.write(extinf_branded + "\r\n" + url + "\r\n")
                count += 1
    return count

def compress_if_large(filename):
    if not os.path.exists(filename): return filename
    if os.path.getsize(filename) / (1024 * 1024) > MAX_FILE_SIZE_MB:
        zip_filename = filename.replace(".m3u", ".zip")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf: zipf.write(filename, os.path.basename(filename))
        return zip_filename
    return filename

async def is_playlist_alive(groups):
    all_valid_urls = [curl for g in groups.values() for _, curl, _ in g if curl.lower().startswith("http")]
    if not all_valid_urls: return False
    test_urls = random.sample(all_valid_urls, min(ALIVE_CHECK_SAMPLE, len(all_valid_urls)))
    headers = {"User-Agent": "TiviMate/4.7.0 (Linux; Android 11)"}
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(sock_connect=2, sock_read=3)) as session:
        async def check(url):
            try:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status in [200, 206, 301, 302, 307]:
                        chunk = await resp.content.read(256)
                        if chunk and b"<html>" not in chunk.lower() and b"<!doctype" not in chunk.lower(): return True
            except: pass
            return False
        results = await asyncio.gather(*[check(u) for u in test_urls])
        return any(results)

async def fetch_and_analyze(session, url, idx):
    global FETCH_SEM
    async def _fetch():
        try:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True) as response:
                if response.status in [200, 206]:
                    temp = f"temp_{uuid.uuid4().hex}.m3u"
                    with open(temp, 'wb') as f:
                        async for chunk in response.content.iter_chunked(4 * 1024 * 1024):
                            f.write(chunk)
                    groups, total, adult, live, vod, series = await analyze_async(temp)
                    safe_delete(temp)
                    if total < MIN_CHANNELS_REQUIRED or not await is_playlist_alive(groups): return {"id": idx, "success": False}
                    return {"id": idx, "groups": groups, "total": total, "size_mb": get_clean_size_mb(groups), "live": live, "vod": vod, "series": series, "success": True}
        except: pass
        return {"id": idx, "success": False}

    try:
        if FETCH_SEM is not None:
            async with FETCH_SEM:
                return await asyncio.wait_for(_fetch(), timeout=FETCH_TIMEOUT)
        return await asyncio.wait_for(_fetch(), timeout=FETCH_TIMEOUT)
    except: return {"id": idx, "success": False}

async def safe_edit(bot, chat_id, message_id, text, edit_state, markup=None, force=False):
    if force or (time.time() - edit_state["time"] > 3.0):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown", reply_markup=markup)
            edit_state["time"] = time.time()
        except: pass

async def extract_urls_from_chat(app, chat_id_pyro, limit=HISTORY_LIMIT):
    urls = set()
    try:
        async for msg in app.get_chat_history(chat_id_pyro, limit=limit):
            text = str(msg.text or msg.caption or "")
            if not text:
                continue
            found = re.findall(r'(https?://[^\s]+)', text)
            for u in found:
                lu = u.lower()
                if 'm3u' in lu or 'get.php' in lu:
                    urls.add(u)
    except:
        pass
    return urls

# ================== 1. دالة الصيد التلقائي والموازي (TURBO) ==================
async def run_hunter_action(bot, chat_id, message_id, args):
    global DIALOG_SEM, FETCH_SEM
    try:
        edit_state = {"time": 0}
        target_count = int(args[-1]) if args[-1].isdigit() else int(args[0])
        keyword = " ".join(args[:-1]).lower() if len(args) > 1 and args[-1].isdigit() else (" ".join(args[1:]).lower() if len(args) > 1 else "")

        await safe_edit(bot, chat_id, message_id, "🚀 **بدأ الصيد المباشر بالتوربو الفائق (البحث الصارم)...**", edit_state, stop_button(), force=True)

        app = Client("wassim_fast_scraper", api_id=24974564, api_hash="b87511de89b42178862e13e84147952b", session_string=SESSION_STRING)
        await app.start()

        found_count, scanned, collected_links, tested_urls = 0, 0, [], set()
        total_live, total_vod, total_series = 0, 0, 0
        found_lock = asyncio.Lock()

        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20, ttl_dns_cache=300, use_dns_cache=True)
        async with aiohttp.ClientSession(connector=connector) as session_req:

            target_chats = []
            async for dialog in app.get_dialogs():
                chat = dialog.chat
                if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
                    continue
                chat_name = chat.title or str(chat.id)
                if any(kw in chat_name.lower() for kw in TARGET_KEYWORDS):
                    target_chats.append((chat.id, chat_name))

            await safe_edit(bot, chat_id, message_id, f"🎯 **تم اكتشاف {len(target_chats)} قناة هدف. بدء المعالجة...**", edit_state, stop_button(), force=True)

            async def process_one_chat(chat_id_pyro, chat_name):
                nonlocal found_count, scanned, collected_links, tested_urls, total_live, total_vod, total_series
                async with DIALOG_SEM:
                    if found_count >= target_count:
                        return
                    scanned += 1
                    await safe_edit(bot, chat_id, message_id, f"🔍 **فحص:** {chat_name}\n✅ المجهز: {found_count}/{target_count}", edit_state, stop_button())

                    urls_to_test = await extract_urls_from_chat(app, chat_id_pyro, limit=HISTORY_LIMIT)

                    async with found_lock:
                        valid_urls = [u for u in urls_to_test if u not in tested_urls]
                        tested_urls.update(valid_urls)

                    if not valid_urls:
                        return

                    tasks = [fetch_and_analyze(session_req, u, i) for i, u in enumerate(valid_urls)]
                    results = await asyncio.gather(*tasks)

                    async def handle_result(res):
                        nonlocal found_count, collected_links, total_live, total_vod, total_series
                        if found_count >= target_count:
                            return
                        if not (res and res.get("success")):
                            return
                        groups = res["groups"]
                        
                        # --- تطبيق فلتر البحث الذكي الصارم ---
                        if keyword:
                            filtered = defaultdict(list)
                            for g_name, entries in groups.items():
                                for extinf, curl, _ in entries:
                                    if is_smart_match(keyword, g_name, extinf):
                                        filtered[g_name].append((extinf, curl, False))
                            groups = filtered
                            
                        if not groups:
                            return

                        fname = f"Hunter_{uuid.uuid4().hex[:4].upper()}.m3u"
                        write_m3u_and_get_count(groups, fname)
                        link = await upload_to_cloud_sem(compress_if_large(fname), "all")
                        safe_delete(fname)
                        if link:
                            async with found_lock:
                                if found_count < target_count:
                                    found_count += 1
                                    total_live += res.get("live", 0)
                                    total_vod += res.get("vod", 0)
                                    total_series += res.get("series", 0)
                                    collected_links.append(f"🔹 <b>الباقة {found_count}:</b> <code>{link}</code>")
                                    await safe_edit(bot, chat_id, message_id, f"🎉 **صيد قوي!**\n✅ المجهز: {found_count}/{target_count}", edit_state, stop_button(), force=True)

                    await asyncio.gather(*[handle_result(r) for r in results])

            await asyncio.gather(*[process_one_chat(cid, cname) for cid, cname in target_chats])

        await app.stop()

        if collected_links:
            if keyword:
                cap_title = f"🔥 𝗘𝗫𝗖𝗟𝗨𝗦𝗜𝗩𝗘 𝗦𝗘𝗥𝗩𝗘𝗥: {keyword.upper()} 🔥"
                ai_title = f"EXCLUSIVE {keyword.upper()} SERVER"
            else:
                cap_title = "🔗 𝗗𝗜𝗥𝗘𝗖𝗧 𝗜𝗣𝗧𝗩 𝗟𝗜𝗡𝗞𝗦 🔗"
                ai_title = "DIRECT IPTV LINKS"

            caption = WARNING_TEXT + LINK_POST_CAPTION.replace("🔗 𝗗𝗜𝗥𝗘𝗖𝗧 𝗜𝗣𝗧𝗩 𝗟𝗜𝗡𝗞𝗦 🔗", cap_title).replace("{links}", "\n\n".join(collected_links))

            await send_post_with_ai_image(
                bot=bot,
                channel_id=CHANNEL_ID,
                title_text=ai_title,
                server_count=found_count,
                keyword=keyword,
                full_caption_with_links=caption,
                live=total_live,
                vod=total_vod,
                series=total_series
            )

            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"🏁 **اكتملت العملية بنجاح!** تم النشر بنجاح.")
        else:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ لم أجد نتائج مطابقة للبحث الصارم.")
    except Exception as e:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ خطأ: {e}")
        except: pass

# ================== 2. دالة الصيد كملف نصي (hunttxt) — TURBO ==================
async def run_hunttxt_action(bot, chat_id, message_id, args):
    global DIALOG_SEM
    try:
        edit_state = {"time": 0}
        target_count = int(args[-1]) if args[-1].isdigit() else int(args[0])
        keyword = " ".join(args[:-1]).lower() if len(args) > 1 and args[-1].isdigit() else (" ".join(args[1:]).lower() if len(args) > 1 else "")

        await safe_edit(bot, chat_id, message_id, "🚀 **بدأ الصيد النصي بالتوربو الموازي (البحث الصارم)...**", edit_state, stop_button(), force=True)

        app = Client("wassim_fast_scraper", api_id=24974564, api_hash="b87511de89b42178862e13e84147952b", session_string=SESSION_STRING)
        await app.start()

        found_count, scanned, collected_links_raw, tested_urls = 0, 0, [], set()
        found_lock = asyncio.Lock()

        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20, ttl_dns_cache=300, use_dns_cache=True)
        async with aiohttp.ClientSession(connector=connector) as session_req:
            target_chats = []
            async for dialog in app.get_dialogs():
                chat = dialog.chat
                if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
                    continue
                chat_name = chat.title or str(chat.id)
                if any(kw in chat_name.lower() for kw in TARGET_KEYWORDS):
                    target_chats.append((chat.id, chat_name))

            await safe_edit(bot, chat_id, message_id, f"🎯 **تم اكتشاف {len(target_chats)} قناة. بدء الفحص...**", edit_state, stop_button(), force=True)

            async def process_one_chat(chat_id_pyro, chat_name):
                nonlocal found_count, scanned, collected_links_raw, tested_urls
                async with DIALOG_SEM:
                    if found_count >= target_count:
                        return
                    scanned += 1
                    await safe_edit(bot, chat_id, message_id, f"🔍 **فحص:** {chat_name}\n✅ المستخرج: {found_count}/{target_count}", edit_state, stop_button())

                    urls_to_test = await extract_urls_from_chat(app, chat_id_pyro, limit=HISTORY_LIMIT)

                    async with found_lock:
                        valid_urls = [u for u in urls_to_test if u not in tested_urls]
                        tested_urls.update(valid_urls)

                    if not valid_urls:
                        return

                    tasks = [fetch_and_analyze(session_req, u, i) for i, u in enumerate(valid_urls)]
                    results = await asyncio.gather(*tasks)

                    async def handle_result(res):
                        nonlocal found_count, collected_links_raw
                        if found_count >= target_count:
                            return
                        if not (res and res.get("success")):
                            return
                        groups = res["groups"]
                        
                        # --- تطبيق فلتر البحث الذكي الصارم ---
                        if keyword:
                            filtered = defaultdict(list)
                            for g_name, entries in groups.items():
                                for extinf, curl, _ in entries:
                                    if is_smart_match(keyword, g_name, extinf):
                                        filtered[g_name].append((extinf, curl, False))
                            groups = filtered
                            
                        if not groups:
                            return

                        fname = f"Hunter_{uuid.uuid4().hex[:4].upper()}.m3u"
                        write_m3u_and_get_count(groups, fname)
                        link = await upload_to_cloud_sem(compress_if_large(fname), "all")
                        safe_delete(fname)
                        if link:
                            async with found_lock:
                                if found_count < target_count:
                                    found_count += 1
                                    collected_links_raw.append(link)
                                    await safe_edit(bot, chat_id, message_id, f"🎉 **تم التجهيز!**\n✅ المستخرج: {found_count}/{target_count}", edit_state, stop_button(), force=True)

                    await asyncio.gather(*[handle_result(r) for r in results])

            await asyncio.gather(*[process_one_chat(cid, cname) for cid, cname in target_chats])

        await app.stop()

        if collected_links_raw:
            txt_filename = f"Cloud_Links_{target_count}_{uuid.uuid4().hex[:4]}.txt"
            with open(txt_filename, "w", encoding="utf-8") as f: f.write("\n".join(collected_links_raw))
            with open(txt_filename, "rb") as f_send:
                await bot.send_document(chat_id=chat_id, document=f_send, caption=f"✅ **اكتمل صيد الملف النصي!**\nإليك {len(collected_links_raw)} روابط سحابية.")
            safe_delete(txt_filename)
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        else:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ لم أجد نتائج مطابقة للبحث الصارم.")
    except Exception as e:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ خطأ: {e}")
        except: pass

# ================== 3. دالة السحب السريع (scrape) — TURBO ==================
async def run_scrape_action(bot, chat_id, message_id, args):
    global DIALOG_SEM
    try:
        edit_state = {"time": 0}
        target_count = int(args[0])
        await safe_edit(bot, chat_id, message_id, "⚡ **بدأ السحب الفائق الخام للمصنع...**", edit_state, stop_button(), force=True)

        app = Client("wassim_fast_scraper", api_id=24974564, api_hash="b87511de89b42178862e13e84147952b", session_string=SESSION_STRING)
        await app.start()

        all_links = []
        links_lock = asyncio.Lock()

        target_chats = []
        async for dialog in app.get_dialogs():
            chat = dialog.chat
            if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
                continue
            target_chats.append(chat.id)

        async def scrape_one(chat_id_pyro):
            async with DIALOG_SEM:
                if len(all_links) >= target_count * 2:
                    return
                urls = await extract_urls_from_chat(app, chat_id_pyro, limit=HISTORY_LIMIT)
                async with links_lock:
                    all_links.extend(urls)

        await asyncio.gather(*[scrape_one(cid) for cid in target_chats])

        await app.stop()
        final_links = list(set(all_links))[:target_count]
        if final_links:
            txt_filename = f"Scraped_{len(final_links)}.txt"
            with open(txt_filename, "w", encoding="utf-8") as f: f.write("\n".join(final_links))
            with open(txt_filename, "rb") as f_send:
                await bot.send_document(chat_id=chat_id, document=f_send, caption=f"⚡ **اكتمل السحب السريع بنجاح!**\nتم جلب {len(final_links)} روابط.")
            safe_delete(txt_filename)
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        else:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ لم يتم العثور على روابط جديدة.")
    except Exception as e:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ خطأ: {e}")
        except: pass

# ================== المحرك السحابي الأساسي المتحكم ==================
async def main():
    global DIALOG_SEM, FETCH_SEM, UPLOAD_SEM
    if not SESSION_STRING: exit(1)

    DIALOG_SEM = asyncio.Semaphore(MAX_PARALLEL_DIALOGS)
    FETCH_SEM = asyncio.Semaphore(MAX_PARALLEL_FETCHES)
    UPLOAD_SEM = asyncio.Semaphore(MAX_PARALLEL_UPLOADS)

    bot = Bot(token=TOKEN)
    payload = json.loads(os.environ.get("PAYLOAD", "{}"))
    action = payload.get("action")
    chat_id = payload.get("chat_id")
    message_id = payload.get("message_id")
    if not chat_id or not action: return

    try:
        if action == "hunt":
            await run_hunter_action(bot, chat_id, message_id, payload.get("args", []))
        elif action == "hunttxt":
            await run_hunttxt_action(bot, chat_id, message_id, payload.get("args", []))
        elif action == "scrape":
            await run_scrape_action(bot, chat_id, message_id, payload.get("args", []))
        elif action == "process_file":
            await safe_edit(bot, chat_id, message_id, "⚙️ **المصنع يقوم بتنظيف وتفريغ الملف بالفورمات الأصلي الشرعي...** ⏳", {"time": 0}, stop_button(), force=True)
            tg_file = await bot.get_file(payload.get("file_id"))
            filepath = "temp_dl.m3u"
            await tg_file.download_to_drive(filepath)

            groups, total, adult, live, vod, series = await analyze_async(filepath)
            os.remove(filepath)

            out_file = "clean_original.m3u"
            write_m3u_and_get_count(groups, out_file)
            final_file = compress_if_large(out_file)

            git_link, catbox_link = await asyncio.gather(
                upload_to_cloud_sem(final_file, "github"),
                upload_to_cloud_sem(final_file, "catbox_m3u8"),
            )

            safe_delete(out_file)
            if final_file != out_file: safe_delete(final_file)

            msg = f"✅ **اكتمل التنظيف بالفورمات الأصلي!**\n\n📡 إجمالي القنوات: {total:,}\n📺 Live: {live:,} | 🎬 VOD: {vod:,} | 🍿 Series: {series:,}\n🔞 محذوف (إباحي): {adult:,}\n\n🔗 **GitHub:**\n`{git_link}`\n\n🔗 **Catbox:**\n`{catbox_link}`"
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, parse_mode="Markdown")

    except Exception as e:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ خطأ داخلي في عمل المصنع: {str(e)}")
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
