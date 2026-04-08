#!/usr/bin/env python3
"""
從 App 的 toilet.json 生成網頁版用的 toilets.json。
對齊 App 的分組邏輯：按地址分組 → 20m 座標合併 → 提取基底名稱 → 樓層分組。
"""

import json
import re
import math
import os
from collections import defaultdict

INPUT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'Swift', 'Toilet', 'Toilet', 'Models', 'toilet.json')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'assets', 'findtoilet', 'toilets.json')

CAT_MAP = {
    '宗教禮儀場所': '宗教', '商業營業場所': '商業', '交通': '交通',
    '文化育樂活動場所': '文教', '公園': '公園', '觀光地區及風景區': '景點',
    '社福機構、集會場所': '社福', '民眾洽公場所': '政府', '其他': '其他',
    '休閒娛樂場所': '休閒',
}
GRADE_MAP = {'特優級': 1, '優等級': 2, '普通級': 3, '不合格': 4}

# Floor patterns (same as Swift app, but more careful to not match "7-11" etc.)
FLOOR_PATTERNS = [
    r'(?<!\d)(\d+)F(?!\w)',   # "1F", "2F" but not "11F" in "7-11F"
    r'(\d+)樓',
    r'B(\d+)',
    r'地下(\d+)樓',
    r'(\d+)層',
]

# Toilet type suffixes to remove when extracting base name
TYPE_SUFFIXES = [
    '-女廁所', '-男廁所', '-無障礙廁所', '-親子廁所', '-性別友善廁所', '-混合廁所',
    '-女廁', '-男廁', '-無障礙', '-親子', '-性別友善', '-混合',
]


def extract_floor(name):
    """Extract floor info from toilet name. Match App logic."""
    # Basement first
    m = re.search(r'[Bb](\d+)', name)
    if m:
        num = int(m.group(1))
        return f'B{num}', -num
    m = re.search(r'地下(\d+)', name)
    if m:
        num = int(m.group(1))
        return f'B{num}', -num
    # Upper floors - be careful not to match numbers in names like "7-11"
    m = re.search(r'(?<![0-9-])(\d+)F\b', name, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        return f'{num}F', num
    m = re.search(r'(\d+)[樓層]', name)
    if m:
        num = int(m.group(1))
        return f'{num}F', num
    return '1F', 1


def clean_name(name):
    """Remove floor info and type suffix from toilet name to get base location name."""
    clean = name

    # Remove type suffixes (e.g., "-女廁所", "-男廁")
    for suffix in TYPE_SUFFIXES:
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)]
            break

    # Remove floor patterns carefully
    # First remove patterns like "1F-", "B1-", "2樓-" that appear as segments
    clean = re.sub(r'-?[Bb]\d+(?:樓|F)?-?', '', clean)
    clean = re.sub(r'-?地下\d+樓-?', '', clean)
    # For "NF" patterns, only remove if preceded by separator or clearly a floor
    clean = re.sub(r'(?<![0-9])(\d{1,2})F(?![a-zA-Z0-9])', '', clean)
    clean = re.sub(r'(\d{1,2})[樓層]', '', clean)

    # Clean up residual dashes and whitespace
    clean = re.sub(r'-+$', '', clean)
    clean = re.sub(r'^-+', '', clean)
    clean = re.sub(r'--+', '-', clean)
    clean = clean.strip()

    return clean


def find_common_prefix(names):
    """Find longest common prefix among a list of names."""
    if not names:
        return ''
    prefix = names[0]
    for name in names[1:]:
        while not name.startswith(prefix) and prefix:
            prefix = prefix[:-1]
    # Don't end on a partial character boundary for CJK
    return prefix.rstrip('-').strip()


def extract_location_name(toilets):
    """Extract the display name for a group of toilets. Match App logic."""
    if not toilets:
        return ''

    # Clean all names
    cleaned = [clean_name(t.get('name', '')) for t in toilets]
    cleaned = [n for n in cleaned if n]

    if not cleaned:
        return toilets[0].get('name', '')

    # Find common prefix
    prefix = find_common_prefix(cleaned)

    if prefix and len(prefix) >= 2:
        return prefix

    # Fallback: most common cleaned name
    from collections import Counter
    counts = Counter(cleaned)
    return counts.most_common(1)[0][0]


