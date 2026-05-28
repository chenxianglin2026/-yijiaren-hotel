const app = getApp()

Page({
  data: {
    // 订单信息
    order: null,
    loading: true,
    hasActiveOrder: false,

    // 入住状态
    checkinStatus: 'pending', // pending | active | completed
    // 门锁
    lockStatus: 'locked', // locked | unlocking | unlocked
    lockCode: '',
    showCode: false,
    // 倒计时
    codeTimer: 0,
    codeTimerText: '',

    // 蓝牙状态
    bleAvailable: false,
    bleConnecting: false,
    bleConnected: false,

    // 房间信息
    roomNumber: '',
    floor: '',
    wifiName: '',
    wifiPassword: '',

    // 酒店服务
    services: [
      { id: 1, icon: '🧹', label: '客房清洁', desc: '预约打扫服务' },
      { id: 2, icon: '🛎️', label: '客房服务', desc: '送物到房间' },
      { id: 3, icon: '🍜', label: '叫醒服务', desc: '设置叫醒时间' },
      { id: 4, icon: '📞', label: '前台电话', desc: '联系酒店前台' }
    ],

    // 附近推荐
    nearbyPlaces: [
      { name: '西湖风景区', distance: '1.2km', icon: '🏞️' },
      { name: '银泰百货', distance: '800m', icon: '🛍️' },
      { name: '地铁1号线', distance: '500m', icon: '🚇' }
    ]
  },

  onLoad(options) {
    // 可以从订单列表传过来的订单id
    const orderId = options.orderId || ''
    this.loadActiveOrder(orderId)
  },

  onShow() {
    // 检查蓝牙
    this.checkBluetooth()
  },

  loadActiveOrder(orderId) {
    const that = this
    this.setData({ loading: true })

    // TODO: app.request({ url: '/orders/active' })
    // 模拟有效订单数据
    setTimeout(() => {
      const mockOrder = {
        id: orderId || 'YD20240528001',
        roomName: '雅致大床房',
        roomNumber: '806',
        floor: '8层',
        checkInDate: '2024-05-28',
        checkOutDate: '2024-05-30',
        nights: 2,
        guestName: '陈先生',
        price: 298,
        status: 'paid',
        // 门锁密码（6位）
        lockCode: '',
        // WiFi信息
        wifiName: 'YJR-Hotel',
        wifiPassword: 'yijiaren2024',
        // 酒店电话
        hotelPhone: '0571-88886666'
      }

      // 生成动态密码（模拟）
      const lockCode = String(Math.floor(100000 + Math.random() * 900000))

      that.setData({
        order: { ...mockOrder, lockCode },
        roomNumber: mockOrder.roomNumber,
        floor: mockOrder.floor,
        wifiName: mockOrder.wifiName,
        wifiPassword: mockOrder.wifiPassword,
        hasActiveOrder: true,
        loading: false,
        checkinStatus: 'active'
      })
    }, 800)
  },

  // ========== 蓝牙 ==========
  checkBluetooth() {
    const that = this
    wx.openBluetoothAdapter({
      success() {
        that.setData({ bleAvailable: true })
      },
      fail() {
        that.setData({ bleAvailable: false })
      }
    })
  },

  connectBluetooth() {
    this.setData({ bleConnecting: true })
    // TODO: 实际蓝牙连接逻辑
    setTimeout(() => {
      this.setData({
        bleConnecting: false,
        bleConnected: true,
        lockStatus: 'unlocked'
      })
      wx.showToast({ title: '门锁已打开 🔓', icon: 'success' })
    }, 1500)
  },

  // ========== 密码锁 ==========
  toggleShowCode() {
    this.setData({ showCode: !this.data.showCode })
  },

  copyLockCode() {
    wx.setClipboardData({
      data: this.data.order.lockCode,
      success() {
        wx.showToast({ title: '密码已复制', icon: 'success' })
      }
    })
  },

  // ========== 一键开锁 ==========
  unlockDoor() {
    const that = this
    this.setData({ lockStatus: 'unlocking' })

    // 模拟开锁
    setTimeout(() => {
      that.setData({
        lockStatus: 'unlocked',
        showCode: true
      })
      wx.showToast({ title: '门锁已打开 🔓', icon: 'success' })

      // 10秒后重新锁定显示
      setTimeout(() => {
        that.setData({ lockStatus: 'locked' })
      }, 10000)
    }, 1200)
  },

  // ========== 酒店服务 ==========
  onServiceTap(e) {
    const id = e.currentTarget.dataset.id
    switch (id) {
      case 1:
        wx.showModal({
          title: '客房清洁',
          content: '是否确认预约清洁服务？',
          success: (res) => {
            if (res.confirm) {
              wx.showToast({ title: '已预约，稍后为您服务', icon: 'success' })
            }
          }
        })
        break
      case 2:
        wx.showModal({
          title: '客房服务',
          content: '将为您转接客房服务，是否继续？',
          success: (res) => {
            if (res.confirm) {
              wx.showToast({ title: '已通知，请稍候', icon: 'success' })
            }
          }
        })
        break
      case 3:
        wx.showToast({ title: '叫醒服务开发中', icon: 'none' })
        break
      case 4:
        wx.makePhoneCall({
          phoneNumber: this.data.order?.hotelPhone || '0571-88886666'
        })
        break
    }
  },

  // ========== 查看WiFi ==========
  copyWifi() {
    const { wifiName, wifiPassword } = this.data
    wx.setClipboardData({
      data: `WiFi: ${wifiName}\n密码: ${wifiPassword}`,
      success() {
        wx.showToast({ title: 'WiFi信息已复制', icon: 'success' })
      }
    })
  }
})
