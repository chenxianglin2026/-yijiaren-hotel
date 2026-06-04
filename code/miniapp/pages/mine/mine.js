const app = getApp()
const api = require('../../utils/api')
const C = require('../../utils/const')

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

    // 收藏数量
    favoriteCount: 0,

    // 功能菜单
    menus: [
      [
        { icon: '📋', label: '我的订单', desc: '查看全部订单', url: '/pages/orders/orders', badge: '' },
        { icon: '🎫', label: '优惠券', desc: '3张可用', url: '', badge: '3' },
        { icon: '⭐', label: '我的收藏', desc: '收藏的酒店', url: '', badge: '', handler: 'goFavorites' }
      ],
      [
        { icon: '🏨', label: '门店详情', desc: '查看当前门店', url: '', badge: '', handler: 'goHotel' },
        { icon: '💬', label: '在线客服', desc: '联系酒店管家', url: '', badge: '', handler: 'contactService' },
        { icon: '📞', label: '紧急电话', desc: '一键拨打前台', url: '', badge: '', handler: 'callFrontDesk' }
      ],
      [
        { icon: '📝', label: '常用入住人', desc: '管理入住人信息', url: '', badge: '' },
        { icon: '⚙️', label: '设置', desc: '账号与偏好设置', url: '', badge: '', handler: 'goSettings' },
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
    this.loadFavoriteCount()
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
      // 检查本地存储
      const localToken = wx.getStorageSync('token')
      if (localToken) {
        app.globalData.token = localToken
        this.setData({
          isLoggedIn: true,
          userInfo: wx.getStorageSync('userInfo') || { nickName: '酒店住客', avatarUrl: '' },
          phoneNumber: app.globalData.phoneNumber || '138****8888'
        })
        this.loadOrderStats()
      } else {
        this.setData({
          isLoggedIn: false,
          userInfo: null,
          phoneNumber: ''
        })
      }
    }
  },

  loadFavoriteCount() {
    const favorites = wx.getStorageSync('favorites') || []
    this.setData({ favoriteCount: favorites.length })
  },

  loadOrderStats() {
    if (C.DEV_MODE) {
      this.setData({
        orderStats: { pending: 1, paid: 1, completed: 1 }
      })
      return
    }
    // 生产环境：调用真实统计接口
    api.get('/api/orders', { page: 1, page_size: 1 })
      .then(res => {
        this.setData({
          orderStats: {
            pending: res.pending_count || 0,
            paid: res.paid_count || 0,
            completed: res.completed_count || 0
          }
        })
      })
      .catch(() => {})
  },

  // ========== 登录 ==========
  onLogin() {
    // 跳转到独立登录页面
    wx.navigateTo({ url: '/pages/login/login' })
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
    const { url, label, handler } = e.currentTarget.dataset

    // 优先使用 handler
    if (handler && this[handler]) {
      this[handler]()
      return
    }

    if (url) {
      wx.navigateTo({ url })
    } else {
      switch (label) {
        case '在线客服':
          this.contactService()
          break
        case '紧急电话':
          this.callFrontDesk()
          break
        case '设置':
          this.goSettings()
          break
        case '帮助中心':
          wx.showToast({ title: '帮助中心开发中', icon: 'none' })
          break
        case '优惠券':
          wx.showToast({ title: '优惠券页面开发中', icon: 'none' })
          break
        case '常用入住人':
          wx.showToast({ title: '入住人管理开发中', icon: 'none' })
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

  // ========== 新增功能处理方法 ==========

  // 查看门店详情
  goHotel() {
    const store = app.globalData.currentStore
    const storeId = store ? store.id : 1
    wx.navigateTo({ url: `/pages/hotel/hotel?id=${storeId}` })
  },

  // 我的收藏
  goFavorites() {
    const favorites = wx.getStorageSync('favorites') || []
    if (favorites.length === 0) {
      wx.showToast({ title: '暂无收藏的门店', icon: 'none' })
      return
    }
    // 跳转到第一个收藏的门店
    wx.navigateTo({ url: `/pages/hotel/hotel?id=${favorites[0]}` })
  },

  // 在线客服
  contactService() {
    // 尝试打开客服会话
    wx.showActionSheet({
      itemList: ['在线客服', '电话咨询', '添加管家微信'],
      success(res) {
        switch (res.tapIndex) {
          case 0:
            wx.showToast({ title: '客服功能开发中', icon: 'none' })
            break
          case 1:
            const store = app.globalData.currentStore
            wx.makePhoneCall({
              phoneNumber: (store && store.phone) || '0571-88886666'
            })
            break
          case 2:
            wx.showToast({ title: '管家微信功能开发中', icon: 'none' })
            break
        }
      }
    })
  },

  // 紧急电话
  callFrontDesk() {
    const store = app.globalData.currentStore
    wx.makePhoneCall({
      phoneNumber: (store && store.phone) || '0571-88886666'
    })
  },

  // 设置页面
  goSettings() {
    wx.showActionSheet({
      itemList: ['账号安全', '消息通知', '清除缓存', '关于我们'],
      success(res) {
        switch (res.tapIndex) {
          case 0:
            wx.showToast({ title: '账号安全设置开发中', icon: 'none' })
            break
          case 1:
            wx.showToast({ title: '消息通知设置开发中', icon: 'none' })
            break
          case 2:
            wx.showModal({
              title: '清除缓存',
              content: '确定要清除本地缓存吗？不会影响您的订单和账号信息。',
              confirmColor: '#c8a052',
              success(modalRes) {
                if (modalRes.confirm) {
                  wx.clearStorageSync()
                  // 保留必要的 token
                  const token = app.globalData.token
                  if (token) {
                    wx.setStorageSync('token', token)
                  }
                  wx.showToast({ title: '缓存已清除', icon: 'success' })
                }
              }
            })
            break
          case 3:
            wx.showModal({
              title: '关于伊家人酒店',
              content: '版本：v1.0.0\n\n伊家人酒店致力于为您提供温馨舒适的住宿体验。\n\n旗下拥有西湖店、钱江店、西溪店等多家精品酒店。',
              showCancel: false,
              confirmText: '知道了',
              confirmColor: '#c8a052'
            })
            break
        }
      }
    })
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
