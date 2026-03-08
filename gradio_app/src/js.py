import os 
from .logger import LOGGER

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

load_tf_input = """
() => {
const v = document.getElementById('tf_input_example_select')?.value || "";
return [v];
}
"""

load_inf_input = """
() => {
const v = document.getElementById('inf_input_example_select')?.value || "";
return [v];
}
"""


def build_html_text(filepath, **keys) -> str:
    if not os.path.isfile(filepath):
        LOGGER.warn(f"{filepath} is not a file")
        return ""
    
    with open(filepath, "r", encoding="utf-8") as f:
        tpl = f.read()
    if not keys:
        return tpl
    return tpl.format(**keys)
