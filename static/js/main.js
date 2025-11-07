async function fetchJSON(url) {
  const res = await fetch(url);
  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    const msg = text?.slice(0, 500) || res.statusText || 'Unknown error';
    throw new Error(`Server error (${res.status}): ${msg}`);
  }
  if (!res.ok) {
    const msg = data?.error || res.statusText || 'Unknown error';
    const err = new Error(msg);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

const gridEl = document.getElementById('stocksGrid');
const showMoreBtn = document.getElementById('showMore');
const summaryEl = document.getElementById('summary');
const errorsEl = document.getElementById('errors');

let allQuotes = [];   // full dataset from /api/quotes_all?limit=all
let shownCount = 0;   // how many cards are currently visible
const PAGE_SIZE = 6;  // show 6 at a time

function fmtNumber(x) {
  if (x === null || x === undefined || Number.isNaN(x)) return '—';
  try {
    const n = Number(x);
    if (!Number.isFinite(n)) return String(x);
    if (Math.abs(n) >= 1000) return n.toLocaleString();
    return n % 1 === 0 ? n.toString() : n.toFixed(2);
  } catch {
    return String(x);
  }
}

function makeStockCard(q) {
  const change = q.change ?? 0;
  const pct = q.change_pct ?? 0;
  const up = Number(pct) > 0;

  const badgeClass = up ? 'badge chg-pos' : 'badge chg-neg';
  const pctStr = (pct === null || pct === undefined) ? '—' : `${pct > 0 ? '+' : ''}${pct}%`;

  const div = document.createElement('div');
  div.className = 'stock-card';

  div.innerHTML = `
    <div class="stock-top">
      <div>
        <div class="sym">${q.symbol ?? ''}</div>
        <div class="ex small">${q.currency || 'INR'}</div>
      </div>
      <div class="price">${fmtNumber(q.price)}</div>
    </div>
    <div class="meta">
      <span class="${badgeClass}">${pctStr}</span>
      <span class="small">Change: ${fmtNumber(change)}</span>
      <span class="small">MCap: ${fmtNumber(q.market_cap)}</span>
    </div>
  `;

  // Click to analyze this symbol (uses /api/summary)
  div.addEventListener('click', async () => {
    try {
      errorsEl.style.display = 'none';
      const data = await fetchJSON(`/api/summary?symbol=${encodeURIComponent(q.symbol)}`);
      summaryEl.innerHTML = `
        <h3>Signal: ${data.signal} (Score ${data.score})</h3>
        <ul>${(data.reasons || []).map(r => `<li>${r}</li>`).join('')}</ul>
        <p><strong>PE:</strong> ${data.fundamentals?.trailingPe ?? '—'} |
           <strong>ROE:</strong> ${data.fundamentals?.returnOnEquity ?? '—'} |
           <strong>D/E:</strong> ${data.fundamentals?.debtToEquity ?? '—'}</p>
      `;
      summaryEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) {
      errorsEl.textContent = e.message || 'Failed to load summary';
      errorsEl.style.display = 'block';
    }
  });

  return div;
}

function renderNextPage() {
  const next = allQuotes.slice(shownCount, shownCount + PAGE_SIZE);
  next.forEach(q => gridEl.appendChild(makeStockCard(q)));
  shownCount += next.length;
  if (shownCount >= allQuotes.length) {
    showMoreBtn.classList.add('hidden');
  } else {
    showMoreBtn.classList.remove('hidden');
  }
}

async function loadAllStocks() {
  try {
    errorsEl.style.display = 'none';
    // Load entire demo dataset
    const resp = await fetchJSON('/api/quotes_all?limit=all');
    allQuotes = Array.isArray(resp?.data) ? resp.data : [];
    // Basic sort by symbol for stable layout
    allQuotes.sort((a, b) => String(a.symbol).localeCompare(String(b.symbol)));
    // Reset grid
    gridEl.innerHTML = '';
    shownCount = 0;
    renderNextPage(); // first 6
  } catch (e) {
    errorsEl.textContent = e.message || 'Failed to load demo stocks';
    errorsEl.style.display = 'block';
  }
}

document.getElementById('go').addEventListener('click', async () => {
  const input = document.getElementById('symbol').value.trim();
  if (!input) {
    errorsEl.textContent = 'Please enter a symbol present in the demo CSV (e.g., ACC.NS, ADANIENT.NS).';
    errorsEl.style.display = 'block';
    return;
  }
  try {
    errorsEl.style.display = 'none';
    const symbol = input.toUpperCase();
    const data = await fetchJSON(`/api/summary?symbol=${encodeURIComponent(symbol)}`);
    summaryEl.innerHTML = `
      <h3>Signal: ${data.signal} (Score ${data.score})</h3>
      <ul>${(data.reasons || []).map(r => `<li>${r}</li>`).join('')}</ul>
      <p><strong>PE:</strong> ${data.fundamentals?.trailingPe ?? '—'} |
         <strong>ROE:</strong> ${data.fundamentals?.returnOnEquity ?? '—'} |
         <strong>D/E:</strong> ${data.fundamentals?.debtToEquity ?? '—'}</p>
    `;
  } catch (e) {
    errorsEl.textContent = e.message || 'Failed to load summary';
    errorsEl.style.display = 'block';
  }
});

showMoreBtn.addEventListener('click', renderNextPage);

// Load grid on page load
loadAllStocks();
