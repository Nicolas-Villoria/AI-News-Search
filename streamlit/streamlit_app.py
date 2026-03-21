"""
streamlit_app.py — Streamlit frontend for AI News Search.

A thin HTTP client that talks to the FastAPI backend.
No ML models are loaded here — all heavy lifting happens in the API.

Run with:
    streamlit run streamlit_app.py
"""

import streamlit as st
from helpers import api_get, api_post, format_time_ago

# ── Page config ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI News Search",
    page_icon="🔍",
    layout="wide",
)

st.markdown("""
<style>
    .score-bar {
        height: 8px;
        border-radius: 4px;
        margin-bottom: 2px;
    }
    .result-card {
        padding: 1.2rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        margin-bottom: 1rem;
        background: #fafafa;
    }
    [data-theme="dark"] .result-card {
        background: #1e1e1e;
        border-color: #333;
    }
    .metric-card {
        text-align: center;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Tabs ────────────────────────────────────────────────────────────

tab_search, tab_health, tab_how_it_works = st.tabs(["Search", "Pipeline Health", "How it works"])

# ── How it works Tab ──────────────────────────────────────────────

with tab_how_it_works:
    st.header("How it works")
    st.caption("This is a semantic search over AI news, powered by FAISS + DistilBART")

    st.divider()

    health = api_get("/health")
    if health:
        st.metric("Articles Indexed", health["articles_count"])
        col1, col2 = st.columns(2)
        col1.metric("Embedding", "Loaded" if health["models_loaded"]["embedding"] else "No")
        col2.metric("Summarizer", "Loaded" if health["models_loaded"]["summarizer"] else "No")

        if health.get("pipeline_stats"):
            ps = health["pipeline_stats"]
            st.caption(f"Last pipeline: {ps.get('status', 'N/A')} in {ps.get('total_seconds', '?')}s")

    st.divider()
    st.markdown(
        "**How it works**\n\n"
        "1. Crawls 24 RSS feeds for AI news\n"
        "2. Filters with keyword scoring\n"
        "3. Embeds with MiniLM-L6-v2\n"
        "4. Ranks by semantic + freshness + keywords\n"
        "5. Summarizes on demand with DistilBART"
    )

# ── Search Tab ──────────────────────────────────────────────────────

with tab_search:
    st.header("Search AI News")

    col_input, col_k = st.columns([4, 1])
    with col_input:
        query = st.text_input(
            "Enter your search query",
            placeholder="e.g. large language model agents, AI safety regulation, vision transformers ...",
            label_visibility="collapsed",
        )
    with col_k:
        top_k = st.selectbox("Results", [5, 10, 15, 20, 30], index=1, label_visibility="collapsed")

    example_queries = ["Large language models", "AI safety and regulation", "Computer vision breakthroughs", "AI agents and tool use"]
    cols = st.columns(len(example_queries))
    for col, eq in zip(cols, example_queries):
        if col.button(eq, use_container_width=True):
            query = eq

    # Persistent summary cache across Streamlit re-runs
    if "summaries" not in st.session_state:
        st.session_state.summaries = {}

    if query:
        with st.spinner("Searching..."):
            response = api_post("/search", {"query": query, "top_k": top_k})

        if response and response.get("results"):
            st.caption(f"Found **{response['total_results']}** results for *\"{response['query']}\"*")

            for i, article in enumerate(response["results"]):
                relevance = article.get("relevance_score", 0)
                semantic = article.get("semantic_score", 0)
                time_sc = article.get("time_score", 0)
                keyword = article.get("keyword_score", 0)
                article_key = article.get("link", f"article_{i}")

                with st.container():
                    st.markdown(f"---")

                    # Title row
                    title_col, score_col = st.columns([5, 1])
                    with title_col:
                        st.markdown(f"### [{article.get('title', 'Untitled')}]({article.get('link', '#')})")
                        source = article.get("source", "Unknown")
                        time_ago = format_time_ago(article.get("published"))
                        st.caption(f"**{source}**  ·  {time_ago}")
                    with score_col:
                        st.metric("Score", f"{relevance:.3f}", label_visibility="collapsed")

                    # Score breakdown
                    s1, s2, s3 = st.columns(3)
                    s1.progress(min(semantic, 1.0), text=f"Semantic: {semantic:.3f}")
                    s2.progress(min(time_sc, 1.0), text=f"Freshness: {time_sc:.3f}")
                    s3.progress(min(keyword, 1.0), text=f"Keyword: {keyword:.3f}")

                    # Text preview
                    text = article.get("text", "")
                    preview = text[:300] + "..." if len(text) > 300 else text
                    st.markdown(f"<small>{preview}</small>", unsafe_allow_html=True)

                    # Show cached summary if we already have one
                    if article_key in st.session_state.summaries:
                        st.info(f"**Summary:** {st.session_state.summaries[article_key]}")

                    # Summarize button
                    if st.button("Summarize", key=f"sum_{i}", disabled=(article_key in st.session_state.summaries)):
                        if text and len(text.strip()) >= 100:
                            with st.spinner("Generating summary..."):
                                summary_resp = api_post("/summarize", {"text": text}, timeout=60)
                            if summary_resp and summary_resp.get("summary"):
                                st.session_state.summaries[article_key] = summary_resp["summary"]
                                st.rerun()
                        else:
                            st.warning("Article text too short to summarize.")

        elif response:
            st.info("No results found. Try a different query.")


# ── Pipeline Health Tab ─────────────────────────────────────────────

with tab_health:
    st.header("Pipeline Health")

    health_data = api_get("/health")

    if not health_data:
        st.warning("Could not connect to API.")
    else:
        ps = health_data.get("pipeline_stats")

        if not ps:
            st.info("No pipeline has been run yet. Click below to start one.")
        else:
            # Top-level metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Articles Crawled", ps["crawl"]["articles"])
            m2.metric("After Filter", ps["filter"]["output"])
            m3.metric("Filter Pass Rate", f"{ps['filter']['pass_rate']:.0%}")
            m4.metric("Total Time", f"{ps['total_seconds']}s")

            st.divider()

            # Timing breakdown
            st.subheader("Stage Timing")
            timing_cols = st.columns(3)
            timing_cols[0].metric("Crawl", f"{ps['crawl']['seconds']}s")
            timing_cols[1].metric("Filter", f"{ps['filter']['seconds']}s")
            timing_cols[2].metric("Embed + Index", f"{ps['index']['seconds']}s")

            st.divider()

            # Per-feed stats
            st.subheader("Feed Health")

            feed_stats = ps.get("feed_stats", [])
            if feed_stats:
                success_count = sum(1 for f in feed_stats if f["status"] == "success")
                fail_count = len(feed_stats) - success_count

                fc1, fc2 = st.columns(2)
                fc1.metric("Feeds Succeeded", f"{success_count}/{len(feed_stats)}")
                fc2.metric("Feeds Failed", fail_count)

                # Feed table
                feed_table = []
                for f in sorted(feed_stats, key=lambda x: x["article_count"], reverse=True):
                    feed_table.append({
                        "Source": f["source"],
                        "Articles": f["article_count"],
                        "Status": "✅" if f["status"] == "success" else "❌",
                        "Time (s)": f["elapsed_seconds"],
                        "Error": f.get("error") or "",
                    })

                st.dataframe(feed_table, use_container_width=True, hide_index=True)

            st.divider()

            # Last run info
            st.subheader("Run Info")
            r1, r2, r3 = st.columns(3)
            r1.markdown(f"**Started:** {ps.get('started_at', 'N/A')}")
            r2.markdown(f"**Finished:** {ps.get('finished_at', 'N/A')}")
            r3.markdown(f"**Status:** {ps.get('status', 'N/A')}")

        # Re-run button
        st.divider()
        if health_data.get("pipeline_running"):
            st.warning("Pipeline is currently running...")
        else:
            if st.button("Re-run Pipeline", type="primary"):
                with st.spinner("Pipeline started... this may take 1-2 minutes."):
                    result = api_post("/pipeline/run", {}, timeout=5)
                    if result:
                        st.success(result.get("message", "Pipeline started"))
                        st.caption("Refresh the page in a couple of minutes to see updated stats.")
