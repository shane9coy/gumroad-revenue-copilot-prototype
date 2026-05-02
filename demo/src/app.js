import { products as seededProducts } from "../data/products.js";
import {
  applyDateRange,
  buildAdminActionPreview,
  buildAggregateProduct,
  buildContentRadar,
  buildRefundOps,
  buildRetentionSaver,
  buildSalesDashboard,
  buildShortestQa,
  buildProductMetrics,
  detectSignals,
  formatCurrency,
  formatPercent,
  generateSuggestions,
  setSalesDashboardData,
} from "./analytics.js?v=prompt-context-examples-20260501-1";

let products = seededProducts;

const DAY_MS = 24 * 60 * 60 * 1000;

function toDateInputValue(date) {
  return date.toISOString().slice(0, 10);
}

function getTrailingDateRange(days) {
  const normalizedDays = Math.max(1, Number(days) || 1);
  const end = new Date();
  const start = new Date(end.getTime() - (normalizedDays - 1) * DAY_MS);

  return {
    start: toDateInputValue(start),
    end: toDateInputValue(end),
  };
}

const defaultCustomRange = getTrailingDateRange(30);
const defaultCustomStartDate = defaultCustomRange.start;
const defaultCustomEndDate = defaultCustomRange.end;

const dateRangeCopy = {
  "30": {
    label: "last 30 days",
    churnBadge: "Last 30 days",
    days: 30,
  },
  "90": {
    label: "last 90 days",
    churnBadge: "Last 90 days",
    days: 90,
  },
  "180": {
    label: "last 180 days",
    churnBadge: "Last 180 days",
    days: 180,
  },
  all: {
    label: "all-time",
    churnBadge: "All-time range",
    days: 365,
  },
  custom: {
    label: "custom date range",
    churnBadge: "Custom range",
    days: 30,
  },
};

const INITIAL_MERCHANT_MESSAGE = {
  id: "merchant-initial",
  role: "assistant",
  content:
    "Gumroad Merchant is ready. Click any signal below and I will stage a prompt in the input first. Edit it, then send when it sounds right.",
  citations: [],
  followups: [
    "Break down my products and explain why some are selling better than others.",
    "Compare my traffic sources and tell me which one deserves the next test.",
    "Find the biggest conversion, refund, or churn issue in this date range.",
  ],
};

function initialMerchantMessages() {
  return [{ ...INITIAL_MERCHANT_MESSAGE }];
}

function createEmptyFeatureInsights(overrides = {}) {
  return {
    key: "",
    live: false,
    loading: false,
    analyticsSummary: null,
    contentRadar: {
      summary: null,
      trends: [],
    },
    refundOps: {
      summary: null,
      cases: [],
      preventionActions: [],
    },
    retention: {
      summary: null,
      risks: [],
    },
    admin: {
      summary: null,
      templates: [],
    },
    qa: {
      summary: null,
      suites: [],
      tests: [],
    },
    error: "",
    ...overrides,
  };
}

const state = {
  selectedProductId: "all",
  activePortfolioProductId: "prod-creator-os",
  dateRange: "30",
  customStartDate: defaultCustomStartDate,
  customEndDate: defaultCustomEndDate,
  locationScope: "world",
  activeTrendMetric: "revenue",
  sourceSort: "revenue",
  churnSortDirection: "desc",
  locationSortDirection: "desc",
  refundMode: "prevent",
  activeRefundCaseId: null,
  activeContentTrendId: null,
  activeAdminActionId: null,
  activeQaSuiteId: null,
  featureInsights: createEmptyFeatureInsights(),
  generated: true,
  activeSuggestionId: null,
  expandedSuggestionIds: new Set(),
  merchantSessionId: "",
  merchantMessages: initialMerchantMessages(),
  merchantSessions: {
    recent: [],
    saved: [],
  },
  merchantSessionView: "saved",
  merchantSessionsLoading: false,
  merchantSending: false,
  merchantSamplesDismissed: false,
  merchantChatFullscreen: false,
  merchantRailCollapsed: false,
  merchantTranscriptHeight: null,
  analyticsSource: {
    label: "Static seed fallback",
    live: false,
    trackedCampaignCount: 0,
  },
};

const productSelect = document.querySelector("#product-select");
const dateRangeSelect = document.querySelector("#date-range-select");
const customStartDate = document.querySelector("#custom-start-date");
const customEndDate = document.querySelector("#custom-end-date");
const chartRangeSelect = document.querySelector("#chart-range-select");
const productName = document.querySelector("#product-name");
const productDescription = document.querySelector("#product-description");
const dataSourceNote = document.querySelector("#data-source-note");
const productTags = document.querySelector("#product-tags");
const metricGrid = document.querySelector("#metric-grid");
const sourceTable = document.querySelector("#source-table");
const churnMetricGrid = document.querySelector("#churn-metric-grid");
const churnFormula = document.querySelector("#churn-formula");
const churnRangeBadge = document.querySelector("#churn-range-badge");
const locationsTable = document.querySelector("#locations-table");
const locationScopeSelect = document.querySelector("#location-scope-select");
const utmTable = document.querySelector("#utm-table");
const exportSummary = document.querySelector("#export-summary");
const exportCsvButton = document.querySelector("#export-csv-button");
const suggestions = document.querySelector("#suggestions");
const portfolioTabs = document.querySelector("#portfolio-tabs");
const portfolioDetail = document.querySelector("#portfolio-detail");
const barChart = document.querySelector("#bar-chart");
const chartCaption = document.querySelector("#chart-caption");
const chartDetailPanel = document.querySelector("#chart-detail-panel");
const chartSourceBreakdown = document.querySelector("#chart-source-breakdown");
const chartMetricButtons = document.querySelectorAll("[data-chart-metric]");
const sourceSortSelect = document.querySelector("#source-sort-select");
const locationSortButton = document.querySelector("#location-sort-button");
const refundOpsStatus = document.querySelector("#refund-ops-status");
const refundOpsMetrics = document.querySelector("#refund-ops-metrics");
const refundOpsLayout = document.querySelector(".refund-ops-layout");
const refundCaseHeading = document.querySelector("#refund-case-heading");
const refundCaseList = document.querySelector("#refund-case-list");
const refundCaseDetail = document.querySelector("#refund-case-detail");
const refundPreventionList = document.querySelector("#refund-prevention-list");
const refundModeButtons = document.querySelectorAll("[data-refund-mode]");
const contentRadarStatus = document.querySelector("#content-radar-status");
const contentRadarMetrics = document.querySelector("#content-radar-metrics");
const contentTrendList = document.querySelector("#content-trend-list");
const contentPlanDetail = document.querySelector("#content-plan-detail");
const retentionSaverStatus = document.querySelector("#retention-saver-status");
const retentionMetrics = document.querySelector("#retention-metrics");
const pauseOfferList = document.querySelector("#pause-offer-list");
const retentionRiskList = document.querySelector("#retention-risk-list");
const retentionRiskBadge = document.querySelector("#retention-risk-badge");
const adminPreviewStatus = document.querySelector("#admin-preview-status");
const adminPreviewMetrics = document.querySelector("#admin-preview-metrics");
const adminActionList = document.querySelector("#admin-action-list");
const adminActionDetail = document.querySelector("#admin-action-detail");
const shortestQaStatus = document.querySelector("#shortest-qa-status");
const shortestQaMetrics = document.querySelector("#shortest-qa-metrics");
const shortestQaList = document.querySelector("#shortest-qa-list");
const shortestQaDetail = document.querySelector("#shortest-qa-detail");
const actionReview = document.querySelector("#action-review");
const actionReviewTitle = document.querySelector("#action-review-title");
const actionReviewMeta = document.querySelector("#action-review-meta");
const actionReviewCopy = document.querySelector("#action-review-copy");
const actionReviewSteps = document.querySelector("#action-review-steps");
const actionReviewClose = document.querySelector("#action-review-close");
const actionReviewCopyButton = document.querySelector("#action-review-copy-button");
const actionReviewCopyStatus = document.querySelector("#action-review-copy-status");
const dashboardView = document.querySelector("#dashboard-view");
const clickSignalHeader = document.querySelector("#click-signal-header");
const clickSignalClose = document.querySelector("#click-signal-close");
const merchantLanesGroup = document.querySelector("#merchant-lanes-group");
const embeddedPagePanel = document.querySelector("#embedded-page-panel");
const embeddedPageFrame = document.querySelector("#embedded-page-frame");
const embeddedPageKicker = document.querySelector("#embedded-page-kicker");
const embeddedPageTitle = document.querySelector("#embedded-page-title");
const embeddedPageDescription = document.querySelector("#embedded-page-description");
const embeddedPageClose = document.querySelector("#embedded-page-close");
const workspaceNavLinks = document.querySelectorAll("[data-dashboard-view], [data-embedded-page]");
const merchantPanel = document.querySelector(".merchant-panel");
const merchantChatShell = document.querySelector(".merchant-chat-shell");
const merchantStatus = document.querySelector("#merchant-status");
const merchantMessages = document.querySelector("#merchant-messages");
const merchantSamples = document.querySelector("#merchant-samples");
const merchantChatForm = document.querySelector("#merchant-chat-form");
const merchantChatInput = document.querySelector("#merchant-chat-input");
const merchantChatSubmit = document.querySelector("#merchant-chat-submit");
const merchantFullscreenButton = document.querySelector("#merchant-fullscreen-button");
const merchantRailToggle = document.querySelector("#merchant-rail-toggle");
const merchantResizeGrip = document.querySelector("#merchant-resize-grip");
const merchantVoiceRow = document.querySelector("#merchant-voice-row");
const merchantVoiceButton = document.querySelector("#merchant-voice-button");
const merchantNewChatButton = document.querySelector("#merchant-new-chat");
const merchantSaveChatButton = document.querySelector("#merchant-save-chat");
const merchantRenameChatButton = document.querySelector("#merchant-rename-chat");
const merchantDeleteChatButton = document.querySelector("#merchant-delete-chat");
const merchantSessionList = document.querySelector("#merchant-session-list");
const merchantSavedSessionList = document.querySelector("#merchant-saved-session-list");
const merchantSessionTabs = document.querySelectorAll("[data-merchant-session-view]");
const merchantSessionPanels = document.querySelectorAll("[data-merchant-session-panel]");
const themeToggle = document.querySelector("#theme-toggle");

const MERCHANT_API_BASE =
  window.GUMROAD_MERCHANT_API_BASE ?? "http://127.0.0.1:8001";
const MERCHANT_SESSION_STORAGE_KEY = "gumroad-merchant-session-id";
const MERCHANT_TRANSCRIPT_HEIGHT_STORAGE_KEY = "gumroad-merchant-transcript-height";
const MERCHANT_RAIL_COLLAPSED_STORAGE_KEY = "gumroad-merchant-rail-collapsed";
const MERCHANT_TRANSCRIPT_MIN_HEIGHT = 620;
const MERCHANT_TRANSCRIPT_MOBILE_MIN_HEIGHT = 360;
const MERCHANT_RECENT_SESSION_LIMIT = 10;
const MERCHANT_SAVED_SESSION_LIMIT = 10;
const THEME_STORAGE_KEY = "gumroad-merchant-theme";
const embeddedPages = {
  architecture: {
    src: "./architecture.html?v=action-language-cleanup-20260501",
    kicker: "Architecture",
    title: "Gumroad Merchant architecture",
    description:
      "This frame explains the whole demo: seeded analytics become detected signals, agent lanes turn them into action-ready recommendations, and the future Rails path shows where real Gumroad data, permissions, and audit trails would connect.",
  },
  chatflow: {
    src: "./chatbot-redis-temporal-architecture.html?v=action-language-cleanup-20260501",
    kicker: "Chat flow",
    title: "Gumroad Merchant durability",
    description:
      "This frame explains how the agent becomes production-durable: SQL stores the transcript of record, Redis coordinates in-flight state, and Temporal can run 24-hour workflows, retries, and long agent jobs across browser reloads or later sessions.",
  },
  mcp: {
    src: "./mcp.html?v=merchant-mcp-skill-download-20260502",
    kicker: "MCP server",
    title: "Connect your local agent",
    description:
      "This frame shows how to connect Codex, Claude, Cursor, or another MCP-capable local agent to Gumroad Merchant with a copyable installer prompt and the scoped automation plan.",
  },
  brief: {
    src: "./brief.html?v=action-language-cleanup-20260501",
    kicker: "Prototype brief",
    title: "Hackathon demo brief",
    description: "The operator-facing project brief without leaving the dashboard.",
  },
};
const dashboardShortcuts = {
  "all-products": "#analytics-controls",
  sales: "#sales-panel",
  churn: "#churn-panel",
  utm: "#utm-panel",
  "content-radar": "#content-radar-panel",
  retention: "#retention-saver-panel",
  "admin-preview": "#admin-preview-panel",
  qa: "#shortest-qa-panel",
};

function storedTheme() {
  const saved = window.localStorage.getItem(THEME_STORAGE_KEY);

  if (saved === "dark" || saved === "light") {
    return saved;
  }

  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  const normalizedTheme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = normalizedTheme;
  window.localStorage.setItem(THEME_STORAGE_KEY, normalizedTheme);

  if (themeToggle) {
    const isDark = normalizedTheme === "dark";
    themeToggle.setAttribute("aria-pressed", String(isDark));
    themeToggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
  }

}

const signalPanelConfigs = [
  { id: "merchant-panel", selector: ".merchant-panel", showPrompt: false },
  { id: "suggested-next-moves-panel", selector: "#suggested-next-moves-panel", promptKey: "suggestions" },
  { id: "sales-panel", selector: "#sales-panel", promptKey: "performance" },
  { id: "refund-ops-panel", selector: "#refund-ops-panel", promptKey: "refunds", showPrompt: false, showToggle: false, lockOpen: true },
  { id: "content-radar-panel", selector: "#content-radar-panel", promptKey: "content" },
  { id: "retention-saver-panel", selector: "#retention-saver-panel", promptKey: "retention" },
  { id: "admin-preview-panel", selector: "#admin-preview-panel", promptKey: "admin" },
  { id: "shortest-qa-panel", selector: "#shortest-qa-panel", promptKey: "qa" },
  { id: "traffic-source-panel", selector: ".traffic-source-panel", promptKey: "sources", showToggle: false, lockOpen: true },
  { id: "churn-panel", selector: "#churn-panel", promptKey: "churn", showToggle: false, lockOpen: true },
  { id: "locations-panel", selector: "#locations-panel", promptKey: "sources", showToggle: false, lockOpen: true },
  { id: "utm-panel", selector: "#utm-panel", promptKey: "content", showToggle: false, lockOpen: true },
  { id: "export-panel", selector: "#export-panel", promptKey: "export", showToggle: false, lockOpen: true },
];

let stagedPromptTimer = 0;
let featureInsightsRequestId = 0;

