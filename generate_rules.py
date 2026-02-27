import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

# 路径配置
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_DB = os.path.join(BASE_PATH, 'db.json')
OUTPUT_LIST = os.path.join(BASE_PATH, 'MyVideo.list')

def get_deep_domains(api_url):
    found_domains = set()
    found_keywords = set()
    for i in range(3):
        try:
            timestamp = int(time.time())
            nonce = random.randint(100, 999)
            target_url = f"{api_url}?ac=detail&pg=1&_t={timestamp}&_n={nonce}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            resp = requests.get(target_url, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                vod_list = data.get('list', [])
                for vod in vod_list:
                    play_url = vod.get('vod_play_url', '')
                    urls = re.findall(r'https?://[^\$,\s]+', play_url)
                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]
                        if domain and len(domain) > 3:
                            found_domains.add(domain)
                            parts = domain.split('.')
                            if len(parts) >= 3:
                                prefix = parts[0]
                                if re.match(r'^[a-z]{1,4}\d+$', prefix):
                                    keyword = re.sub(r'\d+', '', prefix)
                                    if len(keyword) >= 2: found_keywords.add(keyword)
                            if len(parts) >= 2:
                                main_name = parts[-2]
                                if len(main_name) > 4: found_keywords.add(main_name)
            time.sleep(0.2)
        except:
            continue
    return found_domains, found_keywords

def generate():
    if not os.path.exists(JSON_DB):
        print("❌ 错误: 找不到 db.json")
        return

    # --- 1. 读取历史数据并记录初始数量 ---
    all_domains, all_keywords = set(), {"m3u8", "yyv", "cdnlz", "yzzy", "wwzy", "10cong", "bfzy", "jszy", "360zy"}
    if os.path.exists(OUTPUT_LIST):
        with open(OUTPUT_LIST, 'r', encoding='utf-8') as f:
            content = f.read()
            all_keywords.update(re.findall(r'DOMAIN-KEYWORD,([^,\s]+)', content))
            all_domains.update(re.findall(r'DOMAIN-SUFFIX,([^,\s]+)', content))
    
    # 记录初始数量用于对比
    initial_kw_count = len(all_keywords)
    initial_dm_count = len(all_domains)
    print(f"📥 历史载入: 关键词 {initial_kw_count} / 域名 {initial_dm_count}")

    # --- 2. 爬取新数据 ---
    with open(JSON_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    sites = db.get('sites', [])
    total = len(sites)
    print(f"🚀 开始扫描 {total} 个采集站...")
    print("::group::🔍 点击展开详细探测日志")

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知站')
        api = site.get('api', '')
        print(f"[{i}/{total}] {(i/total)*100:>3.0f}% 正在探测: {name}")
        
        if api and api.startswith('http'):
            api_host = urlparse(api).netloc.split(':')[0]
            if api_host: all_domains.add(api_host)
            domains, keywords = get_deep_domains(api)
            all_domains.update(domains)
            all_keywords.update(keywords)
    
    print("::endgroup::")

    # --- 3. 终极去重逻辑 ---
    exclude = ["com", "net", "org", "www", "cdn", "index", "html", "payload", "github", "vip"]
    processed_keywords = set()
    for k in all_keywords:
        if not k or len(k) <= 1 or k in exclude: continue
        base = re.sub(r'\d+$', '', k)
        processed_keywords.add(base if len(base) > 2 else k)

    final_keywords = sorted(list(processed_keywords))
    final_domains = []
    sorted_raw_domains = sorted(list(all_domains), key=len)
    for d in sorted_raw_domains:
        if not d or "." not in d: continue
        if not any(kw in d for kw in final_keywords):
            if not any(d.endswith("." + x) for x in final_domains):
                final_domains.append(d)

    # --- 4. 写入文件 ---
    with open(OUTPUT_LIST, 'w', encoding='utf-8') as f:
        f.write("payload:\n")
        for kw in final_keywords: f.write(f"  - DOMAIN-KEYWORD,{kw}\n")
        for d in sorted(final_domains): f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    # --- 5. 计算并显示增量统计 ---
    added_kw = len(final_keywords) - initial_kw_count
    added_dm = len(final_domains) - initial_dm_count
    
    print("\n" + "="*30)
    print(f"📊 最终增量统计报告:")
    print(f"✨ 新增关键词: {max(0, added_kw)} 条")
    print(f"✨ 新增域名后缀: {max(0, added_dm)} 条")
    print(f"总库规模: 关键词 {len(final_keywords)} / 域名 {len(final_domains)}")
    print("="*30)

if __name__ == "__main__":
    generate()
