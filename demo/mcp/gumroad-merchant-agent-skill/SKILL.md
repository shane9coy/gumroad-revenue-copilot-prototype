---
name: gumroad-merchant-mcp
description: Use when the user wants to operate the Gumroad Merchant MCP server for creator analytics, Refund Ops, Content Radar, Retention Saver, admin API/CLI actions, local agent actions, QA generation, or Gumroad help-doc search from an MCP-capable agent.
---

# Gumroad Merchant MCP

Use this skill when the `gumroad_merchant` MCP server is available. The server reads the local seeded Gumroad Merchant database and exposes analytics, refund, growth, retention, admin action, QA, and help-doc tools.

## First Move

1. Confirm the MCP server is connected.
2. Call `get_gumroad_merchant_help_menu` with `section="all"`.
3. If the user asks a business question, use the narrowest relevant tool first instead of guessing from memory.
4. Cite concrete fields from tool results: product name, product id, revenue, conversion, refund rate, traffic source, case id, trend id, action id, or help-doc title.

## Execution

- Tools with `local_write` may write only local test-profile rows or generated artifacts inside the repo.
- Treat refunds, disputes, emails, posts, product edits, pricing changes, subscription changes, payout changes, and admin operations as permission-scoped workflows unless a production MCP server explicitly exposes scoped write permissions.
- For write-like requests, summarize the intended action, affected object, risk, required confirmation, and audit note before any apply step.

## Common Variables

- `product_id`: use `all` by default. Seeded examples include `prod-audio-pack`, `prod-creator-os`, `prod-design-kit`, and `prod-zine-guide`.
- `date_range`: use `30`, `90`, or `all`.
- `limit`: use a small integer such as `5`, `6`, `10`, or `20`.
- `mode`: refund case filter. Use `all`, `prevent`, `review`, or `dispute`.
- `case_id`: get from `list_refund_cases`.
- `trend_id`: get from `list_content_trends`.
- `signal_id`: get from `get_detected_signals`.
- `action_id`: get from `list_agent_actions`, `list_admin_action_templates`, or a previous preview result.
- `suite_id`, `test_id`: get from `list_shortest_qa_suites` or `generate_shortest_qa_tests`.

## Demo Command Guide

Use these natural-language commands as reliable demo prompts. Call the mapped MCP tools underneath.

1. "Use Gumroad Merchant to show me what I can do."
   Tool: `get_gumroad_merchant_help_menu(section="all")`

2. "Show the analytics tools only."
   Tool: `get_gumroad_merchant_help_menu(section="analytics")`

3. "Summarize monthly sales and tell me what changed."
   Tools: `get_product_metrics(product_id="all", date_range="30")`, then `get_dashboard_summary(product_id="all", date_range="30")`

4. "Compare the last 90 days across all products."
   Tools: `get_product_metrics(product_id="all", date_range="90")`, `get_traffic_sources(product_id="all", date_range="90", limit=6)`

5. "Which traffic source is converting best?"
   Tool: `get_traffic_sources(product_id="all", date_range="30", limit=6)`

6. "Show me the strongest revenue signals."
   Tool: `get_detected_signals(product_id="all", date_range="30")`

7. "Build a realistic three-month sales plan."
   Tool: `build_strategy_plan(product_id="all", date_range="30", horizon_months=3)`

8. "Build a six-month plan for the creator OS product."
   Tool: `build_strategy_plan(product_id="prod-creator-os", date_range="90", horizon_months=6)`

9. "Review the first detected signal and tell me the next action."
   Tools: `get_detected_signals`, then `get_action_review(signal_id=...)`

10. "Show Refund Ops status."
    Tool: `get_refund_ops_summary(product_id="all", date_range="30")`

11. "List refund cases that need review."
    Tool: `list_refund_cases(product_id="all", date_range="30", mode="review", limit=10)`

12. "List chargeback dispute cases."
    Tool: `list_refund_cases(product_id="all", date_range="30", mode="dispute", limit=10)`

13. "Open this refund case."
    Tool: `get_refund_case(case_id=...)`

14. "Build a dispute packet for the highest-risk case."
    Tools: `list_refund_cases(mode="dispute")`, then `build_dispute_evidence_pack(case_id=...)`

15. "Draft a buyer reply for this refund case."
    Tool: `draft_refund_reply(case_id=...)`

16. "What can reduce preventable refunds?"
    Tool: `get_refund_prevention_actions(product_id="all", date_range="30")`

17. "Show Content Radar opportunities."
    Tool: `get_content_radar_summary(product_id="all", date_range="30")`

18. "List the best campaign angles."
    Tool: `list_content_trends(product_id="all", date_range="30", limit=6)`

19. "Build a four-week marketing plan."
    Tool: `build_marketing_plan(product_id="all", date_range="30", horizon_weeks=4)`

20. "Draft campaign assets for the strongest trend."
    Tools: `list_content_trends`, then `draft_campaign_assets(product_id="all", date_range="30", trend_id=..., channel=...)`

21. "Stage a tracked campaign action."
    Tool: `stage_tracked_campaign_action(product_id="all", date_range="30")`

22. "Create the tracked campaign row."
    Tool: `create_tracked_campaign_action(product_id="all", date_range="30")`

23. "Show tracked campaigns."
    Tool: `list_tracked_campaigns(product_id="all", limit=20)`

