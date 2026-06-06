App({
  globalData: {
    token: '',
    userInfo: null,
    phoneNumber: '',
    // 当前选择的门店
    currentStore: {
      id: 1,
      name: '伊家人酒店·西湖店',
      address: '杭州市西湖区龙井路88号',
      lat: 30.2375,
      lng: 120.1398,
      phone: '0571-88886666'
    },
    // 附近门店列表
    nearbyStores: [],
    // API 基础地址
    apiBase: require('./utils/const').API_BASE,  // 统一走 const.js 配置
    // 当前定位
    location: {
      lat: 30.2375,
      lng: 120.1398,
      city: '杭州'
    }
  },

  onLaunch() {
    // 检查登录状态
    const token = wx.getStorageSync('token')
    if (token) {
      this.globalData.token = token
      this.checkLogin()
    }

    // 获取系统信息
    const systemInfo = wx.getSystemInfoSync()
    this.globalData.systemInfo = systemInfo
    this.globalData.statusBarHeight = systemInfo.statusBarHeight
    this.globalData.navBarHeight = systemInfo.platform === 'android' ? 48 : 44
    this.globalData.safeTop = systemInfo.statusBarHeight + (systemInfo.platform === 'android' ? 48 : 44)
  },

  // 检查登录是否有效
  checkLogin() {
    const that = this
    wx.request({
      url: `${this.globalData.apiBase}/api/user/profile`,
      header: { Authorization: `Bearer ${this.globalData.token}` },
      success(res) {
        if (res.data.code === 0) {
          that.globalData.userInfo = res.data.data
        } else {
          that.globalData.token = ''
          wx.removeStorageSync('token')
        }
      },
      fail() {
        // 网络失败保留本地token
      }
    })
  },

  // 微信登录获取token
  wxLogin(callback) {
    const that = this
    wx.login({
      success(loginRes) {
        if (loginRes.code) {
          wx.request({
            url: `${that.globalData.apiBase}/api/auth/wx-login`,
            method: 'POST',
            data: { code: loginRes.code },
            success(res) {
              if (res.data.code === 0 && res.data.data.token) {
                that.globalData.token = res.data.data.token
                wx.setStorageSync('token', res.data.data.token)
                if (res.data.data.userInfo) {
                  that.globalData.userInfo = res.data.data.userInfo
                }
                callback && callback(true)
              } else {
                callback && callback(false)
              }
            },
            fail() {
              callback && callback(false)
            }
          })
        }
      }
    })
  },

  // 获取用户手机号
  getPhoneNumber(e, callback) {
    const that = this
    if (e.detail.errMsg !== 'getPhoneNumber:ok') {
      wx.showToast({ title: '获取手机号失败', icon: 'none' })
      return
    }
    wx.request({
      url: `${this.globalData.apiBase}/api/auth/bind-phone`,
      method: 'POST',
      header: { Authorization: `Bearer ${this.globalData.token}` },
      data: {
        encryptedData: e.detail.encryptedData,
        iv: e.detail.iv
      },
      success(res) {
        if (res.data.code === 0) {
          that.globalData.phoneNumber = res.data.data.phone
          callback && callback(true, res.data.data.phone)
        } else {
          wx.showToast({ title: '绑定失败', icon: 'none' })
          callback && callback(false)
        }
      }
    })
  },

  // 切换门店
  switchStore(store) {
    this.globalData.currentStore = store
    wx.setStorageSync('currentStore', store)
  },

  // 请求封装
  request(options) {
    const app = this
    return new Promise((resolve, reject) => {
      const header = {
        'Content-Type': 'application/json'
      }
      if (app.globalData.token) {
        header.Authorization = `Bearer ${app.globalData.token}`
      }
      wx.request({
        url: `${app.globalData.apiBase}${options.url}`,
        method: options.method || 'GET',
        data: options.data || {},
        header,
        success(res) {
          if (res.statusCode === 401) {
            app.globalData.token = ''
            wx.removeStorageSync('token')
            wx.navigateTo({ url: '/pages/mine/mine' })
            reject(res)
          } else if (res.data.code === 0) {
            resolve(res.data.data)
          } else {
            wx.showToast({ title: res.data.msg || '请求失败', icon: 'none' })
            reject(res.data)
          }
        },
        fail(err) {
          wx.showToast({ title: '网络异常', icon: 'none' })
          reject(err)
        }
      })
    })
  }
})
