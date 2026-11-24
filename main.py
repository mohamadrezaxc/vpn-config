import base64
import json
import os
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# تنظیمات گیت‌هاب
# توکن از تنظیمات Vercel (Environment Variables) خوانده می‌شود
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
REPO_OWNER = "mohamadrezaxc"
REPO_NAME = "vpn-config"
FILE_PATH = "servers.json"

# برای Vercel باید مسیر قالب‌ها دقیق مشخص شود
templates = Jinja2Templates(directory="templates")

def get_file_from_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        return json.loads(content), data['sha']
    return None, None

def update_file_in_github(content_dict, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    json_str = json.dumps(content_dict, ensure_ascii=False, indent=2)
    content_b64 = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": "Update servers.json via Vercel Panel",
        "content": content_b64,
        "sha": sha,
        "branch": "main"
    }
    response = requests.put(url, headers=headers, json=data)
    return response.status_code in [200, 201]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    data, sha = get_file_from_github()
    if data is None:
        return HTMLResponse("<h2>خطا: فایل servers.json پیدا نشد یا توکن اشتباه است.</h2>")
    return templates.TemplateResponse("index.html", {"request": request, "data": data})

@app.post("/add_server")
async def add_server(name: str = Form(...), host: str = Form(...), port: int = Form(...), username: str = Form(...), password: str = Form(...)):
    data, sha = get_file_from_github()
    if data:
        new_server = {
            "id": f"srv_{len(data['servers']) + 1:02d}",
            "name": name,
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "certificate_settings": { "verify_server_cert": False, "cert_cn": "opengw.net", "save_cert_request": False },
            "auth_settings": { "ms_chap_v2": True, "chap": True, "pap": True, "eap_ms_chap_v2": False, "eap_tls": False },
            "network_settings": { "mtu": 1500, "limit_mss": 1300, "tls_sni": "cbi.ir", "allow_local_port": False, "use_proxy": "none" },
            "advanced_settings": { "save_credentials": True, "retry_before_prompt": False, "use_fingerprint": False, "retry_seconds": 0, "connection_timeout": 0 }
        }
        data['servers'].append(new_server)
        if update_file_in_github(data, sha):
            return RedirectResponse(url="/", status_code=303)
    return HTMLResponse("خطا در ذخیره سرور")

@app.post("/delete_server")
async def delete_server(server_id: str = Form(...)):
    data, sha = get_file_from_github()
    if data:
        data['servers'] = [s for s in data['servers'] if s['id'] != server_id]
        if update_file_in_github(data, sha):
            return RedirectResponse(url="/", status_code=303)
    return HTMLResponse("خطا در حذف سرور")
