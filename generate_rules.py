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
    
    # 模拟 3 次请求，诱导 API 返回不同的负载均衡节点
    for i in range(3):
        try:
            # 构造随机参数，绕过 API 缓存
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
                    # 提取 http/https 链接
                    urls = re.findall(r'https?://[^\$,\s]+', play_url)
                    for u in urls:
                        # 提取域名并去除端口
                        domain = urlparse(u).netloc.split(':')[0]
                        if domain and len(domain) > 3:
                            found_domains.add(domain)
                            
                            # --- 🧠 智能词根提取逻辑 ---
                            # 针对 yyv14.qwe132456.cc 这种模式
                            parts = domain.split('.')
                            if len(parts) >= 3:
                                prefix = parts[0] # 获取 yyv14
                                # 如果前缀符合 [字母]+[数字] 模式（如 yyv14, v10, cdn2）
                                if re.match(r'^[a-z]{1,4}\d+$', prefix):
                                    # 提取纯字母词根 (yyv)
                                    keyword = re.sub(r'\d+', '', prefix)
                                    if len(keyword) >= 2:
                                        found_keywords.add(keyword)
            
            # 每次请求间歇 1 秒，增加成功率
            time.sleep(1)
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
    all_keywords = {"m3u8", "index.m3u8", "yyv", "cdnlz", "yzzy"} # 预设一些死硬关键词

    print(f"🚀 开始深度扫描 {len(db.get('sites', []))} 个采集站 API...")
    
    for site in db.get('sites', []):
        api = site.get('api', '')
        if not api or not api.startswith('http'): continue
            
        print(f"🔎 正在探测: {site.get('name', '未知站')}")
        
        # 记录 API 自身的域名
        api_host = urlparse(api).netloc.split(':')[0]
        if api_host: all_domains.add(api_host)
        
        # 获取深度嗅探结果
        domains, keywords = get_deep_domains(api)
        all_domains.update(domains)
        all_keywords.update(keywords)

    # 写入文件
    with open('MyVideo.list', 'w', encoding='utf-8') as f:
        f.write("# ----------------------------------------------------------\n")
        f.write(f"# 2026 自动生成精确直连规则 (多路径扫描版)\n")
        f.write(f"# 更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("# ----------------------------------------------------------\n\n")
        
        # 先写关键词规则（优先级最高，应对随机域名）
        f.write("# [关键词补漏]\n")
        for kw in sorted(list(all_keywords)):
            if kw: f.write(f"DOMAIN-KEYWORD,{kw}\n")
        
        f.write("\n# [精确域名匹配]\n")
        # 再写后缀规则
        for d in sorted(list(all_domains)):
            if d: f.write(f"DOMAIN-SUFFIX,{d}\n")
            
    print(f"✅ 生成完毕！捕获域名: {len(all_domains)}，提取词根: {len(all_keywords)}")

if __name__ == "__main__":
    generate()