function setWorkspaceNavActive(activePage) {
  workspaceNavLinks.forEach((link) => {
    const isActive =
      activePage === "dashboard"
        ? link.dataset.dashboardView === "dashboard"
        : link.dataset.embeddedPage === activePage;

    link.classList.toggle("active", isActive);
    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

function showDashboardView({ updateHash = true, scrollTop = true } = {}) {
  dashboardView.hidden = false;
  embeddedPagePanel.hidden = true;
  setWorkspaceNavActive("dashboard");

  if (updateHash) {
    window.history.pushState(null, "", "#dashboard");
  }

  if (scrollTop) {
    window.requestAnimationFrame(() => {
      document.querySelector("#analytics-controls")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }
}

function showEmbeddedPage(pageKey, { updateHash = true } = {}) {
  const page = embeddedPages[pageKey];

  if (!page) {
    showDashboardView({ updateHash, scrollTop: false });
    return;
  }

  embeddedPageKicker.textContent = page.kicker;
  embeddedPageTitle.textContent = page.title;
  embeddedPageDescription.textContent = page.description;
  embeddedPageFrame.src = page.src;
  embeddedPageFrame.title = page.title;
  dashboardView.hidden = true;
  embeddedPagePanel.hidden = false;
  setWorkspaceNavActive(pageKey);

  if (updateHash) {
    window.history.pushState(null, "", `#${pageKey}`);
  }

  window.requestAnimationFrame(() => {
    embeddedPagePanel.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function syncWorkspaceViewFromHash() {
  const hash = window.location.hash.replace(/^#/, "");

  if (embeddedPages[hash]) {
    showEmbeddedPage(hash, { updateHash: false });
    return;
  }

  showDashboardView({ updateHash: false, scrollTop: false });

  if (hash && hash !== "dashboard") {
    window.requestAnimationFrame(() => {
      const target = revealDashboardTarget(`#${CSS.escape(hash)}`);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }
}

function getSelectedProduct() {
  const baseProduct =
    state.selectedProductId === "all"
      ? buildAggregateProduct(products)
      : products.find((product) => product.id === state.selectedProductId) ?? products[0];

  return applyDateRange(baseProduct, state.dateRange, {
    customDays: getRangeDays(),
  });
}

function getRangeLabel() {
  if (state.dateRange === "custom") {
    return `${dateRangeCopy.custom.label} (${state.customStartDate} to ${state.customEndDate})`;
  }

  return dateRangeCopy[state.dateRange]?.label ?? dateRangeCopy["30"].label;
}

function getChurnRangeBadgeLabel() {
  return dateRangeCopy[state.dateRange]?.churnBadge ?? dateRangeCopy["30"].churnBadge;
}

function joinPromptItems(items, emptyText = "No visible rows in this view.") {
  return items.filter(Boolean).join("; ") || emptyText;
}

function buildAgentAnswerExamples(product, metrics, dashboard = buildSalesDashboard(product, metrics)) {
  const topSource = metrics.currentSources[0];
  const topLocation = dashboard.locations[0];
  const topUtm = dashboard.utmLinks[0];
  const directSource = metrics.currentSources.find(
    (source) => source.name.toLowerCase() === "direct"
  );
  const topSourceName = topSource?.name ?? "The top source";
  const topLocationName = topLocation
    ? `${topLocation.region}, ${topLocation.country}`
    : "the top buyer region";
  const topCampaignName = topUtm?.campaign ?? "the cleanest tracked campaign";
  const topCampaignSource =
    [topUtm?.source, topUtm?.medium].filter(Boolean).join(" / ") || "the top tracked source";
  const directRevenue = formatCurrency(directSource?.revenueCents ?? 0, product.currency);

  return {
    locations:
      `${topSourceName} is the top revenue source. ${topLocationName} is the top buyer region. These are separate leaders in the selected range, not proof that ${topSourceName} is driving ${topLocationName} sales.`,
    conversions:
      `${topCampaignName} is the cleanest conversion read: ${topCampaignSource} converts at ${formatPercent(topUtm?.conversion ?? 0)}, compared with ${formatPercent(metrics.currentConversion)} overall. Treat that as a campaign test worth repeating, not proof it will work everywhere.`,
    churn:
      `Churn is ${formatPercent(dashboard.churn.rate)} and refund rate is ${formatPercent(metrics.currentRefundRate)}. If both rise together, inspect product promises, onboarding, and compatibility notes before changing price.`,
    utm:
      `Direct shows ${directRevenue} in revenue, but that bucket can hide apps, email, mobile clients, bookmarks, and private shares. Use tracked links before calling it organic demand.`,
  };
}

function visiblePromptRows(rows, limit = 6) {
  return joinPromptItems(rows.filter(Boolean).slice(0, limit));
}

function buildSectionPrompt(sectionId, product, metrics, range) {
  const productName = product.name;

  if (sectionId === "sales-panel") {
    const dashboard = buildSalesDashboard(product, metrics);
    const topSource = metrics.currentSources[0];
    const rows = [
      `Revenue ${formatCurrency(metrics.currentRevenueCents, product.currency)} (${formatDelta(metrics.revenueDeltaPercent, "last period")})`,
      `${metrics.currentSales.toLocaleString("en-US")} sales from ${metrics.currentViews.toLocaleString("en-US")} views`,
      `Conversion ${formatPercent(metrics.currentConversion)} (${formatDelta(metrics.conversionDelta, "last period")})`,
      `Refund rate ${formatPercent(metrics.currentRefundRate)} from ${metrics.currentRefunds.toLocaleString("en-US")} refunds`,
      topSource
        ? `Top source ${topSource.name}: ${topSource.views.toLocaleString("en-US")} views, ${topSource.sales.toLocaleString("en-US")} sales, ${formatCurrency(topSource.revenueCents, product.currency)} revenue`
        : "",
      `Churn read ${formatPercent(dashboard.churn.rate)} with ${formatCurrency(dashboard.churn.revenueLostCents, product.currency)} recurring revenue lost`,
    ];

    return `Explain the Recent signal section for ${productName} over the ${range}. Use these current data points: ${visiblePromptRows(rows)}. Interpret what changed, which evidence matters most, and the next action the merchant should take.`;
  }

  if (sectionId === "suggested-next-moves-panel") {
    const signals = detectSignals(product, metrics);
    const cards = generateSuggestions(product, metrics, signals);
    const rows = cards.map((card) => {
      const evidence = asArray(card.evidence)
        .map((item) => `${item.label}: ${item.value}${item.comparison ? ` (${item.comparison})` : ""}`)
        .join(", ");
      return `${card.label} / ${card.title}: ${card.confidence} confidence. ${card.reason ?? card.whyItMatters ?? card.recommendation}${evidence ? ` Evidence: ${evidence}` : ""}`;
    });

    return `Explain the Suggested next moves section for ${productName} over the ${range}. Use these current recommendation rows: ${visiblePromptRows(rows, 4)}. Tell me why each suggestion is ranked this way, where the evidence is strongest or weakest, and which action should be staged first.`;
  }

  if (sectionId === "refund-ops-panel") {
    const refundOps = getRefundOpsView(product, metrics);
    const activeMode = state.refundMode;
    const visibleCases = refundOps.cases.filter((item) => item.mode === activeMode);
    const caseRows = activeMode === "prevent"
      ? refundOps.preventionActions.map((action) =>
        `${action.title}: ${action.recommendedAction}. Evidence: ${action.evidence.join(", ")}`
      )
      : visibleCases.map((caseItem) =>
        `${caseItem.label}: ${formatCurrency(caseItem.amountCents, product.currency)}, risk ${caseItem.riskScore}/100, ${caseItem.reason}. Recommended action: ${caseItem.recommendedAction}`
      );
    const rows = [
      `Mode ${activeMode} with ${refundOpsModeCount(refundOps, activeMode).toLocaleString("en-US")} visible items`,
      `Refund rate ${formatPercent(refundOps.summary.refundRate)} vs ${formatPercent(refundOps.summary.previousRefundRate)} previous`,
      `Disputed ${formatCurrency(refundOps.summary.disputedAmountCents, product.currency)}`,
      `Open cases ${refundOps.summary.casesNeedingReview.toLocaleString("en-US")}`,
      `Preventable estimate ${formatCurrency(refundOps.summary.preventableRefundEstimateCents, product.currency)}`,
      ...caseRows,
    ];

    return `Explain the Refund Ops section for ${productName} over the ${range}. Use these current Refund Ops data points: ${visiblePromptRows(rows, 7)}. Interpret the active tab, the biggest risk, and the next case or prevention action to handle.`;
  }

  if (sectionId === "content-radar-panel") {
    const radar = getContentRadarView(product, metrics);
    const activeTrend =
      radar.trends.find((trend) => trend.id === state.activeContentTrendId) ?? radar.trends[0];
    const rows = [
      `${radar.summary.trendCount.toLocaleString("en-US")} trends; top fit ${radar.summary.topFitScore}/100`,
      `Primary channel ${radar.summary.primaryChannel}`,
      `Expected KPI ${radar.summary.expectedKpi}`,
      activeTrend
        ? `Selected trend ${activeTrend.title}: ${activeTrend.fitScore}/100 fit, channel ${activeTrend.channel}, KPI ${activeTrend.expectedKpi}`
        : "",
      activeTrend?.rationale ? `Rationale ${activeTrend.rationale}` : "",
      activeTrend?.evidence?.length ? `Evidence ${activeTrend.evidence.join(", ")}` : "",
      activeTrend?.risks?.length ? `Risks ${activeTrend.risks.join(", ")}` : "",
      activeTrend?.utmPlan ? `UTM ${activeTrend.utmPlan}` : "",
    ];

    return `Explain the Content Radar section for ${productName} over the ${range}. Use these current trend data points: ${visiblePromptRows(rows)}. Explain why the selected trend is recommended, what KPI should improve, what risk to watch, and whether a tracked campaign should be created.`;
  }

  if (sectionId === "retention-saver-panel") {
    const retention = getRetentionView(product, metrics);
    const offerRows = retention.pauseOffers.map((offer) =>
      `${offer.label}: ${formatCurrency(offer.estimatedSavedCents, product.currency)} estimated saved, best for ${offer.bestFor}`
    );
    const riskRows = retention.risks.map((risk) => `${risk.label}: ${risk.value}. ${risk.detail}`);
    const rows = [
      `Churn ${formatPercent(retention.summary.churnRate)} from ${retention.summary.canceledMembers.toLocaleString("en-US")} canceled memberships`,
      `Lost recurring revenue ${formatCurrency(retention.summary.revenueLostCents, product.currency)}`,
      `Modeled saved revenue ${formatCurrency(retention.summary.revenueSavedCents, product.currency)} with ${formatPercent(retention.summary.saveRate)} save assumption`,
      ...offerRows,
      ...riskRows,
    ];

    return `Explain the Retention Saver section for ${productName} over the ${range}. Use these current pause and churn data points: ${visiblePromptRows(rows, 7)}. Explain what the save estimate means, which risk matters most, and what retention action should happen next.`;
  }

  if (sectionId === "admin-preview-panel") {
    const adminPreview = getAdminPreviewView(product, metrics);
    const activeAction =
      adminPreview.templates.find((template) => template.id === state.activeAdminActionId) ?? adminPreview.templates[0];
    const rows = [
      `${adminPreview.summary.templateCount.toLocaleString("en-US")} templates`,
      `${adminPreview.summary.safeReadCount.toLocaleString("en-US")} reads available`,
      `${adminPreview.summary.blockedWriteCount.toLocaleString("en-US")} writes with preflight checks`,
      activeAction
        ? `Selected action ${activeAction.label}: ${activeAction.riskLevel}, ${activeAction.unsafeWrite ? "write action" : "read action"}`
        : "",
      activeAction?.commandText ? `Command ${activeAction.commandText}` : "",
      activeAction?.requiredInputs?.length ? `Required inputs ${activeAction.requiredInputs.join(", ")}` : "",
      activeAction?.preflightChecks?.length ? `Preflight ${activeAction.preflightChecks.join(", ")}` : "",
      activeAction?.auditNote ? `Audit note ${activeAction.auditNote}` : "",
    ];

    return `Explain the Admin Actions section for ${productName}. Use these current action data points: ${visiblePromptRows(rows)}. Explain what can run locally, what needs preflight, and which action is safest to prepare first.`;
  }

  if (sectionId === "shortest-qa-panel") {
    const qa = getShortestQaView(product, metrics);
    const activeSuite =
      qa.suites.find((suite) => suite.id === state.activeQaSuiteId) ?? qa.suites[0];
    const rows = [
      `${qa.summary.suiteCount.toLocaleString("en-US")} suites`,
      `${qa.summary.assertionCount.toLocaleString("en-US")} assertions`,
      activeSuite ? `Selected suite ${activeSuite.title}: ${activeSuite.targetSurface}` : "",
      activeSuite?.riskCovered ? `Risk covered ${activeSuite.riskCovered}` : "",
      activeSuite?.steps?.length ? `Steps ${activeSuite.steps.join(", ")}` : "",
      activeSuite?.assertions?.length ? `Assertions ${activeSuite.assertions.join(", ")}` : "",
      activeSuite?.passFailEvidence ? `Pass/fail evidence ${activeSuite.passFailEvidence}` : "",
    ];

    return `Explain the Shortest QA section for ${productName} over the ${range}. Use these current QA data points: ${visiblePromptRows(rows)}. Explain what this suite validates, what evidence proves pass/fail, and which test should run first.`;
  }

  if (sectionId === "traffic-source-panel") {
    const rows = getSortedSources(metrics).map((source) =>
      `${source.name}: ${source.views.toLocaleString("en-US")} views, ${source.sales.toLocaleString("en-US")} sales, ${formatPercent(source.conversion)} conversion, ${formatCurrency(source.revenueCents, product.currency)} revenue, AOV ${formatCurrency(source.averageOrderCents, product.currency)}`
    );

    return `Analyze traffic source performance for ${productName} over the ${range}. Use the current source sort (${state.sourceSort}) and these rows: ${joinPromptItems(rows)}. Compare source quality, conversion, revenue concentration, and recommend one source test the merchant can run.`;
  }

  if (sectionId === "churn-panel") {
    const dashboard = buildSalesDashboard(product, metrics);
    const examples = buildAgentAnswerExamples(product, metrics, dashboard);
    const rows = [
      `Churn rate ${formatPercent(dashboard.churn.rate)}`,
      `Last period ${formatPercent(dashboard.churn.previousRate)}`,
      `${dashboard.churn.canceled.toLocaleString("en-US")} churned users`,
      `${formatCurrency(dashboard.churn.revenueLostCents, product.currency)} revenue lost`,
      `Formula ${dashboard.churn.formula}`,
    ];

    return `Analyze subscription health for ${productName} over the ${range}. Pull the churn panel data into the answer: ${joinPromptItems(rows)}. Use this answer-style example for churn/refund context: "${examples.churn}" Explain whether churn risk is getting better or worse and suggest one retention action the merchant can apply.`;
  }

  if (sectionId === "locations-panel") {
    const dashboard = buildSalesDashboard(product, metrics);
    const examples = buildAgentAnswerExamples(product, metrics, dashboard);
    const scopeLabel = state.locationScope === "us" ? "United States" : "World";
    const locations = sortByDirection(
      state.locationScope === "us" ? dashboard.usLocations : dashboard.locations,
      (location) => location.revenueCents,
      state.locationSortDirection
    ).map((location) =>
      `${location.country}, ${location.region}: ${location.views.toLocaleString("en-US")} views, ${location.sales.toLocaleString("en-US")} sales, ${formatCurrency(location.revenueCents, product.currency)} revenue`
    );

    return `Analyze where buyers are coming from for ${productName} over the ${range}. Use the current geography scope (${scopeLabel}) and these buyer-location rows: ${joinPromptItems(locations)}. Use this answer-style example when comparing locations to another signal: "${examples.locations}" Summarize the strongest geographies, weak-but-interesting regions, and one next action.`;
  }

  if (sectionId === "utm-panel") {
    const dashboard = buildSalesDashboard(product, metrics);
    const examples = buildAgentAnswerExamples(product, metrics, dashboard);
    const rows = dashboard.utmLinks.map((link) =>
      `${link.campaign} (${link.source}/${link.medium}): ${link.clicks.toLocaleString("en-US")} clicks, ${link.sales.toLocaleString("en-US")} sales, ${formatPercent(link.conversion)} conversion, ${formatCurrency(link.revenueCents, product.currency)} revenue`
    );

    return `Analyze tracked campaign performance for ${productName} over the ${range}. Use these UTM rows: ${joinPromptItems(rows)}. Use this answer-style example for attribution cleanup: "${examples.utm}" Compare attribution quality and identify which campaign deserves another test or automation.`;
  }

  if (sectionId === "export-panel") {
    return `Explain the customer sales CSV export for ${productName} over the ${range}. Describe which fields matter, how the one-day buffer should be interpreted, and which follow-up actions this export should drive.`;
  }

  return "";
}

function buildMerchantPrompt(promptKey, detail = {}) {
  const product = getSelectedProduct();
  const metrics = buildProductMetrics(product);
  const range = getRangeLabel();
  const productName = product.name;
  const answerExamples = buildAgentAnswerExamples(product, metrics);

  const prompts = {
    performance: `Explain what the Recent signal section is for ${productName} over the ${range}. Tell me how to interpret revenue, views, conversion, refund rate, and signal confidence before I decide on a next move. Use this answer-style example when explaining conversion: "${answerExamples.conversions}"`,
    refunds: `Explain what the Refund Ops section is for ${productName} over the ${range}. Walk me through Prevent, Resolve, and Dispute mode, what the risk scores mean, and what action should happen next.`,
    content: `Explain what the Content Radar section is for ${productName} over the ${range}. Describe how to read the trend fit, recommended channel, KPI baseline/target, evidence, and risks before creating a tracked campaign.`,
    retention: `Explain what the Retention Saver section is for ${productName} over the ${range}. Show how to interpret churn, lost revenue, save-rate assumptions, pause offers, and retention automations.`,
    admin: `Explain what the Admin Actions section is for ${productName}. Describe how to interpret reads, writes, preflight checks, audit notes, and execution modes.`,
    qa: `Explain what the Shortest QA section is for the Gumroad Merchant demo. Describe how to interpret suites, scenarios, assertions, pass/fail evidence, and automation coverage.`,
    sources: `Explain what the traffic-source section is for ${productName} over the ${range}. Show how to compare views, sales, conversion, revenue, and source quality before choosing a next test.`,
    suggestions: `Explain what the Suggested next moves section is for ${productName} over the ${range}. Show how to read confidence, rationale, evidence, and what actions the agent can stage or apply locally.`,
    churn: `Explain what the Subscription health section is for ${productName} over the ${range}. Show how to interpret churn rate, churned users, revenue lost, and retention risk. Use this answer-style example for churn/refund context: "${answerExamples.churn}"`,
    export: `Explain what the synthetic customer sales CSV section is for ${productName}. Show how to interpret the export fields, why the one-day buffer matters, and what actions the export should trigger.`,
  };

  if (detail.prompt) return detail.prompt;
  if (detail.subsectionLabel && detail.sectionId) {
    const sectionPrompt = buildSectionPrompt(detail.sectionId, product, metrics, range);
    if (sectionPrompt) {
      return `${sectionPrompt} Focus specifically on the "${detail.subsectionLabel}" subsection and connect its visible context (${detail.label ?? "current visible values"}) to the section data.`;
    }
  }
  if (detail.sectionId) {
    const sectionPrompt = buildSectionPrompt(detail.sectionId, product, metrics, range);
    if (sectionPrompt) return sectionPrompt;
  }
  if (detail.subsectionLabel) {
    return `Explain the "${detail.subsectionLabel}" part of the ${detail.sectionLabel ?? promptKey} section for ${productName} over the ${range}. Analyze the current data shown here: ${detail.label ?? "the visible card values"}. Tell me what it means, why it matters, and one follow-up action.`;
  }
  if (detail.metricLabel) {
    return `Explain the ${detail.metricLabel} metric for ${productName} over the ${range}. Current value: ${detail.metricValue}. Context: ${detail.metricChange}. What should I do next?`;
  }
  if (detail.sourceName) {
    return `Explain the ${detail.sourceName} traffic source for ${productName}. Compare its views, sales, conversion, and revenue, then suggest one follow-up test.`;
  }
  if (detail.label) {
    return `Explain this ${detail.type ?? "signal"} for ${productName}: ${detail.label}. Cite the evidence and suggest the next action.`;
  }

  return prompts[promptKey] ?? prompts.performance;
}

function renderMiniAgentButton(promptKey, detail = {}) {
  const prompt = buildMerchantPrompt(promptKey, detail);
  const label = detail.subsectionLabel || detail.metricLabel || detail.label || "this data";

  return `
    <button
      class="mini-agent-button"
      type="button"
      data-merchant-prompt="${escapeHtml(prompt)}"
      aria-label="Ask Agent to explain ${escapeHtml(label)}"
      title="Ask Agent to explain this data"
    >
      <span aria-hidden="true">?</span>
    </button>
  `;
}

function buildMerchantFollowups(message) {
  const product = getSelectedProduct();
  const productName = product.name;
  const portfolioPrompt =
    state.selectedProductId === "all"
      ? "Break down my products and explain why some are selling better than others."
      : `Compare ${productName} against the rest of my products and explain why it is selling better or worse.`;
  const normalized = String(message ?? "").toLowerCase();

  const shared = [
    portfolioPrompt,
    `Compare the traffic sources for ${productName} and tell me which one deserves the next test.`,
    `Find the biggest conversion, refund, or churn issue for ${productName} in this date range.`,
  ];

  if (normalized.includes("refund") || normalized.includes("chargeback")) {
    return [
      `Which refund case should I resolve first for ${productName}?`,
      `Draft the buyer reply and show the next send step.`,
      shared[0],
    ];
  }

  if (normalized.includes("content") || normalized.includes("campaign") || normalized.includes("utm")) {
    return [
      `Turn this into a one-week content test for ${productName}.`,
      `Draft the UTM plan and success metric for the strongest current campaign idea.`,
      shared[1],
    ];
  }

  if (normalized.includes("retention") || normalized.includes("churn") || normalized.includes("pause")) {
    return [
      `Which churn signal matters most for ${productName}?`,
      `Draft a pause-before-cancel offer I can apply or schedule.`,
      shared[0],
    ];
  }

  if (normalized.includes("admin") || normalized.includes("cli") || normalized.includes("command")) {
    return [
      `Show the preflight checks before this admin action.`,
      `Explain the required permission and next execution step.`,
      shared[1],
    ];
  }

  if (normalized.includes("qa") || normalized.includes("test")) {
    return [
      `Generate the shortest judge demo path.`,
      `Write the pass/fail assertions for this lane.`,
      shared[2],
    ];
  }

  return shared;
}

function stageMerchantPrompt(message) {
  const prompt = String(message ?? "").trim();

  if (!prompt) {
    return;
  }

  activatePanelById("merchant-panel");

  if (merchantPanel?.classList.contains("is-collapsed")) {
    toggleSignalPanel(merchantPanel, true);
  }

  merchantChatInput.value = prompt;
  merchantChatSubmit.disabled = false;
  merchantStatus.textContent = "Staged";
  window.clearTimeout(stagedPromptTimer);
  stagedPromptTimer = window.setTimeout(() => {
    if (merchantStatus.textContent === "Staged") {
      merchantStatus.textContent = state.merchantSessionId ? "Ready" : "Local";
    }
  }, 1800);
  document.querySelector(".merchant-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  merchantChatInput.focus({ preventScroll: true });
}

function toggleSignalPanel(panel, forceExpanded) {
  const isExpanded = forceExpanded ?? !panel.classList.contains("is-expanded");
  const body = panel.querySelector(":scope > .signal-panel-body");
  const toggle = panel.querySelector("[data-signal-toggle]");

  panel.classList.toggle("is-expanded", isExpanded);
  panel.classList.toggle("is-collapsed", !isExpanded);

  if (body) {
    body.hidden = !isExpanded;
  }
  if (toggle) {
    toggle.setAttribute("aria-expanded", String(isExpanded));
    toggle.setAttribute("aria-label", isExpanded ? "Collapse section" : "Open section");
    toggle.innerHTML = `
      <span class="toggle-glyph" aria-hidden="true"></span>
      <span>${isExpanded ? "Collapse" : "Open"}</span>
    `;
  }
}

function renderSectionAgentButton(promptKey, sectionId = "") {
  if (!promptKey) return "";

  return `
    <button
      class="section-agent-button"
      type="button"
      data-merchant-prompt-key="${escapeHtml(promptKey)}"
      ${sectionId ? `data-merchant-section-id="${escapeHtml(sectionId)}"` : ""}
      aria-label="Ask Agent about this section"
      title="Ask Agent about this section"
    >
      <span class="section-agent-icon" aria-hidden="true">?</span>
    </button>
  `;
}

function setupSignalAccordions() {
  signalPanelConfigs.forEach((config) => {
    const panel = document.querySelector(config.selector);

    if (!panel || panel.dataset.signalPanelReady === "true") {
      return;
    }

    const header = panel.querySelector(":scope > .panel-header")
      ?? panel.querySelector(":scope > .source-title-row")
      ?? panel.querySelector(":scope > .detail-header");

    if (!header) {
      return;
    }

    const body = document.createElement("div");
    body.className = "signal-panel-body";
    while (header.nextSibling) {
      body.append(header.nextSibling);
    }
    panel.append(body);

    const controlsMarkup = config.showPrompt !== false ? renderSectionAgentButton(config.promptKey, config.id) : "";

    if (controlsMarkup) {
      const controls = document.createElement("div");
      controls.className = "signal-panel-controls";
      controls.innerHTML = controlsMarkup;
      header.append(controls);
    }
    header.classList.add("signal-panel-header");
    panel.classList.add("signal-panel");
    panel.dataset.signalPanelReady = "true";
    if (config.promptKey) {
      panel.dataset.promptKey = config.promptKey;
    }

    if (!config.lockOpen) {
      header.addEventListener("click", (event) => {
        if (event.target.closest("button, a, select, input, textarea, label")) {
          return;
        }
        toggleSignalPanel(panel);
      });
    }

    toggleSignalPanel(panel, config.lockOpen ? true : Boolean(config.defaultOpen));
  });
}

function panelTabForTarget(targetId) {
  return [...document.querySelectorAll("[data-panel-target]")].find(
    (button) => button.dataset.panelTarget === targetId
  );
}

function activatePanelById(targetId) {
  const button = panelTabForTarget(targetId);
  const group = button?.closest("[data-panel-group]");

  if (!button || !group) {
    return false;
  }

  setDashboardGroupCollapsed(group, false);
  setPanelGroupActive(group, targetId);
  return true;
}

function revealDashboardTarget(targetOrSelector) {
  const target =
    typeof targetOrSelector === "string"
      ? document.querySelector(targetOrSelector)
      : targetOrSelector;

  if (!target) {
    return null;
  }

  let panel = target;
  while (panel && panel !== document.body) {
    if (panel.id && activatePanelById(panel.id)) {
      break;
    }
    panel = panel.parentElement;
  }

  return target;
}

function setPanelGroupActive(group, targetId) {
  const buttons = [...group.querySelectorAll("[data-panel-target]")];
  const targetIds = buttons.map((button) => button.dataset.panelTarget).filter(Boolean);

  buttons.forEach((button) => {
    const isActive = button.dataset.panelTarget === targetId;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
    button.setAttribute("tabindex", isActive ? "0" : "-1");
  });

  targetIds.forEach((id) => {
    const panel = document.getElementById(id);

    if (!panel) {
      return;
    }

    const isActive = id === targetId;
    panel.hidden = !isActive;
    panel.setAttribute("role", "tabpanel");

    const tab = panelTabForTarget(id);
    if (tab) {
      tab.id = tab.id || `${group.id || group.dataset.panelGroup}-${id}-tab`;
      panel.setAttribute("aria-labelledby", tab.id);
    }

    if (isActive && panel.classList.contains("signal-panel")) {
      toggleSignalPanel(panel, true);
    }
  });
}

function dashboardGroupTitle(group) {
  return group.querySelector(":scope > .dashboard-group-header h2")?.textContent?.trim()
    ?? group.getAttribute("aria-label")
    ?? "Dashboard group";
}

function setDashboardGroupCollapsed(group, collapsed) {
  const shell = group.querySelector(":scope > .panel-group-shell");
  const toggle = group.querySelector("[data-dashboard-group-toggle]");
  const header = group.querySelector(":scope > .dashboard-group-header");
  const label = dashboardGroupTitle(group);

  group.classList.toggle("is-group-collapsed", collapsed);

  if (shell) {
    shell.hidden = collapsed;
  }

  if (toggle) {
    const actionLabel = `${collapsed ? "Open" : "Collapse"} ${label}`;
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute("aria-label", actionLabel);
    toggle.title = actionLabel;
  }

  if (header) {
    header.title = `${collapsed ? "Open" : "Collapse"} ${label}`;
  }
}

function setupDashboardGroupToggle(group) {
  const header = group.querySelector(":scope > .dashboard-group-header");
  const shell = group.querySelector(":scope > .panel-group-shell");

  if (
    group.dataset.groupCollapsible === "false" ||
    !header ||
    !shell ||
    header.querySelector("[data-dashboard-group-toggle]")
  ) {
    return;
  }

  shell.id = shell.id || `${group.id || group.dataset.panelGroup}-body`;

  const toggle = document.createElement("button");
  toggle.className = "dashboard-group-toggle";
  toggle.type = "button";
  toggle.dataset.dashboardGroupToggle = "";
  toggle.setAttribute("aria-controls", shell.id);
  toggle.innerHTML = `
    <span class="toggle-glyph" aria-hidden="true"></span>
  `;
  const actionSlot = header.querySelector(":scope > .merchant-panel-actions");
  (actionSlot ?? header).append(toggle);
  header.classList.add("is-toggleable");
  header.setAttribute("aria-controls", shell.id);

  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDashboardGroupCollapsed(group, !group.classList.contains("is-group-collapsed"));
  });

  header.addEventListener("click", (event) => {
    if (event.target.closest("button, a, select, input, textarea, label, [role='tab']")) {
      return;
    }

    setDashboardGroupCollapsed(group, !group.classList.contains("is-group-collapsed"));
  });

  setDashboardGroupCollapsed(group, group.classList.contains("is-group-collapsed"));
}

function setupPanelGroups() {
  document.querySelectorAll("[data-panel-group]").forEach((group) => {
    if (group.dataset.panelGroupReady === "true") {
      return;
    }

    setupDashboardGroupToggle(group);

    const buttons = [...group.querySelectorAll("[data-panel-target]")];

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        setPanelGroupActive(group, button.dataset.panelTarget);
      });
    });

    const requestedDefault =
      buttons.find((button) => button.classList.contains("active"))?.dataset.panelTarget ??
      group.dataset.panelDefault ??
      buttons[0]?.dataset.panelTarget;

    if (requestedDefault) {
      setPanelGroupActive(group, requestedDefault);
    }

    group.dataset.panelGroupReady = "true";
  });
}

function promptKeyForElement(element) {
  const panel = element.closest("[data-prompt-key], .signal-panel");
  return panel?.dataset.promptKey ?? "performance";
}

function decorateSubsectionAgentButtons() {
  const targets = document.querySelectorAll(
    ".refund-section-heading, .detail-header:not(.signal-panel-header), .ops-detail-header"
  );

  targets.forEach((target) => {
    if (target.closest("#refund-ops-panel")) {
      return;
    }

    if (target.closest(".merchant-message") || target.querySelector(":scope > .mini-agent-button")) {
      return;
    }

    const heading =
      target.querySelector("h3") ??
      target.querySelector("span:first-child") ??
      target.querySelector(".eyebrow");
    const label = heading?.textContent?.trim();

    if (!label) {
      return;
    }

    const promptKey = promptKeyForElement(target);
    const button = document.createElement("button");
    button.className = "mini-agent-button inline-mini-agent-button";
    button.type = "button";
    button.dataset.merchantPrompt = buildMerchantPrompt(promptKey, {
      sectionId: target.closest(".signal-panel")?.id ?? "",
      sectionLabel: target.closest(".signal-panel")?.querySelector(".signal-panel-header h2, .signal-panel-header h3")?.textContent?.trim() ?? promptKey,
      subsectionLabel: label,
      label: target.textContent.trim().replace(/\s+/g, " "),
    });
    button.setAttribute("aria-label", `Ask Agent to explain ${label}`);
    button.title = "Ask Agent to explain this section";
    button.innerHTML = `<span aria-hidden="true">?</span>`;
    target.append(button);
  });
}

function renderProductOptions() {
  const options = [
    { id: "all", name: "All products" },
    ...products.map((product) => ({ id: product.id, name: product.name })),
  ];
  productSelect.innerHTML = options
    .map((product) => `<option value="${product.id}">${product.name}</option>`)
    .join("");
  productSelect.value = state.selectedProductId;
}

function renderPeriodSummary() {
  if (dateRangeSelect) {
    dateRangeSelect.value = state.dateRange;
  }

  if (customStartDate) {
    customStartDate.value = state.customStartDate;
  }

  if (customEndDate) {
    customEndDate.value = state.customEndDate;
  }

  if (chartRangeSelect) {
    chartRangeSelect.value = state.dateRange;
  }

  if (churnRangeBadge) {
    churnRangeBadge.textContent = getChurnRangeBadgeLabel();
  }
}

function renderProductHeader(product) {
  if (dataSourceNote) {
    const campaignCount = state.analyticsSource.trackedCampaignCount;
    dataSourceNote.textContent = campaignCount > 0
      ? `${state.analyticsSource.label} · ${campaignCount} tracked campaign${campaignCount === 1 ? "" : "s"}`
      : state.analyticsSource.label;
  }

  if (!productName || !productDescription || !productTags) {
    return;
  }

  productName.textContent = product.name;
  productDescription.textContent = product.description;
  productTags.innerHTML = product.tags
    .map((tag) => {
      const tagName = String(tag);
      const shortcut = dashboardShortcuts[tagName];

      if (!shortcut) {
        return `<span class="tag">${escapeHtml(tagName)}</span>`;
      }

      return `
        <button class="tag tag-button" type="button" data-dashboard-shortcut="${escapeHtml(tagName)}">
          ${escapeHtml(tagName)}
        </button>
      `;
    })
    .join("");
}

const ESTIMATED_PAYOUT_FEE_RATE = 0.1;

function estimatePayoutCents(metrics, period = "current") {
  const revenueCents =
    period === "previous" ? metrics.previousRevenueCents : metrics.currentRevenueCents;
  const refundCents =
    period === "previous" ? metrics.previousRefundCents : metrics.currentRefundCents;
  const netBeforeFees = Math.max(0, revenueCents - refundCents);

  return Math.round(netBeforeFees * (1 - ESTIMATED_PAYOUT_FEE_RATE));
}

function percentChange(current, previous) {
  if (previous > 0) return (current - previous) / previous;
  return current > 0 ? 1 : 0;
}

function renderMetrics(product, metrics) {
  const currentPayoutCents = estimatePayoutCents(metrics);
  const previousPayoutCents = estimatePayoutCents(metrics, "previous");
  const payoutDeltaPercent = percentChange(currentPayoutCents, previousPayoutCents);
  const cards = [
    {
      label: "Revenue",
      value: formatCurrency(metrics.currentRevenueCents, product.currency),
      change: formatDelta(metrics.revenueDeltaPercent, "prior period"),
    },
    {
      label: "Payout",
      value: formatCurrency(currentPayoutCents, product.currency),
      change: formatDelta(payoutDeltaPercent, "prior payout"),
      tone: currentPayoutCents >= previousPayoutCents ? "good" : "warn",
    },
    {
      label: "Sales",
      value: metrics.currentSales.toLocaleString(),
      change: formatDelta(metrics.salesDeltaPercent, "prior period"),
    },
    {
      label: "Views",
      value: metrics.currentViews.toLocaleString(),
      change: formatDelta(metrics.viewsDeltaPercent, "prior period"),
    },
    {
      label: "Conversion",
      value: formatPercent(metrics.currentConversion),
      change: `Prior ${formatPercent(metrics.previousConversion)}`,
      tone: metrics.currentConversion >= metrics.previousConversion ? "good" : "warn",
    },
    {
      label: "Refund rate",
      value: formatPercent(metrics.currentRefundRate),
      change: `${metrics.currentRefunds} refunds this period`,
      tone: metrics.currentRefundRate > metrics.previousRefundRate ? "warn" : "good",
    },
  ];

  metricGrid.innerHTML = cards
    .map((card, index) => {
      const tone = card.tone ?? deltaTone(card.change);

      return `
        <article class="metric-card ${tone}" style="--index: ${index}">
          <div class="metric-label">${card.label}</div>
          <div class="metric-value">${card.value}</div>
          <div class="metric-change ${tone}">${card.change}</div>
        </article>
      `;
    })
    .join("");
}

function clampNumber(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

const productImagePalettes = [
  ["#F883E1", "#ffc900", "#211817"],
  ["#23a093", "#fff7ec", "#211817"],
  ["#315bb3", "#F883E1", "#fffdf8"],
  ["#ffc900", "#3b1930", "#fffdf8"],
];

function portfolioProductViews() {
  return products.map((product) =>
    applyDateRange(product, state.dateRange, {
      customDays: getRangeDays(),
    })
  );
}

function ensureActivePortfolioProduct(productViews) {
  if (!productViews.length) {
    state.activePortfolioProductId = "";
    return null;
  }

  const activeProduct =
    productViews.find((product) => product.id === state.activePortfolioProductId) ?? productViews[0];
  state.activePortfolioProductId = activeProduct.id;
  return activeProduct;
}

function productInitials(name) {
  const initials = String(name ?? "")
    .split(/\s+/)
    .map((part) => part.match(/[a-z0-9]/i)?.[0] ?? "")
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return initials || "G";
}

function escapeSvgText(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function productImageDataUri(product, index) {
  const [primary, secondary, text] = productImagePalettes[index % productImagePalettes.length];
  const category = product.category || "Digital product";
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="760" height="520" viewBox="0 0 760 520">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="${primary}"/>
          <stop offset="100%" stop-color="${secondary}"/>
        </linearGradient>
        <pattern id="grid" width="34" height="34" patternUnits="userSpaceOnUse">
          <path d="M34 0H0V34" fill="none" stroke="rgba(33,24,23,.18)" stroke-width="2"/>
        </pattern>
      </defs>
      <rect width="760" height="520" rx="38" fill="url(#bg)"/>
      <rect width="760" height="520" rx="38" fill="url(#grid)"/>
      <circle cx="642" cy="92" r="78" fill="rgba(255,253,248,.3)"/>
      <circle cx="114" cy="420" r="118" fill="rgba(255,253,248,.24)"/>
      <rect x="74" y="78" width="612" height="364" rx="28" fill="rgba(255,253,248,.76)" stroke="#211817" stroke-width="5"/>
      <text x="110" y="168" fill="${text}" font-family="Avenir Next, Helvetica, Arial, sans-serif" font-size="34" font-weight="900">${escapeSvgText(category)}</text>
      <text x="110" y="292" fill="${text}" font-family="Avenir Next, Helvetica, Arial, sans-serif" font-size="122" font-weight="950" letter-spacing="2">${escapeSvgText(productInitials(product.name))}</text>
      <text x="110" y="358" fill="${text}" font-family="Avenir Next, Helvetica, Arial, sans-serif" font-size="36" font-weight="850">${escapeSvgText(formatCurrency(product.priceCents, product.currency))}</text>
      <rect x="500" y="308" width="116" height="42" rx="21" fill="#211817"/>
      <text x="558" y="337" text-anchor="middle" fill="#fffdf8" font-family="Avenir Next, Helvetica, Arial, sans-serif" font-size="18" font-weight="900">GUMROAD</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function rankLabel(rank) {
  if (rank % 100 >= 11 && rank % 100 <= 13) return `${rank}th`;
  const suffix = rank % 10 === 1 ? "st" : rank % 10 === 2 ? "nd" : rank % 10 === 3 ? "rd" : "th";
  return `${rank}${suffix}`;
}

function renderPortfolioProgressRows(rows) {
  return rows
    .map((row) => {
      const width = clampNumber(row.percent, 0, 100);
      return `
        <div class="portfolio-progress-row">
          <div>
            <span>${escapeHtml(row.label)}</span>
            <strong>${escapeHtml(row.value)}</strong>
          </div>
          <p>${escapeHtml(row.note)}</p>
          <span class="portfolio-progress-track" aria-hidden="true">
            <span style="width: ${width}%"></span>
          </span>
        </div>
      `;
    })
    .join("");
}

function renderProductPortfolio() {
  if (!portfolioTabs || !portfolioDetail) {
    return;
  }

  const productViews = portfolioProductViews();
  const activeProduct = ensureActivePortfolioProduct(productViews);

  if (!activeProduct) {
    portfolioTabs.innerHTML = "";
    portfolioDetail.innerHTML = `<p class="muted-copy">No products available in this demo dataset.</p>`;
    return;
  }

  const productModels = productViews.map((product, index) => ({
    product,
    index,
    metrics: buildProductMetrics(product),
  }));
  const activeModel = productModels.find(({ product }) => product.id === activeProduct.id) ?? productModels[0];
  const activeMetrics = activeModel.metrics;
  const totalRevenue = Math.max(
    productModels.reduce((sum, item) => sum + item.metrics.currentRevenueCents, 0),
    1
  );
  const totalViews = Math.max(
    productModels.reduce((sum, item) => sum + item.metrics.currentViews, 0),
    1
  );
  const maxRevenue = Math.max(...productModels.map((item) => item.metrics.currentRevenueCents), 1);
  const maxConversion = Math.max(...productModels.map((item) => item.metrics.currentConversion), 0.01);
  const averageConversion =
    productModels.reduce((sum, item) => sum + item.metrics.currentConversion, 0) / productModels.length;
  const revenueRank =
    [...productModels]
      .sort((left, right) => right.metrics.currentRevenueCents - left.metrics.currentRevenueCents)
      .findIndex(({ product }) => product.id === activeProduct.id) + 1;
  const topSource = activeMetrics.topSource;
  const discoverShare =
    activeMetrics.currentViews > 0 ? activeMetrics.discoverImpressions / activeMetrics.currentViews : 0;
  const revenueShare = activeMetrics.currentRevenueCents / totalRevenue;
  const viewShare = activeMetrics.currentViews / totalViews;
  const portfolioPrompt = `Analyze ${activeProduct.name} for ${getRangeLabel()}: revenue ${formatCurrency(activeMetrics.currentRevenueCents, activeProduct.currency)}, ${activeMetrics.currentSales.toLocaleString("en-US")} sales, ${formatPercent(activeMetrics.currentConversion)} conversion, ${formatPercent(activeMetrics.currentRefundRate)} refund rate. Compare it against the rest of the product portfolio and suggest actionable next steps.`;
  const statCards = [
    {
      label: "Revenue",
      value: formatCurrency(activeMetrics.currentRevenueCents, activeProduct.currency),
      note: formatDelta(activeMetrics.revenueDeltaPercent, "prior period"),
      tone: activeMetrics.revenueDeltaPercent >= 0 ? "good" : "warn",
    },
    {
      label: "Sales",
      value: activeMetrics.currentSales.toLocaleString("en-US"),
      note: `${rankLabel(revenueRank)} by revenue`,
      tone: revenueRank === 1 ? "good" : "",
    },
    {
      label: "Conversion",
      value: formatPercent(activeMetrics.currentConversion),
      note: `${formatPercent(activeMetrics.currentConversion - averageConversion)} vs portfolio avg`,
      tone: activeMetrics.currentConversion >= averageConversion ? "good" : "warn",
    },
    {
      label: "Refunds",
      value: formatPercent(activeMetrics.currentRefundRate),
      note: `${activeMetrics.currentRefunds.toLocaleString("en-US")} refund${activeMetrics.currentRefunds === 1 ? "" : "s"} in range`,
      tone: activeMetrics.currentRefundRate <= activeMetrics.previousRefundRate ? "good" : "warn",
    },
  ];
  const progressRows = [
    {
      label: "Portfolio revenue share",
      value: formatPercent(revenueShare),
      note: `${formatCurrency(activeMetrics.currentRevenueCents, activeProduct.currency)} of current portfolio revenue.`,
      percent: revenueShare * 100,
    },
    {
      label: "Portfolio view share",
      value: formatPercent(viewShare),
      note: `${activeMetrics.currentViews.toLocaleString("en-US")} views inside the selected range.`,
      percent: viewShare * 100,
    },
    {
      label: "Conversion strength",
      value: formatPercent(activeMetrics.currentConversion),
      note: `Portfolio average is ${formatPercent(averageConversion)}.`,
      percent: (activeMetrics.currentConversion / maxConversion) * 100,
    },
    {
      label: "Discover reach",
      value: `${activeMetrics.discoverImpressions.toLocaleString("en-US")} impressions`,
      note: topSource
        ? `${topSource.name} is the current top revenue source.`
        : `${Math.round(discoverShare * 100)}% of views came through Discover.`,
      percent: discoverShare * 100,
    },
  ];

  portfolioTabs.innerHTML = productModels
    .map(({ product, metrics, index }) => {
      const active = product.id === activeProduct.id;
      return `
        <button
          class="portfolio-tab ${active ? "active" : ""}"
          type="button"
          role="tab"
          aria-selected="${active ? "true" : "false"}"
          data-portfolio-product-id="${escapeHtml(product.id)}"
        >
          <img src="${escapeHtml(productImageDataUri(product, index))}" alt="" aria-hidden="true" />
          <span>
            <strong>${escapeHtml(product.name)}</strong>
            <small>${escapeHtml(product.category || "Digital product")} · ${formatCurrency(metrics.currentRevenueCents, product.currency)}</small>
          </span>
        </button>
      `;
    })
    .join("");

  portfolioDetail.innerHTML = `
    <article class="portfolio-focus-card">
      <div class="portfolio-product-image">
        <img src="${escapeHtml(productImageDataUri(activeProduct, activeModel.index))}" alt="${escapeHtml(activeProduct.name)} product preview" />
      </div>
      <div class="portfolio-product-copy">
        <p class="eyebrow">Monthly overview · ${escapeHtml(getChurnRangeBadgeLabel())}</p>
        <h3>${escapeHtml(activeProduct.name)}</h3>
        <p>${escapeHtml(activeProduct.description)}</p>
        <div class="portfolio-meta-row">
          <span>${escapeHtml(activeProduct.creator)}</span>
          <span>${escapeHtml(activeProduct.category || "Digital product")}</span>
          <span>${formatCurrency(activeProduct.priceCents, activeProduct.currency)}</span>
          <span>${Number(activeProduct.rating ?? 0).toFixed(1)} stars · ${Number(activeProduct.reviewCount ?? 0).toLocaleString("en-US")} reviews</span>
        </div>
        <div class="portfolio-action-row">
          <button class="secondary-button" type="button" data-merchant-prompt="${escapeHtml(portfolioPrompt)}">Ask Merchant</button>
          <span>${rankLabel(revenueRank)} by revenue in this product set</span>
        </div>
      </div>
    </article>

    <div class="portfolio-stat-grid">
      ${statCards
        .map((card) => `
          <article class="portfolio-stat ${card.tone}">
            <span>${escapeHtml(card.label)}</span>
            <strong>${escapeHtml(card.value)}</strong>
            <small>${escapeHtml(card.note)}</small>
          </article>
        `)
        .join("")}
    </div>

    <section class="portfolio-readout">
      <div>
        <p class="eyebrow">Product read</p>
        <h3>${escapeHtml(activeProduct.name)} in context</h3>
        <p>
          ${escapeHtml(activeProduct.name)} contributes ${formatPercent(revenueShare)} of portfolio revenue and ${formatPercent(viewShare)} of portfolio views for ${escapeHtml(getRangeLabel())}. Conversion is ${activeMetrics.currentConversion >= averageConversion ? "above" : "below"} the product average, so the next move should compare traffic quality against refund pressure before scaling.
        </p>
      </div>
      <div class="portfolio-progress-list">
        ${renderPortfolioProgressRows(progressRows)}
      </div>
    </section>

    <section class="portfolio-comparison-list" aria-label="All product comparison">
      ${productModels
        .sort((left, right) => right.metrics.currentRevenueCents - left.metrics.currentRevenueCents)
        .map(({ product, metrics, index }) => {
          const active = product.id === activeProduct.id;
          const width = (metrics.currentRevenueCents / maxRevenue) * 100;
          return `
            <article class="portfolio-compare-row ${active ? "active" : ""}">
              <img src="${escapeHtml(productImageDataUri(product, index))}" alt="" aria-hidden="true" />
              <div>
                <strong>${escapeHtml(product.name)}</strong>
                <span>${metrics.currentSales.toLocaleString("en-US")} sales · ${formatPercent(metrics.currentConversion)} conversion · ${formatPercent(metrics.currentRefundRate)} refunds</span>
              </div>
              <strong>${formatCurrency(metrics.currentRevenueCents, product.currency)}</strong>
              <span class="portfolio-row-track" aria-hidden="true">
                <span style="width: ${clampNumber(width, 4, 100)}%"></span>
              </span>
            </article>
          `;
        })
        .join("")}
    </section>
  `;
}

const trendChartMetrics = {
  revenue: {
    label: "Revenue",
    axisLabel: "Daily revenue",
    kind: "currency",
    normalizeByDay: true,
  },
  payout: {
    label: "Payout",
    axisLabel: "Daily estimated payout",
    kind: "currency",
    normalizeByDay: true,
  },
  sales: {
    label: "Sales",
    axisLabel: "Daily sales",
    kind: "number",
    normalizeByDay: true,
  },
  conversion: {
    label: "Conversion",
    axisLabel: "Conversion rate",
    kind: "percent",
    normalizeByDay: false,
  },
  views: {
    label: "Views",
    axisLabel: "Daily views",
    kind: "number",
    normalizeByDay: true,
  },
  refundRate: {
    label: "Refunds",
    axisLabel: "Refund rate",
    kind: "percent",
    normalizeByDay: false,
  },
};

const trendChartPalette = [
  "#F883E1",
  "#23a093",
  "#7ca4ff",
  "#ffc900",
  "#b891ff",
  "#ff7a59",
];

function getTrendMetricConfig() {
  if (!trendChartMetrics[state.activeTrendMetric]) {
    state.activeTrendMetric = "revenue";
  }

  return trendChartMetrics[state.activeTrendMetric];
}

function getTrendMetricValue(metrics, metricKey, period) {
  const isPrevious = period === "previous";

  if (metricKey === "revenue") {
    return isPrevious ? metrics.previousRevenueCents : metrics.currentRevenueCents;
  }

  if (metricKey === "payout") {
    return estimatePayoutCents(metrics, period);
  }

  if (metricKey === "sales") {
    return isPrevious ? metrics.previousSales : metrics.currentSales;
  }

  if (metricKey === "conversion") {
    return isPrevious ? metrics.previousConversion : metrics.currentConversion;
  }

  if (metricKey === "views") {
    return isPrevious ? metrics.previousViews : metrics.currentViews;
  }

  if (metricKey === "refundRate") {
    return isPrevious ? metrics.previousRefundRate : metrics.currentRefundRate;
  }

  return 0;
}

function getTrendDisplayValue(metrics, metricKey, period, days) {
  const config = trendChartMetrics[metricKey] ?? trendChartMetrics.revenue;
  const value = getTrendMetricValue(metrics, metricKey, period);

  return config.normalizeByDay ? value / Math.max(days, 1) : value;
}

function getTrendPointCount(days) {
  if (days <= 30) return 12;
  if (days <= 90) return 14;
  return 16;
}

function getTrendDateBounds() {
  normalizeCustomDateRange();

  const start = parseDateInput(state.customStartDate) ?? parseDateInput(defaultCustomStartDate);
  const end = parseDateInput(state.customEndDate) ?? parseDateInput(defaultCustomEndDate);

  return { start, end };
}

function dateAtTrendPoint(start, end, pointIndex, pointCount) {
  const ratio = pointCount <= 1 ? 1 : pointIndex / (pointCount - 1);
  const dateTime = start.getTime() + (end.getTime() - start.getTime()) * ratio;

  return new Date(dateTime);
}

function formatTrendDateLabel(date, start, end) {
  const crossesYears = start.getUTCFullYear() !== end.getUTCFullYear();
  const label = new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    month: "short",
    day: "numeric",
    year: crossesYears ? "2-digit" : undefined,
  }).format(date);

  return crossesYears ? label.replace(", ", " '") : label;
}

function buildTrendDateTicks(pointCount) {
  const { start, end } = getTrendDateBounds();
  const candidates = [
    { index: 0 },
    { index: Math.floor((pointCount - 1) / 2) },
    { index: pointCount - 1 },
  ];
  const usedIndexes = new Set();

  return candidates
    .filter((tick) => {
      if (usedIndexes.has(tick.index)) return false;
      usedIndexes.add(tick.index);
      return true;
    })
    .map((tick) => {
      const date = dateAtTrendPoint(start, end, tick.index, pointCount);

      return {
        index: tick.index,
        label: formatTrendDateLabel(date, start, end),
      };
    });
}

function buildTrendPoints(metrics, metricKey, days, pointCount, seriesIndex, productName) {
  const config = trendChartMetrics[metricKey] ?? trendChartMetrics.revenue;
  const previousValue = getTrendDisplayValue(metrics, metricKey, "previous", days);
  const currentValue = getTrendDisplayValue(metrics, metricKey, "current", days);
  const phase = (seriesIndex + 1) * 0.71 + String(productName).length * 0.037;
  const waveScale = config.kind === "percent" ? 0.035 : 0.085;

  return Array.from({ length: pointCount }, (_, pointIndex) => {
    const t = pointCount <= 1 ? 1 : pointIndex / (pointCount - 1);
    const baseValue = previousValue + (currentValue - previousValue) * t;
    const isEndpoint = pointIndex === 0 || pointIndex === pointCount - 1;
    const wave =
      isEndpoint
        ? 0
        : Math.sin((pointIndex + 1) * 1.13 + phase) * waveScale +
          Math.cos((pointIndex + 1) * 0.61 + phase) * (waveScale * 0.48);
    const waveBase = Math.max(Math.abs(baseValue), config.kind === "percent" ? 0.01 : 1);
    const rawValue = Math.max(0, baseValue + waveBase * wave);
    const value = config.kind === "percent" ? clampNumber(rawValue, 0, 1) : rawValue;

    return { index: pointIndex, value };
  });
}

function trendProductsForChart(product) {
  return state.selectedProductId === "all" ? portfolioProductViews() : [product];
}

function formatCompactNumber(value) {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  }

  return String(roundDisplay(value));
}

function formatTrendValue(metricKey, value, currency) {
  const config = trendChartMetrics[metricKey] ?? trendChartMetrics.revenue;

  if (config.kind === "currency") {
    return formatCurrency(Math.round(value), currency);
  }

  if (config.kind === "percent") {
    return formatPercent(value);
  }

  return formatCompactNumber(value);
}

function formatTrendAxisValue(metricKey, value, currency) {
  const config = trendChartMetrics[metricKey] ?? trendChartMetrics.revenue;

  if (config.kind === "currency") {
    const amount = Math.round(value / 100);
    return `$${formatCompactNumber(amount)}`;
  }

  return formatTrendValue(metricKey, value, currency);
}

function renderChart(product, metrics) {
  if (!barChart) return;

  const metricConfig = getTrendMetricConfig();
  const metricKey = state.activeTrendMetric;
  const days = getRangeDays();
  const pointCount = getTrendPointCount(days);
  const chartProducts = trendProductsForChart(product);
  const series = chartProducts.map((seriesProduct, index) => {
    const seriesMetrics = buildProductMetrics(seriesProduct);

    return {
      product: seriesProduct,
      metrics: seriesMetrics,
      color: trendChartPalette[index % trendChartPalette.length],
      points: buildTrendPoints(
        seriesMetrics,
        state.activeTrendMetric,
        days,
        pointCount,
        index,
        seriesProduct.name
      ),
    };
  });
  const values = series.flatMap((item) => item.points.map((point) => point.value));
  const rawMax = Math.max(...values, metricConfig.kind === "percent" ? 0.01 : 1);
  const yMax = metricConfig.kind === "percent"
    ? Math.min(1, Math.max(0.01, rawMax * 1.18))
    : Math.max(1, rawMax * 1.18);
  const chart = {
    width: 720,
    height: 300,
    left: 72,
    right: 694,
    top: 28,
    bottom: 244,
  };
  const xFor = (pointIndex) =>
    chart.left + ((chart.right - chart.left) * pointIndex) / Math.max(pointCount - 1, 1);
  const yFor = (value) =>
    chart.bottom - ((chart.bottom - chart.top) * value) / Math.max(yMax, 0.0001);
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((tick) => yMax * tick);
  const xTicks = buildTrendDateTicks(pointCount);
  const grid = yTicks
    .map((tickValue) => {
      const y = yFor(tickValue);
      return `
        <line class="trend-grid-line" x1="${chart.left}" x2="${chart.right}" y1="${y}" y2="${y}"></line>
        <text class="trend-axis-label" x="${chart.left - 12}" y="${y + 4}" text-anchor="end">${escapeSvgText(formatTrendAxisValue(metricKey, tickValue, product.currency))}</text>
      `;
    })
    .join("");
  const xLabels = xTicks
    .map((tick) => {
      const x = xFor(tick.index);
      return `<text class="trend-axis-label" x="${x}" y="${chart.bottom + 30}" text-anchor="middle">${escapeSvgText(tick.label)}</text>`;
    })
    .join("");
  const lineMarkup = series
    .map((item, seriesIndex) => {
      const coords = item.points.map((point) => ({
        x: xFor(point.index),
        y: yFor(point.value),
        value: point.value,
      }));
      const polylinePoints = coords.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
      const visibleDots = coords.filter((_, pointIndex) =>
        pointIndex === 0 || pointIndex === coords.length - 1 || pointIndex % 3 === seriesIndex % 3
      );

      return `
        <polyline class="trend-chart-line" style="--series-color: ${item.color}" points="${polylinePoints}"></polyline>
        ${visibleDots
    .map((point) => `
          <g>
            <circle class="trend-chart-dot" style="--series-color: ${item.color}" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="4.8"></circle>
            <title>${escapeSvgText(`${item.product.name}: ${formatTrendValue(metricKey, point.value, item.product.currency)}`)}</title>
          </g>
        `)
    .join("")}
      `;
    })
    .join("");
  const legend = series
    .map((item) => {
      const currentValue = item.points[item.points.length - 1]?.value ?? 0;

      return `
        <span class="trend-legend-item">
          <span class="trend-legend-swatch" style="--series-color: ${item.color}"></span>
          <span>${escapeHtml(item.product.name)}</span>
          <strong>${escapeHtml(formatTrendValue(metricKey, currentValue, item.product.currency))}</strong>
        </span>
      `;
    })
    .join("");
  const chartScope =
    state.selectedProductId === "all" ? `${series.length} product lines` : product.name;

  chartCaption.textContent = `${metricConfig.axisLabel} · ${getRangeLabel()} · ${chartScope}`;
  chartMetricButtons.forEach((button) => {
    const active = button.dataset.chartMetric === state.activeTrendMetric;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  barChart.innerHTML = `
    <svg class="trend-chart-svg" viewBox="0 0 ${chart.width} ${chart.height}" role="img" aria-label="${escapeHtml(metricConfig.label)} trend by product">
      <rect class="trend-chart-stage" x="0" y="0" width="${chart.width}" height="${chart.height}" rx="16"></rect>
      <g class="trend-grid">${grid}</g>
      <g class="trend-lines">${lineMarkup}</g>
      <g class="trend-x-axis">${xLabels}</g>
    </svg>
    <div class="trend-chart-legend">${legend}</div>
  `;

  renderChartDetail(product, metrics);
}

function renderSources(product, metrics) {
  const rows = getSortedSources(metrics)
    .map((source, index) => {
      return `
        <article class="source-row" style="--index: ${index}">
          <div>
            <div class="source-name">${escapeHtml(source.name)}</div>
            <div class="source-meta">AOV ${formatCurrency(source.averageOrderCents, product.currency)}</div>
          </div>
          <div class="source-meta">${source.views.toLocaleString()} / ${source.sales.toLocaleString()}</div>
          <div class="source-conversion">${formatPercent(source.conversion)}</div>
          <div class="source-revenue">${formatCurrency(source.revenueCents, product.currency)}</div>
        </article>
      `;
    });

  sourceTable.innerHTML = rows.join("");
  sourceSortSelect.value = state.sourceSort;
}

function renderSalesDashboard(product, metrics) {
  const dashboard = buildSalesDashboard(product, metrics);
  const locationRows = sortByDirection(
    state.locationScope === "us" ? dashboard.usLocations : dashboard.locations,
    (location) => location.revenueCents,
    state.locationSortDirection
  );
  const churnCards = [
    { label: "Churn rate", value: formatPercent(dashboard.churn.rate), raw: dashboard.churn.rate },
    { label: "Last period", value: formatPercent(dashboard.churn.previousRate), raw: dashboard.churn.previousRate },
    { label: "Churned users", value: dashboard.churn.canceled.toLocaleString(), raw: dashboard.churn.canceled },
    {
      label: "Revenue lost",
      value: formatCurrency(dashboard.churn.revenueLostCents, product.currency),
      raw: dashboard.churn.revenueLostCents,
    },
  ];

  churnMetricGrid.innerHTML = sortByDirection(
    churnCards,
    (card) => card.raw,
    state.churnSortDirection
  )
    .map((card) => {
      return `
        <article class="mini-metric">
          <span>${escapeHtml(card.label)}</span>
          <strong>${escapeHtml(card.value)}</strong>
        </article>
      `;
    })
    .join("");
  churnFormula.textContent = `Churn rate = ${dashboard.churn.formula} = ${formatPercent(dashboard.churn.rate)}.`;

  locationsTable.innerHTML = locationRows.length
    ? locationRows
    .map((location) => {
      return `
        <article class="detail-row location-row">
          <div>
            <strong>${escapeHtml(location.country)}</strong>
            <span>${escapeHtml(location.region)}</span>
          </div>
          <span>${location.views.toLocaleString()} views · ${location.sales.toLocaleString()} sales</span>
          <strong>${formatCurrency(location.revenueCents, product.currency)}</strong>
        </article>
      `;
    })
    .join("")
    : `<div class="empty-state compact-empty">No locations in this view.</div>`;

  utmTable.innerHTML = dashboard.utmLinks
    .map((link) => {
      const statusLabel = link.isDraft ? "Draft campaign" : "Measured campaign";

      return `
        <article class="detail-row utm-row" title="${escapeHtml(link.trackingUrl ?? "")}">
          <div>
            <strong>${escapeHtml(link.campaign)}</strong>
            <span>${escapeHtml(link.source)} / ${escapeHtml(link.medium)} · ${escapeHtml(link.destination)} · ${escapeHtml(statusLabel)}</span>
          </div>
          <span>${link.clicks.toLocaleString()} clicks</span>
          <span>${link.sales.toLocaleString()} sales</span>
          <span>${formatPercent(link.conversion)}</span>
          <strong>${formatCurrency(link.revenueCents, product.currency)}</strong>
        </article>
      `;
    })
    .join("");

  exportSummary.textContent = `${dashboard.csv.rows.length} synthetic customer rows prepared with customer, tax, fee, refund, subscription, affiliate, payment, referrer, location, and UTM fields. ${dashboard.csv.timezoneNote} Add a one-day buffer around exported ranges.`;
  exportCsvButton.dataset.csv = toCsv(dashboard.csv.columns, dashboard.csv.rows);
  exportCsvButton.dataset.filename = `${product.id}-sales-demo.csv`;
  updateSortButton(locationSortButton, state.locationSortDirection, "locations");
}

function backendRefundCaseToView(caseItem) {
  const caseType = caseItem.case_type ?? caseItem.caseType ?? "";
  const mode = caseItem.mode ?? (caseType === "chargeback_dispute" ? "dispute" : "review");

  return {
    id: String(caseItem.case_id ?? caseItem.id ?? crypto.randomUUID()),
    purchaseId: String(caseItem.purchase_id ?? caseItem.purchaseId ?? "seeded-purchase"),
    amountCents: toNumber(caseItem.amount_cents ?? caseItem.amount?.cents, 0),
    caseType,
    mode,
    status: caseItem.status ?? "needs_review",
    reason: caseItem.reason ?? caseItem.label ?? "Refund review",
    paymentType: caseItem.payment_type ?? caseItem.paymentType ?? "Seeded payment",
    sourceName: caseItem.source_name ?? caseItem.sourceName ?? "Seeded source",
    riskScore: Math.round(toNumber(caseItem.risk_score ?? caseItem.riskScore, 0)),
    recommendedAction: caseItem.recommended_action ?? caseItem.recommendedAction ?? "Check the case evidence before taking action.",
    buyerReply: caseItem.buyer_reply ?? caseItem.buyerReply ?? "",
    disputeEvidence: caseItem.dispute_evidence ?? caseItem.disputeEvidence ?? "",
    auditNote: caseItem.audit_note ?? caseItem.auditNote ?? "",
    deliveryEvidence: caseItem.delivery_evidence ?? caseItem.deliveryEvidence ?? "Seeded delivery evidence is available in the local DB.",
    policySnapshot: caseItem.policy_snapshot ?? caseItem.policySnapshot ?? "Check policy context before deciding.",
    label: caseItem.label ?? formatStatus(caseType || mode),
    timeline: asArray(caseItem.timeline).map((item) => ({
      label: item.label ?? item.check ?? "Timeline",
      value: item.value ?? item.detail ?? "",
    })),
    evidence: asArray(caseItem.evidence).map((item) => {
      if (!item || typeof item !== "object") {
        return {
          status: "review",
          label: String(item ?? "Evidence"),
          detail: "Loaded from the backend case payload.",
        };
      }

      return {
        status: item.status ?? "review",
        label: item.label ?? item.check ?? "Evidence",
        detail: item.detail ?? item.value ?? "",
      };
    }),
  };
}

function backendRefundActionToView(action) {
  return {
    id: String(action.id ?? action.title ?? crypto.randomUUID()),
    title: action.title ?? "Refund prevention action",
    impact: action.impact ?? "Calculated from Refund Ops summary and case data.",
    recommendedAction: action.recommended_action ?? action.recommendedAction ?? "Check this action before changing product copy.",
    evidence: asArray(action.evidence).map(formatBackendEvidence).filter(Boolean),
  };
}

function getRefundOpsView(product, metrics) {
  const fallback = () => ({
    ...buildRefundOps(product, metrics),
    source: "fallback",
  });
  const insights = currentFeatureInsights();
  const summary = insights?.refundOps?.summary;

  if (!summary) {
    return fallback();
  }

  const cases = asArray(insights.refundOps.cases).map(backendRefundCaseToView);
  const preventionActions = asArray(insights.refundOps.preventionActions).map(backendRefundActionToView);

  return {
    source: "live",
    summary: {
      refundRate: toNumber(summary.refund_rate),
      previousRefundRate: toNumber(summary.previous_refund_rate),
      refunds: toNumber(summary.refunds),
      refundAmountCents: toNumber(summary.refund_amount_cents),
      disputedAmountCents: toNumber(summary.disputed_amount_cents),
      amountUnderReviewCents: toNumber(summary.amount_under_review_cents),
      casesNeedingReview: toNumber(summary.cases_needing_review),
      caseCount: toNumber(summary.case_count),
      preventableRefundEstimateCents: toNumber(summary.preventable_refund_estimate_cents),
      modeCounts: {
        prevent: toNumber(summary.mode_counts?.prevent, preventionActions.length),
        review: toNumber(summary.mode_counts?.review, cases.filter((item) => item.mode === "review").length),
        dispute: toNumber(summary.mode_counts?.dispute, cases.filter((item) => item.mode === "dispute").length),
      },
      boundary: summary.boundary ?? "",
    },
    cases,
    preventionActions,
  };
}

function refundOpsModeCount(refundOps, activeMode) {
  const modeCounts = refundOps.summary.modeCounts ?? {};
  const visibleCount =
    activeMode === "prevent"
      ? refundOps.preventionActions.length
      : refundOps.cases.filter((item) => item.mode === activeMode).length;

  return visibleCount || toNumber(modeCounts[activeMode], 0);
}

function refundOpsStatusLabel(refundOps, activeMode) {
  const count = refundOpsModeCount(refundOps, activeMode);
  const countLabel = count.toLocaleString("en-US");

  if (activeMode === "prevent") {
    return { count, label: `${countLabel} prevent` };
  }

  if (activeMode === "dispute") {
    return { count, label: `${countLabel} dispute${count === 1 ? "" : "s"}` };
  }

  return { count, label: `${countLabel} to review` };
}

function backendTrendToView(trend) {
  const expectedKpi = trend.expected_kpi ?? {};
  const draft = asArray(trend.draft_outlines)[0] ?? {};
  const channel = trend.channel ?? "Content";
  const campaignName = trend.campaign_utm_name ?? trend.utm?.campaign ?? "content-radar-campaign";
  const source = trend.utm?.source ?? channel.toLowerCase().replaceAll(" ", "-");
  const medium = trend.utm?.medium ?? "content";
  const fitScore = Math.round(toNumber(trend.score, 0));

  return {
    id: String(trend.id ?? trend.trend_id ?? campaignName),
    title: trend.title ?? "Content trend",
    angle: trend.trend_angle ?? asArray(trend.angles)[0] ?? "Review this content angle against current analytics.",
    channel,
    expectedKpi: expectedKpi.name ?? "Expected KPI",
    fitScore,
    trendScore: fitScore,
    rationale: trend.fit_rationale ?? "Calculated trend fit is available from the backend payload.",
    risk: formatRiskDetail(asArray(trend.risks)[0]),
    risks: asArray(trend.risks).map(formatRiskDetail).filter(Boolean),
    evidence: asArray(trend.evidence).map(formatBackendEvidence).filter(Boolean),
    outline: asArray(trend.angles).length ? asArray(trend.angles) : asArray(draft.copyable_outline),
    draft: {
      post: draft.draft_copy ?? `${trend.title ?? "Content trend"} via utm_campaign=${campaignName}.`,
      email: draft.draft_copy ?? "",
    },
    kpiBaseline: expectedKpi.baseline_formatted ?? "",
    kpiTarget: expectedKpi.target_formatted ?? "",
    kpiWindow: expectedKpi.measurement_window ?? "next review period",
    utmCampaign: campaignName,
    utmPlan: `utm_source=${encodeURIComponent(source)}&utm_medium=${encodeURIComponent(medium)}&utm_campaign=${encodeURIComponent(campaignName)}`,
  };
}

function getContentRadarView(product, metrics) {
  const fallback = () => ({
    ...buildContentRadar(product, metrics),
    source: "fallback",
  });
  const insights = currentFeatureInsights();
  const trends = asArray(insights?.contentRadar?.trends).map(backendTrendToView);

  if (!trends.length) {
    return fallback();
  }

  const lead = trends[0];
  return {
    source: "live",
    summary: {
      trendCount: trends.length,
      topFitScore: lead.fitScore,
      primaryChannel: lead.channel,
      campaignName: lead.utmCampaign,
      expectedKpi: lead.expectedKpi,
      readOnly: true,
    },
    trends,
    plan: {
      executionNote:
        insights.contentRadar.summary?.boundary ??
        "Content Radar turns trend signals into campaign plans, tracking rows, and launch steps.",
    },
    drafts: {
      campaignBrief: `${lead.title}: ${lead.rationale}`,
      utmPlan: lead.utmPlan,
    },
  };
}

function retentionOfferToView(offer) {
  return {
    id: String(offer.id ?? offer.label ?? crypto.randomUUID()),
    label: offer.label ?? "Pause offer",
    bestFor: offer.best_for ?? offer.bestFor ?? "Cancellation-intent workflow.",
    estimatedSavedCents: toNumber(
      offer.estimated_revenue_saved_cents ?? offer.estimatedSavedCents ?? offer.estimated_revenue_saved?.cents,
      0
    ),
    reviewSteps: [
      offer.merchant_review_prompt ?? "Check cancellation context before showing this offer.",
      `Use the ${offer.save_rate_assumption_formatted ?? "calculated"} save-rate assumption for this estimate.`,
      "Keep the normal cancellation path available.",
    ],
  };
}

function retentionRiskToView(risk) {
  const drivers = asArray(risk.drivers);
  const driverText = drivers.length ? drivers.join(" ") : "Backend risk score combines churn, refund pressure, source mix, and sample recurring rows.";

  return {
    label: risk.title ?? risk.product?.name ?? "Cancellation risk",
    value: `${formatStatus(risk.risk_level ?? "risk")} · ${Math.round(toNumber(risk.risk_score, 0))}/100`,
    detail: `Because ${risk.canceled ?? 0} cancellations at ${risk.churn_rate_formatted ?? "0%"} churn represent ${formattedMoney(risk.revenue_lost, risk.revenue_lost_cents)} modeled lost revenue. ${driverText}`,
  };
}

function getRetentionView(product, metrics) {
  const fallback = () => ({
    ...buildRetentionSaver(product, metrics),
    source: "fallback",
  });
  const insights = currentFeatureInsights();
  const summary = insights?.retention?.summary;

  if (!summary) {
    return fallback();
  }

  const churn = summary.membership_churn ?? {};
  const estimate = summary.pause_revenue_estimate ?? {};

  return {
    source: "live",
    summary: {
      sourceIssue: "SQLite calculated",
      churnRate: toNumber(churn.churn_rate),
      canceledMembers: toNumber(churn.canceled),
      revenueLostCents: toNumber(churn.revenue_lost_cents),
      expectedSavedMembers: toNumber(estimate.estimated_saved_memberships),
      revenueSavedCents: toNumber(estimate.estimated_revenue_saved_cents),
      saveRate: toNumber(estimate.save_rate_assumption),
      readOnly: true,
    },
    pauseOffers: asArray(summary.pause_offer_options).map(retentionOfferToView),
    risks: asArray(insights.retention.risks).length
      ? asArray(insights.retention.risks).map(retentionRiskToView)
      : asArray(summary.top_cancellation_risks).map(retentionRiskToView),
  };
}

function qaPassFailText(value) {
  if (!value || typeof value !== "object") {
    return String(value ?? "Use screenshots, copied text, and backend response JSON as evidence.");
  }

  const pass = asArray(value.pass)[0];
  const capture = asArray(value.capture).join(", ");
  return `${pass ? `Pass evidence: ${pass}` : "Pass evidence comes from the backend QA payload."}${capture ? ` Capture: ${capture}.` : ""}`;
}

function getShortestQaView(product, metrics) {
  const fallback = () => ({
    ...buildShortestQa(product, metrics),
    source: "fallback",
  });
  const insights = currentFeatureInsights();
  const suites = asArray(insights?.qa?.suites);
  const tests = asArray(insights?.qa?.tests);

  if (!suites.length) {
    return fallback();
  }

  const testsBySuite = new Map();
  tests.forEach((test) => {
    if (!testsBySuite.has(test.suite_id)) {
      testsBySuite.set(test.suite_id, test);
    }
  });

  const suiteViews = suites.map((suite) => {
    const test = testsBySuite.get(suite.id) ?? {};
    const riskCovered = asArray(test.risk_covered).length
      ? asArray(test.risk_covered).join(" ")
      : test.risk_covered ?? suite.purpose ?? "Review deterministic QA coverage.";

    return {
      id: suite.id,
      title: suite.name ?? suite.title ?? "QA suite",
      targetSurface: asArray(suite.target_surfaces).join(", ") || test.target_surface || "Gumroad Merchant",
      riskCovered,
      steps: asArray(test.steps).length ? asArray(test.steps) : [suite.purpose ?? "Review this suite."],
      assertions: asArray(test.assertions).length ? asArray(test.assertions) : [`${suite.scenario_count ?? 0} backend scenarios are available.`],
      passFailEvidence: qaPassFailText(test.pass_fail_evidence),
    };
  });

  return {
    source: "live",
    summary: {
      suiteCount: toNumber(insights.qa.summary?.suite_count, suiteViews.length),
      assertionCount:
        tests.reduce((total, test) => total + asArray(test.assertions).length, 0) ||
        toNumber(insights.qa.summary?.test_count, tests.length),
      productName: product.name,
      readOnly: true,
    },
    suites: suiteViews,
  };
}

function adminTemplateToView(template) {
  return {
    id: String(template.id ?? template.title ?? crypto.randomUUID()),
    label: template.title ?? template.label ?? "Admin action",
    commandText: template.command_text ?? template.commandText ?? "gumroad-admin actions prepare",
    description: template.description ?? "",
    riskLevel: template.risk_level ?? template.riskLevel ?? "unknown",
    requiredInputs: asArray(template.required_inputs ?? template.requiredInputs),
    preflightChecks: asArray(template.preflight_checks ?? template.preflightChecks).map((check) =>
      typeof check === "string" ? check : check.detail ?? check.check ?? "Preflight check"
    ),
    auditNote: template.audit_note ?? template.auditNote ?? "Action prepared with audit trail and execution context.",
    blockedReason: template.blocked_reason ?? template.blockedReason ?? "",
    unsafeWrite: Boolean(template.unsafe_write ?? template.unsafeWrite),
  };
}

function getAdminPreviewView(product, metrics) {
  const refundOps = getRefundOpsView(product, metrics);
  const retentionSaver = getRetentionView(product, metrics);
  const fallback = () => ({
    ...buildAdminActionPreview(product, metrics, refundOps, retentionSaver),
    source: "fallback",
  });
  const insights = currentFeatureInsights();
  const summary = insights?.admin?.summary;
  const templates = asArray(summary?.templates).length
    ? asArray(summary.templates)
    : asArray(insights?.admin?.templates);

  if (!summary || !templates.length) {
    return fallback();
  }

  const mappedTemplates = templates.map(adminTemplateToView);
  return {
    source: "live",
    summary: {
      sourceIssue: "SQLite calculated",
      templateCount: toNumber(summary.template_count, mappedTemplates.length),
      safeReadCount: mappedTemplates.filter((item) => !item.unsafeWrite).length,
      blockedWriteCount: asArray(summary.blocked_write_templates).length,
      refundSuggestionCount: asArray(summary.refund_ops_case_suggestions).length,
      readOnly: true,
      boundary: summary.boundary ?? "",
    },
    templates: mappedTemplates,
    preview: {
      selected: mappedTemplates[0],
      sourceContext:
        summary.source_context?.summary ??
        "Admin Actions renders commands and audit copy from backend tool payloads.",
      executionNote:
        summary.boundary ??
        "Admin Actions shows the execution mode, preflight checks, and audit notes for each merchant operation.",
    },
  };
}

function renderRefundOps(product, metrics) {
  const refundOps = getRefundOpsView(product, metrics);
  const activeMode = state.refundMode;
  const statusBadge = refundOpsStatusLabel(refundOps, activeMode);
  const visibleCases = refundOps.cases.filter((item) => item.mode === activeMode);
  const activeCaseStillVisible = visibleCases.some((item) => item.id === state.activeRefundCaseId);
  refundOpsLayout?.classList.toggle("is-prevent-mode", activeMode === "prevent");

  if (activeMode === "prevent") {
    state.activeRefundCaseId = null;
  } else if (!activeCaseStillVisible) {
    state.activeRefundCaseId = visibleCases[0]?.id ?? null;
  }

  refundModeButtons.forEach((button) => {
    const isActive = button.dataset.refundMode === activeMode;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
    const mode = button.dataset.refundMode;
    if (mode) {
      button.dataset.count = String(refundOpsModeCount(refundOps, mode));
    }
  });

  refundOpsStatus.textContent = statusBadge.label;
  refundOpsStatus.dataset.count = String(statusBadge.count);
  refundOpsStatus.dataset.mode = activeMode;
  refundOpsStatus.dataset.source = refundOps.source;

  const metricCards = [
    {
      label: "Refund rate",
      value: formatPercent(refundOps.summary.refundRate),
      note: refundOps.source === "live" ? `was ${formatPercent(refundOps.summary.previousRefundRate)}` : "Static seed fallback",
      tone: refundOps.summary.refundRate > refundOps.summary.previousRefundRate ? "warn" : "good",
    },
    {
      label: "Disputed",
      value: formatCurrency(refundOps.summary.disputedAmountCents, product.currency),
      note: "chargeback exposure",
      tone: refundOps.summary.disputedAmountCents > 0 ? "warn" : "good",
    },
    {
      label: "Cases",
      value: refundOps.summary.casesNeedingReview.toLocaleString("en-US"),
      note: "open cases",
      tone: refundOps.summary.casesNeedingReview > 0 ? "warn" : "good",
    },
    {
      label: "Preventable",
      value: formatCurrency(refundOps.summary.preventableRefundEstimateCents, product.currency),
      note: "estimated refund savings",
      tone: "good",
    },
  ];

  refundOpsMetrics.innerHTML = metricCards
    .map(
      (card) => `
        <article class="refund-metric ${card.tone}">
          <span>${escapeHtml(card.label)}</span>
          <strong>${escapeHtml(card.value)}</strong>
          <small>${escapeHtml(card.note)}</small>
        </article>
      `,
    )
    .join("");

  refundCaseHeading.textContent =
    activeMode === "prevent"
      ? "Prevention actions"
      : activeMode === "dispute"
        ? "Chargeback disputes"
        : "Refund queue";

  if (activeMode === "prevent") {
    refundCaseList.innerHTML = refundOps.preventionActions
      .map(
        (action, index) => `
        <article class="refund-action-card" style="--index: ${index}">
          ${renderMiniAgentButton("refunds", {
            sectionLabel: "Refund prevention",
            subsectionLabel: action.title,
            label: `${action.title}. Recommended action: ${action.recommendedAction}`,
          })}
          <h4>${escapeHtml(action.title)}</h4>
          <p>${escapeHtml(action.recommendedAction)}</p>
          </article>
        `,
      )
      .join("");
    renderRefundPreventionDetail(refundOps.preventionActions[0], product);
  } else if (visibleCases.length > 0) {
    refundCaseList.innerHTML = visibleCases.map(renderRefundCaseButton).join("");
    renderRefundCaseDetail(visibleCases.find((item) => item.id === state.activeRefundCaseId) ?? visibleCases[0], product);
  } else {
    refundCaseList.innerHTML = `<div class="empty-state compact-empty">No ${activeMode} cases in this seeded selection.</div>`;
    renderRefundEmptyDetail(activeMode);
  }

  refundPreventionList.innerHTML = refundOps.preventionActions
    .map(
      (action) => `
        <article class="refund-prevention-item">
          ${renderMiniAgentButton("refunds", {
            sectionLabel: "Refund prevention insights",
            subsectionLabel: action.title,
            label: `${action.title}. Evidence: ${action.evidence.join(", ")}`,
          })}
          <h4>${escapeHtml(action.title)}</h4>
          <div>
            ${action.evidence.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
          </div>
        </article>
      `,
    )
    .join("");
}

function renderOpsMetric([label, value, note], promptKey, type, showAgentButton = true) {
  return `
    <article class="ops-metric">
      ${showAgentButton
        ? renderMiniAgentButton(promptKey, {
            sectionLabel: type,
            subsectionLabel: label,
            label: `${label}: ${value}. ${note}`,
          })
        : ""}
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(note)}</small>
    </article>
  `;
}

function renderContentRadar(product, metrics) {
  const radar = getContentRadarView(product, metrics);
  const leadTrend = radar.trends[0];

  if (!radar.trends.some((trend) => trend.id === state.activeContentTrendId)) {
    state.activeContentTrendId = leadTrend?.id ?? null;
  }

  const activeTrend =
    radar.trends.find((trend) => trend.id === state.activeContentTrendId) ?? leadTrend;

  contentRadarStatus.textContent =
    radar.source === "live" ? `${radar.summary.topFitScore}/100 fit` : renderInsightSourceNote();
  contentRadarMetrics.innerHTML = [
    [
      "Trends",
      radar.summary.trendCount.toLocaleString("en-US"),
      radar.source === "live" ? "backend calculated" : "Static seed fallback",
    ],
    ["Top channel", radar.summary.primaryChannel, "best first test"],
    ["KPI", radar.summary.expectedKpi, "watch next"],
  ]
    .map((item) => renderOpsMetric(item, "content", "content radar metric", false))
    .join("");

  contentTrendList.innerHTML = radar.trends
    .map(
      (trend, index) => `
        <button
          class="ops-list-button ${activeTrend?.id === trend.id ? "active" : ""}"
          type="button"
          data-content-trend-id="${escapeHtml(trend.id)}"
          aria-pressed="${activeTrend?.id === trend.id ? "true" : "false"}"
          style="--index: ${index}"
        >
          <span>
            <strong>${escapeHtml(trend.title)}</strong>
            <small>${escapeHtml(trend.channel)} · ${escapeHtml(trend.expectedKpi)}</small>
          </span>
          <span>
            <strong>${trend.fitScore}</strong>
            <small>fit</small>
          </span>
        </button>
      `,
    )
    .join("");

  contentPlanDetail.innerHTML = activeTrend
    ? `
      <div class="ops-detail-header">
        <div>
          <p class="eyebrow">Marketing plan</p>
          <h3>${escapeHtml(activeTrend.title)}</h3>
          <p>${escapeHtml(activeTrend.angle)}</p>
        </div>
        <span class="detail-badge">${activeTrend.trendScore}/100 trend</span>
        ${renderMiniAgentButton("content", {
          sectionLabel: "Content Radar detail",
          subsectionLabel: activeTrend.title,
          label: `${activeTrend.title}: ${activeTrend.rationale} KPI ${activeTrend.expectedKpi}`,
        })}
      </div>
      <div class="ops-detail-grid">
        <div>
          <span>Rationale</span>
          <p>${escapeHtml(activeTrend.rationale)}</p>
        </div>
        <div>
          <span>KPI move</span>
          <p>${
            activeTrend.kpiBaseline && activeTrend.kpiTarget
              ? `${escapeHtml(activeTrend.expectedKpi)} from ${escapeHtml(activeTrend.kpiBaseline)} to ${escapeHtml(activeTrend.kpiTarget)} over ${escapeHtml(activeTrend.kpiWindow)}.`
              : escapeHtml(activeTrend.risk)
          }</p>
        </div>
      </div>
      <ol class="ops-step-list">
        ${activeTrend.outline.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
      </ol>
      ${
        asArray(activeTrend.risks).length
          ? `<div class="ops-risk-list compact-risk-list">
              ${activeTrend.risks
                .map(
                  (risk) => `
                    <article class="ops-risk-row">
                      <span>Risk</span>
                      <p>${escapeHtml(risk)}</p>
                    </article>
                  `,
                )
                .join("")}
            </div>`
          : ""
      }
      <div class="ops-chip-row">
        ${activeTrend.evidence.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
      </div>
      <div class="ops-copy-row">
        <button class="secondary-button" type="button" data-copy-text="${escapeHtml(radar.drafts.campaignBrief)}">Copy brief</button>
        <button class="secondary-button" type="button" data-copy-text="${escapeHtml(activeTrend.draft.post)}">Copy post draft</button>
        <button class="secondary-button" type="button" data-copy-text="${escapeHtml(activeTrend.utmPlan ?? radar.drafts.utmPlan)}">Copy UTM plan</button>
        <button class="secondary-button" type="button" data-merchant-prompt="${escapeHtml(`Create the tracked campaign row and tracking URL for ${activeTrend.title} on ${activeTrend.channel}. Explain why this campaign should be tracked before we scale it.`)}">Create campaign</button>
      </div>
      <p class="detail-note">${escapeHtml(radar.plan.executionNote)}</p>
    `
    : `<div class="empty-state compact-empty">No content trends for this seeded selection.</div>`;
}

function renderRetentionSaver(product, metrics) {
  const retention = getRetentionView(product, metrics);

  retentionSaverStatus.textContent =
    retention.source === "live" ? retention.summary.sourceIssue : renderInsightSourceNote();
  retentionMetrics.innerHTML = [
    ["Churn", formatPercent(retention.summary.churnRate), `${retention.summary.canceledMembers} canceled`],
    ["Lost", formatCurrency(retention.summary.revenueLostCents, product.currency), "recurring revenue"],
    [
      "Saved",
      formatCurrency(retention.summary.revenueSavedCents, product.currency),
      retention.summary.saveRate ? `${formatPercent(retention.summary.saveRate)} assumption` : renderInsightSourceNote(),
    ],
  ]
    .map((item) => renderOpsMetric(item, "retention", "retention metric", false))
    .join("");

  if (retentionRiskBadge) {
    retentionRiskBadge.textContent = retention.summary.saveRate
      ? `${formatPercent(retention.summary.saveRate)} save assumption`
      : renderInsightSourceNote();
  }

  pauseOfferList.innerHTML = retention.pauseOffers
    .map(
      (offer, index) => `
        <article class="ops-card" style="--index: ${index}">
          <h4>${escapeHtml(offer.label)}</h4>
          <strong>${formatCurrency(offer.estimatedSavedCents, product.currency)} estimated saved</strong>
          <ol>
            ${offer.reviewSteps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
          </ol>
        </article>
      `,
    )
    .join("");

  retentionRiskList.innerHTML = retention.risks
    .map(
      (risk) => `
        <article class="ops-risk-row">
          ${renderMiniAgentButton("retention", {
            sectionLabel: "Retention risk model",
            subsectionLabel: risk.label,
            label: `${risk.label}: ${risk.value}. ${risk.detail}`,
          })}
          <span>${escapeHtml(risk.label)}</span>
          <strong>${escapeHtml(risk.value)}</strong>
          <p>${escapeHtml(risk.detail)}</p>
        </article>
      `,
    )
    .join("");
}

function renderAdminPreview(product, metrics) {
  if (!adminPreviewStatus || !adminPreviewMetrics || !adminActionList || !adminActionDetail) {
    return;
  }

  const adminPreview = getAdminPreviewView(product, metrics);
  const leadAction = adminPreview.templates[0];

  if (!adminPreview.templates.some((template) => template.id === state.activeAdminActionId)) {
    state.activeAdminActionId = leadAction?.id ?? null;
  }

  const activeAction =
    adminPreview.templates.find((template) => template.id === state.activeAdminActionId) ?? leadAction;

  adminPreviewStatus.textContent =
    adminPreview.source === "live" ? "Backend actions" : renderInsightSourceNote();
  adminPreviewMetrics.innerHTML = [
    ["Templates", adminPreview.summary.templateCount.toLocaleString("en-US"), adminPreview.source === "live" ? "backend tool output" : "Static seed fallback"],
    ["Reads", adminPreview.summary.safeReadCount.toLocaleString("en-US"), "available"],
    ["Writes", adminPreview.summary.blockedWriteCount.toLocaleString("en-US"), "preflight checks"],
  ]
    .map((item) => renderOpsMetric(item, "admin", "admin action metric"))
    .join("");

  adminActionList.innerHTML = adminPreview.templates
    .map(
      (template, index) => `
        <button
          class="ops-list-button ${activeAction?.id === template.id ? "active" : ""}"
          type="button"
          data-admin-action-id="${escapeHtml(template.id)}"
          aria-pressed="${activeAction?.id === template.id ? "true" : "false"}"
          style="--index: ${index}"
        >
          <span>
            <strong>${escapeHtml(template.label)}</strong>
            <small>${escapeHtml(template.riskLevel)} · ${template.unsafeWrite ? "write action" : "read action"}</small>
          </span>
          <span>
            <small>${template.requiredInputs.length} inputs</small>
          </span>
        </button>
      `,
    )
    .join("");

  adminActionDetail.innerHTML = activeAction
    ? `
      <div class="ops-detail-header">
        <div>
          <p class="eyebrow">Admin Actions</p>
          <h3>${escapeHtml(activeAction.label)}</h3>
          <p>${escapeHtml(activeAction.description || adminPreview.preview.sourceContext)}</p>
        </div>
        <span class="detail-badge">${escapeHtml(activeAction.unsafeWrite ? "Write action" : "Read action")}</span>
        ${renderMiniAgentButton("admin", {
          sectionLabel: "Admin action detail",
          subsectionLabel: activeAction.label,
          label: `${activeAction.label}: ${activeAction.riskLevel}. Required inputs: ${activeAction.requiredInputs.join(", ") || "none"}. Audit note: ${activeAction.auditNote}`,
        })}
      </div>
      <div class="ops-detail-grid">
        <div>
          <span>Command</span>
          <p>${escapeHtml(activeAction.commandText)}</p>
        </div>
        <div>
          <span>Audit note</span>
          <p>${escapeHtml(activeAction.auditNote)}</p>
        </div>
      </div>
      <ol class="ops-step-list">
        ${activeAction.preflightChecks.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
      </ol>
      ${
        activeAction.blockedReason
          ? `<p class="detail-note">${escapeHtml(activeAction.blockedReason)}</p>`
          : `<p class="detail-note">${escapeHtml(adminPreview.preview.executionNote)}</p>`
      }
      <div class="ops-copy-row">
        <button class="secondary-button" type="button" data-copy-text="${escapeHtml(activeAction.commandText)}">Copy command</button>
        <button class="secondary-button" type="button" data-copy-text="${escapeHtml(activeAction.auditNote)}">Copy audit note</button>
      </div>
    `
    : `<div class="empty-state compact-empty">No admin action selected.</div>`;
}

function renderShortestQa(product, metrics) {
  const qa = getShortestQaView(product, metrics);
  const leadSuite = qa.suites[0];

  if (!qa.suites.some((suite) => suite.id === state.activeQaSuiteId)) {
    state.activeQaSuiteId = leadSuite?.id ?? null;
  }

  const activeSuite =
    qa.suites.find((suite) => suite.id === state.activeQaSuiteId) ?? leadSuite;

  shortestQaStatus.textContent =
    qa.source === "live" ? "Backend generated" : renderInsightSourceNote();
  shortestQaMetrics.innerHTML = [
    ["Suites", qa.summary.suiteCount.toLocaleString("en-US"), "journeys"],
    ["Assertions", qa.summary.assertionCount.toLocaleString("en-US"), "checks"],
    ["Scope", qa.source === "live" ? "Backend" : "Local", "automated tests"],
  ]
    .map((item) => renderOpsMetric(item, "qa", "QA metric", false))
    .join("");

  shortestQaList.innerHTML = qa.suites
    .map(
      (suite, index) => `
        <button
          class="ops-list-button ${activeSuite?.id === suite.id ? "active" : ""}"
          type="button"
          data-qa-suite-id="${escapeHtml(suite.id)}"
          aria-pressed="${activeSuite?.id === suite.id ? "true" : "false"}"
          style="--index: ${index}"
        >
          <span>
            <strong>${escapeHtml(suite.title)}</strong>
            <small>${escapeHtml(suite.targetSurface)}</small>
          </span>
          <span>
            <small>${suite.assertions.length} checks</small>
          </span>
        </button>
      `,
    )
    .join("");

  const copyText = activeSuite
    ? [
      `# ${activeSuite.title}`,
      `Target: ${activeSuite.targetSurface}`,
      `Risk covered: ${activeSuite.riskCovered}`,
      "",
      "Steps:",
      ...activeSuite.steps.map((step, index) => `${index + 1}. ${step}`),
      "",
      "Assertions:",
      ...activeSuite.assertions.map((assertion) => `- ${assertion}`),
      "",
      `Pass/fail evidence: ${activeSuite.passFailEvidence}`,
    ].join("\n")
    : "";

  shortestQaDetail.innerHTML = activeSuite
    ? `
      <div class="ops-detail-header">
        <div>
          <p class="eyebrow">Shortest QA</p>
          <h3>${escapeHtml(activeSuite.title)}</h3>
          <p>${escapeHtml(activeSuite.riskCovered)}</p>
        </div>
        <span class="detail-badge">${activeSuite.assertions.length} checks</span>
        ${renderMiniAgentButton("qa", {
          sectionLabel: "Shortest QA detail",
          subsectionLabel: activeSuite.title,
          label: `${activeSuite.title}: ${activeSuite.riskCovered}. ${activeSuite.assertions.length} checks.`,
        })}
      </div>
      <div class="ops-detail-grid">
        <div>
          <span>Steps</span>
          <ol>${activeSuite.steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
        </div>
        <div>
          <span>Assertions</span>
          <ol>${activeSuite.assertions.map((assertion) => `<li>${escapeHtml(assertion)}</li>`).join("")}</ol>
        </div>
      </div>
      <p class="detail-note">${escapeHtml(activeSuite.passFailEvidence)}</p>
      <div class="ops-copy-row">
        <button class="secondary-button" type="button" data-copy-text="${escapeHtml(copyText)}">Copy QA scenario</button>
      </div>
    `
    : `<div class="empty-state compact-empty">No QA suite selected.</div>`;
}

function renderRefundCaseButton(caseItem, index) {
  const isActive = state.activeRefundCaseId === caseItem.id;
  return `
    <button
      class="refund-case-button ${isActive ? "active" : ""}"
      type="button"
      data-refund-case-id="${escapeHtml(caseItem.id)}"
      aria-pressed="${isActive ? "true" : "false"}"
      style="--index: ${index}"
    >
      <span>
        <strong>${escapeHtml(caseItem.label)}</strong>
        <small>${escapeHtml(formatStatus(caseItem.status))} · ${escapeHtml(caseItem.sourceName)}</small>
      </span>
      <span>
        <strong>${formatCurrency(caseItem.amountCents, "USD")}</strong>
        <small>risk ${caseItem.riskScore}/100</small>
      </span>
    </button>
  `;
}

function renderRefundPreventionDetail(action, product) {
  if (!action) {
    renderRefundEmptyDetail("prevent");
    return;
  }

  refundCaseDetail.innerHTML = `
    <div class="refund-detail-header">
      <div>
        <p class="eyebrow">Prevention</p>
        <h3>${escapeHtml(action.title)}</h3>
      </div>
      <span class="detail-badge">Action-ready</span>
      ${renderMiniAgentButton("refunds", {
        sectionLabel: "Refund prevention detail",
        subsectionLabel: action.title,
        label: `${action.title}. Recommended action: ${action.recommendedAction}`,
      })}
    </div>
    <div class="refund-detail-section">
      <h4>Recommended action</h4>
      <p>${escapeHtml(action.recommendedAction)}</p>
    </div>
    <div class="refund-evidence-list">
      ${action.evidence.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
    </div>
    <p class="detail-note">This panel prepares the product update workflow for ${escapeHtml(product.name)}.</p>
  `;
}

function renderRefundCaseDetail(caseItem, product) {
  const copyItems = [
    ["Copy buyer reply", caseItem.buyerReply],
    ["Copy dispute evidence", caseItem.disputeEvidence],
    ["Copy audit note", caseItem.auditNote],
  ];

  refundCaseDetail.innerHTML = `
    <div class="refund-detail-header">
      <div>
        <p class="eyebrow">${escapeHtml(caseItem.label)}</p>
        <h3>${escapeHtml(caseItem.reason)}</h3>
        <p class="refund-detail-meta">
          ${escapeHtml(caseItem.purchaseId)} · ${escapeHtml(caseItem.paymentType)} · ${escapeHtml(formatCurrency(caseItem.amountCents, product.currency))}
        </p>
      </div>
      <span class="detail-badge">${escapeHtml(formatStatus(caseItem.status))}</span>
      ${renderMiniAgentButton("refunds", {
        sectionLabel: "Refund case detail",
        subsectionLabel: caseItem.caseId ?? caseItem.id,
        label: `${caseItem.label}: ${caseItem.reason}. Risk ${caseItem.riskScore}/100. Recommended action: ${caseItem.recommendedAction}`,
      })}
    </div>

    <p class="refund-detail-copy">${escapeHtml(caseItem.recommendedAction)}</p>

    <div class="refund-detail-grid">
      <div class="refund-detail-section">
        <h4>Purchase facts</h4>
        <p>${escapeHtml(caseItem.deliveryEvidence)}</p>
      </div>
      <div class="refund-detail-section">
        <h4>Policy snapshot</h4>
        <p>${escapeHtml(caseItem.policySnapshot)}</p>
      </div>
    </div>

    <div class="refund-timeline">
      ${caseItem.timeline
        .map(
          (item) => `
            <div>
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(item.value)}</strong>
            </div>
          `,
        )
        .join("")}
    </div>

    <div class="refund-checklist">
      ${caseItem.evidence
        .map(
          (item) => `
            <div>
              <span>${escapeHtml(item.status)}</span>
              <strong>${escapeHtml(item.label)}</strong>
              <p>${escapeHtml(item.detail)}</p>
            </div>
          `,
        )
        .join("")}
    </div>

    <div class="refund-copy-actions">
      ${copyItems
        .map(
          ([label, value]) => `
            <button class="secondary-button" type="button" data-refund-copy="${escapeHtml(value)}">
              ${escapeHtml(label)}
            </button>
          `,
        )
        .join("")}
      <span id="refund-copy-status" class="copy-status" aria-live="polite"></span>
    </div>
  `;
}

function renderRefundEmptyDetail(mode) {
  refundCaseDetail.innerHTML = `
    <div class="empty-state compact-empty">
      No ${escapeHtml(mode)} detail selected for this seeded dashboard.
    </div>
  `;
}

function renderSuggestions(product, metrics) {
  if (!state.generated) {
    suggestions.innerHTML = `<div class="empty-state">Choose a product and generate insights.</div>`;
    renderActionReview([]);
    return;
  }

  const signals = detectSignals(product, metrics);
  const cards = generateSuggestions(product, metrics, signals);
  const cardIds = new Set(cards.map((card) => card.id));

  state.expandedSuggestionIds.forEach((id) => {
    if (!cardIds.has(id)) {
      state.expandedSuggestionIds.delete(id);
    }
  });

  if (!cards.some((card) => card.id === state.activeSuggestionId)) {
    state.activeSuggestionId = null;
  }

  suggestions.innerHTML = cards.map(renderSuggestionCard).join("");
  renderActionReview(cards);
}

function renderSuggestionCard(card, index) {
  const isExpanded = state.expandedSuggestionIds.has(card.id);
  const detailId = `suggestion-detail-${card.id}`;

  return `
    <article class="suggestion-card ${isExpanded ? "expanded" : ""}" style="--index: ${index}">
      <div class="suggestion-card-header">
        <div class="suggestion-title-wrap">
          <div class="suggestion-topline">
            <span class="suggestion-label">${escapeHtml(card.label)}</span>
            <span class="confidence">${escapeHtml(card.confidence)} confidence</span>
          </div>
          <h3>${escapeHtml(card.title)}</h3>
          <p class="suggestion-summary">${escapeHtml(card.recommendation)}</p>
        </div>
        <div class="suggestion-card-actions">
          ${renderMiniAgentButton("suggestions", {
            sectionLabel: "Suggested next moves",
            subsectionLabel: card.title,
            label: `${card.label}: ${card.confidence} confidence. ${card.recommendation} ${card.reason ?? card.whyItMatters ?? ""}`,
          })}
          <button
            class="suggestion-expand-button"
            type="button"
            data-suggestion-toggle="${escapeHtml(card.id)}"
            aria-expanded="${isExpanded ? "true" : "false"}"
            aria-controls="${escapeHtml(detailId)}"
            aria-label="${isExpanded ? "Collapse" : "Expand"} ${escapeHtml(card.title)}"
          >
            <span class="suggestion-chevron" aria-hidden="true"></span>
          </button>
        </div>
      </div>
      <div id="${escapeHtml(detailId)}" class="suggestion-detail" ${isExpanded ? "" : "hidden"}>
        <div class="suggestion-rationale">
          <span>Because</span>
          <p>${escapeHtml(card.reason ?? card.whyItMatters)}</p>
        </div>
        <div class="evidence-list">
          ${card.evidence
            .map(
              (item) => `
                <div class="evidence-item">
                  <span class="evidence-label">${escapeHtml(item.label)}</span>
                  <span class="evidence-value">${escapeHtml(item.value)}</span>
                  ${item.comparison ? `<span class="evidence-comparison">${escapeHtml(item.comparison)}</span>` : ""}
                </div>
              `,
            )
            .join("")}
        </div>
      </div>
    </article>
  `;
}

function renderActionReview(cards) {
  const activeCard = cards.find((card) => card.id === state.activeSuggestionId);

  if (!activeCard) {
    actionReview.hidden = true;
    actionReviewCopyStatus.textContent = "";
    return;
  }

  const steps = activeCard.action?.steps ?? [];
  const copyText = activeCard.action?.copyText ?? activeCard.recommendation;

  actionReview.hidden = false;
  actionReviewTitle.textContent = activeCard.action?.reviewTitle ?? activeCard.title;
  actionReviewMeta.textContent = `${activeCard.label} · ${activeCard.confidence} confidence · ready`;
  actionReviewCopy.textContent = copyText;
  actionReviewCopyButton.dataset.copyText = copyText;
  actionReviewCopyStatus.textContent = "";
  actionReviewSteps.innerHTML = steps
    .map((step) => `<li>${escapeHtml(step)}</li>`)
    .join("");
}

function render() {
  const product = getSelectedProduct();
  const metrics = buildProductMetrics(product);

  renderPeriodSummary();
  renderProductHeader(product);
  renderMetrics(product, metrics);
  renderProductPortfolio();
  renderChart(product, metrics);
  renderSources(product, metrics);
  renderSalesDashboard(product, metrics);
  renderRefundOps(product, metrics);
  renderContentRadar(product, metrics);
  renderRetentionSaver(product, metrics);
  renderAdminPreview(product, metrics);
  renderShortestQa(product, metrics);
  renderSuggestions(product, metrics);
  decorateSubsectionAgentButtons();
  syncMerchantContext();
}

function activeMerchantSession() {
  return findMerchantSessionById(state.merchantSessionId);
}

function findMerchantSessionById(sessionId) {
  const normalized = String(sessionId ?? "").trim();
  if (!normalized) return null;

  return [...state.merchantSessions.recent, ...state.merchantSessions.saved].find(
    (session) => session.id === normalized,
  ) ?? null;
}

function merchantLocalMessageCount() {
  return state.merchantMessages.filter((message) => message.id !== INITIAL_MERCHANT_MESSAGE.id).length;
}

function merchantSessionIsManageable(session = activeMerchantSession()) {
  return Number(session?.message_count ?? 0) > 0 || merchantLocalMessageCount() > 0;
}

function merchantSessionTitle(session) {
  if (!session) return "New conversation";
  const title = String(session.title ?? "").trim();

  if (!title || title === "Gumroad Merchant") {
    return session.message_count > 0 ? "Untitled conversation" : "New conversation";
  }

  return title;
}

function formatSessionDate(value) {
  if (!value) return "No messages";
  const date = new Date(value);

  if (Number.isNaN(date.valueOf())) {
    return "Local";
  }

  return new Intl.DateTimeFormat([], {
    month: "short",
    day: "numeric",
  }).format(date);
}

function renderMerchantSessionList(sessions, element, emptyText) {
  if (!element) return;

  if (!sessions.length) {
    element.innerHTML = `<p class="merchant-session-empty">${escapeHtml(emptyText)}</p>`;
    return;
  }

  element.innerHTML = sessions
    .map((session) => {
      const isActive = session.id === state.merchantSessionId;
      const isSaved = Boolean(session.saved_at);
      const title = merchantSessionTitle(session);
      const lastTouched = session.latest_message_at ?? session.updated_at ?? session.created_at;

      return `
        <article
          class="merchant-session-item ${isActive ? "active" : ""}"
        >
          <button
            class="merchant-session-main"
            type="button"
            data-merchant-session-id="${escapeHtml(session.id)}"
            aria-pressed="${isActive ? "true" : "false"}"
          >
            <span class="merchant-session-title">${escapeHtml(title)}</span>
            <span class="merchant-session-meta">
              ${escapeHtml(formatSessionDate(lastTouched))} · ${Number(session.message_count ?? 0).toLocaleString()} msgs${isSaved ? " · saved" : ""}
            </span>
          </button>
        </article>
      `;
    })
    .join("");
}

function renderMerchantSessions() {
  const currentSession = activeMerchantSession();
  const saved = Boolean(currentSession?.saved_at);
  const activeView = state.merchantSessionView === "saved" ? "saved" : "recent";
  merchantSessionTabs.forEach((tab) => {
    const isActive = tab.dataset.merchantSessionView === activeView;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-pressed", isActive ? "true" : "false");
    const label = tab.querySelector("[data-merchant-session-count]");
    if (label && tab.dataset.merchantSessionView === "recent") {
      label.textContent = `${MERCHANT_RECENT_SESSION_LIMIT} max`;
    }
    if (label && tab.dataset.merchantSessionView === "saved") {
      label.textContent = `${state.merchantSessions.saved.length.toLocaleString()} saved`;
    }
  });
  merchantSessionPanels.forEach((panel) => {
    panel.hidden = panel.dataset.merchantSessionPanel !== activeView;
  });

  renderMerchantSessionList(
    state.merchantSessions.recent,
    merchantSessionList,
    state.merchantSessionsLoading ? "Loading recent chats" : "No recent chats yet",
  );
  renderMerchantSessionList(
    state.merchantSessions.saved,
    merchantSavedSessionList,
    state.merchantSessionsLoading ? "Loading saved chats" : "No saved chats yet",
  );

  merchantSaveChatButton.textContent = saved ? "Unsave" : "Save";
  const canManageCurrentSession = Boolean(state.merchantSessionId) && merchantSessionIsManageable(currentSession);
  merchantSaveChatButton.disabled = !canManageCurrentSession || state.merchantSending;
  merchantRenameChatButton.disabled = !canManageCurrentSession || state.merchantSending;
  merchantDeleteChatButton.disabled = !canManageCurrentSession || state.merchantSending;
}

function renderMerchantChat() {
  const messageMarkup = state.merchantMessages
    .map((message) => {
      const citations = Array.isArray(message.citations) ? message.citations : [];
      const followups = Array.isArray(message.followups) ? message.followups : [];
      const isAssistant = message.role === "assistant";

      return `
        <article class="merchant-message ${escapeHtml(message.role)}">
          ${
            isAssistant
              ? `<div class="merchant-message-avatar" aria-hidden="true">
                  <img src="./assets/gumroad-merchant-icon.png" alt="" />
                </div>`
              : ""
          }
          <div class="merchant-message-body">
            ${renderMerchantMessageContent(message.content)}
            ${
              citations.length
                ? `<div class="merchant-citations">
                    ${citations
                      .map(
                        (citationItem) => `
                          <span title="${escapeHtml(citationItem.excerpt ?? "")}">
                            ${escapeHtml(citationItem.label)}
                          </span>
                        `,
                      )
                      .join("")}
                  </div>`
                : ""
            }
            ${
              message.role === "assistant" && followups.length
                ? `<div class="merchant-followups" aria-label="Suggested follow-up prompts">
                    ${followups
                      .map(
                        (followup) => `
                          <button class="merchant-followup-button" type="button" data-merchant-prompt="${escapeHtml(followup)}">
                            ${escapeHtml(followup)}
                          </button>
                        `,
                      )
                      .join("")}
                  </div>`
                : ""
            }
          </div>
        </article>
      `;
    })
    .join("");

  const thinkingMarkup = state.merchantSending
    ? `
      <article class="merchant-message assistant merchant-message-thinking" aria-live="polite" aria-label="Gumroad Merchant is thinking">
        <div class="merchant-message-avatar" aria-hidden="true">
          <img src="./assets/gumroad-merchant-icon.png" alt="" />
        </div>
        <div class="merchant-message-body">
          <div class="merchant-thinking-indicator">
            <span>Thinking</span>
            <span class="merchant-thinking-dots" aria-hidden="true">
              <i></i>
              <i></i>
              <i></i>
            </span>
          </div>
        </div>
      </article>
    `
    : "";

  merchantMessages.innerHTML = `${messageMarkup}${thinkingMarkup}`;
  merchantMessages.scrollTop = merchantMessages.scrollHeight;
  merchantSamples.hidden =
    state.merchantSamplesDismissed || state.merchantMessages.length > 1;
  merchantChatSubmit.disabled =
    state.merchantSending || !merchantChatInput.value.trim();
  setMerchantFullscreen(state.merchantChatFullscreen);
  renderMerchantSessions();
}

async function initMerchantChat() {
  renderMerchantChat();
  const existingSessionId = window.localStorage.getItem(MERCHANT_SESSION_STORAGE_KEY) ?? "";

  try {
    merchantStatus.textContent = "Syncing";
    await merchantFetch("/api/agent/data/refresh?force=true", {
      method: "POST",
    });
    const session = await merchantFetch(
      `/api/agent/chat/session?${new URLSearchParams({
        session_id: existingSessionId,
        product_id: state.selectedProductId,
        date_range: getBackendDateRange(),
      })}`
    );
    state.merchantSessionId = session.session_id;
    window.localStorage.setItem(MERCHANT_SESSION_STORAGE_KEY, session.session_id);
    merchantStatus.textContent = "Ready";
    try {
      await loadMerchantHistory();
    } catch {
      state.merchantMessages = initialMerchantMessages();
      state.merchantSamplesDismissed = false;
    }
  } catch {
    merchantStatus.textContent = "Offline";
  }

  await loadMerchantSessions();
  await initMerchantVoice();
  renderMerchantChat();
}

async function loadMerchantHistory() {
  if (!state.merchantSessionId) {
    return;
  }

  const history = await merchantFetch(
    `/api/agent/chat/history?${new URLSearchParams({
      session_id: state.merchantSessionId,
      limit: "50",
    })}`
  );

  if (Array.isArray(history.messages) && history.messages.length > 0) {
    state.merchantMessages = history.messages.map((message) => ({
      id: `history-${message.id}`,
      role: message.role,
      content: message.content,
      citations: message.citations ?? [],
      followups: message.followups ?? [],
    }));
    state.merchantSamplesDismissed = true;
  } else {
    state.merchantMessages = initialMerchantMessages();
    state.merchantSamplesDismissed = false;
  }
}

async function loadMerchantSessions() {
  state.merchantSessionsLoading = true;
  renderMerchantSessions();

  try {
    const sessions = await merchantFetch(
      `/api/agent/chat/sessions?${new URLSearchParams({
        recent_limit: String(MERCHANT_RECENT_SESSION_LIMIT),
        saved_limit: String(MERCHANT_SAVED_SESSION_LIMIT),
      })}`
    );
    state.merchantSessions = {
      recent: Array.isArray(sessions.recent) ? sessions.recent : [],
      saved: Array.isArray(sessions.saved) ? sessions.saved : [],
    };
  } catch {
    state.merchantSessions = {
      recent: [],
      saved: [],
    };
  } finally {
    state.merchantSessionsLoading = false;
    renderMerchantSessions();
  }
}

async function submitMerchantMessage(value) {
  const message = value.trim();

  if (!message || state.merchantSending) {
    return;
  }

  state.merchantSamplesDismissed = true;
  state.merchantSending = true;
  state.merchantMessages.push({
    id: `user-${Date.now()}`,
    role: "user",
    content: message,
    citations: [],
  });
  merchantChatInput.value = "";
  merchantStatus.textContent = "Thinking";
  renderMerchantChat();

  try {
    const response = await merchantFetch("/api/agent/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: state.merchantSessionId,
        product_id: state.selectedProductId,
        date_range: getBackendDateRange(),
      }),
    });

    state.merchantSessionId = response.session_id;
    window.localStorage.setItem(MERCHANT_SESSION_STORAGE_KEY, response.session_id);
    state.merchantMessages.push({
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: response.answer,
      citations: response.citations ?? [],
      followups: buildMerchantFollowups(message),
    });
    merchantStatus.textContent = response.fallback ? "Cited" : "Live";
    await loadAnalyticsDataset({ silent: true });
    await loadMerchantSessions();
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Chat request failed.";
    state.merchantMessages.push({
      id: `assistant-error-${Date.now()}`,
      role: "assistant",
      content: `I cannot reach the Gumroad Merchant backend yet. Start the API server, then try again. ${detail}`,
      citations: [],
      followups: [
        "Retry this after the API server is running.",
        "Show me the local fallback demo path.",
      ],
    });
    merchantStatus.textContent = "Offline";
  } finally {
    state.merchantSending = false;
    renderMerchantChat();
    merchantChatInput.focus();
  }
}

async function createNewMerchantChat() {
  if (state.merchantSending) {
    return;
  }

  try {
    merchantStatus.textContent = "Syncing";
    const session = await merchantFetch(
      `/api/agent/chat/session?${new URLSearchParams({
        product_id: state.selectedProductId,
        date_range: getBackendDateRange(),
      })}`
    );
    state.merchantSessionId = session.session_id;
    window.localStorage.setItem(MERCHANT_SESSION_STORAGE_KEY, session.session_id);
    state.merchantMessages = initialMerchantMessages();
    state.merchantSamplesDismissed = false;
    state.merchantSessionView = "recent";
    merchantChatInput.value = "";
    merchantStatus.textContent = "Ready";
    await loadMerchantSessions();
  } catch {
    merchantStatus.textContent = "Offline";
  } finally {
    renderMerchantChat();
    merchantChatInput.focus();
  }
}

async function loadMerchantSession(sessionId) {
  const normalized = String(sessionId ?? "").trim();

  if (!normalized || normalized === state.merchantSessionId || state.merchantSending) {
    return;
  }

  try {
    merchantStatus.textContent = "Syncing";
    await merchantFetch(
      `/api/agent/chat/session?${new URLSearchParams({
        session_id: normalized,
        product_id: state.selectedProductId,
        date_range: getBackendDateRange(),
      })}`
    );
    state.merchantSessionId = normalized;
    window.localStorage.setItem(MERCHANT_SESSION_STORAGE_KEY, normalized);
    await loadMerchantHistory();
    await loadMerchantSessions();
    merchantStatus.textContent = "Ready";
  } catch {
    merchantStatus.textContent = "Offline";
  } finally {
    renderMerchantChat();
    merchantChatInput.focus();
  }
}

async function toggleSaveMerchantSession(sessionId = state.merchantSessionId, explicitSaved = null) {
  const normalized = String(sessionId ?? "").trim();

  if (!normalized || state.merchantSending) {
    return;
  }

  const currentSession = findMerchantSessionById(normalized);
  const isCurrentSession = normalized === state.merchantSessionId;
  const canManageTarget = Number(currentSession?.message_count ?? 0) > 0
    || (isCurrentSession && merchantLocalMessageCount() > 0);

  if (!canManageTarget) {
    merchantStatus.textContent = "Send first";
    renderMerchantChat();
    return;
  }

  const nextSaved =
    typeof explicitSaved === "boolean" ? explicitSaved : !Boolean(currentSession?.saved_at);

  try {
    merchantStatus.textContent = nextSaved ? "Saving" : "Unsaving";
    await merchantFetch(`/api/agent/chat/sessions/${encodeURIComponent(normalized)}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ saved: nextSaved }),
    });
    if (isCurrentSession && nextSaved) {
      state.merchantSessionView = "saved";
    }
    await loadMerchantSessions();
    merchantStatus.textContent = "Ready";
  } catch {
    merchantStatus.textContent = "Offline";
  } finally {
    renderMerchantChat();
  }
}

async function renameMerchantSession() {
  if (!state.merchantSessionId || state.merchantSending) {
    return;
  }

  const currentSession = activeMerchantSession();
  const nextTitle = window.prompt("Conversation name", merchantSessionTitle(currentSession));
  const cleanedTitle = String(nextTitle ?? "").trim();

  if (!cleanedTitle) {
    return;
  }

  try {
    merchantStatus.textContent = "Renaming";
    await merchantFetch(`/api/agent/chat/sessions/${encodeURIComponent(state.merchantSessionId)}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: cleanedTitle }),
    });
    await loadMerchantSessions();
    merchantStatus.textContent = "Ready";
  } catch {
    merchantStatus.textContent = "Offline";
  } finally {
    renderMerchantChat();
  }
}

async function deleteMerchantSession(sessionId = state.merchantSessionId) {
  const normalized = String(sessionId ?? "").trim();

  if (!normalized || state.merchantSending) {
    return;
  }

  const currentSession = findMerchantSessionById(normalized);
  const isCurrentSession = normalized === state.merchantSessionId;
  const canManageTarget = Number(currentSession?.message_count ?? 0) > 0
    || (isCurrentSession && merchantLocalMessageCount() > 0);

  if (!canManageTarget) {
    merchantStatus.textContent = "Nothing to delete";
    renderMerchantChat();
    return;
  }

  const confirmed = window.confirm(`Delete "${merchantSessionTitle(currentSession)}" from this demo?`);

  if (!confirmed) {
    return;
  }

  try {
    merchantStatus.textContent = "Deleting";
    await merchantFetch(`/api/agent/chat/sessions/${encodeURIComponent(normalized)}`, {
      method: "DELETE",
    });
    if (isCurrentSession) {
      state.merchantSessionId = "";
      window.localStorage.removeItem(MERCHANT_SESSION_STORAGE_KEY);
      state.merchantMessages = initialMerchantMessages();
      state.merchantSamplesDismissed = false;
      await loadMerchantSessions();
      merchantStatus.textContent = "Ready";
      renderMerchantChat();
    } else {
      await loadMerchantSessions();
      merchantStatus.textContent = "Ready";
      renderMerchantChat();
    }
  } catch {
    merchantStatus.textContent = "Offline";
    renderMerchantChat();
  }
}

async function initMerchantVoice() {
  try {
    const response = await merchantFetch("/api/voice/client-secret", {
      method: "POST",
    });
    merchantVoiceRow.hidden = !(response.enabled && response.configured);
  } catch {
    merchantVoiceRow.hidden = true;
  }
}

function syncMerchantContext() {
  if (!state.merchantSessionId) {
    return;
  }
  merchantFetch(
    `/api/agent/chat/session?${new URLSearchParams({
      session_id: state.merchantSessionId,
      product_id: state.selectedProductId,
      date_range: getBackendDateRange(),
    })}`
  ).catch(() => {
    // Context sync is a convenience; chat submission still sends current context.
  });
}

async function merchantFetch(path, options = {}) {
  const response = await fetch(`${MERCHANT_API_BASE}${path}`, options);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function toNumber(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function centsFromPayload(payload, fallback = 0) {
  if (payload && typeof payload === "object") {
    return toNumber(payload.cents, fallback);
  }

  return toNumber(payload, fallback);
}

function formattedMoney(payload, fallbackCents = 0, currency = "USD") {
  if (payload && typeof payload === "object" && payload.formatted) {
    return String(payload.formatted);
  }

  return formatCurrency(centsFromPayload(payload, fallbackCents), currency);
}

function formatBackendEvidence(item) {
  if (!item || typeof item !== "object") {
    return String(item ?? "");
  }

  const label = item.label ?? item.check ?? item.title ?? "Evidence";
  const value = item.value ?? item.detail ?? item.status ?? "";
  const comparison = item.comparison ? ` · ${item.comparison}` : "";
  return `${label}: ${value}${comparison}`;
}

function formatRiskDetail(item) {
  if (!item || typeof item !== "object") {
    return String(item ?? "");
  }

  const label = item.label ?? item.risk_level ?? "Risk";
  const detail = item.detail ?? item.description ?? item.value ?? "";
  return detail ? `${label}: ${detail}` : String(label);
}

function renderInsightSourceNote() {
  if (state.featureInsights.loading) {
    return "Loading live calculations";
  }

  return currentFeatureInsights() ? "SQLite calculated" : "Static seed fallback";
}

function getBackendDateRange() {
  return state.dateRange === "custom" ? String(getRangeDays()) : String(state.dateRange || "30");
}

function getFeatureInsightsKey(productId = state.selectedProductId, dateRange = getBackendDateRange()) {
  return `${productId || "all"}::${dateRange || "30"}`;
}

function currentFeatureInsights() {
  const insights = state.featureInsights;
  return insights?.live && insights.key === getFeatureInsightsKey() ? insights : null;
}

function queryString(params, extras = {}) {
  const merged = new URLSearchParams(params);
  Object.entries(extras).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      merged.set(key, String(value));
    }
  });
  return merged.toString();
}

