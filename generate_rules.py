import json
import re
import os
import requests
from urllib.parse import urlparse

# 🌐 配置你的代理地址 (如果是 Clash 环境，通常是 127.0.0.1:7890)
# 或者你可以使用三个不同的 SOCKS5/HTTP 节点
PROXIES_LIST = [
    None,  # 直连
    {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}, # 代理1
    {"http": "http://127.0.0.1:7891", "https": "http://127.0.0.1:7891"}  # 代理2
]

def get_deep_domains(api_url):
    all_found_domains = set()
    
    # 核心修改：循环使用不同的代理去抓取
    for i, proxy in enumerate(PROXIES_LIST):
        try:
            # print(f"  - 尝试路径 {i+1}...")
            resp = requests.get(f"{api_url}?ac=detail&pg=1", timeout=10, proxies=proxy)
            if resp.status_code == 200:
                data = resp.json()
                vod_list = data.get('list', [])
                for vod in vod_list:
                    play_url = vod.get('vod_play_url', '')
                    urls = re.findall(r'https?://[^\$,\s]+', play_url)
                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]
                        if domain:
                            all_found_domains.add(domain)
        except Exception:
            continue
    return all_found_domains

def generate():
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_path, 'db.json')
    
    if not os.path.exists(json_path): return

    with open(json_path, 'r', encoding='utf-8') as f:
        db = json.load(f)

    final_domains = set()

    print("🚀 开始[多链路]深度扫描 API...")
    for site in db.get('sites', []):
        api = site.get('api', '')
        if not api.startswith('http'): continue
            
        # 1. 记录 API 自身的域名
        api_domain = urlparse(api).netloc.split(':')[0]
        final_domains.add(api_domain)
        
        # 2. 多地抓取视频域名
        print(f"🔎 正在探测(多路径): {site.get('name', '未知站')}")
        video_domains = get_deep_domains(api)
        final_domains.update(video_domains)

    # 3. 写入文件
    with open('MyVideo.list', 'w', encoding='utf-8') as f:
        f.write("# 多链路深度扫描自动生成的精确域名\n")
        # 顺便加上 yyv 补漏规则，应对你遇到的 qwe132456.cc 这种随机马甲
        f.write("DOMAIN-KEYWORD,yyv\n") 
        for d in sorted(list(final_domains)):
            if d:
                f.write(f"DOMAIN-SUFFIX,{d}\n")
            
    print(f"✅ 完成！共捕获 {len(final_domains)} 个唯一域名。")

if __name__ == "__main__":
    generate()
