"""
Application sender adapter wrapping job_agent.py.
Ensures preview and draft generation NEVER send emails or mark applications completed.
"""

from typing import Any, Dict, Optional
import job_agent


class ApplicationSenderAdapter:
    @staticmethod
    def extract_job_spec(offer_text: str, email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return job_agent.extract_job_spec(offer_text=offer_text, email_data=email_data)

    @staticmethod
    def evaluate_match(job_spec: Dict[str, Any], candidate_profile: Dict[str, Any]) -> Dict[str, Any]:
        return job_agent.evaluate_candidate_match(job_spec=job_spec, candidate_profile=candidate_profile)

    @staticmethod
    def generate_draft(job_spec: Dict[str, Any], candidate_profile: Dict[str, Any], fast_mode: bool = False) -> Dict[str, str]:
        return job_agent.generate_application_package(job_spec=job_spec, candidate_profile=candidate_profile, fast_mode=fast_mode)

    @staticmethod
    def is_no_reply(email_address: str) -> bool:
        return job_agent.is_no_reply_email(email_address)

    @staticmethod
    def send_approved_application(
        email_id: str,
        job_spec: Dict[str, Any],
        application_package: Dict[str, str],
        candidate_profile: Dict[str, Any],
        email_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Dispatch explicitly approved application package."""
        return job_agent.submit_application(
            email_id=email_id,
            job_spec=job_spec,
            application_package=application_package,
            candidate_profile=candidate_profile,
            email_data=email_data,
        )