async function loadFeatureInsights({ silent = false } = {}) {
  const productId = state.selectedProductId;
  const dateRange = getBackendDateRange();
  const key = getFeatureInsightsKey(productId, dateRange);

  if (!state.analyticsSource.live) {
    state.featureInsights = createEmptyFeatureInsights({
      key,
      error: "Analytics backend unavailable.",
    });
    if (!silent) render();
    return;
  }

  const requestId = ++featureInsightsRequestId;
  const previous = state.featureInsights;
  state.featureInsights = createEmptyFeatureInsights({
    ...previous,
    key,
    live: false,
    loading: true,
    error: "",
  });

  if (!silent) {
    render();
  }

  const scopedParams = new URLSearchParams({
    product_id: productId,
    date_range: dateRange,
  });

  try {
    const [
      analyticsSummary,
      contentSummary,
      contentTrends,
      refundSummary,
      refundCases,
      refundPrevention,
      retentionSummary,
      retentionRisks,
      adminSummary,
      adminTemplates,
      qaSummary,
      qaSuites,
      qaTests,
    ] = await Promise.all([
      merchantFetch(`/api/analytics/summary?${queryString(scopedParams)}`),
      merchantFetch(`/api/content-radar/summary?${queryString(scopedParams)}`),
      merchantFetch(`/api/content-radar/trends?${queryString(scopedParams, { limit: 8 })}`),
      merchantFetch(`/api/refund-ops/summary?${queryString(scopedParams)}`),
      merchantFetch(`/api/refund-ops/cases?${queryString(scopedParams, { mode: "all", limit: 25 })}`),
      merchantFetch(`/api/refund-ops/prevention-actions?${queryString(scopedParams)}`),
      merchantFetch(`/api/retention-saver/summary?${queryString(scopedParams)}`),
      merchantFetch(`/api/retention-saver/risks?${queryString(scopedParams, { limit: 10 })}`),
      merchantFetch(`/api/admin-preview/summary?${queryString(new URLSearchParams({ product_id: productId, limit: "12" }))}`),
      merchantFetch("/api/admin-preview/templates"),
      merchantFetch("/api/shortest-qa/summary"),
      merchantFetch("/api/shortest-qa/suites"),
      merchantFetch(`/api/shortest-qa/tests?${queryString(new URLSearchParams({ suite_id: "all", limit: "20" }))}`),
    ]);

    if (requestId !== featureInsightsRequestId) {
      return;
    }

    state.featureInsights = createEmptyFeatureInsights({
      key,
      live: true,
      loading: false,
      analyticsSummary: analyticsSummary.data ?? null,
      contentRadar: {
        summary: contentSummary.data ?? null,
        trends: asArray(contentTrends.items),
      },
      refundOps: {
        summary: refundSummary.data ?? null,
        cases: asArray(refundCases.cases),
        preventionActions: asArray(refundPrevention.data?.actions),
      },
      retention: {
        summary: retentionSummary.data ?? null,
        risks: asArray(retentionRisks.items),
      },
      admin: {
        summary: adminSummary.data ?? null,
        templates: asArray(adminTemplates.items),
      },
      qa: {
        summary: qaSummary.data ?? null,
        suites: asArray(qaSuites.items),
        tests: asArray(qaTests.data?.tests),
      },
    });
    render();
  } catch (error) {
    if (requestId !== featureInsightsRequestId) {
      return;
    }

    state.featureInsights = createEmptyFeatureInsights({
      key,
      live: false,
      loading: false,
      error: error instanceof Error ? error.message : "Feature insight request failed.",
    });
    render();
  }
}

