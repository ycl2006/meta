import json
import re
import os
import requests
import time
import random
from urllib.parse import urlparse

# =============================
# 📁 配置区（请确保路径正确）
# =============================
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JSON_DB = os.path.join(BASE_PATH, 'db.json')
OUTPUT_FILE = os.path.join(BASE_PATH, 'MyVideo.list')  # 统一使用 .list 格式

# 模拟浏览器头，防止被 API 拦截
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json'
}

# =============================
# 🔍 核心逻辑组件
# =============================

def get_root_domain(domain):
    """提取根域名，例如 a.b.com -> b.com"""
    if not domain or "." not in domain:
        return domain
    parts = domain.split('.')
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain

def extract_urls_from_text(text):
    """从杂乱文本中嗅探所有 URL"""
    if not text: return set()
    # 匹配 http/https 开头的非空字符，直到遇到分隔符
    return set(re.findall(r'https?://[^\$,\s\x22\x27]+', text))

# =============================
# 📡 深度采集器（带重试与错误捕获）
# =============================
def fetch_site_domains(api_url, domain_counter):
    found_domains = set()
    found_keywords = set()
    
    # 尝试不同页面增加样本多样性
    for attempt in range(3):
        try:
            target_page = random.randint(1, 20)
            target_url = f"{api_url}?ac=detail&pg={target_page}"
            
            response = requests.get(target_url, headers=HEADERS, timeout=12)
            if response.status_code != 200:
                continue
            
            data = response.json()
            vod_list = data.get('list', [])
            if not vod_list:
                continue

            for vod in vod_list:
                # 拼接所有可能包含域名的字段
                raw_content = f"{vod.get('vod_play_url','')}|{vod.get('vod_play_from','')}"
                urls = extract_urls_from_text(raw_content)
                
                for u in urls:
                    domain = urlparse(u).netloc.split(':')[0].lower()
                    if not domain or "." not in domain:
                        continue
                    
                    root = get_root_domain(domain)
                    # 权重系统：记录域名出现的频率
                    domain_counter[domain] = domain_counter.get(domain, 0) + 1
                    domain_counter[root] = domain_counter.get(root, 0) + 1
                    
                    found_domains.add(domain)
                    found_domains.add(root)
                    
                    # 提取关键词（用于泛匹配）
                    keyword = root.split('.')[0]
                    if len(keyword) > 3:
                        found_keywords.add(keyword)
            
            # 只要成功抓到一页就跳出，减轻 API 压力
            return True, found_domains, found_keywords
            
        except Exception as e:
            # 静默处理单个 API 错误
            continue
            
    return False, set(), set()

# =============================
# 🚀 主生成流程
# =============================
def main():
    print("--- 🎬 开始执行规则生成程序 ---")
    
    if not os.path.exists(JSON_DB):
        print(f"❌ 错误: 找不到数据库文件 {JSON_DB}")
        return

    all_domains = set()
    all_keywords = {"m3u8", "cdnlz", "yzzy", "bfzy", "jszy", "360zy", "ffzy", "lzzy"}
    domain_counter = {}

    # 1. 继承旧规则权重（如果有）
    if os.path.exists(OUTPUT_FILE):
        print(f"📥 正在读取现有规则以维持稳定性...")
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                # 提取存量域名
                old_ds = re.findall(r'DOMAIN(?:-SUFFIX)?,\s*([^,\s\n]+)', content)
                for d in old_ds:
                    d = d.lower().strip()
                    all_domains.add(d)
                    domain_counter[d] = domain_counter.get(d, 0) + 5 # 给存量规则极高权重
        except:
            pass

    # 2. 读取站点并采集
    try:
        with open(JSON_DB, 'r', encoding='utf-8') as f:
            db_data = json.load(f)
            sites = db_data.get('sites', [])
    except Exception as e:
        print(f"❌ JSON 解析失败: {e}")
        return

    print(f"📡 准备扫描 {len(sites)} 个影视接口...")
    for i, site in enumerate(sites, 1):
        name = site.get('name', 'Unknown')
        api = site.get('api', '')
        
        print(f"[{i:02d}/{len(sites)}] 正在嗅探: {name.ljust(10)} ", end="", flush=True)
        
        if api.startswith("http"):
            success, domains, kws = fetch_site_domains(api, domain_counter)
            if success:
                all_domains.update(domains)
                all_keywords.update(kws)
                print("✅ Done")
            else:
                print("⚠️ Skip")
        else:
            print("⏩ Null")

    # 3. 智能清洗与过滤
    # 只有出现次数超过 1 次（或者是根域名）才保留，防止脏数据
    final_domains = set()
    for d in all_domains:
        if d.count('.') == 1 or domain_counter.get(d, 0) >= 2:
            final_domains.add(d)

    # 排除常见的非视频 CDN 或 API 关键词
    blacklist_kw = {"static", "api", "player", "image", "script", "style", "css", "js"}
    final_keywords = {k for k in all_keywords if k not in blacklist_kw and len(k) > 3}

    # 4. 写入文件（LIST 格式）
    print(f"📝 正在整理并写入 {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # 按类型排序写入
            # A. 精确子域名
            for d in sorted(list(final_domains)):
                if d.count('.') >= 2:
                    f.write(f"DOMAIN,{d}\n")
            # B. 核心根域名（后缀匹配）
            for d in sorted(list(final_domains)):
                if d.count('.') == 1:
                    f.write(f"DOMAIN-SUFFIX,{d}\n")
            # C. 关键词泛匹配
            for k in sorted(list(final_keywords)):
                f.write(f"DOMAIN-KEYWORD,{k}\n")
                
        print(f"🎉 任务圆满完成！共生成 {len(final_domains)} 条域名规则。")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")

if __name__ == "__main__":
    main()
