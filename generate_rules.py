import json
import re

# 1. 设置：如果你的 db.json 是远程链接，可以用 requests 获取；如果是本地文件则直接打开
def get_keywords_from_db():
    try:
        with open('db.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        keywords = set()
        # 常见非核心词过滤（防止误杀）
        blacklist = {'com', 'net', 'org', 'cn', 'tv', 'me', 'api', 'www', 'provide', 'vod', 'php'}
        
        for site in data.get('sites', []):
            url = site.get('api', '')
            # 提取域名（例如 ffzy5.tv）
            match = re.search(r'https?://([^/:]+)', url)
            if match:
                domain = match.group(1)
                # 分割域名，提取词干
                parts = domain.split('.')
                for part in parts:
                    # 只有长度大于 3 且不在黑名单的词才算核心词
                    if len(part) > 3 and part not in blacklist:
                        keywords.add(part)
        return sorted(list(keywords))
    except Exception as e:
        print(f"Error: {e}")
        return []

# 2. 生成 Clash 规则格式
keywords = get_keywords_from_db()
content = "# Auto-generated Video Rules\n"
for k in keywords:
    content += f"DOMAIN-KEYWORD,{k}\n"

# 3. 写入文件
with open('MyVideo.list', 'w', encoding='utf-8') as f:
    f.write(content)

print("Rules generated successfully!")
