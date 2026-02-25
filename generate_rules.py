import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

def get_deep_domains(api_url):
    """
    通过三次带有随机参数的请求，模拟多路径嗅探，捕获动态 CDN 域名
    """
    found_domains = set()
    found_keywords = set()
    
    for i in range(3):
        try:
            timestamp = int(time.time())
            nonce = random.randint(100, 999)
            target_url = f"{api_url}?ac=detail&pg=1&_t={timestamp}&_n={nonce}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            resp = requests.get(target_url, headers=headers, timeout=15)
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
                            
                            # 提取前缀词根 (如 v12.qewbn.com -> v)
                            parts = domain.split('.')
                            if len(parts) >= 3:
                                prefix = parts[0]
                                if re.match(r'^[a-z]{1,4}\d+$', prefix):
                                    keyword = re.sub(r'\d+', '', prefix)
                                    if len(keyword) >= 2:
                                        found_keywords.add(keyword)

                            # 提取主域核心 (如 wwzycdn.10cong.com -> 10cong)
                            if len(parts) >= 2:
                                main_name = parts[-2]
                                if len(main_name) > 4: 
                                    found_keywords.add(main_name)
            
            time.sleep(0.5)
        except Exception as e:
            print(f"      ⚠️ 第 {i+1} 次尝试失败: {e}")
            
    return found_domains, found_keywords

def generate():
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_path, 'db.json')
    
    if not os.path.exists(json_path):
        print("❌ 找不到 db.json 文件")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        db = json.load(f)

    all_domains = set()
    # 初始关键词库
    all_keywords = {
        "m3u8", "index.m3u8", "yyv", "cdnlz", "yzzy", 
        "wwzy", "10cong", "bfzy", "jszy", "360zy", "360zyx"
    } 

    print(f"🚀 开始深度扫描 {len(db.get('sites', []))} 个采集站 API...")
    
    for site in db.get('sites', []):
        api = site.get('api', '')
        if not api or not api.startswith('http'): continue
            
        print(f"🔎 正在探测: {site.get('name', '未知站')}")
        
        api_host = urlparse(api).netloc.split(':')[0]
        if api_host: all_domains.add(api_host)
        
        domains, keywords = get_deep_domains(api)
        all_domains.update(domains)
        all_keywords.update(keywords)

    # --- 核心修正：写入逻辑必须在 generate 函数内部，才能访问 all_keywords ---
    with open('MyVideo.list', 'w', encoding='utf-8') as f:
        f.write("payload:\n")
        
        print("✍️ 正在写入关键词规则...")
        for kw in sorted(list(all_keywords)):
            # 过滤无效词
            if kw and kw not in ["com", "net", "org", "www", "cdn"]:
                f.write(f"  - DOMAIN-KEYWORD,{kw}\n")
        
        print("✍️ 正在写入域名后缀规则...")
        for d in sorted(list(all_domains)):
            if d:
                f.write(f"  - DOMAIN-SUFFIX,{d}\n")
            
    print(f"✅ 生成完毕！捕获域名: {len(all_domains)}，提取词根: {len(all_keywords)}")

if __name__ == "__main__":
    generate()
