import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

# =============================
# 📁 生产环境配置
# =============================
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_DB = os.path.join(BASE_PATH, 'db.json')
OUTPUT_FILE = os.path.join(BASE_PATH, 'MyVideo.yml')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def get_root_domain(domain):
    if not domain or "." not in domain: return domain
    parts = domain.split('.')
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain

def extract_urls(text):
    if not text: return set()
    return set(re.findall(r'https?://[^\$,\s\x22\x27]+', text))

def fetch_domains(api_url, domain_counter):
    found_domains, found_keywords = set(), set()
    for _ in range(3):
        try:
            page = random.randint(1, 15)
            resp = requests.get(f"{api_url}?ac=detail&pg={page}", headers=HEADERS, timeout=12)
            if resp.status_code != 200: continue
            vod_list = resp.json().get('list', [])
            for vod in vod_list:
                urls = extract_urls(f"{vod.get('vod_play_url','')}|{vod.get('vod_play_from','')}")
                for u in urls:
                    domain = urlparse(u).netloc.split(':')[0].lower()
                    if not domain or "." not in domain: continue
                    root = get_root_domain(domain)
                    domain_counter[domain] = domain_counter.get(domain, 0) + 1
                    domain_counter[root] = domain_counter.get(root, 0) + 1
                    found_domains.update([domain, root])
                    kw = root.split('.')[0]
                    if len(kw) > 3: found_keywords.add(kw)
            return True, found_domains, found_keywords
        except: continue
    return False, set(), set()

# =============================
# 🚀 主程序
# =============================
def generate():
    print("--- [PROD] 规则生成任务启动 ---")
    if not os.path.exists(JSON_DB):
        print("❌ 错误: db.json 不存在"); return

    all_domains, domain_counter = set(), {}
    all_keywords = {"m3u8", "cdnlz", "yzzy", "bfzy", "jszy", "360zy", "ffzy", "lzzy"}
    
    # 统计项
    count_old, count_new = 0, 0

    # 1. 继承历史 (保持稳定性)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing = re.findall(r'DOMAIN(?:-SUFFIX)?,\s*([^,\s\n]+)', f.read())
            for d in existing:
                d = d.lower().strip()
                if d not in all_domains:
                    all_domains.add(d); count_old += 1
                domain_counter[d] = domain_counter.get(d, 0) + 5

    # 2. 采集新数
    with open(JSON_DB, 'r', encoding='utf-8') as f:
        sites = json.load(f).get('sites', [])

    for i, site in enumerate(sites, 1):
        api = site.get('api', '')
        print(f"[{i:02d}] 正在扫描: {site.get('name',''):<10}", end="")
        if api.startswith("http"):
            ok, ds, ks = fetch_domains(api, domain_counter)
            if ok:
                new_finds = ds - all_domains
                count_new += len(new_finds)
                all_domains.update(ds); all_keywords.update(ks)
                print(f" ✅ +{len(new_finds)}")
            else: print(" ❌ Error")
        else: print(" ⏩ Skip")

    # 3. 清洗过滤 (频率过滤)
    final_domains = {d for d in all_domains if d.count('.') == 1 or domain_counter.get(d, 0) >= 2}
    blacklist = {"static", "api", "player", "image", "ts", "index", "script"}
    final_keywords = {k for k in all_keywords if k not in blacklist and len(k) > 3}

    # 4. 写入 YAML (带 payload 格式)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("payload:\n")
        # 排序确保 Git Diff 最小化
        for d in sorted(final_domains):
            if d.count('.') >= 2: f.write(f"  - DOMAIN,{d}\n")
        for d in sorted(final_domains):
            if d.count('.') == 1: f.write(f"  - DOMAIN-SUFFIX,{d}\n")
        for k in sorted(final_keywords):
            f.write(f"  - DOMAIN-KEYWORD,{k}\n")

    # 💡 核心：打印给 GitHub Actions 捕获的统计信息
    print(f"\n[STATS_REPORT]")
    print(f"OLD_COUNT={count_old}")
    print(f"NEW_COUNT={count_new}")
    print(f"TOTAL_COUNT={len(final_domains)}")
    print(f"--- 任务完成 ---")

if __name__ == "__main__":
    generate()
