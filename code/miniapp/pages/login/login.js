const app = getApp()
const api = require('../../utils/api')
const C = require('../../utils/const')

Page({
  data: {
    phoneNumber: '',
    verifyCode: '',
    agreed: false,
    countdown: 0,
    autoFocus: true,
    canLogin: false
  },

  onLoad(options) {
    // 如果已有 token，直接返回
    if (app.globalData.token) {
      wx.navigateBack({ delta: 1 })
      return
    }

    // 从上一页带过来的参数
    if (options.redirect) {
      this.redirectUrl = decodeURIComponent(options.redirect)
    }
  },

  // ========== 输入处理 ==========
  onPhoneInput(e) {
    const phoneNumber = e.detail.value.replace(/\s/g, '').slice(0, 11)
    this.setData({ phoneNumber })
    this.checkCanLogin()
  },

  onCodeInput(e) {
    const verifyCode = e.detail.value.replace(/\s/g, '').slice(0, 6)
    this.setData({ verifyCode })
    this.checkCanLogin()
  },

  onClearPhone() {
    this.setData({ phoneNumber: '', canLogin: false })
  },

  onToggleAgree() {
    this.setData({ agreed: !this.data.agreed })
    this.checkCanLogin()
  },

  // 检查是否可登录
  checkCanLogin() {
    const { phoneNumber, verifyCode, agreed } = this.data
    const canLogin = phoneNumber.length === 11 && verifyCode.length >= 4 && agreed
    this.setData({ canLogin })
  },

  // ========== 验证手机号 ==========
  validatePhone(phone) {
    return /^1[3-9]\d{9}$/.test(phone)
  },

  // ========== 发送验证码 ==========
  onSendCode() {
    const { phoneNumber, countdown } = this.data

    if (countdown > 0) return

    if (!this.validatePhone(phoneNumber)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }

    // 开始倒计时
    this.startCountdown()

    // TODO: 接入真实验证码接口
    // api.post('/auth/send-code', { phone: phoneNumber })
    //   .then(() => {
    //     wx.showToast({ title: '验证码已发送', icon: 'success' })
    //   })
    //   .catch(() => {
    //     this.setData({ countdown: 0 })
    //   })

    // 模拟发送
    wx.showToast({ title: '验证码已发送', icon: 'success' })
  },

  // 倒计时
  startCountdown() {
    this.setData({ countdown: 60 })
    const timer = setInterval(() => {
      const countdown = this.data.countdown - 1
      if (countdown <= 0) {
        clearInterval(this.timerId)
        this.setData({ countdown: 0 })
        return
      }
      this.setData({ countdown })
    }, 1000)
    this.timerId = timer
  },

  // ========== 登录 ==========
  onLogin() {
    const { phoneNumber, verifyCode, agreed, canLogin } = this.data

    if (!canLogin) return

    if (!this.validatePhone(phoneNumber)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }

    if (verifyCode.length < 4) {
      wx.showToast({ title: '请输入完整验证码', icon: 'none' })
      return
    }

    wx.showLoading({ title: '登录中...', mask: true })

    // 模拟登录成功（仅 DEV_MODE）
    if (C.DEV_MODE) {
      setTimeout(() => {
        this.handleLoginSuccess({
          token: 'mock_token_' + Date.now(),
          userInfo: {
            nickName: '酒店住客',
            avatarUrl: '',
            phone: phoneNumber
          }
        })
      }, 1000)
    } else {
      // 生产环境：调用真实登录接口
      api.post('/api/auth/login', {
        phone: phoneNumber,
        code: verifyCode
      }).then(res => {
        this.handleLoginSuccess(res)
      }).catch(err => {
        wx.hideLoading()
        wx.showToast({ title: err.msg || '登录失败', icon: 'none' })
      })
    }
  },

  // 微信手机号一键登录
  onWechatPhoneLogin(e) {
    const that = this
    if (e.detail.errMsg !== 'getPhoneNumber:ok') {
      wx.showToast({ title: '授权取消', icon: 'none' })
      return
    }

    if (!this.data.agreed) {
      wx.showToast({ title: '请先同意用户协议', icon: 'none' })
      return
    }

    wx.showLoading({ title: '登录中...', mask: true })

    wx.login({
      success(loginRes) {
        if (!loginRes.code) {
          wx.hideLoading()
          wx.showToast({ title: '微信登录失败', icon: 'none' })
          return
        }

        api.post('/api/auth/wechat-phone-login', {
          code: loginRes.code,
          encrypted_data: e.detail.encryptedData,
          iv: e.detail.iv,
        }).then(res => {
          that.handleLoginSuccess(res)
        }).catch(err => {
          wx.hideLoading()
          wx.showToast({ title: err.msg || '登录失败', icon: 'none' })
        })
      },
      fail() {
        wx.hideLoading()
        wx.showToast({ title: '微信登录失败', icon: 'none' })
      }
    })
  },

  // 登录成功处理
  handleLoginSuccess(res) {
    wx.hideLoading()

    const { token, userInfo } = res

    // 保存登录状态
    app.globalData.token = token
    app.globalData.userInfo = userInfo
    app.globalData.phoneNumber = userInfo.phone || this.data.phoneNumber
    wx.setStorageSync('token', token)
    wx.setStorageSync('userInfo', userInfo)

    wx.showToast({ title: '登录成功', icon: 'success', duration: 1500 })

    // 延迟返回
    setTimeout(() => {
      const pages = getCurrentPages()
      if (pages.length > 1) {
        wx.navigateBack({ delta: 1 })
      } else {
        wx.switchTab({ url: '/pages/mine/mine' })
      }
    }, 1500)
  },

  // ========== 协议 ==========
  onShowAgreement(e) {
    const type = e.currentTarget.dataset.type
    const titles = {
      service: '用户服务协议',
      privacy: '隐私政策'
    }
    wx.showToast({ title: `${titles[type]}页面开发中`, icon: 'none' })
    // TODO: 跳转到协议详情页
    // wx.navigateTo({ url: `/pages/agreement/agreement?type=${type}` })
  },

  // ========== 生命周期 ==========
  onUnload() {
    // 清除倒计时
    if (this.timerId) {
      clearInterval(this.timerId)
    }
  },

  // ========== 分享 ==========
  onShareAppMessage() {
    return {
      title: '伊家人酒店 - 品质之选',
      path: '/pages/index/index',
      imageUrl: '/images/share-hotel.png'
    }
  }
})
