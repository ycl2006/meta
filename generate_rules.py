import json
import re
import os
import requests
from urllib.parse import urlparse

def get_deep_domains(api_url):
    """请求 API，抓取当前最新的播放域名"""
    try:
        # 增加超时限制，防止某个坏掉的 API 卡死整个 Action
        resp = requests.get(f"{api_url}?ac=detail&pg=1", timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            vod_list = data.get('list', [])
            found_domains = set()
            for vod in vod_list:
                play_url = vod.get('vod_play_url', '')
                # 匹配所有 http/https 链接
                urls = re.findall(r'https?://[^\$,\s]+', play_url)
                for u in urls:
                    domain = urlparse(u).netloc.split(':')[0]
                    if domain:
                        # 只要域名部分
                        found_domains.add(domain)
            return found_domains
    except Exception as e:
        print(f"⚠️ 无法访问 API {api_url}: {e}")
    return set()

def generate():
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_path, 'db.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        db = json.load(f)

    # 用来存放最终精确域名的集合
    final_domains = set()

    print("🚀 开始深入 API 抓取真实播放链接域名...")
    for site in db.get('sites', []):
        api = site.get('api', '')
        if not api.startswith('http'): continue
            
        # 1. 先把 API 自己的域名存下来
        api_domain = urlparse(api).netloc
        if api_domain:
            final_domains.add(api_domain)
        
        # 2. 进去抓具体的播放服务器域名
        print(f"🔎 正在探测: {site.get('name', '未知站')}")
        video_domains = get_deep_domains(api)
        final_domains.update(video_domains)

    # 3. 过滤并输出
    with open('MyVideo.list', 'w', encoding='utf-8') as f:
        f.write("# 深度扫描自动生成的精确域名直连列表\n")
        f.write(f"# 总计捕获域名数量: {len(final_domains)}\n")
        
        # 按照域名排序输出，使用 DOMAIN-SUFFIX 保证子域名也能匹配
        for d in sorted(list(final_domains)):
            if d:
                f.write(f"DOMAIN-SUFFIX,{d}\n")
            
    print(f"✅ 精确识别完成，共捕获 {len(final_domains)} 个播放域名。")

if __name__ == "__main__":
    generate()
