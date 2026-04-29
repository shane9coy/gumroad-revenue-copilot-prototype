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

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const safeDivide = (numerator, denominator) =>
  denominator > 0 ? numerator / denominator : 0;

const percentDelta = (current, previous) =>
  previous > 0 ? (current - previous) / previous : current > 0 ? 1 : 0;

const round = (value, digits = 4) => Number(value.toFixed(digits));

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
