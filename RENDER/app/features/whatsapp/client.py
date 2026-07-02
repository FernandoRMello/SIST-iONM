import json
import urllib.error
import urllib.request
from typing import Any


class MetaWhatsAppClient:
    def create_qr_code(
        self,
        *,
        api_version: str,
        phone_number_id: str,
        access_token: str,
        prefilled_message: str,
    ) -> dict[str, Any]:
        url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/message_qrdls"
        payload = {"prefilled_message": prefilled_message}
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Meta API retornou HTTP {error.code}: {body}") from error

    def send_text(
        self,
        *,
        api_version: str,
        phone_number_id: str,
        access_token: str,
        to_phone: str,
        message: str,
    ) -> dict[str, Any]:
        url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Meta API retornou HTTP {error.code}: {body}") from error
