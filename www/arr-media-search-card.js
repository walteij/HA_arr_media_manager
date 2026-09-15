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
    this._config = {
      title: "ARR Media Search",
      max_results: 10,
      search_after_add: true,
      monitoring_mode: "all",
      monitoring_modes: ["all", "future", "missing", "existing", "first", "latest", "none"],
      root_folder_options: [],
      quality_profile_options: [],
      ...config,
    };
    this._results = [];
    this._status = "";
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  getCardSize() {
    return 4;
  }

  async _lookup(query) {
    const serviceData = {
      config_entry_id: this._config.config_entry_id,
      query,
      max_results: Number(this._config.max_results),
    };
    const response = await this._hass.callService(
      "arr_media_manager",
      "lookup",
      serviceData,
      {},
      false,
      true,
    );
    return response?.response || response || { count: 0, results: [] };
  }

  async _addResult(result, controls, button, status) {
    if (result.id == null) {
      status.textContent = "Dit resultaat heeft geen lookup_id.";
      return;
    }
    button.disabled = true;
    status.textContent = "Toevoegen...";
    const data = {
      config_entry_id: this._config.config_entry_id,
      lookup_id: result.id,
      title: result.title || String(result.id),
      search_after_add: controls.searchAfter.checked,
    };
    if (result.year != null) data.year = Number(result.year);
    if (result.foreign_id) data.foreign_id = result.foreign_id;
    if (result.media_type) data.media_type = result.media_type;
    if (controls.monitoring.value) data.monitoring_mode = controls.monitoring.value;
    if (controls.root.value) data.root_folder = controls.root.value;
    if (controls.quality.value) data.quality_profile = controls.quality.value;

    try {
      await this._hass.callService("arr_media_manager", "add_media", data);
      status.textContent = "Toegevoegd" + (data.search_after_add ? ". Zoekopdracht gestart." : ".");
    } catch (error) {
      status.textContent = `Fout: ${error.message || error}`;
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

    const form = document.createElement("div");
    form.className = "search-form";
    const query = document.createElement("input");
    query.type = "search";
    query.placeholder = "Zoek films, series of artiesten";
    query.autocomplete = "off";
    const search = document.createElement("button");
    search.type = "button";
    search.textContent = "Zoeken";
    form.append(query, search);
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
        this._results = Array.isArray(response.results) ? response.results : [];
        status.textContent = `${this._results.length} resultaat/resultaten gevonden.`;
        this._renderResults(results, status, searchAfterInput, monitoring.select, root.select, quality.select);
      } catch (error) {
        this._results = [];
        results.replaceChildren();
        status.textContent = `Fout: ${error.message || error}`;
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
    for (const result of this._results) {
      const item = document.createElement("article");
      item.className = "result";
      if (result.poster_url) {
        const poster = document.createElement("img");
        poster.src = result.poster_url;
        poster.alt = result.title || "Poster";
        poster.loading = "lazy";
        item.appendChild(poster);
      }
      const details = document.createElement("div");
      details.className = "result-details";
      const heading = document.createElement("h3");
      heading.textContent = result.title || "Onbekende titel";
      details.appendChild(heading);
      const metadata = document.createElement("div");
      metadata.className = "metadata";
      metadata.textContent = [result.year, result.media_type, result.existing ? "Bestaat al" : "Nieuw"]
        .filter((value) => value != null && value !== "")
        .join(" | ");
      details.appendChild(metadata);
      const add = document.createElement("button");
      add.type = "button";
      add.textContent = "Add";
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

  _addStyles() {
    if (this._style) return;
    this._style = document.createElement("style");
    this._style.textContent = `
      ha-card { padding: 16px; }
      h2 { margin: 0 0 12px; font-size: 1.1rem; }
      .content, .search-form, .options { display: grid; gap: 10px; }
      .search-form { grid-template-columns: 1fr auto; }
      input, select, button { box-sizing: border-box; min-height: 40px; padding: 8px 10px; font: inherit; }
      input, select { width: 100%; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color); }
      button { cursor: pointer; border: 0; border-radius: 4px; padding-inline: 16px; background: var(--primary-color); color: var(--text-primary-color, white); }
      button:disabled { opacity: .6; cursor: wait; }
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
      .result button { justify-self: start; min-height: 34px; }
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
  }
}

customElements.define("arr-media-search-card", ArrMediaSearchCard);
customElements.define("arr-media-search-card-editor", ArrMediaSearchCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "arr-media-search-card",
  name: "ARR Media Search",
  description: "Search an ARR app, review results, and add a selected result.",
  preview: true,
});
