from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class WhatsAppContact:
    id: Optional[int]
    phone_number: str
    display_name: str
    client_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class WhatsAppConversation:
    id: Optional[int]
    contact_id: int
    department_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    triage_state: str = "START"
    last_inbound_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    def is_window_open(self) -> bool:
        """Verifica se a janela oficial de atendimento de 24h está aberta (WA-008)."""
        delta = datetime.utcnow() - self.last_inbound_at
        return delta.total_seconds() < 86400
