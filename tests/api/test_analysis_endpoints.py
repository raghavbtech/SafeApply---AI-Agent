"""Tests for risk analysis endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_adhoc_text_analysis_scam(async_client: AsyncClient, auth_headers: dict):
    scam_text = """
    Congratulations! You have been selected at TechCorp Solutions for Graduate Engineer.
    CTC: INR 8,00,000 per annum.
    Please remit refundable registration fee of Rs 1,499 via UPI within 2 hours to hr.techcorp@gmail.com.
    """
    resp = await async_client.post(
        "/api/v1/analysis/text",
        headers=auth_headers,
        json={"text": scam_text, "fast_mode": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] in ("High", "Critical")
    assert data["risk_score"] >= 65
    assert len(data["identified_red_flags"]) > 0
    assert "tool_outputs" in data
    assert "ml_classifier" in data["tool_outputs"]


@pytest.mark.asyncio
async def test_adhoc_text_analysis_legit(async_client: AsyncClient, auth_headers: dict):
    legit_text = """
    Dear Candidate,
    Following your technical interviews, Microsoft India is pleased to offer you an internship.
    Role: Software Engineering Intern. Stipend: INR 50,000 per month. Location: Hyderabad.
    Microsoft never charges any fee at any stage. Review your offer at https://careers.microsoft.com.
    Email: university-recruiting@microsoft.com
    """
    resp = await async_client.post(
        "/api/v1/analysis/text",
        headers=auth_headers,
        json={"text": legit_text, "fast_mode": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "Low"
    assert data["risk_score"] <= 30
