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
# 统一输出文件名
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
    for i in range(6):  # 尝试6次，应对采集站偶尔的卡顿
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
                    # 匹配标准的 URL 地址
                    urls = re.findall(r'https?://[^\$,\s]+', play_url)
                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]
                        if domain and len(domain) > 3 and '.' in domain:
                            if domain not in existing_domains:
                                new_discoveries.append(domain)
                                existing_domains.add(domain)
                            found_domains.add(domain)
                            
                            # 关键字提取优化：取主域名部分
                            parts = domain.split('.')
                            if len(parts) >= 2:
                                main_name = parts[-2]
                                # 只有长度大于4的才认为是有效特征词，防止抓到 com/net 等
                                if len(main_name) > 4:  
                                    found_keywords.add(main_name)
                break 
            
        except Exception as e:
            if i == 2: print(f"    ❌ 网络异常 ({site_name}): {str(e)}")
        
        if not success and i < 2:
            time.sleep(random.uniform(0.5, 4.0))

    return success, found_domains, found_keywords, new_discoveries

def generate():
    if not os.path.exists(JSON_DB):
        print(f"❌ 错误: 找不到数据库文件 {JSON_DB}")
        return

    # --- 1. 初始化规则库 ---
    all_domains = set()
    # 基础保底关键字（你最常用的那些）
    all_keywords = {"m3u8", "yyv", "cdnlz", "yzzy", "wwzy", "10cong", "bfzy", "jszy", "360zy"}
    
    # 如果已有旧文件，先读取进来做增量更新
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            all_keywords.update(re.findall(r'DOMAIN-KEYWORD,([^,\s\n]+)', content))
            all_domains.update(re.findall(r'DOMAIN-SUFFIX,([^,\s\n]+)', content))
    
    print(f"📥 历史载入: 规则库已有 {len(all_domains) + len(all_keywords)} 条记录")

    # --- 2. 解析 db.json 并扫描 ---
    try:
        with open(JSON_DB, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except Exception as e:
        print(f"❌ 读取 db.json 失败: {e}")
        return
    
    sites = db.get('sites', [])
    total = len(sites)
    print(f"🚀 开始探测 {total} 个采集站...")

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知站')
        api = site.get('api', '')
        
        print(f"[{i}/{total}] 正在探测: {name} ", end="", flush=True)
        
        if api and api.startswith('http'):
            api_host = urlparse(api).netloc.split(':')[0]
            if api_host: all_domains.add(api_host)
            
            is_ok, domains, keywords, news = get_deep_domains(api, name, all_domains)
            if is_ok:
                print(f"✅ [新增: {len(news)}]")
                all_keywords.update(keywords)
            else:
                print(f"❌ [连接失败]")
        else:
            print(f"⏩ [跳过]")

    # --- 3. 核心清洗与去重逻辑 ---
    # 排除掉常见的非特征字符
    exclude_list = {"com", "net", "org", "www", "cdn", "index", "html", "github", "vip", "cloud", "video", "api"}
    
    final_keywords = set()
    for k in all_keywords:
        k_clean = k.lower().strip()
        if len(k_clean) > 2 and k_clean not in exclude_list:
            final_keywords.add(k_clean)

    final_domains = set()
    for d in all_domains:
        d_clean = d.lower().strip()
        if not d_clean or "." not in d_clean: continue
        # 💡 优化：如果域名已被关键词覆盖，则不再重复添加后缀规则，精简 YML 体积
        if any(kw in d_clean for kw in final_keywords):
            continue
        final_domains.add(d_clean)

    # --- 4. 生成标准 YAML Payload (修复缩进与空格) ---
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
            f.write("payload:\n")
            # 必须使用 2 个标准的英文半角空格进行缩进
            for kw in sorted(list(final_keywords)):
                if kw.strip():
                    f.write(f"  - DOMAIN-KEYWORD,{kw.strip()}\n")
            
            for d in sorted(list(final_domains)):
                if d.strip():
                    f.write(f"  - DOMAIN-SUFFIX,{d.strip()}\n")
        print(f"🎉 规范文件已存至: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")

    print("\n" + "="*40)
    print(f"🎉 任务完成! 最终规则总数: {len(final_keywords) + len(final_domains)}")
    print(f"📦 规范文件已存至: {OUTPUT_FILE}")
    print("="*40)

if __name__ == "__main__":
    generate()
