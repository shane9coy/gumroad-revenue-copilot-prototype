const MIN_DESCRIPTION_LENGTH = 90;
const IDEAL_TAG_COUNT = 4;
const HIGH_TRAFFIC_VIEWS = 500;
const MIN_SOURCE_SALES = 5;
const REFUND_WARNING_RATE = 0.08;

const currencySymbols = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  CAD: "C$",
  AUD: "A$",
};

let salesDashboardData = {
  "prod-creator-os": {
    churn: {
      activeStart: 142,
      newSubscriptions: 18,
      canceled: 6,
      previousActiveStart: 131,
      previousNewSubscriptions: 12,
      previousCanceled: 3,
      revenueLostCents: 29400,
    },
    locations: [
      { country: "United States", region: "California", views: 590, sales: 18, revenueCents: 88200 },
      { country: "United Kingdom", region: "England", views: 210, sales: 6, revenueCents: 29400 },
      { country: "Canada", region: "Ontario", views: 170, sales: 5, revenueCents: 24500 },
      { country: "Australia", region: "Victoria", views: 95, sales: 3, revenueCents: 14700 },
    ],
    utmLinks: [
      { source: "youtube", medium: "video", campaign: "launch-review", destination: "Product page", clicks: 320, sales: 15, revenueCents: 73500 },
      { source: "newsletter", medium: "email", campaign: "creator-systems", destination: "Product page", clicks: 198, sales: 9, revenueCents: 44100 },
      { source: "gumroad", medium: "discover", campaign: "recommended", destination: "Product page", clicks: 620, sales: 8, revenueCents: 39200 },
    ],
  },
  "prod-design-kit": {
    churn: {
      activeStart: 88,
      newSubscriptions: 9,
      canceled: 2,
      previousActiveStart: 82,
      previousNewSubscriptions: 6,
      previousCanceled: 3,
      revenueLostCents: 5800,
    },
    locations: [
      { country: "United States", region: "New York", views: 260, sales: 14, revenueCents: 40600 },
      { country: "Germany", region: "Berlin", views: 110, sales: 5, revenueCents: 14500 },
      { country: "India", region: "Karnataka", views: 96, sales: 4, revenueCents: 11600 },
      { country: "Brazil", region: "Sao Paulo", views: 74, sales: 3, revenueCents: 8700 },
    ],
    utmLinks: [
      { source: "producthunt", medium: "launch", campaign: "kit-v2", destination: "Product page", clicks: 130, sales: 12, revenueCents: 34800 },
      { source: "gumroad", medium: "discover", campaign: "recommended", destination: "Product page", clicks: 420, sales: 11, revenueCents: 31900 },
      { source: "twitter", medium: "social", campaign: "template-thread", destination: "Product page", clicks: 110, sales: 6, revenueCents: 17400 },
    ],
  },
  "prod-audio-pack": {
    churn: {
      activeStart: 64,
      newSubscriptions: 11,
      canceled: 5,
      previousActiveStart: 58,
      previousNewSubscriptions: 9,
      previousCanceled: 2,
      revenueLostCents: 9500,
    },
    locations: [
      { country: "United States", region: "Georgia", views: 280, sales: 19, revenueCents: 36100 },
      { country: "Japan", region: "Tokyo", views: 140, sales: 9, revenueCents: 17100 },
      { country: "France", region: "Ile-de-France", views: 115, sales: 8, revenueCents: 15200 },
      { country: "Mexico", region: "Jalisco", views: 88, sales: 5, revenueCents: 9500 },
    ],
    utmLinks: [
      { source: "beatstars", medium: "marketplace", campaign: "lofi-drums", destination: "Product page", clicks: 180, sales: 20, revenueCents: 38000 },
      { source: "instagram", medium: "social", campaign: "reel-pack-demo", destination: "Product page", clicks: 240, sales: 17, revenueCents: 32300 },
      { source: "gumroad", medium: "discover", campaign: "recommended", destination: "Product page", clicks: 330, sales: 12, revenueCents: 22800 },
    ],
  },
  "prod-zine-guide": {
    churn: {
      activeStart: 24,
      newSubscriptions: 3,
      canceled: 0,
      previousActiveStart: 21,
      previousNewSubscriptions: 2,
      previousCanceled: 1,
      revenueLostCents: 0,
    },
    locations: [
      { country: "United States", region: "Oregon", views: 34, sales: 2, revenueCents: 1800 },
      { country: "Canada", region: "British Columbia", views: 16, sales: 1, revenueCents: 900 },
      { country: "United Kingdom", region: "Scotland", views: 12, sales: 1, revenueCents: 900 },
      { country: "Netherlands", region: "North Holland", views: 8, sales: 1, revenueCents: 900 },
    ],
    utmLinks: [
      { source: "newsletter", medium: "email", campaign: "tiny-launch", destination: "Product page", clicks: 28, sales: 2, revenueCents: 1800 },
      { source: "direct", medium: "direct", campaign: "bookmarks-and-apps", destination: "Product page", clicks: 32, sales: 3, revenueCents: 2700 },
      { source: "gumroad", medium: "discover", campaign: "recommended", destination: "Product page", clicks: 24, sales: 0, revenueCents: 0 },
    ],
  },
};

export const setSalesDashboardData = (records = {}) => {
  if (!records || typeof records !== "object") return;
  salesDashboardData = {
    ...salesDashboardData,
    ...records,
  };
};

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const safeDivide = (numerator, denominator) =>
  denominator > 0 ? numerator / denominator : 0;

const percentDelta = (current, previous) =>
  previous > 0 ? (current - previous) / previous : current > 0 ? 1 : 0;

const round = (value, digits = 4) => Number(value.toFixed(digits));

const sumValues = (items, getValue) =>
  items.reduce((total, item) => total + getValue(item), 0);

const scaleNumber = (value, scale) => Math.max(0, Math.round(value * scale));

const mergeByKey = (items, getKey, numericKeys) => {
  const map = new Map();

  items.forEach((item) => {
    const key = getKey(item);
    const current = map.get(key);

    if (!current) {
      map.set(key, { ...item });
      return;
    }

    numericKeys.forEach((numericKey) => {
      current[numericKey] += item[numericKey] ?? 0;
    });
  });

  return [...map.values()];
};

const buildSourceMetrics = (sources, overallConversion) =>
  sources
    .map((source) => {
      const conversion = safeDivide(source.sales, source.views);
      return {
        ...source,
        conversion: round(conversion),
        averageOrderCents: Math.round(safeDivide(source.revenueCents, source.sales)),
        conversionLift: round(
          overallConversion > 0 ? conversion / overallConversion - 1 : 0
        ),
      };
    })
    .sort((a, b) => {
      if (b.revenueCents !== a.revenueCents) return b.revenueCents - a.revenueCents;
      return b.sales - a.sales;
    });

const mergeSources = (sources) =>
  mergeByKey(
    sources,
    (source) => source.name.toLowerCase(),
    ["views", "sales", "revenueCents"]
  ).sort((a, b) => b.revenueCents - a.revenueCents);

const aggregatePeriod = (items, period) => ({
  views: sumValues(items, (product) => product[period].views),
  sales: sumValues(items, (product) => product[period].sales),
  revenueCents: sumValues(items, (product) => product[period].revenueCents),
  refunds: sumValues(items, (product) => product[period].refunds),
  refundCents: sumValues(items, (product) => product[period].refundCents),
  discoverImpressions: sumValues(
    items,
    (product) => product[period].discoverImpressions
  ),
  sources: mergeSources(items.flatMap((product) => product[period].sources)),
});

