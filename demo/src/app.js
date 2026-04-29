import { products } from "../data/products.js";
import {
  buildProductMetrics,
  detectSignals,
  formatCurrency,
  formatPercent,
  generateSuggestions,
} from "./analytics.js";

const state = {
  selectedProductId: products[0]?.id,
  generated: false,
  activeSuggestionId: null,
};

const productSelect = document.querySelector("#product-select");
const productName = document.querySelector("#product-name");
const productDescription = document.querySelector("#product-description");
const productTags = document.querySelector("#product-tags");
const metricGrid = document.querySelector("#metric-grid");
const sourceTable = document.querySelector("#source-table");
const suggestions = document.querySelector("#suggestions");
const confidenceSummary = document.querySelector("#confidence-summary");
const generateButton = document.querySelector("#generate-button");
const barChart = document.querySelector("#bar-chart");
const chartCaption = document.querySelector("#chart-caption");
const actionReview = document.querySelector("#action-review");
const actionReviewTitle = document.querySelector("#action-review-title");
const actionReviewMeta = document.querySelector("#action-review-meta");
const actionReviewCopy = document.querySelector("#action-review-copy");
const actionReviewSteps = document.querySelector("#action-review-steps");
const actionReviewClose = document.querySelector("#action-review-close");
const actionReviewCopyButton = document.querySelector("#action-review-copy-button");
const actionReviewCopyStatus = document.querySelector("#action-review-copy-status");

function getSelectedProduct() {
  return products.find((product) => product.id === state.selectedProductId) ?? products[0];
}

function renderProductOptions() {
  productSelect.innerHTML = products
    .map((product) => `<option value="${product.id}">${product.name}</option>`)
    .join("");
  productSelect.value = state.selectedProductId;
}

function renderProductHeader(product) {
  productName.textContent = product.name;
  productDescription.textContent = product.description;
  productTags.innerHTML = product.tags
    .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join("");
}

function renderMetrics(product, metrics) {
  const cards = [
    {
      label: "Revenue",
      value: formatCurrency(metrics.currentRevenueCents, product.currency),
      change: formatDelta(metrics.revenueDeltaPercent, "prior period"),
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
        <div class="metric-card ${tone}" style="--index: ${index}">
          <div class="metric-label">${card.label}</div>
          <div class="metric-value">${card.value}</div>
          <div class="metric-change ${tone}">${card.change}</div>
        </div>
      `;
    })
    .join("");
}

function renderChart(metrics) {
  const maxValue = Math.max(
    metrics.currentViews,
    metrics.previousViews,
    metrics.currentSales * 20,
    metrics.previousSales * 20,
    1,
  );

  const groups = [
    {
      label: "Prior",
      period: { views: metrics.previousViews, sales: metrics.previousSales },
    },
    {
      label: "Current",
      period: { views: metrics.currentViews, sales: metrics.currentSales },
    },
  ];

  chartCaption.textContent = `${metrics.currentSales.toLocaleString()} sales from ${metrics.currentViews.toLocaleString()} views`;
  barChart.innerHTML = groups
    .map((group, index) => {
      const viewHeight = Math.max(8, (group.period.views / maxValue) * 100);
      const salesHeight = Math.max(8, ((group.period.sales * 20) / maxValue) * 100);

      return `
        <div class="bar-group" aria-label="${group.label} period" style="--index: ${index}">
          <div class="bar-wrap">
            <div class="bar" style="height: ${viewHeight}%"></div>
            <div class="bar-label">${group.label}<br />views</div>
          </div>
          <div class="bar-wrap">
            <div class="bar sales" style="height: ${salesHeight}%"></div>
            <div class="bar-label">${group.label}<br />sales</div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderSources(product, metrics) {
  const rows = product.current.sources
    .slice()
    .sort((a, b) => b.sales - a.sales)
    .map((source, index) => {
      const conversion = source.views > 0 ? source.sales / source.views : 0;
      return `
        <div class="source-row" style="--index: ${index}">
          <div>
            <div class="source-name">${escapeHtml(source.name)}</div>
            <div class="source-meta">${source.views.toLocaleString()} views · ${source.sales.toLocaleString()} sales</div>
          </div>
          <div class="source-conversion">${formatPercent(conversion)}</div>
        </div>
      `;
    });

  sourceTable.innerHTML = rows.join("");
}

function renderSuggestions(product, metrics) {
  if (!state.generated) {
    confidenceSummary.textContent = "Waiting";
    suggestions.innerHTML = `<div class="empty-state">Choose a product and generate insights.</div>`;
    renderActionReview([]);
    return;
  }

  const signals = detectSignals(product, metrics);
  const cards = generateSuggestions(product, metrics, signals);
  const strongCount = signals.filter((signal) => signal.confidence === "high").length;
  confidenceSummary.textContent = strongCount > 0 ? `${strongCount} high-confidence signal` : `${signals.length} signal`;

  if (!cards.some((card) => card.id === state.activeSuggestionId)) {
    state.activeSuggestionId = null;
  }

  suggestions.innerHTML = cards.map(renderSuggestionCard).join("");
  renderActionReview(cards);
}

function renderSuggestionCard(card, index) {
  const isActive = state.activeSuggestionId === card.id;

  return `
    <article class="suggestion-card ${isActive ? "active" : ""}" style="--index: ${index}">
      <div class="suggestion-topline">
        <span class="suggestion-label">${escapeHtml(card.label)}</span>
        <span class="confidence">${escapeHtml(card.confidence)} confidence</span>
      </div>
      <h3>${escapeHtml(card.title)}</h3>
      <p>${escapeHtml(card.recommendation)}</p>
      <p>${escapeHtml(card.whyItMatters)}</p>
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
      <div class="suggestion-action">
        <span>${escapeHtml(card.action?.label ?? card.action)}</span>
        <button class="review-action-button" type="button" data-suggestion-action="${escapeHtml(card.id)}" aria-pressed="${isActive ? "true" : "false"}">
          Review
        </button>
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
  actionReviewMeta.textContent = `${activeCard.label} · ${activeCard.confidence} confidence · review-only`;
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

  renderProductHeader(product);
  renderMetrics(product, metrics);
  renderChart(metrics);
  renderSources(product, metrics);
  renderSuggestions(product, metrics);
}

function formatDelta(value, suffix) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatPercent(value)} vs ${suffix}`;
}

function deltaTone(text) {
  if (text.trim().startsWith("+")) return "good";
  if (text.trim().startsWith("0")) return "";
  return "warn";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

productSelect.addEventListener("change", (event) => {
  state.selectedProductId = event.target.value;
  state.generated = false;
  state.activeSuggestionId = null;
  render();
});

generateButton.addEventListener("click", () => {
  state.generated = true;
  state.activeSuggestionId = null;
  render();
});

suggestions.addEventListener("click", (event) => {
  const actionButton = event.target.closest("[data-suggestion-action]");

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

renderProductOptions();
render();
