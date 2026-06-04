const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    currentTab: 'all',
    tabs: [
      { key: 'all', label: '全部', count: 0 },
      { key: 'pending', label: '待付款', count: 0 },
      { key: 'paid', label: '已预订', count: 0 },
      { key: 'staying', label: '入住中', count: 0 },
      { key: 'completed', label: '已完成', count: 0 }
    ],
    orders: [],
    loading: true,
    hasMore: true,
    page: 1,

    // 订单统计
    summary: {
      pending: 0,
      booked: 0,
      staying: 0,
      completed: 0
    }
  },

  onLoad() {
    this.loadOrders()
  },

  onShow() {
    // Tab页每次显示时刷新
  },

  onPullDownRefresh() {
    this.setData({ page: 1, orders: [] })
    this.loadOrders().then(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    if (this.data.hasMore) {
      this.loadOrders()
    }
  },

  // ========== Tab切换 ==========
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ currentTab: tab, page: 1, orders: [] })
    this.loadOrders()
  },

  // ========== 加载订单 ==========
  loadOrders() {
    const that = this
    const { currentTab, page } = this.data
    this.setData({ loading: true })

    const params = { page, page_size: 20 }
    if (currentTab !== 'all') {
      params.status = currentTab
    }

    api.get('/api/orders', params)
      .then(res => {
        const orders = res.items || res.orders || res || []
        const list = Array.isArray(orders) ? orders : []

        // 计算各状态数量
        const allOrders = page === 1 ? list : list  // 第一页时重新算tab counts
        const counts = {}
        if (page === 1 && currentTab === 'all') {
          // 如果是全部tab第一页，后端可能返回各状态计数
          counts.pending = res.pending_count || 0
          counts.paid = res.paid_count || 0
          counts.staying = res.staying_count || 0
          counts.completed = res.completed_count || 0
        }

        const tabs = that.data.tabs.map(t => ({
          ...t,
          count: t.key === 'all' ? (res.total || list.length) : (counts[t.key] || 0)
        }))

        that.setData({
          orders: page === 1 ? list : [...that.data.orders, ...list],
          loading: false,
          hasMore: list.length >= 20,
          tabs,
          summary: {
            pending: counts.pending || 0,
            booked: counts.paid || 0,
            staying: counts.staying || 0,
            completed: counts.completed || 0
          }
        })
      })
      .catch(err => {
        console.error('[Orders] 加载订单失败:', err)
        that.setData({ loading: false, hasMore: false })
        wx.showToast({ title: '加载失败，请重试', icon: 'none' })
      })
  },

  // ========== 订单操作 ==========
  onOrderTap(e) {
    const order = e.currentTarget.dataset.order
    if (order.status === 'paid' || order.status === 'staying' || order.status === 'completed') {
      wx.navigateTo({ url: `/pages/checkin/checkin?orderId=${order.id}` })
    } else if (order.status === 'pending') {
      this.onPayOrder(e)
    }
  },

  onPayOrder(e) {
    const order = e.currentTarget.dataset.order
    wx.showModal({
      title: '确认支付',
      content: `支付 ¥${order.totalPrice} 完成预订？`,
      confirmText: '立即支付',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '支付中...' })
          setTimeout(() => {
            wx.hideLoading()
            wx.showToast({ title: '支付成功', icon: 'success' })
            // 更新订单状态
            const orders = this.data.orders.map(o => {
              if (o.id === order.id) {
                return { ...o, status: 'paid', statusLabel: '已预订' }
              }
              return o
            })
            this.setData({ orders })
          }, 1000)
        }
      }
    })
  },

  onCancelOrder(e) {
    const orderId = e.currentTarget.dataset.id
    wx.showModal({
      title: '取消订单',
      content: '确定要取消此订单吗？',
      confirmColor: '#C56C6C',
      success: (res) => {
        if (res.confirm) {
          wx.showToast({ title: '订单已取消', icon: 'success' })
          const orders = this.data.orders.map(o => {
            if (o.id === orderId) {
              return { ...o, status: 'cancelled', statusLabel: '已取消' }
            }
            return o
          })
          this.setData({ orders })
        }
      }
    })
  },

  onGoCheckin(e) {
    const order = e.currentTarget.dataset.order
    wx.navigateTo({ url: `/pages/checkin/checkin?orderId=${order.id}` })
  },

  onContactHotel() {
    wx.makePhoneCall({
      phoneNumber: app.globalData.currentStore.phone || '0571-88886666'
    })
  },

  onViewDetail(e) {
    const order = e.currentTarget.dataset.order
    wx.navigateTo({ url: `/pages/checkin/checkin?orderId=${order.id}` })
  },

  onBookAgain(e) {
    const order = e.currentTarget.dataset.order
    // 从订单信息提取roomId (简化处理)
    wx.switchTab({ url: '/pages/index/index' })
  },

  onGoHome() {
    wx.switchTab({ url: '/pages/index/index' })
  }
})
