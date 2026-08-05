"""页面弹窗组件。"""
import streamlit as st


@st.dialog("Detailed Search Results", width="large")
def show_detail_dialog(title, date, result_data):
    """Display detailed search results in a dialog."""
    st.subheader(f"{title}")
    st.caption(f"Search Date: {date}")
    
    papers = result_data.get("papers", [])
    search_terms = result_data.get("search_terms", {})
    inputs = result_data.get("inputs", {})
    
    if inputs:
        with st.expander("Original Input", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Potential COI:**")
                st.code(inputs.get("fixed", "N/A"), language=None)
            with col2:
                st.markdown("**Author(s):**")
                st.code(inputs.get("candidate", "N/A"), language=None)
    
    if search_terms:
        with st.expander("Generated Search Queries", expanded=False):
            for author_name, terms in search_terms.items():
                st.markdown(f"**{author_name}:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("*Web of Science:*")
                    st.code(terms.get("wos", "N/A"), language=None)
                with col2:
                    st.markdown("*Google Scholar:*")
                    st.code(terms.get("gs", "N/A"), language=None)
                st.divider()
    
    st.subheader(f"Found {len(papers)} Potential Collaboration(s)")
    
    if papers:
        for idx, paper in enumerate(papers, 1):
            with st.container():
                st.markdown(f"**{idx}. {paper.get('title', 'No Title')}**")
              

                if "matched_pairs" in paper:
                    pairs_str = " | ".join(paper["matched_pairs"])
                    st.caption(f"**Matched Pair(s):** {pairs_str}")

                
                col1, col2, col3 = st.columns([2, 2, 3])
                with col1:
                    st.caption(f"Year: {paper.get('year', 'N/A')}")
                with col2:
                    sources = paper.get('sources', [paper.get('source', 'Unknown')])
                    st.caption(f"Sources: {', '.join(sources)}")
                with col3:
                    doi = paper.get('doi')
                    details = paper.get('details', '')
                    content = []
                    if doi:
                        content.append(f"[DOI: {doi}](https://doi.org/{doi})")
                    
                    # Ensure Details/Match Scores are shown
                    if details:
                         content.append(details)
                    
                    st.caption(" | ".join(content))
                
                st.divider()
    else:
        st.info("No collaboration papers found in the databases.")