export const buildAggregateProduct = (items) => {
  const current = aggregatePeriod(items, "current");
  const previous = aggregatePeriod(items, "previous");
  const reviewCount = sumValues(items, (product) => product.reviewCount);
  const weightedRating = safeDivide(
    sumValues(items, (product) => product.rating * product.reviewCount),
    reviewCount
  );

  return {
    id: "all",
    name: "All products",
    creator: "Portfolio overview",
    category: "All products",
    priceCents: Math.round(safeDivide(current.revenueCents, current.sales)),
    currency: "USD",
    tags: ["all-products", "sales", "churn", "utm"],
    rating: round(weightedRating, 1),
    reviewCount,
    description:
      "Portfolio-wide analytics across every seeded product, matching the default Gumroad overview before drilling into a product.",
    childProductIds: items.map((product) => product.id),
    current,
    previous,
  };
};

const dateRangeScales = {
  "30": 1,
  "90": 2.75,
  "180": 5.4,
  all: 6.4,
};

const scaleFromCustomDays = (days) => {
  if (!Number.isFinite(days) || days <= 0) return dateRangeScales["30"];
  return Math.max(0.25, Math.min(dateRangeScales.all, days / 30));
};

const scalePeriod = (period, scale) => ({
  ...period,
  views: scaleNumber(period.views, scale),
  sales: scaleNumber(period.sales, scale),
  revenueCents: scaleNumber(period.revenueCents, scale),
  refunds: scaleNumber(period.refunds, scale),
  refundCents: scaleNumber(period.refundCents, scale),
  discoverImpressions: scaleNumber(period.discoverImpressions, scale),
  sources: period.sources.map((source) => ({
    ...source,
    views: scaleNumber(source.views, scale),
    sales: scaleNumber(source.sales, scale),
    revenueCents: scaleNumber(source.revenueCents, scale),
  })),
});

export const applyDateRange = (product, dateRange, options = {}) => {
  const scale =
    dateRange === "custom"
      ? scaleFromCustomDays(options.customDays)
      : dateRangeScales[dateRange] ?? 1;

  if (scale === 1) {
    return { ...product, dashboardScale: scale, dateRange };
  }

  return {
    ...product,
    dashboardScale: scale,
    dateRange,
    current: scalePeriod(product.current, scale),
    previous: scalePeriod(product.previous, scale),
  };
};

const mergeDashboardRecords = (records) => ({
  churn: records.reduce(
    (total, record) => ({
      activeStart: total.activeStart + record.churn.activeStart,
      newSubscriptions: total.newSubscriptions + record.churn.newSubscriptions,
      canceled: total.canceled + record.churn.canceled,
      previousActiveStart:
        total.previousActiveStart + record.churn.previousActiveStart,
      previousNewSubscriptions:
        total.previousNewSubscriptions + record.churn.previousNewSubscriptions,
      previousCanceled: total.previousCanceled + record.churn.previousCanceled,
      revenueLostCents: total.revenueLostCents + record.churn.revenueLostCents,
    }),
    {
      activeStart: 0,
      newSubscriptions: 0,
      canceled: 0,
      previousActiveStart: 0,
      previousNewSubscriptions: 0,
      previousCanceled: 0,
      revenueLostCents: 0,
    }
  ),
  locations: mergeByKey(
    records.flatMap((record) => record.locations),
    (location) => `${location.country}::${location.region}`,
    ["views", "sales", "revenueCents"]
  ),
  utmLinks: mergeByKey(
    records.flatMap((record) => record.utmLinks),
    (link) =>
      `${link.source}::${link.medium}::${link.campaign}::${link.destination}`,
    ["clicks", "sales", "revenueCents"]
  ),
});

const scaleDashboardData = (data, scale) => {
  const baseScale = Math.sqrt(scale);

  return {
    churn: {
      activeStart: scaleNumber(data.churn.activeStart, baseScale),
      newSubscriptions: scaleNumber(data.churn.newSubscriptions, scale),
      canceled: scaleNumber(data.churn.canceled, scale),
      previousActiveStart: scaleNumber(
        data.churn.previousActiveStart,
        baseScale
      ),
      previousNewSubscriptions: scaleNumber(
        data.churn.previousNewSubscriptions,
        scale
      ),
      previousCanceled: scaleNumber(data.churn.previousCanceled, scale),
      revenueLostCents: scaleNumber(data.churn.revenueLostCents, scale),
    },
    locations: data.locations.map((location) => ({
      ...location,
      views: scaleNumber(location.views, scale),
      sales: scaleNumber(location.sales, scale),
      revenueCents: scaleNumber(location.revenueCents, scale),
    })),
    utmLinks: data.utmLinks.map((link) => ({
      ...link,
      clicks: scaleNumber(link.clicks, scale),
      sales: scaleNumber(link.sales, scale),
      revenueCents: scaleNumber(link.revenueCents, scale),
    })),
  };
};

const buildDashboardDataForProduct = (product) => {
  const productIds =
    Array.isArray(product.childProductIds) && product.childProductIds.length > 0
      ? product.childProductIds
      : [product.id];
  const records = productIds
    .map((productId) => salesDashboardData[productId])
    .filter(Boolean);
  const merged = mergeDashboardRecords(
    records.length > 0 ? records : [salesDashboardData["prod-creator-os"]]
  );
  const scale = product.dashboardScale ?? 1;

  return scale === 1 ? merged : scaleDashboardData(merged, scale);
};

const buildMetadataCompleteness = (product) => {
  const checks = [
    {
      label: "Category",
      complete: Boolean(product.category && product.category.trim().length > 0),
    },
    {
      label: "Tags",
      complete: Array.isArray(product.tags) && product.tags.length >= IDEAL_TAG_COUNT,
    },
    {
      label: "Description",
      complete:
        typeof product.description === "string" &&
        product.description.trim().length >= MIN_DESCRIPTION_LENGTH,
    },
    {
      label: "Rating",
      complete: Number(product.rating) >= 4.3,
    },
    {
      label: "Reviews",
      complete: Number(product.reviewCount) >= 10,
    },
  ];

  const completed = checks.filter((check) => check.complete).length;
  const missing = checks
    .filter((check) => !check.complete)
    .map((check) => check.label);

  return {
    score: round(completed / checks.length, 2),
    completed,
    total: checks.length,
    missing,
  };
};

const makeAction = (kind, label, safeToApply = false, review = {}) => ({
  kind,
  label,
  safeToApply,
  ...review,
});

const signal = (id, type, strength, data = {}) => ({
  id,
  type,
  strength,
  ...data,
});

export const formatCurrency = (cents, currency = "USD") => {
  const amount = safeDivide(cents, 100);
  const symbol = currencySymbols[currency] ?? `${currency} `;
  const formatted = amount.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return `${symbol}${formatted}`;
};

export const formatPercent = (value) => {
  const percentage = value * 100;
  const rounded = percentage.toFixed(1).replace(/\.0$/, "");
  return `${rounded}%`;
};

const refundReasonForProduct = (product) => {
  const reasons = {
    "prod-creator-os": "Expectation mismatch: buyer expected onboarding videos and a setup checklist.",
    "prod-design-kit": "Template scope mismatch: buyer expected a custom implementation service.",
    "prod-audio-pack": "Compatibility mismatch: buyer expected Logic-ready stems instead of WAV and Ableton files.",
    "prod-zine-guide": "Duplicate purchase review: buyer bought twice from direct traffic.",
    all: "Portfolio-wide refund pressure points to checkout expectations and support response gaps.",
  };

  return reasons[product.id] ?? "Buyer expectation mismatch before checkout.";
};

