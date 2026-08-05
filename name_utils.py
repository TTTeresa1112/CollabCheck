"""作者姓名解析与检索式生成工具。"""
import re
import unicodedata


def normalize_name(name):
    return re.sub(r'[^a-zA-Z\s,.\u00C0-\u017F]', '', name).strip()

def parse_semicolon_name(name):
    """Parses 'First;Last' or 'First,Last' or 'First Last'.
    
    For both ';' and ',': text BEFORE separator = First Name, text AFTER separator = Last Name.
    """
    if ';' in name:
        parts = name.split(';', 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    if ',' in name:
        parts = name.split(',', 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    parts = name.split()
    if len(parts) >= 2:
        return ' '.join(parts[:-1]), parts[-1]
    return '', name


def generate_wos_search_term(given_name, family_name):
    """
    根据给定的名和姓生成 Web of Science (WOS) 检索式变体列表
    """
    if not family_name:
        return []
    
    variants = []
    
    # 处理名部分
    given_tokens = [t for t in given_name.split() if t]
    initials = [t[0] for t in given_tokens if t]
    initials_str = " ".join(initials)
    initials_compact = "".join(initials)
    first_given = given_tokens[0] if given_tokens else ""
    
    # 姓在前名在后
    if given_tokens:
        variants.append(f"AU=({family_name} {given_name})")                # Lane Nancy Catherine
        variants.append(f"AU=({family_name} {initials_str})")             # Lane N C
        variants.append(f"AU=({family_name} {initials_compact})")         # Lane NC
        variants.append(f"AU=({family_name} {first_given})")              # Lane Nancy
        if initials:
            variants.append(f"AU=({family_name} {initials[0]})")          # Lane N
        variants.append(f"AU=({family_name}, {given_name})")              # Lane, Nancy Catherine
    else:
        variants.append(f"AU=({family_name})")
    
    # 名在前姓在后
    if given_tokens:
        variants.append(f"AU=({given_name} {family_name})")               # Nancy Catherine Lane
        variants.append(f"AU=({initials_str} {family_name})")             # N C Lane
        variants.append(f"AU=({initials_compact} {family_name})")         # NC Lane
        variants.append(f"AU=({first_given} {family_name})")              # Nancy Lane
        if initials:
            variants.append(f"AU=({initials[0]} {family_name})")          # N Lane
        variants.append(f"AU=({given_name}, {family_name})")              # Nancy Catherine, Lane
    
    # 去重
    variants = list(dict.fromkeys(variants))
    return variants


def generate_google_scholar_author_search_term(family_name, given_name):
    """
    生成用于Google Scholar的作者检索式变体列表。
    """
    variants = set()
    family_name = family_name.strip()
    given_name = given_name.strip()

    # 1. 使用 author: 操作符
    # 格式：author:"姓 名" 或 author:"姓 首字母"
    if given_name:
        variants.add(f'author:"{given_name} {family_name}"')
    
    # 提取首字母
    name_parts = given_name.split()
    initials = ''.join([part[0].upper() for part in name_parts if part]) if name_parts else ''
    if initials:
        variants.add(f'author:"{initials} {family_name}"')

    # 2. 简单地将全名作为短语搜索（不加author:）
    if given_name:
        variants.add(f'"{given_name} {family_name}"')
    if initials:
        variants.add(f'"{initials} {family_name}"')

    # 3. 考虑将名中的特殊字符（如é）转换为标准英文字母
    if given_name:
        normalized_given_name = unicodedata.normalize('NFD', given_name).encode('ascii', 'ignore').decode('ascii')
        if normalized_given_name != given_name:
            variants.add(f'author:"{normalized_given_name} {family_name}"')
            variants.add(f'"{normalized_given_name} {family_name}"')

    return list(variants)
