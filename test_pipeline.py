"""
SafeApply - Test Suite & Evaluation Benchmark

Runs 12 benchmark cases:
- 3 Clearly Fake offers (Target: High Risk)
- 3 Clearly Legitimate offers (Target: Low Risk - false-positive check)
- 3 Ambiguous offers (Target: Medium Risk)
- 3 Edge cases (Target: graceful Low/Medium handling)

Also runs:
- Grounding / hallucination regression tests
- RAG category-coverage test

Measures latency and prints an evaluation summary suitable for README reporting.
"""

import time

from agent import analyze_job_offer
from extractor import extract_offer_details
from tools import check_red_flags_rag, detect_fraud_ml
from ml_classifier import predict_job_offer


TEST_CASES = [
    # ----------------------------------------------------
    # Category 1: Clearly Fake Offers (Expected: High Risk)
    # ----------------------------------------------------
    {
        "id": "FAKE_01",
        "category": "Clearly Fake",
        "expected": "High",
        "description": "TechCorp upfront registration fee with urgency and Gmail domain",
        "text": """
        Congratulations! You are selected as Software Engineer Intern at TechCorp Solutions.
        CTC: INR 8,00,000 per annum.
        To confirm your placement slot, you must pay a refundable registration charge of Rs 1,499 via UPI within 2 hours.
        Submit payment screenshot to hr.techcorp@gmail.com immediately or your offer will be revoked.
        """,
    },
    {
        "id": "FAKE_02",
        "category": "Clearly Fake",
        "expected": "High",
        "description": "Exorbitant salary for simple work-from-home data entry with Telegram contact",
        "text": """
        URGENT HIRING: Work from Home 2 hours daily doing copy paste data entry.
        Guaranteed payout: INR 75,000 per month plus daily bonus. No interview, no experience needed.
        Direct selection letter. Contact hiring director immediately on Telegram @AmazonJobsIndiaDesk.
        """,
    },
    {
        "id": "FAKE_03",
        "category": "Clearly Fake",
        "expected": "High",
        "description": "MacBook dispatch courier insurance fee with identity-document request",
        "text": """
        Welcome to CloudScale Systems India!
        We are shipping your welcome kit including Apple MacBook Pro M3.
        Please transfer refundable transit clearance insurance charge of Rs 5,000 to our courier account.
        Also send photos of your front and back Aadhaar card for IT asset security.
        Contact: logistics-team@cloudscale-hiring-portal.com
        """,
    },

    # ----------------------------------------------------
    # Category 2: Clearly Legitimate Offers
    # Expected: Low Risk
    # ----------------------------------------------------
    {
        "id": "LEGIT_01",
        "category": "Clearly Legitimate",
        "expected": "Low",
        "description": "Standard Microsoft internship offer using official corporate domain",
        "text": """
        Dear Candidate,
        Following your technical interviews with our engineering team, we are pleased to offer you an internship at Microsoft India (R&D) Pvt. Ltd.
        Role: Software Engineering Intern
        Stipend: INR 50,000 per month
        Location: Hyderabad Campus
        No fees or security deposits are required at any stage of our recruitment process.
        Please review your formal offer letter on the Microsoft Careers Portal: https://careers.microsoft.com.
        Sincerely,
        University Recruiting Team, Microsoft India
        Email: university-recruiting@microsoft.com
        """,
    },
    {
        "id": "LEGIT_02",
        "category": "Clearly Legitimate",
        "expected": "Low",
        "description": "Standard Infosys campus placement letter using official portal/domain",
        "text": """
        Dear Candidate,
        Congratulations on successfully clearing the InfyTQ certification and technical interview rounds!
        Infosys Limited is pleased to offer you the role of Systems Engineer.
        Compensation: INR 3,60,000 per annum (3.6 LPA).
        Joining location will be Mysore Development Centre for initial training.
        Infosys never charges any fee or asks for money deposit from job seekers at any stage of recruitment.
        Kindly accept through our candidate portal at https://career.infosys.com.
        Talent Acquisition Group, Infosys Limited
        Email: campus_recruitment@infosys.com
        """,
    },
    {
        "id": "LEGIT_03",
        "category": "Clearly Legitimate",
        "expected": "Low",
        "description": "Standard Razorpay screening invite using corporate email",
        "text": """
        Hi Raghav,
        Thanks for applying to the Backend Developer position at Razorpay.
        We reviewed your GitHub projects and would love to invite you for a 45-minute technical discussion with our engineering lead next Tuesday.
        There is no fee associated with our application process.
        Let us know your available time slots.
        Best regards,
        Aditi Sharma | Talent Acquisition, Razorpay
        Email: aditi.sharma@razorpay.com
        """,
    },

    # ----------------------------------------------------
    # Category 3: Ambiguous / Borderline Offers
    # Expected: Medium Risk
    # ----------------------------------------------------
    {
        "id": "AMBIG_01",
        "category": "Ambiguous",
        "expected": "Medium",
        "description": "Generic Gmail recruiter without fee request",
        "text": """
        Hi,
        I found your profile on LinkedIn for our boutique digital marketing agency, Apex Media.
        We have an open junior web designer role. Salary is around INR 25,000 per month depending on your portfolio.
        Please reply with your resume and sample links if interested.
        Regards,
        Karan (karan.apexmedia@gmail.com)
        """,
    },
    {
        "id": "AMBIG_02",
        "category": "Ambiguous",
        "expected": "Medium",
        "description": "Generic Gmail recruiter with weak screening and a short acceptance deadline",
        "text": """
        Dear Applicant,
        We have an immediate vacancy for Junior QA Tester at NovaTech Labs.
        CTC: 4.5 LPA.
        Your profile has been shortlisted without an initial screening round.
        Please confirm your interest within 2 hours today so that your slot is not released to another candidate.
        Recruitment Desk
        Email: novatech.recruitment@gmail.com
        """,
    },
    {
        "id": "AMBIG_03",
        "category": "Ambiguous",
        "expected": "Medium",
        "description": "Vague freelance project with public Yahoo contact",
        "text": """
        Looking for college students to assist with research transcription.
        Payment: ₹15,000 per completed module.
        Work at your own pace from home. Contact the project coordinator for assignment guidelines.
        Email: research.coordinator77@yahoo.com
        """,
    },

    # ----------------------------------------------------
    # Category 4: Edge Cases / Resilience
    # ----------------------------------------------------
    {
        "id": "EDGE_01",
        "category": "Edge Case",
        "expected": "Low",
        "description": "Short job notice with no scam signal",
        "text": "Looking for Python intern in Bengaluru. Send resume to jobs@startup.io.",
    },
    {
        "id": "EDGE_02",
        "category": "Edge Case",
        "expected": "Low",
        "description": "Empty input string",
        "text": "",
    },
    {
        "id": "EDGE_03",
        "category": "Edge Case",
        "expected": "Low",
        "description": "Standard campus drive notification without money or sensitive-data request",
        "text": """
        Campus Placement Notice:
        Orion Technologies will conduct an aptitude test and technical interview
        on Friday at 10:00 AM in Block C. Eligible students may register through
        the university placement portal before Thursday evening.
        """,
    },
]


