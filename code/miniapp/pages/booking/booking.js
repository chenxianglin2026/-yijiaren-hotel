const app = getApp()

Page({
  data: {
    roomId: '', roomName: '', roomPrice: 0, room: null,
    checkInDate: '', checkOutDate: '', checkInWeek: '', checkOutWeek: '', nights: 1,
    today: '', calendarOpen: false, calendarType: '',
    calendarYear: 2024, calendarMonth: 6, calendarDays: [],
    roomCount: 1, guestName: '', guestPhone: '', remark: '',
    roomTotal: 0, serviceFee: 0, discount: 0, totalPrice: 0,
    arrivalTime: '14:00',
    arrivalTimes: ['12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00','20:00','21:00','22:00'],
    showPolicy: false, submitting: false, showPayModal: false, paying: false
  },

  onLoad(options) {
    const roomId = options.roomId || ''
    const roomName = decodeURIComponent(options.roomName || '')
    const price = parseFloat(options.price) || 0
    const today = new Date()
    const tomorrow = new Date(today); tomorrow.setDate(tomorrow.getDate() + 1)
    const fmt = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
    const wm = ['周日','周一','周二','周三','周四','周五','周六']
    this.setData({
      roomId, roomName, roomPrice: price,
      checkInDate: fmt(today), checkOutDate: fmt(tomorrow),
      checkInWeek: wm[today.getDay()], checkOutWeek: wm[tomorrow.getDay()],
      nights: 1, today: fmt(today),
      calendarYear: today.getFullYear(), calendarMonth: today.getMonth() + 1
    })
    this.loadRoomBrief(roomId); this.calcPrice(); this.buildCalendar()
  },

  loadRoomBrief(roomId) {
    this.setData({ room: { id: parseInt(roomId)||101, name: this.data.roomName||'雅致大床房', image:'/images/room-double.png', bed:'1.8m大床', area:'28㎡', window:true, breakfast:true, maxGuests:2, price:this.data.roomPrice||298 }})
  },

  buildCalendar() {
    const { calendarYear, calendarMonth } = this.data
    const fd = new Date(calendarYear, calendarMonth-1, 1), ld = new Date(calendarYear, calendarMonth, 0)
    const days = []
    for(let i=0;i<fd.getDay();i++) days.push({day:'',disabled:true})
    const t=new Date(); t.setHours(0,0,0,0)
    const ts=`${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}`
    for(let i=1;i<=ld.getDate();i++){
      const d=new Date(calendarYear,calendarMonth-1,i)
      const ds=`${calendarYear}-${String(calendarMonth).padStart(2,'0')}-${String(i).padStart(2,'0')}`
      days.push({day:i,disabled:d<t,date:ds,isToday:ds===ts})
    }
    this.setData({calendarDays:days})
  },

  openCalendar(e){ this.setData({calendarOpen:true,calendarType:e.currentTarget.dataset.type}) },
  closeCalendar(){ this.setData({calendarOpen:false}) },
  onDayTap(e){
    const {date,disabled}=e.currentTarget.dataset; if(disabled) return
    const {calendarType,checkInDate,checkOutDate}=this.data
    const wm=['周日','周一','周二','周三','周四','周五','周六']
    const d=new Date(date+'T00:00:00'), w=wm[d.getDay()]
    if(calendarType==='checkin'){
      if(date>=checkOutDate){
        const nd=new Date(d); nd.setDate(nd.getDate()+1)
        this.setData({checkInDate:date,checkInWeek:w,checkOutDate:wm[nd.getDay()],checkOutWeek:wm[nd.getDay()]})
      }else{this.setData({checkInDate:date,checkInWeek:w})}
    }else{
      if(date<=checkInDate){wx.showToast({title:'离店日期需晚于入住日期',icon:'none'});return}
      this.setData({checkOutDate:date,checkOutWeek:w})
    }
    this.calcNights(); this.calcPrice(); this.closeCalendar()
  },

  prevMonth(){
    let {calendarYear,calendarMonth}=this.data
    if(calendarMonth===1){this.setData({calendarYear:calendarYear-1,calendarMonth:12})}
    else{this.setData({calendarMonth:calendarMonth-1})}
    this.buildCalendar()
  },
  nextMonth(){
    let {calendarYear,calendarMonth}=this.data
    if(calendarMonth===12){this.setData({calendarYear:calendarYear+1,calendarMonth:1})}
    else{this.setData({calendarMonth:calendarMonth+1})}
    this.buildCalendar()
  },
  calcNights(){
    const d1=new Date(this.data.checkInDate+'T00:00:00'), d2=new Date(this.data.checkOutDate+'T00:00:00')
    this.setData({nights:Math.max(1,Math.round((d2-d1)/(86400000)))})
  },
  increaseRoom(){ this.setData({roomCount:Math.min(this.data.roomCount+1,5)}); this.calcPrice() },
  decreaseRoom(){ this.setData({roomCount:Math.max(this.data.roomCount-1,1)}); this.calcPrice() },
  calcPrice(){
    const {roomPrice,nights,roomCount}=this.data
    const rt=roomPrice*nights*roomCount, sf=0, dc=nights>=3?Math.floor(rt*0.1):0
    this.setData({roomTotal:rt,serviceFee:sf,discount:dc,totalPrice:rt-dc+sf})
  },
  onNameInput(e){this.setData({guestName:e.detail.value})},
  onPhoneInput(e){this.setData({guestPhone:e.detail.value})},
  onRemarkInput(e){this.setData({remark:e.detail.value})},
  onArrivalChange(e){this.setData({arrivalTime:this.data.arrivalTimes[e.detail.value]})},

  submitOrder(){
    const {guestName,guestPhone}=this.data
    if(!guestName.trim()){wx.showToast({title:'请填写入住人姓名',icon:'none'});return}
    if(!guestPhone.trim()||!/^1\d{10}$/.test(guestPhone)){wx.showToast({title:'请填写正确的手机号',icon:'none'});return}
    this.setData({showPayModal:true})
  },
  closePayModal(){this.setData({showPayModal:false})},

  // ========== 真实支付流程 ==========
  async confirmPay() {
    const that = this
    this.setData({ showPayModal: false, paying: true, submitting: true })
    wx.showLoading({ title: '创建订单...', mask: true })

    try {
      const { roomId, checkInDate, checkOutDate, roomCount, totalPrice, guestName, guestPhone, remark } = this.data

      // Step 1: 创建订单
      const orderRes = await app.request({
        url: '/api/orders',
        method: 'POST',
        data: {
          room_id: parseInt(roomId),
          checkin_date: checkInDate,
          checkout_date: checkOutDate,
          room_count: roomCount,
          total_price: totalPrice,
          guest_name: guestName,
          guest_phone: guestPhone,
          remark: remark
        }
      })
      if (!orderRes || !orderRes.id) throw new Error('订单创建失败')

      // Step 2: 获取支付参数
      const payRes = await app.request({
        url: '/api/payment/create',
        method: 'POST',
        data: { order_id: orderRes.id }
      })
      if (!payRes || !payRes.pay_params) throw new Error('获取支付参数失败')

      wx.hideLoading()
      const pp = payRes.pay_params

      // Step 3: 调起微信支付
      wx.requestPayment({
        timeStamp: pp.timeStamp,
        nonceStr: pp.nonceStr,
        package: pp.package,
        signType: pp.signType || 'RSA',
        paySign: pp.paySign,
        success() {
          wx.showToast({ title: '支付成功！', icon: 'success', duration: 2000 })
          that.setData({ paying: false, submitting: false })
          setTimeout(() => { wx.switchTab({ url: '/pages/orders/orders' }) }, 2000)
        },
        fail(err) {
          that.setData({ paying: false, submitting: false })
          if (err.errMsg.indexOf('cancel') === -1) {
            wx.showModal({ title: '支付未完成', content: '订单已生成，可在订单列表继续支付', showCancel: false, confirmText: '知道了' })
          }
        }
      })
    } catch (err) {
      wx.hideLoading()
      that.setData({ paying: false, submitting: false })
      wx.showModal({ title: '下单失败', content: err.message || '请稍后重试', showCancel: false })
    }
  },

  togglePolicy(){ this.setData({showPolicy:!this.data.showPolicy}) }
})
