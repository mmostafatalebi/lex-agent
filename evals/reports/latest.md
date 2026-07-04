# LexAgent Evaluation Report

Generated: 2026-07-04T10:45:25Z
Cache mode: replay
Total cost: $0.1008 (cached: 0 calls, live: 56)

> **Note:** These numbers were produced by a deterministic keyword-baseline stub, not by real Claude, because this environment has no AWS credentials or database. The harness, cache, and report format are exercised end to end; regenerate against the real pipeline with `python -m evals --mode record` (requires AWS Bedrock and a seeded Postgres).

## Summary

| Fixture | Doc Type | Precision | Recall | F1 | Hallucination | Ret. Precision | Ret. Recall |
|---|---|---|---|---|---|---|---|
| msa_problematic | ✓ | 0.80 | 0.80 | 0.80 | 0.00 | 1.00 | 1.00 |
| nda_broad_scope | ✓ | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 |
| sow_ambiguous | ✓ | 0.67 | 0.50 | 0.57 | 0.00 | 0.75 | 0.75 |
| **Macro avg** | 100% | 0.82 | 0.77 | 0.79 | 0.00 | 0.92 | 0.92 |

## Per-fixture detail

### msa_problematic

Document type matched ✓

Expected 5 flags, detected 5 flags, matched 4.

| Expected | Detected | Match | Notes |
|---|---|---|---|
| Limitation of Liability / unlimited_liability / dealbreaker | clause_007 / "unlimited liability for any and all damages, los" / dealbreaker | ✓ | stub keyword overlap |
| Intellectual Property Assignment / broad_ip_assignment / dealbreaker | clause_004 / "pre-existing intellectual property owned or crea" / dealbreaker | ✓ | stub keyword overlap |
| Term and Termination / one_sided_termination / important | clause_006 / "at any time, for any reason or no reason, effect" / important | ✓ | stub keyword overlap |
| Non-Competition / overbroad_non_compete / important | clause_005 / "three (3) years following termination. Confident" / important | ✓ | stub keyword overlap |
| Payment Terms / missing_payment_timeline / important | (not detected) | ✗ | No detected flag matched this expected risk. |

Detected but unmatched:
- clause_009 / "three (3) years following its termination, Contr"

### nda_broad_scope

Document type matched ✓

Expected 3 flags, detected 3 flags, matched 3.

| Expected | Detected | Match | Notes |
|---|---|---|---|
| Term / indefinite_term / dealbreaker | clause_004 / "in perpetuity, surviving indefinitely and never " / dealbreaker | ✓ | stub keyword overlap |
| Definition of Confidential Information / broad_confidentiality / important | clause_002 / "any and all information of any kind whatsoever, " / important | ✓ | stub keyword overlap |
| Indemnification / unlimited_liability / dealbreaker | clause_005 / "without any cap or limitation on the amount of s" / dealbreaker | ✓ | stub keyword overlap |

### sow_ambiguous

Document type matched ✓

Expected 4 flags, detected 3 flags, matched 2.

| Expected | Detected | Match | Notes |
|---|---|---|---|
| Scope of Services / vague_scope / important | clause_002 / "as needed, including but not limited to such tas" / important | ✓ | stub keyword overlap |
| Deliverables and Acceptance / vague_scope / important | (not detected) | ✗ | No detected flag matched this expected risk. |
| Change Control / one_sided_amendment / dealbreaker | clause_004 / "in its sole discretion, modify, expand, or redir" / dealbreaker | ✓ | stub keyword overlap |
| Fees and Payment / missing_payment_timeline / important | (not detected) | ✗ | No detected flag matched this expected risk. |

Detected but unmatched:
- clause_005 / "in its sole discretion. If the Client is not sat"
