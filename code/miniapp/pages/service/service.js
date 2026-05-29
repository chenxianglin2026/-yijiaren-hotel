/**
 * 伊家人酒店 - 在店服务
 * 呼叫保洁 / 客房送物 / 维修报修
 */
const api = require('../../utils/api')
const C = require('../../utils/const')

Page({
  data: {
    // 门店信息
    hotelId: 1,
    roomNumber: '', // 可以从入住信息获取

    // 服务类型列表
    serviceTypes: [
      {
        key: 'cleaning',
        icon: '🧹',
        label: '呼叫保洁',
        desc: '房间打扫、更换床品',
        color: '#E8A838',
        bg: '#FFF8E8',
      },
      {
        key: 'delivery',
        icon: '📦',
        label: '客房送物',
        desc: '毛巾、牙具、矿泉水等',
        color: '#5B8DEF',
        bg: '#EDF4FF',
      },
      {
        key: 'maintenance',
        icon: '🔧',
        label: '维修报修',
        desc: '空调、热水、灯具等',
        color: '#C56C6C',
        bg: '#FFF0F0',
      },
      {
        key: 'other',
        icon: '💁',
        label: '其他服务',
        desc: '加床、叫醒等',
        color: '#6BAA75',
        bg: '#F0FAF0',
      },
    ],

    // 快捷入口
    quickActions: [
      { icon: '🛎️', label: '一键呼叫前台', action: 'callFrontDesk' },
      { icon: '📋', label: '我的请求', action: 'myRequests' },
    ],

    // 弹窗
    showForm: false,
    currentService: null,
    formData: {
      description: '',
      priority: 'normal',
      roomNumber: '',
    },
    submitting: false,

    // 请求列表
    requestList: [],
    requestLoading: false,
    requestPage: 1,
    requestHasMore: true,
  },

  onLoad() {
    // 获取当前门店和房间
    const app = getApp()
    if (app.globalData.currentStore) {
      this.setData({ hotelId: app.globalData.currentStore.id })
    }
    // 尝试从入住信息中获取房号
    const checkinInfo = wx.getStorageSync('checkinInfo')
    if (checkinInfo && checkinInfo.roomNumber) {
      this.setData({
        roomNumber: checkinInfo.roomNumber,
        'formData.roomNumber': checkinInfo.roomNumber,
      })
    }
  },

  onShow() {
    // 刷新服务请求列表
    this.loadRequests(false)
  },

  // ============== 选择服务类型 ==============
  onServiceTap(e) {
    const service = e.currentTarget.dataset.service
    this.setData({
      showForm: true,
      currentService: service,
      'formData.description': '',
      'formData.priority': 'normal',
    })
    if (!this.data.formData.roomNumber && !this.data.roomNumber) {
      // 如果没房号，提示填写
    }
  },

  closeForm() {
    this.setData({ showForm: false, currentService: null })
  },

  // ============== 表单输入 ==============
  onDescInput(e) {
    this.setData({ 'formData.description': e.detail.value })
  },
  onRoomInput(e) {
    this.setData({ 'formData.roomNumber': e.detail.value, roomNumber: e.detail.value })
  },
  onPriorityTap(e) {
    const p = e.currentTarget.dataset.priority
    this.setData({ 'formData.priority': p })
  },

  // ============== 提交服务请求 ==============
  async onSubmitRequest() {
    const { formData, currentService } = this.data

    if (!formData.roomNumber.trim()) {
      wx.showToast({ title: '请填写房间号', icon: 'none' })
      return
    }
    if (!formData.description.trim()) {
      wx.showToast({ title: '请填写服务描述', icon: 'none' })
      return
    }
    if (this.data.submitting) return

    this.setData({ submitting: true })
    wx.showLoading({ title: '提交中...', mask: true })

    try {
      if (C.DEV_MODE) {
        await this.delay(600)
      } else {
        await api.post('/api/cleaning/service', {
          hotel_id: this.data.hotelId,
          room_number: formData.roomNumber.trim(),
          request_type: currentService.key,
          description: formData.description.trim(),
          priority: formData.priority,
        })
      }

      wx.hideLoading()
      this.setData({ submitting: false, showForm: false, currentService: null })
      wx.showToast({ title: '请求已提交', icon: 'success' })

      // 保存当前房号
      wx.setStorageSync('lastRoomNumber', formData.roomNumber.trim())

      // 刷新列表
      setTimeout(() => this.loadRequests(false), 500)
    } catch (e) {
      wx.hideLoading()
      this.setData({ submitting: false })
      wx.showToast({ title: e.msg || '提交失败', icon: 'none' })
    }
  },

  // ============== 加载我的请求列表 ==============
  async loadRequests(loadMore) {
    if (this.data.requestLoading) return
    const page = loadMore ? this.data.requestPage + 1 : 1

    this.setData({ requestLoading: true })

    try {
      if (C.DEV_MODE) {
        await this.delay(500)
        const mockList = this.getMockRequests()
        this.setData({
          requestList: loadMore
            ? [...this.data.requestList, ...mockList]
            : mockList,
          requestPage: page,
          requestHasMore: mockList.length >= C.PAGE_SIZE,
          requestLoading: false,
        })
        return
      }

      const res = await api.get('/api/cleaning/service', {
        page,
        page_size: C.PAGE_SIZE,
      })

      this.setData({
        requestList: loadMore
          ? [...this.data.requestList, ...res.items]
          : res.items,
        requestPage: page,
        requestHasMore: res.items.length >= C.PAGE_SIZE,
        requestLoading: false,
      })
    } catch (e) {
      console.error('加载请求失败:', e)
      this.setData({ requestLoading: false })
    }
  },

  // ============== 快捷操作 ==============
  onQuickAction(e) {
    const action = e.currentTarget.dataset.action
    if (action === 'callFrontDesk') {
      const app = getApp()
      const store = app.globalData.currentStore
      if (store && store.phone) {
        wx.makePhoneCall({ phoneNumber: store.phone })
      } else {
        wx.showModal({
          title: '联系前台',
          content: '请拨打前台电话：0571-88886666',
          confirmText: '拨打',
          cancelText: '取消',
          confirmColor: '#C8A96E',
          success: (res) => {
            if (res.confirm) {
              wx.makePhoneCall({ phoneNumber: '057188886666' })
            }
          },
        })
      }
    } else if (action === 'myRequests') {
      // 滚动到下方列表
      wx.pageScrollTo({ selector: '.request-section', duration: 300 })
    }
  },

  // ============== 查看请求详情 ==============
  onRequestDetail(e) {
    const req = e.currentTarget.dataset.request
    const statusInfo = C.SERVICE_STATUS[req.status] || {}
    const typeInfo = this.data.serviceTypes.find(s => s.key === req.request_type) || {}
    wx.showModal({
      title: `${typeInfo.label || req.request_type}`,
      content: [
        `房间号：${req.room_number}`,
        `状态：${statusInfo.label || req.status}`,
        `描述：${req.description}`,
        req.remark ? `处理备注：${req.remark}` : '',
        `时间：${(req.created_at || '').slice(0, 16).replace('T', ' ')}`,
      ].filter(Boolean).join('\n'),
      confirmColor: '#C8A96E',
      showCancel: false,
      confirmText: '知道了',
    })
  },

  // ============== Mock 数据 ==============
  getMockRequests() {
    return [
      {
        id: 2001, user_id: 1, hotel_id: 1,
        room_number: '301', request_type: 'cleaning',
        description: '需要打扫卫生间，补充沐浴露和洗发水',
        priority: 'normal', status: 'pending',
        created_at: '2026-05-29T14:30:00',
      },
      {
        id: 2002, user_id: 1, hotel_id: 1,
        room_number: '301', request_type: 'delivery',
        description: '需要2瓶矿泉水、一套牙具',
        priority: 'normal', status: 'completed',
        created_at: '2026-05-29T13:00:00',
        completed_at: '2026-05-29T13:15:00',
        remark: '已送达房间',
      },
      {
        id: 2003, user_id: 1, hotel_id: 1,
        room_number: '301', request_type: 'maintenance',
        description: '空调出风口有异响，制热效果差',
        priority: 'urgent', status: 'accepted',
        created_at: '2026-05-29T12:00:00',
        accepted_at: '2026-05-29T12:05:00',
      },
    ]
  },

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
  },
})
