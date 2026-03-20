import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_DB = os.path.join(BASE_PATH, 'db.json')
# 建议改为 .list 后缀，如果你在 Clash 配置里用的是 .list
OUTPUT_FILE = os.path.join(BASE_PATH, 'MyVideo.list') 

# =============================
# 🌐 URL提取
# =============================
def extract_urls(text):
    urls = set()
    if not text:
        return urls
    base_urls = re.findall(r'https?://[^\$,\s]+', text)
    urls.update(base_urls)
    for u in list(base_urls):
        try:
            decoded = requests.utils.unquote(u)
            nested = re.findall(r'https?://[^\$,\s]+', decoded)
            urls.update(nested)
        except:
            pass
    m3u8_urls = re.findall(r'https?://[^\s]+\.m3u8', text)
    urls.update(m3u8_urls)
    return urls

# =============================
# 🌍 根域名提取
# =============================
def get_root_domain(domain):
    parts = domain.split('.')
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain

# =============================
# 📡 深度采集函数
# =============================
def get_deep_domains(api_url, site_name, domain_counter):
    found_domains = set()
    found_keywords = set()
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    success = False

    for i in range(6):
        try:
            page = random.randint(1, 10)
            url = f"{api_url}?ac=detail&pg={page}"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                vod_list = data.get('list', [])
                if not vod_list: continue
                success = True
                for vod in vod_list:
                    text = " ".join([
                        vod.get('vod_play_url', ''),
                        vod.get('vod_down_url', ''),
                        vod.get('vod_play_from', ''),
                        str(vod)
                    ])
                    urls = extract_urls(text)
                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]
                        if not domain or "." not in domain: continue
                        root = get_root_domain(domain)
                        domain_counter[domain] = domain_counter.get(domain, 0) + 1
                        domain_counter[root] = domain_counter.get(root, 0) + 1
                        found_domains.add(domain)
                        found_domains.add(root)
                        main = root.split('.')[0]
                        bad = {"static","player","stream","media","video","cache","play","download","file","cdn","api","data"}
                        if len(main) > 3 and main not in bad:
                            found_keywords.add(main)
                break
        except:
            pass
        time.sleep(random.uniform(0.5, 2))
    return success, found_domains, found_keywords

# =============================
# 🚀 主流程
# =============================
def generate():
    if not os.path.exists(JSON_DB):
        print("❌ 缺少 db.json")
        return

    all_domains = set()
    all_keywords = {"m3u8","cdnlz","yzzy","bfzy","jszy","360zy","ffzy","lzzy"}
    domain_counter = {}

    # 🔄 读取旧规则（实现增量权重继承）
    old_file_path = OUTPUT_FILE if os.path.exists(OUTPUT_FILE) else OUTPUT_FILE.replace('.list', '.yml')
    
    if os.path.exists(old_file_path):
        print(f"📥 正在从旧规则中继承权重: {os.path.basename(old_file_path)}")
        try:
            with open(old_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                old_domains = set(re.findall(r'DOMAIN(?:-SUFFIX)?,\s*([^,\s\n\x27]+)', content))
                old_keywords = set(re.findall(r'DOMAIN-KEYWORD,\s*([^,\s\n\x27]+)', content))
                bad_kw = {"static","player","stream","media","video","cache","play","download","file","cdn","api","data"}
                for d in old_domains:
                    d = d.lower().strip()
                    if "." in d:
                        all_domains.add(d)
                        domain_counter[d] = domain_counter.get(d, 0) + 2
                        root = get_root_domain(d)
                        all_domains.add(root)
                        domain_counter[root] = domain_counter.get(root, 0) + 2
                for k in old_keywords:
                    k = k.lower().strip()
                    if len(k) > 3 and k not in bad_kw:
                        all_keywords.add(k)
        except Exception as e:
            print(f"⚠️ 读取旧文件失败: {e}")

    # 📡 采集新站点
    with open(JSON_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)
    sites = db.get('sites', [])
    print(f"🚀 开始扫描 {len(sites)} 个站点...")

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知')
        api = site.get('api', '')
        print(f"[{i}/{len(sites)}] {name} ", end="", flush=True)
        if api.startswith("http"):
            ok, domains, kws = get_deep_domains(api, name, domain_counter)
            if ok:
                all_domains.update(domains)
                all_keywords.update(kws)
                print("✅")
            else:
                print("❌")
        else:
            print("⏩")

    # 🧹 稳定过滤
    final_domains = set()
    for d in all_domains:
        d = d.lower().strip()
        if "." not in d: continue
        if d.count('.') == 1 or domain_counter.get(d, 0) >= 2:
            final_domains.add(d)
    final_keywords = {k.lower().strip() for k in all_keywords if len(k) > 3}

    # 📝 输出 LIST 格式（顶格、无 payload、无横杠）
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for d in sorted(final_domains):
            if d.count('.') >= 2:
                f.write(f"DOMAIN,{d}\n")
        for d in sorted(final_domains):
            if d.count('.') == 1:
                f.write(f"DOMAIN-SUFFIX,{d}\n")
        for k in sorted(final_keywords):
            f.write(f"DOMAIN-KEYWORD,{k}\n")

    print(f"\n🎉 任务完成！文件: {os.path.basename(OUTPUT_FILE)}")

if __name__ == "__main__":
    generate()