GROUNDING_CASES = [
    {
        "id": "GROUND_01",
        "description": "Bank and Aadhaar request must not hallucinate PIN/OTP/password/card details",
        "text": """
        Congratulations. You have been shortlisted for a software role.
        Please provide your bank account details and Aadhaar card copy.
        Contact: recruitment.team@gmail.com
        """,
        "forbidden_terms": [
            "upi pin",
            "otp",
            "internet banking password",
            "net banking password",
            "debit card",
            "credit card",
        ],
    },
    {
        "id": "GROUND_02",
        "description": "UPI payment request must not be transformed into UPI PIN request",
        "text": """
        Congratulations on your selection.
        To reserve your slot, pay a refundable registration fee of INR 999 via UPI within 2 hours.
        Send the payment screenshot to hiring.team@gmail.com.
        """,
        "expected": "High",
        "forbidden_terms": [
            "upi pin",
            "otp",
            "banking password",
            "debit card",
        ],
    },
    {
        "id": "GROUND_03",
        "description": "Protective anti-fee statement must not be treated as an affirmative fee demand",
        "text": """
        Following your interview, Microsoft India would like to invite you to the next technical round.
        Microsoft never charges applicants any recruitment fee and does not request security deposits.
        Please use the careers portal for all further communication.
        Email: university-recruiting@microsoft.com
        """,
        "expected": "Low",
    },
]


def _benchmark_case_passes(case: dict, actual: str) -> bool:
    """
    Strict grading for declared benchmark targets.

    Clearly Fake, Clearly Legitimate, and Ambiguous cases must match their
    declared expected verdict exactly. Edge cases may resolve to Low or Medium
    because incomplete text can reasonably trigger cautious handling.
    """
    if case["category"] == "Edge Case":
        return actual in ["Low", "Medium"]

    return actual == case["expected"]


