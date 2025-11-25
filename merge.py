import requests
import yaml

# -------- 配置 --------
SUB_URL = "https://api.touhou.center/sub/bd44806c62afd82b/clash"
TEMPLATE_FILE = "template.yaml"
OUTPUT_FILE = "output.yaml"

# 节点组名称
HK_GROUP_NAME = "🇭🇰 香港流量优先"
JP_GROUP_NAME = "🇯🇵 日本节点"
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

# ---- 自定义手动选择代理组 ----
custom_groups = [
    {
        "name": JP_GROUP_NAME,
        "type": "select",
        "proxies": japan_nodes + [REMOTE_GLOBAL_PROXY]
    },
    {
        "name": HK_GROUP_NAME,
        "type": "select",
        "proxies": hk05_nodes + [REMOTE_GLOBAL_PROXY]
    }
]

# ---- 合并 proxy-groups ----
final_groups = []
existing_names = set()

# 先加入 template/远程 groups
for g in groups:
    if g["name"] not in existing_names:
        final_groups.append(g)
        existing_names.add(g["name"])

# 加入自定义手动选择组
for g in custom_groups:
    if g["name"] not in existing_names:
        final_groups.append(g)
        existing_names.add(g["name"])

# ---- 合并最终 YAML ----
final = template.copy()
final["proxies"] = nodes
final["proxy-groups"] = final_groups

# ---- 合并规则 ----
template_rules = template.get("rules", [])
merged_rules = template_rules.copy() + rules

# 替换 RULE-SET,Global 为香港手动选择组
for i, rule in enumerate(merged_rules):
    if isinstance(rule, str) and rule.startswith("RULE-SET,Global"):
        merged_rules[i] = f"RULE-SET,Global,{HK_GROUP_NAME}"

final["rules"] = merged_rules

# ---- 合并 rule-providers ----
template_providers = template.get("rule-providers", {})
final["rule-providers"] = {**rule_providers, **template_providers}

# ---- 输出 YAML ----
save_yaml(OUTPUT_FILE, final)
print("Generated output.yaml successfully.")
