import json
import re
import os
import requests

def get_deep_domains(api_url):
    """进入 API 内部，抓取最近更新的一个视频，提取播放域名"""
    try:
        # 尝试请求采集站最近更新的数据（取 1 条即可）
        resp = requests.get(f"{api_url}?ac=detail&pg=1", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # 寻找播放地址字段 (通常在 vod_play_url)
            vod_list = data.get('list', [])
            if vod_list:
                play_url = vod_list[0].get('vod_play_url', '')
                # 提取 m3u8 链接中的域名
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
    blacklist = {'com', 'net', 'org', 'cn', 'tv', 'me', 'api', 'www', 'provide', 'vod', 'php', 'm3u8', 'index'}

    print("🚀 开始深度扫描 API 内隐藏的变体域名...")
    for site in db.get('sites', []):
        api = site.get('api', '')
        # 1. 提取 API 自身的词根
        api_domain = re.search(r'https?://([^/:]+)', api).group(1)
        
        # 2. 深度识别：进去抓视频播放域名
        video_domains = get_deep_domains(api)
        
        # 合并所有发现的域名进行词根提取
        for domain in [api_domain] + video_domains:
            parts = domain.split('.')
            for part in parts:
                # 提取核心词根 (去除数字和常见干扰词)
                clean_part = re.split(r'\d+|api|cj|zy|vip|msc|cdn', part.lower())[0]
                if len(clean_part) >= 3 and clean_part not in blacklist:
                    all_keywords.add(clean_part)
                elif len(part) >= 3 and part not in blacklist:
                    all_keywords.add(part)

    # 写入文件
    with open('MyVideo.list', 'w', encoding='utf-8') as f:
        f.write("# 深度扫描自动生成的规则 (含隐藏视频域名)\n")
        for k in sorted(list(all_keywords)):
            f.write(f"DOMAIN-KEYWORD,{k}\n")
    print(f"✅ 深度识别完成，共提取 {len(all_keywords)} 个核心特征。")

if __name__ == "__main__":
    generate()
