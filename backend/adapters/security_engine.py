"""
Security engine adapter wrapping agent.py, tools.py, and security_actions.py.
"""

from typing import Any, Dict, List
import agent
import auto_scan
import security_actions
import extractor
import search_indexer


class SecurityEngineAdapter:
    @staticmethod
    def analyze_text(text: str, fast_mode: bool = False) -> Dict[str, Any]:
        return agent.analyze_job_offer(text, fast_mode=fast_mode)

    @staticmethod
    def analyze_stored_email(email: Dict[str, Any], fast_mode: bool = False) -> Dict[str, Any]:
        context = auto_scan.build_analysis_context(email)
        return agent.analyze_job_offer(context, fast_mode=fast_mode)

    @staticmethod
    def generate_checklist(email: Dict[str, Any]) -> List[Dict[str, Any]]:
        return security_actions.generate_verification_checklist(email)

    @staticmethod
    def local_quarantine_record(email: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return security_actions.quarantine_email(email, reason=reason)

    @staticmethod
    def get_service_health() -> Dict[str, Any]:
        return {
            "genai_configured": agent.is_azure_openai_configured() or agent.is_github_models_configured(),
            "search_configured": search_indexer.is_azure_configured(),
            "language_configured": extractor.is_azure_language_configured(),
            "ml_classifier_active": True,
        }
