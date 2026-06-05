const app = getApp()
const api = require('../../utils/api')
const C = require('../../utils/const')

Page({
  data: {
    roomId: '',
    room: null,
    loading: true,
    swiperCurrent: 0,
    images: [],
    selectedDatePrice: 0,

    // 设施标签
    facilities: [],

    // 价格日历
    calYear: 2024,
    calMonth: 6,
    calDays: []
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ roomId: options.id })
      this.loadRoomDetail(options.id)
    }
  },

  loadRoomDetail(roomId) {
    const that = this
    const hotelId = app.globalData.currentStore.id
    this.setData({ loading: true })

    api.get(`/api/hotels/${hotelId}/rooms/${roomId}`)
      .then(room => {
        const images = room.images && room.images.length > 0
          ? room.images
          : [
              `/images/room-${room.type || 'double'}-1.png`,
              `/images/room-${room.type || 'double'}-2.png`,
              `/images/room-${room.type || 'double'}-3.png`,
              `/images/room-${room.type || 'double'}-4.png`
            ]

        const facilities = room.facilities
          ? room.facilities.map(f => ({ icon: f.icon || '✨', label: f.label || f }))
          : [
              { icon: '🛏️', label: '金可儿床垫' },
              { icon: '📺', label: '55寸电视' },
              { icon: '📶', label: '免费WiFi' },
              { icon: '❄️', label: '独立空调' },
              { icon: '🚿', label: '干湿分离' },
              { icon: '🪟', label: room.window ? '有窗' : '无窗' },
              { icon: '🍳', label: room.breakfast ? '含早餐' : '不含早' },
              { icon: '👥', label: `最多${room.maxGuests || 2}人` }
            ]

        const now = new Date()
        that.setData({
          room, images, facilities,
          loading: false,
          calYear: now.getFullYear(),
          calMonth: now.getMonth() + 1,
          selectedDatePrice: room.price || 0
        })
        that.buildPriceCalendar()
      })
      .catch(err => {
        if (C.DEV_MODE) console.error('[Room] 加载房型详情失败:', err)
        that.setData({ loading: false })
        wx.showToast({ title: '加载失败，请重试', icon: 'none' })
      })
  },

  // ========== 价格日历 ==========
  buildPriceCalendar() {
    const { calYear, calMonth, room } = this.data
    if (!room) return

    const firstDay = new Date(calYear, calMonth - 1, 1)
    const lastDay = new Date(calYear, calMonth, 0)
    const daysInMonth = lastDay.getDate()
    const startWeekDay = firstDay.getDay()

    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayStr = this.fmtDate(today)

    // Generate random-ish but somewhat realistic price variations
    const seed = (calYear * 100 + calMonth) * 7 + (room.id || 101)
    const pseudoRandom = (d) => {
      const n = (seed * d * 13 + d * 7) % 100
      return n
    }

    const days = []
    for (let i = 0; i < startWeekDay; i++) {
      days.push({ day: '', disabled: true })
    }

    for (let i = 1; i <= daysInMonth; i++) {
      const dateObj = new Date(calYear, calMonth - 1, i)
      const dateStr = this.fmtDate(dateObj)
      const isPast = dateObj < today
      const dayOfWeek = dateObj.getDay()

      // Weekend premium
      let priceVariation = 0
      if (dayOfWeek === 0 || dayOfWeek === 6) {
        priceVariation = Math.floor(room.price * 0.15) // 15% weekend premium
      }

      // Some random daily variation
      const r = pseudoRandom(i)
      if (r < 20) priceVariation = -Math.floor(room.price * 0.08)   // discount day
      else if (r > 80) priceVariation = Math.floor(room.price * 0.12) // premium day

      const dayPrice = room.price + priceVariation

      let priceLevel = 'mid'
      if (dayPrice <= room.price - 20) priceLevel = 'low'
      else if (dayPrice >= room.price + 30) priceLevel = 'high'

      days.push({
        day: i,
        disabled: isPast,
        date: dateStr,
        isToday: dateStr === todayStr,
        price: dayPrice,
        priceLevel
      })
    }

    this.setData({ calDays: days })
  },

  fmtDate(d) {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  },

  prevCalMonth() {
    let { calYear, calMonth } = this.data
    if (calMonth === 1) {
      this.setData({ calYear: calYear - 1, calMonth: 12 })
    } else {
      this.setData({ calMonth: calMonth - 1 })
    }
    setTimeout(() => this.buildPriceCalendar(), 50)
  },

  nextCalMonth() {
    let { calYear, calMonth } = this.data
    if (calMonth === 12) {
      this.setData({ calYear: calYear + 1, calMonth: 1 })
    } else {
      this.setData({ calMonth: calMonth + 1 })
    }
    setTimeout(() => this.buildPriceCalendar(), 50)
  },

  onCalDayTap(e) {
    const { date, disabled } = e.currentTarget.dataset
    if (disabled) return
    const day = this.data.calDays.find(d => d.date === date)
    if (day && day.price) {
      this.setData({ selectedDatePrice: day.price })
      wx.showToast({ title: `${date} ¥${day.price}/晚`, icon: 'none' })
    }
  },

  // ========== 图片 ==========
  onSwiperChange(e) {
    this.setData({ swiperCurrent: e.detail.current })
  },

  onImageTap(e) {
    const urls = this.data.images
    const current = e.currentTarget.dataset.index
    wx.previewImage({ urls, current: urls[current] })
  },

  // ========== 预订 ==========
  onBook() {
    const { room } = this.data
    wx.navigateTo({
      url: `/pages/booking/booking?roomId=${room.id}&roomName=${encodeURIComponent(room.name)}&price=${room.price}`
    })
  },

  // ========== 联系客服 ==========
  onContact() {
    wx.makePhoneCall({
      phoneNumber: app.globalData.currentStore.phone || '0571-88886666'
    })
  }
})
