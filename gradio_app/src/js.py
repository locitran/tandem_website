direct2url_refresh = """
(url) => {
    if (!url) return;
    window.location.assign(url);   // current tab navigates to url
}
"""

direct2url_open = """
(url) => {
    if (!url) return;
    window.open(url, "_blank", "noopener,noreferrer");  // open new tab
}
"""

session_box = """
() => {
    const el = document.getElementById("session-id");
    if (!el) return;

    const text = el.innerText.trim();
    navigator.clipboard.writeText(text);

    // Optional visual feedback
    el.style.background = "#d1fae5";
    setTimeout(() => {el.style.background = "";}, 600);
}
"""