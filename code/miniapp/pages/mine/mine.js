const app = getApp()

Page({
  data: {
    // 用户信息
    isLoggedIn: false,
    userInfo: null,
    phoneNumber: '',

    // 订单统计
    orderStats: {
      pending: 0,
      paid: 0,
      completed: 0
    },

    // 会员信息
    memberLevel: '普通会员',
    memberPoints: 280,
    memberCoupons: 3,

    // 功能菜单
    menus: [
      [
        { icon: '📋', label: '我的订单', desc: '查看全部订单', url: '/pages/orders/orders', badge: '' },
        { icon: '🎫', label: '优惠券', desc: '3张可用', url: '', badge: '3' },
        { icon: '⭐', label: '我的收藏', desc: '收藏的酒店', url: '', badge: '' }
      ],
      [
        { icon: '🏨', label: '浏览记录', desc: '最近浏览的房型', url: '', badge: '' },
        { icon: '💬', label: '在线客服', desc: '联系酒店管家', url: '', badge: '' },
        { icon: '📞', label: '紧急电话', desc: '一键拨打前台', url: '', badge: '' }
      ],
      [
        { icon: '📝', label: '常用入住人', desc: '管理入住人信息', url: '', badge: '' },
        { icon: '⚙️', label: '设置', desc: '账号与偏好设置', url: '', badge: '' },
        { icon: '❓', label: '帮助中心', desc: '常见问题与指引', url: '', badge: '' }
      ]
    ],

    // 快捷操作
    quickActions: [
      { icon: '📅', label: '我的行程' },
      { icon: '💳', label: '发票管理' },
      { icon: '📮', label: '意见反馈' },
      { icon: '🎁', label: '邀请有礼' }
    ]
  },

  onLoad() {
    this.checkLoginStatus()
  },

  onShow() {
    // 刷新登录状态和数据
    this.checkLoginStatus()
  },

  checkLoginStatus() {
    const token = app.globalData.token
    const userInfo = app.globalData.userInfo
    const phoneNumber = app.globalData.phoneNumber

    if (token && (userInfo || phoneNumber)) {
      this.setData({
        isLoggedIn: true,
        userInfo: userInfo || { nickName: '酒店住客', avatarUrl: '' },
        phoneNumber: phoneNumber || '138****8888'
      })
      this.loadOrderStats()
    } else {
      this.setData({
        isLoggedIn: false,
        userInfo: null,
        phoneNumber: ''
      })
    }
  },

  loadOrderStats() {
    // TODO: app.request({ url: '/orders/stats' })
    this.setData({
      orderStats: {
        pending: 1,
        paid: 1,
        completed: 1
      }
    })
  },

  // ========== 登录 ==========
  onLogin() {
    const that = this
    wx.getUserProfile({
      desc: '用于完善个人资料',
      success(res) {
        const userInfo = res.userInfo
        app.globalData.userInfo = userInfo
        app.wxLogin((success) => {
          if (success) {
            that.setData({
              isLoggedIn: true,
              userInfo,
              phoneNumber: app.globalData.phoneNumber || ''
            })
            that.loadOrderStats()
          }
        })
      },
      fail() {
        // 用户拒绝授权，尝试静默登录
        app.wxLogin((success) => {
          if (success) {
            that.setData({
              isLoggedIn: true,
              userInfo: { nickName: '酒店住客', avatarUrl: '' },
              phoneNumber: app.globalData.phoneNumber || ''
            })
            that.loadOrderStats()
          }
        })
      }
    })
  },

  getPhoneNumber(e) {
    const that = this
    app.getPhoneNumber(e, (success, phone) => {
      if (success && phone) {
        that.setData({ phoneNumber: phone })
      }
    })
  },

  // ========== 菜单点击 ==========
  onMenuTap(e) {
    const { url, label } = e.currentTarget.dataset
    if (url) {
      wx.navigateTo({ url })
    } else {
      switch (label) {
        case '在线客服':
          wx.showToast({ title: '客服功能开发中', icon: 'none' })
          break
        case '紧急电话':
          wx.makePhoneCall({
            phoneNumber: app.globalData.currentStore.phone || '0571-88886666'
          })
          break
        case '设置':
          wx.showToast({ title: '设置页面开发中', icon: 'none' })
          break
        case '帮助中心':
          wx.showToast({ title: '帮助中心开发中', icon: 'none' })
          break
        default:
          wx.showToast({ title: '功能开发中', icon: 'none' })
      }
    }
  },

  onActionTap(e) {
    const { label } = e.currentTarget.dataset
    wx.showToast({ title: `${label}开发中`, icon: 'none' })
  },

  // ========== 退出登录 ==========
  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      confirmColor: '#C56C6C',
      success: (res) => {
        if (res.confirm) {
          app.globalData.token = ''
          app.globalData.userInfo = null
          app.globalData.phoneNumber = ''
          wx.removeStorageSync('token')
          this.setData({
            isLoggedIn: false,
            userInfo: null,
            phoneNumber: '',
            orderStats: { pending: 0, paid: 0, completed: 0 }
          })
          wx.showToast({ title: '已退出', icon: 'success' })
        }
      }
    })
  }
})
