const app = getApp()

Page({
  data: {
    roomId: '',
    roomName: '',
    roomPrice: 0,
    room: null,

    // 入住离店日期
    checkInDate: '',
    checkOutDate: '',
    checkInWeek: '',
    checkOutWeek: '',
    nights: 1,

    // 日历相关
    today: '',
    calendarOpen: false,
    calendarType: '', // 'checkin' | 'checkout'
    calendarYear: 2024,
    calendarMonth: 5,
    calendarDays: [],

    // 房间数量
    roomCount: 1,
    // 入住人信息
    guestName: '',
    guestPhone: '',
    // 备注
    remark: '',

    // 费用明细
    roomTotal: 0,
    serviceFee: 0,
    discount: 0,
    totalPrice: 0,

    // 预计抵店时间
    arrivalTime: '14:00',
    arrivalTimes: ['12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00'],

    // 是否展示取消政策
    showPolicy: false
  },

  onLoad(options) {
    const roomId = options.roomId || ''
    const roomName = decodeURIComponent(options.roomName || '')
    const price = parseFloat(options.price) || 0

    // 默认日期：今天入住，明天离店
    const today = new Date()
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)

    const fmt = (d) => {
      const y = d.getFullYear()
      const m = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${y}-${m}-${day}`
    }

    const weekMap = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

    const checkInDate = fmt(today)
    const checkOutDate = fmt(tomorrow)
    const checkInWeek = weekMap[today.getDay()]
    const checkOutWeek = weekMap[tomorrow.getDay()]

    this.setData({
      roomId,
      roomName,
      roomPrice: price,
      checkInDate,
      checkOutDate,
      checkInWeek,
      checkOutWeek,
      nights: 1,
      today: checkInDate,
      calendarYear: today.getFullYear(),
      calendarMonth: today.getMonth() + 1
    })

    this.loadRoomBrief(roomId)
    this.calcPrice()
    this.buildCalendar()
  },

  loadRoomBrief(roomId) {
    // TODO: app.request({ url: `/rooms/${roomId}/brief` })
    const mock = {
      id: parseInt(roomId) || 101,
      name: this.data.roomName || '雅致大床房',
      image: '/images/room-double.png',
      bed: '1.8m大床',
      area: '28㎡',
      window: true,
      breakfast: true,
      maxGuests: 2,
      price: this.data.roomPrice || 298
    }
    this.setData({ room: mock })
  },

  // ========== 日历 ==========
  buildCalendar() {
    const { calendarYear, calendarMonth } = this.data
    const firstDay = new Date(calendarYear, calendarMonth - 1, 1)
    const lastDay = new Date(calendarYear, calendarMonth, 0)
    const daysInMonth = lastDay.getDate()
    const startWeekDay = firstDay.getDay()

    const days = []
    // 填充前面的空白
    for (let i = 0; i < startWeekDay; i++) {
      days.push({ day: '', disabled: true })
    }
    // 填充日期
    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`
    for (let i = 1; i <= daysInMonth; i++) {
      const dateStr = `${calendarYear}-${String(calendarMonth).padStart(2,'0')}-${String(i).padStart(2,'0')}`
      const isPast = dateStr < todayStr
      days.push({
        day: i,
        disabled: isPast,
        date: dateStr,
        isToday: dateStr === todayStr
      })
    }

    this.setData({ calendarDays: days })
  },

  openCalendar(e) {
    const type = e.currentTarget.dataset.type
    this.setData({ calendarOpen: true, calendarType: type })
  },

  closeCalendar() {
    this.setData({ calendarOpen: false })
  },

  onDayTap(e) {
    const { date, disabled } = e.currentTarget.dataset
    if (disabled) return

    const { calendarType, checkInDate, checkOutDate } = this.data
    const weekMap = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    const d = new Date(date)
    const week = weekMap[d.getDay()]

    if (calendarType === 'checkin') {
      // 如果选择的入住日期 >= 当前离店日期，自动调整离店日期为入住日+1
      if (date >= checkOutDate) {
        const nextDay = new Date(d)
        nextDay.setDate(nextDay.getDate() + 1)
        const y = nextDay.getFullYear()
        const m = String(nextDay.getMonth() + 1).padStart(2, '0')
        const day = String(nextDay.getDate()).padStart(2, '0')
        const newOut = `${y}-${m}-${day}`
        this.setData({
          checkInDate: date,
          checkInWeek: week,
          checkOutDate: newOut,
          checkOutWeek: weekMap[nextDay.getDay()]
        })
      } else {
        this.setData({
          checkInDate: date,
          checkInWeek: week
        })
      }
    } else {
      // 离店日期必须 > 入住日期
      if (date <= checkInDate) {
        wx.showToast({ title: '离店日期需晚于入住日期', icon: 'none' })
        return
      }
      this.setData({
        checkOutDate: date,
        checkOutWeek: week
      })
    }

    this.calcNights()
    this.calcPrice()
    this.closeCalendar()
  },

  prevMonth() {
    const { calendarYear, calendarMonth } = this.data
    if (calendarMonth === 1) {
      this.setData({ calendarYear: calendarYear - 1, calendarMonth: 12 })
    } else {
      this.setData({ calendarMonth: calendarMonth - 1 })
    }
    this.buildCalendar()
  },

  nextMonth() {
    const { calendarYear, calendarMonth } = this.data
    if (calendarMonth === 12) {
      this.setData({ calendarYear: calendarYear + 1, calendarMonth: 1 })
    } else {
      this.setData({ calendarMonth: calendarMonth + 1 })
    }
    this.buildCalendar()
  },

  calcNights() {
    const d1 = new Date(this.data.checkInDate)
    const d2 = new Date(this.data.checkOutDate)
    const nights = Math.round((d2.getTime() - d1.getTime()) / (1000 * 60 * 60 * 24))
    this.setData({ nights: Math.max(1, nights) })
  },

  // ========== 数量 ==========
  increaseRoom() {
    const count = Math.min(this.data.roomCount + 1, 5)
    this.setData({ roomCount: count })
    this.calcPrice()
  },

  decreaseRoom() {
    const count = Math.max(this.data.roomCount - 1, 1)
    this.setData({ roomCount: count })
    this.calcPrice()
  },

  // ========== 费用计算 ==========
  calcPrice() {
    const { roomPrice, nights, roomCount } = this.data
    const roomTotal = roomPrice * nights * roomCount
    const serviceFee = 0 // 免服务费
    const discount = nights >= 3 ? Math.floor(roomTotal * 0.1) : 0 // 连住3晚9折
    const totalPrice = roomTotal - discount + serviceFee

    this.setData({
      roomTotal,
      serviceFee,
      discount,
      totalPrice
    })
  },

  // ========== 表单输入 ==========
  onNameInput(e) {
    this.setData({ guestName: e.detail.value })
  },

  onPhoneInput(e) {
    this.setData({ guestPhone: e.detail.value })
  },

  onRemarkInput(e) {
    this.setData({ remark: e.detail.value })
  },

  onArrivalChange(e) {
    this.setData({ arrivalTime: this.data.arrivalTimes[e.detail.value] })
  },

  // ========== 提交订单 ==========
  submitOrder() {
    const { guestName, guestPhone, checkInDate, checkOutDate, roomCount, totalPrice, roomId } = this.data

    if (!guestName.trim()) {
      wx.showToast({ title: '请填写入住人姓名', icon: 'none' })
      return
    }
    if (!guestPhone.trim() || !/^1\d{10}$/.test(guestPhone)) {
      wx.showToast({ title: '请填写正确的手机号', icon: 'none' })
      return
    }

    wx.showModal({
      title: '确认预订',
      content: `${guestName}，确认预订${checkInDate}至${checkOutDate}，共${totalPrice}元？`,
      confirmText: '确认支付',
      success: (res) => {
        if (res.confirm) {
          // TODO: app.request({ url: '/orders', method: 'POST', data: {...} })
          wx.showLoading({ title: '提交中...' })
          setTimeout(() => {
            wx.hideLoading()
            wx.showToast({ title: '预订成功！', icon: 'success' })
            setTimeout(() => {
              wx.switchTab({ url: '/pages/orders/orders' })
            }, 1500)
          }, 1000)
        }
      }
    })
  },

  togglePolicy() {
    this.setData({ showPolicy: !this.data.showPolicy })
  }
})