async function loadAnalyticsDataset({ silent = false } = {}) {
  try {
    const payload = await merchantFetch("/api/analytics/products");
    if (Array.isArray(payload.products) && payload.products.length > 0) {
      products = payload.products;
    }
    if (payload.dashboardData && typeof payload.dashboardData === "object") {
      setSalesDashboardData(payload.dashboardData);
    }
    if (state.selectedProductId !== "all" && !products.some((product) => product.id === state.selectedProductId)) {
      state.selectedProductId = "all";
    }
    state.analyticsSource = {
      label: "SQLite evidence store",
      live: true,
      trackedCampaignCount: Number(payload.trackedCampaignCount ?? 0),
    };
    renderProductOptions();
    render();
    await loadFeatureInsights({ silent: true });
  } catch {
    state.analyticsSource = {
      label: "Static seed fallback",
      live: false,
      trackedCampaignCount: 0,
    };
    state.featureInsights = createEmptyFeatureInsights({
      key: getFeatureInsightsKey(),
      error: "Analytics backend unavailable.",
    });
    if (!silent) {
      render();
    }
  }
}

function formatDelta(value, suffix) {
  if (!Number.isFinite(value)) {
    return `No ${suffix} comparison`;
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatPercent(value)} vs ${suffix}`;
}

function deltaTone(text) {
  if (text.trim().startsWith("+")) return "good";
  if (text.trim().startsWith("0")) return "";
  return "warn";
}

function parseDateInput(value) {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(Date.UTC(year, month - 1, day));
}

function normalizeCustomDateRange() {
  const start = parseDateInput(state.customStartDate);
  const end = parseDateInput(state.customEndDate);

  if (!start || !end) {
    state.customStartDate = defaultCustomStartDate;
    state.customEndDate = defaultCustomEndDate;
    return;
  }

  if (start > end) {
    state.customStartDate = toDateInputValue(end);
    state.customEndDate = toDateInputValue(start);
  }
}

function syncCustomDatesToPreset(dateRange) {
  if (dateRange === "custom") return;

  const { start, end } = getTrailingDateRange(
    dateRangeCopy[dateRange]?.days ?? dateRangeCopy["30"].days
  );

  state.customStartDate = start;
  state.customEndDate = end;
}

function getCustomRangeDays() {
  normalizeCustomDateRange();
  const start = parseDateInput(state.customStartDate);
  const end = parseDateInput(state.customEndDate);

  if (!start || !end) return dateRangeCopy.custom.days;
  return Math.max(1, Math.round((end - start) / DAY_MS) + 1);
}

function getRangeDays() {
  if (state.dateRange === "custom") return getCustomRangeDays();
  return dateRangeCopy[state.dateRange]?.days ?? dateRangeCopy["30"].days;
}

function roundDisplay(value) {
  return value >= 10 ? Math.round(value) : Number(value.toFixed(1));
}

function getSortedSources(metrics) {
  const accessors = {
    revenue: (source) => source.revenueCents,
    views: (source) => source.views,
    sales: (source) => source.sales,
    conversion: (source) => source.conversion,
    source: (source) => source.name.toLowerCase(),
  };
  const getValue = accessors[state.sourceSort] ?? accessors.revenue;

  return [...metrics.currentSources].sort((left, right) => {
    const leftValue = getValue(left);
    const rightValue = getValue(right);

    if (typeof leftValue === "string" || typeof rightValue === "string") {
      return String(leftValue).localeCompare(String(rightValue));
    }

    if (rightValue !== leftValue) return rightValue - leftValue;
    return right.revenueCents - left.revenueCents;
  });
}

function renderChartDetail() {
  chartDetailPanel.hidden = true;
  chartSourceBreakdown.innerHTML = "";
}

function sortByDirection(items, getValue, direction) {
  const multiplier = direction === "asc" ? 1 : -1;

  return [...items].sort((left, right) => {
    const delta = getValue(left) - getValue(right);
    if (delta !== 0) return delta * multiplier;
    return 0;
  });
}

function toggleDirection(direction) {
  return direction === "desc" ? "asc" : "desc";
}

function updateSortButton(button, direction, label) {
  if (!button) {
    return;
  }

  const highToLow = direction === "desc";
  button.classList.toggle("ascending", !highToLow);
  button.setAttribute(
    "aria-label",
    `Sort ${label} from ${highToLow ? "lowest to highest" : "highest to lowest"}`
  );
  button.setAttribute("aria-pressed", String(highToLow));
}

function formatStatus(value) {
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeMerchantMessageContent(content) {
  const raw = String(content ?? "").trim();

  if (!raw) {
    return "";
  }

  if (/\n/.test(raw)) {
    return raw;
  }

  return raw
    .replace(/\s+(First prevention move:|Recommended action:|Audit note:|Copy packet:|Tracking URL:|Risk covered:|Execution note:|Suggested action:|Blocked reason:|Sources:)/g, "\n\n$1")
    .replace(/\. (The top case|Top Refund Ops cases|Start with|Week 1 move|Because this|This result|No email|No admin action|These are natural-language|My first next move|Churn is also readable|The SQLite snapshot|I query it)/g, ".\n\n$1")
    .replace(/; (?=[A-Z][A-Za-z0-9 /-]{2,48}:)/g, "\n- ");
}

function renderMerchantMessageContent(content) {
  const blocks = normalizeMerchantMessageContent(content)
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);

  if (!blocks.length) {
    return "<p></p>";
  }

  return blocks
    .map((block) => {
      const lines = block
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      const heading = block.match(/^(#{1,3})\s+(.+)$/);

      if (heading) {
        return `<h4>${escapeHtml(heading[2])}</h4>`;
      }

      const isList =
        lines.length > 1 &&
        lines.every((line) => /^([-*]\s+|\d+[.)]\s+)/.test(line));
      const isKeyValue =
        lines.length > 1 &&
        lines.every((line) => /^[A-Z][A-Za-z0-9 /-]{2,48}:\s+/.test(line));

      if (isList) {
        return `<ul>${lines
          .map((line) => `<li>${escapeHtml(line.replace(/^([-*]\s+|\d+[.)]\s+)/, ""))}</li>`)
          .join("")}</ul>`;
      }

      if (isKeyValue) {
        return `<dl class="merchant-key-values">${lines
          .map((line) => {
            const [label, ...rest] = line.split(":");
            return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(rest.join(":").trim())}</dd></div>`;
          })
          .join("")}</dl>`;
      }

      return `<p>${escapeHtml(block).replaceAll("\n", "<br>")}</p>`;
    })
    .join("");
}

