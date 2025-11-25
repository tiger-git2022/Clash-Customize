import requests
import yaml

# -------- 配置 --------
SUB_URL = "https://api.touhou.center/sub/bd44806c62afd82b/clash"
TEMPLATE_FILE = "template.yaml"
OUTPUT_FILE = "output.yaml"

# fallback 配置
FALLBACK_GROUP_NAME = "🇭🇰 香港流量优先Fallback"
LOCAL_HK_PROXY = "🇭🇰 香港自动选择（0.5倍率)"
REMOTE_GLOBAL_PROXY = "🌐 国际网站"

# -------- 工具函数 --------
def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True)

# -------- 下载订阅 --------
print("Downloading subscription...")
sub = requests.get(SUB_URL, timeout=10).text
sub_yaml = yaml.safe_load(sub)

template = load_yaml(TEMPLATE_FILE)

nodes = sub_yaml.get("proxies", [])
groups = sub_yaml.get("proxy-groups", [])
rules = sub_yaml.get("rules", [])
rule_providers = sub_yaml.get("rule-providers", {})

print(f"Loaded {len(nodes)} nodes")

# ---- 自动筛选节点 ----
# 日本节点：排除 "3倍率" 和 "流媒体"
japan_nodes = [
    n["name"] for n in nodes
    if "日本" in n["name"] and "3倍率" not in n["name"] and "流媒体" not in n["name"]
]

# 香港节点：0.5 倍率
hk05_nodes = [n["name"] for n in nodes if ("香港" in n["name"] and "0.5" in n["name"])]

print("Japan nodes:", len(japan_nodes))
print("HK 0.5 nodes:", len(hk05_nodes))

# ---- 自定义代理组 ----
custom_groups = [
    {
        "name": "🇯🇵 日本节点",
        "type": "url-test",
        "proxies": japan_nodes,
        "url": "http://www.gstatic.com/generate_204",
        "interval": 300
    },
    {
        "name": LOCAL_HK_PROXY,
        "type": "url-test",
        "proxies": hk05_nodes,
        "url": "http://www.gstatic.com/generate_204",
        "interva
