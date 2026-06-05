const app = getApp()
const api = require('../../utils/api')
const C = require('../../utils/const')

Page({
  data: {
    // 订单信息
    order: null,
    loading: true,
    hasActiveOrder: false,
    checkinStatus: 'active',

    // 开锁方式: ble | code | qr
    unlockMethod: 'ble',

    // 门锁状态
    lockStatus: 'locked',
    lockCode: '',
    showCode: false,

    // 蓝牙
    bleAvailable: false,
    bleConnecting: false,

    // 二维码倒计时
    qrTimer: 0,
    qrInterval: null,

    // 身份证
    idCardFront: '',
    idCardBack: '',
    idCardUploaded: false,

    // 人脸识别
    faceVerified: false,

    // WiFi
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
    const orderId = options.orderId || ''
    this.loadActiveOrder(orderId)
  },

  onShow() {
    this.checkBluetooth()
  },

  onUnload() {
    if (this.data.qrInterval) {
      clearInterval(this.data.qrInterval)
    }
  },

  loadActiveOrder(orderId) {
    const that = this
    this.setData({ loading: true })

    api.get(`/api/checkin/${orderId}`)
      .then(order => {
        const lockCode = order.lock_code || String(Math.floor(100000 + Math.random() * 900000))
        const normalized = {
          ...order,
          lockCode,
          wifiName: order.wifi_name || 'YJR-Hotel',
          wifiPassword: order.wifi_password || '',
          hotelPhone: order.hotel_phone || order.phone || '0571-88886666'
        }

        that.setData({
          order: normalized,
          roomNumber: order.room_number || order.roomNumber || '',
          floor: order.floor || '',
          wifiName: normalized.wifiName,
          wifiPassword: normalized.wifiPassword,
          lockCode,
          hasActiveOrder: true,
          loading: false,
          checkinStatus: 'active'
        })

        that.startQrTimer()
      })
      .catch(err => {
        if (C.DEV_MODE) console.error('[Checkin] 加载入住信息失败:', err)
        that.setData({ loading: false, hasActiveOrder: false })
        wx.showToast({ title: '暂无入住信息', icon: 'none' })
      })
  },

  // ========== 开锁方式切换 ==========
  switchUnlockMethod(e) {
    const method = e.currentTarget.dataset.method
    this.setData({ unlockMethod: method })

    if (method === 'qr') {
      this.startQrTimer()
    } else {
      this.stopQrTimer()
    }
  },

  // ========== 身份证上传 ==========
  uploadIdCard(e) {
    const side = e.currentTarget.dataset.side
    const that = this

    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['camera', 'album'],
      success(res) {
        const tempFilePath = res.tempFilePaths[0]
        if (side === 'front') {
          that.setData({ idCardFront: tempFilePath })
        } else {
          that.setData({ idCardBack: tempFilePath })
        }

        // 检查是否都已上传
        const { idCardFront, idCardBack } = that.data
        if (idCardFront && idCardBack) {
          that.setData({ idCardUploaded: true })
          wx.showToast({ title: '身份证上传完成', icon: 'success' })
        } else {
          wx.showToast({ title: `${side === 'front' ? '正面' : '反面'}上传成功`, icon: 'success' })
        }
      },
      fail() {
        wx.showToast({ title: '取消上传', icon: 'none' })
      }
    })
  },

  // ========== 人脸识别 ==========
  startFaceVerify() {
    const that = this
    wx.showModal({
      title: '人脸识别验证',
      content: '即将开始人脸识别，请将面部对准屏幕框内，根据提示完成眨眼、张嘴等动作。',
      confirmText: '开始验证',
      success(res) {
        if (res.confirm) {
          wx.showLoading({ title: '验证中...', mask: true })
          // 模拟人脸识别过程
          setTimeout(() => {
            wx.hideLoading()
            that.setData({ faceVerified: true })
            wx.showToast({ title: '身份验证通过 ✅', icon: 'success' })
          }, 2000)
        }
      }
    })
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

  bleUnlock() {
    const that = this
    this.setData({ lockStatus: 'unlocking', bleConnecting: true })

    // 模拟蓝牙连接开锁过程
    setTimeout(() => {
      that.setData({
        lockStatus: 'unlocked',
        bleConnecting: false
      })
      wx.vibrateShort({ type: 'medium' })
      wx.showToast({ title: '门锁已打开 🔓', icon: 'success' })

      // 10秒后自动恢复锁定状态
      setTimeout(() => {
        that.setData({ lockStatus: 'locked' })
      }, 10000)
    }, 1500)
  },

  // ========== 密码开锁 ==========
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

  refreshLockCode() {
    const newCode = String(Math.floor(100000 + Math.random() * 900000))
    this.setData({ lockCode: newCode })
    wx.showToast({ title: '密码已刷新', icon: 'success' })
  },

  // ========== 二维码开锁 ==========
  startQrTimer() {
    this.stopQrTimer()
    this.setData({ qrTimer: 30 })

    const interval = setInterval(() => {
      let timer = this.data.qrTimer - 1
      if (timer <= 0) {
        timer = 30
        // 刷新二维码
      }
      this.setData({ qrTimer: timer })
    }, 1000)

    this.setData({ qrInterval: interval })
  },

  stopQrTimer() {
    if (this.data.qrInterval) {
      clearInterval(this.data.qrInterval)
      this.setData({ qrInterval: null, qrTimer: 0 })
    }
  },

  refreshQrCode() {
    this.setData({ qrTimer: 30 })
    wx.showToast({ title: '二维码已刷新', icon: 'success' })
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

  // ========== 导航 ==========
  onGoBook() {
    wx.switchTab({ url: '/pages/index/index' })
  },

  // ========== WiFi ==========
  copyWifi() {
    const { wifiName, wifiPassword } = this.data
    wx.setClipboardData({
      data: `WiFi名称：${wifiName}\nWiFi密码：${wifiPassword}`,
      success() {
        wx.showToast({ title: 'WiFi信息已复制', icon: 'success' })
      }
    })
  }
})
