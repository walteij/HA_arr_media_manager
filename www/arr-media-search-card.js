const ARR_MEDIA_SEARCH_CARD_VERSION = "1.0.0";

class ArrMediaSearchCard extends HTMLElement {
  getConfigElement() {
    return document.createElement("arr-media-search-card-editor");
  }

  getStubConfig() {
    return { title: "ARR Media Search" };
  }

  setConfig(config) {
    if (!config || !config.config_entry_id) {
      throw new Error("config_entry_id is required");
    }
    if (config.max_results != null && (!Number.isInteger(Number(config.max_results)) || Number(config.max_results) < 1 || Number(config.max_results) > 50)) {
      throw new Error("max_results must be an integer between 1 and 50");
    }
    this._config = {
      title: "ARR Media Search",
      max_results: 10,
      search_after_add: true,
      show_overview: true,
      show_posters: true,
      show_existing: true,
      confirm_before_add: true,
      default_query: "",
      compact: false,
      result_columns: 1,
      hide_application_name: false,
      monitoring_mode: "all",
      monitoring_modes: ["all", "future", "missing", "existing", "first", "latest", "none"],
      root_folder_options: [],
      quality_profile_options: [],
      ...config,
    };
    this._results = [];
    this._status = "";
    this._application = "";
    if (!this._loggedVersion) {
      console.info(`ARR Media Search card ${ARR_MEDIA_SEARCH_CARD_VERSION}`);
      this._loggedVersion = true;
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  getCardSize() {
    return 4;
  }

  async _callActionWithResponse(action, data) {
    const response = await this._hass.callService("arr_media_manager", action, data, {}, false, true);
    return response?.response || response || {};
  }

  async _lookup(query) {
    const serviceData = {
      config_entry_id: this._config.config_entry_id,
      query,
      max_results: Number(this._config.max_results),
    };
    return this._callActionWithResponse("lookup", serviceData);
  }

  async _addResult(result, controls, button, status) {
    if (result.lookup_id == null) {
      status.textContent = "Dit resultaat heeft geen lookup_id.";
      return;
    }
    if (result.already_exists) {
      status.textContent = "Dit medium is al aanwezig.";
      return;
    }
    if (this._config.confirm_before_add && !window.confirm(`'${result.title || result.lookup_id}' toevoegen?`)) return;
    button.disabled = true;
    status.textContent = "Toevoegen...";
    const data = {
      config_entry_id: this._config.config_entry_id,
      lookup_id: result.lookup_id,
      search_after_add: controls.searchAfter.checked,
    };
    if (controls.monitoring.value) data.monitoring_mode = controls.monitoring.value;
    if (controls.root.value) data.root_folder = controls.root.value;
    if (controls.quality.value) data.quality_profile = controls.quality.value;

    try {
      const response = await this._callActionWithResponse("add_media", data);
      if (response.status === "partial_success") {
        status.textContent = response.message || "Toegevoegd, maar de zoekopdracht kon niet worden gestart.";
      } else if (response.already_exists) {
        status.textContent = "Dit medium is al aanwezig.";
      } else {
        status.textContent = response.search_accepted ? "Toegevoegd en zoekopdracht gestart." : "Toegevoegd.";
      }
    } catch (error) {
      status.textContent = this._readableError(error, "Toevoegen mislukt.");
      button.disabled = false;
    }
  }

  _makeSelect(labelText, options, selected) {
    const label = document.createElement("label");
    label.className = "field";
    const text = document.createElement("span");
    text.textContent = labelText;
    const select = document.createElement("select");
    for (const option of options) {
      const item = document.createElement("option");
      if (typeof option === "object") {
        item.value = option.value;
        item.textContent = option.label ?? option.value;
      } else {
        item.value = option;
        item.textContent = option;
      }
      select.appendChild(item);
    }
    if (selected != null) select.value = selected;
    label.append(text, select);
    return { label, select };
  }

  _render() {
    if (!this._config) return;
    this.innerHTML = "";

    const card = document.createElement("ha-card");
    const content = document.createElement("div");
    content.className = "content";
    const title = document.createElement("h2");
    title.textContent = this._config.title;
    content.appendChild(title);
    const application = document.createElement("div");
    application.className = "application-status";
    application.textContent = "ARR Media Manager";
    content.appendChild(application);

    const form = document.createElement("div");
    form.className = "search-form";
    const query = document.createElement("input");
    query.type = "search";
    query.value = this._config.default_query;
    query.placeholder = "Zoek films, series of artiesten";
    query.autocomplete = "off";
    const search = document.createElement("button");
    search.type = "button";
    search.textContent = "Zoeken";
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "secondary-button";
    clear.textContent = "Wissen";
    clear.addEventListener("click", () => {
      query.value = "";
      results.replaceChildren();
      status.textContent = "";
    });
    form.append(query, search, clear);
    content.appendChild(form);

    const options = document.createElement("div");
    options.className = "options";
    const searchAfter = document.createElement("label");
    searchAfter.className = "checkbox";
    const searchAfterInput = document.createElement("input");
    searchAfterInput.type = "checkbox";
    searchAfterInput.checked = Boolean(this._config.search_after_add);
    searchAfter.append(searchAfterInput, document.createTextNode("Zoeken na toevoegen"));
    options.appendChild(searchAfter);

    const monitoring = this._makeSelect("Monitoring", this._config.monitoring_modes, this._config.monitoring_mode);
    options.appendChild(monitoring.label);
    const root = this._makeSelect("Root folder", this._config.root_folder_options, this._config.root_folder);
    const quality = this._makeSelect("Quality profile", this._config.quality_profile_options, this._config.quality_profile);
    if (this._config.root_folder_options.length) options.appendChild(root.label);
    if (this._config.quality_profile_options.length) options.appendChild(quality.label);
    content.appendChild(options);

    const status = document.createElement("div");
    status.className = "status";
    content.appendChild(status);
    const results = document.createElement("div");
    results.className = "results";
    content.appendChild(results);

    const runSearch = async () => {
      const value = query.value.trim();
      if (!value) {
        status.textContent = "Vul een zoekterm in.";
        return;
      }
      if (!this._hass) {
        status.textContent = "Home Assistant is nog niet beschikbaar.";
        return;
      }
      search.disabled = true;
      status.textContent = "Zoeken...";
      try {
        const response = await this._lookup(value);
        this._application = response.application || "";
        application.textContent = this._config.hide_application_name
          ? "ARR Media Manager"
          : `ARR Media Manager | ${this._application || "verbinding actief"}`;
        this._results = Array.isArray(response.results) ? response.results : [];
        if (!this._results.length) status.textContent = "Geen resultaten gevonden.";
        else status.textContent = `${this._results.length} resultaat/resultaten gevonden.`;
        this._renderResults(results, status, searchAfterInput, monitoring.select, root.select, quality.select);
      } catch (error) {
        this._results = [];
        results.replaceChildren();
        status.textContent = this._readableError(error, "Zoeken mislukt.");
      } finally {
        search.disabled = false;
      }
    };

    search.addEventListener("click", runSearch);
    query.addEventListener("keydown", (event) => {
      if (event.key === "Enter") runSearch();
    });
    card.appendChild(content);
    this.appendChild(card);
    this._addStyles();
  }

  _renderResults(container, status, searchAfter, monitoring, root, quality) {
    container.replaceChildren();
    container.style.gridTemplateColumns = `repeat(${Math.max(1, Number(this._config.result_columns) || 1)}, minmax(0, 1fr))`;
    for (const result of this._results) {
      const item = document.createElement("article");
      item.className = this._config.compact ? "result compact" : "result";
      const posterUrl = this._safePosterUrl(result.poster_url);
      if (this._config.show_posters) {
        const poster = document.createElement("img");
        poster.src = posterUrl || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='92' viewBox='0 0 64 92'%3E%3Crect width='64' height='92' fill='%23666'/%3E%3C/svg%3E";
        poster.alt = result.title || "Poster";
        poster.loading = "lazy";
        poster.addEventListener("error", () => { poster.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='92' viewBox='0 0 64 92'%3E%3Crect width='64' height='92' fill='%23666'/%3E%3C/svg%3E"; });
        item.appendChild(poster);
      }
      const details = document.createElement("div");
      details.className = "result-details";
      const heading = document.createElement("h3");
      heading.textContent = result.title || "Onbekende titel";
      details.appendChild(heading);
      const metadata = document.createElement("div");
      metadata.className = "metadata";
      metadata.textContent = [result.year, result.media_type, this._config.show_existing ? (result.already_exists ? "Bestaat al" : "Nieuw") : null]
        .filter((value) => value != null && value !== "")
        .join(" | ");
      details.appendChild(metadata);
      if (this._config.show_overview && result.overview) {
        const overview = document.createElement("p");
        overview.className = "overview";
        overview.textContent = result.overview;
        details.appendChild(overview);
      }
      const add = document.createElement("button");
      add.type = "button";
      add.textContent = result.already_exists ? "Al aanwezig" : "Add";
      add.disabled = Boolean(result.already_exists);
      add.addEventListener("click", () => this._addResult(
        result,
        { searchAfter, monitoring, root, quality },
        add,
        status,
      ));
      details.appendChild(add);
      item.appendChild(details);
      container.appendChild(item);
    }
  }

  _safePosterUrl(value) {
    if (!value) return null;
    try {
      const url = new URL(value);
      if (url.protocol !== "https:" || url.username || url.password) return null;
      return url.toString();
    } catch (_) {
      return null;
    }
  }

  _readableError(error, fallback) {
    const message = String(error?.message || "");
    if (message.includes("not initialized") || message.includes("not available")) return "De ARR-koppeling is niet beschikbaar.";
    if (message.includes("required") || message.includes("empty")) return "Vul alle verplichte velden in.";
    if (message.includes("already") || message.includes("library")) return "Dit medium is al aanwezig.";
    return fallback;
  }

  _addStyles() {
    if (this._style) return;
    this._style = document.createElement("style");
    this._style.textContent = `
      ha-card { padding: 16px; }
      h2 { margin: 0 0 12px; font-size: 1.1rem; }
      .content, .search-form, .options { display: grid; gap: 10px; }
      .search-form { grid-template-columns: 1fr auto auto; }
      input, select, button { box-sizing: border-box; min-height: 40px; padding: 8px 10px; font: inherit; }
      input, select { width: 100%; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color); }
      button { cursor: pointer; border: 0; border-radius: 4px; padding-inline: 16px; background: var(--primary-color); color: var(--text-primary-color, white); }
      button:disabled { opacity: .6; cursor: wait; }
      .secondary-button { background: var(--secondary-background-color); color: var(--primary-text-color); }
      .application-status { color: var(--secondary-text-color); font-size: .85rem; }
      .checkbox { display: flex; gap: 8px; align-items: center; }
      .checkbox input { width: auto; min-height: auto; }
      .field { display: grid; gap: 4px; color: var(--secondary-text-color); font-size: .9rem; }
      .status { min-height: 1.3em; color: var(--secondary-text-color); }
      .results { display: grid; gap: 10px; }
      .result { display: grid; grid-template-columns: 64px 1fr; gap: 12px; padding: 10px 0; border-top: 1px solid var(--divider-color); }
      .result img { width: 64px; height: 92px; object-fit: cover; border-radius: 3px; background: var(--secondary-background-color); }
      .result-details { display: grid; align-content: start; gap: 6px; }
      h3 { margin: 0; font-size: 1rem; }
      .metadata { color: var(--secondary-text-color); font-size: .85rem; }
      .overview { margin: 0; color: var(--secondary-text-color); font-size: .9rem; }
      .result button { justify-self: start; min-height: 34px; }
      .result.compact { padding-block: 4px; }
      .result.compact img { height: 64px; }
      @media (max-width: 600px) { .results { grid-template-columns: 1fr !important; } }
      @media (max-width: 420px) { .search-form { grid-template-columns: 1fr; } }
    `;
    this.appendChild(this._style);
  }
}

class ArrMediaSearchCardEditor extends HTMLElement {
  set hass(hass) { this._hass = hass; }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    this.innerHTML = "";
    const selector = document.createElement("ha-selector");
    selector.hass = this._hass;
    selector.selector = { config_entry: { integration: "arr_media_manager" } };
    selector.value = this._config.config_entry_id || "";
    selector.addEventListener("value-changed", (event) => {
      this._config.config_entry_id = event.detail.value;
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
    });
    this.appendChild(selector);

    for (const field of ["title", "max_results"]) {
      const input = document.createElement("input");
      input.value = this._config[field] || "";
      input.placeholder = field;
      input.addEventListener("change", (event) => {
        this._config[field] = field === "max_results" ? Number(event.target.value) : event.target.value;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      this.appendChild(input);
    }
    for (const field of ["search_after_add", "show_overview", "show_posters", "show_existing", "confirm_before_add", "compact"]) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = Boolean(this._config[field]);
      input.addEventListener("change", (event) => {
        this._config[field] = event.target.checked;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      label.append(input, document.createTextNode(field));
      this.appendChild(label);
    }
  }
}

if (!customElements.get("arr-media-search-card")) customElements.define("arr-media-search-card", ArrMediaSearchCard);
if (!customElements.get("arr-media-search-card-editor")) customElements.define("arr-media-search-card-editor", ArrMediaSearchCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "arr-media-search-card")) {
  window.customCards.push({
    type: "arr-media-search-card",
    name: "ARR Media Search",
    description: "Search an ARR app, review results, and add a selected result.",
    preview: true,
  });
}