const refundActionCopy = (product, caseType) => {
  if (caseType === "chargeback_dispute") {
    return {
      label: "Chargeback dispute",
      recommendedAction:
        `Compile purchase, delivery, product-page, and support evidence for ${product.name}, then prepare the dispute submission workflow.`,
      auditNote:
        "Refund balance evidence note: purchase delivered, product page reviewed, support timeline attached, and dispute response prepared for submission.",
    };
  }

  if (caseType === "voluntary_refund_review") {
    return {
      label: "Refund review",
      recommendedAction:
        `Offer a support-first resolution for ${product.name}: clarify access, include setup help, and approve a refund only if the buyer still cannot use the product.`,
      auditNote:
        "Refund request reviewed with purchase, delivery, support, and product-page context. No automatic refund was issued.",
    };
  }

  return {
    label: "Refund request",
    recommendedAction:
      `Respond with the included-file list, compatibility notes, and support path for ${product.name}; keep the refund decision manual.`,
    auditNote:
      "Buyer refund request triaged with purchase facts, delivery evidence, and policy context. Awaiting manual decision.",
  };
};

const buildRefundCase = (product, metrics, template, index) => {
  const source = metrics.currentSources[index % Math.max(1, metrics.currentSources.length)] ?? {
    name: "Direct",
    revenueCents: metrics.currentAverageOrderCents,
  };
  const action = refundActionCopy(product, template.caseType);
  const purchaseId = `demo-${product.id}-${index + 1}`;
  const amountCents =
    template.caseType === "chargeback_dispute"
      ? Math.max(metrics.currentAverageOrderCents, source.averageOrderCents ?? 0)
      : Math.max(100, Math.round(Math.max(metrics.currentAverageOrderCents, source.averageOrderCents ?? 0) / 2));
  const buyerIssue = refundReasonForProduct(product);
  const riskScore = clamp(
    Math.round(metrics.currentRefundRate * 720) + 24 + (source.name.includes("Discover") ? 8 : 0) + template.riskBoost,
    28,
    96
  );
  const evidenceScore = clamp(62 + (template.caseType === "chargeback_dispute" ? 13 : 8) + (source.name ? 7 : 0), 48, 94);
  const paymentType = template.caseType === "chargeback_dispute" ? "Card" : index % 2 === 0 ? "Card" : "PayPal";
  const deliveryEvidence = `Purchase ${purchaseId} was recorded on 2026-04-${String(23 + index).padStart(2, "0")} with product access available after checkout.`;

  return {
    id: `refund-${product.id}-${index + 1}`,
    purchaseId,
    productId: product.id,
    caseType: template.caseType,
    mode: template.caseType === "chargeback_dispute" ? "dispute" : "review",
    status: template.status,
    label: action.label,
    reason: buyerIssue,
    amountCents,
    paymentType,
    sourceName: source.name,
    buyerIssue,
    dueAt: `2026-04-${String(27 + index).padStart(2, "0")}T17:00:00+00:00`,
    riskScore,
    evidenceScore,
    recommendedAction: action.recommendedAction,
    buyerReply:
      `Thanks for reaching out. I checked your ${product.name} purchase and can help with the issue before we make a refund decision. The likely issue is: ${buyerIssue} Reply with what you were trying to do and I will either help resolve it or review the refund request manually.`,
    disputeEvidence:
      `${action.label} evidence packet for ${product.name}: purchase ${purchaseId}, ${paymentType} payment, ${source.name} source. ${deliveryEvidence} Buyer issue: ${buyerIssue} Recommended action: ${action.recommendedAction}`,
    auditNote: action.auditNote,
    deliveryEvidence,
    policySnapshot:
      "Refunds and chargebacks can affect payout balance. Chargebacks are payment disputes, not normal Gumroad refund requests, and evidence must be reviewed before submission.",
    timeline: [
      { label: "Purchase", value: `2026-04-${String(23 + index).padStart(2, "0")} 14:30 UTC` },
      { label: "Access", value: "Download access created after checkout" },
      { label: "Case opened", value: `2026-04-${String(24 + index).padStart(2, "0")}` },
      { label: "Due", value: `2026-04-${String(27 + index).padStart(2, "0")}` },
    ],
    evidence: [
      { label: "Purchase record", status: "ready", detail: purchaseId },
      { label: "Delivery/access proof", status: "ready", detail: "Access event present in seeded demo facts" },
      { label: "Product page promise", status: "review", detail: "Compare buyer issue with included files and compatibility copy" },
      { label: "Support contact", status: "review", detail: "Attach the support thread before dispute submission" },
    ],
    auditEvents: [
      {
        actor: "Gumroad Merchant",
        action: "case_detected",
        amountCents,
        note: `Refund Ops detected ${template.caseType.replaceAll("_", " ")} from seeded purchase facts.`,
      },
      {
        actor: "Gumroad Merchant",
        action: "review_packet_prepared",
        amountCents,
        note: action.auditNote,
      },
    ],
  };
};

const refundCaseTemplates = (metrics) => {
  const templates = [];
  if (metrics.currentRefunds > 0) {
    templates.push({ caseType: "refund_request", status: "needs_review", riskBoost: 0 });
  }
  if (metrics.currentRefunds >= 2 || metrics.currentRefundRate >= 0.06) {
    templates.push({ caseType: "chargeback_dispute", status: "evidence_due", riskBoost: 6 });
  }
  if (metrics.currentRefunds >= 3) {
    templates.push({ caseType: "voluntary_refund_review", status: "reply_drafted", riskBoost: 3 });
  }
  return templates;
};

const buildRefundPreventionActions = (product, metrics, cases) => {
  const actions = [];
  const discover = metrics.currentSources.find((source) =>
    source.name.toLowerCase().includes("discover")
  );
  const direct = metrics.currentSources.find((source) => source.name.toLowerCase() === "direct");

  if (discover && metrics.currentRefunds > 0) {
    actions.push({
      id: "discover-refund-fit",
      title: "High refund rate from Gumroad Discover",
      impact: "Review Discover refund fit before scaling that channel.",
      evidence: [
        `${discover.views.toLocaleString("en-US")} Discover views`,
        `${discover.sales.toLocaleString("en-US")} Discover sales`,
        `${formatPercent(metrics.currentRefundRate)} refund rate`,
      ],
      recommendedAction:
        "Add format, compatibility, and included-file details above the buy button for Discover visitors.",
    });
  }

  if (cases.some((item) => item.reason.toLowerCase().includes("compatibility"))) {
    actions.push({
      id: "compatibility-expectations",
      title: "Refunds mention compatibility",
      impact: "Clarifies whether the product works for the buyer before checkout.",
      evidence: ["Compatibility appears in the seeded refund-case reasons"],
      recommendedAction:
        "Add a supported-tools line, setup requirements, and one plain-language example of what is not included.",
    });
  }

  if (cases.some((item) => item.caseType === "chargeback_dispute")) {
    actions.push({
      id: "support-delay-dispute-risk",
      title: "Support delay likely drove dispute risk",
      impact: "Reduces the chance that a buyer bypasses support and opens a payment dispute.",
      evidence: [
        `${cases.filter((item) => item.caseType === "chargeback_dispute").length} chargeback dispute case`,
        "Evidence packet requires support-thread review",
      ],
      recommendedAction:
        "Reply with access help within one business day and copy the audit note before making a refund decision.",
    });
  }

  if (direct && direct.views > 100) {
    actions.push({
      id: "direct-policy-copy",
      title: "Direct buyers need clearer refund expectations",
      impact: "Direct traffic often mixes email, apps, bookmarks, and private shares, so checkout copy has to do more work.",
      evidence: [
        `${direct.views.toLocaleString("en-US")} direct views`,
        `${direct.sales.toLocaleString("en-US")} direct sales`,
      ],
      recommendedAction:
        "Move refund expectations and delivery timing into the first screen instead of relying on support follow-up.",
    });
  }

  if (!actions.length) {
    actions.push({
      id: "baseline-refund-monitoring",
      title: "Keep refund monitoring active",
      impact: "Refund pressure is not elevated enough to justify a broad product-page rewrite.",
      evidence: [
        `${metrics.currentRefunds.toLocaleString("en-US")} refunds`,
        `${formatPercent(metrics.currentRefundRate)} refund rate`,
      ],
      recommendedAction:
        `Keep ${product.name} stable and review new cases before changing price or policy copy.`,
    });
  }

  return actions.slice(0, 4);
};

