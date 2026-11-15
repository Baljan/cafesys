(function () {
  "use strict";

  var SLIDE_MS = 12000;
  var POLL_MS = 15000;
  var STALE_MS = 2 * 60 * 1000;
  var RELOAD_MS = 6 * 60 * 60 * 1000;

  var cfg = window.SKARM;
  var stage = document.querySelector(".skarm-stage");
  var offline = document.querySelector(".skarm-offline");
  var clock = document.querySelector(".skarm-clock");

  var data = JSON.parse(document.getElementById("skarm-data").textContent);
  var loadedAt = Date.now();
  var lastOk = Date.now();
  var index = -1;
  var lastKey = null;

  function esc(value) {
    return String(value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmt(n) {
    return Number(n).toLocaleString("sv-SE");
  }

  function num(n) {
    return '<span class="num">' + fmt(n) + "</span>";
  }

  function cafeName(key) {
    return data.cafes.filter(function (c) {
      return c.key === key;
    })[0].name;
  }

  function sum(counts) {
    return data.cafes.reduce(function (acc, c) {
      return acc + counts[c.key];
    }, 0);
  }

  function isStale() {
    return Date.now() - lastOk > STALE_MS;
  }

  function slide(key, title, sub, body) {
    return {
      key: key,
      html: "<h1>" + title + "</h1>" + (sub ? '<p class="sub">' + sub + "</p>" : "") + body,
    };
  }

  // Slides. Each returns null when it has nothing worth showing.

  function rushSlide() {
    var t = data.today;
    var r = t.rush;
    // Old numbers must not pose as the current break.
    if (!r || isStale()) return null;
    if (sum(r.counts) === 0 && !t.open.baljan && !t.open.byttan) return null;

    var title = r.live
      ? r.lunch ? "Lunchen" : "Nuvarande akademisk kvart"
      : r.lunch ? "Senaste lunchen" : "Senaste akademiska kvarten";

    var sides = data.cafes.map(function (c) {
      var n = r.counts[c.key];
      return (
        '<div class="' + c.key + '"><span class="cafe">' + esc(c.name) + "</span>" +
        (!t.open[c.key] && n === 0 ? '<span class="is-closed">Stängt</span>' : num(n)) +
        "</div>"
      );
    });

    return slide("rush", title, "Blipp " + r.start + "–" + r.end, '<div class="duel">' + sides.join("") + "</div>");
  }

  function todaySlide() {
    var t = data.today;
    var total = sum(t.totals);
    if (total === 0) return null;

    var score =
      '<span class="cafe baljan">Baljan</span>' + num(t.totals.baljan) +
      '<span class="dash">–</span>' +
      num(t.totals.byttan) + '<span class="cafe byttan">Byttan</span>';

    var split = data.cafes.map(function (c) {
      return '<span class="' + c.key + '" style="flex-grow:' + t.totals[c.key] + '"></span>';
    });

    var max = 1;
    t.hours.forEach(function (h) {
      max = Math.max(max, h.baljan, h.byttan);
    });
    var hours = t.hours.map(function (h) {
      var cls = h.hour === t.now_hour ? " is-now" : h.hour > t.now_hour ? " is-future" : "";
      var bars = data.cafes.map(function (c) {
        return '<span class="bar ' + c.key + '" style="height:' + (100 * h[c.key]) / max + '%"></span>';
      });
      return (
        '<div class="hour' + cls + '"><div class="bars">' + bars.join("") + "</div>" +
        '<span class="label">' + ("0" + h.hour).slice(-2) + ":00</span></div>"
      );
    });

    return slide(
      "today",
      "Baljan mot Byttan",
      "Idag, " + esc(t.day),
      '<div class="score">' + score + "</div>" +
        '<div class="split">' + split.join("") + "</div>" +
        '<div class="hours">' + hours.join("") + "</div>"
    );
  }

  function topSlide() {
    var top = data.top;
    if (!cfg.showTop || !top) return null;

    // Second place to the left of the winner, third to the right.
    var steps = [1, 0, 2]
      .filter(function (i) {
        return top.people[i];
      })
      .map(function (i) {
        var p = top.people[i];
        return (
          '<div class="step place-' + Math.min(p.rank, 3) + '">' +
          '<span class="name">' + esc(p.name) + "</span>" +
          '<div class="block"><span class="rank">' + p.rank + "</span>" +
          '<span class="count">' + num(p.count) + "blipp</span></div>" +
          "</div>"
        );
      });

    return slide(
      "top",
      "Terminens ledare",
      "Topplistan " + esc(top.name),
      '<div class="podium">' + steps.join("") + "</div>" +
        '<p class="podium-note">Personalen tävlar i en egen liga. ' +
        "Vill du inte synas här? Bocka ur topplistan under Profil på baljan.org.</p>"
    );
  }

  function recordSlide() {
    var s = data.semester;
    if (!s || !s.record) return null;
    var r = s.record;
    return slide(
      "record",
      "Flest blipp på en kvart",
      "Terminsrekord " + esc(s.name),
      '<div class="hero ' + r.cafe + '">' + num(r.n) +
        '<span class="note">I ' + esc(cafeName(r.cafe)) + " " + esc(r.day) + " kl. " + r.start + "</span>" +
        "</div>"
    );
  }

  function rhythmSlide() {
    var s = data.semester;
    if (!s || !s.rhythm) return null;
    var avgs = s.rhythm.map(function (b) {
      return b.avg;
    });
    var max = Math.max.apply(null, avgs);
    var min = Math.min.apply(null, avgs);
    if (max === min) return null;

    var calm = s.rhythm[avgs.indexOf(min)];
    var busy = s.rhythm[avgs.indexOf(max)];
    var beats = s.rhythm.map(function (b) {
      var cls = b === calm ? " is-calm" : b === busy ? " is-busy" : "";
      return (
        '<div class="beat' + cls + '">' +
        '<span class="avg">' + fmt(b.avg) + "</span>" +
        '<div class="bars"><span class="bar" style="height:' + (100 * b.avg) / max + '%"></span></div>' +
        '<span class="label">' + ("0" + b.hour).slice(-2) + ":00</span>" +
        "</div>"
      );
    });

    return slide(
      "rhythm",
      "När är det lugnast?",
      "Blipp per akademisk kvart i snitt, " + esc(s.name),
      '<div class="rhythm">' + beats.join("") + "</div>" +
        '<p class="verdict">Lugnast kl. <span class="calm">' + calm.hour + "</span>, " +
        'flest blipp kl. <span class="busy">' + busy.hour + "</span>.</p>"
    );
  }

  function semesterSlide() {
    var s = data.semester;
    if (!s) return null;
    var tally = data.cafes.map(function (c) {
      return '<span class="' + c.key + '"><span class="cafe">' + esc(c.name) + "</span>" + num(s.totals[c.key]) + "</span>";
    });

    return slide(
      "semester",
      s.ended ? "Förra terminen" : "Hittills den här terminen",
      esc(s.name),
      '<div class="hero">' + num(s.total) +
        '<span class="note">koppar kaffe, te och choklad</span></div>' +
        '<div class="tally">' + tally.join("") + "</div>"
    );
  }

  function fallbackSlide() {
    return slide("fallback", "Kaffe åt folket!", "", '<img src="' + cfg.kleggbert + '" alt="" />');
  }

  function build(fn) {
    // A broken slide is skipped instead of freezing the screen.
    try {
      return fn();
    } catch (e) {
      return null;
    }
  }

  function deck() {
    var base = [todaySlide, topSlide, recordSlide, rhythmSlide, semesterSlide]
      .map(build)
      .filter(Boolean);
    var rush = build(rushSlide);
    if (!rush) return base.length ? base : [fallbackSlide()];
    if (!data.today.rush.live) return [rush].concat(base);

    // During a break the live numbers are the point, so show them every other slide.
    var out = [];
    base.forEach(function (s) {
      out.push(rush, s);
    });
    return out.length ? out : [rush];
  }

  function show(s) {
    var el = document.createElement("section");
    el.className = "slide slide-" + s.key;
    el.innerHTML = s.html;
    stage.appendChild(el);

    var old = stage.querySelectorAll(".slide.is-active");
    el.getBoundingClientRect();
    el.classList.add("is-active");

    for (var i = 0; i < old.length; i++) {
      old[i].classList.remove("is-active");
      (function (node) {
        window.setTimeout(function () {
          if (node.parentNode) node.parentNode.removeChild(node);
        }, 900);
      })(old[i]);
    }
  }

  function get(url, onOk) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url);
    xhr.timeout = 15000;
    xhr.onload = function () {
      try {
        if (xhr.status === 200) onOk(xhr.responseText);
      } finally {
        updateOffline();
      }
    };
    xhr.onerror = xhr.ontimeout = updateOffline;
    xhr.send();
  }

  // Reload now and then to pick up deploys, but only when the page is
  // reachable, so a restart never leaves the screen on an error page.
  function maybeReload() {
    if (Date.now() - loadedAt < RELOAD_MS) return;
    get(window.location.href, function () {
      window.location.reload();
    });
  }

  function next() {
    var slides = deck();
    index = (index + 1) % slides.length;
    if (slides.length > 1 && slides[index].key === lastKey) {
      index = (index + 1) % slides.length;
    }
    lastKey = slides[index].key;
    show(slides[index]);
    maybeReload();
  }

  function poll() {
    get(cfg.dataUrl, function (text) {
      data = JSON.parse(text);
      lastOk = Date.now();
    });
  }

  function updateOffline() {
    offline.hidden = !isStale();
  }

  function tick() {
    var now = new Date();
    clock.textContent = ("0" + now.getHours()).slice(-2) + ":" + ("0" + now.getMinutes()).slice(-2);
  }

  // Keep the screen on where the browser allows it (Safari 16.4+).
  function stayAwake() {
    if (!("wakeLock" in navigator) || document.visibilityState !== "visible") return;
    navigator.wakeLock.request("screen").catch(function () {});
  }

  document.addEventListener("visibilitychange", stayAwake);
  stayAwake();

  tick();
  window.setInterval(tick, 1000);
  window.setInterval(poll, POLL_MS);
  window.setInterval(next, SLIDE_MS);
  next();
})();
