import httpx
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _call_gemini(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.is_configured():
            return "AI Solution is not configured. Please provide a valid GEMINI_API_KEY in .env."

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(self.endpoint, headers=headers, json=payload)

            if resp.status_code != 200:
                logger.error(f"AI Solution API error ({resp.status_code}): {resp.text}")
                return f"AI generation unavailable (Status {resp.status_code})."

            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    return parts[0].get("text", "")

            return "No response received from AI Solution."

        except Exception as e:
            logger.error(f"Failed to communicate with AI Solution API: {e}")
            return f"Error contacting AI service: {str(e)}"

    def generate_grid_briefing(self, dashboard_data: Dict[str, Any]) -> str:
        system_instruction = (
            "You are an expert Chief Energy Grid Dispatcher and AI Advisor for Renewable Energy Systems. "
            "Provide crisp, professional, and actionable executive summaries of power grid balance, "
            "highlighting risks (deficits, curtailment) and exact battery storage recommendations."
        )

        prompt = f"""
Analyze the following renewable energy grid status and generate an Executive Operator Briefing:

Grid Summary:
- Total Generation Next Hour: {dashboard_data.get('total_generation_mw', 'N/A')} MW
- Total Demand Next Hour: {dashboard_data.get('total_demand_mw', 'N/A')} MW
- Net Grid Balance: {dashboard_data.get('net_balance_mw', 'N/A')} MW ({dashboard_data.get('grid_status', 'N/A')})
- Battery SOC: {dashboard_data.get('battery_soc_pct', 'N/A')}% (Status: {dashboard_data.get('battery_status', 'N/A')})
- Active Alerts Count: {len(dashboard_data.get('active_alerts', []))}

Key Active Alerts:
{dashboard_data.get('active_alerts', [])[:3]}

Provide:
1. Operational Risk Assessment (High/Medium/Low)
2. Immediate 0-6 Hour Dispatch Directives (BESS Charging/Discharging MW)
3. 24-72 Hour Renewable Trend Advisory
"""
        return self._call_gemini(prompt, system_instruction=system_instruction)

    def copilot_chat(self, user_message: str, grid_context: Optional[Dict[str, Any]] = None) -> str:
        system_instruction = (
            "You are the Grid Cast AI Solution Copilot, an intelligent assistant embedded in the "
            "National Renewable Dispatch Desk. You provide technically precise, concise, and safety-critical "
            "guidance on grid balancing, renewable curtailment avoidance, and BESS optimization."
        )

        context_str = ""
        if grid_context:
            context_str = f"\nCurrent Grid Telemetry & Operational State:\n{grid_context}\n"

        full_prompt = f"{context_str}\nOperator Question: {user_message}\nAI Copilot Response:"
        return self._call_gemini(full_prompt, system_instruction=system_instruction)

gemini_service = GeminiService()
