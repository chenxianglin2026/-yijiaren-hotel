/**
 * 伊家人酒店 - 保洁端
 * 工单列表、接单、开始清洁、完工打卡拍照
 */
const api = require('../../utils/api')
const C = require('../../utils/const')

Page({
  data: {
    // 当前保洁员信息
    cleaner: null,

    // 标签页
    activeTab: 'pending', // pending | mine | completed

    // 工单列表
    taskList: [],
    loading: false,
    page: 1,
    hasMore: true,

    // 工单类型/状态映射
    taskTypes: C.TASK_TYPES,
    taskStatus: C.TASK_STATUS,

    // 打卡弹窗
    showCheckin: false,
    currentTask: null,
    checkinPhoto: '',    // 本地临时路径
    checkinPhotoUrl: '', // 上传后URL
    checkinNote: '',
    submitting: false,

    // 空状态文案
    emptyText: '暂无待接工单',

    // 今日统计
    stats: { completed: 0, inProgress: 0, pending: 0 },
  },

  onLoad() {
    this.loadStats()
    this.loadTasks()
  },

  onShow() {
    // 每次切回刷新
    this.loadTasks(false)
    this.loadStats()
  },

  onPullDownRefresh() {
    Promise.all([this.loadTasks(false), this.loadStats()])
      .then(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadTasks(true)
    }
  },

  // ============== 加载统计 ==============
  async loadStats() {
    try {
      if (C.DEV_MODE) {
        this.setData({
          stats: { completed: 12, inProgress: 2, pending: 5 }
        })
        return
      }
      const res = await api.get('/api/cleaning/my-tasks')
      // 从列表中计算，或请求专门统计接口
    } catch (e) {
      if (C.DEV_MODE) console.error('加载统计失败:', e)
    }
  },

  // ============== 加载工单列表 ==============
  async loadTasks(loadMore = false) {
    if (this.data.loading) return

    const page = loadMore ? this.data.page + 1 : 1
    this.setData({ loading: true })

    try {
      if (C.DEV_MODE) {
        // Mock 数据
        await this.delay(600)
        const mockTasks = this.getMockTasks(page)
        const list = loadMore
          ? [...this.data.taskList, ...mockTasks]
          : mockTasks
        this.setData({
          taskList: list,
          page,
          hasMore: mockTasks.length >= C.PAGE_SIZE,
          loading: false,
        })
        return
      }

      const params = {
        page,
        page_size: C.PAGE_SIZE,
      }

      if (this.data.activeTab === 'mine') {
        // 保洁员自己的工单
        const res = await api.get('/api/cleaning/my-tasks', params)
        const list = loadMore
          ? [...this.data.taskList, ...res.items]
          : res.items
        this.setData({
          taskList: list,
          page,
          hasMore: res.items.length >= C.PAGE_SIZE,
          loading: false,
        })
      } else if (this.data.activeTab === 'completed') {
        params.status = 'completed'
        const res = await api.get('/api/cleaning/my-tasks', params)
        const list = loadMore
          ? [...this.data.taskList, ...res.items]
          : res.items
        this.setData({
          taskList: list,
          page,
          hasMore: res.items.length >= C.PAGE_SIZE,
          loading: false,
        })
      } else {
        // pending - 待接单
        params.status = 'pending'
        const res = await api.get('/api/cleaning/tasks', params)
        const list = loadMore
          ? [...this.data.taskList, ...res.items]
          : res.items
        this.setData({
          taskList: list,
          page,
          hasMore: res.items.length >= C.PAGE_SIZE,
          loading: false,
        })
      }
    } catch (e) {
      if (C.DEV_MODE) console.error('加载工单失败:', e)
      this.setData({ loading: false })
      if (!loadMore) {
        this.setData({ taskList: [] })
      }
    }
  },

  // ============== 切换 Tab ==============
  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab
    if (tab === this.data.activeTab) return
    this.setData({
      activeTab: tab,
      taskList: [],
      page: 1,
      hasMore: true,
      emptyText: tab === 'pending' ? '暂无待接工单' : tab === 'completed' ? '暂无已完成工单' : '暂无工单',
    })
    this.loadTasks(false)
  },

  // ============== 接单 ==============
  async onAccept(e) {
    const task = e.currentTarget.dataset.task
    wx.showModal({
      title: '确认接单',
      content: `确认接取 ${task.room_number} 的${C.TASK_TYPES[task.task_type]?.label || '保洁'}任务？`,
      confirmColor: '#c8a052',
      success: async (res) => {
        if (!res.confirm) return
        wx.showLoading({ title: '接单中...', mask: true })

        try {
          if (C.DEV_MODE) {
            await this.delay(400)
          } else {
            await api.post('/api/cleaning/tasks/accept', { task_id: task.id })
          }
          wx.hideLoading()
          wx.showToast({ title: '接单成功！', icon: 'success' })
          this.loadTasks(false)
          this.loadStats()
        } catch (e) {
          wx.hideLoading()
          wx.showToast({ title: e.msg || '接单失败', icon: 'none' })
        }
      },
    })
  },

  // ============== 开始清洁 ==============
  async onStartClean(e) {
    const task = e.currentTarget.dataset.task
    wx.showModal({
      title: '开始清洁',
      content: `确认开始清洁 ${task.room_number}？`,
      confirmColor: '#c8a052',
      success: async (res) => {
        if (!res.confirm) return
        wx.showLoading({ title: '开始清洁...', mask: true })

        try {
          if (C.DEV_MODE) {
            await this.delay(400)
          } else {
            await api.post('/api/cleaning/tasks/start', { task_id: task.id })
          }
          wx.hideLoading()
          wx.showToast({ title: '已开始清洁', icon: 'success' })
          this.loadTasks(false)
          this.loadStats()
        } catch (e) {
          wx.hideLoading()
          wx.showToast({ title: e.msg || '操作失败', icon: 'none' })
        }
      },
    })
  },

  // ============== 打开完工打卡弹窗 ==============
  onCheckin(e) {
    const task = e.currentTarget.dataset.task
    this.setData({
      showCheckin: true,
      currentTask: task,
      checkinPhoto: '',
      checkinPhotoUrl: '',
      checkinNote: '',
    })
  },

  closeCheckin() {
    this.setData({ showCheckin: false, currentTask: null })
  },

  // ============== 拍照 ==============
  onTakePhoto() {
    const that = this
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera'],
      camera: 'back',
      success(res) {
        const tempFilePath = res.tempFiles[0].tempFilePath
        that.setData({ checkinPhoto: tempFilePath })
        // 模拟上传（实际项目中上传到OSS/服务器）
        that.setData({ checkinPhotoUrl: tempFilePath })
      },
      fail(err) {
        if (err.errMsg.indexOf('cancel') === -1) {
          wx.showToast({ title: '拍照失败', icon: 'none' })
        }
      },
    })
  },

  // ============== 提交完工 ==============
  async onSubmitCheckin() {
    if (!this.data.checkinPhoto) {
      wx.showToast({ title: '请拍摄完工照片', icon: 'none' })
      return
    }
    if (this.data.submitting) return

    this.setData({ submitting: true })
    wx.showLoading({ title: '提交中...', mask: true })

    const task = this.data.currentTask

    try {
      if (C.DEV_MODE) {
        await this.delay(800)
      } else {
        // 先上传照片获得 URL，再调用接口
        let photoUrls = this.data.checkinPhotoUrl
        // 如果是本地文件，先上传
        if (this.data.checkinPhoto && !this.data.checkinPhotoUrl.startsWith('http')) {
          try {
            const uploadRes = await api.upload('/api/upload', this.data.checkinPhoto, 'file')
            photoUrls = uploadRes.url || this.data.checkinPhotoUrl
          } catch (e) {
            // 上传失败也用本地路径
            if (C.DEV_MODE) console.warn('照片上传失败，使用本地路径', e)
          }
        }

        await api.post('/api/cleaning/tasks/complete', {
          task_id: task.id,
          photo_urls: JSON.stringify([photoUrls]),
          notes: this.data.checkinNote || undefined,
        })
      }

      wx.hideLoading()
      this.setData({ submitting: false, showCheckin: false, currentTask: null })
      wx.showToast({ title: '完工打卡成功！', icon: 'success' })
      this.loadTasks(false)
      this.loadStats()
    } catch (e) {
      wx.hideLoading()
      this.setData({ submitting: false })
      wx.showToast({ title: e.msg || '提交失败', icon: 'none' })
    }
  },

  onCheckinNoteInput(e) {
    this.setData({ checkinNote: e.detail.value })
  },

  // ============== 查看详情 ==============
  onTaskDetail(e) {
    const task = e.currentTarget.dataset.task
    // 展示工单详情
    const statusInfo = C.TASK_STATUS[task.status] || {}
    const typeInfo = C.TASK_TYPES[task.task_type] || {}
    wx.showModal({
      title: `${task.room_number} - ${typeInfo.label || task.task_type}`,
      content: [
        `状态：${statusInfo.label || task.status}`,
        `类型：${typeInfo.label || task.task_type}`,
        task.notes ? `备注：${task.notes}` : '',
        task.photo_urls ? `完工照片：已上传` : '',
        task.accepted_at ? `接单时间：${task.accepted_at}` : '',
        task.completed_at ? `完成时间：${task.completed_at}` : '',
      ].filter(Boolean).join('\n'),
      confirmColor: '#c8a052',
      showCancel: false,
      confirmText: '知道了',
    })
  },

  // ============== Mock 数据 ==============
  getMockTasks(page) {
    const mockList = [
      {
        id: 1001, hotel_id: 1, room_number: '301', task_type: 'cleanup',
        status: 'pending', notes: '客人退房，需全面清洁消毒，更换床品毛巾',
        created_at: '2026-05-29T10:30:00', accepted_at: null, completed_at: null,
        cleaner_id: null,
      },
      {
        id: 1002, hotel_id: 1, room_number: '508', task_type: 'daily',
        status: 'pending', notes: '住客需求日常打扫，补充矿泉水',
        created_at: '2026-05-29T11:00:00', accepted_at: null, completed_at: null,
        cleaner_id: null,
      },
      {
        id: 1003, hotel_id: 1, room_number: '712', task_type: 'deep_clean',
        status: 'pending', notes: 'VIP套房深度保养，地毯清洁打蜡',
        created_at: '2026-05-29T09:15:00', accepted_at: null, completed_at: null,
        cleaner_id: null,
      },
      {
        id: 1004, hotel_id: 1, room_number: '206', task_type: 'cleanup',
        status: 'accepted', notes: '客人已退房',
        created_at: '2026-05-29T08:45:00', accepted_at: '2026-05-29T08:50:00',
        completed_at: null, cleaner_id: 10,
      },
      {
        id: 1005, hotel_id: 1, room_number: '415', task_type: 'turndown',
        status: 'in_progress', notes: '夜床服务，需要更换毛巾和铺夜床',
        created_at: '2026-05-29T16:00:00', accepted_at: '2026-05-29T16:05:00',
        completed_at: null, cleaner_id: 10,
      },
      {
        id: 1006, hotel_id: 1, room_number: '102', task_type: 'cleanup',
        status: 'completed', notes: '退房清洁',
        created_at: '2026-05-29T07:30:00', accepted_at: '2026-05-29T07:35:00',
        completed_at: '2026-05-29T08:20:00', cleaner_id: 10,
        photo_urls: '["/images/clean-102.jpg"]',
      },
      {
        id: 1007, hotel_id: 1, room_number: '220', task_type: 'cleanup',
        status: 'completed', notes: '退房清洁',
        created_at: '2026-05-29T09:00:00', accepted_at: '2026-05-29T09:05:00',
        completed_at: '2026-05-29T09:50:00', cleaner_id: 10,
        photo_urls: '["/images/clean-220.jpg"]',
      },
      {
        id: 1008, hotel_id: 1, room_number: '330', task_type: 'daily',
        status: 'completed', notes: '日常打扫',
        created_at: '2026-05-29T10:00:00', accepted_at: '2026-05-29T10:05:00',
        completed_at: '2026-05-29T10:35:00', cleaner_id: 10,
      },
    ]

    if (this.data.activeTab === 'pending') {
      return mockList.filter(t => t.status === 'pending')
    } else if (this.data.activeTab === 'completed') {
      return mockList.filter(t => t.status === 'completed')
    }
    // 'mine' 返回保洁员已接的单
    return mockList.filter(t => ['accepted', 'in_progress'].includes(t.status))
  },

  // ============== 工具 ==============
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
  },
})