export const buildRefundOps = (product, metrics) => {
  const cases = refundCaseTemplates(metrics).map((template, index) =>
    buildRefundCase(product, metrics, template, index)
  );
  const disputedAmountCents = sumValues(
    cases.filter((item) => item.caseType === "chargeback_dispute"),
    (item) => item.amountCents
  );
  const amountUnderReviewCents = sumValues(cases, (item) => item.amountCents);
  const preventionActions = buildRefundPreventionActions(product, metrics, cases);

  return {
    summary: {
      refundRate: metrics.currentRefundRate,
      previousRefundRate: metrics.previousRefundRate,
      refunds: metrics.currentRefunds,
      refundAmountCents: metrics.currentRefundCents,
      disputedAmountCents,
      amountUnderReviewCents,
      casesNeedingReview: cases.filter((item) =>
        ["needs_review", "evidence_due", "reply_drafted"].includes(item.status)
      ).length,
      caseCount: cases.length,
      preventableRefundEstimateCents: Math.round(metrics.currentRefundCents * 0.42),
      modeCounts: {
        prevent: preventionActions.length,
        review: cases.filter((item) => item.mode === "review").length,
        dispute: cases.filter((item) => item.mode === "dispute").length,
      },
    },
    cases,
    preventionActions,
  };
};

const trendLibraryForProduct = (product, metrics) => {
  const topSource = metrics.currentSources[0]?.name ?? "Direct";
  const category = String(product.category || "Creator tools").toLowerCase();
  const tags = (product.tags ?? []).join(" ").toLowerCase();
  const base = [
    {
      id: "proof-led-walkthrough",
      title: "Show the before-and-after workflow",
      angle:
        "Creators are buying clearer operating systems, not vague productivity promises.",
      channel: topSource.includes("YouTube") ? "YouTube" : "Short-form video",
      trendScore: 84,
      kpi: "Qualified product-page views",
      risk: "Can look generic if the example is not tied to the buyer's actual workflow.",
      outline: [
        "Open with the messy before state.",
        "Show the product in use for one concrete task.",
        "End with the buyer outcome and a tracked Gumroad link.",
      ],
    },
    {
      id: "build-in-public-teardown",
      title: "Tear down one real creator setup",
      angle:
        "Educational teardown content earns trust before the product pitch.",
      channel: "Newsletter",
      trendScore: 78,
      kpi: "Email clicks to product page",
      risk: "Needs permission or anonymized examples to avoid feeling invasive.",
      outline: [
        "Pick one common creator bottleneck.",
        "Explain the mistake with a screenshot or simple checklist.",
        "Offer the product as the repeatable fix.",
      ],
    },
    {
      id: "compatibility-proof",
      title: "Answer compatibility before checkout",
      angle:
        "Buyers convert faster when they know exactly what formats, tools, and limits are included.",
      channel: metrics.currentRefundRate >= 0.06 ? "Product page + email" : "Product page",
      trendScore: 76,
      kpi: "Refund-rate reduction",
      risk: "Too much caveat copy can suppress impulse buyers if it is not scannable.",
      outline: [
        "State supported tools and formats above the buy button.",
        "Add one 'not included' line.",
        "Link the campaign to a compatibility-specific UTM.",
      ],
    },
  ];

  if (category.includes("music") || tags.includes("audio") || tags.includes("sample")) {
    base.unshift({
      id: "producer-demo-loop",
      title: "Turn one pack into a finished loop",
      angle:
        "Music buyers respond to hearing the finished output before reading the file list.",
      channel: "Instagram Reels",
      trendScore: 88,
      kpi: "Sales from social demos",
      risk: "Performance can overfit to one sound if the demo is too narrow.",
      outline: [
        "Start with the raw sample.",
        "Layer the finished loop in under 20 seconds.",
        "Pin file compatibility and license notes in the caption.",
      ],
    });
  }

  if (category.includes("writing") || tags.includes("zine") || tags.includes("publishing")) {
    base.unshift({
      id: "tiny-launch-diary",
      title: "Publish a tiny launch diary",
      angle:
        "Small creative launches perform well when the buyer sees a complete path instead of a polished fantasy.",
      channel: "Newsletter",
      trendScore: 82,
      kpi: "Repeat direct buyers",
      risk: "Low-priced products need tight calls to action to avoid passive readership.",
      outline: [
        "Share the first launch constraint.",
        "Show the checklist or page that solved it.",
        "Invite readers to use the exact template.",
      ],
    });
  }

  if (category.includes("design") || tags.includes("template")) {
    base.unshift({
      id: "template-remix-thread",
      title: "Remix one template into three launches",
      angle:
        "Template buyers want proof that the kit adapts to more than one product category.",
      channel: "X / Twitter",
      trendScore: 86,
      kpi: "Conversion from social traffic",
      risk: "Can attract buyers expecting custom implementation if the boundary is unclear.",
      outline: [
        "Show three product variants from the same kit.",
        "Name what changed and what stayed reusable.",
        "Close with the included files and support boundary.",
      ],
    });
  }

  return base;
};

const campaignSlug = (product, trend) =>
  `${String(product.name || "portfolio")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 34)}-${trend.id}`;

export const buildContentRadar = (product, metrics) => {
  const topSource = metrics.currentSources[0] ?? null;
  const trends = trendLibraryForProduct(product, metrics)
    .map((trend) => {
      const sourceMatch = topSource && trend.channel.toLowerCase().includes(topSource.name.split(" ")[0].toLowerCase());
      const fitScore = clamp(
        Math.round(
          58 +
            trend.trendScore * 0.18 +
            metrics.currentConversion * 420 +
            (sourceMatch ? 8 : 0) -
            metrics.currentRefundRate * 120
        ),
        45,
        96
      );
      const utmCampaign = campaignSlug(product, trend);

      return {
        ...trend,
        fitScore,
        utmCampaign,
        expectedKpi: trend.kpi,
        rationale: `${product.name} has ${formatPercent(metrics.currentConversion)} conversion, ${metrics.currentSales.toLocaleString("en-US")} current sales, and ${topSource?.name ?? "direct"} as the strongest revenue source.`,
        evidence: [
          `${topSource?.name ?? "Top source"}: ${formatCurrency(topSource?.revenueCents ?? 0, product.currency)}`,
          `${formatPercent(metrics.currentRefundRate)} refund rate`,
          `${metrics.currentViews.toLocaleString("en-US")} current views`,
        ],
        draft: {
          post:
            `${trend.title}: show the specific buyer problem, prove the product working on-screen, then send traffic through ?utm_source=${encodeURIComponent(trend.channel.toLowerCase().replaceAll(" ", "-"))}&utm_medium=content&utm_campaign=${encodeURIComponent(utmCampaign)}.`,
          email:
            `Subject: A cleaner way to use ${product.name}\n\nOpen with the buyer problem, show the concrete workflow, then link to the product with the ${utmCampaign} UTM campaign.`,
        },
      };
    })
    .sort((a, b) => b.fitScore - a.fitScore)
    .slice(0, 5);

  const lead = trends[0];

  return {
    summary: {
      trendCount: trends.length,
      topFitScore: lead?.fitScore ?? 0,
      primaryChannel: lead?.channel ?? "Newsletter",
      campaignName: lead?.utmCampaign ?? "seeded-content-campaign",
      expectedKpi: lead?.expectedKpi ?? "Qualified product-page views",
      readOnly: true,
    },
    trends,
    plan: {
      objective: `Turn ${product.name} analytics into one content campaign that can be measured through UTM links.`,
      campaignName: lead?.utmCampaign ?? "seeded-content-campaign",
      recommendedChannel: lead?.channel ?? "Newsletter",
      weeklySteps: [
        "Week 1: publish the proof-led asset and route every link through the campaign UTM.",
        "Week 2: reuse the best comment/question as a product-page FAQ or compatibility note.",
        "Week 3: compare source conversion, refund mentions, and campaign revenue before scaling.",
      ],
      executionNote:
        "Content Radar turns product signals into campaign plans, tracked links, and launch steps.",
    },
    drafts: {
      campaignBrief: `${lead?.title ?? "Content campaign"} for ${product.name}: ${lead?.angle ?? "Use one buyer problem, one proof asset, and one tracked Gumroad link."}`,
      postDraft: lead?.draft.post ?? "",
      emailDraft: lead?.draft.email ?? "",
      utmPlan: `utm_source=${encodeURIComponent((lead?.channel ?? "newsletter").toLowerCase().replaceAll(" ", "-"))}&utm_medium=content&utm_campaign=${encodeURIComponent(lead?.utmCampaign ?? "seeded-content-campaign")}`,
    },
  };
};