function clampMerchantTranscriptHeight(value) {
  const minHeight = window.matchMedia("(max-width: 760px)").matches
    ? MERCHANT_TRANSCRIPT_MOBILE_MIN_HEIGHT
    : MERCHANT_TRANSCRIPT_MIN_HEIGHT;
  const viewportMax = Math.max(minHeight, window.innerHeight - 180);
  return Math.max(minHeight, Math.min(Math.round(value), Math.min(760, viewportMax)));
}

function setMerchantTranscriptHeight(value) {
  const height = clampMerchantTranscriptHeight(value);
  state.merchantTranscriptHeight = height;
  merchantChatShell?.style.setProperty("--merchant-chat-height", `${height}px`);
  merchantMessages.style.setProperty("--merchant-chat-height", `${height}px`);
  window.localStorage.setItem(MERCHANT_TRANSCRIPT_HEIGHT_STORAGE_KEY, String(height));
}

function setMerchantFullscreen(open) {
  if (open && merchantPanel.classList.contains("is-collapsed")) {
    toggleSignalPanel(merchantPanel, true);
  }

  state.merchantChatFullscreen = open;
  merchantPanel.classList.toggle("is-fullscreen", open);
  document.body.classList.toggle("merchant-chat-fullscreen-open", open);

  if (merchantFullscreenButton) {
    merchantFullscreenButton.textContent = open ? "Exit" : "Expand";
    merchantFullscreenButton.setAttribute("aria-pressed", String(open));
  }
}

