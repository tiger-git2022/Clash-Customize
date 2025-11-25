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
        "interval": 300
    }
]

# ---- 添加 Global Fallback ----
custom_fallback = {
    "name": FALLBACK_GROUP_NAME,
    "type": "fallback",
    "proxies": [LOCAL_HK_PROXY, REMOTE_GLOBAL_PROXY],
    "fallback-filter": {
        "fail-count": 1,
        "interval": 300
    }
}

# ---- 合并 proxy-groups ----
final_groups = []

existing_names = set()
# 先加入 template/远程 groups
for g in groups:
    if g["name"] not in existing_names:
        final_groups.append(g)
        existing_names.add(g["name"])

# 再加入自定义组（日本、香港）
for g in custom_groups:
    if g["name"] not in existing_names:
        final_groups.append(g)
        existing_names.add(g["name"])

# 最后加入 fallback
if FALLBACK_GROUP_NAME not in existing_names:
    final_groups.append(custom_fallback)
    existing_names.add(FALLBACK_GROUP_NAME)

# ---- 合并最终 YAML ----
final = template.copy()
final["proxies"] = nodes
final["proxy-groups"] = final_groups

# ---- 合并规则 ----
template_rules = template.get("rules", [])
merged_rules = template_rules.copy() + rules  # 本地规则在前，远程规则在后

# 替换 RULE-SET,Global 为 fallback group
for i, rule in enumerate(merged_rules):
    if isinstance(rule, str) and rule.startswith("RULE-SET,Global"):
        merged_rules[i] = f"RULE-SET,Global,{FALLBACK_GROUP_NAME}"

final["rules"] = merged_rules

# ---- 合并 rule-providers ----
template_providers = template.get("rule-providers", {})
final["rule-providers"] = {**rule_providers, **template_providers}

# ---- 输出 YAML ----
save_yaml(OUTPUT_FILE, final)
print("Generated output.yaml successfully.")