export const buildRetentionSaver = (product, metrics) => {
  const dashboard = buildSalesDashboard(product, metrics);
  const churn = dashboard.churn;
  const saveRate = 0.096;
  const expectedSavedMembers = round(churn.canceled * saveRate, 2);
  const revenueSavedCents = Math.round(churn.revenueLostCents * saveRate);
  const avgLostRevenueCents = Math.round(safeDivide(churn.revenueLostCents, churn.canceled));
  const refundPressure = metrics.currentRefundRate >= 0.06;

  return {
    summary: {
      sourceIssue: "#4884",
      churnRate: churn.rate,
      canceledMembers: churn.canceled,
      revenueLostCents: churn.revenueLostCents,
      expectedSavedMembers,
      revenueSavedCents,
      saveRate,
      readOnly: true,
    },
    pauseOffers: [
      {
        id: "pause-1-month",
        label: "Pause for 1 month",
        bestFor: "Temporary budget, travel, or busy-season objections.",
        estimatedSavedCents: Math.round(revenueSavedCents * 0.58),
        reviewSteps: [
          "Show before cancel anyway.",
          "Let access lapse after the current paid period.",
          "Resume billing on the next eligible recurring-charge tick.",
        ],
      },
      {
        id: "pause-3-months",
        label: "Pause for 3 months",
        bestFor: "Seasonal creators or buyers who say they are not using the membership right now.",
        estimatedSavedCents: Math.round(revenueSavedCents * 0.42),
        reviewSteps: [
          "Ask for a reason before the final cancel step.",
          "Explain when access and billing resume.",
          "Record the pause decision in the audit timeline.",
        ],
      },
    ],
    risks: [
      {
        label: "Cancellation reason",
        value: refundPressure ? "Expectation mismatch" : "Low usage",
        detail: refundPressure
          ? "Refund pressure suggests the pause offer should not hide product-fit problems."
          : "A pause offer can save buyers who are not ready to cancel permanently.",
      },
      {
        label: "Revenue saved model",
        value: `${formatPercent(saveRate)} save-rate assumption`,
        detail: `${formatCurrency(avgLostRevenueCents, product.currency)} estimated revenue lost per canceled member in this seeded period.`,
      },
      {
        label: "Execution",
        value: "Action plan",
        detail: "Membership billing, access, and subscription changes are prepared as executable workflows.",
      },
    ],
  };
};

export const buildAdminActionPreview = (product, metrics, refundOps, retentionSaver) => {
  const firstCase = refundOps.cases[0];
  const templates = [
    {
      id: "purchase-lookup",
      label: "Exact purchase lookup",
      commandText: `Look up purchase ${firstCase?.purchaseId ?? "purchase_id"} with an exact identifier and return the support context needed for action.`,
      riskLevel: "read-action",
      requiredInputs: ["purchase_id"],
      preflightChecks: ["Admin token present", "Purchase id exact match", "No buyer email in URL"],
      auditNote: "Purchase lookup prepared for support context.",
      blockedReason: "",
    },
    {
      id: "refund-review-note",
      label: "Add refund review note",
      commandText: `Prepare a refund review note for ${firstCase?.purchaseId ?? "purchase_id"}: Refund Ops packet reviewed; no automatic action taken.`,
      riskLevel: "write-action",
      requiredInputs: ["purchase_id", "admin_note"],
      preflightChecks: ["Merchant confirmation", "Refund policy reviewed", "Audit event required"],
      auditNote: firstCase?.auditNote ?? "Refund review note prepared from seeded case context.",
      blockedReason: "Simulated only in this prototype.",
    },
    {
      id: "resend-receipt",
      label: "Resend receipt",
      commandText: `Prepare a receipt resend workflow for ${firstCase?.purchaseId ?? "purchase_id"} after buyer identity and support history are checked.`,
      riskLevel: "write-action",
      requiredInputs: ["purchase_id"],
      preflightChecks: ["Buyer identity checked", "Receipt not recently resent", "Support ticket linked"],
      auditNote: "Receipt resend prepared with buyer identity and support history checked.",
      blockedReason: "Email send requires merchant confirmation.",
    },
    {
      id: "pause-membership",
      label: "Pause membership",
      commandText: "Prepare a one-cycle membership pause workflow after the buyer request, access impact, and resume date are confirmed.",
      riskLevel: "financial-write",
      requiredInputs: ["subscription_id", "pause_cycles"],
      preflightChecks: ["Buyer requested pause", "Access lapse copy shown", "Resume date confirmed"],
      auditNote: `Retention Saver estimates ${formatCurrency(retentionSaver.summary.revenueSavedCents, product.currency)} saved from pause offers.`,
      blockedReason: "Membership state changes require the Gumroad admin API and merchant confirmation.",
    },
    {
      id: "payout-hold",
      label: "Payout hold / resume",
      commandText: "Prepare a payout hold or resume action after policy owner approval, risk evidence, and actor attribution are recorded.",
      riskLevel: "high-risk-admin",
      requiredInputs: ["seller_id", "reason", "reviewer"],
      preflightChecks: ["Policy owner confirmation", "Risk evidence attached", "Actor attribution recorded"],
      auditNote: "High-risk payout action prepared with audit context.",
      blockedReason: "Money-movement admin commands require production permission scope.",
    },
  ];

  return {
    summary: {
      sourceIssue: "Action-ready",
      templateCount: templates.length,
      safeReadCount: templates.filter((item) => item.riskLevel === "read-action").length,
      blockedWriteCount: templates.filter((item) => item.riskLevel !== "read-action").length,
      readOnly: true,
    },
    templates,
    preview: {
      selected: templates[0],
      sourceContext:
        "This dashboard prepares admin action intent, required checks, execution mode, and audit copy.",
      executionNote:
        "Admin actions are shown with execution mode, preflight checks, permission requirements, and audit notes.",
    },
  };
};

