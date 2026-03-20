import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

# =============================
# 📁 路径配置
# =============================
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_DB = os.path.join(BASE_PATH, 'db.json')
OUTPUT_FILE = os.path.join(BASE_PATH, 'MyVideo.yml') 

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

# =============================
# 🔍 工具函数
# =============================

def get_root_domain(domain):
    if not domain or "." not in domain:
        return domain
    parts = domain.split('.')
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain

def extract_urls(text):
    if not text: return set()
    return set(re.findall(r'https?://[^\$,\s\x22\x27]+', text))

# =============================
# 📡 深度采集模块
# =============================

def fetch_domains_from_api(api_url, domain_counter):
    found_domains = set()
    found_keywords = set()
    
    for _ in range(3): 
        try:
            page = random.randint(1, 15)
            target_url = f"{api_url}?ac=detail&pg={page}"
            resp = requests.get(target_url, headers=HEADERS, timeout=10)
            
            if resp.status_code != 200: continue
            
            data = resp.json()
            vod_list = data.get('list', [])
            if not vod_list: continue

            for vod in vod_list:
                raw_text = f"{vod.get('vod_play_url','')}|{vod.get('vod_play_from','')}"
                urls = extract_urls(raw_text)
                
                for u in urls:
                    domain = urlparse(u).netloc.split(':')[0].lower()
                    if not domain or "." not in domain: continue
                    
                    root = get_root_domain(domain)
                    domain_counter[domain] = domain_counter.get(domain, 0) + 1
                    domain_counter[root] = domain_counter.get(root, 0) + 1
                    
                    found_domains.add(domain)
                    found_domains.add(root)
                    
                    kw = root.split('.')[0]
                    if len(kw) > 3: found_keywords.add(kw)
            
            return True, found_domains, found_keywords
        except:
            continue
    return False, set(), set()

# =============================
# 🚀 主生成流程
# =============================

def generate():
    print("--- 🚀 开始生成 MyVideo.yml 规则 ---")
    
    if not os.path.exists(JSON_DB):
        print(f"❌ 错误: 找不到 {JSON_DB}")
        return

    all_domains = set()
    all_keywords = {"m3u8", "cdnlz", "yzzy", "bfzy", "jszy", "360zy", "ffzy", "lzzy"}
    domain_counter = {}
    
    # 【新增】计数器
    count_old = 0
    count_new = 0

    # 1. 增量继承
    if os.path.exists(OUTPUT_FILE):
        print("📥 正在读取旧规则以继承权重...")
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                existing = re.findall(r'DOMAIN(?:-SUFFIX)?,\s*([^,\s\n]+)', content)
                for d in existing:
                    d = d.lower().strip()
                    if d not in all_domains:
                        all_domains.add(d)
                        count_old += 1
                    domain_counter[d] = domain_counter.get(d, 0) + 3 
        except Exception as e:
            print(f"⚠️ 读取旧文件跳过: {e}")

    # 2. 读取数据库并爬取
    with open(JSON_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    sites = db.get('sites', [])
    print(f"📡 准备扫描 {len(sites)} 个接口...")

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知')
        api = site.get('api', '')
        print(f"[{i:02d}] 正在处理: {name.ljust(10)} ", end="", flush=True)
        
        if api.startswith("http"):
            ok, ds, ks = fetch_domains_from_api(api, domain_counter)
            if ok:
                # 计算本次新抓到了多少个从未见过的域名
                new_finds = ds - all_domains
                count_new += len(new_finds)
                
                all_domains.update(ds)
                all_keywords.update(ks)
                print(f"✅ (新增 {len(new_finds)})")
            else:
                print("❌")
        else:
            print("⏩")

    # 3. 智能清洗
    final_domains = set()
    for d in all_domains:
        if d.count('.') == 1 or domain_counter.get(d, 0) >= 2:
            final_domains.add(d)

    blacklist = {"static", "api", "player", "image", "script", "style", "ts", "index"}
    final_keywords = {k for k in all_keywords if k not in blacklist and len(k) > 3}

    # 4. 严格按照 YAML 格式写入
    print(f"📝 正在整理并写入 YAML 文件...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("payload:\n")
            for d in sorted(list(final_domains)):
                if d.count('.') >= 2:
                    f.write(f"  - DOMAIN,{d}\n")
            for d in sorted(list(final_domains)):
                if d.count('.') == 1:
                    f.write(f"  - DOMAIN-SUFFIX,{d}\n")
            for k in sorted(list(final_keywords)):
                f.write(f"  - DOMAIN-KEYWORD,{k}\n")
        
        # 【输出统计报告】
        print("\n" + "="*30)
        print(f"📊 规则更新报告:")
        print(f"🔹 历史继承: {count_old} 条")
        print(f"🔸 本次新获: {count_new} 条")
        print(f"✅ 最终总数: {len(final_domains)} 条 (已去重/清洗)")
        print("="*30)
        print(f"🎉 文件已保存: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ 写入失败: {e}")

if __name__ == "__main__":
    generate()