function setMerchantRailCollapsed(collapsed, persist = true) {
  state.merchantRailCollapsed = Boolean(collapsed);
  merchantLanesGroup?.classList.toggle("is-merchant-rail-collapsed", state.merchantRailCollapsed);

  if (merchantRailToggle) {
    const actionLabel = state.merchantRailCollapsed ? "Expand merchant menu" : "Collapse merchant menu";
    merchantRailToggle.setAttribute("aria-expanded", String(!state.merchantRailCollapsed));
    merchantRailToggle.setAttribute("aria-label", actionLabel);
    merchantRailToggle.title = actionLabel;
    const toggleLabel = merchantRailToggle.querySelector(".merchant-rail-toggle-label");
    if (toggleLabel) {
      toggleLabel.textContent = state.merchantRailCollapsed ? "Expand menu" : "Collapse menu";
    }
  }

  if (persist) {
    window.localStorage.setItem(
      MERCHANT_RAIL_COLLAPSED_STORAGE_KEY,
      state.merchantRailCollapsed ? "true" : "false",
    );
  }
}

function resetRangeScopedState() {
  state.activeSuggestionId = null;
  state.expandedSuggestionIds.clear();
  state.activeRefundCaseId = null;
  state.activeContentTrendId = null;
  state.activeAdminActionId = null;
  state.activeQaSuiteId = null;
}

