import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_DB = os.path.join(BASE_PATH, 'db.json')
OUTPUT_FILE = os.path.join(BASE_PATH, 'MyVideo.yml')

def load_existing_rules():
    """从现有的 YAML 文件中读取已有的域名和关键词"""
    existing_domains = set()
    existing_keywords = set()
    
    if not os.path.exists(OUTPUT_FILE):
        return existing_domains, existing_keywords

    print(f"📖 正在加载历史规则: {OUTPUT_FILE}")
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("- DOMAIN,"):
                    existing_domains.add(line.replace("- DOMAIN,", "").strip())
                elif line.startswith("- DOMAIN-KEYWORD,"):
                    existing_keywords.add(line.replace("- DOMAIN-KEYWORD,", "").strip())
                elif line.startswith("- DOMAIN-SUFFIX,"):
                    existing_domains.add(line.replace("- DOMAIN-SUFFIX,", "").strip())
    except Exception as e:
        print(f"⚠️ 读取历史文件失败 (跳过): {e}")
        
    return existing_domains, existing_keywords

def extract_urls(text):
    """提取所有URL（含嵌套 / 解码 / m3u8）"""
    urls = set()
    if not text: return urls

    base_urls = re.findall(r'https?://[^\s\$,"]+', text)
    urls.update(base_urls)

    for u in list(base_urls):
        try:
            decoded = requests.utils.unquote(u)
            nested = re.findall(r'https?://[^\s\$,"]+', decoded)
            urls.update(nested)
        except: pass

    m3u8_urls = re.findall(r'https?://[^\s]+\.m3u8', text)
    urls.update(m3u8_urls)
    return urls

def get_deep_domains(api_url, site_name, existing_domains):
    found_domains = set()
    found_keywords = set()
    new_discoveries = []

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept': 'application/json'}
    success = False

    for i in range(3): # 减少重试次数，提高效率
        try:
            timestamp, nonce = int(time.time()), random.randint(100, 999)
            page = random.randint(1, 10) 
            url = f"{api_url}?ac=detail&pg={page}&_t={timestamp}&_n={nonce}"
            resp = requests.get(url, headers=headers, timeout=8)

            if resp.status_code == 200:
                data = resp.json()
                vod_list = data.get('list', [])
                if not vod_list: continue
                
                success = True
                for vod in vod_list:
                    raw_text = " ".join([vod.get('vod_play_url', ''), vod.get('vod_down_url', ''), json.dumps(vod, ensure_ascii=False)])
                    urls = extract_urls(raw_text)

                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]
                        if domain and len(domain) > 3 and '.' in domain:
                            if domain not in existing_domains:
                                new_discoveries.append(domain)
                                existing_domains.add(domain) # 实时加入防止本次扫描重复
                            found_domains.add(domain)

                            parts = domain.split('.')
                            if len(parts) >= 2:
                                main = parts[-2].lower()
                                bad_keywords = {"static", "player", "stream", "video", "cache", "cdn", "api", "img"}
                                if len(main) > 4 and main not in bad_keywords:
                                    found_keywords.add(main)
                break
        except Exception: pass
        time.sleep(1)
    return success, found_domains, found_keywords, new_discoveries

def generate():
    if not os.path.exists(JSON_DB):
        print("❌ 找不到 db.json")
        return

    # 1. 加载历史数据（实现增量的关键）
    all_domains, all_keywords = load_existing_rules()
    
    # 保底关键词
    base_keywords = {"m3u8", "yyv", "cdnlz", "yzzy", "wwzy", "bfzy", "jszy", "360zy"}
    all_keywords.update(base_keywords)

    print(f"🚀 开始增量扫描 (当前已有域名: {len(all_domains)})...")

    try:
        with open(JSON_DB, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except Exception as e:
        print(f"❌ db.json 读取失败: {e}"); return

    sites = db.get('sites', [])
    total_new = 0

    for i, site in enumerate(sites, 1):
        name, api = site.get('name', '未知'), site.get('api', '')
        print(f"[{i}/{len(sites)}] {name} ", end="", flush=True)

        if api.startswith("http"):
            ok, domains, keywords, news = get_deep_domains(api, name, all_domains)
            if ok:
                all_keywords.update(keywords)
                total_new += len(news)
                print(f"✅ +{len(news)}")
            else: print("❌")
        else: print("⏩")

    # 2. 清洗规则
    exclude_list = {"com", "net", "org", "www", "cdn", "index", "html", "github", "vip", "cloud"}
    final_keywords = {k.lower().strip() for k in all_keywords if len(k) > 2 and k not in exclude_list}
    final_domains = {d.lower().strip() for d in all_domains if d and "." in d}

    # 3. 覆盖写入（包含老数据和新抓的数据）
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
            f.write("payload:\n")
            # 写入域名
            for d in sorted(final_domains): f.write(f"  - DOMAIN,{d}\n")
            # 写入关键词
            for kw in sorted(final_keywords): f.write(f"  - DOMAIN-KEYWORD,{kw}\n")
            # 写入后缀
            for d in sorted(final_domains): f.write(f"  - DOMAIN-SUFFIX,{d}\n")
        
        print("\n" + "="*40)
        print(f"🎉 增量更新完成!")
        print(f"新增域名: {total_new}")
        print(f"当前总规则数: {len(final_keywords) + len(final_domains)}")
        print("="*40)
    except Exception as e:
        print(f"❌ 写入失败: {e}")

if __name__ == "__main__":
    generate()
