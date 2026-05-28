const app = getApp()

Page({
  data: {
    // 当前标签
    currentTab: 'all', // all | pending | paid | completed | cancelled
    tabs: [
      { key: 'all', label: '全部' },
      { key: 'pending', label: '待支付' },
      { key: 'paid', label: '已支付' },
      { key: 'completed', label: '已完成' },
      { key: 'cancelled', label: '已取消' }
    ],
    // 订单列表
    orders: [],
    // 加载状态
    loading: true,
    hasMore: true,
    page: 1
  },

  onLoad() {
    this.loadOrders()
  },

  onShow() {
    // 每次显示时刷新
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

    // TODO: app.request({ url: '/orders', data: { status: currentTab, page } })
    // 模拟订单数据
    const mockOrders = [
      {
        id: 'YD20240528001',
        roomName: '雅致大床房',
        roomImage: '/images/room-double.png',
        storeName: '伊家人酒店·西湖店',
        checkInDate: '2024-05-28',
        checkOutDate: '2024-05-30',
        nights: 2,
        roomCount: 1,
        guestName: '陈先生',
        price: 298,
        totalPrice: 596,
        status: 'paid',
        statusLabel: '已支付',
        createTime: '2024-05-27 14:30',
        roomNumber: '806'
      },
      {
        id: 'YD20240525002',
        roomName: '尊享套房',
        roomImage: '/images/room-suite.png',
        storeName: '伊家人酒店·西湖店',
        checkInDate: '2024-06-10',
        checkOutDate: '2024-06-12',
        nights: 2,
        roomCount: 1,
        guestName: '陈先生',
        price: 598,
        totalPrice: 1196,
        status: 'pending',
        statusLabel: '待支付',
        createTime: '2024-05-25 09:15',
        remainTime: 1800 // 剩余支付时间（秒）
      },
      {
        id: 'YD20240520003',
        roomName: '豪华双床房',
        roomImage: '/images/room-twin.png',
        storeName: '伊家人酒店·钱江店',
        checkInDate: '2024-05-20',
        checkOutDate: '2024-05-22',
        nights: 2,
        roomCount: 1,
        guestName: '陈先生',
        price: 368,
        totalPrice: 736,
        status: 'completed',
        statusLabel: '已完成',
        createTime: '2024-05-18 16:00',
        roomNumber: '1206'
      },
      {
        id: 'YD20240515004',
        roomName: '亲子家庭房',
        roomImage: '/images/room-family.png',
        storeName: '伊家人酒店·西溪店',
        checkInDate: '2024-05-15',
        checkOutDate: '2024-05-16',
        nights: 1,
        roomCount: 1,
        guestName: '陈先生',
        price: 428,
        totalPrice: 428,
        status: 'cancelled',
        statusLabel: '已取消',
        createTime: '2024-05-14 10:30',
        cancelTime: '2024-05-14 20:00'
      }
    ]

    // 按tab过滤
    let filtered = mockOrders
    if (currentTab !== 'all') {
      filtered = mockOrders.filter(o => o.status === currentTab)
    }

    setTimeout(() => {
      that.setData({
        orders: page === 1 ? filtered : [...that.data.orders, ...filtered],
        loading: false,
        hasMore: false // 模拟无更多
      })
    }, 500)
  },

  // ========== 订单操作 ==========
  onOrderTap(e) {
    const order = e.currentTarget.dataset.order
    if (order.status === 'paid' || order.status === 'completed') {
      // 跳转入住页面
      wx.navigateTo({ url: `/pages/checkin/checkin?orderId=${order.id}` })
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
          // TODO: 调支付接口
          wx.showLoading({ title: '支付中...' })
          setTimeout(() => {
            wx.hideLoading()
            wx.showToast({ title: '支付成功', icon: 'success' })
            this.loadOrders()
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
          // TODO: app.request({ url: `/orders/${orderId}/cancel`, method: 'POST' })
          wx.showToast({ title: '订单已取消', icon: 'success' })
          this.loadOrders()
        }
      }
    })
  },

  onGoCheckin(e) {
    const order = e.currentTarget.dataset.order
    wx.navigateTo({ url: `/pages/checkin/checkin?orderId=${order.id}` })
  }
})
