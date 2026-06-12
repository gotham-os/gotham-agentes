import fs from "node:fs/promises";
import path from "node:path";

const DEFAULT_EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

function logStep(message) {
  console.log(`[meta-ads] ${message}`);
}

function parseArgs(argv) {
  const parsed = { _: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const next = argv[index + 1];
      if (!next || next.startsWith("--")) parsed[key] = true;
      else {
        parsed[key] = next;
        index += 1;
      }
    } else {
      parsed._.push(arg);
    }
  }
  return parsed;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

async function writeJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function slugify(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

function unique(values) {
  return [...new Set(values.map((value) => String(value || "").trim()).filter(Boolean))];
}

function toNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function cleanLine(value) {
  return String(value || "")
    .replace(/[\u200b\u200c\u200d\ufeff]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function decodeHtmlEntities(value) {
  return String(value || "")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCodePoint(Number.parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number.parseInt(code, 10)));
}

function htmlToText(value) {
  return decodeHtmlEntities(String(value || ""))
    .replace(/<script[\s\S]*?<\/script>/gi, "\n")
    .replace(/<style[\s\S]*?<\/style>/gi, "\n")
    .replace(/<svg[\s\S]*?<\/svg>/gi, "\n")
    .replace(/<(br|hr)\b[^>]*>/gi, "\n")
    .replace(/<\/(div|p|span|a|section|article|header|footer|li|ul|ol|h1|h2|h3|h4|button)>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .split("\n")
    .map(cleanLine)
    .filter(Boolean)
    .join("\n");
}

function normalizeInputText(value) {
  const raw = String(value || "");
  if (/<html[\s>]|<body[\s>]|<div[\s>]/i.test(raw)) return htmlToText(raw);
  return raw;
}

function fingerprintText(value) {
  return normalizeText(value)
    .replace(/https?:\/\/\S+|www\.\S+/g, " ")
    .replace(
      /\b(?:[a-z0-9-]+\.)+(?:com\.br|net\.br|org\.br|edu\.br|gov\.br|com|net|org|io|ai|app|dev|co|br|digital|online|site|store|me)\b/g,
      " "
    )
    .replace(/\b(o|a|os|as|de|da|do|das|dos|e|em|para|por|com|que|se|um|uma|the|and|for|to|of|in)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 220);
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractDomains(value) {
  const text = String(value || "");
  const domains = [];
  const urlMatches = text.matchAll(/https?:\/\/(?:www\.)?([^\/\s"'<>]+)/gi);
  for (const match of urlMatches) domains.push(match[1]);

  const standaloneMatches = text.matchAll(
    /\b((?:[a-z0-9-]+\.)+(?:com\.br|net\.br|org\.br|edu\.br|gov\.br|com|net|org|io|ai|app|dev|co|br|digital|online|site|store|me))\b/gi
  );
  for (const match of standaloneMatches) domains.push(match[1]);

  return unique(
    domains
      .map((domain) =>
        cleanLine(domain)
          .toLowerCase()
          .replace(/^www\./, "")
          .replace(/[),.;:]+$/g, "")
      )
      .filter((domain) => domain.length >= 4 && !domain.includes("fbcdn.net") && !domain.includes("static.xx"))
  );
}

function parseCreativeVariants(text) {
  const match = String(text || "").match(
    /(\d+)\s+(?:an[uú]ncios?|ads?)\s+(?:usam|usa|use|uses)\s+(?:esse|este|this)\s+(?:criativo|creative)\s+(?:e|and)\s+(?:esse|este|this)?\s*(?:texto|text)/i
  );
  return match ? Math.max(1, Number.parseInt(match[1], 10)) : 1;
}

function toTerms(values) {
  return unique((Array.isArray(values) ? values : [values]).flatMap((value) => {
    if (!value) return [];
    return String(value)
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }));
}

function hasTerm(text, term) {
  const normalized = normalizeText(term);
  if (!normalized) return false;
  if (text.includes(normalized)) return true;
  if (normalized.length > 5 && text.includes(normalized.slice(0, -1))) return true;
  return false;
}

function scoreCardRelevance(card, context) {
  const relevance = context.relevance || {};
  const text = normalizeText(
    [
      card.page_name,
      card.copy_preview,
      ...(card.destination_domains || [])
    ].join(" ")
  );
  const queryTerms = normalizeText(context.query)
    .split(" ")
    .filter((term) => term.length >= 3 && !["para", "com", "que", "dos", "das"].includes(term));
  const requiredAll = toTerms(relevance.required_all);
  const requiredAny = toTerms(relevance.required_any);
  const excludeAny = toTerms(relevance.exclude_any);
  const matchedQueryTerms = queryTerms.filter((term) => hasTerm(text, term));
  const matchedRequiredAll = requiredAll.filter((term) => hasTerm(text, term));
  const matchedRequiredAny = requiredAny.filter((term) => hasTerm(text, term));
  const matchedExclude = excludeAny.filter((term) => hasTerm(text, term));
  const minQueryTerms = Number(relevance.min_query_terms || Math.min(2, queryTerms.length || 1));
  const queryOk = queryTerms.length ? matchedQueryTerms.length >= minQueryTerms : true;
  const allOk = matchedRequiredAll.length === requiredAll.length;
  const anyOk = requiredAny.length ? matchedRequiredAny.length > 0 : true;
  const excluded = matchedExclude.length > 0;
  const relevant = queryOk && allOk && anyOk && !excluded;

  let score = 0;
  if (queryOk) score += 35;
  score += matchedQueryTerms.length * 10;
  score += matchedRequiredAll.length * 18;
  score += matchedRequiredAny.length * 10;
  if (excluded) score -= 50;

  return {
    relevant,
    score: Math.max(0, Math.min(100, score)),
    matched_query_terms: matchedQueryTerms,
    matched_required_all: matchedRequiredAll,
    matched_required_any: matchedRequiredAny,
    excluded_terms: matchedExclude
  };
}

function isChromeLine(line) {
  return (
    /^(Library ID|Identificação da biblioteca):/i.test(line) ||
    /^(Active|Ativo)$/i.test(line) ||
    /^(Inactive|Inativo)$/i.test(line) ||
    /^(Started running on|Veiculação iniciada em)/i.test(line) ||
    /^(Platforms?|Plataformas)$/i.test(line) ||
    /^(Sponsored|Patrocinado)$/i.test(line) ||
    /^Esse anúncio tem várias versões/i.test(line) ||
    /^\d+\s+an[uú]ncios?\s+usam/i.test(line) ||
    /^\d+\s+ads?\s+use/i.test(line) ||
    /^Abrir menu/i.test(line) ||
    /^Ver resumo/i.test(line) ||
    /^Ver detalhes do anúncio/i.test(line) ||
    /^Acessar o perfil/i.test(line) ||
    /^Reproduzir/i.test(line) ||
    /^Configurações$/i.test(line) ||
    /^Entrar no modo de tela cheia/i.test(line) ||
    /^Change Position$/i.test(line) ||
    /^Alterar volume$/i.test(line) ||
    /^\d+:\d{2}(\s*\/\s*\d+:\d{2})?$/.test(line)
  );
}

function parseApproxDate(text) {
  const started = text.match(/(?:Started running on|Veiculação iniciada em)\s+([^\n]+)/i);
  const active = /(^|\n)\s*(Active|Ativo)\s*(\n|$)/i.test(text);
  return { started_running_on: cleanLine(started?.[1] || ""), active };
}

function parseCardsFromText(pageText, context) {
  const text = normalizeInputText(pageText).replace(/\r/g, "");
  const rawParts = text.split(/(?=(?:Library ID|Identificação da biblioteca):\s*\d+)/gi);
  const cards = [];

  for (const rawPart of rawParts) {
    const part = rawPart.trim();
    const idMatch = part.match(/(?:Library ID|Identificação da biblioteca):\s*(\d+)/i);
    if (!idMatch) continue;

    const lines = unique(
      part
        .split("\n")
        .map(cleanLine)
        .filter((line) => line && line.length < 500)
    );
    const pageName = lines.find((line) => !isChromeLine(line)) || "";
    const dateInfo = parseApproxDate(part);
    const copyLines = lines.filter((line) =>
      !isChromeLine(line) &&
      line !== pageName
    );
    const copyPreview = copyLines.slice(0, 8).join(" | ").slice(0, 900);
    const destinationDomains = extractDomains(`${part}\n${copyPreview}`);

    const card = {
      library_id: idMatch[1],
      query: context.query,
      cluster_key: context.cluster_key,
      country: context.country,
      page_name: pageName,
      active: dateInfo.active,
      started_running_on: dateInfo.started_running_on,
      creative_variants_count: parseCreativeVariants(part),
      destination_domains: destinationDomains,
      copy_fingerprint: fingerprintText(copyPreview),
      copy_preview: copyPreview,
      raw_text_preview: part.slice(0, 1400)
    };
    card.relevance = scoreCardRelevance(card, context);
    cards.push(card);
  }

  return cards;
}

function analyzeScale(cards) {
  const explicitDuplicateCards = cards.filter((card) => toNumber(card.creative_variants_count, 1) >= 2);
  const explicitDuplicateAdsEstimate = explicitDuplicateCards.reduce(
    (total, card) => total + toNumber(card.creative_variants_count, 1),
    0
  );
  const maxDuplicateVariants = explicitDuplicateCards.reduce(
    (max, card) => Math.max(max, toNumber(card.creative_variants_count, 1)),
    1
  );
  const groups = new Map();

  for (const card of cards) {
    if (!card.copy_fingerprint || card.copy_fingerprint.length < 35) continue;
    const key = `${card.page_name || "unknown"}|${card.copy_fingerprint}`;
    if (!groups.has(key)) {
      groups.set(key, {
        page_name: card.page_name || "",
        copy_fingerprint: card.copy_fingerprint,
        cards: []
      });
    }
    groups.get(key).cards.push(card);
  }

  const repeatedCopyGroups = [...groups.values()].filter((group) => group.cards.length >= 2);
  const fingerprintGroups = new Map();
  for (const card of cards) {
    if (!card.copy_fingerprint || card.copy_fingerprint.length < 35) continue;
    if (!fingerprintGroups.has(card.copy_fingerprint)) {
      fingerprintGroups.set(card.copy_fingerprint, []);
    }
    fingerprintGroups.get(card.copy_fingerprint).push(card);
  }

  const crossSourceGroups = [...fingerprintGroups.entries()]
    .map(([fingerprint, groupedCards]) => {
      const pages = unique(groupedCards.map((card) => card.page_name));
      const domains = unique(groupedCards.flatMap((card) => card.destination_domains || []));
      return { fingerprint, cards: groupedCards, pages, domains };
    })
    .filter((group) => group.cards.length >= 2 && (group.pages.length >= 2 || group.domains.length >= 2));
  const crossPageGroups = crossSourceGroups.filter((group) => group.pages.length >= 2);
  const crossDomainGroups = crossSourceGroups.filter((group) => group.domains.length >= 2);

  let signal = "low";
  if (
    maxDuplicateVariants >= 5 ||
    explicitDuplicateCards.length >= 3 ||
    crossDomainGroups.length >= 1 ||
    crossPageGroups.length >= 2 ||
    repeatedCopyGroups.length >= 2
  ) {
    signal = "high";
  } else if (
    maxDuplicateVariants >= 2 ||
    explicitDuplicateCards.length >= 1 ||
    crossPageGroups.length >= 1 ||
    repeatedCopyGroups.length >= 1
  ) {
    signal = "medium";
  }

  const explicitExamples = explicitDuplicateCards.slice(0, 4).map((card) => ({
    type: "meta_declared_same_creative_text",
    page_name: card.page_name,
    library_id: card.library_id,
    variants: toNumber(card.creative_variants_count, 1),
    copy_preview: String(card.copy_preview || "").slice(0, 220)
  }));
  const repeatedExamples = repeatedCopyGroups.slice(0, 3).map((group) => ({
    type: "same_page_same_copy",
    page_name: group.page_name,
    duplicate_cards: group.cards.length,
    library_ids: group.cards.map((card) => card.library_id).slice(0, 6),
    copy_fingerprint: group.copy_fingerprint.slice(0, 160)
  }));
  const crossSourceExamples = crossSourceGroups.slice(0, 4).map((group) => ({
    type: group.domains.length >= 2 ? "cross_domain_same_ad_fingerprint" : "cross_page_same_ad_fingerprint",
    source_pages: group.pages.slice(0, 8),
    destination_domains: group.domains.slice(0, 8),
    duplicate_cards: group.cards.length,
    library_ids: group.cards.map((card) => card.library_id).slice(0, 8),
    proof: "same normalized copy fingerprint across distinct page/domain sources",
    copy_fingerprint: group.fingerprint.slice(0, 180)
  }));

  return {
    signal,
    scaled_duplicate_groups: explicitDuplicateCards.length,
    scaled_duplicate_ads_estimate: explicitDuplicateAdsEstimate,
    max_duplicate_variants: maxDuplicateVariants,
    same_page_duplicate_groups: repeatedCopyGroups.length,
    cross_source_duplicate_groups: crossSourceGroups.length,
    cross_page_duplicate_groups: crossPageGroups.length,
    cross_domain_duplicate_groups: crossDomainGroups.length,
    repeated_copy_groups: repeatedCopyGroups.length,
    duplicate_examples: [...crossSourceExamples, ...explicitExamples, ...repeatedExamples].slice(0, 8)
  };
}

function summarizeGlobalScaleGroup(fingerprint, groupedCards) {
  const pages = unique(groupedCards.map((card) => card.page_name));
  const domains = unique(groupedCards.flatMap((card) => card.destination_domains || []));
  const queries = unique(groupedCards.map((card) => card.query));
  const clusters = unique(groupedCards.map((card) => card.cluster_key));
  const libraryIds = unique(groupedCards.map((card) => card.library_id));
  const explicitVariants = groupedCards.reduce(
    (total, card) => total + toNumber(card.creative_variants_count, 1),
    0
  );

  return {
    type:
      domains.length >= 2
        ? "global_cross_domain_same_ad"
        : pages.length >= 2
          ? "global_cross_page_same_ad"
          : queries.length >= 2
            ? "global_cross_query_same_ad"
            : "global_same_ad",
    duplicate_cards: groupedCards.length,
    estimated_total_variants: Math.max(groupedCards.length, explicitVariants),
    source_pages: pages.slice(0, 10),
    destination_domains: domains.slice(0, 10),
    queries: queries.slice(0, 10),
    clusters: clusters.slice(0, 10),
    library_ids: libraryIds.slice(0, 12),
    proof: "same normalized copy fingerprint detected across the full collection, not only inside one search page",
    copy_fingerprint: fingerprint.slice(0, 220),
    copy_preview: String(groupedCards.find((card) => card.copy_preview)?.copy_preview || "").slice(0, 260)
  };
}

function buildGlobalScaleIntelligence(results) {
  const cards = results.flatMap((result) => relevantCards(result.cards || []));
  const groups = new Map();
  for (const card of cards) {
    if (!card.copy_fingerprint || card.copy_fingerprint.length < 35) continue;
    if (!groups.has(card.copy_fingerprint)) groups.set(card.copy_fingerprint, []);
    groups.get(card.copy_fingerprint).push(card);
  }

  const globalGroups = [...groups.entries()]
    .map(([fingerprint, groupedCards]) => summarizeGlobalScaleGroup(fingerprint, groupedCards))
    .filter((group) => {
      const crossSource = group.source_pages.length >= 2 || group.destination_domains.length >= 2;
      const crossQuery = group.queries.length >= 2 || group.clusters.length >= 2;
      return group.duplicate_cards >= 2 && (crossSource || crossQuery);
    })
    .sort((a, b) => {
      const aWeight =
        a.duplicate_cards * 4 +
        a.source_pages.length * 3 +
        a.destination_domains.length * 4 +
        a.queries.length * 2 +
        a.clusters.length * 2;
      const bWeight =
        b.duplicate_cards * 4 +
        b.source_pages.length * 3 +
        b.destination_domains.length * 4 +
        b.queries.length * 2 +
        b.clusters.length * 2;
      return bWeight - aWeight;
    });

  const byCluster = new Map();
  for (const group of globalGroups) {
    for (const cluster of group.clusters) {
      if (!byCluster.has(cluster)) byCluster.set(cluster, []);
      byCluster.get(cluster).push(group);
    }
  }

  return {
    groups: globalGroups.slice(0, 40),
    byCluster
  };
}

function enrichSignalsWithGlobalScale(results) {
  const intelligence = buildGlobalScaleIntelligence(results);
  for (const result of results) {
    const groups = intelligence.byCluster.get(result.cluster_key) || [];
    if (!groups.length || !result.signal) continue;

    const crossDomain = groups.filter((group) => group.destination_domains.length >= 2).length;
    const crossQuery = groups.filter((group) => group.queries.length >= 2).length;
    const crossCluster = groups.filter((group) => group.clusters.length >= 2).length;
    const maxCards = groups.reduce((max, group) => Math.max(max, group.duplicate_cards), 0);
    const globalSignal = crossDomain || groups.length >= 2 || maxCards >= 3 ? "high" : "medium";

    result.signal.metrics.global_scale_signal = globalSignal;
    result.signal.metrics.global_duplicate_groups = groups.length;
    result.signal.metrics.global_cross_query_duplicate_groups = crossQuery;
    result.signal.metrics.global_cross_cluster_duplicate_groups = crossCluster;
    result.signal.metrics.global_cross_domain_duplicate_groups = crossDomain;
    result.signal.metrics.global_duplicate_examples = groups.slice(0, 6);
    result.signal.tags = unique([
      ...(result.signal.tags || []),
      "global_scaled_ad_signal",
      ...(crossQuery ? ["cross_query_duplicate_ad"] : []),
      ...(crossCluster ? ["cross_cluster_duplicate_ad"] : []),
      ...(crossDomain ? ["global_cross_domain_duplicate_ad"] : [])
    ]);
    if (globalSignal === "high") result.signal.strength = "high";
    else if (result.signal.strength === "low") result.signal.strength = "medium";
    result.signal.summary = `${result.signal.summary} Inteligencia global: ${groups.length} grupo(s) de anuncio parecido em paginas/domínios/queries diferentes; cross-domain ${crossDomain}.`;
  }

  return intelligence.groups;
}

function relevantCards(cards) {
  return cards.filter((card) => card.relevance?.relevant !== false);
}

function scoreStrength(cards) {
  const filtered = relevantCards(cards);
  if (!filtered.length) return "low";
  const activeCount = filtered.filter((card) => card.active).length;
  const uniquePages = unique(filtered.map((card) => card.page_name)).length;
  const scale = analyzeScale(filtered);
  if (activeCount >= 8 || uniquePages >= 5 || scale.signal === "high") return "high";
  if (activeCount >= 3 || filtered.length >= 5 || scale.signal === "medium") return "medium";
  return filtered.length ? "low" : "low";
}

function adsToSignal(cards, context, capturedAt, pageUrl) {
  const filtered = relevantCards(cards);
  const activeCount = filtered.filter((card) => card.active).length;
  const pages = unique(filtered.map((card) => card.page_name)).slice(0, 8);
  const ids = unique(filtered.map((card) => card.library_id)).slice(0, 12);
  const scale = analyzeScale(filtered);
  const relevantCount = filtered.length;
  const relevanceRate = cards.length ? relevantCount / cards.length : 0;
  const snippets = filtered
    .map((card) => card.copy_preview)
    .filter(Boolean)
    .slice(0, 3);

  return {
    id: `meta-ads-${slugify(context.cluster_key)}-${slugify(context.query)}`,
    cluster_key: context.cluster_key,
    source: "Meta Ads Library via Playwright",
    source_url: pageUrl,
    captured_at: capturedAt,
    region: context.country,
    evidence_type: relevantCount ? "distribution" : "benchmark",
    strength: scoreStrength(cards),
    title: `Meta Ads Library: "${context.query}" retornou ${cards.length} cards (${relevantCount} relevantes)`,
    summary: relevantCount
      ? `Coleta encontrou ${cards.length} cards, ${relevantCount} relevantes, ${activeCount} ativos e ${pages.length} paginas unicas. Sinal de escala duplicada: ${scale.signal}; grupos cross-page/domain: ${scale.cross_source_duplicate_groups}. Amostras: ${snippets.join(" / ")}`
      : `Nenhum card extraido para "${context.query}". Pode ser falta de demanda, bloqueio da interface, captcha/login ou DOM alterado.`,
    audience: "Anunciantes e compradores alcançados por Meta Ads",
    pain_terms: [context.query, "ads ativos", "concorrentes anunciando"],
    offer_terms: snippets,
    tags: unique([
      "meta_ads",
      "distribution",
      "digital_delivery",
      ...(scale.signal !== "low" ? ["scaled_ads_signal"] : []),
      ...(scale.cross_source_duplicate_groups ? ["cross_source_duplicate_ad"] : []),
      ...(scale.cross_domain_duplicate_groups ? ["cross_domain_duplicate_ad"] : []),
      ...(cards.length && relevanceRate < 0.5 ? ["low_precision_query"] : []),
      ...(context.tags || [])
    ]),
    metrics: {
      query: context.query,
      cards_found: cards.length,
      relevant_cards: relevantCount,
      irrelevant_cards: cards.length - relevantCount,
      relevance_rate: Number(relevanceRate.toFixed(3)),
      active_ads: activeCount,
      unique_pages: pages.length,
      sample_pages: pages,
      sample_library_ids: ids,
      scale_signal: scale.signal,
      scaled_duplicate_groups: scale.scaled_duplicate_groups,
      scaled_duplicate_ads_estimate: scale.scaled_duplicate_ads_estimate,
      max_duplicate_variants: scale.max_duplicate_variants,
      same_page_duplicate_groups: scale.same_page_duplicate_groups,
      cross_source_duplicate_groups: scale.cross_source_duplicate_groups,
      cross_page_duplicate_groups: scale.cross_page_duplicate_groups,
      cross_domain_duplicate_groups: scale.cross_domain_duplicate_groups,
      repeated_copy_groups: scale.repeated_copy_groups,
      duplicate_examples: scale.duplicate_examples
    }
  };
}

function buildUrl(query, country) {
  const params = new URLSearchParams({
    active_status: "active",
    ad_type: "all",
    country,
    q: query,
    search_type: "keyword_unordered",
    media_type: "all"
  });
  return `https://www.facebook.com/ads/library/?${params.toString()}`;
}

async function acceptDialogs(page) {
  const labels = [
    "Allow all cookies",
    "Accept all",
    "Aceitar todos",
    "Permitir todos os cookies",
    "Only allow essential cookies",
    "Permitir apenas cookies essenciais",
    "Fechar",
    "Close"
  ];
  for (const label of labels) {
    try {
      const locator = page.getByRole("button", { name: new RegExp(label, "i") });
      if (await locator.first().isVisible({ timeout: 800 })) {
        await locator.first().click({ timeout: 1200 });
        await page.waitForTimeout(500);
      }
    } catch {
      // Dialog labels vary by locale; ignore misses.
    }
  }
}

async function collectQuery(browser, context, options) {
  const prefix = context.index && context.total ? `[${context.index}/${context.total}]` : "";
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1200 },
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
  });
  const url = buildUrl(context.query, context.country);
  const capturedAt = new Date().toISOString();

  try {
    logStep(`${prefix} abrindo Meta Ads Library: "${context.query}" (${context.cluster_key})`);
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: options.timeoutMs });
    await acceptDialogs(page);
    logStep(`${prefix} pagina carregada; aguardando resultados e rolando ${options.scrollRounds} vez(es)`);
    await page.waitForTimeout(options.initialWaitMs);
    for (let index = 0; index < options.scrollRounds; index += 1) {
      await page.mouse.wheel(0, 1800);
      await page.waitForTimeout(options.scrollWaitMs);
    }

    const pageText = await page.locator("body").innerText({ timeout: options.timeoutMs });
    const cards = parseCardsFromText(pageText, context).slice(0, options.maxAdsPerQuery);
    const signal = adsToSignal(cards, context, capturedAt, url);
    logStep(
      `${prefix} extraidos ${cards.length} cards, ${signal.metrics.active_ads} ativos, ` +
        `${signal.metrics.unique_pages} paginas, escala ${signal.metrics.scale_signal}`
    );
    const screenshotPath = options.snapshotDir
      ? path.join(options.snapshotDir, `${slugify(context.cluster_key)}-${slugify(context.query)}.png`)
      : "";
    const htmlPath = options.snapshotDir
      ? path.join(options.snapshotDir, `${slugify(context.cluster_key)}-${slugify(context.query)}.html`)
      : "";

    if (options.snapshotDir) {
      await fs.mkdir(options.snapshotDir, { recursive: true });
      await page.screenshot({ path: screenshotPath, fullPage: true });
      await fs.writeFile(htmlPath, await page.content(), "utf8");
    }

    return {
      query: context.query,
      cluster_key: context.cluster_key,
      url,
      captured_at: capturedAt,
      status: "ok",
      cards,
      signal,
      snapshot: { screenshot_path: screenshotPath, html_path: htmlPath }
    };
  } catch (error) {
    logStep(`${prefix} erro na query "${context.query}": ${error.message}`);
    return {
      query: context.query,
      cluster_key: context.cluster_key,
      url,
      captured_at: capturedAt,
      status: "error",
      error: error.message,
      cards: [],
      signal: adsToSignal([], context, capturedAt, url),
      snapshot: {}
    };
  } finally {
    await page.close().catch(() => {});
  }
}

async function collectFromFixture(filePath, queryConfig) {
  logStep(`modo fixture: lendo ${filePath}`);
  const text = await fs.readFile(filePath, "utf8");
  const capturedAt = new Date().toISOString();
  const country = queryConfig.country || "BR";
  const total = queryConfig.queries.length;
  const results = queryConfig.queries.map((queryItem, index) => {
    const context = {
      country,
      cluster_key: queryItem.cluster_key,
      query: queryItem.query,
      tags: queryItem.tags || [],
      relevance: queryItem.relevance || {},
      index: index + 1,
      total
    };
    const cards = parseCardsFromText(text, context).slice(0, queryConfig.max_ads_per_query || 12);
    const url = `fixture://${filePath}`;
    const signal = adsToSignal(cards, context, capturedAt, url);
    logStep(
      `[${index + 1}/${total}] fixture "${context.query}": ${cards.length} cards, ` +
        `${signal.metrics.active_ads} ativos, escala ${signal.metrics.scale_signal}`
    );
    return {
      query: context.query,
      cluster_key: context.cluster_key,
      url,
      captured_at: capturedAt,
      status: "fixture",
      cards,
      signal,
      snapshot: {}
    };
  });
  const global_scale_groups = enrichSignalsWithGlobalScale(results);
  logStep(`inteligencia global: ${global_scale_groups.length} grupo(s) de duplicacao/escala detectados`);
  return {
    run_name: "meta-ads-fixture",
    captured_at: capturedAt,
    country,
    results,
    signals: results.map((result) => result.signal),
    ads: results.flatMap((result) => result.cards),
    global_scale_groups
  };
}

async function collectLive(queryConfig, args) {
  let playwright;
  try {
    playwright = await import("playwright-core");
  } catch (error) {
    throw new Error("playwright-core nao esta instalado. Rode: npm install");
  }

  const country = args.country || queryConfig.country || "BR";
  const browserPath = args["browser-path"] || process.env.META_ADS_BROWSER_PATH || DEFAULT_EDGE_PATH;
  const options = {
    maxAdsPerQuery: Number(args["max-ads"] || queryConfig.max_ads_per_query || 12),
    scrollRounds: Number(args["scroll-rounds"] || queryConfig.scroll_rounds || 5),
    initialWaitMs: Number(args["initial-wait-ms"] || 6500),
    scrollWaitMs: Number(args["scroll-wait-ms"] || 1400),
    timeoutMs: Number(args["timeout-ms"] || 45000),
    snapshotDir: args["snapshot-dir"] || "data/raw/meta_ads_snapshots"
  };
  const headless = String(args.headless ?? "true").toLowerCase() !== "false";
  logStep(`coleta real iniciada: ${queryConfig.queries.length} query(s), pais ${country}, max ${options.maxAdsPerQuery} ads/query`);
  logStep(`abrindo navegador: ${browserPath} | headless=${headless}`);
  const browser = await playwright.chromium.launch({
    executablePath: browserPath,
    headless,
    args: ["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"]
  });

  const capturedAt = new Date().toISOString();
  const results = [];
  const total = queryConfig.queries.length;
  try {
    for (const [index, queryItem] of queryConfig.queries.entries()) {
      const context = {
        country,
        cluster_key: queryItem.cluster_key,
        query: queryItem.query,
        tags: queryItem.tags || [],
        relevance: queryItem.relevance || {},
        index: index + 1,
        total
      };
      results.push(await collectQuery(browser, context, options));
    }
  } finally {
    logStep("fechando navegador");
    await browser.close().catch(() => {});
  }

  const global_scale_groups = enrichSignalsWithGlobalScale(results);
  logStep(`inteligencia global: ${global_scale_groups.length} grupo(s) de duplicacao/escala detectados`);
  return {
    run_name: "meta-ads-library-playwright",
    captured_at: capturedAt,
    country,
    browser_path: browserPath,
    options,
    results,
    signals: results.map((result) => result.signal),
    ads: results.flatMap((result) => result.cards),
    global_scale_groups
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const queriesFile = args["queries-file"] || "data/meta_ads_queries.json";
  logStep(`lendo queries: ${queriesFile}`);
  const queryConfig = await readJson(queriesFile);
  let output;

  if (args["from-fixture"]) {
    output = await collectFromFixture(args["from-fixture"], queryConfig);
  } else {
    output = await collectLive(queryConfig, args);
  }

  const outPath = args.out || "data/raw/meta-ads-library.json";
  logStep(`salvando JSON bruto: ${outPath}`);
  await writeJson(outPath, output);
  logStep(`OK meta ads: ${outPath}`);
  logStep(`queries processadas: ${output.results.length}`);
  logStep(`ads extraidos: ${output.ads.length}`);
  logStep(`sinais gerados: ${output.signals.length}`);
  logStep(`grupos globais de escala/duplicacao: ${output.global_scale_groups?.length || 0}`);
}

main().catch((error) => {
  console.error(`ERROR: ${error.message}`);
  process.exitCode = 1;
});

export { parseCardsFromText, adsToSignal };
