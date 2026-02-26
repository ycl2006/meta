import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

# 获取当前脚本所在目录，确保在 GitHub Actions 环境下路径正确
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_DB = os.path.join(BASE_PATH, 'db.json')
OUTPUT_LIST = os.path.join(BASE_PATH, 'MyVideo.list')

def get_deep_domains(api_url):
    """
    通过三次随机请求捕获动态 CDN 域名
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
                            
                            parts = domain.split('.')
                            # 提取前缀词根 (如 v12.qewbn.com -> v)
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
            time.sleep(0.3)
        except Exception as e:
            print(f"      ⚠️ 探测失败: {e}")
            
    return found_domains, found_keywords

def generate():
    if not os.path.exists(JSON_DB):
        print("❌ 错误: 找不到 db.json 文件")
        return

    # --- 1. 读取历史数据 (增量合并的核心) ---
    all_domains = set()
    all_keywords = {
        "m3u8", "yyv", "cdnlz", "yzzy", "wwzy", "10cong", "bfzy", "jszy", "360zy", "360zyx"
    } 
    
    if os.path.exists(OUTPUT_LIST):
        print(f"📂 发现现有规则，正在读取历史记录进行增量合并...")
        with open(OUTPUT_LIST, 'r', encoding='utf-8') as f:
            for line in f:
                # 兼容 Clash Rule Provider 格式提取内容
                kw_match = re.search(r'DOMAIN-KEYWORD,([^,\s]+)', line)
                sf_match = re.search(r'DOMAIN-SUFFIX,([^,\s]+)', line)
                if kw_match: all_keywords.add(kw_match.group(1).strip())
                if sf_match: all_domains.add(sf_match.group(1).strip())
        print(f"📥 已载入历史: {len(all_keywords)} 关键词, {len(all_domains)} 域名")

    # --- 2. 爬取新数据 ---
    with open(JSON_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)

    sites = db.get('sites', [])
    print(f"🚀 开始增量扫描 {len(sites)} 个采集站...")
    
    for site in sites:
        api = site.get('api', '')
        if not api or not api.startswith('http'): continue
            
        print(f"🔎 正在探测: {site.get('name', '未知站')}")
        
        # 将 API 自身的域名也加入直连
        api_host = urlparse(api).netloc.split(':')[0]
        if api_host: all_domains.add(api_host)
        
        domains, keywords = get_deep_domains(api)
        all_domains.update(domains)
        all_keywords.update(keywords)

    # --- 3. 过滤与持久化 ---
    # 过滤掉黑名单和无效词
    exclude = ["com", "net", "org", "www", "cdn", "index", "html", "payload", "github"]
    
    final_keywords = sorted([k for k in all_keywords if k and len(k) > 1 and k not in exclude])
    final_domains = sorted([d for d in all_domains if d and "." in d])

    with open(OUTPUT_LIST, 'w', encoding='utf-8') as f:
        f.write("payload:\n")
        print(f"✍️ 写入关键词 ({len(final_keywords)} 条)")
        for kw in final_keywords:
            f.write(f"  - DOMAIN-KEYWORD,{kw}\n")
        
        print(f"✍️ 写入域名后缀 ({len(final_domains)} 条)")
        for d in final_domains:
            f.write(f"  - DOMAIN-SUFFIX,{d}\n")
            
    print(f"✅ 处理完成！总规模：域名 {len(final_domains)}，词根 {len(final_keywords)}")

if __name__ == "__main__":
    generate()
