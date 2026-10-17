// static/js/india-map.js - Heat Severity Map (schematic state shapes, click to zoom)
(function () {
  var host = document.getElementById('hsm'), dataEl = document.getElementById('map-data');
  if (!host || !dataEl) return;
  var pts = JSON.parse(dataEl.textContent || '[]').sort(function (a, b) { return b.temp - a.temp; });

  // [id, label, state names in your database (| separated), polygon as lon,lat,lon,lat...]
  var ST = [
    ['jk','Jammu & Kashmir','Jammu and Kashmir|Ladakh',[74.3,37,76.8,35.7,78.5,35.5,79.5,34,78.8,32.5,76.8,32.7,75.3,32.9,74.8,32.5,74.2,34]],
    ['hm','Himachal & Uttarakhand','Himachal Pradesh|Uttarakhand',[76.8,32.7,78.8,32.5,79,31,80.2,30.4,81,30.2,80.1,28.8,79,29.2,77.6,30.2,77,30.6,76.6,31.3]],
    ['pb','Punjab & Haryana','Punjab|Haryana',[74.6,31,74.8,32.5,75.3,32.9,76.8,32.7,76.6,31.3,77,30.6,77.6,30.2,77.4,28.7,76.9,28.4,76.2,28.4,75.2,29.6,74,29.8]],
    ['rj','Rajasthan','Rajasthan',[70,26.5,70.5,27.8,72.8,29,74,29.8,75.2,29.6,76.2,28.4,77.5,27.6,78.2,26.8,77,25.2,75,24.4,74.3,23.5,73.4,23.9,72.4,24.6,71,24.5,70.1,25.8]],
    ['gj','Gujarat','Gujarat',[71,24.5,72.4,24.6,73.4,23.9,74.3,23.5,74.1,22.2,73.6,21.2,73,20.5,72.8,20.5,72.7,21.7,72,21,70.2,21,69,22.3,70,22.8,68.5,23.3,68.2,23.7,70,24.2]],
    ['up','Uttar Pradesh','Uttar Pradesh',[77.6,30.2,79,29.2,80.1,28.8,81,28.2,84.1,27.4,83.7,25.9,83.4,24.5,81.8,24.2,80.5,25.1,79,25.3,78.5,25.8,78.2,26.8,77.5,27.6,77.4,28.7]],
    ['mp','Madhya Pradesh','Madhya Pradesh',[74.3,23.5,75,24.4,77,25.2,78.2,26.8,78.5,25.8,79,25.3,80.5,25.1,81.8,24.2,82.8,23.4,82,22.4,80.5,21.4,79.5,21.7,78,21.6,76.5,21.5,75,21.5,74.1,22.2]],
    ['cg','Chhattisgarh','Chhattisgarh',[82,22.4,82.8,23.4,84.2,23.5,84,22.3,83.4,21.3,82.3,19.9,81.4,18.9,80.5,19.5,80.5,21.4]],
    ['mh','Maharashtra','Maharashtra',[72.8,20.5,73,20.5,73.6,21.2,74.1,22.2,75,21.5,76.5,21.5,78,21.6,79.5,21.7,80.5,21.4,80.5,19.5,79.9,19,78.5,19.2,77.5,18.6,76.5,17.8,75.8,17,74.5,16.5,73.7,16,73,17.5,72.8,19]],
    ['ts','Telangana','Telangana',[78.5,19.2,79.9,19,80.5,19.5,81.4,18.9,81,17.5,80.6,16.8,79.5,16.3,78.5,15.8,77.7,16.4,77.3,17.4,76.5,17.8,77.5,18.6]],
    ['ap','Andhra Pradesh','Andhra Pradesh',[81.4,18.9,81,17.5,80.6,16.8,79.5,16.3,78.5,15.8,77.7,15,77.8,14,78.3,13.5,78.9,13.3,80.1,13.4,80.2,15.5,81.5,16.5,83,17.5,84.2,18.6,82.3,19.9]],
    ['ka','Karnataka','Karnataka',[74.5,16.5,75.8,17,76.5,17.8,77.3,17.4,77.7,16.4,78.5,15.8,77.7,15,77.8,14,78.3,13.5,78.6,12.5,77.8,11.7,76.4,11.8,75.5,11.9,74.8,12.8,73.9,15.4,73.7,16]],
    ['kl','Kerala','Kerala',[75.5,11.9,76.4,11.8,77.2,10.2,77,8.5,76.5,8.8,75.8,11.2]],
    ['tn','Tamil Nadu','Tamil Nadu',[76.4,11.8,77.8,11.7,78.6,12.5,78.3,13.5,78.9,13.3,80.1,13.4,79.8,11.5,79.9,10.3,78.9,9.2,77.5,8.1,77,8.5,77.2,10.2]],
    ['od','Odisha','Odisha',[82.3,19.9,83.4,21.3,84,22.3,85.5,22.6,87,21.5,86.5,20.2,85,19.3,84.2,18.6]],
    ['bh','Bihar & Jharkhand','Bihar|Jharkhand',[83.7,25.9,84.1,27.4,86,26.6,87.8,26.4,87.9,25.2,87.3,24,86.4,23.4,85.5,22.6,84,22.3,84.2,23.5,82.8,23.4,83.4,24.5]],
    ['wb','West Bengal','West Bengal',[87.8,26.4,88.1,26.5,89,26.2,88.7,24.9,88.2,24.5,88.1,22,88.9,21.6,87,21.5,85.5,22.6,86.4,23.4,87.3,24,87.9,25.2]],
    ['ne','North-East','Assam|Sikkim|Meghalaya|Tripura|Manipur|Mizoram|Nagaland|Arunachal Pradesh',[88.1,26.5,88.1,27.8,89,27.3,90,26.8,92,26.9,93.5,27,95.2,28,96.1,29.4,97.4,28.2,97,27.3,95.4,26,94.5,24,93.3,22.8,92.5,22,92.2,23.6,91.5,24.1,91,25.2,89.8,25.3,89,26.2]],
    ['del','Delhi','Delhi',[76.85,28.95,77.35,28.95,77.35,28.4,76.85,28.4]]
  ];

  function P(lo, la) { return [(lo - 68) * 8, (38 - la) * 8]; }
  function col(t) { return t < 38 ? '#e9c46a' : t < 41 ? '#f2a65a' : t < 45 ? '#e4694f' : '#b44a6c'; }
  function stateOf(p) {
    var s = (p.state || '').toLowerCase();
    for (var i = 0; i < ST.length; i++) if (ST[i][2].toLowerCase().split('|').indexOf(s) > -1) return ST[i][0];
    return null;
  }

  var temp = {}, BB = {}, D = {}, cur = [0, 0, 240, 262], sel = null, NS = 'http://www.w3.org/2000/svg';
  pts.forEach(function (p) { var id = stateOf(p); if (id) temp[id] = Math.max(temp[id] || 0, p.temp); });
  ST.forEach(function (s) {
    var xy = [], i, a = s[3];
    for (i = 0; i < a.length; i += 2) xy.push(P(a[i], a[i + 1]));
    var xs = xy.map(function (q) { return q[0]; }), ys = xy.map(function (q) { return q[1]; });
    BB[s[0]] = [Math.min.apply(0, xs), Math.min.apply(0, ys), Math.max.apply(0, xs), Math.max.apply(0, ys)];
    D[s[0]] = 'M' + xy.map(function (q) { return q[0] + ' ' + q[1]; }).join('L') + 'Z';
  });

  // build the panel
  var grid = '', n;
  [70, 75, 80, 85, 90, 95].forEach(function (l) { n = P(l, 0)[0]; grid += '<line class="hsm-gl" x1="' + n + '" y1="0" x2="' + n + '" y2="262"/><text class="hsm-gt" x="' + (n + 1) + '" y="258">' + l + '°E</text>'; });
  [10, 15, 20, 25, 30, 35].forEach(function (l) { n = P(0, l)[1]; grid += '<line class="hsm-gl" x1="0" y1="' + n + '" x2="240" y2="' + n + '"/><text class="hsm-gt" x="2" y="' + (n - 1.5) + '">' + l + '°N</text>'; });
  var states = ST.map(function (s, i) {
    return '<path class="hsm-st" data-id="' + s[0] + '" style="animation-delay:' + i * 40 + 'ms' + (temp[s[0]] ? ';fill:' + col(temp[s[0]]) : '') + '" d="' + D[s[0]] + '"><title>' + s[1] + (temp[s[0]] ? ' · ' + temp[s[0]].toFixed(1) + ' °C' : '') + '</title></path>';
  }).join('');
  var pins = pts.map(function (p, i) {
    var q = P(p.lon, p.lat);
    return '<g class="hsm-pg" style="animation-delay:' + (1000 + i * 70) + 'ms">' + (i < 3 ? '<circle class="hsm-pulse" cx="' + q[0] + '" cy="' + q[1] + '"/>' : '') +
      '<circle class="hsm-ring" cx="' + q[0] + '" cy="' + q[1] + '"/><circle class="hsm-dot" cx="' + q[0] + '" cy="' + q[1] + '"/><text class="hsm-pl" x="' + (q[0] + 4.5) + '" y="' + (q[1] + 1.8) + '">' + p.temp.toFixed(1) + '</text></g>';
  }).join('');
  host.innerHTML = '<svg viewBox="0 0 240 262" style="--s:1"><g>' + grid + '</g><g id="hsm-states">' + states + '</g><g id="hsm-pins">' + pins + '</g></svg>' +
    '<div class="hsm-tl">India · max forecast temp</div><button type="button" class="hsm-reset">Reset view</button>' +
    '<div class="hsm-bl"><div class="hsm-leg"><i style="background:#e9c46a"></i><i style="background:#f2a65a"></i><i style="background:#e4694f"></i><i style="background:#b44a6c"></i></div><div class="hsm-lt"><span>&lt;38°C</span><span>41°C</span><span>45°C+</span></div></div>' +
    '<div class="hsm-br">Click a state to zoom</div>';
  var svg = host.querySelector('svg'), rd = host.querySelector('.hsm-br'), rs = host.querySelector('.hsm-reset');

  // zoom: animate the viewBox; a moving highlight runs around the state's border
  function view(t) {
    var f = cur.slice(), t0 = performance.now();
    (function step(now) {
      var k = Math.min(1, (now - t0) / 650), e = 1 - Math.pow(1 - k, 3), v = f.map(function (a, i) { return a + (t[i] - a) * e; });
      svg.setAttribute('viewBox', v.join(' ')); svg.style.setProperty('--s', v[2] / 240); cur = v;
      if (k < 1) requestAnimationFrame(step);
    })(t0);
  }
  function zoom(id) {
    var old = svg.querySelector('.hsm-trace'); if (old) old.remove();
    svg.querySelectorAll('.hsm-st').forEach(function (e) { e.classList.remove('sel'); });
    if (!id || id === sel) {
      sel = null; rs.classList.remove('on'); view([0, 0, 240, 262]); rd.textContent = 'Click a state to zoom';
      host.dispatchEvent(new CustomEvent('hsm:select', { detail: null }));   // tell the detail panel to hide
      return;
    }
    sel = id;
    svg.querySelector('.hsm-st[data-id="' + id + '"]').classList.add('sel');
    var tr = document.createElementNS(NS, 'path');
    tr.setAttribute('class', 'hsm-trace'); tr.setAttribute('pathLength', '1'); tr.setAttribute('d', D[id]);
    svg.insertBefore(tr, svg.querySelector('#hsm-pins'));
    var b = BB[id], cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2, w = Math.max((b[2] - b[0]) * 1.5, 60), h = Math.max((b[3] - b[1]) * 1.5, 65), k = Math.max(w / 240, h / 262), W = 240 * k, H = 262 * k;
    view([Math.max(-10, cx - W / 2), Math.max(-5, cy - H / 2), W, H]);
    rs.classList.add('on');
    var s = ST.filter(function (x) { return x[0] === id; })[0];
    rd.textContent = s[1] + (temp[id] ? ' · ' + temp[id].toFixed(1) + ' °C' : ' · no data');
    // tell the detail panel which state was chosen and which regions are in it
    host.dispatchEvent(new CustomEvent('hsm:select', { detail: { id: id, label: s[1], points: pts.filter(function (p) { return stateOf(p) === id; }) } }));
  }
  svg.addEventListener('click', function (e) { var p = e.target.closest('.hsm-st'); if (p) zoom(p.dataset.id); });
  rs.addEventListener('click', function () { zoom(null); });
  svg.addEventListener('pointermove', function (e) {
    if (sel) return;
    var q = svg.createSVGPoint(); q.x = e.clientX; q.y = e.clientY;
    var r = q.matrixTransform(svg.getScreenCTM().inverse());
    rd.textContent = (38 - r.y / 8).toFixed(2) + '°N ' + (r.x / 8 + 68).toFixed(2) + '°E';
  });
  svg.addEventListener('pointerleave', function () { if (!sel) rd.textContent = 'Click a state to zoom'; });

  // hottest regions list
  var rk = document.getElementById('hsm-rank');
  if (rk) {
    rk.innerHTML = pts.slice(0, 7).map(function (p, i) {
      return '<div class="hsm-rk" data-id="' + (stateOf(p) || '') + '"><span>' + (i + 1) + '</span><span>' + p.name + '</span><span class="t"><i data-w="' + Math.max(5, Math.min(100, (p.temp - 30) / 20 * 100)).toFixed(0) + '" style="background:' + col(p.temp) + '"></i></span><b>' + p.temp.toFixed(1) + '°</b></div>';
    }).join('');
    rk.addEventListener('click', function (e) { var r = e.target.closest('.hsm-rk'); if (r && r.dataset.id) zoom(r.dataset.id); });
    setTimeout(function () { rk.querySelectorAll('i').forEach(function (e, i) { setTimeout(function () { e.style.width = e.dataset.w + '%'; }, i * 90); }); }, 500);
  }
})();