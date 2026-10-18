import { useState } from "react";
import type { FormEvent } from "react";

type LogMatch = {
  date: string;
  job_name: string;
  file: string;
  line: number;
  text: string;
};

type SearchResult = {
  directory: string;
  search_text: string | null;
  files_scanned: number;
  match_count: number;
  truncated: boolean;
  matches: LogMatch[];
};

type SearchForm = {
  date: string;
  jobName: string;
  searchText: string;
  caseSensitive: boolean;
  maxResults: number;
};

const initialForm: SearchForm = {
  date: "",
  jobName: "",
  searchText: "",
  caseSensitive: false,
  maxResults: 100,
};

function App() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function updateForm<K extends keyof SearchForm>(key: K, value: SearchForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);

    const date = form.date.trim();
    const jobName = form.jobName.trim();
    const searchText = form.searchText.trim();
    if (!date && !jobName && !searchText) {
      setError("Enter at least one filter before searching.");
      return;
    }
    if (date && !/^\d{8}$/.test(date)) {
      setError("Enter the date as DDMMYYYY, for example 18062025.");
      return;
    }
    if (!Number.isInteger(form.maxResults) || form.maxResults < 1 || form.maxResults > 1000) {
      setError("Maximum results must be between 1 and 1000.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: date || null,
          job_name: jobName || null,
          search_text: searchText || null,
          case_sensitive: form.caseSensitive,
          max_results: form.maxResults,
        }),
      });
      const payload = (await response.json()) as SearchResult | { error: string };
      if (!response.ok) {
        setError("error" in payload ? payload.error : "Search failed.");
        return;
      }
      setResult(payload as SearchResult);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not connect to the search server.");
    } finally {
      setLoading(false);
    }
  }

  function resetSearch() {
    setForm(initialForm);
    setResult(null);
    setError("");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="AutoSys Log Search home">
          <span className="brand-mark" aria-hidden="true">A</span>
          <span>Ops<span className="brand-muted"> / </span>AutoSys</span>
        </a>
        <span className="server-status"><span className="status-dot" /> LOG SEARCH</span>
      </header>

      <section className="content">
        <div className="intro">
          <div className="eyebrow"><span /> OPERATIONS TOOLKIT</div>
          <h1>Find the signal<br /><span>in your logs.</span></h1>
          <p>Search AutoSys job output by date, job name, or matching text.</p>
        </div>

        <section className="search-card" aria-labelledby="search-heading">
          <div className="card-heading">
            <div>
              <span className="section-kicker">LOG EXPLORER</span>
              <h2 id="search-heading">Build your search</h2>
            </div>
            <span className="path-hint">\\server01\Log\<span>{'{date}'}</span>\<span>{'{job}'}</span></span>
          </div>

          <form onSubmit={submitSearch} noValidate>
            <div className="filter-grid">
              <label className="field">
                <span className="field-label">DATE <span className="optional">OPTIONAL</span></span>
                <span className="input-wrap">
                  <span className="input-icon" aria-hidden="true">▦</span>
                  <input
                    value={form.date}
                    onChange={(event) => updateForm("date", event.target.value)}
                    placeholder="DDMMYYYY"
                    inputMode="numeric"
                    maxLength={8}
                    aria-describedby="date-help"
                  />
                </span>
                <span className="field-help" id="date-help">Example: 18062025</span>
              </label>

              <label className="field">
                <span className="field-label">JOB NAME <span className="optional">OPTIONAL</span></span>
                <span className="input-wrap">
                  <span className="input-icon job-icon" aria-hidden="true">⌘</span>
                  <input
                    value={form.jobName}
                    onChange={(event) => updateForm("jobName", event.target.value)}
                    placeholder="e.g. DAILY_JOB"
                    autoComplete="off"
                  />
                </span>
                <span className="field-help">One folder name</span>
              </label>
            </div>

            <label className="field query-field">
              <span className="field-label">CONTAINS TEXT <span className="optional">OPTIONAL</span></span>
              <span className="input-wrap">
                <span className="input-icon search-icon" aria-hidden="true">⌕</span>
                <input
                  value={form.searchText}
                  onChange={(event) => updateForm("searchText", event.target.value)}
                  placeholder="Search errors, job output, or any log text..."
                  autoComplete="off"
                />
                <kbd>↵</kbd>
              </span>
            </label>

            <div className="options-row">
              <label className="check-control">
                <input
                  type="checkbox"
                  checked={form.caseSensitive}
                  onChange={(event) => updateForm("caseSensitive", event.target.checked)}
                />
                <span className="custom-check" aria-hidden="true" />
                <span>Match case</span>
              </label>
              <label className="limit-control">
                <span>MAX RESULTS</span>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={form.maxResults}
                  onChange={(event) => updateForm("maxResults", Number(event.target.value))}
                />
              </label>
              <span className="limit-note">Up to 1,000 matches</span>
            </div>

            <div className="form-footer">
              <span className="form-note"><span className="info-icon">i</span> Use any filter combination. At least one is required.</span>
              <div className="actions">
                <button className="reset-button" type="button" onClick={resetSearch}>Reset</button>
                <button className="search-button" type="submit" disabled={loading}>
                  {loading ? <><span className="spinner" /> Searching</> : <>Search logs <span aria-hidden="true">→</span></>}
                </button>
              </div>
            </div>
          </form>
        </section>

        {error && <div className="notice error-notice" role="alert"><span>!</span>{error}</div>}

        {result && (
          <section className="results-section" aria-live="polite">
            <div className="results-heading">
              <div>
                <span className="section-kicker">SEARCH OUTPUT</span>
                <h2>Matches <span className="count-badge">{result.match_count}</span></h2>
              </div>
              <div className="scan-summary">{result.files_scanned.toLocaleString()} files scanned</div>
            </div>
            {result.truncated && (
              <div className="notice truncated-notice">Showing the first {result.match_count} matches. Increase the limit to see more.</div>
            )}
            {result.matches.length === 0 ? (
              <div className="empty-state">
                <span className="empty-mark">⌕</span>
                <h3>No matching lines</h3>
                <p>Try another search term or broaden your filters.</p>
              </div>
            ) : (
              <div className="matches-list">
                {result.matches.map((match, index) => (
                  <article className="match-card" key={`${match.date}-${match.job_name}-${match.file}-${match.line}-${index}`}>
                    <div className="match-meta">
                      <span className="job-tag">{match.job_name}</span>
                      <span className="date-tag">{match.date}</span>
                      <span className="file-path">{match.file}</span>
                      <span className="line-number">LINE {match.line}</span>
                    </div>
                    <pre>{match.text}</pre>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}
      </section>
      <footer className="footer">AUTOSYS LOG SEARCH <span>•</span> READ-ONLY ACCESS</footer>
    </main>
  );
}

export default App;
