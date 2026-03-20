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
    """提取根域名，例如 v1.api.m3u8.com -> m3u8.com"""
    if not domain or "." not in domain: return domain
    parts = domain.split('.')
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain

def extract_urls(text):
    """从文本中嗅探 URL"""
    if not text: return set()
    return set(re.findall(r'https?://[^\$,\s\x22\x27]+', text))

def fetch_domains(api_url, domain_counter):
    """从影视站 API 采集域名"""
    found_domains, found_keywords = set(), set()
    for _ in range(3):
        try:
            page = random.randint(1, 20)
            resp = requests.get(f"{api_url}?ac=detail&pg={page}", headers=HEADERS, timeout=12)
            if resp.status_code != 200: continue
            vod_list = resp.json().get('list', [])
            for vod in vod_list:
                urls = extract_urls(f"{vod.get('vod_play_url','')}|{vod.get('vod_play_from','')}")
                for u in urls:
                    domain = urlparse(u).netloc.split(':')[0].lower()
                    if not domain or "." not in domain: continue
                    root = get_root_domain(domain)
                    # 采集到的新域名加 1 分
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
    print("--- [PROD] 规则更新任务启动 ---")
    if not os.path.exists(JSON_DB):
        print("❌ 错误: db.json 不存在"); return

    all_domains, domain_counter = set(), {}
    all_keywords = {"m3u8", "cdnlz", "yzzy", "bfzy", "jszy", "360zy", "ffzy", "lzzy"}
    
    count_old, count_new = 0, 0

    # 1. 【核心：历史保护】读取旧规则并赋予极高权重
    if os.path.exists(OUTPUT_FILE):
        print("📥 正在加载存量规则并锁定权重...")
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                # 兼容 DOMAIN 和 DOMAIN-SUFFIX
                existing = re.findall(r'DOMAIN(?:-SUFFIX)?,\s*([^,\s\n]+)', content)
                for d in existing:
                    d = d.lower().strip()
                    if d not in all_domains:
                        all_domains.add(d)
                        count_old += 1
                    # 给旧文件里已有的域名初始权重设为 10，确保它们绝对不会被过滤
                    domain_counter[d] = 10 
        except Exception as e:
            print(f"⚠️ 读取旧文件失败: {e}")

    # 2. 采集新数
    with open(JSON_DB, 'r', encoding='utf-8') as f:
        sites = json.load(f).get('sites', [])

    print(f"📡 扫描 {len(sites)} 个影视接口...")
    for i, site in enumerate(sites, 1):
        api = site.get('api', '')
        print(f"[{i:02d}] 正在处理: {site.get('name',''):<10}", end="")
        if api.startswith("http"):
            ok, ds, ks = fetch_domains(api, domain_counter)
            if ok:
                new_finds = ds - all_domains
                count_new += len(new_finds)
                all_domains.update(ds)
                all_keywords.update(ks)
                print(f" ✅ +{len(new_finds)}")
            else: print(" ❌ Error")
        else: print(" ⏩ Skip")

    # 3. 【核心：智能过滤】
    final_domains = set()
    for d in all_domains:
        # 保留逻辑：
        # - 条件 A: 是根域名 (如 aaa.com)
        # - 条件 B: 是历史存量 (权重 >= 10)
        # - 条件 C: 是新采集且频率足够高 (权重 >= 2)
        if d.count('.') == 1 or domain_counter.get(d, 0) >= 10 or domain_counter.get(d, 0) >= 2:
            final_domains.add(d)

    blacklist = {"static", "api", "player", "image", "ts", "index", "script", "css", "js"}
    final_keywords = {k for k in all_keywords if k not in blacklist and len(k) > 3}

    # 4. 写入 YAML (payload 格式)
    print(f"📝 写入更新至 {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("payload:\n")
            # 排序确保 Git Diff 最小化
            sorted_ds = sorted(list(final_domains))
            # 先写子域名精确匹配
            for d in sorted_ds:
                if d.count('.') >= 2: f.write(f"  - DOMAIN,{d}\n")
            # 再写根域名后缀匹配
            for d in sorted_ds:
                if d.count('.') == 1: f.write(f"  - DOMAIN-SUFFIX,{d}\n")
            # 最后写关键字
            for k in sorted(final_keywords):
                f.write(f"  - DOMAIN-KEYWORD,{k}\n")
    except Exception as e:
        print(f"❌ 写入失败: {e}")

    print(f"\n[STATS] 继承:{count_old} | 新获:{count_new} | 最终总数:{len(final_domains)}")
    print("--- 任务圆满完成 ---")

if __name__ == "__main__":
    generate()
