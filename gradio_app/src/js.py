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

load_home_input = """
() => {
const v = document.getElementById('input_example_select')?.value || "";
return [v];
}
"""

focus_refresh = """
<script>
    (() => {
        if (window.__tandem_focus_refresh_bound__) return;
        window.__tandem_focus_refresh_bound__ = true;

        let lastTrigger = 0;
        const throttleMs = 500;
        const triggerRefresh = () => {
        const now = Date.now();
        if (now - lastTrigger < throttleMs) return;
        lastTrigger = now;

        const btn = document.getElementById("focus_refresh_btn");
        if (btn) btn.click();
        };

        document.addEventListener("visibilitychange", () => {
        if (!document.hidden) triggerRefresh();
        });
        window.addEventListener("focus", triggerRefresh);
    })();
</script>
"""

open_hash_details = """
() => {
    function closeSiblings(targetSection) {
        if (!targetSection) return;

        const selector = targetSection.classList.contains("qa-item")
            ? ".qa-item"
            : targetSection.classList.contains("tutorial-item")
                ? ".tutorial-item"
                : "";

        if (!selector) return;

        document.querySelectorAll(selector).forEach((item) => {
            if (item !== targetSection) {
                item.open = false;
            }
        });
    }

    function openHashTarget() {
        const hash = window.location.hash;
        if (!hash) return false;

        const target = document.getElementById(hash.slice(1));
        if (!target) return false;

        const section = target.matches("details") ? target : target.closest("details");
        if (section) {
            closeSiblings(section);
            section.open = true;
        }

        window.requestAnimationFrame(() => {
            target.scrollIntoView({ block: "start" });
        });
        return true;
    }

    function retryOpenHash(attempts = 24, delay = 150) {
        if (openHashTarget() || attempts <= 0) return;
        window.setTimeout(() => retryOpenHash(attempts - 1, delay), delay);
    }

    if (!window.__tandem_hash_details_bound__) {
        window.__tandem_hash_details_bound__ = true;
        window.addEventListener("hashchange", () => retryOpenHash());
        document.addEventListener("click", (event) => {
            const summary = event.target.closest(".qa-item > summary, .tutorial-item > summary");
            if (!summary) return;

            const section = summary.parentElement;
            if (!(section instanceof HTMLDetailsElement)) return;

            window.setTimeout(() => {
                if (section.open) {
                    closeSiblings(section);
                }
            }, 0);
        });
    }

    retryOpenHash();
    return [];
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
