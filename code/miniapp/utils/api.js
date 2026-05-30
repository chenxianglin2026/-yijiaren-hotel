/**
 * 伊家人酒店小程序 - API 封装工具
 * BaseURL: http://localhost:8001
 * 封装 wx.request，提供统一的请求/响应拦截、Token 管理、错误处理
 */

const BASE_URL = 'http://43.163.5.90:8001'

// 请求队列，用于并发请求时的 token 刷新
let isRefreshing = false
let refreshQueue = []

// 默认请求头
const getDefaultHeader = () => {
  const header = {
    'Content-Type': 'application/json'
  }
  const token = wx.getStorageSync('token')
  if (token) {
    header['Authorization'] = `Bearer ${token}`
  }
  return header
}

// 通用请求方法
const request = (options) => {
  return new Promise((resolve, reject) => {
    const {
      url,
      method = 'GET',
      data = {},
      header: customHeader = {},
      showLoading = false,
      loadingText = '加载中...',
      timeout = 30000
    } = options

    if (showLoading) {
      wx.showLoading({ title: loadingText, mask: true })
    }

    const mergedHeader = { ...getDefaultHeader(), ...customHeader }

    const requestUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`

    console.log(`[API] ${method} ${requestUrl}`, data)

    wx.request({
      url: requestUrl,
      method,
      data,
      header: mergedHeader,
      timeout,
      success(res) {
        if (showLoading) wx.hideLoading()

        const { statusCode, data: resData } = res

        console.log(`[API] Response ${statusCode}:`, resData)

        // 处理不同的 HTTP 状态码
        switch (statusCode) {
          case 200:
          case 201:
          case 204:
            // 业务层 code 判断
            if (resData && resData.code !== undefined) {
              if (resData.code === 0 || resData.code === 200) {
                resolve(resData.data !== undefined ? resData.data : resData)
              } else if (resData.code === 401) {
                // Token 过期，尝试刷新或跳转登录
                handleAuthExpired()
                reject({ code: 401, msg: resData.msg || '登录已过期' })
              } else {
                wx.showToast({ title: resData.msg || '请求失败', icon: 'none' })
                reject(resData)
              }
            } else {
              // 没有业务 code，直接返回
              resolve(resData)
            }
            break
          case 401:
            handleAuthExpired()
            reject({ code: 401, msg: '未授权，请重新登录' })
            break
          case 403:
            wx.showToast({ title: '没有权限', icon: 'none' })
            reject({ code: 403, msg: '没有权限' })
            break
          case 404:
            wx.showToast({ title: '请求的资源不存在', icon: 'none' })
            reject({ code: 404, msg: '资源不存在' })
            break
          case 500:
            wx.showToast({ title: '服务器繁忙，请稍后重试', icon: 'none' })
            reject({ code: 500, msg: '服务器错误' })
            break
          default:
            wx.showToast({ title: `请求失败(${statusCode})`, icon: 'none' })
            reject({ code: statusCode, msg: `请求失败` })
        }
      },
      fail(err) {
        if (showLoading) wx.hideLoading()
        console.error('[API] Network error:', err)
        wx.showToast({ title: '网络异常，请检查网络', icon: 'none' })
        reject({ code: -1, msg: '网络异常', error: err })
      }
    })
  })
}

// Token 过期处理
const handleAuthExpired = () => {
  wx.removeStorageSync('token')
  const app = getApp()
  if (app) {
    app.globalData.token = ''
    app.globalData.userInfo = null
    app.globalData.phoneNumber = ''
  }
  // 跳转到我的页面（会提示登录）
  wx.switchTab({ url: '/pages/mine/mine' })
}

// 便捷方法
const api = {
  /**
   * GET 请求
   * @param {string} url - 请求路径
   * @param {object} data - 查询参数
   * @param {object} options - 额外选项
   */
  get(url, data = {}, options = {}) {
    return request({ url, method: 'GET', data, ...options })
  },

  /**
   * POST 请求
   * @param {string} url - 请求路径
   * @param {object} data - 请求体
   * @param {object} options - 额外选项
   */
  post(url, data = {}, options = {}) {
    return request({ url, method: 'POST', data, ...options })
  },

  /**
   * PUT 请求
   * @param {string} url - 请求路径
   * @param {object} data - 请求体
   * @param {object} options - 额外选项
   */
  put(url, data = {}, options = {}) {
    return request({ url, method: 'PUT', data, ...options })
  },

  /**
   * DELETE 请求
   * @param {string} url - 请求路径
   * @param {object} data - 请求体
   * @param {object} options - 额外选项
   */
  delete(url, data = {}, options = {}) {
    return request({ url, method: 'DELETE', data, ...options })
  },

  /**
   * 文件上传
   * @param {string} url - 上传路径
   * @param {string} filePath - 本地文件路径
   * @param {string} name - 文件字段名
   * @param {object} formData - 额外表单数据
   */
  upload(url, filePath, name = 'file', formData = {}) {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token')
      const header = token ? { 'Authorization': `Bearer ${token}` } : {}
      const uploadUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`

      wx.showLoading({ title: '上传中...', mask: true })

      wx.uploadFile({
        url: uploadUrl,
        filePath,
        name,
        formData,
        header,
        success(res) {
          wx.hideLoading()
          try {
            const data = JSON.parse(res.data)
            if (data.code === 0 || data.code === 200) {
              resolve(data.data !== undefined ? data.data : data)
            } else {
              wx.showToast({ title: data.msg || '上传失败', icon: 'none' })
              reject(data)
            }
          } catch (e) {
            resolve(res.data)
          }
        },
        fail(err) {
          wx.hideLoading()
          wx.showToast({ title: '上传失败', icon: 'none' })
          reject(err)
        }
      })
    })
  }
}

module.exports = api
