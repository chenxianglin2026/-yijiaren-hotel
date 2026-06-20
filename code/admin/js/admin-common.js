/**
 * admin-common.js — 伊家人管理后台共享库 (精简版)
 * 子页面在iframe中直接读localStorage获取token
 */
(function() {
  var YJ = window.YJ || {};

  function getToken() {
    try { return localStorage.getItem('yjr_token') || ''; } catch(e) { return ''; }
  }

  function getUser() {
    try { return localStorage.getItem('yjr_user') || ''; } catch(e) { return ''; }
  }

  YJ.init = function() {
    var t = getToken();
    if (t) return Promise.resolve(t);
    return new Promise(function(resolve) {
      var n = 0;
      var iv = setInterval(function() {
        t = getToken();
        if (t) { clearInterval(iv); resolve(t); return; }
        if (++n > 30) { clearInterval(iv); resolve(''); }
      }, 100);
    });
  };

  YJ.api = function(url, opt) {
    opt = opt || {};
    var h = { 'Authorization': 'Bearer ' + getToken(), 'Content-Type': 'application/json' };
    if (opt.params) {
      var q = [];
      for (var k in opt.params) {
        if (opt.params[k] !== '' && opt.params[k] != null) q.push(k + '=' + opt.params[k]);
      }
      if (q.length) url += (url.indexOf('?') < 0 ? '?' : '&') + q.join('&');
    }
    var fo = { method: opt.method || 'GET', headers: h };
    if (opt.body) fo.body = JSON.stringify(opt.body);
    return fetch(url, fo).then(function(r) {
      if (r.status === 401) { localStorage.clear(); if (window.top !== window) window.top.location.href = 'pages/login.html'; throw new Error('expired'); }
      return r.json().then(function(j) {
        if (j.code !== undefined && j.code !== 0) throw new Error(j.msg || j.detail || 'fail');
        return j;
      });
    });
  };

  YJ.get = function(url, p) { return YJ.api(url, { params: p }).then(function(r) { return r.data !== undefined ? r.data : r; }); };
  YJ.post = function(url, b) { return YJ.api(url, { method: 'POST', body: b }); };
  YJ.put = function(url, b) { return YJ.api(url, { method: 'PUT', body: b }); };
  YJ.del = function(url) { return YJ.api(url, { method: 'DELETE' }); };

  YJ.toast = function(msg, type) {
    var c = document.getElementById('toasts') || (function() { var d = document.createElement('div'); d.id = 'toasts'; d.style.cssText = 'position:fixed;top:16px;right:16px;z-index:9999'; document.body.appendChild(d); return d; })();
    var e = document.createElement('div');
    e.style.cssText = 'padding:10px 20px;margin-bottom:8px;border-radius:6px;font-size:13px;color:#fff;background:' + ({info:'#1677ff',ok:'#52c41a',warn:'#faad14',err:'#ff4d4f'}[type]||'#1677ff');
    e.textContent = msg;
    c.appendChild(e);
    setTimeout(function() { e.remove(); }, 3000);
  };

  YJ.parseItems = function(r) {
    if (Array.isArray(r)) return r;
    if (r.items) return r.items;
    if (r.data) return Array.isArray(r.data) ? r.data : (r.data.items || []);
    return [];
  };

  window.YJ = YJ;

  // Auto-init on load
  YJ.init().then(function(t) {
    window["YJR_TOKEN"] = t;
  });
})();
