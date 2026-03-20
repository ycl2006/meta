# 🎬 Auto Video Rules Generator (PROD)

![Update Status](https://img.shields.io/badge/Status-Live-brightgreen)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![License](https://img.shields.io/badge/License-MIT-orange)

这是一个基于 Python 自动化采集的影视规则集生成器。它会自动从指定的 CMS 接口中嗅探、清洗并去重，生成最适合 **OpenClash / Clash** 使用的 YAML 规则文件。

---

## 🚀 自动化特性

* **定时更新**：每天 **00:00, 08:00, 16:00** (北京时间) 自动运行。
* **智能过滤**：自动识别根域名与子域名，过滤低频脏数据。
* **权重继承**：保留历史有效规则，确保视频流播放的连贯性。
* **格式兼容**：原生支持 Clash `behavior: classical` 格式。

---

## 🛠️ 如何在 OpenClash 中使用？

1.  进入 OpenClash -> **配置文件订阅** 或 **第三方规则订阅**。
2.  添加新的规则集 (Rule Provider)：
    * **策略组**：选择你的“视频流”或“直连”策略。
    * **类型**：`http`
    * **行为**：`classical`
    * **格式**：`yaml`
    * **URL**：`https://raw.githubusercontent.com/你的用户名/仓库名/main/MyVideo.yml`
3.  保存配置并应用。

### 示例配置 (Config.yaml)

```yaml
rule-providers:
  MyVideo:
    type: http
    behavior: classical
    path: ./rule_provider/MyVideo.yml
    url: "[https://raw.githubusercontent.com/你的用户名/仓库名/main/MyVideo.yml](https://raw.githubusercontent.com/你的用户名/仓库名/main/MyVideo.yml)"
    interval: 86400

📊 数据来源
规则基于 db.json 中配置的站点接口实时嗅探生成。

注意：本项目仅提供域名规则采集工具，不存储任何视频资源。
