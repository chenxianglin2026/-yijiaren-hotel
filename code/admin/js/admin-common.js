  YJ.token = function() {
    if (YJ._token) return YJ._token;
    var t = typeof window.YJR_TOKEN;
    if (t == 'str' + 'ing' && window.YJR_TOKEN) {
      YJ._token = window.YJR_TOKEN;
    } else if (window.parent !== window) {
      t = typeof window.parent.YJR_TOKEN;
      if (t == 'str' + 'ing' && window.parent.YJR_TOKEN) {
        YJ._token = window.parent.YJR_TOKEN;
      }
    } else {
      try { YJ._token = localStorage.getItem('yjr_token') || ''; } catch(e) { YJ._token = ''; }
    }
    return YJ._token;
  };