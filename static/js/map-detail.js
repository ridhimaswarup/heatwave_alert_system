// static/js/map-detail.js - shows the selected state's details beside the zoomed map
(function () {
  var host = document.getElementById('hsm'), list = document.getElementById('hsm-list'), box = document.getElementById('hsm-detail');
  if (!host || !list || !box) return;
  var SEV = { LOW: '#e9c46a', MODERATE: '#f2a65a', HIGH: '#e4694f', SEVERE: '#b44a6c' };
  var ALERT = { YELLOW: '#e9c46a', ORANGE: '#f2a65a', RED: '#e4694f' };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function cap(s) { s = String(s || ''); return s.charAt(0) + s.slice(1).toLowerCase(); }
  function num(v, d) { return v == null ? '–' : Number(v).toFixed(d); }

  function region(p) {
    var sc = SEV[p.severity] || '#6b7f77', ac = ALERT[p.alert] || '#6b7f77';
    return '<div class="hsm-reg">' +
      '<div class="hsm-reg-top"><b>' + esc(p.name) + '</b><span class="hsm-badge" style="background:' + sc + '">' + esc(cap(p.severity) || 'No level') + '</span></div>' +
      '<div class="hsm-facts">' +
        '<div><small>Forecast max (' + esc(p.fdate) + ')</small><strong>' + num(p.temp, 1) + ' °C</strong></div>' +
        '<div><small>Latest reading</small><strong>' + num(p.obs_temp, 1) + ' °C</strong></div>' +
        '<div><small>Humidity</small><strong>' + num(p.obs_hum, 0) + '%</strong></div>' +
        '<div><small>Climate zone</small><strong>' + esc(p.climate || '–') + '</strong></div>' +
        '<div><small>Station</small><strong>' + esc(p.station) + '</strong></div>' +
        '<div><small>Status</small><strong>' + esc(p.status || '–') + '</strong></div>' +
      '</div>' +
      (p.alert
        ? '<div class="hsm-adv" style="border-color:' + ac + ';background:color-mix(in srgb,' + ac + ' 16%,#fff)"><b>' + esc(cap(p.alert)) + ' advisory · ' + (p.notified || 0) + ' stakeholder' + (p.notified === 1 ? '' : 's') + ' notified</b>' + esc(p.message) + '</div>'
        : '<div class="hsm-adv" style="border-color:#d3dfd7;background:#f8faf6"><b>No advisory issued</b>for the latest forecast.</div>') +
      '<a class="hsm-link" href="' + esc(p.region_url) + '">Open region →</a>' +
      (p.adv_url ? '<a class="hsm-link" href="' + esc(p.adv_url) + '">Open advisory →</a>' : '') +
    '</div>';
  }

  host.addEventListener('hsm:select', function (e) {
    var d = e.detail;
    if (!d) { box.hidden = true; list.hidden = false; return; }
    var pts = d.points.slice().sort(function (a, b) { return b.temp - a.temp; });
    var top = pts[0];
    box.innerHTML = '<button type="button" class="hsm-back">← Hottest regions</button>' +
      '<div class="hsm-eyebrow">Selected state</div><h3 class="hsm-state">' + esc(d.label) + '</h3>' +
      (top
        ? '<div class="hsm-top"><span class="hsm-bignum">' + top.temp.toFixed(1) + '°C</span><span class="hsm-badge" style="background:' + (SEV[top.severity] || '#6b7f77') + '">' + esc(cap(top.severity)) + '</span></div>' + pts.map(region).join('')
        : '<p class="hsm-empty">No forecast data for this state yet.</p>');
    box.querySelector('.hsm-back').onclick = function () { host.querySelector('.hsm-reset').click(); };
    list.hidden = true; box.hidden = false; box.scrollTop = 0;
  });
})();