24. "List pending agent actions."
    Tool: `list_agent_actions(action_type="all", status="pending", product_id="all", limit=20)`

25. "Apply this pending local action."
    Tool: `apply_agent_action(action_id=...)`

26. "Generate a 30-day roadmap."
    Tool: `generate_roadmap_artifact(product_id="all", date_range="30", horizon_days=30)`

27. "Generate the architecture diagram."
    Tool: `generate_architecture_diagram(diagram_type="agent-action-system")`

28. "Show retention risk."
    Tool: `get_retention_saver_summary(product_id="all", date_range="30")`

29. "List cancellation risks."
    Tool: `list_cancellation_risks(product_id="all", date_range="30", limit=10)`

30. "Build a pause-offer plan."
    Tool: `build_pause_offer_plan(product_id="all", date_range="30")`

31. "Estimate revenue saved if pause offers convert at 12%."
    Tool: `estimate_pause_revenue_saved(product_id="all", date_range="30", save_rate="12%")`

32. "Answer Gumroad issue 4677's admin API and CLI questions."
    Tool: `get_admin_api_cli_recommendation()`

33. "List admin action templates."
    Tool: `list_admin_action_templates()`

34. "Prepare an exact purchase lookup command."
    Tool: `build_cli_command_preview(action_id="purchase_lookup", purchase_id=...)`

35. "Prepare an admin action and show permission requirements."
    Tool: `preview_admin_action(action_id=..., purchase_id=..., case_id=..., reason=..., note=...)`

36. "Show QA coverage."
    Tool: `get_shortest_qa_summary()`

37. "List QA suites."
    Tool: `list_shortest_qa_suites()`

38. "Generate QA tests for Refund Ops."
    Tool: `generate_shortest_qa_tests(suite_id="refund_ops", target_surface="all", priority="all", limit=5)`

39. "Show this QA test."
    Tool: `get_shortest_qa_test(test_id=...)`

40. "Search products for creator."
    Tool: `search_products(query="creator", limit=5)`

41. "Search Gumroad help docs for chargebacks."
    Tool: `search_gumroad_help_docs(query="chargebacks", category="money_ops", limit=5)`

42. "Which help docs are loaded?"
    Tool: `get_help_doc_inventory()`

43. "What local data is loaded?"
    Tool: `get_database_inventory()`

## Tool Map

Analytics:
- `get_product_metrics(product_id="all", date_range="30")`
- `get_traffic_sources(product_id="all", date_range="30", limit=6)`
- `get_detected_signals(product_id="all", date_range="30")`
- `get_dashboard_summary(product_id="all", date_range="30")`
- `build_strategy_plan(product_id="all", date_range="30", horizon_months=3)`
- `get_action_review(signal_id, product_id="all", date_range="30")`

Refund Ops:
- `get_refund_ops_summary(product_id="all", date_range="30")`
- `list_refund_cases(product_id="all", date_range="30", mode="all", limit=10)`
- `get_refund_case(case_id)`
- `build_dispute_evidence_pack(case_id)`
- `draft_refund_reply(case_id)`
- `get_refund_prevention_actions(product_id="all", date_range="30")`

Growth:
- `get_content_radar_summary(product_id="all", date_range="30")`
- `list_content_trends(product_id="all", date_range="30", limit=6)`
- `build_marketing_plan(product_id="all", date_range="30", horizon_weeks=4)`
- `draft_campaign_assets(product_id="all", date_range="30", trend_id=null, channel=null)`
- `stage_tracked_campaign_action(product_id="all", date_range="30")`
- `create_tracked_campaign_action(product_id="all", date_range="30")`
- `list_tracked_campaigns(product_id="all", limit=20)`

Local actions and artifacts:
- `list_agent_actions(action_type="all", status="all", product_id="all", limit=20)`
- `apply_agent_action(action_id)`
- `generate_roadmap_artifact(product_id="all", date_range="30", horizon_days=30)`
- `generate_architecture_diagram(diagram_type="agent-action-system")`

Retention:
- `get_retention_saver_summary(product_id="all", date_range="30")`
- `list_cancellation_risks(product_id="all", date_range="30", limit=10)`
- `build_pause_offer_plan(product_id="all", date_range="30")`
- `estimate_pause_revenue_saved(product_id="all", date_range="30", save_rate=null)`

Admin actions:
- `get_admin_action_preview_summary(product_id="all", limit=6)`
- `get_admin_api_cli_recommendation()`
- `list_admin_action_templates()`
- `build_cli_command_preview(action_id="purchase_lookup", purchase_id=null, case_id=null, product_id=null, creator_id=null, user_id=null, user_email=null, target_id=null, risk_state=null, fee_percent=null, reason=null, note=null)`
- `preview_admin_action(action_id="purchase_lookup", purchase_id=null, case_id=null, product_id=null, creator_id=null, user_id=null, user_email=null, target_id=null, risk_state=null, fee_percent=null, starts_at=null, ends_at=null, expires_at=null, reason=null, note=null)`

QA and search:
- `get_shortest_qa_summary()`
- `list_shortest_qa_suites()`
- `generate_shortest_qa_tests(suite_id="all", target_surface="all", priority="all", limit=null)`
- `get_shortest_qa_test(test_id)`
- `search_products(query="", limit=5)`
- `search_gumroad_help_docs(query, category="money_ops", limit=5)`
- `get_help_doc_inventory()`
- `get_database_inventory()`
