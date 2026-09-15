class ArrMediaManagerCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.config_entry_id) {
      throw new Error("config_entry_id is required");
    }
    this._config = {
      title: "ARR Media Manager",
      search_after_add: true,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  getCardSize() {
    return 2;
  }

  _render() {
    if (!this._config) {
      return;
    }

    this.innerHTML = "";
    const card = document.createElement("ha-card");
    const content = document.createElement("div");
    content.className = "content";

    const title = document.createElement("h2");
    title.textContent = this._config.title;
    content.appendChild(title);

    const query = document.createElement("input");
    query.className = "query";
    query.type = "search";
    query.placeholder = "Zoekterm";
    query.autocomplete = "off";
    content.appendChild(query);

    const button = document.createElement("button");
    button.className = "search-button";
    button.type = "button";
    button.textContent = "Zoek en download";
    content.appendChild(button);

    const status = document.createElement("div");
    status.className = "status";
    content.appendChild(status);

    const submit = async () => {
      const value = query.value.trim();
      if (!value) {
        status.textContent = "Vul een zoekterm in.";
        return;
      }
      if (!this._hass) {
        status.textContent = "Home Assistant is nog niet beschikbaar.";
        return;
      }

      button.disabled = true;
      status.textContent = "Zoeken...";
      try {
        await this._hass.callService("arr_media_manager", "search_and_add", {
          config_entry_id: this._config.config_entry_id,
          query: value,
          search_after_add: Boolean(this._config.search_after_add),
          exact_match: Boolean(this._config.exact_match ?? false),
          ...(this._config.year ? { year: Number(this._config.year) } : {}),
        });
        status.textContent = "Toegevoegd. Download gestart.";
        query.value = "";
      } catch (error) {
        status.textContent = `Fout: ${error.message || error}`;
      } finally {
        button.disabled = false;
      }
    };

    button.addEventListener("click", submit);
    query.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        submit();
      }
    });

    card.appendChild(content);
    this.appendChild(card);
    this._addStyles();
  }

  _addStyles() {
    if (this._style) {
      return;
    }
    this._style = document.createElement("style");
    this._style.textContent = `
      ha-card { padding: 16px; }
      h2 { margin: 0 0 12px; font-size: 1.1rem; }
      .content { display: grid; gap: 10px; }
      select, input, button {
        box-sizing: border-box;
        width: 100%;
        min-height: 40px;
        padding: 8px 10px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font: inherit;
      }
      button {
        cursor: pointer;
        background: var(--primary-color);
        color: var(--text-primary-color, white);
        border: 0;
      }
      button:disabled { opacity: 0.6; cursor: wait; }
      .status { min-height: 1.3em; color: var(--secondary-text-color); }
    `;
    this.appendChild(this._style);
  }
}

customElements.define("arr-media-manager-card", ArrMediaManagerCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "arr-media-manager-card",
  name: "ARR Media Manager Search",
  description: "Search an ARR app and start the download workflow.",
});
