import json
import re
import os
import requests

def get_deep_domains(api_url):
    try:
        resp = requests.get(f"{api_url}?ac=detail&pg=1", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            vod_list = data.get('list', [])
            if vod_list:
                play_url = vod_list[0].get('vod_play_url', '')
                urls = re.findall(r'https?://[^\$,\s]+', play_url)
                domains = []
                for u in urls:
                    d_match = re.search(r'https?://([^/:]+)', u)
                    if d_match:
                        domains.append(d_match.group(1))
                return domains
    except:
        pass
    return []

def generate():
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_path, 'db.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        db = json.load(f)

    all_keywords = set()
    # 缩小黑名单，只放最容易造成大规模误杀的纯后缀/通用词
    blacklist = {'com', 'net', 'org', 'cn', 'tv', 'me', 'api', 'www', 'provide', 'vod', 'php', 'm3u8', 'index', 'static', 'html'}

    print("🚀 开始深度扫描 API 内隐藏的变体域名...")
    for site in db.get('sites', []):
        api = site.get('api', '')
        if not api.startswith('http'): continue
            
        try:
            api_domain = re.search(r'https?://([^/:]+)', api).group(1)
        except:
            continue
        
        video_domains = get_deep_domains(api)
        
        for domain in [api_domain] + video_domains:
            parts = domain.split('.')
            for part in parts:
                part = part.lower()
                
                # --- 优化点：不再盲目切除 cdn ---
                # 我们只切除数字、api、cj、zy 这种纯功能词
                clean_part = re.split(r'\d+|api|cj|zy|vip|msc|jx|play', part)[0]
                
                # --- 智能判定逻辑 ---
                # 1. 如果它是纯粹的 "cdn" 或 "app"，丢弃（防止误杀全局）
                if clean_part in {'cdn', 'app', 'v'}:
                    # 但是！如果原词长得像 "wlcdn" 或 "cdnlz"，我们要保留原词
                    if len(part) >= 4 and part not in blacklist:
                        all_keywords.add(part)
                    continue
                
                # 2. 正常提取词根
                if len(clean_part) >= 3 and clean_part not in blacklist:
                    all_keywords.add(clean_part)
                elif len(part) >= 3 and part not in blacklist:
                    if not re.match(r'^v\d+$', part):
                        all_keywords.add(part)

    with open('MyVideo.list', 'w', encoding='utf-8') as f:
        f.write("# 深度扫描自动生成的规则 (智能识别影视CDN)\n")
        for k in sorted(list(all_keywords)):
            f.write(f"DOMAIN-KEYWORD,{k}\n")
            
    print(f"✅ 识别完成，共提取 {len(all_keywords)} 个有效核心特征。")

if __name__ == "__main__":
    generate()
