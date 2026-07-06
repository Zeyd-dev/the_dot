"""
styles.py — Shared CSS snippets for The Dot Resource Matcher.

Usage in any Streamlit page:
    import styles
    st.markdown(styles.HIDE_SIDEBAR, unsafe_allow_html=True)
    st.markdown(styles.FONTS_AND_RESET, unsafe_allow_html=True)
"""

# Hides the Streamlit sidebar and multipage nav on every page.
# The <script> block injects the rule into <head> immediately (before React
# renders) so the sidebar never flashes even without hideSidebarNav in config.toml.
HIDE_SIDEBAR = """
<style>
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarNav"],
section[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavSeparator"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    width: 0 !important;
    pointer-events: none !important;
}
</style>
<script>
(function(){
    var s=document.createElement('style');
    s.textContent='[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stSidebarNav"],section[data-testid="stSidebarNav"]{display:none!important;visibility:hidden!important;opacity:0!important;width:0!important;}';
    document.head.appendChild(s);
})();
</script>
"""

# DM Sans / DM Mono Google Fonts import + root resets shared by all pages.
FONTS_AND_RESET = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #0a0f1a; }
.block-container { padding: 0 !important; max-width: 100% !important; }
</style>
"""
