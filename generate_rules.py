import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_DB = os.path.join(BASE_PATH, 'db.json')
OUTPUT_FILE = os.path.join(BASE_PATH, 'MyVideo.yml')

def get_deep_domains(api_url, site_name, existing_domains):
    found_domains = set()
    found_keywords = set()
    new_discoveries = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
        'Accept': 'application/json'
    }

    success = False

    for i in range(6):
        try:
            timestamp = int(time.time())
            nonce = random.randint(100, 999)
            page = random.randint(1, 5)  # ✅ 随机页提升覆盖率

            target_url = f"{api_url}?ac=detail&pg={page}&_t={timestamp}&_n={nonce}"

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

                    urls = re.findall(r'https?://[^\$,\s]+', play_url)

                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]

                        if domain and len(domain) > 3 and '.' in domain:
                            if domain not in existing_domains:
                                new_discoveries.append(domain)
                                existing_domains.add(domain)

                            found_domains.add(domain)

                            # ✅ 提取主域名关键词
                            parts = domain.split('.')
                            if len(parts) >= 2:
                                main_name = parts[-2].lower()

                                bad_keywords = {
                                    "static", "player", "stream", "media",
                                    "video", "cache", "play", "download",
                                    "file", "cdn", "api", "data"
                                }

                                if len(main_name) > 4 and main_name not in bad_keywords:
                                    found_keywords.add(main_name)

                break

        except requests.exceptions.Timeout:
            print(f"    ⏱️ 超时: {site_name}")
        except requests.exceptions.RequestException as e:
            if i == 2:
                print(f"    ❌ 请求失败 ({site_name}): {str(e)}")

        time.sleep(random.uniform(0.5, 2.0))

    return success, found_domains, found_keywords, new_discoveries


def generate():
    if not os.path.exists(JSON_DB):
        print(f"❌ 找不到数据库文件: {JSON_DB}")
        return

    all_domains = set()
    all_keywords = {"m3u8", "yyv", "cdnlz", "yzzy", "wwzy", "10cong", "bfzy", "jszy", "360zy"}

    # ✅ 读取旧规则（增量更新）
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            all_keywords.update(re.findall(r'DOMAIN-KEYWORD,([^,\s\n]+)', content))
            all_domains.update(re.findall(r'DOMAIN-SUFFIX,([^,\s\n]+)', content))

    print(f"📥 历史规则: {len(all_domains) + len(all_keywords)} 条")

    # 读取 db.json
    try:
        with open(JSON_DB, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except Exception as e:
        print(f"❌ db.json 读取失败: {e}")
        return

    sites = db.get('sites', [])
    total = len(sites)

    print(f"🚀 开始扫描 {total} 个站点...")

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知')
        api = site.get('api', '')

        print(f"[{i}/{total}] {name} ", end="", flush=True)

        if api.startswith("http"):
            api_host = urlparse(api).netloc.split(':')[0]
            if api_host:
                all_domains.add(api_host)

            is_ok, domains, keywords, news = get_deep_domains(api, name, all_domains)

            if is_ok:
                print(f"✅ +{len(news)}")
                all_keywords.update(keywords)
            else:
                print("❌ 失败")
        else:
            print("⏩ 跳过")

    # =============================
    # ✅ 清洗规则
    # =============================

    exclude_list = {
        "com", "net", "org", "www", "cdn", "index",
        "html", "github", "vip", "cloud", "video", "api"
    }

    final_keywords = set()
    for k in all_keywords:
        k = k.lower().strip()
        if len(k) > 2 and k not in exclude_list:
            final_keywords.add(k)

    final_domains = set()
    for d in all_domains:
        d = d.lower().strip()
        if not d or "." not in d:
            continue

        main_part = d.split('.')[-2]

        # ✅ 只在完全匹配关键词才跳过（防误杀）
        if main_part in final_keywords:
            continue

        final_domains.add(d)

    # =============================
    # ✅ 生成 YAML（优化版）
    # =============================

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
            f.write("payload:\n")

            # 🎯 精确匹配（优先）
            for d in sorted(final_domains):
                f.write(f"  - DOMAIN,{d}\n")

            # 🎯 关键词
            for kw in sorted(final_keywords):
                f.write(f"  - DOMAIN-KEYWORD,{kw}\n")

            # 🎯 后缀兜底
            for d in sorted(final_domains):
                f.write(f"  - DOMAIN-SUFFIX,{d}\n")

        print(f"🎉 已生成: {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ 写入失败: {e}")
        return

    print("\n" + "="*40)
    print(f"🎉 完成! 总规则: {len(final_keywords) + len(final_domains)}")
    print("="*40)


if __name__ == "__main__":
    generate()
