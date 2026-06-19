/**
 * admin-common.js — 伊家人管理后台统一前端库
 * 职责: token获取、API调用封装、数据解析、通用工具
 * 
 * Token获取优先级:
 *   1. window.YJR_TOKEN        — 父窗口注入 (index.html设置)
 *   2. window.parent.YJR_TOKEN — 从父窗口读取 (同源iframe)
 *   3. localStorage.yjr_token  — 本地存储兜底
 *   4. postMessage             — 异步接收父窗口消息 (兜底)
 *
 * 使用方式 (子页面):
 *   <script src="../js/admin-common.js"></script>
 *   <script>
 *     YJ.init().then(function() {
 *       YJ.get('/api/orders').then(function(data) { ... });
 *     });
 *   </script>
 */
(function() {
  'use strict';

  var YJ = window.YJ || {};

  // ==================== Token 管理 ====================
  YJ._token = null;
  YJ._ready = false;
  YJ._initPromise = null;
  YJ._pendingResolve = null;

  /**
   * 同步获取当前token (可能为空)
   */
  YJ.token = function() {
    if (YJ._token) return YJ._token;
    // 优先级: 自身 > 父窗口 > localStorage
    if (typeof window.YJR_TOKEN === 'string' && window.YJR_TOKEN) {
      YJ._token = window.YJR_TOKEN;
    } else if (window.parent !== window && typeof window.parent.YJR_TOKEN === 'string' && window.parent.YJR_TOKEN) {
      YJ._token = window.parent.YJR_TOKEN;
    } else {
      try { YJ._token = localStorage.getItem('yjr_token') || ''; } catch(e) { YJ._token = ''; }
    }
    return YJ._token;
  };

  /**
   * 设置token (供index.html调用)
   */
  YJ.setToken = function(t) {
    YJ._token = t;
    if (!YJ._ready && YJ._pendingResolve) {
      YJ._ready = true;
      var resolve = YJ._pendingResolve;
      YJ._pendingResolve = null;
      resolve(t);
    }
  };

  /**
   * 初始化: 返回Promise, 等待token就绪后resolve
   * 如果token立即可用则同步resolve; 否则等待postMessage或超时3秒
   */
  YJ.init = function() {
    if (YJ._initPromise) return YJ._initPromise;

    var tok = YJ.token();
    if (tok) {
      YJ._ready = true;
      YJ._initPromise = Promise.resolve(tok);
      return YJ._initPromise;
    }

    // 等待token (postMessage 或 轮询)
    YJ._initPromise = new Promise(function(resolve) {
      YJ._pendingResolve = resolve;

      // 监听父窗口postMessage
      var onMsg = function(e) {
        if (e.data && e.data.type === 'YJR_TOKEN') {
          YJ._token = e.data.token;
          YJ._ready = true;
          window.removeEventListener('message', onMsg);
          if (YJ._pendingResolve) {
            var r = YJ._pendingResolve;
            YJ._pendingResolve = null;
            r(YJ._token);
          }
        }
      };
      window.addEventListener('message', onMsg);

      // 超时3秒后强制用localStorage兜底
      setTimeout(function() {
        if (!YJ._ready) {
          try { YJ._token = localStorage.getItem('yjr_token') || ''; } catch(e) { YJ._token = ''; }
          YJ._ready = true;
          window.removeEventListener('message', onMsg);
          if (YJ._pendingResolve) {
            var r = YJ._pendingResolve;
            YJ._pendingResolve = null;
            r(YJ._token);
          }
        }
      }, 3000);
    });

    return YJ._initPromise;
  };

  // ==================== API 调用封装 ====================

  /**
   * 获取认证headers
   */
  YJ.authHeaders = function(extra) {
    var h = { 'Authorization': 'Bearer ' + (YJ._token || '') };
    if (extra) {
      for (var k in extra) { if (extra.hasOwnProperty(k)) h[k] = extra[k]; }
    }
    return h;
  };

  /**
   * 通用API调用, 自动处理:
   *   - 认证header
   *   - 401 → 跳转登录
   *   - JSON解析 + 统一错误格式
   * 
   * @param {string} url     - API路径 (如 '/api/orders')
   * @param {object} options - fetch options (method, body, params等)
   *   options.params - URL查询参数对象, 自动拼接到url
   * @returns {Promise<object>} { code: 0, data: ..., msg: ... }
   */
  YJ.api = function(url, options) {
    options = options || {};
    var method = options.method || 'GET';
    var headers = YJ.authHeaders(options.headers || {});

    // 拼接查询参数
    if (options.params) {
      var qs = [];
      for (var k in options.params) {
        if (options.params.hasOwnProperty(k) && options.params[k] !== '' && options.params[k] !== null && options.params[k] !== undefined) {
          qs.push(encodeURIComponent(k) + '=' + encodeURIComponent(options.params[k]));
        }
      }
      if (qs.length) url += (url.indexOf('?') === -1 ? '?' : '&') + qs.join('&');
    }

    var fetchOpts = { method: method, headers: headers };
    if (options.body) {
      if (typeof options.body === 'object' && !(options.body instanceof FormData)) {
        fetchOpts.body = JSON.stringify(options.body);
        headers['Content-Type'] = 'application/json';
      } else {
        fetchOpts.body = options.body;
      }
    }

    return fetch(url, fetchOpts).then(function(r) {
      if (r.status === 401) {
        // 清理并跳转登录
        try { localStorage.removeItem('yjr_token'); localStorage.removeItem('yjr_user'); } catch(e) {}
        if (window.top !== window) {
          window.top.location.href = 'pages/login.html';
        } else {
          window.location.href = 'pages/login.html';
        }
        throw new Error('登录已过期，请重新登录');
      }
      return r.json().then(function(j) {
        // 统一格式: { code: 0, data: ..., msg: ... }
        if (j.code !== undefined && j.code !== 0) {
          throw new Error(j.msg || j.detail || '请求失败');
        }
        return j;
      }).catch(function(e) {
        // JSON解析失败, 可能是非JSON响应
        if (e instanceof SyntaxError) throw new Error('服务器响应格式错误 (HTTP ' + r.status + ')');
        throw e;
      });
    });
  };

  /**
   * GET 快捷方法
   * @returns {Promise<object>} 解析后的响应数据 (res.data)
   */
  YJ.get = function(url, params) {
    return YJ.api(url, { method: 'GET', params: params }).then(function(res) {
      return res.data !== undefined ? res.data : res;
    });
  };

  /**
   * POST 快捷方法
   */
  YJ.post = function(url, body) {
    return YJ.api(url, { method: 'POST', body: body }).then(function(res) {
      return res.data !== undefined ? res.data : res;
    });
  };

  /**
   * PUT 快捷方法
   */
  YJ.put = function(url, body) {
    return YJ.api(url, { method: 'PUT', body: body }).then(function(res) {
      return res.data !== undefined ? res.data : res;
    });
  };

  /**
   * DELETE 快捷方法
   */
  YJ.del = function(url) {
    return YJ.api(url, { method: 'DELETE' }).then(function(res) {
      return res.data !== undefined ? res.data : res;
    });
  };

  // ==================== 通用工具 ====================

  /** Toast消息提示 */
  YJ.toast = function(msg, type) {
    type = type || 'info';
    var container = document.getElementById('yj-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'yj-toast-container';
      container.style.cssText = 'position:fixed;top:16px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
      document.body.appendChild(container);
    }
    var el = document.createElement('div');
    el.style.cssText = 'padding:10px 20px;border-radius:6px;font-size:13px;color:#fff;pointer-events:auto;box-shadow:0 4px 12px rgba(0,0,0,.2);animation:yj-fadein .3s ease;max-width:360px;word-break:break-all;';
    var colors = { info: '#1677ff', success: '#52c41a', warning: '#faad14', error: '#ff4d4f' };
    el.style.background = colors[type] || colors.info;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(function() {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.3s';
      setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 300);
    }, 3000);
  };

  /** 格式化金额 */
  YJ.fmtMoney = function(n) {
    return '¥' + Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  };

  /** 格式化日期 YYYY-MM-DD */
  YJ.fmtDate = function(d) {
    d = d || new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  };

  /** 格式化日期时间 */
  YJ.fmtDateTime = function(d) {
    d = d || new Date();
    return YJ.fmtDate(d) + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0') + ':' + String(d.getSeconds()).padStart(2, '0');
  };

  /** 获取当前选择的门店ID */
  YJ.selectedHotelId = function() {
    try { return localStorage.getItem('selectedHotelId') || ''; } catch(e) { return ''; }
  };

  /** 安全获取嵌套数据: YJ.getData(res, 'data.items', []) */
  YJ.getData = function(obj, path, fallback) {
    var keys = path.split('.');
    var val = obj;
    for (var i = 0; i < keys.length; i++) {
      if (val == null) return fallback;
      val = val[keys[i]];
    }
    return val != null ? val : fallback;
  };

  /** 
   * 数据解析: 兼容各种后端返回格式
   * 支持: { items: [...] } / { data: { items: [...] } } / { code:0, data: [...] } / 直接数组
   */
  YJ.parseItems = function(res, path) {
    // 如果指定了path, 按path提取
    if (path) return YJ.getData(res, path, []);
    // 自动尝试常见格式
    var data = res;
    if (data.code === 0 && data.data !== undefined) data = data.data;
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.items)) return data.items;
    if (data && data.data && Array.isArray(data.data.items)) return data.data.items;
    if (data && data.data && Array.isArray(data.data)) return data.data;
    return [];
  };

  // ==================== 暴露到全局 ====================
  window.YJ = YJ;

  // 立即尝试同步获取token (用于YJ.init()调用前的兜底)
  var immediateToken = YJ.token();
  if (immediateToken) {
    YJ._ready = true;
  }

  // 注入一个简单的CSS动画
  if (document.head) {
    var style = document.createElement('style');
    style.textContent = '@keyframes yj-fadein{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}';
    document.head.appendChild(style);
  }
})();
