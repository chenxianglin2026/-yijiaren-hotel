/** admin-common.js v5 — 完整版，所有函数在一个闭包里 */
(function() {
  var YJ = window.YJ || {};
  var _token = '';

  YJ.init = function() {
    if (_token) return Promise.resolve(_token);
    return fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'admin123' })
    }).then(function(r) { return r.json(); })
      .then(function(j) {
        _token = j.access_token || '';
        if (_token) try { localStorage.setItem('yjr_token', _token); } catch(e) {}
        return _token;
      });
  };

  YJ.api = function(url, opt) {
    opt = opt || {};
    function call() {
      var h = { 'Authorization': 'Bearer ' + _token };
      if (opt.body) h['Content-Type'] = 'application/json';
      var u = url;
      if (opt.params) {
        var q = [];
        for (var k in opt.params) {
          if (opt.params[k] != null && opt.params[k] !== '') q.push(k + '=' + opt.params[k]);
        }
        if (q.length) u += (u.indexOf('?') < 0 ? '?' : '&') + q.join('&');
      }
      var fo = { method: opt.method || 'GET', headers: h };
      if (opt.body) fo.body = JSON.stringify(opt.body);
      return fetch(u, fo).then(function(r) {
        if (r.status === 401) { _token = ''; return YJ.init().then(function() { return call(); }); }
        return r.json().then(function(j) {
          if (!r.ok) throw new Error(j.detail || j.msg || 'HTTP ' + r.status);
          return j;
        });
      });
    }
    return YJ.init().then(function() { return call(); });
  };

  YJ.get = function(url, p) { return YJ.api(url, { params: p }).then(function(r) { return r.data !== undefined ? r.data : r; }); };
  YJ.post = function(url, b) { return YJ.api(url, { method: 'POST', body: b }); };
  YJ.put = function(url, b) { return YJ.api(url, { method: 'PUT', body: b }); };
  YJ.del = function(url) { return YJ.api(url, { method: 'DELETE' }); };
  YJ.toast = function(m, t) { console.log('['+(t||'info')+']', m); };
  YJ.fmtDate = function(d) { d = new Date(d); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); };
  YJ.fmtMoney = function(n) { return '¥' + Number(n||0).toLocaleString(); };
  YJ.fmtDateTime = function(d) { d = new Date(d); return YJ.fmtDate(d)+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'); };
  YJ.selectedHotelId = function() { try { return localStorage.getItem('selectedHotelId')||''; } catch(e) { return ''; } };
  YJ.getData = function(obj, path, fb) { var ks=path.split('.'),v=obj; for(var i=0;i<ks.length;i++){if(v==null)return fb;v=v[ks[i]]} return v!=null?v:fb; };
  YJ.authHeaders = function() { return { 'Authorization': 'Bearer ' + _token }; };
  YJ.parseItems = function(r) { if (Array.isArray(r)) return r; if (r.items) return r.items; if (r.data) return Array.isArray(r.data)?r.data:(r.data.items||[]); return []; };

  window.YJ = YJ;
})();
