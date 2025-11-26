#!/usr/bin/env python3
# merge.py - generate output.yaml with region groups (HK/JP/TW)
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

# 新节点组名称
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

print(f"Loaded {len(nodes)} nodes, {len(remote_groups)} remote groups")

# -------- 分类节点（只根据名称包含关键字） --------
hk_nodes = [p["name"] for p in nodes if "香港" in p.get("name", "")]
jp_nodes = [p["name"] for p in nodes if "日本" in p.get("name", "")]
tw_nodes = [p["name"] for p in nodes if "台湾" in p.get("name", "")]

print(f"Found: HK={len(hk_nodes)}, JP={len(jp_nodes)}, TW={len(tw_nodes)}")

# -------- 提取倍率并排序逻辑 --------
# 显示形式只有：0.5倍率, 2倍率, 2.5倍率, 3倍率；其余视为 1 倍率
def parse_multiplier_from_name(name: str) -> float:
    # 精确匹配显示形式
    if "0.5倍率" in name:
        return 0.5
    if "2.5倍率" in name:
        return 2.5
    if "2倍率" in name:
        return 2.0
    if "3倍率" in name:
        return 3.0
    # fallback: 匹配像 "0.5" "2.5" "2" "3" + 可能的变体（保守）
    m = re.search(r"(0\.5|2\.5|2|3)", name)
    if m and ("倍率" in name or re.search(r"\b0\.5\b|\b2\.5\b|\b2\b|\b3\b", name)):
        try:
            return float(m.group(1))
        except:
            pass
    # 默认 1 倍率
    return 1.0

def sort_nodes_by_multiplier(lst):
    # sort by (multiplier, then name) ascending
    return sorted(lst, key=lambda n: (parse_multiplier_from_name(n), n))

hk_nodes = sort_nodes_by_multiplier(hk_nodes)
jp_nodes = sort_nodes_by_multiplier(jp_nodes)
tw_nodes = sort_nodes_by_multiplier(tw_nodes)

# -------- 构造三个自定义 select 组（放最前面）--------
custom_groups = [
    {"name": HK_GROUP, "type": "select", "proxies": hk_nodes},
    {"name": JP_GROUP, "type": "select", "proxies": jp_nodes},
    {"name": TW_GROUP, "type": "select", "proxies": tw_nodes},
]

# -------- 替换远程组中地区节点为对应新组 --------
def get_proxy_name(item):
    # item could be string or dict with 'name'
    if isinstance(item, dict):
        return item.get("name") or str(item)
    return str(item)

def replace_region_proxies(proxy_list):
    """
    For a given proxy list, replace any entries that are region nodes with the corresponding
    group name. If multiple region types appear, include multiple group names (dedup, preserve order).
    Non-region proxies are kept as-is (deduped).
    """
    new = []
    for p in proxy_list:
        pname = get_proxy_name(p)
        # region mapping checks
        if "香港" in pname:
            if HK_GROUP not in new:
                new.append(HK_GROUP)
            continue
        if "日本" in pname:
            if JP_GROUP not in new:
                new.append(JP_GROUP)
            continue
        if "台湾" in pname:
            if TW_GROUP not in new:
                new.append(TW_GROUP)
            continue
        # keep other proxies as-is
        if pname not in new:
            new.append(pname)
    return new

new_remote_groups = []
for g in remote_groups:
    if isinstance(g, dict) and "proxies" in g:
        g_copy = deepcopy(g)
        g_copy["proxies"] = replace_region_proxies(g.get("proxies", []))
        new_remote_groups.append(g_copy)
    else:
        new_remote_groups.append(g)

# -------- 合并 proxy-groups：自定义组排最前，避免重复组名 --------
final_groups = []
seen = set()

# add custom first
for cg in custom_groups:
    if cg["name"] not in seen:
        final_groups.append(cg)
        seen.add(cg["name"])

# add modified remote groups
for g in new_remote_groups:
    if isinstance(g, dict):
        name = g.get("name")
        # 如果远程组名与已存在冲突，跳过以避免重复
        if name:
            if name in seen:
                continue
            final_groups.append(g)
            seen.add(name)
        else:
            # unnamed group, append
            final_groups.append(g)
    else:
        # non-dict entry, append
        final_groups.append(g)

# -------- 生成最终配置 --------
final = deepcopy(template) if template else {}
final["proxies"] = nodes
final["proxy-groups"] = final_groups

# 保持 template 中的其它字段（rules, rule-providers 等）原样（已在 final 中）
save_yaml(OUTPUT_FILE, final)
print("Saved ->", OUTPUT_FILE)
