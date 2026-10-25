// Dindshenchas map. Plain JS, no build step; Leaflet is the only library.
// All text from data files is inserted with textContent, never as HTML.
(function () {
  "use strict";

  var IRELAND = [[51.35, -10.7], [55.45, -5.35]];
  // Map symbols follow print cartography: a solid dot for a certain identification,
  // an open ring for a probable one; red marks the place being read.
  var INK = "#1c1b19", RUBRIC = "#a51d1d", AREA = "#2f6f8f";
  var WATER_KINDS = ["lake", "river", "harbour", "estuary", "waterfall"];

  // Interface strings. Place names and the dindshenchas texts come from the data.
  var STRINGS = {
    en: {
      title: "Dindshenchas Map",
      tagline: "Ireland's place lore",
      about: "About",
      switchTo: "Gaeilge",
      mapLabel: "Map of Ireland with dindshenchas places",
      places: "Places",
      choose: "Choose a marker on the map, or a name below.",
      unlocated: "Not yet located",
      unlocatedHint: "Places whose modern location is disputed or unknown.",
      legendCertain: "Identification certain",
      legendProbable: "Probable",
      legendArea: "Extent of a lake, river or range",
      legendApprox: "Approximate extent",
      back: "← All places",
      textLanguage: "Language of the text",
      tabEnglish: "English",
      tabIrish: "Old Irish",
      ocrNote: "Text transcribed by machine from scans of the printed editions and not yet proofread. " +
        "Follow the scan links to check readings.",
      close: "Close",
      satellite: "Satellite",
      terrain: "Terrain",
      areas: "Shaded areas",
      zoomIn: "Zoom in",
      zoomOut: "Zoom out",
      notLocated: "Location not yet identified",
      probable: "identification probable",
      approximate: "marker approximate",
      county: function (e) { return e.county ? "Co. " + e.county : null; },
      altName: function (e) { return e.name_en; },
      note: function (e) { return e.note; },
      poem: "Poem: ",
      prose: "Prose: ",
      proseTitle: function (n, title) { return "Rennes Dindshenchas no. " + n + ": " + title; },
      pages: function (p) { return p.length > 1 ? "pp. " + p[0] + "–" + p[1] : "p. " + p[0]; },
      viewScan: "View scan",
      sources: "Sources",
      photoCredit: "Photo credit",
      incomplete: function (ga, en) {
        return "The scan's text recognition is incomplete for this poem: " + ga +
          " Irish lines but " + en + " English lines were recovered.";
      },
      noIrish: "The Irish text of this section could not be recovered from the scan.",
      noEnglish: "The translation of this section could not be recovered from the scan.",
      stokesNotes: "Stokes’s notes",
      today: "Today",
      historical: "Historical photo",
      via: ", via ",
      logainm: "https://www.logainm.ie/en/"
    },
    ga: {
      title: "Léarscáil an Dindshenchais",
      tagline: "Seanchas áiteanna na hÉireann",
      about: "Eolas",
      switchTo: "English",
      mapLabel: "Léarscáil d’Éirinn le háiteanna an dindshenchais",
      places: "Áiteanna",
      choose: "Roghnaigh marcóir ar an léarscáil, nó ainm thíos.",
      unlocated: "Gan aimsiú fós",
      unlocatedHint: "Áiteanna a bhfuil a suíomh inniu faoi dhíospóid nó anaithnid.",
      legendCertain: "Aithint chinnte",
      legendProbable: "Dóchúil",
      legendArea: "Fairsinge locha, abhann nó sléibhte",
      legendApprox: "Fairsinge neasach",
      back: "← Gach áit",
      textLanguage: "Teanga an téacs",
      tabEnglish: "Béarla",
      tabIrish: "Sean-Ghaeilge",
      ocrNote: "Rinne meaisín an téacs seo a thras-scríobh ó scananna de na heagráin chlóite, " +
        "agus níl sé profléite fós. Lean na naisc chuig na scananna chun na léamha a sheiceáil.",
      close: "Dún",
      satellite: "Satailít",
      terrain: "Tír-raon",
      areas: "Limistéir scáthaithe",
      zoomIn: "Zúmáil isteach",
      zoomOut: "Zúmáil amach",
      notLocated: "Níor aimsíodh an suíomh fós",
      probable: "aithint dhóchúil",
      approximate: "marcóir neasach",
      county: function (e) { return e.county_ga; },
      altName: function (e) { return e.name_ga || e.name_en; },
      note: function (e) { return e.note_ga || e.note; },
      poem: "Dán: ",
      prose: "Prós: ",
      proseTitle: function (n, title) { return "Dindshenchas Rennes, uimh. " + n + ": " + title; },
      pages: function (p) { return p.length > 1 ? "lgh. " + p[0] + "–" + p[1] : "lch. " + p[0]; },
      viewScan: "Féach ar an scanadh",
      sources: "Foinsí",
      photoCredit: "Creidiúint an ghrianghraif",
      incomplete: function (ga, en) {
        return "Tá aithint téacs an scanta neamhiomlán don dán seo: aisghabhadh " + ga +
          " líne Ghaeilge ach " + en + " líne Bhéarla.";
      },
      noIrish: "Níorbh fhéidir téacs Gaeilge na coda seo a aisghabháil ón scanadh.",
      noEnglish: "Níorbh fhéidir aistriúchán na coda seo a aisghabháil ón scanadh.",
      stokesNotes: "Nótaí Stokes",
      today: "Inniu",
      historical: "Grianghraf stairiúil",
      via: ", trí ",
      logainm: "https://www.logainm.ie/ga/"
    }
  };

  var ui = initialUiLang();
  var t = STRINGS[ui];
  var lang = readPref("lang") || "en";
  var entryCache = {};
  var markers = {};
  var places = [];
  var current = null;

  // ---------- map ----------

  var map = L.map("map", {
    // Whole zoom levels only: fractional zooms leave hairline seams between tiles
    zoomSnap: 1,
    minZoom: 6,
    maxZoom: 16,
    maxBounds: L.latLngBounds([[50.9, -11.8], [56.0, -4.4]]),  // Ireland with a margin
    maxBoundsViscosity: 0.8,
    attributionControl: false,
    zoomControl: false
  });
  L.control.attribution({ prefix: '<a href="https://leafletjs.com">Leaflet</a>' }).addTo(map);
  map.fitBounds(IRELAND);

  // Offline fallback: a plain outline of the island, drawn under the tiles so the
  // map still works if the imagery provider is unavailable.
  map.createPane("fallback");
  map.getPane("fallback").style.zIndex = 150;

  var satellite = L.tileLayer(
    "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg",
    {
      maxNativeZoom: 15,
      maxZoom: 16,
      attribution: '<a href="https://cloudless.eox.at">EOxCloudless 2024</a> by EOX IT Services GmbH ' +
        "(contains modified Copernicus Sentinel data 2024)"
    }
  );
  var terrain = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    subdomains: "abc",
    maxNativeZoom: 17,
    maxZoom: 16,
    attribution: 'Map: © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA), ' +
      'data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  });
  (readPref("base") === "terrain" ? terrain : satellite).addTo(map);
  map.on("baselayerchange", function (e) {
    writePref("base", e.layer === terrain ? "terrain" : "satellite");
  });

  // Rebuilt when the interface language changes, since Leaflet bakes in labels
  var zoomControl = null;
  var layersControl = null;
  function mapControls() {
    if (zoomControl) zoomControl.remove();
    if (layersControl) layersControl.remove();
    zoomControl = L.control.zoom({ zoomInTitle: t.zoomIn, zoomOutTitle: t.zoomOut }).addTo(map);
    var layers = {};
    layers[t.satellite] = satellite;
    layers[t.terrain] = terrain;
    var overlays = {};
    overlays[t.areas] = areasGroup;
    layersControl = L.control.layers(layers, overlays, { position: "topright" }).addTo(map);
  }

  // Drawn only once tiles start failing, so it never shows through tile seams.
  var fallbackShown = false;
  function showFallback() {
    if (fallbackShown) return;
    fallbackShown = true;
    map.getContainer().classList.add("fallback");
    fetchJSON("data/ireland.geojson").then(function (geo) {
      // Fill only, no outline, so the modern border between the two parts never shows
      L.geoJSON(geo, {
        pane: "fallback",
        interactive: false,
        style: { stroke: false, fillColor: "#e7e0cf", fillOpacity: 1 }
      }).addTo(map);
    });
  }
  satellite.on("tileerror", showFallback);
  terrain.on("tileerror", showFallback);

  // ---------- labels ----------

  // Place each label to the right of its marker, or to the left if that
  // collides with a label already placed or another marker; failing both, hide
  // it until hovered. Places with more text, and the selected place, go first.
  var LABEL_SIDES = { right: [9, 0], left: [-9, 0] };

  function layoutLabels() {
    var box = map.getContainer().getBoundingClientRect();
    var ids = Object.keys(markers);
    var dots = ids.map(function (id) {
      var p = map.latLngToContainerPoint(markers[id].getLatLng());
      return { id: id, left: p.x - 9, right: p.x + 9, top: p.y - 9, bottom: p.y + 9 };
    });
    var placed = [];
    ids.sort(function (a, b) { return labelPriority(b) - labelPriority(a); });
    ids.forEach(function (id) {
      var tip = markers[id].getTooltip();
      var node = tip.getElement();
      if (!node) return;
      node.classList.remove("label-hidden");
      var ok = Object.keys(LABEL_SIDES).some(function (side) {
        tip.options.direction = side;
        tip.options.offset = LABEL_SIDES[side];
        tip.update();
        var r = node.getBoundingClientRect();
        var rect = { left: r.left - box.left, right: r.right - box.left, top: r.top - box.top, bottom: r.bottom - box.top };
        var hit = placed.some(function (q) { return overlaps(rect, q); }) ||
          dots.some(function (d) { return d.id !== id && overlaps(rect, d); });
        if (!hit) placed.push(rect);
        return !hit;
      });
      if (!ok) node.classList.add("label-hidden");
    });
  }

  function labelPriority(id) {
    if (current && current.id === id) return 1000;
    var f = places.find(function (p) { return p.id === id; });
    return f ? f.properties.prose + f.properties.verse : 0;
  }

  function overlaps(a, b) {
    return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
  }

  map.on("zoomend", layoutLabels);
  window.addEventListener("resize", layoutLabels);

  // ---------- places ----------

  fetchJSON("data/places.geojson").then(function (geo) {
    places = geo.features;
    places.forEach(function (f) {
      if (!f.geometry) return;
      var c = f.geometry.coordinates;
      var m = L.circleMarker([c[1], c[0]], markerStyle(f, false)).addTo(map);
      m.bindTooltip(f.properties.name_mir, {
        permanent: true,
        interactive: true,
        direction: "right",
        offset: LABEL_SIDES.right,
        // Water features are lettered in italic, as on Ordnance Survey maps
        className: "place-label" + (WATER_KINDS.indexOf(f.properties.kind) >= 0 ? " water" : "")
      });
      m.on("click", function () { go(f.id); });
      // The label opens the place too, and shows itself on hover if it was hidden
      var label = m.getTooltip().getElement();
      L.DomEvent.on(label, "click", function (ev) {
        L.DomEvent.stop(ev);
        go(f.id);
      });
      m.on("mouseover", function () { label.classList.add("label-hover"); });
      m.on("mouseout", function () { label.classList.remove("label-hover"); });
      markers[f.id] = m;
    });
    renderLists();
    layoutLabels();
    route();
    loadAreas();
  });

  // ---------- area shapes (lakes, rivers, mountain ranges, plains) ----------

  // Drawn beneath the markers; the marker stays as the label and click target,
  // and the shape is clickable too. Built by tools/make_areas.py.
  map.createPane("areas");
  map.getPane("areas").style.zIndex = 380;  // above tiles, below markers
  var areaRenderer = L.svg({ pane: "areas" });
  var areas = {};
  // All shapes in one group, so the layers menu can switch them off; the choice is remembered
  var areasGroup = L.layerGroup();
  if (readPref("areas") !== "off") areasGroup.addTo(map);
  map.on("overlayadd overlayremove", function (e) {
    if (e.layer === areasGroup) writePref("areas", e.type === "overlayadd" ? "on" : "off");
  });

  function loadAreas() {
    fetchJSON("data/areas.geojson").then(function (geo) {
      geo.features.forEach(function (f) {
        if (!markers[f.id]) return;
        var layer = L.geoJSON(f, { renderer: areaRenderer, style: areaStyle(f, false) }).addTo(areasGroup);
        var label = markers[f.id].getTooltip().getElement();
        layer.on("click", function () { go(f.id); });
        layer.on("mouseover", function () { label.classList.add("label-hover"); });
        layer.on("mouseout", function () { label.classList.remove("label-hover"); });
        areas[f.id] = { layer: layer, feature: f };
      });
      if (current) highlight(current.id);
    });
  }

  function markerStyle(f, selected) {
    var probable = f.properties.confidence === "probable";
    return {
      radius: selected ? 8 : probable ? 5 : 5.5,
      color: probable ? INK : "#fff",
      weight: probable ? 2 : 1.25,  // a thin white edge keeps solid dots visible on dark imagery
      fillColor: selected ? RUBRIC : probable ? "#fff" : INK,
      fillOpacity: 1
    };
  }

  function areaStyle(f, selected) {
    var color = selected ? RUBRIC : AREA;
    if (f.properties.kind === "river") {
      return { color: color, weight: selected ? 5 : 4, opacity: selected ? 0.7 : 0.5, lineCap: "round" };
    }
    return {
      color: color,
      weight: selected ? 2 : 1.5,
      opacity: 0.9,
      fillColor: color,
      fillOpacity: selected ? 0.2 : 0.18,
      // A dashed edge marks an approximate extent, such as a plain with no fixed boundary
      dashArray: f.properties.approximate ? "6 5" : null
    };
  }

  function renderLists() {
    var located = document.getElementById("place-list");
    var unlocated = document.getElementById("unlocated-list");
    located.replaceChildren();
    unlocated.replaceChildren();
    var sorted = places.slice().sort(function (a, b) {
      return a.properties.name_mir.localeCompare(b.properties.name_mir, "ga");
    });
    sorted.forEach(function (f) {
      var li = el("li");
      var btn = el("button");
      btn.appendChild(el("span", f.properties.name_mir));
      btn.type = "button";
      var alt = t.altName(f.properties);
      if (alt) btn.appendChild(el("small", alt));
      btn.addEventListener("click", function () { go(f.id); });
      li.appendChild(btn);
      (f.geometry ? located : unlocated).appendChild(li);
    });
  }

  // ---------- routing (#place-id) ----------

  function go(id) {
    if (location.hash === "#" + id) route();
    else location.hash = id;
  }

  window.addEventListener("hashchange", route);

  function route() {
    var id = decodeURIComponent(location.hash.slice(1));
    if (!id) return showHome();
    var f = places.find(function (p) { return p.id === id; });
    if (!f) return showHome();
    if (f.geometry) {
      var c = f.geometry.coordinates;
      var zoom = Math.max(map.getZoom(), 9);
      // Leaflet's fly animation fails on a map with no size (e.g. in a hidden tab)
      if (map.getSize().x) map.flyTo([c[1], c[0]], zoom, { duration: 0.8 });
      else map.setView([c[1], c[0]], zoom);
    }
    loadEntry(id).then(renderEntry, function () {
      showHome();
    });
  }

  function loadEntry(id) {
    if (!entryCache[id]) {
      entryCache[id] = fetchJSON("data/entries/" + encodeURIComponent(id) + ".json");
    }
    return entryCache[id];
  }

  function showHome() {
    current = null;
    document.getElementById("panel-home").hidden = false;
    document.getElementById("entry").hidden = true;
    highlight(null);
  }

  // ---------- entry panel ----------

  function renderEntry(e) {
    current = e;
    highlight(e.id);
    document.getElementById("panel-home").hidden = true;
    var art = document.getElementById("entry");
    art.hidden = false;

    renderEntryText();
    document.getElementById("panel").scrollTop = 0;
    if (window.matchMedia("(max-width: 760px)").matches) {
      art.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // Everything in the entry that depends on the interface language
  function renderEntryText() {
    var e = current;
    text("entry-title", e.name_mir);
    var sub = [t.altName(e), t.county(e)].filter(Boolean).join(", ");
    if (e.confidence === "unlocated") sub = t.notLocated;
    else if (e.confidence === "probable") sub += "; " + t.probable;
    if (e.precision === "approximate") sub += "; " + t.approximate;
    text("entry-subtitle", sub);

    var note = document.getElementById("entry-note");
    note.hidden = !t.note(e);
    note.textContent = t.note(e) || "";

    renderImages(e.images || []);
    renderSections();
    renderSources();
    renderLinks(e);
  }

  function renderImages(images) {
    var box = document.getElementById("entry-figures");
    box.replaceChildren();
    images.forEach(function (img, n) {
      var fig = el("figure");
      var tag = el("img");
      tag.src = img.file;
      tag.alt = img.caption || current.name_en || current.name_mir;
      tag.loading = "lazy";
      fig.appendChild(tag);
      if (img.era === "historical") {
        var badge = el("span", t.historical);
        badge.className = "era";
        fig.appendChild(badge);
      }

      // Credit sits behind a small (i) button: shown on hover, or toggled by tap
      var credit = el("figcaption", (img.era === "historical" ? t.historical : t.today) +
        (img.date ? " (" + img.date + ")" : "") + ": " + img.author + ", ");
      credit.id = "credit-" + n;
      credit.appendChild(link(img.licence, img.licence_url || img.source_url));
      credit.appendChild(document.createTextNode(t.via));
      credit.appendChild(link("Wikimedia Commons", img.source_url));
      var btn = el("button", "i");
      btn.type = "button";
      btn.className = "credit-btn";
      btn.setAttribute("aria-label", t.photoCredit);
      btn.setAttribute("aria-expanded", "false");
      btn.setAttribute("aria-controls", credit.id);
      btn.addEventListener("click", function () {
        var open = fig.classList.toggle("credit-open");
        btn.setAttribute("aria-expanded", String(open));
      });
      fig.appendChild(btn);
      fig.appendChild(credit);
      box.appendChild(fig);
    });
  }

  function renderSections() {
    var box = document.getElementById("entry-sections");
    box.replaceChildren();
    current.sections.forEach(function (s) {
      var sec = el("section");
      sec.className = "section";
      sec.appendChild(el("h3", sectionTitle(s)));

      var body = s[lang] || [];
      if (!body.length) {
        sec.appendChild(el("p", lang === "ga" ? t.noIrish : t.noEnglish));
      } else if (s.type === "verse") {
        body.forEach(function (stanza) {
          var p = el("p");
          p.className = "stanza";
          stanza.forEach(function (line) { p.appendChild(el("span", line)); });
          sec.appendChild(p);
        });
      } else {
        var div = el("div");
        div.className = "prose";
        body.forEach(function (para) { div.appendChild(el("p", para)); });
        sec.appendChild(div);
      }

      if (lang === "en" && s.notes && s.notes.length) {
        var d = el("details");
        d.appendChild(el("summary", t.stokesNotes));
        s.notes.forEach(function (n) { d.appendChild(el("p", n)); });
        sec.appendChild(d);
      }
      box.appendChild(sec);
    });
  }

  function sectionTitle(s) {
    return s.type === "verse" ? t.poem + s.title : t.prose + t.proseTitle(s.number, s.title);
  }

  // Citations, scan links and OCR caveats go last, so the text comes first
  function renderSources() {
    var list = document.getElementById("sources-list");
    list.replaceChildren();
    current.sections.forEach(function (s) {
      var li = el("li");
      li.appendChild(el("strong", sectionTitle(s)));
      li.appendChild(document.createTextNode(". " + s.citation +
        (s.pages ? ", " + t.pages(s.pages) : "") + ". "));
      li.appendChild(link(t.viewScan, s.scan));
      if (s.incomplete) {
        var w = el("span", " " + t.incomplete(s.incomplete[0], s.incomplete[1]));
        w.className = "warning";
        li.appendChild(w);
      }
      list.appendChild(li);
    });
  }

  function renderLinks(e) {
    var p = document.getElementById("entry-links");
    p.replaceChildren();
    var parts = [];
    // The Irish-language Wikipedia (Vicipéid) in Irish mode where it has an article
    if (ui === "ga" && e.wikipedia_ga) parts.push(link("Vicipéid", wikiUrl("ga", e.wikipedia_ga)));
    else if (e.wikipedia) parts.push(link("Wikipedia", wikiUrl("en", e.wikipedia)));
    if (e.logainm) parts.push(link("Logainm.ie", t.logainm + encodeURIComponent(e.logainm)));
    p.hidden = !parts.length;
    parts.forEach(function (a, i) {
      if (i) p.appendChild(document.createTextNode(", "));
      p.appendChild(a);
    });
  }

  function placeById(id) {
    return places.find(function (p) { return p.id === id; });
  }

  function wikiUrl(lang, title) {
    return "https://" + lang + ".wikipedia.org/wiki/" + encodeURIComponent(title.replace(/ /g, "_"));
  }

  function highlight(id) {
    Object.keys(markers).forEach(function (k) {
      markers[k].setStyle(markerStyle(placeById(k), k === id));
      if (k === id) markers[k].bringToFront();
    });
    Object.keys(areas).forEach(function (k) {
      areas[k].layer.setStyle(areaStyle(areas[k].feature, k === id));
    });
    layoutLabels();  // the selected place's label takes priority
  }

  // ---------- language tabs ----------

  document.querySelectorAll(".tabs button").forEach(function (b) {
    b.addEventListener("click", function () { setLang(b.dataset.lang); });
  });
  setLang(lang);

  function setLang(l) {
    lang = l;
    writePref("lang", l);
    document.querySelectorAll(".tabs button").forEach(function (b) {
      b.setAttribute("aria-selected", String(b.dataset.lang === l));
    });
    document.getElementById("entry-sections").lang = l === "ga" ? "mga" : "en";
    if (current) renderSections();
  }

  // ---------- interface language (English / Gaeilge) ----------

  function initialUiLang() {
    var param = new URLSearchParams(location.search).get("lang");
    if (param === "ga" || param === "en") return param;
    var saved = readPref("ui");
    if (saved === "ga" || saved === "en") return saved;
    var langs = navigator.languages || [navigator.language || ""];
    return langs.some(function (l) { return /^ga\b/i.test(l); }) ? "ga" : "en";
  }

  function setUiLang(l) {
    ui = l;
    t = STRINGS[l];
    writePref("ui", l);
    document.documentElement.lang = l;
    document.title = t.title;
    document.querySelectorAll("[data-i18n]").forEach(function (n) {
      n.textContent = t[n.dataset.i18n];
    });
    document.querySelectorAll("[data-i18n-aria]").forEach(function (n) {
      n.setAttribute("aria-label", t[n.dataset.i18nAria]);
    });
    document.querySelectorAll("[data-ui-lang]").forEach(function (n) {
      n.hidden = n.dataset.uiLang !== l;
    });
    var btn = document.getElementById("ui-lang-btn");
    btn.textContent = t.switchTo;
    btn.lang = l === "ga" ? "en" : "ga";
    // Keep a shared ?lang= link in step with the choice
    var url = new URL(location.href);
    if (url.searchParams.has("lang")) {
      url.searchParams.set("lang", l);
      history.replaceState(null, "", url);
    }
    mapControls();
    if (places.length) renderLists();
    if (current) renderEntryText();
  }

  document.getElementById("ui-lang-btn").addEventListener("click", function () {
    setUiLang(ui === "ga" ? "en" : "ga");
  });
  setUiLang(ui);

  // ---------- misc UI ----------

  document.getElementById("back-btn").addEventListener("click", function () {
    history.pushState(null, "", location.pathname + location.search);
    showHome();
    map.flyToBounds(IRELAND, { duration: 0.8 });
  });
  document.getElementById("about-btn").addEventListener("click", function () {
    document.getElementById("about").showModal();
  });

  // ---------- helpers ----------

  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ": " + r.status);
      return r.json();
    });
  }

  function el(tag, content) {
    var node = document.createElement(tag);
    if (content != null) node.textContent = content;
    return node;
  }

  function text(id, value) {
    document.getElementById(id).textContent = value || "";
  }

  function link(label, href) {
    var a = el("a", label);
    // Only allow http(s) links from data files
    if (/^https?:\/\//.test(href || "")) {
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener";
    }
    return a;
  }

  function readPref(key) {
    try { return localStorage.getItem("dindshenchas." + key); } catch (e) { return null; }
  }

  function writePref(key, value) {
    try { localStorage.setItem("dindshenchas." + key, value); } catch (e) { /* private mode */ }
  }
})();
