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


# =============================
# 🌐 URL提取（嵌套+解码+m3u8）
# =============================
def extract_urls(text):
    urls = set()
    if not text:
        return urls

    base_urls = re.findall(r'https?://[^\$,\s]+', text)
    urls.update(base_urls)

    for u in list(base_urls):
        try:
            decoded = requests.utils.unquote(u)
            nested = re.findall(r'https?://[^\$,\s]+', decoded)
            urls.update(nested)
        except:
            pass

    m3u8_urls = re.findall(r'https?://[^\s]+\.m3u8', text)
    urls.update(m3u8_urls)

    return urls


# =============================
# 🌍 根域名提取
# =============================
def get_root_domain(domain):
    parts = domain.split('.')
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


# =============================
# 📡 深度采集
# =============================
def get_deep_domains(api_url, site_name, domain_counter):
    found_domains = set()
    found_keywords = set()

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }

    success = False

    for i in range(6):
        try:
            page = random.randint(1, 10)
            url = f"{api_url}?ac=detail&pg={page}"

            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                vod_list = data.get('list', [])

                if not vod_list:
                    continue

                success = True

                for vod in vod_list:
                    text = " ".join([
                        vod.get('vod_play_url', ''),
                        vod.get('vod_down_url', ''),
                        vod.get('vod_play_from', ''),
                        str(vod)
                    ])

                    urls = extract_urls(text)

                    for u in urls:
                        domain = urlparse(u).netloc.split(':')[0]

                        if not domain or "." not in domain:
                            continue

                        root = get_root_domain(domain)

                        # 权重统计
                        domain_counter[domain] = domain_counter.get(domain, 0) + 1
                        domain_counter[root] = domain_counter.get(root, 0) + 1

                        found_domains.add(domain)
                        found_domains.add(root)

                        # 关键词（只取根域）
                        main = root.split('.')[0]

                        bad = {
                            "static","player","stream","media","video",
                            "cache","play","download","file","cdn","api","data"
                        }

                        if len(main) > 3 and main not in bad:
                            found_keywords.add(main)

                break

        except:
            pass

        time.sleep(random.uniform(0.5, 2))

    return success, found_domains, found_keywords


# =============================
# 🚀 主流程
# =============================
def generate():
    if not os.path.exists(JSON_DB):
        print("❌ 缺少 db.json")
        return

    all_domains = set()
    all_keywords = {
        "m3u8","cdnlz","yzzy","bfzy","jszy","360zy","ffzy","lzzy"
    }

    domain_counter = {}

    print("📥 读取旧规则（增量 + 权重继承）")

    # =============================
    # 🔄 读取旧YML（核心升级点）
    # =============================
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

            old_domains = set(re.findall(r'DOMAIN(?:-SUFFIX)?,([^,\s\n]+)', content))
            old_keywords = set(re.findall(r'DOMAIN-KEYWORD,([^,\s\n]+)', content))

            bad_kw = {
                "static","player","stream","media","video",
                "cache","play","download","file","cdn","api","data"
            }

            # 🔥 域名继承 + 权重+2
            for d in old_domains:
                d = d.lower().strip()
                if "." in d:
                    all_domains.add(d)
                    domain_counter[d] = domain_counter.get(d, 0) + 2

                    root = get_root_domain(d)
                    all_domains.add(root)
                    domain_counter[root] = domain_counter.get(root, 0) + 2

            # 🔥 关键词继承
            for k in old_keywords:
                k = k.lower().strip()
                if len(k) > 3 and k not in bad_kw:
                    all_keywords.add(k)

    # =============================
    # 📡 读取站点
    # =============================
    with open(JSON_DB, 'r', encoding='utf-8') as f:
        db = json.load(f)

    sites = db.get('sites', [])

    print(f"🚀 扫描 {len(sites)} 个站点")

    for i, site in enumerate(sites, 1):
        name = site.get('name', '未知')
        api = site.get('api', '')

        print(f"[{i}] {name} ", end="")

        if api.startswith("http"):
            ok, domains, kws = get_deep_domains(api, name, domain_counter)

            if ok:
                all_domains.update(domains)
                all_keywords.update(kws)
                print("✅")
            else:
                print("❌")
        else:
            print("⏩")

    # =============================
    # 🧹 稳定过滤（核心）
    # =============================
    final_domains = set()

    for d in all_domains:
        d = d.lower().strip()
        if "." not in d:
            continue

        # 根域直接保留
        if d.count('.') == 1:
            final_domains.add(d)
            continue

        # 子域必须权重>=2
        if domain_counter.get(d, 0) >= 2:
            final_domains.add(d)

    final_keywords = set()
    for k in all_keywords:
        k = k.lower().strip()
        if len(k) > 3:
            final_keywords.add(k)

    # =============================
    # 📝 输出（LIST 格式：适配 SubConverter/ACL4SSR）
    # =============================
    # 将输出文件名从 .yml 改为 .list
    LIST_OUTPUT_FILE = OUTPUT_FILE.replace('.yml', '.list')
    
    with open(LIST_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # 🎯 精确匹配
        for d in sorted(final_domains):
            if d.count('.') >= 2:
                f.write(f"DOMAIN,{d}\n")

        # 🔥 核心：后缀匹配（最常用）
        for d in sorted(final_domains):
            if d.count('.') == 1:
                f.write(f"DOMAIN-SUFFIX,{d}\n")

        # 🧠 关键词泛匹配
        for k in sorted(final_keywords):
            f.write(f"DOMAIN-KEYWORD,{k}\n")

    print("\n🎉 完成转换")
    print(f"📄 文件已保存为: {os.path.basename(LIST_OUTPUT_FILE)}")
    print(f"🌐 域名数量: {len(final_domains)}")
    print(f"🧠 关键词数量: {len(final_keywords)}")

if __name__ == "__main__":
    generate()
