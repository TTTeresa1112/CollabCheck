"""搜索编排：串起姓名解析、检索式生成、数据库查询与结果聚合。"""
import datetime
import streamlit as st

from name_utils import (
    parse_semicolon_name,
    generate_wos_search_term,
    generate_google_scholar_author_search_term,
)
from sources import (
    fetch_pubmed,
    fetch_openalex,
    fetch_crossref,
    fetch_semanticscholar,
    fetch_doaj,
    merge_results,
)
from search_lock import get_search_lock_safe
from ui import show_detail_dialog

# 全局搜索锁（跨会话共享）
search_lock = get_search_lock_safe()


def run_search(fixed_input, candidate_input):
    """执行 COI 检索：查询多个学术数据库并聚合结果。"""
    if not fixed_input.strip() or not candidate_input.strip():
        st.error("⚠️ 请同时填写 Potential COI 与 Author(s) 后再开始搜索。")
        return

    if not search_lock.try_acquire():
        _, err_msg = search_lock.get_status()
        st.error(err_msg if err_msg else "⚠️ 系统繁忙，请稍后再试。")
        return

    try:
        st.session_state.is_searching = True

        job_title = "CollabCheck Results"

        fixed_authors = [n.strip() for n in fixed_input.split('\n') if n.strip()]
        candidate_authors = [n.strip() for n in candidate_input.split('\n') if n.strip()]

        st.info(f"正在检查 {len(fixed_authors)} 位潜在 COI 与 {len(candidate_authors)} 位作者...")

        all_raw_results = []
        generated_queries = {}

        candidate_wos_parts = []
        candidate_gs_parts = []

        for c_name in candidate_authors:
            c_g, c_f = parse_semicolon_name(c_name)
            if not c_f:
                continue

            c_wos_vars = generate_wos_search_term(c_g, c_f)
            if c_wos_vars:
                candidate_wos_parts.append("(" + " OR ".join(c_wos_vars) + ")")

            c_gs_vars = generate_google_scholar_author_search_term(c_f, c_g)
            if c_gs_vars:
                candidate_gs_parts.append("(" + " OR ".join(c_gs_vars) + ")")

        all_candidates_wos_str = " OR ".join(candidate_wos_parts)
        all_candidates_gs_str = " OR ".join(candidate_gs_parts)

        for f_name in fixed_authors:
            f_g, f_f = parse_semicolon_name(f_name)
            if not f_f:
                continue

            f_wos_vars = generate_wos_search_term(f_g, f_f)
            if f_wos_vars and all_candidates_wos_str:
                fixed_wos_part = " OR ".join(f_wos_vars)
                final_wos = f"({fixed_wos_part}) AND ({all_candidates_wos_str})"
            else:
                final_wos = "Could not generate query (missing terms)"

            f_gs_vars = generate_google_scholar_author_search_term(f_f, f_g)
            if f_gs_vars and all_candidates_gs_str:
                fixed_gs_part = " OR ".join(f_gs_vars)
                final_gs = f"({fixed_gs_part}) AND ({all_candidates_gs_str})"
            else:
                final_gs = "Could not generate query (missing terms)"

            display_name = f"{f_f} {f_g}"
            generated_queries[display_name] = {
                "wos": final_wos,
                "gs": final_gs
            }

        with st.status("Checking potential conflicts...", expanded=True) as status:
            processed = 0
            total = len(fixed_authors) * len(candidate_authors)

            for f_name in fixed_authors:
                f_given, f_family = parse_semicolon_name(f_name)
                for c_name in candidate_authors:
                    c_given, c_family = parse_semicolon_name(c_name)

                    # Update status label with current pair
                    status.update(label=f"Checking ({processed+1}/{total}): {f_family} vs {c_family}", state="running")
                    st.write(f"Searching: **{f_family}, {f_given}** & **{c_family}, {c_given}**...")

                    res_pm = fetch_pubmed(f_given, f_family, c_given, c_family)
                    res_oa = fetch_openalex(f_given, f_family, c_given, c_family)
                    res_cr = fetch_crossref(f_given, f_family, c_given, c_family)
                    res_s2 = fetch_semanticscholar(f_given, f_family, c_given, c_family)
                    res_doaj = fetch_doaj(f_given, f_family, c_given, c_family)

                    current_pair_name = f"COI: {f_family}, {f_given} with Author: {c_family}, {c_given}"
                    combined_res = res_pm + res_oa + res_cr + res_s2 + res_doaj
                    for r in combined_res:
                        r["matched_pair"] = current_pair_name

                    all_raw_results.extend(combined_res)

                    processed += 1

            status.update(label="Search Completed!", state="complete", expanded=False)
        unique_results = merge_results(all_raw_results)

        input_data = {
            "fixed": fixed_input,
            "candidate": candidate_input
        }

        st.success("Search completed successfully!")

        complex_result = {
            "papers": unique_results,
            "search_terms": generated_queries,
            "inputs": input_data
        }

        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.history_queue.append({
            "timestamp": timestamp_str,
            "title": job_title,
            "data": complex_result
        })

        show_detail_dialog(job_title, timestamp_str, complex_result)

    except Exception as e:
        st.error(f"An error occurred during search: {e}")
    finally:
        # Always release lock
        search_lock.release()
        st.session_state.is_searching = False
