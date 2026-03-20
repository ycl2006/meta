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


def extract_urls(text):
    """🔥 提取所有URL（含嵌套 / 解码 / m3u8）"""
    urls = set()

    if not text:
        return urls

    # 基础URL
    base_urls = re.findall(r'https?://[^\s\$,"]+', text)
    urls.update(base_urls)

    # 🔥 解码嵌套URL（关键）
    for u in list(base_urls):
        try:
            decoded = requests.utils.unquote(u)
            nested = re.findall(r'https?://[^\s\$,"]+', decoded)
            urls.update(nested)
        except:
            pass

    # 🔥 强抓 m3u8
    m3u8_urls = re.findall(r'https?://[^\s]+\.m3u8', text)
    urls.update(m3u8_urls)

    return urls


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
            page = random.randint(1, 8)  # 🔥 更深扫描

            url = f"{api_url}?ac=detail&pg={page}&_t={timestamp}&_n={nonce}"

            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                vod_list = data.get('list', [])

                if not vod_list:
                    time.sleep(random.uniform(0.5, 1.5))
                    continue

                success = True

                for vod in vod_list:
                    # 🔥 多字段合并抓取
                    raw_text = " ".join([
                        vod.get('vod_play_url', ''),
                        vod.get('vod_down_url', ''),
                        vod.get('vod_play_from', ''),
                        json.dumps(vod, ensure_ascii=False)  # 🔥 全字段兜底
                    ])

                    urls = extract_urls(raw_text)

                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]

                        if domain and len(domain) > 3 and '.' in domain:
                            if domain not in existing_domains:
                                new_discoveries.append(domain)
                                existing_domains.add(domain)

                            found_domains.add(domain)

                            # 🔥 提取主域关键词
                            parts = domain.split('.')
                            if len(parts) >= 2:
                                main = parts[-2].lower()

                                bad_keywords = {
                                    "static", "player", "stream", "media",
                                    "video", "cache", "play", "download",
                                    "file", "cdn", "api", "data", "img",
                                    "js", "css"
                                }

                                if len(main) > 4 and main not in bad_keywords:
                                    found_keywords.add(main)

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
        print(f"❌ 找不到 db.json")
        return

    all_domains = set()

    # 🔥 核心保底关键词
    all_keywords = {
        "m3u8", "yyv", "cdnlz", "yzzy",
        "wwzy", "bfzy", "jszy", "360zy"
    }

    print("🚀 开始全量扫描...")

    try:
        with open(JSON_DB, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except Exception as e:
        print(f"❌ db.json 读取失败: {e}")
        return

    sites = db.get('sites', [])

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知')
        api = site.get('api', '')

        print(f"[{i}/{len(sites)}] {name} ", end="", flush=True)

        if api.startswith("http"):
            host = urlparse(api).netloc.split(':')[0]
            if host:
                all_domains.add(host)

            ok, domains, keywords, news = get_deep_domains(api, name, all_domains)

            if ok:
                print(f"✅ +{len(news)}")
                all_keywords.update(keywords)
            else:
                print("❌")
        else:
            print("⏩")

    # =============================
    # 🔥 清洗规则
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

        main = d.split('.')[-2]

        # 🔥 防误杀（仅完全匹配才跳过）
        if main in final_keywords:
            continue

        final_domains.add(d)

    # =============================
    # 🔥 输出 YAML
    # =============================

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
            f.write("payload:\n")

            # 精确匹配
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