def run_benchmark():
    print("=" * 96)
    print("SAFEAPPLY TEST SUITE & RESPONSIBLE AI EVALUATION BENCHMARK")
    print("=" * 96)

    results = []
    total_time = 0.0
    passed_verdicts = 0

    print(
        f"{'ID':<10} {'Category':<20} {'Expected':<10} {'Actual':<10} "
        f"{'Score':<8} {'Latency':<12} {'Status'}"
    )
    print("-" * 96)

    for case in TEST_CASES:
        start_t = time.time()
        res = analyze_job_offer(case["text"])
        elapsed = time.time() - start_t
        total_time += elapsed

        actual = res["risk_level"]
        score = res["risk_score"]

        is_pass = _benchmark_case_passes(case, actual)

        if is_pass:
            passed_verdicts += 1
            status = "PASS [OK]"
        else:
            status = "FAIL [X]"

        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "description": case["description"],
                "expected": case["expected"],
                "actual": actual,
                "score": score,
                "latency": elapsed,
                "status": status,
                "flags": res.get("identified_red_flags", []),
                "execution_mode": res.get("execution_mode", "Unknown"),
            }
        )

        print(
            f"{case['id']:<10} {case['category']:<20} "
            f"{case['expected']:<10} {actual:<10} "
            f"{score:<8} {elapsed:<12.3f} {status}"
        )

    avg_latency = total_time / len(TEST_CASES)

    legitimate_results = [
        item
        for item in results
        if item["category"] == "Clearly Legitimate"
    ]

    false_positives = sum(
        1
        for item in legitimate_results
        if item["actual"] in ["Medium", "High"]
    )

    fp_rate = (
        false_positives / len(legitimate_results) * 100
        if legitimate_results
        else 0.0
    )

    print("=" * 96)
    print(
        f"Total Benchmark Cases: {len(TEST_CASES)} | "
        f"Passed: {passed_verdicts}/{len(TEST_CASES)} "
        f"({(passed_verdicts / len(TEST_CASES)) * 100:.1f}%)"
    )
    print(f"Average Pipeline Latency: {avg_latency:.3f}s per query")
    print(
        "False-Positive Rate on Legitimate Offers: "
        f"{fp_rate:.1f}% "
        f"({false_positives} false alarms out of "
        f"{len(legitimate_results)} legitimate offers)"
    )
    print("=" * 96)

    return results


def run_grounding_tests():
    """
    Regression tests for the RAG-to-GenAI grounding boundary.

    These tests specifically fail when the final response introduces sensitive
    details that were present only in a retrieved pattern and not in the offer.
    """
    print("\n" + "=" * 96)
    print("GROUNDING / HALLUCINATION REGRESSION TESTS")
    print("=" * 96)

    passed = 0

    for case in GROUNDING_CASES:
        res = analyze_job_offer(case["text"])

        combined_output = " ".join(
            [
                str(res.get("explanation", "")),
                " ".join(
                    str(flag)
                    for flag in res.get("identified_red_flags", [])
                ),
            ]
        ).lower()

        failures = []

        for forbidden in case.get("forbidden_terms", []):
            if forbidden.lower() in combined_output:
                failures.append(
                    f"unsupported term appeared: '{forbidden}'"
                )

        expected = case.get("expected")
        if expected and res["risk_level"] != expected:
            failures.append(
                f"expected verdict {expected}, got {res['risk_level']}"
            )

        if failures:
            status = "FAIL [X]"
            detail = "; ".join(failures)
        else:
            status = "PASS [OK]"
            detail = "Grounded output"
            passed += 1

        print(
            f"{case['id']:<12} {status:<12} "
            f"{case['description']} | {detail}"
        )

    print(
        f"Grounding Tests Passed: {passed}/{len(GROUNDING_CASES)}"
    )

    return passed == len(GROUNDING_CASES)


