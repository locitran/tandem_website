import html
import os

from .. import js
from ..settings import HTML_DIR


POPUP_MODAL_TEMPLATE = os.path.join(HTML_DIR, "popup_modal.html")


def build_popup_pair(modal_id, trigger_text, title, body_html):
    trigger = '<span class="popup-link" data-open-modal="{}">{}</span>'.format(
        html.escape(modal_id, quote=True),
        html.escape(trigger_text),
    )
    modal = js.build_html_text(
        POPUP_MODAL_TEMPLATE,
        modal_id=html.escape(modal_id, quote=True),
        title=html.escape(title),
        body_html=body_html,
    )
    
    return trigger, modal

def build_event_popup(modal_id, trigger_text, title, event_groups):
    body_parts = []
    for group in event_groups:
        level = str(group.get("level", "")).strip()
        events = group.get("events", []) or []
        for event in events:
            message = str(event.get("message", "")).strip()
            action = str(event.get("action", "") or "").strip()
            savs = (event.get("savs", []) or [])

            if message:
                body_parts.append("<p>> <strong>{}</strong> {}</p>".format(html.escape(level), html.escape(message),))

            if savs:
                sav_items = "".join("<li>{}</li>".format(html.escape(str(sav))) for sav in savs)
                body_parts.append("<ul>{}</ul>".format(sav_items))

            if action:
                body_parts.append("<p><strong>Action:</strong> {}</p>".format(html.escape(action)))

    if not body_parts:
        body_parts.append("<p>No details available.</p>")

    return build_popup_pair(modal_id, trigger_text, title, "".join(body_parts))
