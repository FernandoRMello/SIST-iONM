from typing import Tuple, Optional
from app.features.whatsapp.domain.entities import WhatsAppConversation

class WhatsAppTriageEngine:
    """
    Máquina de estados isolada e testável para automação da triagem inicial (WA-006).
    """
    SECTOR_MAPPING = {
        "1": 1,  # Comercial / Vendas
        "2": 2,  # Suporte Técnico
        "3": 3,  # Financeiro / Faturamento
    }

    @classmethod
    def process_input(cls, conversation: WhatsAppConversation, user_message: str) -> Tuple[str, Optional[int], bool]:
        """
        Retorna: (Mensagem_De_Resposta, Target_Department_Id, Encaminhar_Para_Humano)
        """
        clean_input = user_message.strip()
        current_state = conversation.triage_state

        if current_state == "START":
            conversation.triage_state = "AWAITING_SECTOR"
            welcome_text = (
                "Olá! Seja bem-vindo ao atendimento automatizado SIST-iONM.\n\n"
                "Por favor, digite o número correspondente ao setor desejado:\n"
                "1 - Comercial e Vendas\n"
                "2 - Suporte Técnico\n"
                "3 - Financeiro e Contas\n"
                "4 - Falar diretamente com um atendente"
            )
            return welcome_text, None, False

        elif current_state == "AWAITING_SECTOR":
            if clean_input == "4":
                conversation.triage_state = "HUMAN_HANDOFF"
                return "Entendido. Estou transferindo você agora mesmo para um de nossos atendentes...", None, True
            
            if clean_input in cls.SECTOR_MAPPING:
                dept_id = cls.SECTOR_MAPPING[clean_input]
                conversation.triage_state = "HUMAN_HANDOFF"
                conversation.department_id = dept_id
                
                sectors_names = {"1": "Comercial", "2": "Suporte Técnico", "3": "Financeiro"}
                return f"Perfeito! Sua conversa foi encaminhada para a fila do setor de {sectors_names[clean_input]}. Aguarde um momento.", dept_id, True
            
            return "Opção inválida. Por favor, selecione um número de 1 a 4 conforme o menu anterior.", None, False

        return "", conversation.department_id, True