def test_rag_category_coverage():
    """
    Confirm that a deliberately multi-signal scam retrieves the major
    evidence-supported fraud categories rather than several duplicate records
    from only one category.
    """
    sample = """
    Congratulations on your direct selection at Infosys India.
    No interview is required.
    Please pay a refundable registration fee of INR 2,499 via UPI within 2 hours.
    Send your Aadhaar card copy and bank account details.
    Contact: careers.infosys.hr@gmail.com
    """

    extracted = extract_offer_details(sample)
    matches = check_red_flags_rag(sample, extracted)

    categories = {
        match.get("category")
        for match in matches
        if match.get("category")
    }

    expected_categories = {
        "upfront_fee",
        "urgency_pressure",
        "premature_personal_info",
        "domain_mismatch",
    }

    missing = expected_categories - categories

    print("\n" + "=" * 96)
    print("RAG CATEGORY-COVERAGE TEST")
    print("=" * 96)
    print("Retrieved categories:", ", ".join(sorted(categories)) or "None")
    print("Expected categories:", ", ".join(sorted(expected_categories)))

    if missing:
        print("RAG category coverage: FAIL [X]")
        print("Missing categories:", ", ".join(sorted(missing)))
        return False

    # Also verify that each returned category carries observed evidence.
    missing_evidence = [
        match.get("category", "unknown")
        for match in matches
        if not match.get("evidence")
    ]

    if missing_evidence:
        print("RAG category coverage: FAIL [X]")
        print(
            "Matches missing observed evidence:",
            ", ".join(missing_evidence),
        )
        return False

    print("RAG category coverage: PASS [OK]")
    return True


def test_ml_classifier():
    """
    Test the EMSCAD machine learning classifier on distinct fraud and legitimate samples.
    """
    print("\n" + "=" * 96)
    print("EMSCAD MACHINE LEARNING CLASSIFIER TEST")
    print("=" * 96)

    fraud_sample = (
        "URGENT HIRING: Work from Home data entry clerk. Earn cash Rs 75,000 monthly. "
        "No interview required. Direct selection. Remit registration fee via link."
    )
    legit_sample = (
        "We are hiring a Software Engineering Intern at Microsoft India. "
        "Our engineering team develops scalable cloud services for global enterprise clients. "
        "Please review the formal job description and company profile on our careers portal."
    )

    fraud_res = detect_fraud_ml(fraud_sample)
    legit_res = detect_fraud_ml(legit_sample)

    print(f"Scam Sample Probability:  {fraud_res['fraud_probability_pct']}% | Verdict: {fraud_res['verdict']} | Level: {fraud_res['risk_level']}")
    print(f"Scam Detected Tokens:     {fraud_res['top_risk_tokens']}")
    print(f"Legit Sample Probability: {legit_res['fraud_probability_pct']}% | Verdict: {legit_res['verdict']} | Level: {legit_res['risk_level']}")
    print(f"Legit Detected Tokens:    {legit_res['top_legit_tokens']}")

    passed = True
    if fraud_res["ml_fraud_probability"] < 0.70:
        print("[FAIL] Scam sample probability should be >= 70%")
        passed = False

    if legit_res["ml_fraud_probability"] > 0.30:
        print("[FAIL] Legit sample probability should be <= 30%")
        passed = False

    required_keys = ["is_flagged", "ml_fraud_probability", "risk_level", "verdict", "top_risk_tokens"]
    for k in required_keys:
        if k not in fraud_res:
            print(f"[FAIL] Missing key {k} in ML output")
            passed = False

    print(f"ML Classifier Unit Test: {'PASS [OK]' if passed else 'FAIL [X]'}")
    return passed


def run_all_tests():
    ml_ok = test_ml_classifier()
    benchmark_results = run_benchmark()
    grounding_ok = run_grounding_tests()
    rag_coverage_ok = test_rag_category_coverage()

    benchmark_ok = all(
        item["status"].startswith("PASS")
        for item in benchmark_results
    )

    print("\n" + "=" * 96)
    print("FINAL TEST SUMMARY")
    print("=" * 96)
    print(
        "ML Classifier:",
        "PASS" if ml_ok else "FAIL",
    )
    print(
        "Benchmark:",
        "PASS" if benchmark_ok else "FAIL",
    )
    print(
        "Grounding:",
        "PASS" if grounding_ok else "FAIL",
    )
    print(
        "RAG Coverage:",
        "PASS" if rag_coverage_ok else "FAIL",
    )

    all_ok = ml_ok and benchmark_ok and grounding_ok and rag_coverage_ok

    print(
        "Overall:",
        "PASS [OK]" if all_ok else "FAIL [X]",
    )
    print("=" * 96)

    return all_ok


if __name__ == "__main__":
    success = run_all_tests()
    raise SystemExit(0 if success else 1)