def haversine(lat1, lng1, lat2, lng2):
    """Distance in meters between two points."""
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLng = math.radians(lng2 - lng1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def get_type_flag(t_type):
    flags = {
        '女廁所': 1, '男廁所': 2, '無障礙廁所': 4,
        '親子廁所': 8, '性別友善廁所': 16, '混合廁所': 3
    }
    return flags.get(t_type, 0)


def main():
    with open(INPUT_PATH, 'r') as f:
        data = json.load(f)

    # Filter valid records
    valid = []
    for t in data:
        try:
            lat = float(t.get('latitude', '0'))
            lng = float(t.get('longitude', '0'))
        except (ValueError, TypeError):
            continue
        if 21.5 < lat < 26.5 and 119 < lng < 123:
            t['_lat'] = lat
            t['_lng'] = lng
            valid.append(t)

    print(f'Valid records: {len(valid)}')

    # === Step 1: Group by address (like App) ===
    addr_groups = defaultdict(list)
    for t in valid:
        addr = t.get('address', '').strip()
        if addr:
            addr_groups[addr].append(t)
        else:
            # No address - use coordinate key
            key = f"{round(t['_lat'], 4)},{round(t['_lng'], 4)}"
            addr_groups[key].append(t)

    print(f'Address groups: {len(addr_groups)}')

    # Build location objects from address groups
    locations = []
    for addr, toilets in addr_groups.items():
        avg_lat = sum(t['_lat'] for t in toilets) / len(toilets)
        avg_lng = sum(t['_lng'] for t in toilets) / len(toilets)
        locations.append({
            'toilets': toilets,
            'lat': avg_lat,
            'lng': avg_lng,
            'address': toilets[0].get('address', ''),
        })

    # === Step 2: Merge locations within 20m (like App) ===
    MERGE_THRESHOLD = 20.0
    merged = []
    used = set()

    # Sort by lat for efficient neighbor search
    locations.sort(key=lambda l: l['lat'])

    for i, loc in enumerate(locations):
        if i in used:
            continue
        group = [loc]
        used.add(i)

        for j in range(i + 1, len(locations)):
            if j in used:
                continue
            # Quick lat check (20m ≈ 0.00018 degrees)
            if locations[j]['lat'] - loc['lat'] > 0.0003:
                break
            dist = haversine(loc['lat'], loc['lng'], locations[j]['lat'], locations[j]['lng'])
            if dist <= MERGE_THRESHOLD:
                group.append(locations[j])
                used.add(j)

        # Merge group
        all_toilets = []
        for g in group:
            all_toilets.extend(g['toilets'])
        avg_lat = sum(t['_lat'] for t in all_toilets) / len(all_toilets)
        avg_lng = sum(t['_lng'] for t in all_toilets) / len(all_toilets)

        merged.append({
            'toilets': all_toilets,
            'lat': avg_lat,
            'lng': avg_lng,
            'address': group[0]['address'],
        })

    print(f'After 20m merge: {len(merged)}')

    # === Step 3: Build output with floor grouping ===
    result = []
    multi_floor_count = 0

    for loc in merged:
        toilets = loc['toilets']

        # Extract display name (App logic)
        name = extract_location_name(toilets)

        # Grade (highest)
        grade = 0
        for t in toilets:
            g = GRADE_MAP.get(t.get('grade', ''), 0)
            if g and (not grade or g < grade):  # lower number = better grade
                grade = g

        # Category
        cat = ''
        for t in toilets:
            type2 = t.get('type2', '')
            if type2 and type2 in CAT_MAP:
                cat = CAT_MAP[type2]
                break

        # Diaper
        has_diaper = any(t.get('diaper', '0') == '1' for t in toilets)

        # Floor grouping
        floors_dict = defaultdict(lambda: {'fn': '', 'fo': 0, 'types': set()})
        for t in toilets:
            fn, fo = extract_floor(t.get('name', ''))
            key = f'{fn}-{fo}'
            floors_dict[key]['fn'] = fn
            floors_dict[key]['fo'] = fo
            t_type = t.get('type', '')
            if t_type and t_type not in ['特優級'] and '場所' not in t_type and '風景區' not in t_type:
                floors_dict[key]['types'].add(t_type)

        # Build all_flags and floors list
        all_flags = 0
        floors_list = []
        for floor in floors_dict.values():
            f = 0
            for tt in floor['types']:
                f |= get_type_flag(tt)
            all_flags |= f
            floors_list.append({'fn': floor['fn'], 'fo': floor['fo'], 'f': f})
        if has_diaper:
            all_flags |= 32

        floors_list.sort(key=lambda x: x['fo'])

        # Toilet count
        tc = len(toilets)

        entry = {
            'n': name,
            'a': loc['address'],
            'lt': round(loc['lat'], 6),
            'lg': round(loc['lng'], 6),
            'g': grade,
            'c': cat,
            'f': all_flags,
            'tc': tc,  # toilet count
        }

        if len(floors_list) > 1:
            entry['fl'] = floors_list
            multi_floor_count += 1

        result.append(entry)

    print(f'Total locations: {len(result)}')
    print(f'Multi-floor: {multi_floor_count}')

    # Save
    output = os.path.abspath(OUTPUT_PATH)
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f'Saved: {output} ({size_mb:.2f} MB)')


if __name__ == '__main__':
    main()
