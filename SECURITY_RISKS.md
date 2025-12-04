# Security & Risk Analysis

| Risk | Scenario | Likelihood | Impact | Mitigation | Monitoring |
| --- | --- | --- | --- | --- | --- |
| LLM prompt injection & data exfiltration | Malicious inputs attempt to coerce planner into leaking stored data or bypassing constraints. | Medium | High | Keep system prompts strict; validate/escape user input; restrict tools to mock data; enforce JSON output parsing; rate-limit requests. | Log planner errors; add anomaly detection on unusual prompt patterns or repeated failures. |
| Abuse of booking/payment flows | Automated requests spam booking simulation or force failed payments to probe behavior. | Medium | Medium | Add auth (JWT/OAuth) per user; rate-limit POST /plan and /plan/{id}/book; cap retry counts; do not expose internal errors. | Track booking attempts per user/IP; alert on spikes or high failure rates. |
| Sensitive data exposure (PII, payment info) | Returning or logging user profile/payment details. | Medium | High | Avoid storing full payment data; mask identifiers; scrub logs; segregate secrets via environment variables; apply data minimization. | Centralized logging with filters; periodic scans for secrets/PII in logs. |
| Misuse of calendar access | Unauthorized access to another user’s busy slots. | Low | Medium | Require user-scoped auth; enforce authorization checks on calendar queries; limit returned data to availability only. | Audit calendar queries per user; alert on cross-user access attempts. |
| Logging secrets or tokens | Misconfigured logging leaks env vars or payment flags. | Low | High | Structured logging that excludes secrets; never log payment tokens or card data; review debug logging before release. | Log scrubbing in pipeline; automated checks for secrets in logs/repo. |
| Data integrity for mock inventory | Planner relies on static catalog that could be tampered with to inflate prices. | Low | Medium | Store catalogs in signed/static assets or controlled config; validate schema on load. | Periodic checksum/validation of catalog data; alert on changes. |
| Denial of service | Large payloads or heavy query loops exhaust resources. | Medium | Medium | Set request size limits, timeouts, and concurrency caps; cache common responses; paginate future listings. | Observe latency/throughput; alert on sustained resource spikes. |

Notes:
- Authentication/authorization is not implemented in this PoC; required for production.
- Payment simulation must be replaced with a PCI-compliant provider; never log cardholder data.
