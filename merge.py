#!/usr/bin/env python3
# merge.py - generate output.yaml with custom groups always at front (both in proxy-groups list and inside each group)
# Requires: requests, PyYAML

import re
import sys
import requests
import yaml
from copy import deepcopy

# -------- 配置 --------
SUB_URL = "https://api.touhou.center/sub/bd44806c62afd82b/clash"
TEMPLATE_FILE = "template.yaml"
OUTPUT_FILE = "output.yaml"

# 自定义节点组名称
HK_GROUP = "🇭🇰 香港节点"
JP_GROUP = "🇯🇵 日本节点"
TW_GROUP = "🇹🇼 台湾节点"

# -------- 工具函数 --------
def load_yaml(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}")
        sys.exit(1)

def save_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

# -------- 下载订阅 --------
print("Downloading subscription from:", SUB_URL)
resp = requests.get(SUB_URL, timeout=20)
resp.raise_for_status()
sub_yaml = yaml.safe_load(resp.text)

# -------- 读取 template --------
template = load_yaml(TEMPLATE_FILE)

nodes = sub_yaml.get("proxies", []) or []
remote_groups = sub_yaml.get("proxy-groups", []) or []

# 保留远程 rules 和 rule-providers
remote_rules = sub_yaml.get("rules", []) or []
remote_rule_providers = sub_yaml.get("rule-providers", {}) or {}

# 本地 template 的 rules 和 rule-providers
local_rules = template.get("rules", []) or []
local_rule_providers = template.get("rule-providers", {}) or {}

print(f"Loaded nodes={len(nodes)}, remote groups={len(remote_groups)}, local rules={len(local_rules)}, remote rules={len(remote_rules)}")

# -------- 分类节点 --------
hk_nodes = [p["name"] for p in nodes if "香港" in p.get("name", "")]
jp_nodes = [p["name"] for p in nodes if "日本" in p.get("name", "")]
tw_nodes = [p["name"] for p in nodes if "台湾" in p.get("name", "")]

# -------- 倍率解析与排序 --------
def parse_multiplier_from_name(name: str) -> float:
    if "0.5倍率" in name:
        return 0.5
    if "2.5倍率" in name:
        return 2.5
    if "2倍率" in name:
        return 2.0
    if "3倍率" in name:
        return 3.0
    return 1.0

def sort_nodes(lst):
    return sorted(lst, key=lambda n: (parse_multiplier_from_name(n), n))

hk_nodes = sort_nodes(hk_nodes)
jp_nodes = sort_nodes(jp_nodes)
tw_nodes = sort_nodes(tw_nodes)

# -------- 自定义 select 组 --------
custom_groups = [
    {"name": HK_GROUP, "type": "select", "proxies": hk_nodes},
    {"name": JP_GROUP, "type": "select", "proxies": jp_nodes},
    {"name": TW_GROUP, "type": "select", "proxies": tw_nodes},
]

# -------- 替换远程组内地区节点（自定义节点组在 proxies 内始终最前） --------
def get_proxy_name(item):
    return item["name"] if isinstance(item, dict) else str(item)

def replace_region_proxies(proxy_list):
    front_groups = []
    remaining = []
    for p in proxy_list:
        pname = get_proxy_name(p)
        if "香港" in pname and HK_GROUP not in front_groups:
            front_groups.append(HK_GROUP)
            continue
        if "日本" in pname and JP_GROUP not in front_groups:
            front_groups.append(JP_GROUP)
            continue
        if "台湾" in pname and TW_GROUP not in front_groups:
            front_groups.append(TW_GROUP)
            continue
        if pname not in remaining:
            remaining.append(pname)
    return front_groups + remaining

new_remote_groups = []
for g in remote_groups:
    if isinstance(g, dict) and "proxies" in g:
        g2 = deepcopy(g)
        g2["proxies"] = replace_region_proxies(g.get("proxies", []))
        new_remote_groups.append(g2)
    else:
        new_remote_groups.append(g)

# -------- 合并 proxy-groups（自定义组在最前面）--------
final_groups = deepcopy(custom_groups)
seen = set(cg["name"] for cg in custom_groups)

for g in new_remote_groups:
    name = g.get("name") if isinstance(g, dict) else None
    if name and name in seen:
        continue
    final_groups.append(g)
    if name:
        seen.add(name)

# -------- 合并 rule-providers --------
merged_rule_providers = deepcopy(local_rule_providers)
merged_rule_providers.update(remote_rule_providers)

# -------- 最终配置 --------
final = deepcopy(template) if template else {}
final["proxies"] = nodes
final["proxy-groups"] = final_groups
final["rules"] = local_rules + remote_rules
final["rule-providers"] = merged_rule_providers

# -------- 保存输出 --------
save_yaml(OUTPUT_FILE, final)
print("Saved ->", OUTPUT_FILE)
