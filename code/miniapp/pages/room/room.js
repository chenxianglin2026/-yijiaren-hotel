const app = getApp()

Page({
  data: {
    roomId: '',
    room: null,
    loading: true,
    swiperCurrent: 0,
    // 图片列表（模拟）
    images: []
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ roomId: options.id })
      this.loadRoomDetail(options.id)
    }
  },

  loadRoomDetail(roomId) {
    const that = this
    this.setData({ loading: true })

    // TODO: app.request({ url: `/rooms/${roomId}` })
    // 模拟数据
    const mockDetail = {
      id: parseInt(roomId),
      name: '雅致大床房',
      type: 'double',
      typeLabel: '大床房',
      area: '28㎡',
      bed: '1.8m × 2.0m 金可儿大床',
      window: true,
      breakfast: true,
      wifi: true,
      floor: '3-8层',
      maxGuests: 2,
      originalPrice: 368,
      price: 298,
      tags: ['限量特惠', '含双早'],
      available: 5,
      description: '简约雅致设计风格，暖米色调营造温馨舒适氛围。配备国际品牌金可儿床垫，300支高密度纯棉床品，让您享受深度睡眠。独立干湿分离卫浴，精选白茶香氛洗护用品。',
      highlights: [
        '金可儿床垫 · 星级睡眠体验',
        '300支纯棉床品 · 亲肤柔软',
        '干湿分离卫浴 · 白茶香氛洗护',
        '55寸智能电视 · 免费高速WiFi',
        '独立空调 · 迷你吧 · 保险箱',
        '24小时热水 · 电热水壶 · 茶具'
      ],
      notice: [
        '入住时间：14:00后',
        '退房时间：12:00前',
        '允许携带宠物（需加收清洁费）',
        '禁止在房间内吸烟',
        '免费提供婴儿床（需提前预约）'
      ],
      reviews: [
        { id: 1, user: '张先生', avatar: '', score: 5, content: '房间很干净，床品舒适，前台服务态度很好，下次还会再来。', date: '2024-05-20', tags: ['干净卫生', '服务热情'] },
        { id: 2, user: '李女士', avatar: '', score: 4, content: '酒店位置好，离西湖很近步行可达。房间布置温馨，早餐种类丰富。', date: '2024-05-15', tags: ['位置优越', '早餐丰富'] },
        { id: 3, user: '王先生', avatar: '', score: 5, content: '出差首选，智能门锁很方便，不用排队办入住，体验非常好。', date: '2024-05-10', tags: ['智能入住', '商务出行'] }
      ],
      reviewSummary: {
        avgScore: 4.8,
        total: 128,
        tags: [
          { label: '干净卫生', count: 96 },
          { label: '服务热情', count: 82 },
          { label: '床品舒适', count: 75 },
          { label: '位置优越', count: 68 }
        ]
      }
    }

    // 根据id调整数据
    const roomMap = {
      101: mockDetail,
      102: { ...mockDetail, id: 102, name: '豪华双床房', type: 'double', typeLabel: '双床房', area: '35㎡', bed: '1.35m × 2.0m 双床', price: 368, originalPrice: 458, tags: ['含双早', '高层景观'] },
      103: { ...mockDetail, id: 103, name: '舒适单人间', type: 'single', typeLabel: '单人间', area: '22㎡', bed: '1.5m × 2.0m 大床', price: 198, originalPrice: 258, tags: ['经济实惠'], breakfast: false },
      201: { ...mockDetail, id: 201, name: '尊享套房', type: 'suite', typeLabel: '套房', area: '55㎡', bed: '2.0m × 2.2m 大床', price: 598, originalPrice: 788, tags: ['独立客厅', '浴缸', '城市景观'] },
      202: { ...mockDetail, id: 202, name: '行政景观套房', type: 'suite', typeLabel: '套房', area: '65㎡', bed: '2.0m × 2.2m 大床', price: 738, originalPrice: 988, tags: ['行政酒廊', '管家服务', '全景视野'] },
      301: { ...mockDetail, id: 301, name: '亲子家庭房', type: 'family', typeLabel: '家庭房', area: '42㎡', bed: '1.8m大床 + 1.2m小床', price: 428, originalPrice: 528, tags: ['儿童主题', '含三早'] }
    }

    setTimeout(() => {
      const room = roomMap[roomId] || mockDetail
      // 生成模拟图片列表
      const images = [
        `/images/room-${room.type}-1.png`,
        `/images/room-${room.type}-2.png`,
        `/images/room-${room.type}-3.png`,
        `/images/room-${room.type}-4.png`
      ]
      that.setData({ room, images, loading: false })
    }, 400)
  },

  onSwiperChange(e) {
    this.setData({ swiperCurrent: e.detail.current })
  },

  onImageTap(e) {
    const urls = this.data.images
    const current = e.currentTarget.dataset.index
    wx.previewImage({ urls, current: urls[current] })
  },

  // 预订
  onBook() {
    const { room } = this.data
    wx.navigateTo({
      url: `/pages/booking/booking?roomId=${room.id}&roomName=${room.name}&price=${room.price}`
    })
  },

  // 联系客服
  onContact() {
    wx.makePhoneCall({
      phoneNumber: app.globalData.currentStore.phone || '0571-88886666'
    })
  }
})
