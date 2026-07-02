from datetime import datetime, timedelta

from app.features.whatsapp.domain.entities import WhatsAppConversation
from app.features.whatsapp.domain.triage import WhatsAppTriageEngine


def test_conversation_window_is_open_for_less_than_24_hours() -> None:
    open_conversation = WhatsAppConversation(
        id=1,
        contact_id=10,
        last_inbound_at=datetime.utcnow() - timedelta(hours=23),
    )
    closed_conversation = WhatsAppConversation(
        id=2,
        contact_id=10,
        last_inbound_at=datetime.utcnow() - timedelta(hours=25),
    )

    assert open_conversation.is_window_open()
    assert not closed_conversation.is_window_open()


def test_triage_starts_with_sector_menu() -> None:
    conversation = WhatsAppConversation(id=None, contact_id=10)

    reply, department_id, handoff = WhatsAppTriageEngine.process_input(
        conversation,
        "olá",
    )

    assert "1 - Comercial e Vendas" in reply
    assert department_id is None
    assert handoff is False
    assert conversation.triage_state == "AWAITING_SECTOR"


def test_triage_assigns_selected_sector_and_requests_handoff() -> None:
    conversation = WhatsAppConversation(
        id=1,
        contact_id=10,
        triage_state="AWAITING_SECTOR",
    )

    reply, department_id, handoff = WhatsAppTriageEngine.process_input(
        conversation,
        " 3 ",
    )

    assert "Financeiro" in reply
    assert department_id == 3
    assert handoff is True
    assert conversation.department_id == 3
    assert conversation.triage_state == "HUMAN_HANDOFF"


def test_triage_repeats_menu_instruction_for_invalid_sector() -> None:
    conversation = WhatsAppConversation(
        id=1,
        contact_id=10,
        triage_state="AWAITING_SECTOR",
    )

    reply, department_id, handoff = WhatsAppTriageEngine.process_input(
        conversation,
        "financeiro",
    )

    assert "Opção inválida" in reply
    assert department_id is None
    assert handoff is False
    assert conversation.triage_state == "AWAITING_SECTOR"


def test_triage_option_four_requests_direct_handoff() -> None:
    conversation = WhatsAppConversation(
        id=1,
        contact_id=10,
        triage_state="AWAITING_SECTOR",
    )

    reply, department_id, handoff = WhatsAppTriageEngine.process_input(
        conversation,
        "4",
    )

    assert "transferindo" in reply
    assert department_id is None
    assert handoff is True
    assert conversation.triage_state == "HUMAN_HANDOFF"