function setDateRange(dateRange) {
  if (!dateRangeCopy[dateRange]) return;

  state.dateRange = dateRange;
  if (dateRange === "custom") {
    normalizeCustomDateRange();
  } else {
    syncCustomDatesToPreset(dateRange);
  }
  resetRangeScopedState();
  render();
  void loadFeatureInsights({ silent: true });
}

productSelect.addEventListener("change", (event) => {
  state.selectedProductId = event.target.value;
  state.generated = true;
  resetRangeScopedState();
  render();
  void loadFeatureInsights({ silent: true });
});

portfolioTabs?.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-portfolio-product-id]");
  if (!tab) return;

  state.activePortfolioProductId = tab.dataset.portfolioProductId;
  renderProductPortfolio();
});

dateRangeSelect?.addEventListener("change", (event) => {
  setDateRange(event.target.value);
});

chartRangeSelect?.addEventListener("change", (event) => {
  setDateRange(event.target.value);
});

chartMetricButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const metricKey = button.dataset.chartMetric;

    if (!trendChartMetrics[metricKey]) {
      return;
    }

    state.activeTrendMetric = metricKey;
    render();
  });
});

customStartDate?.addEventListener("input", (event) => {
  if (!event.target.value) return;
  state.customStartDate = event.target.value;
  setDateRange("custom");
});