export const buildShortestQa = (product, metrics) => {
  const suites = [
    {
      id: "refund-ops-journey",
      title: "Refund Ops case review",
      targetSurface: "Dashboard + Merchant chat",
      riskCovered: "Accidentally treating a chargeback as a normal refund.",
      steps: [
        "Open Refund Ops and switch to Dispute.",
        "Select the highest-risk chargeback case.",
        "Copy the dispute evidence and audit note.",
        "Ask Merchant chat to build a dispute packet.",
      ],
      assertions: [
        "The UI says chargeback dispute, not refund dispute.",
        "Copy buttons produce action packet text.",
        "Chat answer cites Refund Ops case evidence.",
      ],
    },
    {
      id: "content-radar-journey",
      title: "Content Radar marketing plan",
      targetSurface: "Content Radar",
      riskCovered: "Generating vague marketing advice that is not tied to analytics.",
      steps: [
        "Select a product with meaningful traffic.",
        "Open Content Radar.",
        "Open the top trend and copy the UTM plan.",
      ],
      assertions: [
        "The top trend includes fit score, channel, risk, and expected KPI.",
        "The plan references product/source/refund evidence.",
        "No live posting or ad spend action is available.",
      ],
    },
    {
      id: "retention-saver-journey",
      title: "Membership pause save estimate",
      targetSurface: "Retention Saver",
      riskCovered: "Overstating saved revenue from pause offers.",
      steps: [
        "Open Retention Saver.",
        "Compare canceled members, revenue lost, and estimated save.",
        "Compare 1-month and 3-month pause options.",
      ],
      assertions: [
        "The save model shows the 9.6% assumption.",
        "Pause offers are action-ready and tied to issue #4884.",
        "Membership state changes are prepared as explicit workflows.",
      ],
    },
    {
      id: "admin-action-journey",
      title: "Admin action execution checks",
      targetSurface: "Admin Actions",
      riskCovered: "Executing a dangerous admin write from a demo surface.",
      steps: [
        "Open Admin Actions.",
        "Inspect read and write action templates.",
        "Copy an audit note for a refund case.",
      ],
      assertions: [
        "Every write command includes preflight checks.",
        "Write actions include permission requirements.",
        "Admin actions expose the execution mode.",
      ],
    },
  ];

  return {
    summary: {
      suiteCount: suites.length,
      assertionCount: sumValues(suites, (suite) => suite.assertions.length),
      productName: product.name,
      readOnly: true,
    },
    suites: suites.map((suite) => ({
      ...suite,
      passFailEvidence:
        `Use screenshots, copied text, and Merchant chat citations from ${product.name} at ${formatPercent(metrics.currentConversion)} conversion.`,
    })),
  };
};

export const buildSalesDashboard = (product, metrics) => {
  const data = buildDashboardDataForProduct(product);
  const churnBase = data.churn.activeStart + data.churn.newSubscriptions;
  const previousChurnBase =
    data.churn.previousActiveStart + data.churn.previousNewSubscriptions;
  const churnRate = round(safeDivide(data.churn.canceled, churnBase));
  const previousChurnRate = round(
    safeDivide(data.churn.previousCanceled, previousChurnBase)
  );
  const locations = data.locations
    .map((location) => ({
      ...location,
      conversion: round(safeDivide(location.sales, location.views)),
    }))
    .sort((a, b) => b.revenueCents - a.revenueCents);
  const utmLinks = data.utmLinks
    .map((link) => ({
      ...link,
      conversion: round(safeDivide(link.sales, link.clicks)),
    }))
    .sort((a, b) => b.revenueCents - a.revenueCents);
  const usLocations = locations
    .filter((location) => location.country === "United States")
    .sort((a, b) => b.revenueCents - a.revenueCents);
  const dashboard = {
    churn: {
      rate: churnRate,
      previousRate: previousChurnRate,
      canceled: data.churn.canceled,
      revenueLostCents: data.churn.revenueLostCents,
      base: churnBase,
      formula: `${data.churn.canceled} canceled / (${data.churn.activeStart} active + ${data.churn.newSubscriptions} new)`,
    },
    locations,
    usLocations,
    utmLinks,
  };
  const customers = [
    ["Sana Patel", "sana.patel@example.com"],
    ["Luis Moreno", "luis.moreno@example.com"],
    ["Avery Novak", "avery.novak@example.com"],
    ["Noor Williams", "noor.williams@example.com"],
    ["Elena Park", "elena.park@example.com"],
    ["Marcus Bell", "marcus.bell@example.com"],
  ];
  const exportSources = metrics.currentSources.slice(0, 6);
  const sampleRefundCount = Math.round(
    metrics.currentRefundRate * exportSources.length
  );
  const csvRows = exportSources.map((source, index) => {
    const location = locations[index % locations.length];
    const utm = utmLinks[index % utmLinks.length];
    const salePriceCents = Math.round(safeDivide(source.revenueCents, source.sales || 1));
    const feeCents = Math.round(salePriceCents * 0.1);
    const taxCents = Math.round(salePriceCents * 0.06);
    const refunded = index < sampleRefundCount ? "1" : "0";
    const [buyerName, buyerEmail] = customers[index % customers.length];

    return {
      "Purchase ID": `demo-${product.id}-${index + 1}`,
      "Item Name": product.name,
      "Buyer Name": buyerName,
      "Purchase email": buyerEmail,
      "Buyer Email": buyerEmail,
      "Do not contact": index % 5 === 0 ? "1" : "0",
      "Purchase Date": `2026-04-${String(20 + index).padStart(2, "0")}`,
      "Purchase Time (UTC timezone)": `${String(14 + index).padStart(2, "0")}:30:00`,
      "Subtotal ($)": (salePriceCents / 100).toFixed(2),
      "Taxes ($)": (taxCents / 100).toFixed(2),
      "Sale Price ($)": (salePriceCents / 100).toFixed(2),
      "Fees ($)": (feeCents / 100).toFixed(2),
      "Net Total ($)": ((salePriceCents - feeCents) / 100).toFixed(2),
      "Tax Included in Price?": "0",
      State: location.region,
      Country: location.country,
      Referrer: source.name,
      "Refunded?": refunded,
      "Partial Refund ($)": refunded === "1" ? (salePriceCents / 200).toFixed(2) : "0.00",
      "Fully Refunded?": "0",
      "Disputed?": "0",
      Variants: index % 2 === 0 ? "standard" : "extended",
      "Discount Code": index % 3 === 0 ? "LAUNCH10" : "",
      "Recurring Charge?": index % 4 === 0 ? "1" : "0",
      "Free trial purchase?": "0",
      "Product ID": product.id,
      Quantity: "1",
      Recurrence: index % 4 === 0 ? "Monthly" : "",
      Affiliate: index % 4 === 1 ? "partner@example.com" : "",
      "Affiliate commission ($)": index % 4 === 1 ? (salePriceCents * 0.2 / 100).toFixed(2) : "0.00",
      "Payment Type": index % 3 === 0 ? "PayPal" : "Card",
      "Discover?": source.name.includes("Discover") ? "1" : "0",
      "UTM Source": utm.source,
      "UTM Medium": utm.medium,
      "UTM Campaign": utm.campaign,
      "UTM Destination": utm.destination,
      "Purchasing Power Parity Discounted?": index % 5 === 2 ? "1" : "0",
      "Upsold?": index % 4 === 2 ? "1" : "0",
      "Sent Abandoned Cart Email?": index % 3 === 2 ? "1" : "0",
      Rating: product.rating,
    };
  });

  return {
    ...dashboard,
    csv: {
      columns: Object.keys(csvRows[0] ?? {}),
      rows: csvRows,
      timezoneNote: "CSV export uses UTC; dashboard filters use creator local time.",
    },
  };
};

