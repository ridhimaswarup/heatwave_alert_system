// HeatWatch front-end: India map, count-up numbers, bar fills, charts, flash dismiss.
(function () {
  // Simplified outline of India as [longitude, latitude] points.
  var OUT=[[74.3,37],[76.8,35.7],[78.5,35.5],[79.5,34],[78.8,32.5],[79,31],[80.2,30.4],[81,30.2],[80.1,28.8],[81,28.2],[84.1,27.4],[86,26.6],[88.1,26.5],[88.1,27.8],[89,27.3],[90,26.8],[92,26.9],[93.5,27],[95.2,28],[96.1,29.4],[97.4,28.2],[97,27.3],[95.4,26],[94.5,24],[93.3,22.8],[92.5,22],[92.2,23.6],[91.5,24.1],[91,25.2],[89.8,25.3],[89,26.2],[88.7,24.9],[88.2,24.5],[88.1,22],[88.9,21.6],[87,21.5],[86.5,20.2],[85,19.3],[83,17.5],[81.5,16.5],[80.2,15.5],[80.1,13.4],[79.8,11.5],[79.9,10.3],[78.9,9.2],[77.5,8.1],[76.5,8.8],[75.8,11.2],[74.8,12.8],[73.9,15.4],[73,17.5],[72.8,19],[72.8,20.5],[72.7,21.7],[72,21],[70.2,21],[69,22.3],[70,22.8],[68.5,23.3],[68.2,23.7],[70,24.2],[71,24.5],[70.1,25.8],[70,26.5],[70.5,27.8],[72.8,29],[74,29.8],[74.6,31],[74.8,32.5],[74.2,34]];
  function P(lon, lat) { return [((lon - 68) * 5).toFixed(1), ((37.8 - lat) * 5).toFixed(1)]; }

  // 1. map: outline + pins (first pin = hottest place)
  var map = document.getElementById('map');
  if (map) {
    map.querySelector('path').setAttribute('d', 'M' + OUT.map(function (p) { return P(p[0], p[1]).join(' '); }).join('L') + 'Z');
    var pins = JSON.parse(map.dataset.pins || '[]'), html = '';
    pins.slice().reverse().forEach(function (p, i, all) {
      var peak = i === all.length - 1, xy = P(p.lon, p.lat);
      if (peak) html += '<circle class="ring" cx="' + xy[0] + '" cy="' + xy[1] + '" r="3.4"/>';
      html += '<circle class="pin' + (peak ? ' peak' : '') + '" cx="' + xy[0] + '" cy="' + xy[1] + '" r="' + (peak ? 3.8 : 2.4) + '"><title>' + p.name + '</title></circle>';
    });
    map.querySelector('g').innerHTML = html;
  }

  // 2. start animations shortly after the reveal
  setTimeout(function () {
    if (map) map.classList.add('go');
    document.querySelectorAll('[data-w]').forEach(function (el, i) {
      setTimeout(function () { el.style.width = el.dataset.w + '%'; }, i * 110);
    });
    document.querySelectorAll('[data-n]').forEach(function (el) {
      var n = parseFloat(el.dataset.n), dec = el.dataset.n.indexOf('.') > -1 ? 1 : 0, s = performance.now();
      (function tick(now) {
        var p = Math.min(1, (now - s) / 1200);
        el.textContent = (n * (1 - Math.pow(1 - p, 3))).toFixed(dec);
        if (p < 1) requestAnimationFrame(tick);
      })(s);
    });
  }, 400);

  // 3. Chart.js charts: the route passes the config as JSON in data-chart
  var canvas = document.getElementById('chart');
  if (canvas && window.Chart) {
    Chart.defaults.font.family = "'DM Sans', system-ui, sans-serif";
    Chart.defaults.color = '#6b7f77';
    new Chart(canvas, JSON.parse(canvas.dataset.chart));
  }

  // 4. click a flash message to dismiss it
  document.querySelectorAll('.flash').forEach(function (f) {
    f.addEventListener('click', function () { f.remove(); });
  });
})();