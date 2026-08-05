"""各学术数据库的检索实现与结果聚合。

每个 fetch_* 函数接收固定作者与候选作者的名/姓，
返回统一的论文字典列表：
    {"source", "title", "year", "doi", "details"}
"""
import requests
import time
import urllib.parse
import streamlit as st
from thefuzz import fuzz

from config import USER_EMAIL, NCBI_API_KEY, S2_API_KEY, CURRENT_YEAR, START_YEAR, HEADERS


# ---------- PubMed ----------
def get_pmids_for_author(given_name, family_name):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    given_tokens = [t for t in given_name.split() if t]
    initials = [t[0] for t in given_tokens if t]
    
    search_terms = set()
    if given_name:
        search_terms.add(f'"{family_name} {given_name}"[Author]')
        search_terms.add(f'"{given_name} {family_name}"[Author]')
    if initials:
        search_terms.add(f'"{family_name} {"".join(initials)}"[Author]')
        search_terms.add(f'"{family_name} {initials[0]}"[Author]')
        search_terms.add(f'"{initials[0]} {family_name}"[Author]')

    final_search_term = " OR ".join(list(search_terms))
    if not final_search_term:
        final_search_term = f'"{family_name}"[Author]' if family_name else ''
        if not final_search_term: return set()
    
    params = {
        "db": "pubmed", "term": final_search_term,
        "mindate": f"{START_YEAR}/01/01", "maxdate": f"{CURRENT_YEAR}/12/31",
        "datetype": "pdat", "retmode": "json", "retmax": "100",
        "email": USER_EMAIL, "api_key": NCBI_API_KEY
    }
    try:
        response = requests.get(f"{base_url}esearch.fcgi", params=params, headers=HEADERS)
        response.raise_for_status()
        return set(response.json().get("esearchresult", {}).get("idlist", []))
    except:
        return set()

