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

sync_session_example_select = """
(exampleName) => {
    const urlParams = new URLSearchParams(window.location.search || "");
    const urlExampleName = (urlParams.get("example_name") || "").trim();
    const value = ((exampleName || "").trim() || urlExampleName);
    if (!value) return;

    const selectHasOption = (select, optionValue) => {
        return !!select && Array.from(select.options).some((option) => option.value === optionValue);
    };

    const syncSelects = (attempts = 40) => {
        const infSelect = document.getElementById('inf_input_example_select');
        const tfSelect = document.getElementById('tf_input_example_select');
        const matchedInf = selectHasOption(infSelect, value);
        const matchedTf = selectHasOption(tfSelect, value);

        if (matchedInf) infSelect.value = value;
        if (matchedTf) tfSelect.value = value;

        if ((matchedInf || matchedTf) || attempts <= 0) return;
        window.setTimeout(() => syncSelects(attempts - 1), 150);
    };

    syncSelects();
    window.setTimeout(() => syncSelects(), 0);
    window.setTimeout(() => syncSelects(), 200);
    window.setTimeout(() => syncSelects(), 500);
    window.setTimeout(() => syncSelects(), 1000);
    window.setTimeout(() => syncSelects(), 2000);
}
"""

session_example_sync = """
<script>
    (() => {
        if (window.__tandem_example_hash_bound__) return;
        window.__tandem_example_hash_bound__ = true;

        function selectHasOption(select, value) {
            return !!select && Array.from(select.options).some((option) => option.value === value);
        }

        function consumePendingExample(attempts = 30) {
            if (!window.location.pathname.includes('/session/')) return;

            const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : '';
            if (!hash) return;

            const params = new URLSearchParams(hash);
            const exampleName = params.get('example_name') || '';
            const exampleAction = params.get('example_action') || '';
            if (!exampleName || !exampleAction) return;

            const infSelect = document.getElementById('inf_input_example_select');
            const tfSelect = document.getElementById('tf_input_example_select');
            const isInf = selectHasOption(infSelect, exampleName);
            const isTf = selectHasOption(tfSelect, exampleName);
            if (!isInf && !isTf) {
                if (attempts <= 0) return;
                window.setTimeout(() => consumePendingExample(attempts - 1), 150);
                return;
            }

            const infBridge = document.getElementById('inf_input_example');
            const tfBridge = document.getElementById('tf_input_example');
            const actionBtnId = isInf
                ? (exampleAction === 'view_output' ? 'inf_output_view' : 'inf_input_load')
                : (exampleAction === 'view_output' ? 'tf_output_view' : 'tf_input_load');
            const actionBtn = document.getElementById(actionBtnId);
            if ((!infSelect && !tfSelect) || (!infBridge && !tfBridge) || !actionBtn) {
                if (attempts <= 0) return;
                window.setTimeout(() => consumePendingExample(attempts - 1), 150);
                return;
            }

            if (infSelect) infSelect.value = exampleName;
            if (tfSelect) tfSelect.value = exampleName;
            if (infBridge) {
                infBridge.value = exampleName;
                infBridge.dispatchEvent(new Event('input', { bubbles: true }));
            }
            if (tfBridge) {
                tfBridge.value = exampleName;
                tfBridge.dispatchEvent(new Event('input', { bubbles: true }));
            }
            window.setTimeout(() => actionBtn.click(), 0);

            if (window.history?.replaceState) {
                window.history.replaceState(null, '', window.location.pathname + window.location.search);
            }
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => consumePendingExample());
        } else {
            consumePendingExample();
        }
    })();
</script>
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

popup_modal = """
if (!element.dataset.popupModalBound) {
  element.dataset.popupModalBound = "1";

  element.addEventListener("click", (event) => {
    const openNode = event.target.closest("[data-open-modal]");
    if (openNode && element.contains(openNode)) {
      const modal = element.querySelector(`#${openNode.dataset.openModal}`);
      if (modal) {
        modal.classList.add("is-open");
      }
      return;
    }

    const closeNode = event.target.closest("[data-close-modal]");
    if (closeNode && element.contains(closeNode)) {
      const modal = element.querySelector(`#${closeNode.dataset.closeModal}`);
      if (modal) {
        modal.classList.remove("is-open");
      }
      return;
    }

    const overlay = event.target.closest(".popup-overlay");
    if (overlay && event.target === overlay && element.contains(overlay)) {
      overlay.classList.remove("is-open");
    }
  });
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
