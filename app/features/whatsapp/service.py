import json
from dataclasses import dataclass
from typing import Any

from app.features.whatsapp.repository import WhatsAppSettingsRepository

SAFE_CONFIRMATION_REPLY = (
    "Encontrei sua solicitação, mas preciso confirmar seu cadastro antes de "
    "mostrar informações financeiras ou pedidos. Vou encaminhar para um atendente."
)
HUMAN_HANDOFF_REPLY = "Recebi sua mensagem e vou encaminhar para um atendente."
HUMAN_HANDOFF_KEYWORDS = ("atendente", "humano", "pessoa", "suporte")


@dataclass(frozen=True)
class InboundWhatsAppMessage:
    provider_message_id: str
    from_phone: str
    profile_name: str
    content: str
    message_type: str
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class WhatsAppInboundResult:
    created: bool
    auto_reply: str
    conversation_id: int | None = None
    chat_room_id: int | None = None


def normalize_inbound_payload(payload: dict[str, Any]) -> list[InboundWhatsAppMessage]:
    messages: list[InboundWhatsAppMessage] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            contacts_by_phone = {
                str(contact.get("wa_id") or ""): contact
                for contact in value.get("contacts") or []
            }
            for raw_message in value.get("messages") or []:
                phone = str(raw_message.get("from") or "")
                message_type = str(raw_message.get("type") or "")
                if message_type == "text":
                    content = str((raw_message.get("text") or {}).get("body") or "")
                else:
                    content = f"[{message_type or 'mensagem'}]"
                contact = contacts_by_phone.get(phone) or {}
                profile_name = str((contact.get("profile") or {}).get("name") or phone)
                provider_id = str(raw_message.get("id") or "")
                if not provider_id or not phone:
                    continue
                messages.append(
                    InboundWhatsAppMessage(
                        provider_message_id=provider_id,
                        from_phone=phone,
                        profile_name=profile_name,
                        content=content,
                        message_type=message_type,
                        raw_payload=raw_message,
                    ),
                )
    return messages


def _next_triage_reply(repository: WhatsAppSettingsRepository, contact_id: int) -> str:
    state = repository.get_triage_state(contact_id)
    if not state:
        repository.set_triage_state(contact_id, "ask_name")
        return "Olá! Sou o assistente da SIST-iONM. Para começar, qual é o seu nome?"
    if state == "ask_name":
        repository.set_triage_state(contact_id, "ask_origin")
        return "Obrigado. Você fala de qual empresa/cidade?"
    if state == "ask_origin":
        repository.set_triage_state(contact_id, "choose_department")
        return "Como posso te ajudar? 1 Comercial, 2 Financeiro, 3 Pedidos, 4 Suporte."
    return "Recebi sua mensagem e vou encaminhar para um atendente."


def _content_matches_keywords(content: str, trigger_value: str) -> bool:
    normalized_content = content.lower()
    keywords = [
        keyword.strip().lower()
        for keyword in trigger_value.split(",")
        if keyword.strip()
    ]
    return any(keyword in normalized_content for keyword in keywords)


def resolve_automation_reply(
    repository: WhatsAppSettingsRepository,
    contact: dict[str, Any],
    content: str,
) -> str:
    normalized_content = content.lower()
    if any(keyword in normalized_content for keyword in HUMAN_HANDOFF_KEYWORDS):
        return HUMAN_HANDOFF_REPLY

    for rule in repository.automation_rules():
        if rule.get("is_active") == "Não":
            continue
        if rule.get("trigger_type") != "keyword":
            continue
        if not _content_matches_keywords(content, str(rule.get("trigger_value") or "")):
            continue

        response_type = str(rule.get("response_type") or "")
        if response_type == "human_handoff":
            return HUMAN_HANDOFF_REPLY
        if response_type in {"safe_finance_lookup", "safe_order_lookup"}:
            if not contact.get("client_id"):
                return SAFE_CONFIRMATION_REPLY
        if response_type == "static_reply" and rule.get("response_text"):
            return str(rule["response_text"])
        if rule.get("response_text"):
            return str(rule["response_text"])

    return ""


def handle_inbound_message(
    repository: WhatsAppSettingsRepository,
    message: InboundWhatsAppMessage,
) -> WhatsAppInboundResult:
    if repository.find_message(message.provider_message_id):
        return WhatsAppInboundResult(created=False, auto_reply="")
    contact = repository.upsert_contact(message.from_phone, message.profile_name)
    conversation = repository.ensure_conversation(contact)
    created = repository.insert_inbound_message(
        conversation_id=int(conversation["id"]),
        provider_message_id=message.provider_message_id,
        sender_label=message.profile_name or message.from_phone,
        content=message.content,
        message_type=message.message_type,
        raw_payload_json=json.dumps(message.raw_payload, ensure_ascii=False),
    )
    if created:
        repository.mirror_to_chat(
            int(conversation["chat_room_id"]),
            message.profile_name or message.from_phone,
            message.content,
        )
    automation_reply = (
        resolve_automation_reply(repository, contact, message.content) if created else ""
    )
    return WhatsAppInboundResult(
        created=created,
        auto_reply=automation_reply
        or (_next_triage_reply(repository, int(contact["id"])) if created else ""),
        conversation_id=int(conversation["id"]),
        chat_room_id=int(conversation["chat_room_id"]),
    )
