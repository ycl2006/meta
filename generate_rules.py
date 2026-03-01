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

def get_deep_domains(api_url, site_name, existing_domains):
    found_domains = set()
    found_keywords = set()
    new_discoveries = []
    
    # 增加一点随机性绕过基础防火墙
    headers = {
        'User-Agent': 'okhttp/4.9.0',
        'Accept': 'application/json'
    }

    success = False
    for i in range(5): # 尝试5次
        try:
            timestamp = int(time.time())
            nonce = random.randint(100, 999)
            target_url = f"{api_url}?ac=detail&pg=1&_t={timestamp}&_n={nonce}"
            
            resp = requests.get(target_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                vod_list = data.get('list', [])
                if not vod_list:
                    continue
                
                success = True
                for vod in vod_list:
                    play_url = vod.get('vod_play_url', '')
                    urls = re.findall(r'https?://[^\$,\s]+', play_url)
                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]
                        if domain and len(domain) > 3:
                            found_domains.add(domain)
                            # 实时检查是否是新域名
                            if domain not in existing_domains:
                                new_discoveries.append(domain)
                                existing_domains.add(domain) # 避免单次重复显示
                            
                            # 提取关键字逻辑
                            parts = domain.split('.')
                            if len(parts) >= 3:
                                prefix = parts[0]
                                if re.match(r'^[a-z]{1,4}\d+$', prefix):
                                    kw = re.sub(r'\d+', '', prefix)
                                    if len(kw) >= 2: found_keywords.add(kw)
                            if len(parts) >= 2:
                                main_name = parts[-2]
                                if len(main_name) > 4: found_keywords.add(main_name)
                break 
            else:
                print(f"   ⚠️  HTTP 错误: {resp.status_code}")
        except Exception as e:
            if i == 2: print(f"   ❌ 网络异常: {str(e)}")
            continue
        time.sleep(1)

    return success, found_domains, found_keywords, new_discoveries

def generate():
    if not os.path.exists(JSON_DB):
        print("❌ 错误: 找不到 db.json")
        return

    # --- 1. 读取历史数据 ---
    all_domains, all_keywords = set(), {"m3u8", "yyv", "cdnlz", "yzzy", "wwzy", "10cong", "bfzy", "jszy", "360zy"}
    if os.path.exists(OUTPUT_LIST):
        with open(OUTPUT_LIST, 'r', encoding='utf-8') as f:
            content = f.read()
            all_keywords.update(re.findall(r'DOMAIN-KEYWORD,([^,\s]+)', content))
            all_domains.update(re.findall(r'DOMAIN-SUFFIX,([^,\s]+)', content))
    
    initial_dm_count = len(all_domains)
    print(f"📥 历史载入: 域名库已有 {initial_dm_count} 条记录")

    # --- 2. 爬取新数据 ---
    with open(JSON_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    sites = db.get('sites', [])
    total = len(sites)
    print(f"🚀 开始扫描 {total} 个采集站...")

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知站')
        api = site.get('api', '')
        
        # 实时显示探测状态
        print(f"[{i}/{total}] 正在探测: {name} ", end="", flush=True)
        
        if api and api.startswith('http'):
            # 记录接口主域名
            api_host = urlparse(api).netloc.split(':')[0]
            if api_host: all_domains.add(api_host)
            
            # 深入探测
            is_ok, domains, keywords, news = get_deep_domains(api, name, all_domains)
            
            if is_ok:
                print(f"✅ [成功]")
                if news:
                    for d in news:
                        print(f"   ✨ 发现新域名: {d}")
                all_keywords.update(keywords)
            else:
                print(f"❌ [失败或无数据]")
        else:
            print(f"⏩ [跳过: 无效API]")

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

    # --- 5. 统计报告 ---
    added_dm = len(final_domains) - initial_dm_count
    print("\n" + "="*40)
    print(f"🎉 扫描任务完成!")
    print(f"✨ 本次新收割域名: {max(0, added_dm)} 条")
    print(f"📦 规则文件已更新: {OUTPUT_LIST}")
    print("="*40)

if __name__ == "__main__":
    generate()
