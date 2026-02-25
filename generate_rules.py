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
                            
                            # --- 🧠 逻辑 1：提取前缀词根 (如 v12.qewbn.com -> v) ---
                            parts = domain.split('.')
                            if len(parts) >= 3:
                                prefix = parts[0]
                                if re.match(r'^[a-z]{1,4}\d+$', prefix):
                                    keyword = re.sub(r'\d+', '', prefix)
                                    if len(keyword) >= 2:
                                        found_keywords.add(keyword)

                            # --- 🧠 逻辑 2：提取主域核心 (如 wwzycdn.10cong.com -> 10cong) ---
                            # 增加这个逻辑来对付境外采集站
                            if len(parts) >= 2:
                                main_name = parts[-2] # 拿到倒数第二个元素
                                # 如果主域名是这种乱码或特定代号，抓下来
                                if len(main_name) > 4: 
                                    found_keywords.add(main_name)
            
            time.sleep(0.5) # 稍微缩短间歇，提速
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
    
    # --- 🟢 重点：手动扩充预设词库，拦截已知境外采集站 ---
    all_keywords = {
        "m3u8", "index.m3u8", "yyv", "cdnlz", "yzzy", 
        "wwzy", "10cong", "bfzy", "jszy", "hhzy", "ffzy"
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

    with open('MyVideo.list', 'w', encoding='utf-8') as f:
        f.write("# ----------------------------------------------------------\n")
        f.write(f"# 2026 自动生成精确直连规则 (境外采集站增强版)\n")
        f.write(f"# 更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("# ----------------------------------------------------------\n\n")
        
        f.write("# [关键词补漏 - 应对境外乱码域名]\n")
        for kw in sorted(list(all_keywords)):
            # 过滤掉太短或太通用的词，防止误杀
            if kw and kw not in ["com", "net", "org", "www"]:
                f.write(f"DOMAIN-KEYWORD,{kw}\n")
        
        f.write("\n# [精确域名匹配]\n")
        for d in sorted(list(all_domains)):
            if d: f.write(f"DOMAIN-SUFFIX,{d}\n")
            
    print(f"✅ 生成完毕！捕获域名: {len(all_domains)}，提取词根: {len(all_keywords)}")

if __name__ == "__main__":
    generate()
# --- 核心修正：写入符合 Clash Classic (YAML) 格式的文件 ---
    with open('MyVideo.list', 'w', encoding='utf-8') as f:
        # 1. 必须有 payload 头部
        f.write("payload:\n")
        
        # 2. 写入关键词规则（必须有 2 个空格缩进和杠符号）
        print("✍️ 正在写入关键词规则...")
        for kw in sorted(list(all_keywords)):
            if kw and kw not in ["com", "net", "org", "www", "cdn"]:
                f.write(f"  - DOMAIN-KEYWORD,{kw}\n")
        
        # 3. 写入后缀规则（必须有 2 个空格缩进和杠符号）
        print("✍️ 正在写入域名后缀规则...")
        for d in sorted(list(all_domains)):
            if d:
                f.write(f"  - DOMAIN-SUFFIX,{d}\n")
            
    print(f"✅ 转换完毕！文件已适配 clash-classic 格式。")