export const buildProductMetrics = (product) => {
  const { current, previous } = product;
  const currentConversion = safeDivide(current.sales, current.views);
  const previousConversion = safeDivide(previous.sales, previous.views);
  const currentRefundRate = safeDivide(current.refunds, current.sales);
  const previousRefundRate = safeDivide(previous.refunds, previous.sales);
  const currentAverageOrderCents = Math.round(
    safeDivide(current.revenueCents, current.sales)
  );
  const previousAverageOrderCents = Math.round(
    safeDivide(previous.revenueCents, previous.sales)
  );
  const currentSources = buildSourceMetrics(current.sources, currentConversion);
  const previousSources = buildSourceMetrics(previous.sources, previousConversion);
  const topSource = currentSources[0] ?? null;
  const strongestSource =
    currentSources
      .filter((source) => source.sales >= MIN_SOURCE_SALES)
      .sort((a, b) => b.conversion - a.conversion)[0] ?? topSource;
  const metadataCompleteness = buildMetadataCompleteness(product);

  return {
    currentViews: current.views,
    previousViews: previous.views,
    viewsDelta: current.views - previous.views,
    viewsDeltaPercent: round(percentDelta(current.views, previous.views)),
    currentSales: current.sales,
    previousSales: previous.sales,
    salesDelta: current.sales - previous.sales,
    salesDeltaPercent: round(percentDelta(current.sales, previous.sales)),
    currentRevenueCents: current.revenueCents,
    previousRevenueCents: previous.revenueCents,
    revenueDeltaCents: current.revenueCents - previous.revenueCents,
    revenueDeltaPercent: round(
      percentDelta(current.revenueCents, previous.revenueCents)
    ),
    currentConversion: round(currentConversion),
    previousConversion: round(previousConversion),
    conversionDelta: round(currentConversion - previousConversion),
    conversionDeltaPercent: round(percentDelta(currentConversion, previousConversion)),
    currentRefundRate: round(currentRefundRate),
    previousRefundRate: round(previousRefundRate),
    refundRateDelta: round(currentRefundRate - previousRefundRate),
    refundRateDeltaPercent: round(percentDelta(currentRefundRate, previousRefundRate)),
    currentRefunds: current.refunds,
    previousRefunds: previous.refunds,
    currentRefundCents: current.refundCents,
    previousRefundCents: previous.refundCents,
    currentAverageOrderCents,
    previousAverageOrderCents,
    averageOrderDeltaCents: currentAverageOrderCents - previousAverageOrderCents,
    discoverImpressions: current.discoverImpressions,
    previousDiscoverImpressions: previous.discoverImpressions,
    discoverImpressionsDelta: current.discoverImpressions - previous.discoverImpressions,
    discoverImpressionsDeltaPercent: round(
      percentDelta(current.discoverImpressions, previous.discoverImpressions)
    ),
    currentSources,
    previousSources,
    topSource,
    strongestSource,
    sourceConversion: topSource ? topSource.conversion : 0,
    metadataCompleteness,
  };
};

export const detectSignals = (product, metrics) => {
  const signals = [];
  const conversionIsFalling =
    metrics.previousConversion > 0 &&
    metrics.currentConversion < metrics.previousConversion * 0.8;
  const trafficIsHighOrGrowing =
    metrics.currentViews >= HIGH_TRAFFIC_VIEWS || metrics.viewsDeltaPercent >= 0.3;

  if (trafficIsHighOrGrowing && conversionIsFalling) {
    signals.push(
      signal("high-traffic-falling-conversion", "conversion", "high", {
        views: metrics.currentViews,
        previousConversion: metrics.previousConversion,
        currentConversion: metrics.currentConversion,
        viewsDeltaPercent: metrics.viewsDeltaPercent,
      })
    );
  }

  const outperformingSource = metrics.currentSources.find(
    (source) =>
      source.sales >= MIN_SOURCE_SALES &&
      source.conversion >= metrics.currentConversion * 1.5
  );

  if (outperformingSource) {
    signals.push(
      signal("source-outperformance", "source", "medium", {
        source: outperformingSource,
        overallConversion: metrics.currentConversion,
      })
    );
  }

  if (
    metrics.discoverImpressions >= 500 &&
    metrics.metadataCompleteness.score < 0.8
  ) {
    signals.push(
      signal("discover-metadata-gap", "discover", "medium", {
        discoverImpressions: metrics.discoverImpressions,
        metadataCompleteness: metrics.metadataCompleteness,
      })
    );
  }

  const refundRateJumped =
    metrics.previousRefundRate > 0
      ? metrics.currentRefundRate >= metrics.previousRefundRate * 1.5
      : metrics.currentRefundRate > 0;

  if (
    metrics.currentRefunds >= 3 &&
    metrics.currentRefundRate >= REFUND_WARNING_RATE &&
    refundRateJumped
  ) {
    signals.push(
      signal("refund-warning", "refunds", "high", {
        refunds: metrics.currentRefunds,
        refundRate: metrics.currentRefundRate,
        previousRefundRate: metrics.previousRefundRate,
        refundCents: metrics.currentRefundCents,
      })
    );
  }

  const priceIsMeaningful = product.priceCents >= 1500;
  const enoughTrafficForPriceRead = metrics.currentViews >= 300;
  const packagingUseful =
    priceIsMeaningful &&
    enoughTrafficForPriceRead &&
    (metrics.conversionDeltaPercent <= -0.15 ||
      metrics.currentRefundRate >= 0.06 ||
      (product.priceCents >= 4000 && metrics.currentConversion < 0.035));

  if (packagingUseful) {
    signals.push(
      signal("pricing-packaging-experiment", "pricing", "low", {
        priceCents: product.priceCents,
        averageOrderCents: metrics.currentAverageOrderCents,
        currentConversion: metrics.currentConversion,
        refundRate: metrics.currentRefundRate,
      })
    );
  }

  return signals;
};

