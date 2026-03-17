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
# 统一文件名与 Workflow 一致
OUTPUT_FILE = os.path.join(BASE_PATH, 'MyVideo.yml')

def get_deep_domains(api_url, site_name, existing_domains):
    found_domains = set()
    found_keywords = set()
    new_discoveries = []
    
    headers = {
        'User-Agent': 'okhttp/4.9.0',
        'Accept': 'application/json'
    }

    success = False
    for i in range(3):  # 尝试3次，减少由于单个站卡顿导致的整体超时
        try:
            timestamp = int(time.time())
            nonce = random.randint(100, 999)
            target_url = f"{api_url}?ac=detail&pg=1&_t={timestamp}&_n={nonce}"
            
            resp = requests.get(target_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                vod_list = data.get('list', [])
                if not vod_list:
                    time.sleep(random.uniform(0.5, 1.5))
                    continue
                
                success = True
                for vod in vod_list:
                    play_url = vod.get('vod_play_url', '')
                    # 匹配标准的 URL
                    urls = re.findall(r'https?://[^\$,\s]+', play_url)
                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]
                        if domain and len(domain) > 3 and '.' in domain:
                            if domain not in existing_domains:
                                new_discoveries.append(domain)
                                existing_domains.add(domain)
                            found_domains.add(domain)
                            
                            # 关键字提取优化
                            parts = domain.split('.')
                            if len(parts) >= 2:
                                main_name = parts[-2]
                                if len(main_name) > 4: 
                                    found_keywords.add(main_name)
                break 
            
        except Exception as e:
            if i == 2: print(f"    ❌ 网络异常: {str(e)}")
        
        if not success and i < 2:
            time.sleep(random.uniform(0.5, 2.0))

    return success, found_domains, found_keywords, new_discoveries

def generate():
    if not os.path.exists(JSON_DB):
        print("❌ 错误: 找不到 db.json")
        return

    # --- 1. 读取历史数据 ---
    all_domains = set()
    # 默认保底关键字
    all_keywords = {"m3u8", "yyv", "cdnlz", "yzzy", "wwzy", "10cong", "bfzy", "jszy", "360zy"}
    
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # 改进正则，兼容 Clash 格式提取
            all_keywords.update(re.findall(r'DOMAIN-KEYWORD,([^,\s\n]+)', content))
            all_domains.update(re.findall(r'DOMAIN-SUFFIX,([^,\s\n]+)', content))
    
    initial_count = len(all_domains) + len(all_keywords)
    print(f"📥 历史载入: 规则库已有 {initial_count} 条记录")

    # --- 2. 爬取新数据 ---
    try:
        with open(JSON_DB, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except Exception as e:
        print(f"❌ 读取 db.json 失败: {e}")
        return
    
    sites = db.get('sites', [])
    total = len(sites)
    print(f"🚀 开始扫描 {total} 个采集站...")

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知站')
        api = site.get('api', '')
        
        print(f"[{i}/{total}] 正在探测: {name} ", end="", flush=True)
        
        if api and api.startswith('http'):
            # 接口域名
            api_host = urlparse(api).netloc.split(':')[0]
            if api_host: all_domains.add(api_host)
            
            # 深入探测
            is_ok, domains, keywords, news = get_deep_domains(api, name, all_domains)
            
            if is_ok:
                print(f"✅ [发现新域名: {len(news)}]")
                all_keywords.update(keywords)
            else:
                print(f"❌ [超时或格式错误]")
        else:
            print(f"⏩ [跳过: 无效API]")

    # --- 3. 清洗与去重 ---
    exclude = ["com", "net", "org", "www", "cdn", "index", "html", "github", "vip", "cloud"]
    
    # 关键字清洗
    final_keywords = set()
    for k in all_keywords:
        k_clean = k.lower().strip()
        if len(k_clean) > 2 and k_clean not in exclude:
            final_keywords.add(k_clean)

    # 域名清洗：如果域名已经包含在关键词中，则不再单独添加后缀规则
    final_domains = set()
    for d in all_domains:
        d_clean = d.lower().strip()
        if not d_clean or "." not in d_clean: continue
        # 如果域名中包含任何一个关键词，跳过（简化规则）
        if any(kw in d_clean for kw in final_keywords):
            continue
        final_domains.add(d_clean)

    # --- 4. 写入文件 ---
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("payload:\n")
        for kw in sorted(list(final_keywords)):
            f.write(f"  - DOMAIN-KEYWORD,{kw}\n")
        for d in sorted(list(final_domains)):
            f.write(f"  - DOMAIN-SUFFIX,{d}\n")

    print("\n" + "="*40)
    print(f"🎉 任务完成! 现有规则总数: {len(final_keywords) + len(final_domains)}")
    print(f"📦 文件已保存至: {OUTPUT_FILE}")
    print("="*40)

if __name__ == "__main__":
    generate()