def fetch_pubmed(fixed_given, fixed_family, candidate_given, candidate_family):
    fixed_pmids = get_pmids_for_author(fixed_given, fixed_family)
    if not fixed_pmids: return []
    candidate_pmids = get_pmids_for_author(candidate_given, candidate_family)
    if not candidate_pmids: return []
    
    common_pmids = fixed_pmids.intersection(candidate_pmids)
    if not common_pmids: return []

    results = []
    try:
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        ids = ",".join(common_pmids)
        params = {"db": "pubmed", "id": ids, "retmode": "json", "email": USER_EMAIL, "api_key": NCBI_API_KEY}
        response = requests.get(f"{base_url}esummary.fcgi", params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        for pmid, details in data.get("result", {}).items():
            if pmid == "uids": continue
            title = details.get("title", "No Title")
            pub_year = details.get("pubdate", str(START_YEAR)).split(" ")[0]
            doi = ""
            for an_id in details.get("articleids", []):
                if an_id.get("idtype") == "doi":
                    doi = an_id.get('value')
                    break
            results.append({
                "source": "PubMed",
                "title": title,
                "year": pub_year,
                "doi": doi,
                "details": f"PMID: {pmid}"
            })
    except Exception as e:
        st.write(f"PubMed Error: {e}")
    return results


# ---------- OpenAlex ----------
def get_openalex_author_id(given_name, family_name):
    full_name = f"{given_name} {family_name}".strip()
    if not full_name: return None
    url = "https://api.openalex.org/authors?data-version=2"
    try:
        resp = requests.get(url, params={"filter": f"display_name.search:{full_name}", "mailto": USER_EMAIL}, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if data.get("results"):
            return data["results"][0].get("id").split('/')[-1]
    except:
        pass
    return None

def fetch_openalex(fixed_given, fixed_family, candidate_given, candidate_family):
    fixed_id = get_openalex_author_id(fixed_given, fixed_family)
    candidate_id = get_openalex_author_id(candidate_given, candidate_family)
    if not fixed_id or not candidate_id: return []

    results = []
    try:
        works_url = "https://api.openalex.org/works?data-version=2"
        # Get fixed author works
        params_f = {"filter": f"author.id:{fixed_id},publication_year:>{START_YEAR-1}", "per-page": 100, "mailto": USER_EMAIL}
        resp_f = requests.get(works_url, params=params_f, headers=HEADERS)
        fixed_works = {w["id"]: w for w in resp_f.json().get("results", [])}
        
        if not fixed_works: return []

        # Get candidate works
        params_c = {"filter": f"author.id:{candidate_id},publication_year:>{START_YEAR-1}", "per-page": 100, "mailto": USER_EMAIL}
        resp_c = requests.get(works_url, params=params_c, headers=HEADERS)
        candidate_works = resp_c.json().get("results", [])

        for work in candidate_works:
            if work["id"] in fixed_works:
                doi = work.get("doi", "").replace("https://doi.org/", "")
                results.append({
                    "source": "OpenAlex",
                    "title": work.get("display_name", "No Title"),
                    "year": work.get("publication_year", "N/A"),
                    "doi": doi,
                    "details": f"OpenAlex ID: {work['id']}"
                })
    except Exception as e:
        st.write(f"OpenAlex Error: {e}")
    return results


# ---------- Crossref ----------
def fetch_crossref(fixed_given, fixed_family, candidate_given, candidate_family):
    base_url = "https://api.crossref.org/works"
    author_query = f"{fixed_given} {fixed_family}, {candidate_given} {candidate_family}"
    params = {
        "query.author": author_query,
        "filter": f"from-pub-date:{START_YEAR}-01-01",
        "select": "DOI,title,author,published",
        "rows": 50,
        "mailto": USER_EMAIL
    }
    results = []
    try:
        resp = requests.get(base_url, params=params, headers=HEADERS)
        data = resp.json()
        for item in data.get("message", {}).get("items", []):
            authors = item.get("author", [])
            auth_strs = []
            for a in authors:
                auth_strs.append(f"{a.get('given','')} {a.get('family','')}".strip().lower())
                auth_strs.append(f"{a.get('family','')} {a.get('given','')}".strip().lower())
            
            f_names = [f"{fixed_given} {fixed_family}".lower(), f"{fixed_family} {fixed_given}".lower()]
            c_names = [f"{candidate_given} {candidate_family}".lower(), f"{candidate_family} {candidate_given}".lower()]
            
            best_f = max([fuzz.token_set_ratio(f, a) for f in f_names for a in auth_strs] or [0])
            best_c = max([fuzz.token_set_ratio(c, a) for c in c_names for a in auth_strs] or [0])
            
            if best_f >= 85 and best_c >= 85:
                title = item.get("title", ["No Title"])[0]
                pub = item.get("published-print", item.get("published-online", {}))
                year = pub.get("date-parts", [[START_YEAR]])[0][0] if pub else START_YEAR
                results.append({
                    "source": "Crossref",
                    "title": title,
                    "year": year,
                    "doi": item.get("DOI"),
                    "details": f"Match Score: {best_f}/{best_c}"
                })
    except Exception as e:
        # st.write(f"Crossref Error: {e}") 
        pass
    return results


# ---------- Semantic Scholar ----------
last_s2_time = 0

def s2_safe_request(url, params):
    global last_s2_time
    min_int = 1.1 if S2_API_KEY else 3.1
    elapsed = time.time() - last_s2_time
    if elapsed < min_int: time.sleep(min_int - elapsed)
    last_s2_time = time.time()
    headers = HEADERS.copy()
    if S2_API_KEY: headers["x-api-key"] = S2_API_KEY
    return requests.get(url, params=params, headers=headers)

def fetch_semanticscholar(fixed_given, fixed_family, candidate_given, candidate_family):
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    f_name = f"{fixed_given} {fixed_family}".strip()
    c_name = f"{candidate_given} {candidate_family}".strip()
    params = {
        "query": f'"{f_name}" "{c_name}"',
        "fields": "title,year,externalIds,authors",
        "limit": 70,
        "year": f"{START_YEAR}-"
    }
    results = []
    try:
        resp = s2_safe_request(base_url, params)
        if resp and resp.status_code == 200:
            for paper in resp.json().get('data', []):
                if paper.get('year') and int(paper.get('year')) < START_YEAR: continue
                
                # Check authors fuzzy
                p_auths = [a.get('name','') for a in paper.get('authors', [])]
                best_f = max([fuzz.token_set_ratio(f_name, a) for a in p_auths] or [0])
                best_c = max([fuzz.token_set_ratio(c_name, a) for a in p_auths] or [0])
                
                if best_f >= 72 and best_c >= 72:
                    results.append({
                        "source": "SemanticScholar",
                        "title": paper.get("title"),
                        "year": paper.get("year"),
                        "doi": paper.get("externalIds", {}).get("DOI"),
                        "details": f"Match: {best_f}/{best_c}"
                    })
    except Exception as e:
        st.write(f"SemanticScholar Error: {e}")
        pass
    return results


# ---------- DOAJ ----------
def fetch_doaj(fixed_given, fixed_family, candidate_given, candidate_family):
    base_url = "https://doaj.org/api/v4/search/articles/"
    # Query syntax: (bibjson.author.name:"Name1" AND bibjson.author.name:"Name2")
    f_name = f"{fixed_given} {fixed_family}".strip()
    c_name = f"{candidate_given} {candidate_family}".strip()
    
    query = f'(bibjson.author.name:"{f_name}" AND bibjson.author.name:"{c_name}")'
    encoded_query = urllib.parse.quote(query)
    final_url = f"{base_url}{encoded_query}"
    
    params = {
        "page": 1,
        "pageSize": 50
    }
    
    results = []
    try:
        resp = requests.get(final_url, params=params, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("results", []):
                bib = item.get("bibjson", {})
                
                year = bib.get("year")
                if year and int(year) < START_YEAR: continue
                
                title = bib.get("title", "No Title")
                
                doi = ""
                for id_obj in bib.get("identifier", []):
                    if id_obj.get("type") == "doi":
                        doi = id_obj.get("id")
                        break
                
                results.append({
                    "source": "DOAJ",
                    "title": title,
                    "year": year,
                    "doi": doi,
                    "details": "DOAJ Match" 
                })
    except Exception as e:
        st.write(f"DOAJ Error: {e}")
        pass
    return results


# ---------- 结果聚合 ----------
def merge_results(all_results):
    merged = {}
    for r in all_results:
        doi = r.get('doi')
        # If no DOI, use title/year slug as key
        if not doi:
            key = f"{r['title'][:30]}_{r['year']}"
        else:
            key = doi.lower().strip()
        
        if key in merged:
            merged[key]["sources"].append(r["source"])
           
            new_pair = r.get("matched_pair")
            if new_pair and new_pair not in merged[key].get("matched_pairs", []):
                if "matched_pairs" not in merged[key]:
                    merged[key]["matched_pairs"] = []
                merged[key]["matched_pairs"].append(new_pair)

            merged[key]["sources"] = list(set(merged[key]["sources"])) # dedup sources
            
            # Preserve Match scores if present in the new result but not in existing
            new_details = r.get("details", "")
            if "Match" in new_details:
                current_details = merged[key].get("details", "")
                if "Match" not in current_details:
                    merged[key]["details"] = f"{current_details} | {new_details}" if current_details else new_details
                elif new_details not in current_details: 
                     merged[key]["details"] = f"{current_details} | {new_details}"
        else:
            r["sources"] = [r["source"]]
            r["matched_pairs"] = [r.get("matched_pair")] if r.get("matched_pair") else []
            merged[key] = r
    
    final_list = list(merged.values())
    # Sort by year desc
    final_list.sort(key=lambda x: str(x.get('year', '0')), reverse=True)
    return final_list
