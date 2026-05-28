const app = getApp()

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
        status: 'staying',
        statusLabel: '入住中',
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
        statusLabel: '待付款',
        createTime: '2024-05-25 09:15',
        remainTime: 1800
      },
      {
        id: 'YD20240523003',
        roomName: '豪华双床房',
        roomImage: '/images/room-twin.png',
        storeName: '伊家人酒店·钱江店',
        checkInDate: '2024-06-15',
        checkOutDate: '2024-06-17',
        nights: 2,
        roomCount: 1,
        guestName: '陈先生',
        price: 368,
        totalPrice: 736,
        status: 'paid',
        statusLabel: '已预订',
        createTime: '2024-05-23 11:00',
        roomNumber: ''
      },
      {
        id: 'YD20240520004',
        roomName: '舒适单人间',
        roomImage: '/images/room-single.png',
        storeName: '伊家人酒店·西溪店',
        checkInDate: '2024-05-20',
        checkOutDate: '2024-05-22',
        nights: 2,
        roomCount: 1,
        guestName: '陈先生',
        price: 198,
        totalPrice: 396,
        status: 'completed',
        statusLabel: '已完成',
        createTime: '2024-05-18 16:00',
        roomNumber: '302'
      },
      {
        id: 'YD20240515005',
        roomName: '亲子家庭房',
        roomImage: '/images/room-family.png',
        storeName: '伊家人酒店·西湖店',
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

    // 计算各状态数量
    const counts = {
      pending: mockOrders.filter(o => o.status === 'pending').length,
      paid: mockOrders.filter(o => o.status === 'paid').length,
      staying: mockOrders.filter(o => o.status === 'staying').length,
      completed: mockOrders.filter(o => o.status === 'completed').length,
      cancelled: mockOrders.filter(o => o.status === 'cancelled').length
    }

    // 更新tab计数
    const tabs = that.data.tabs.map(t => ({
      ...t,
      count: t.key === 'all' ? mockOrders.length : (counts[t.key] || 0)
    }))

    setTimeout(() => {
      that.setData({
        orders: page === 1 ? filtered : [...that.data.orders, ...filtered],
        loading: false,
        hasMore: false,
        tabs,
        summary: {
          pending: counts.pending,
          booked: counts.paid,
          staying: counts.staying,
          completed: counts.completed
        }
      })
    }, 500)
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
