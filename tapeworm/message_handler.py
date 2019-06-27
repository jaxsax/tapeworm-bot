import logging
import json

from html import escape
from datetime import datetime

from .model_link import list_links, from_dict, create_multi
from .services import parse_link_contents

logger = logging.getLogger(__name__)


def _get_text(message):
    return message["text"]


def _get_from(message):
    return message["from"]["id"]


def response_text(src, message):
    return {"chat_id": src["chat"]["id"], "text": message}


def is_command(text):
    return text[0] == "/"


def is_command_of(text, command):
    return is_command(text) and command in text


def find_all_url_types(message):
    if "entities" not in message:
        return []
    return list(
        map(
            lambda x: message["text"][x["offset"] : x["offset"] + x["length"]],
            filter(lambda x: x["type"] == "url", message["entities"]),
        )
    )


def build_link_line(number, link):
    title = f'<a href="{link.link}">{escape(link.title)}</a>'
    user = f"{link.by}"
    return f"{number}. {title} by {user}"


def button(text, cb_data="links:noop"):
    return {"text": text, "callback_data": cb_data}


def reply_keyboard_markup(limit, offset):
    lower_limit = 0 if offset - limit < 0 else offset - limit
    left_button = button(f"<{lower_limit}", f"links:less:{lower_limit}")
    current_page = int(offset / 10) + 1
    return {
        "inline_keyboard": [
            [
                left_button,
                button(str(current_page)),
                button(f"{limit}>", f"links:more:{offset+limit}"),
            ]
        ]
    }


def build_recent_links(limit=10, offset=0):
    links = list_links(limit, offset)
    number = range(offset + 1, offset + len(links) + 1)

    body = map(lambda x: build_link_line(x[0], x[1]), zip(number, links))

    body_full = "\n".join(body)
    return {
        "text": """
<b>Last {0} links added</b>

{1}
        """.format(
            limit, body_full
        ),
        "parse_mode": "HTML",
        "disable_notification": True,
        "disable_web_page_preview": True,
        "reply_markup": json.dumps(reply_keyboard_markup(limit, offset)),
    }


def create_links_from_message(message, url_entities):
    skipped_urls, added_urls = parse_link_contents(url_entities)

    author = _get_from(message)
    today = datetime.utcnow()
    enhance_link = lambda x: from_dict(dict({"by": author, "date": today}, **x))
    added_urls_as_links = list(map(enhance_link, added_urls))
    added_links = list(create_multi(added_urls_as_links))

    return skipped_urls, added_links


def build_add_link_response(message, skipped_urls, added_urls):
    added_titles = list(map(lambda x: x.title.strip(), added_urls))

    skipped_urls_by_nl = "\n".join(map(lambda x: f"{x[0]} (http:{x[1]})", skipped_urls))
    skipped_url_response = (
        f"*Skipped urls*\n{skipped_urls_by_nl}" if skipped_urls else ""
    )

    number = range(1, len(added_urls) + 1)
    link_line = lambda x: f"{x[0]}. [{x[1].title}]({x[1].link})"
    body = map(link_line, zip(number, added_urls))
    body_full = "\n".join(body)

    links_added_response = f"*Links added*\n{body_full}" if added_titles else ""
    return {
        "chat_id": message["chat"]["id"],
        "text": """
{0}

{1}
        """.format(
            skipped_url_response, links_added_response.strip()
        ),
        "parse_mode": "Markdown",
        "disable_notification": True,
        "disable_web_page_preview": True,
    }


def handle_message(message):
    if "text" not in message:
        return None

    text = _get_text(message)

    if is_command_of(text, "links"):
        return dict({"chat_id": message["chat"]["id"]}, **build_recent_links())

    url_entities = find_all_url_types(message)
    if url_entities:
        skipped_urls, added_urls = create_links_from_message(message, url_entities)
        return build_add_link_response(message, skipped_urls, added_urls)
    return None


def handle_callback_query(callback_query):
    if "data" not in callback_query:
        return None

    data = callback_query["data"]
    logger.debug("Parsing callback query %s", callback_query.keys())
    if data.startswith("links:noop"):
        return None
    if data.startswith("links:more") or data.startswith("links:less"):
        args = data.split(":")
        if len(args) < 3:
            return None
        if not args[2].isdigit():
            return None

        offset = int(args[2])
        return dict(
            {
                "chat_id": callback_query["message"]["chat"]["id"],
                "message_id": callback_query["message"]["message_id"],
            },
            **build_recent_links(10, offset),
        )
    return None
