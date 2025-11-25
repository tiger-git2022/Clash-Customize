import requests
import yaml
import re

SUB_URL = "https://api.touhou.center/sub/bd44806c62afd82b/clash"

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True)

print("Downloading subscription...")
sub = requests.get(SUB_URL).text
sub_yaml = yaml.safe_load(sub)

template = load_yaml("template.yaml")

nodes = sub_yaml.get("proxies", [])
groups = sub_yaml.get("proxy-groups", [])

print(f"Loaded {len(nodes)} nodes")

# ---- 自动筛选节点 ----
japan_nodes = [n["name"] for n in nodes if "日本" in n["name"]]
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
        "name": "🇭🇰 香港自动选择（0.5倍率）",
        "type": "url-test",
        "proxies": hk05_nodes,
        "url": "http://www.gstatic.com/generate_204",
        "interval": 300
    }
]

# ---- 合并 ----
final = template
final["proxies"] = nodes
final["proxy-groups"] = groups + custom_groups

# 规则无需处理，因为 template.yaml 已包含 RULE-SET → 日本节点

save_yaml("output.yaml", final)
print("Generated output.yaml successfully.")