export const generateSuggestions = (product, metrics, signals) => {
  const suggestions = signals.map((item) => {
    if (item.id === "high-traffic-falling-conversion") {
      return {
        id: "tighten-positioning",
        type: "conversion",
        label: "Conversion",
        title: "Tighten the first-screen positioning",
        recommendation:
          "Move the buyer outcome into the first sentence and make the preview or hero copy match the traffic source that is now sending the most views.",
        reason:
          `${metrics.currentViews.toLocaleString("en-US")} people viewed this product, but conversion is ${formatPercent(metrics.currentConversion)} after being ${formatPercent(metrics.previousConversion)} in the previous period, so the page is attracting attention without turning enough of it into purchases. Here is why we recommend improving the first-screen positioning: clearer outcome copy should convert the traffic you already have before you change price or broaden promotion.`,
        whyItMatters:
          "The product is getting meaningful attention, but fewer visitors are buying compared with the previous period.",
        confidence: "high",
        action: makeAction("edit_description", "Update product description", false, {
          reviewTitle: "Draft a sharper first sentence",
          copyText:
            "For independent creators who need a calm operating system for launches, content, sponsors, and revenue reviews.",
          steps: [
            "Open the product description editor.",
            "Move the buyer outcome into the first sentence.",
            "Mirror the strongest traffic source's language in the preview copy.",
            "Leave the price unchanged until the next analytics window.",
          ],
        }),
        evidence: [
          {
            label: "Current views",
            value: metrics.currentViews.toLocaleString("en-US"),
            comparison: `${formatPercent(metrics.viewsDeltaPercent)} vs previous period`,
          },
          {
            label: "Conversion",
            value: formatPercent(metrics.currentConversion),
            comparison: `down from ${formatPercent(metrics.previousConversion)}`,
          },
        ],
      };
    }

    if (item.id === "source-outperformance") {
      return {
        id: "double-down-on-source",
        type: "source",
        label: "Traffic source",
        title: `Lean into ${item.source.name}`,
        recommendation:
          "Reuse the message, examples, or offer framing from this source in the product page and next promotion.",
        reason:
          `${item.source.name} is converting at ${formatPercent(item.source.conversion)} while the product average is ${formatPercent(item.overallConversion)}, so this source is already showing which audience or promise is working. Here is why we recommend leaning into it: reusing that message in the product page and next promotion should improve conversion by matching the buyer intent that is already proving out.`,
        whyItMatters:
          "One source is converting better than the product average, which gives you a concrete clue about what audience or framing is resonating.",
        confidence: "medium",
        action: makeAction("review_source", `Review ${item.source.name} traffic`, false, {
          reviewTitle: `Turn ${item.source.name} into the next test`,
          copyText: `Use the ${item.source.name} angle in the next product-page edit and promotion, then compare conversion against the product average.`,
          steps: [
            `Review the promise, example, or audience used in ${item.source.name}.`,
            "Reuse the winning message in the product page or next promotion.",
            "Track whether the source continues to beat the product average.",
          ],
        }),
        evidence: [
          {
            label: `${item.source.name} conversion`,
            value: formatPercent(item.source.conversion),
            comparison: `product average is ${formatPercent(item.overallConversion)}`,
          },
          {
            label: `${item.source.name} revenue`,
            value: formatCurrency(item.source.revenueCents, product.currency),
          },
        ],
      };
    }

    if (item.id === "discover-metadata-gap") {
      const missing = item.metadataCompleteness.missing.join(", ");
      return {
        id: "complete-discover-metadata",
        type: "discover",
        label: "Discover",
        title: "Make the Discover listing easier to classify",
        recommendation:
          "Fill in the missing metadata and add specific tags that describe the buyer, use case, and format.",
        reason:
          `Discover produced ${item.discoverImpressions.toLocaleString("en-US")} impressions while metadata completeness is only ${formatPercent(item.metadataCompleteness.score)}${missing ? ` and missing ${missing}` : ""}, so Gumroad has traffic context but not enough classification detail. Here is why we recommend improving the listing metadata: clearer category and tags should help the right buyers understand the product faster and give Discover cleaner signals to work with.`,
        whyItMatters:
          "Discover is creating impressions, but incomplete metadata can make it harder for the right buyers to understand or find the product.",
        confidence: "medium",
        action: makeAction("edit_metadata", "Update category and tags", false, {
          reviewTitle: "Tighten Discover metadata",
          copyText:
            "Add tags that describe the buyer, use case, and product format instead of broad one-word labels.",
          steps: [
            "Fill the missing category if it is blank.",
            "Add at least four specific tags.",
            "Keep tags tied to actual product content, not broad search bait.",
          ],
        }),
        evidence: [
          {
            label: "Discover impressions",
            value: item.discoverImpressions.toLocaleString("en-US"),
          },
          {
            label: "Metadata completeness",
            value: formatPercent(item.metadataCompleteness.score),
            comparison: missing ? `missing: ${missing}` : undefined,
          },
        ],
      };
    }

    if (item.id === "refund-warning") {
      return {
        id: "clarify-expectations",
        type: "refunds",
        label: "Refunds",
        title: "Clarify what buyers get before checkout",
        recommendation:
          "Add a short contents section, compatibility notes, and a clearer refund expectation near the buy button.",
        reason:
          `Refund rate is ${formatPercent(item.refundRate)} after being ${formatPercent(item.previousRefundRate)}, so buyers may be hitting a gap between what the page promises and what they receive. Here is why we recommend clarifying expectations near checkout: a tighter contents, compatibility, and refund note should reduce avoidable mismatches before they become refund requests.`,
        whyItMatters:
          "Refunds rose in the current period, which can point to a mismatch between the sales page and the delivered product.",
        confidence: "high",
        action: makeAction(
          "edit_product_page",
          "Clarify included files and expectations",
          false,
          {
            reviewTitle: "Clarify what buyers receive",
            copyText:
              "Includes the full file list, compatibility notes, setup steps, and refund expectations before checkout.",
            steps: [
              "Add a short contents section near the buy button.",
              "Call out compatibility or usage requirements.",
              "Set refund expectations before purchase.",
            ],
          }
        ),
        evidence: [
          {
            label: "Refund rate",
            value: formatPercent(item.refundRate),
            comparison: `was ${formatPercent(item.previousRefundRate)}`,
          },
          {
            label: "Refunded amount",
            value: formatCurrency(item.refundCents, product.currency),
          },
        ],
      };
    }

    if (item.id === "pricing-packaging-experiment") {
      return {
        id: "test-packaging",
        type: "pricing",
        label: "Pricing",
        title: "Test a clearer package ladder",
        recommendation:
          "Try a simple packaging experiment: keep the current product as the base offer and test a higher-value bundle with examples, bonuses, or a commercial-use tier.",
        reason:
          `The current price is ${formatCurrency(item.priceCents, product.currency)} and average order value is ${formatCurrency(item.averageOrderCents, product.currency)}, so there is enough purchase behavior to test packaging without immediately changing the base offer. Here is why we recommend a package ladder: a clearer bundle or commercial-use tier can improve revenue per buyer while keeping the existing product stable for comparison.`,
        whyItMatters:
          "The product has enough traffic to learn from a packaging test without making a permanent price change.",
        confidence: "low",
        action: makeAction("create_experiment", "Draft a packaging experiment", false, {
          reviewTitle: "Draft a packaging test",
          copyText:
            "Keep the current product as the base offer and test a higher-value bundle with examples, bonuses, or a commercial-use tier.",
          steps: [
            "Keep the existing product and price live.",
            "Draft one higher-value package with clear additional value.",
            "Run the test as an experiment before changing the base offer.",
          ],
        }),
        evidence: [
          {
            label: "Current price",
            value: formatCurrency(item.priceCents, product.currency),
          },
          {
            label: "Average order",
            value: formatCurrency(item.averageOrderCents, product.currency),
          },
        ],
      };
    }

    return null;
  });

  const filtered = suggestions.filter(Boolean);

  if (filtered.length > 0) {
    return filtered;
  }

  return [
    {
      id: "collect-more-signal",
      type: "baseline",
      label: "Baseline",
      title: "Keep collecting signal before changing the offer",
      recommendation:
        "Hold pricing steady and focus the next promotion on one clear audience so the next analytics period is easier to read.",
      reason:
        `The current period has ${metrics.currentViews.toLocaleString("en-US")} views, ${metrics.currentSales.toLocaleString("en-US")} sales, and ${formatPercent(metrics.currentConversion)} conversion without a dominant warning signal, so the best move is to collect cleaner evidence before changing the offer. Here is why we recommend one focused promotion: it creates a readable test window where you can see whether a specific audience and channel actually improves conversion.`,
      whyItMatters:
        "The current data does not show a strong issue yet, so a small controlled promotion is more useful than a broad rewrite.",
      confidence: "low",
      action: makeAction("plan_promotion", "Plan one focused promotion", false, {
        reviewTitle: "Plan one clean signal test",
        copyText:
          "Run one focused promotion for a single audience so the next analytics period is easier to interpret.",
        steps: [
          "Choose one audience and one channel.",
          "Keep the product page stable during the promotion.",
          "Review views, sales, and conversion after the next period.",
        ],
      }),
      evidence: [
        {
          label: "Current views",
          value: metrics.currentViews.toLocaleString("en-US"),
        },
        {
          label: "Current sales",
          value: metrics.currentSales.toLocaleString("en-US"),
          comparison: `${formatPercent(metrics.currentConversion)} conversion`,
        },
      ],
    },
  ];
};