customStartDate?.addEventListener("change", (event) => {
  state.customStartDate = event.target.value || defaultCustomStartDate;
  setDateRange("custom");
});

customEndDate?.addEventListener("input", (event) => {
  if (!event.target.value) return;
  state.customEndDate = event.target.value;
  setDateRange("custom");
});

customEndDate?.addEventListener("change", (event) => {
  state.customEndDate = event.target.value || defaultCustomEndDate;
  setDateRange("custom");
});

locationScopeSelect.addEventListener("change", (event) => {
  state.locationScope = event.target.value;
  render();
});

sourceSortSelect.addEventListener("change", (event) => {
  state.sourceSort = event.target.value;
  render();
});

refundModeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.refundMode = button.dataset.refundMode ?? "prevent";
    state.activeRefundCaseId = null;
    render();
  });
});

refundCaseList.addEventListener("click", (event) => {
  const caseButton = event.target.closest("[data-refund-case-id]");

  if (!caseButton) {
    return;
  }

  state.activeRefundCaseId = caseButton.dataset.refundCaseId;
  render();
});

refundCaseDetail.addEventListener("click", async (event) => {
  const copyButton = event.target.closest("[data-refund-copy]");

  if (!copyButton) {
    return;
  }

  const copyText = copyButton.dataset.refundCopy ?? "";
  const status = refundCaseDetail.querySelector("#refund-copy-status");

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(copyText);
    } else {
      copyWithFallback(copyText);
    }
    if (status) status.textContent = "Copied";
  } catch {
    copyWithFallback(copyText);
    if (status) status.textContent = "Copied";
  }
});

contentTrendList.addEventListener("click", (event) => {
  const trendButton = event.target.closest("[data-content-trend-id]");

  if (!trendButton) {
    return;
  }

  state.activeContentTrendId = trendButton.dataset.contentTrendId;
  render();
});

adminActionList?.addEventListener("click", (event) => {
  const actionButton = event.target.closest("[data-admin-action-id]");

  if (!actionButton) {
    return;
  }

  state.activeAdminActionId = actionButton.dataset.adminActionId;
  render();
});

shortestQaList.addEventListener("click", (event) => {
  const suiteButton = event.target.closest("[data-qa-suite-id]");

  if (!suiteButton) {
    return;
  }

  state.activeQaSuiteId = suiteButton.dataset.qaSuiteId;
  render();
});

document.addEventListener("click", (event) => {
  const workspaceLink = event.target.closest("[data-dashboard-view], [data-embedded-page]");

  if (!workspaceLink) {
    return;
  }

  event.preventDefault();

  if (workspaceLink.dataset.dashboardView === "dashboard") {
    showDashboardView();
    return;
  }

  showEmbeddedPage(workspaceLink.dataset.embeddedPage ?? "");
});

embeddedPageClose.addEventListener("click", () => {
  showDashboardView();
});

window.addEventListener("popstate", syncWorkspaceViewFromHash);
window.addEventListener("hashchange", syncWorkspaceViewFromHash);

document.addEventListener("click", (event) => {
  const promptKeyButton = event.target.closest("[data-merchant-prompt-key]");
  const promptButton = event.target.closest("[data-merchant-prompt]");

  if (promptKeyButton) {
    event.preventDefault();
    event.stopPropagation();
    stageMerchantPrompt(buildMerchantPrompt(promptKeyButton.dataset.merchantPromptKey, {
      sectionId: promptKeyButton.dataset.merchantSectionId,
    }));
    return;
  }

  if (promptButton) {
    event.preventDefault();
    event.stopPropagation();
    stageMerchantPrompt(promptButton.dataset.merchantPrompt ?? "");
  }
});

document.addEventListener("click", async (event) => {
  const copyButton = event.target.closest("[data-copy-text]");

  if (!copyButton) {
    return;
  }

  const copyText = copyButton.dataset.copyText ?? "";
  if (!copyButton.dataset.originalLabel) {
    copyButton.dataset.originalLabel = copyButton.textContent ?? "Copy";
  }

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(copyText);
    } else {
      copyWithFallback(copyText);
    }
    copyButton.textContent = "Copied";
    window.setTimeout(() => {
      copyButton.textContent = copyButton.dataset.originalLabel ?? "Copy";
    }, 1200);
  } catch {
    copyWithFallback(copyText);
    copyButton.textContent = "Copied";
  }
});

themeToggle?.addEventListener("click", () => {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(nextTheme);
});

clickSignalClose?.addEventListener("click", () => {
  if (clickSignalHeader) {
    clickSignalHeader.hidden = true;
  }
});

locationSortButton?.addEventListener("click", () => {
  state.locationSortDirection = toggleDirection(state.locationSortDirection);
  render();
});

if (productTags) {
  productTags.addEventListener("click", (event) => {
    const shortcutButton = event.target.closest("[data-dashboard-shortcut]");

    if (!shortcutButton) {
      return;
    }

    const shortcut = shortcutButton.dataset.dashboardShortcut;

    if (shortcut === "all-products" && state.selectedProductId !== "all") {
      state.selectedProductId = "all";
      state.activeSuggestionId = null;
      resetRangeScopedState();
      render();
      void loadFeatureInsights({ silent: true });
    }

    window.requestAnimationFrame(() => {
      const target = revealDashboardTarget(dashboardShortcuts[shortcut]);

      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
}

suggestions.addEventListener("click", (event) => {
  const toggleButton = event.target.closest("[data-suggestion-toggle]");
  const actionButton = event.target.closest("[data-suggestion-action]");

  if (toggleButton) {
    const suggestionId = toggleButton.dataset.suggestionToggle;

    if (state.expandedSuggestionIds.has(suggestionId)) {
      state.expandedSuggestionIds.delete(suggestionId);
    } else {
      state.expandedSuggestionIds.add(suggestionId);
    }

    render();
    return;
  }

  if (!actionButton) {
    return;
  }

  state.activeSuggestionId = actionButton.dataset.suggestionAction;
  render();
});

actionReviewClose.addEventListener("click", () => {
  state.activeSuggestionId = null;
  render();
});

actionReviewCopyButton.addEventListener("click", async () => {
  const copyText = actionReviewCopyButton.dataset.copyText ?? "";

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(copyText);
    } else {
      copyWithFallback(copyText);
    }
    actionReviewCopyStatus.textContent = "Copied";
  } catch {
    copyWithFallback(copyText);
    actionReviewCopyStatus.textContent = "Copied";
  }
});

exportCsvButton.addEventListener("click", () => {
  const csv = exportCsvButton.dataset.csv ?? "";
  const filename = exportCsvButton.dataset.filename ?? "gumroad-sales-demo.csv";
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});

merchantChatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMerchantMessage(merchantChatInput.value);
});

merchantChatInput.addEventListener("input", renderMerchantChat);
merchantChatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    merchantChatForm.requestSubmit();
  }
});

merchantFullscreenButton?.addEventListener("click", () => {
  setMerchantFullscreen(!state.merchantChatFullscreen);
});

merchantRailToggle?.addEventListener("click", () => {
  setMerchantRailCollapsed(!state.merchantRailCollapsed);
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }

  if (state.merchantChatFullscreen) {
    setMerchantFullscreen(false);
  }
});

let merchantResizeState = null;

const savedMerchantTranscriptHeight = Number(
  window.localStorage.getItem(MERCHANT_TRANSCRIPT_HEIGHT_STORAGE_KEY)
);

if (Number.isFinite(savedMerchantTranscriptHeight) && savedMerchantTranscriptHeight > 0) {
  setMerchantTranscriptHeight(savedMerchantTranscriptHeight);
}

merchantResizeGrip.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  merchantResizeGrip.setPointerCapture(event.pointerId);
  merchantResizeState = {
    pointerId: event.pointerId,
    startY: event.clientY,
    startHeight: merchantMessages.getBoundingClientRect().height,
  };
});

merchantResizeGrip.addEventListener("pointermove", (event) => {
  if (!merchantResizeState || event.pointerId !== merchantResizeState.pointerId) {
    return;
  }

  setMerchantTranscriptHeight(
    merchantResizeState.startHeight + event.clientY - merchantResizeState.startY
  );
});

merchantResizeGrip.addEventListener("pointerup", (event) => {
  if (merchantResizeState?.pointerId === event.pointerId) {
    merchantResizeState = null;
  }
});

merchantResizeGrip.addEventListener("keydown", (event) => {
  if (event.key === "ArrowUp" || event.key === "ArrowDown") {
    event.preventDefault();
    const currentHeight = merchantMessages.getBoundingClientRect().height;
    setMerchantTranscriptHeight(currentHeight + (event.key === "ArrowDown" ? 36 : -36));
  }
});

merchantNewChatButton.addEventListener("click", createNewMerchantChat);
merchantSaveChatButton.addEventListener("click", () => {
  void toggleSaveMerchantSession();
});
merchantRenameChatButton.addEventListener("click", renameMerchantSession);
merchantDeleteChatButton.addEventListener("click", () => {
  void deleteMerchantSession();
});

merchantSessionTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    state.merchantSessionView = tab.dataset.merchantSessionView === "saved" ? "saved" : "recent";
    renderMerchantSessions();
  });
});

function handleMerchantSessionListClick(event) {
  const sessionButton = event.target.closest("[data-merchant-session-id]");

  if (!sessionButton) {
    return;
  }

  void loadMerchantSession(sessionButton.dataset.merchantSessionId ?? "");
}

merchantSessionList.addEventListener("click", handleMerchantSessionListClick);
merchantSavedSessionList.addEventListener("click", handleMerchantSessionListClick);

merchantSamples.addEventListener("click", (event) => {
  const sampleButton = event.target.closest("[data-merchant-question]");

  if (!sampleButton) {
    return;
  }

  stageMerchantPrompt(sampleButton.dataset.merchantQuestion ?? "");
});

merchantVoiceButton.addEventListener("click", () => {
  state.merchantMessages.push({
    id: `assistant-voice-${Date.now()}`,
    role: "assistant",
    content:
      "Voice is scaffolded behind the xAI feature flag, but the browser realtime flow is not enabled in this demo slice yet.",
    citations: [],
  });
  renderMerchantChat();
});

function copyWithFallback(value) {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.append(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function toCsv(columns, rows) {
  const escapeCell = (value) => {
    const text = String(value ?? "");
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };

  return [columns.join(","), ...rows.map((row) => columns.map((column) => escapeCell(row[column])).join(","))].join("\n");
}

setupSignalAccordions();
setupPanelGroups();
applyTheme(storedTheme());
setMerchantRailCollapsed(
  window.localStorage.getItem(MERCHANT_RAIL_COLLAPSED_STORAGE_KEY) === "true",
  false,
);
renderProductOptions();
render();
syncWorkspaceViewFromHash();
initMerchantChat();
loadAnalyticsDataset({ silent: true });
